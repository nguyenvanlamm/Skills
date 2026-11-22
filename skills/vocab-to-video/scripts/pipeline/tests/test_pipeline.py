"""The parts of the pipeline around the storyboard: text checks, vocabulary counting, the speech
cache, the upload-text precheck and the still frames. Run from scripts/pipeline:
uv run python -m unittest discover -s tests -v
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_video  # noqa: E402
import publish  # noqa: E402
import run  # noqa: E402
import tts  # noqa: E402
from common import load_config, read_json, tokens, vocab_hits, write_json  # noqa: E402
from validate_dialogue import validate  # noqa: E402

CFG = load_config()


def good_dialogue() -> dict:
    """A small A2 dialogue that passes every check but the word total, which tests don't look at."""
    texts = ["Salut Hugo, tu vas déménager bientôt ?", "Oui, mon loyer est trop cher.",
             "Tu vas déménager où ?", "Près du parc, le loyer est correct."]
    return {"level": "A2", "title": "Hugo déménage",
            "vocab": [{"word": "déménager", "forms": ["déménager"]}, {"word": "le loyer", "forms": ["loyer"]}],
            "hook": {"speaker": "lea", "text": "Tu comprends ce dialogue ?"},
            "short": {"from": 1, "to": 2},
            "lines": [{"speaker": "lea" if i % 2 == 0 else "hugo", "text": t} for i, t in enumerate(texts)]}


def problems_of(d: dict) -> tuple[list[str], list[str]]:
    errors, warnings, _ = validate(d, CFG)
    return [e for e in errors if "words; A2 needs" not in e], warnings


class ValidateDialogue(unittest.TestCase):
    def test_good_dialogue_has_no_other_error(self):
        self.assertEqual(problems_of(good_dialogue())[0], [])

    def test_malformed_input_is_a_fail_line_not_a_crash(self):
        for change in ({"lines": ["Salut"]}, {"vocab": [{"forms": ["x"]}]}, {"vocab": ["loyer"]},
                       {"hook": "Salut ?"}, {"scenes": ["wide"]}, {"cast": ["hugo"]},
                       {"scenes": [{"kind": "wide", "lines": [1, 4], "chars": ["lea"]}]},
                       {"scenes": [{"kind": "wide", "lines": [1, 4], "chars": [{"id": "lea"}], "beats": {"at": "Salut"}}]}):
            with self.subTest(change=change):
                errors, _ = problems_of({**good_dialogue(), **change})
                self.assertTrue(errors)

    def test_storyboard_numbers_are_checked(self):
        base = {"kind": "wide", "lines": [1, 4], "chars": [{"id": "lea"}, {"id": "hugo"}]}
        for change, word in (({"zoom": 1.3}, "zoom"), ({"lines": [True, 4]}, "lines"),
                             ({"chars": [{"id": "lea", "x": "left"}]}, "x of"),
                             ({"chars": [{"id": "lea", "s": -1}]}, "s of"),
                             ({"chars": [{"id": "lea"}, {"id": "lea"}]}, "twice"),
                             ({"beats": [{"at": "+inf", "pose": "wave"}]}, "+seconds"),
                             ({"beats": [{"at": "+-3", "pose": "wave"}]}, "+seconds"),
                             ({"beats": [{"at": "+nan", "pose": "wave"}]}, "+seconds")):
            with self.subTest(change=change):
                errors, _ = problems_of({**good_dialogue(), "scenes": [{**base, **change}]})
                self.assertTrue(any(word in e for e in errors), errors)

    def test_soft_rules_are_warnings(self):
        d = good_dialogue()
        d["title"] = "Un titre vraiment beaucoup trop long pour le haut de la vidéo"
        d["lines"][1]["text"] = "Oui, mon loyer est de 800 euros (trop cher)."
        _, warnings = problems_of(d)
        for word in ("title is", "digits", "brackets"):
            self.assertTrue(any(word in w for w in warnings), (word, warnings))

    def test_level_names_are_not_digits(self):
        d = good_dialogue()
        d["lines"][0]["text"] = "Salut Hugo, tu vas déménager après ton niveau A2 ?"
        self.assertFalse(any("digits" in w for w in problems_of(d)[1]))

    def test_punctuation_only_line(self):
        d = good_dialogue()
        d["lines"][2]["text"] = "... ?"
        self.assertTrue(any("line 3: no words" in e for e in problems_of(d)[0]))

    def test_hook_speaker_walking_in_is_reported(self):
        d = good_dialogue()
        d["scenes"] = [{"kind": "wide", "lines": [1, 4], "chars": [{"id": "lea", "enter": "left"}, {"id": "hugo"}]}]
        self.assertTrue(any("says the hook" in w for w in problems_of(d)[1]))

    def test_hat_tip_needs_a_hat(self):
        d = good_dialogue()
        d["scenes"] = [{"kind": "wide", "lines": [1, 4], "chars": [{"id": "lea"}, {"id": "hugo", "pose": "tiphat"}]}]
        self.assertTrue(any("no hat" in w for w in problems_of(d)[1]))
        d["cast"] = {"hugo": {"hat": "cap"}}
        self.assertFalse(any("no hat" in w for w in problems_of(d)[1]))


class VocabHits(unittest.TestCase):
    def test_one_use_matched_by_two_forms_counts_once(self):
        vocab = [{"word": "s'habituer", "forms": ["habitue", "m'habitue"]}]
        marks, counts = vocab_hits(tokens("Je m'habitue vite."), vocab)
        self.assertEqual(counts, {"s'habituer": 1})
        self.assertEqual(marks, [False, True, False])

    def test_two_uses_count_twice(self):
        vocab = [{"word": "déménager", "forms": ["déménage", "Déménage", "déménager"]}]
        _, counts = vocab_hits(tokens("Je déménage. Tu vas déménager ?"), vocab)
        self.assertEqual(counts, {"déménager": 2})


class FakeProvider:
    name = "fake"

    def __init__(self):
        self.said, self.fail_on = [], None

    def synth(self, text, voice, rate, out):
        if text == self.fail_on:
            out.write_bytes(b"half a fi")  # what a dropped connection leaves behind
            raise RuntimeError("network down")
        self.said.append(text)
        out.write_bytes(f"audio of {text}".encode())
        return [{"text": text, "start_ms": 0, "end_ms": 500}]


class SpeechCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "lines"
        self.prov = FakeProvider()
        tts.PROVIDERS["fake"] = lambda: self.prov
        self.addCleanup(tts.PROVIDERS.pop, "fake")

    def synth(self, texts):
        d = {"level": "A2", "hook": {"speaker": "lea", "text": "Tu écoutes ?"},
             "lines": [{"speaker": "lea" if i % 2 == 0 else "hugo", "text": t} for i, t in enumerate(texts)]}
        return tts.synth_lines(d, CFG, self.dir, provider="fake", log=lambda s: None)

    def audio(self, n):
        return (self.dir / f"{n:03d}.mp3").read_bytes().decode()

    def test_turns_added_in_the_middle_cost_only_their_own_calls(self):
        self.synth(["Un.", "Deux.", "Trois."])
        self.prov.said.clear()
        self.synth(["Un.", "Ah ?", "Oui.", "Deux.", "Trois."])  # a question and its answer
        self.assertEqual(self.prov.said, ["Ah ?", "Oui."])
        self.assertEqual([self.audio(n) for n in (1, 2, 3, 4, 5)],
                         ["audio of Un.", "audio of Ah ?", "audio of Oui.", "audio of Deux.", "audio of Trois."])
        self.assertEqual(read_json(self.dir / "004.json")["index"], 4)

    def test_a_failed_call_never_passes_for_finished_audio(self):
        self.synth(["Un.", "Deux."])
        self.prov.fail_on = "Autre."
        with self.assertRaises(RuntimeError):
            self.synth(["Un.", "Autre."])
        self.prov.fail_on = None
        self.prov.said.clear()
        self.synth(["Un.", "Deux."])
        self.assertEqual(self.audio(2), "audio of Deux.")
        self.assertEqual(list(self.dir.glob("*.part")), [])

    def test_removed_lines_are_deleted(self):
        self.synth(["Un.", "Deux.", "Trois."])
        self.synth(["Un."])
        self.assertEqual(sorted(p.name for p in self.dir.glob("*.mp3")), ["000.mp3", "001.mp3"])


class Precheck(unittest.TestCase):
    def test_metadata_problems_are_found_without_audio_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "ep" / "A2"
            d.mkdir(parents=True)
            self.assertIn("missing", publish.precheck(d, good_dialogue(), CFG)[0])
            write_json(d / "metadata.json", {"youtube": {}})
            self.assertIn("missing or malformed", publish.precheck(d, good_dialogue(), CFG)[0])
            self.assertFalse((d / "out").exists())

    def test_chapters_left_out_are_named(self):
        uses = {"un": 12_000, "deux": 15_000, "trois": 30_000}
        chaps = publish.chapters(uses, "Début")
        self.assertEqual([label for _, label in chaps], ["Début", "un", "trois"])


class RunSteps(unittest.TestCase):
    def test_until_build_stops_before_the_upload_texts(self):
        """`--until build` must not ask for metadata.json (it used to run on to the thumbnail)."""
        source = Path(run.__file__).read_text(encoding="utf-8")
        build_stop = source.index('if args.until == "build":')
        self.assertLess(build_stop, source.index('begin("publish")'))
        self.assertLess(source.index('if args.until == "publish":'), source.index('begin("thumbnail")'))


class Frames(unittest.TestCase):
    def test_one_moment_per_shot_inside_the_shot(self):
        shots = [{"startMs": 0, "endMs": 4000, "chars": [{"id": "lea"}]},
                 {"startMs": 4000, "endMs": 6000, "chars": [{"id": "hugo", "exit": "right"}]}]
        self.assertEqual(check_video.shot_moments({"shots": shots}), [2.8, 4.4])

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is not installed")
    def test_contact_sheet_is_made(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "v.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=10:duration=3",
                            "-pix_fmt", "yuv420p", str(video)], check=True)
            sheets, singles = check_video.contact_sheets(video, [0.5, 1.5, 2.5, 2.8], Path(tmp) / "check", False)
            self.assertEqual((len(sheets), len(singles)), (1, 4))
            self.assertTrue(all(Path(f).stat().st_size > 0 for f in sheets + singles))


if __name__ == "__main__":
    unittest.main()
