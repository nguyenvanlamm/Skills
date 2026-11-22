"""The storyboard: validation, the generated fallback, shot timing and the mouth track.
Run from scripts/pipeline: uv run python -m unittest discover -s tests -v
"""
import array
import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scenes  # noqa: E402
from common import load_config, tokens  # noqa: E402

CFG = load_config()
TEXTS = ["Salut Hugo ! Ça va ?", "Je vais déménager samedi.", "Ah bon ? Pourquoi ?",
         "Mon voisin est bruyant.", "Je vais à l'école demain.", "Tu as déménagé hier ?"]


def dialogue(scene_list=None):
    d = {"lines": [{"speaker": "lea" if i % 2 == 0 else "hugo", "text": t} for i, t in enumerate(TEXTS)]}
    if scene_list is not None:
        d["scenes"] = scene_list
    return d


def timeline(d, with_hook=True, keep=None):
    """Lines as build_episode writes them: each lasts 2 s, 400 ms apart, words spread evenly."""
    out, indices, t = [], [], 300
    rows = ([(0, {"speaker": "lea", "text": "Ton voisin est bruyant ?"})] if with_hook else []) + \
        [(i, l) for i, l in enumerate(d["lines"], 1) if keep is None or i in keep]
    for idx, line in rows:
        toks = tokens(line["text"])
        step = 2000 / len(toks)
        out.append({"speaker": line["speaker"], "text": line["text"], "startMs": t, "endMs": t + 2000,
                    "words": [{"text": w, "startMs": round(t + k * step), "endMs": round(t + (k + 1) * step),
                               "isVocab": False} for k, w in enumerate(toks)]})
        indices.append(idx)
        t += 2400
    return out, indices, t + 1000


WIDE = {"kind": "wide", "set": "street", "time": "day", "chars": [{"id": "lea"}, {"id": "hugo"}]}


class Validate(unittest.TestCase):
    def errors(self, scene_list):
        return scenes.validate_scenes(dialogue(scene_list), CFG)[0]

    def test_good_storyboard_passes(self):
        good = [dict(WIDE, lines=[1, 3], beats=[{"at": "déménager", "pose": "explain"}],
                     labels=[{"at": "déménager", "text": "déménager"}]),
                {"kind": "closeup", "lines": [4, 4], "chars": [{"id": "hugo", "emotion": "angry"}]},
                dict(WIDE, lines=[5, 6])]
        self.assertEqual(self.errors(good), [])

    def test_no_scenes_is_a_warning_not_an_error(self):
        errors, warnings = scenes.validate_scenes(dialogue(), CFG)
        self.assertEqual(errors, [])
        self.assertTrue(any("no `scenes`" in w for w in warnings))

    def test_gap_and_short_coverage(self):
        self.assertTrue(any("line 3 is the next" in e for e in self.errors([dict(WIDE, lines=[1, 2]), dict(WIDE, lines=[4, 6])])))
        self.assertTrue(any("stop at line 4" in e for e in self.errors([dict(WIDE, lines=[1, 4])])))

    def test_unknown_names(self):
        bad = [dict(WIDE, kind="drone", lines=[1, 6], set="moon",
                    chars=[{"id": "lea", "pose": "fly"}, {"id": "zoe"}],
                    beats=[{"at": "Salut", "emotion": "furious"}])]
        text = " | ".join(self.errors(bad))
        for needle in ("kind 'drone'", "set 'moon'", "pose 'fly'", "unknown character 'zoe'", "emotion 'furious'"):
            self.assertIn(needle, text)

    def test_cue_must_be_said_in_the_scene(self):
        errs = self.errors([dict(WIDE, lines=[1, 3], beats=[{"at": "bruyant", "pose": "shrug"}]), dict(WIDE, lines=[4, 6])])
        self.assertTrue(any("'bruyant' is not said" in e for e in errs))

    def test_closeup_takes_one_character(self):
        errs = self.errors([dict(WIDE, kind="closeup", lines=[1, 6])])
        self.assertTrue(any("exactly one character" in e for e in errs))

    def test_bad_cast_value(self):
        d = dialogue()
        d["cast"] = {"lea": {"hair": "mohawk"}}
        self.assertTrue(any("hair 'mohawk'" in e for e in scenes.validate_scenes(d, CFG)[0]))


class FindWord(unittest.TestCase):
    def test_exact_elided_and_inflected(self):
        self.assertEqual(scenes.find_word("samedi", TEXTS), (1, 3))
        self.assertEqual(scenes.find_word("école", TEXTS), (4, 3))       # l'école
        self.assertEqual(scenes.find_word("Ça va", TEXTS), (0, 2))       # two words in a row
        self.assertEqual(scenes.find_word("déménagé", TEXTS[:2]), (1, 2))  # another form of the verb
        self.assertIsNone(scenes.find_word("déménagement", TEXTS))  # another word
        self.assertIsNone(scenes.find_word("loyer", TEXTS))


class Cues(unittest.TestCase):
    def test_a_word_inside_another_word_is_not_a_match(self):
        self.assertIsNone(scenes.find_word("loyer", ["Je vais employer un ami."]))
        self.assertIsNone(scenes.find_word("comme", ["Comment ça va ?"]))

    def test_elision_before_a_short_word_and_typed_without_accents(self):
        self.assertEqual(scenes.find_word("un an", ["C'est un bail d'un an."]), (0, 3))
        self.assertEqual(scenes.find_word("ecole", ["Je vais à l'école demain."]), (0, 3))
        self.assertEqual(scenes.find_word("à école", ["Je vais à l'école demain."]), (0, 2))
        self.assertEqual(scenes.find_word("Ca va", ["Salut ! Ça va ?"]), (0, 1))

    def test_a_beat_for_a_character_lands_on_their_own_line(self):
        lines = [{"speaker": "lea", "text": "Je paie sept cents euros."},
                 {"speaker": "hugo", "text": "Sept cents euros !"}]
        self.assertEqual(scenes.pick_hit("sept cents", lines, "hugo"), ((1, 0), 1))
        self.assertEqual(scenes.pick_hit("sept cents", lines, None), ((0, 2), 2))

    def test_a_repeated_cue_word_is_reported(self):
        d = dialogue([{**WIDE, "lines": [1, 6], "beats": [{"at": "vais", "pose": "wave"}]}])
        _, warnings = scenes.validate_scenes(d, CFG)
        self.assertTrue(any("is said 2 times" in w for w in warnings), warnings)

    def test_a_beat_with_no_who_on_an_offscreen_word_is_reported(self):
        d = dialogue([{**WIDE, "lines": [1, 1]},
                      {"kind": "closeup", "lines": [2, 2], "chars": [{"id": "lea"}],
                       "beats": [{"at": "déménager", "emotion": "shocked"}]},
                      {**WIDE, "lines": [3, 6]}])
        _, warnings = scenes.validate_scenes(d, CFG)
        self.assertTrue(any("is not in the picture" in w for w in warnings), warnings)

    def test_in_the_short_cut_a_cue_never_moves_to_another_line(self):
        # "déménager" is said in line 2; the cut keeps lines 5-6, where line 6 says "déménagé".
        d = dialogue([{**WIDE, "lines": [1, 6], "labels": [{"at": "déménager", "text": "déménager"}]}])
        lines, indices, total = timeline(d, with_hook=False, keep={5, 6})
        shots = scenes.resolve_shots(d, CFG, lines, indices, total, log=lambda s: None)
        self.assertEqual(shots[0]["labels"], [])

    def test_a_seconds_cue_past_the_end_is_pulled_back(self):
        d = dialogue([{**WIDE, "lines": [1, 6], "beats": [{"at": "+900", "who": "lea", "pose": "wave"}]}])
        lines, indices, total = timeline(d)
        said = []
        shots = scenes.resolve_shots(d, CFG, lines, indices, total, log=said.append)
        beat = next(b for b in shots[0]["beats"] if b.get("pose") == "wave")
        self.assertLess(beat["atMs"], shots[0]["endMs"])
        self.assertTrue(any("after the end" in s for s in said))


class AutoScenes(unittest.TestCase):
    def test_generated_storyboard_is_valid_and_complete(self):
        d = dialogue()
        d["scenes"] = scenes.auto_scenes(d, CFG)
        self.assertEqual(scenes.validate_scenes(d, CFG)[0], [])
        self.assertEqual(d["scenes"][0]["chars"][0]["id"], "lea")  # the left-hand speaker stands first
        self.assertIn("closeup", [s["kind"] for s in d["scenes"]])


class Resolve(unittest.TestCase):
    def test_shots_tile_the_timeline(self):
        d = dialogue([dict(WIDE, lines=[1, 2]), {"kind": "closeup", "lines": [3, 3], "chars": [{"id": "lea"}]},
                      dict(WIDE, lines=[4, 6])])
        lines, idx, dur = timeline(d)
        shots = scenes.resolve_shots(d, CFG, lines, idx, dur, log=lambda *_: None)
        self.assertEqual(shots[0]["startMs"], 0)
        self.assertEqual(shots[-1]["endMs"], dur)
        for a, b in zip(shots, shots[1:]):
            self.assertEqual(a["endMs"], b["startMs"])
        # A cut falls in the pause before the scene's first line.
        third = lines[idx.index(3)]
        self.assertLess(lines[idx.index(2)]["endMs"], shots[1]["startMs"])
        self.assertLess(shots[1]["startMs"], third["startMs"])

    def test_cue_lands_on_the_word_and_not_on_the_hook(self):
        d = dialogue([dict(WIDE, lines=[1, 4], beats=[{"at": "bruyant", "pose": "stressed"}],
                           labels=[{"at": "voisin", "text": "le voisin"}]), dict(WIDE, lines=[5, 6])])
        lines, idx, dur = timeline(d)  # the hook also says "voisin" and "bruyant"
        shot = scenes.resolve_shots(d, CFG, lines, idx, dur, log=lambda *_: None)[0]
        line4 = lines[idx.index(4)]
        beat = next(b for b in shot["beats"] if b.get("pose") == "stressed")
        self.assertEqual(beat["atMs"], line4["words"][3]["startMs"])
        self.assertEqual(beat["who"], "hugo")  # the one who says the word
        self.assertEqual(shot["labels"][0]["atMs"], line4["words"][1]["startMs"])

    def test_undirected_characters_gesture_when_they_speak(self):
        d = dialogue([dict(WIDE, lines=[1, 6])])
        lines, idx, dur = timeline(d, with_hook=False)
        beats = scenes.resolve_shots(d, CFG, lines, idx, dur, log=lambda *_: None)[0]["beats"]
        first = [b for b in beats if b["atMs"] == lines[0]["startMs"]]
        self.assertEqual({b["who"] for b in first}, {"lea", "hugo"})
        self.assertEqual(next(b for b in first if b["who"] == "hugo")["pose"], "idle")
        self.assertNotEqual(next(b for b in first if b["who"] == "lea")["pose"], "idle")

    def test_directed_character_is_left_alone(self):
        d = dialogue([dict(WIDE, lines=[1, 6], chars=[{"id": "lea", "pose": "think"}, {"id": "hugo"}])])
        lines, idx, dur = timeline(d, with_hook=False)
        beats = scenes.resolve_shots(d, CFG, lines, idx, dur, log=lambda *_: None)[0]["beats"]
        self.assertEqual([b for b in beats if b["who"] == "lea"], [])

    def test_short_cut_keeps_only_its_scenes(self):
        d = dialogue([dict(WIDE, lines=[1, 2], beats=[{"at": "samedi", "pose": "point"}]),
                      dict(WIDE, lines=[3, 4], beats=[{"at": "bruyant", "pose": "shrug"}]), dict(WIDE, lines=[5, 6])])
        lines, idx, dur = timeline(d, keep={1, 2, 3})
        shots = scenes.resolve_shots(d, CFG, lines, idx, dur, log=lambda *_: None)
        self.assertEqual(len(shots), 2)
        self.assertEqual(shots[-1]["endMs"], dur)
        # Line 4 is cut away, so the beat on its word goes with it.
        self.assertFalse(any(b.get("pose") == "shrug" for b in shots[1]["beats"]))

    def test_long_shot_is_reported(self):
        d = dialogue([dict(WIDE, lines=[1, 6])])
        lines, idx, _ = timeline(d, with_hook=False)
        said = []
        scenes.resolve_shots(d, CFG, lines, idx, 60_000, log=said.append)
        self.assertTrue(any("split the scene" in s for s in said))


class Mouth(unittest.TestCase):
    def test_loud_half_open_and_silent(self):
        rate, fps = 48_000, 60
        tone = lambda amp, ms: [round(amp * math.sin(i * 0.2)) for i in range(rate * ms // 1000)]  # noqa: E731
        mono = tone(0, 500) + tone(20000, 500) + tone(5000, 500) + tone(0, 500)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.wav"
            with wave.open(str(path), "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(array.array("h", [v for s in mono for v in (s, s)]).tobytes())
            track = scenes.mouth_track(path, fps, 2000)
        self.assertEqual(len(track), 120)
        self.assertEqual(set(track[:28]), {"0"})
        self.assertEqual(set(track[36:58]), {"2"})
        self.assertEqual(set(track[68:88]), {"1"})
        self.assertEqual(set(track[100:]), {"0"})

    def test_a_quiet_voice_opens_its_mouth_as_wide_as_a_loud_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "a.wav"
            rate = 48_000
            pcm = array.array("h")
            for amp in (20_000, 0, 3_000):  # a loud line, a pause, a quiet line: one second each
                pcm.extend(int(amp * math.sin(2 * math.pi * 220 * i / rate)) for i in range(rate))
            with wave.open(str(wav), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(pcm.tobytes())
            lines = [{"startMs": 0, "endMs": 1000}, {"startMs": 2000, "endMs": 3000}]
            flat = scenes.mouth_track(wav, 30, 3000)
            fair = scenes.mouth_track(wav, 30, 3000, lines)
            self.assertNotIn("2", flat[62:88])
            self.assertEqual(set(fair[62:88]), {"2"})
            self.assertEqual(set(fair[35:55]), {"0"})


if __name__ == "__main__":
    unittest.main()
