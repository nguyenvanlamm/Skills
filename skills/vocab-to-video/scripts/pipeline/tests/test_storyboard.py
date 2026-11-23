"""storyboard.py against a fake model. Run from scripts/pipeline:
uv run python -m unittest discover -s tests -v
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import storyboard  # noqa: E402
from common import load_config  # noqa: E402

CFG = {**load_config(), "storyboard": {"provider": "ollama", "model": "fake", "retries": 2}}
TEXTS = ["Salut Hugo ! Ça va ?", "Je vais déménager samedi.", "Ah bon ? Pourquoi ?", "Mon voisin est bruyant."]
DIALOGUE = {"level": "A2", "title": "Hugo déménage", "vocab": [{"word": "déménager"}, {"word": "le voisin"}],
            "hook": {"speaker": "lea", "text": "Tu comprends ?"}, "short": {"from": 1, "to": 2},
            "lines": [{"speaker": "lea" if i % 2 == 0 else "hugo", "text": t} for i, t in enumerate(TEXTS)]}
BOTH = [{"id": "lea"}, {"id": "hugo"}]
GOOD = {"scenes": [
    {"kind": "wide", "lines": [1, 2], "set": "street", "time": "day", "shop": "", "chars": BOTH,
     "beats": [{"at": "Salut", "who": "lea", "pose": "wave"}], "labels": [{"at": "déménager", "text": "déménager"}]},
    {"kind": "closeup", "lines": [3, 3], "set": "street", "time": "day", "chars": [{"id": "lea", "emotion": "shocked"}]},
    {"kind": "wide", "lines": [4, 4], "set": "street", "time": "day", "chars": BOTH, "beats": [], "labels": []}]}
GAP = {"scenes": GOOD["scenes"][:2]}                       # line 4 is not covered
BAD_CUE = {"scenes": [{**GOOD["scenes"][0], "beats": [{"at": "bruyant", "who": "lea", "pose": "wave"}]},
                      *GOOD["scenes"][1:]]}                # "bruyant" is said in scene 3


class Model:
    def __init__(self, *answers):
        self.answers, self.seen = list(answers), []

    def __call__(self, sb, messages, fmt):
        self.seen.append([dict(m) for m in messages])
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a if isinstance(a, str) else json.dumps(a)


def run(model, cfg=CFG):
    stats, said = {}, []
    return storyboard.write_scenes(DIALOGUE, cfg, log=said.append, chat=model, stats=stats), stats, said


class WriteScenes(unittest.TestCase):
    def test_a_good_answer_is_taken_at_once_and_tidied(self):
        model = Model(GOOD)
        scenes, stats, _ = run(model)
        self.assertEqual((stats["tries"], stats["first_try"], stats["errors"], stats["warnings"]), (1, True, 0, 0))
        self.assertNotIn("shop", scenes[0])        # empty fields are dropped
        self.assertNotIn("beats", scenes[2])
        system, user = model.seen[0]
        self.assertIn("storyboard", system["content"])
        self.assertIn("2. hugo: Je vais déménager samedi.", user["content"])
        self.assertIn("New words: déménager, le voisin", user["content"])
        self.assertIn("lea (stands on the left)", user["content"])

    def test_the_validator_s_words_go_back_to_the_model(self):
        model = Model(GAP, BAD_CUE, GOOD)
        scenes, stats, _ = run(model)
        self.assertEqual(len(scenes), 3)
        self.assertEqual((stats["tries"], stats["first_try"]), (3, False))
        self.assertIn("scenes stop at line 3", model.seen[1][-1]["content"])
        self.assertIn("'bruyant' is not said in this scene's lines", model.seen[2][-1]["content"])
        self.assertEqual(model.seen[1][-2]["role"], "assistant")

    def test_no_valid_answer_gives_none_so_the_plain_storyboard_is_used(self):
        scenes, stats, said = run(Model(GAP, "not json", GAP))
        self.assertIsNone(scenes)
        self.assertEqual(stats["tries"], 3)
        self.assertTrue(any("plain one is generated" in s for s in said))

    def test_a_valid_answer_with_warnings_is_kept_if_nothing_better_comes(self):
        four = {"scenes": [{"kind": "wide", "lines": [1, 4], "set": "home", "time": "day", "chars": BOTH}]}
        scenes, stats, _ = run(Model(four, GAP, GAP))
        self.assertEqual(len(scenes), 1)
        self.assertEqual((stats["errors"], stats["warnings"]), (0, 1))

    def test_a_wrong_cue_word_costs_the_cue_not_the_storyboard(self):
        scenes, stats, said = run(Model(BAD_CUE, BAD_CUE, BAD_CUE))
        self.assertEqual(len(scenes), 3)
        self.assertNotIn("beats", scenes[0])
        self.assertEqual(scenes[0]["labels"], [{"at": "déménager", "text": "déménager"}])
        self.assertEqual((stats["errors"], stats["salvaged"], stats["history"]), (0, 1, [[1, 0]] * 2))
        self.assertTrue(any("same answer again" in s for s in said))   # the third try is not asked for
        self.assertTrue(any("1 cue(s) were not said" in s for s in said))

    def test_a_label_in_the_wrong_scene_moves_to_the_first_that_says_it(self):
        wrong = [GOOD["scenes"][0], {**GOOD["scenes"][1], "labels": [{"at": "voisin", "text": "le voisin"}]},
                 GOOD["scenes"][2]]
        scenes, changed = storyboard.salvage(DIALOGUE, wrong)
        self.assertEqual(changed, 1)
        self.assertNotIn("labels", scenes[1])
        self.assertEqual(scenes[2]["labels"], [{"at": "voisin", "text": "le voisin"}])
        self.assertEqual(storyboard.problems_of(DIALOGUE, scenes, CFG)[0], [])
        self.assertIn("labels", wrong[1])          # the answer itself is left as it was

    def test_a_dead_server_is_a_warning_not_a_crash(self):
        scenes, _, said = run(Model(RuntimeError("no answer from the model server")))
        self.assertIsNone(scenes)
        self.assertTrue(any("no answer" in s for s in said))

    def test_without_a_model_nothing_is_called(self):
        model = Model()
        for sb in ({"provider": "none"}, {"provider": "ollama", "model": ""}, None):
            cfg = {**CFG, "storyboard": sb}
            self.assertIsNone(storyboard.write_scenes(DIALOGUE, cfg, log=lambda s: None,
                                                      chat=model if sb and sb.get("provider") == "ollama" else None))
        self.assertEqual(model.seen, [])

    def test_the_shipped_config_calls_no_model(self):
        self.assertEqual(load_config()["storyboard"]["provider"], "none")


class Schema(unittest.TestCase):
    def test_names_come_from_the_rig(self):
        s = storyboard.schema(["hugo", "lea"], 4)
        scene = s["properties"]["scenes"]["items"]["properties"]
        self.assertEqual(scene["kind"]["enum"], ["wide", "closeup", "walk"])
        self.assertEqual(scene["chars"]["items"]["properties"]["id"]["enum"], ["hugo", "lea"])
        self.assertNotIn("tiphat", scene["chars"]["items"]["properties"]["pose"]["enum"])
        self.assertEqual(scene["lines"]["items"]["maximum"], 4)


if __name__ == "__main__":
    unittest.main()
