"""Turn a folder of checked episodes into training data for the storyboard model.

Usage: python3 make_dataset.py <dataset folder> [--out <folder>] [--eval-percent 15]

The dataset folder holds <episode>/<LEVEL>/dialogue.json files that contain `scenes`. An episode
is kept only if the dialogue validator finds no error and no storyboard warning. Each kept level
becomes one chat example: the storyboard rules, the dialogue as the model is shown it at run
time, and the scenes as the answer. Whole episodes go to train.jsonl or eval.jsonl, never one
level to each, so the evaluation never sees a theme the model was trained on. When eval.jsonl
already exists its episodes stay the evaluation set and every other episode goes to training,
so results stay comparable as the dataset grows; `--resplit` draws the evaluation set again.

`--repairs` (percent, default 30) adds repair lessons to training: the same dialogue, a storyboard
with one to three of the mistakes models make (a misspelt or misplaced cue, a label in the wrong
scene, a cue said twice, an uncovered line, a beat for someone absent, an overlong scene), the
checker's words about it, and the right storyboard as the answer. They teach the model to use
the repair loop of storyboard.py, which sends back exactly those words.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from common import load_config, read_json  # noqa: E402
from scenes import find_all, pick_hit, validate_scenes  # noqa: E402
from storyboard import PROMPT, brief, feedback, tidy  # noqa: E402
from validate_dialogue import validate  # noqa: E402


def example(dialogue: dict, cfg: dict, name: str) -> dict:
    bare = {k: v for k, v in dialogue.items() if k != "scenes"}
    answer = json.dumps({"scenes": tidy(dialogue["scenes"])}, ensure_ascii=False)
    return {"id": name, "messages": [
        {"role": "system", "content": PROMPT.read_text(encoding="utf-8")},
        {"role": "user", "content": brief(bare, cfg)},
        {"role": "assistant", "content": answer}]}


WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")
VOWELS = "aeiouéèêà"


def _texts(dialogue: dict, sc: dict) -> list[dict]:
    a, b = sc["lines"]
    return dialogue["lines"][a - 1:b]


def _cues(scenes: list[dict], kinds=("beats", "labels")) -> list[tuple[int, str, dict]]:
    return [(i, kind, item) for i, sc in enumerate(scenes) for kind in kinds for item in sc.get(kind) or []
            if isinstance(item.get("at"), str) and not item["at"].startswith("+")]


def _not_said(word: str, dialogue: dict, sc: dict) -> bool:
    return not find_all(word, [l["text"] for l in _texts(dialogue, sc)])


def _misspell(dialogue, scenes, rng) -> bool:
    """A cue word with one letter wrong, as a model writes it when it loses track of the text."""
    cues = _cues(scenes)
    rng.shuffle(cues)
    for i, _, item in cues:
        words = [w for w in WORD.findall(item["at"]) if len(w) >= 4]
        if not words:
            continue
        w = max(words, key=len)
        k = rng.randrange(1, len(w) - 1)
        op = rng.choice(("drop", "swap", "vowel"))
        if op == "drop":
            bad = w[:k] + w[k + 1:]
        elif op == "swap":
            bad = w[:k] + w[k + 1] + w[k] + w[k + 2:]
        else:
            bad = w[:k] + rng.choice([v for v in VOWELS if v != w[k]]) + w[k + 1:]
        at = item["at"].replace(w, bad, 1)
        if at != item["at"] and _not_said(at, dialogue, scenes[i]):
            item["at"] = at
            return True
    return False


def _foreign_word(dialogue, scenes, rng) -> bool:
    """A beat on a word that is said in another scene."""
    cues = _cues(scenes, ("beats",))
    rng.shuffle(cues)
    for i, _, item in cues:
        others = [w for j, sc in enumerate(scenes) if j != i for l in _texts(dialogue, sc)
                  for w in WORD.findall(l["text"]) if len(w) >= 4]
        rng.shuffle(others)
        for w in others[:20]:
            if _not_said(w, dialogue, scenes[i]):
                item["at"] = w
                return True
    return False


def _label_elsewhere(dialogue, scenes, rng) -> bool:
    """A label put in a scene next to the one where its word is first said."""
    order = [i for i, sc in enumerate(scenes) if sc.get("labels")]
    rng.shuffle(order)
    for i in order:
        label = scenes[i]["labels"][0]
        for j in sorted({i - 2, i - 1, i + 1, i + 2}, key=lambda j: abs(j - i)):
            if 0 <= j < len(scenes) and not scenes[j].get("labels") and isinstance(label.get("at"), str) \
                    and _not_said(label["at"], dialogue, scenes[j]):
                scenes[j]["labels"] = [label]
                scenes[i].pop("labels")
                return True
    return False


def _ambiguous(dialogue, scenes, rng) -> bool:
    """A beat on a word the scene says twice, so the cue does not pick one."""
    cues = _cues(scenes, ("beats",))
    rng.shuffle(cues)
    for i, _, item in cues:
        lines = _texts(dialogue, scenes[i])
        words = sorted({w for l in lines for w in WORD.findall(l["text"]) if len(w) >= 3})
        rng.shuffle(words)
        for w in words:
            if pick_hit(w, lines, item.get("who"))[1] >= 2:
                item["at"] = w
                return True
    return False


def _gap(dialogue, scenes, rng) -> bool:
    """A scene that starts one line late, so a line is not covered."""
    order = [i for i, sc in enumerate(scenes) if sc["lines"][0] < sc["lines"][1]]
    if not order:
        return False
    sc = scenes[rng.choice(order)]
    sc["lines"] = [sc["lines"][0] + 1, sc["lines"][1]]
    return True


def _absent(dialogue, scenes, rng) -> bool:
    """A beat for the character who is not in the picture."""
    cast = sorted({c["id"] for sc in scenes for c in sc["chars"]})
    order = [i for i, sc in enumerate(scenes) if len(sc["chars"]) == 1 and sc.get("beats")]
    if len(cast) < 2 or not order:
        return False
    sc = scenes[rng.choice(order)]
    there = sc["chars"][0]["id"]
    sc["beats"][0]["who"] = next(c for c in cast if c != there)
    return True


def _long(dialogue, scenes, rng) -> bool:
    """Two scenes with the same characters run together into one long shot."""
    order = [i for i in range(len(scenes) - 1)
             if [c["id"] for c in scenes[i]["chars"]] == [c["id"] for c in scenes[i + 1]["chars"]]
             and scenes[i + 1]["lines"][1] - scenes[i]["lines"][0] >= 3]
    if not order:
        return False
    i = rng.choice(order)
    a, b = scenes[i], scenes.pop(i + 1)
    a["lines"] = [a["lines"][0], b["lines"][1]]
    for key in ("beats", "labels"):
        if a.get(key) or b.get(key):
            a[key] = (a.get(key) or []) + (b.get(key) or [])
    return True


BREAKS = [(_misspell, 3), (_foreign_word, 2), (_label_elsewhere, 2), (_ambiguous, 3), (_gap, 1), (_absent, 1),
          (_long, 1)]


def repair_example(dialogue: dict, cfg: dict, name: str, rng: random.Random) -> dict | None:
    """A lesson in using the checker's words: the storyboard with one to three of the mistakes a
    model makes, what the checker says about it (worded as at run time), and the storyboard as it
    should be. None when no mistake could be made."""
    good = example(dialogue, cfg, name)
    scenes = copy.deepcopy(tidy(dialogue["scenes"]))
    want = rng.choices((1, 2, 3), weights=(6, 3, 1))[0]
    done = 0
    for _ in range(12):
        if done == want:
            break
        fn = rng.choices([f for f, _ in BREAKS], weights=[w for _, w in BREAKS])[0]
        done += fn(dialogue, scenes, rng)
    errors, warnings = validate_scenes({**dialogue, "scenes": scenes}, cfg)
    if not done or not errors + warnings:
        return None
    system, user, answer = good["messages"]
    wrong = json.dumps({"scenes": tidy(scenes)}, ensure_ascii=False)
    return {"id": f"{name}#fix", "messages": [system, user, {"role": "assistant", "content": wrong},
                                              {"role": "user", "content": feedback(errors + warnings)}, answer]}


def in_eval(episode: str, percent: int) -> bool:
    return int(hashlib.sha256(episode.encode()).hexdigest(), 16) % 100 < percent


def collect(root: Path, cfg: dict, percent: int, fixed: set[str] | None = None, repairs: int = 0,
            ) -> tuple[list[dict], list[dict], list[str]]:
    """`fixed`, when given, names the episodes of the evaluation set instead of the draw.
    `repairs`: the share (percent) of training levels that also give a repair lesson."""
    train, held, dropped = [], [], []
    for path in sorted(root.glob("*/*/dialogue.json")):
        name = f"{path.parent.parent.name}/{path.parent.name}"
        try:
            dialogue = read_json(path)
            errors, _, _ = validate(dialogue, cfg)
            scene_errors, scene_warnings = validate_scenes(dialogue, cfg)
        except (ValueError, OSError) as e:
            errors, scene_errors, scene_warnings, dialogue = [str(e)], [], [], {}
        if errors or scene_errors or scene_warnings or not dialogue.get("scenes"):
            why = (errors + scene_errors + scene_warnings or ["no scenes"])[0]
            dropped.append(f"{name}: {why}")
            continue
        episode = path.parent.parent.name
        is_held = episode in fixed if fixed is not None else in_eval(episode, percent)
        (held if is_held else train).append(example(dialogue, cfg, name))
        rng = random.Random(name)
        if not is_held and rng.random() * 100 < repairs:
            lesson = repair_example(dialogue, cfg, name, rng)
            if lesson:
                train.append(lesson)
    return train, held, dropped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--eval-percent", type=int, default=15)
    ap.add_argument("--resplit", action="store_true")
    ap.add_argument("--repairs", type=int, default=30,
                    help="percent of training levels that also give a repair lesson (0 for none)")
    args = ap.parse_args()
    out = args.out or args.root / "_jsonl"
    out.mkdir(parents=True, exist_ok=True)
    fixed = None
    if (out / "eval.jsonl").exists() and not args.resplit:
        fixed = {json.loads(line)["id"].split("/")[0]
                 for line in (out / "eval.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    train, held, dropped = collect(args.root.resolve(), load_config(), args.eval_percent, fixed, args.repairs)
    for name, rows in (("train", train), ("eval", held)):
        (out / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                           encoding="utf-8")
    for d in dropped:
        print(f"DROP  {d}")
    lessons = sum(r["id"].endswith("#fix") for r in train)
    print(f"train: {len(train)} ({lessons} repair lessons)  eval: {len(held)}  dropped: {len(dropped)}  -> {out}")
    return 0 if train and held else 1


if __name__ == "__main__":
    sys.exit(main())
