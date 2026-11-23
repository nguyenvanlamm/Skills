"""Measure how well a model writes storyboards, on dialogues it has never seen.

Usage: python3 eval_storyboard.py <dataset folder> --models name1,name2 [--url http://127.0.0.1:11434]
                                  [--limit N] [--out results.json]

Uses the episodes that make_dataset.py holds out: those of <root>/_jsonl/eval.jsonl when it exists,
otherwise the same split rule. For each model: how often the
first answer passes the validator, how often an answer passes after the repair loop, how often that
took dropping the cues the model got wrong (`salvaged`), and what the storyboards look like. Two fixed rows frame the numbers: `auto` is the plain generated storyboard
(the floor), `reference` is the storyboard stored with the dialogue (the ceiling).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from common import load_config, read_json, write_json  # noqa: E402
from make_dataset import in_eval  # noqa: E402
from scenes import auto_scenes, validate_scenes  # noqa: E402
from storyboard import write_scenes  # noqa: E402


def describe(dialogue: dict, scenes: list[dict], cfg: dict) -> dict:
    """What a storyboard is like, in numbers that do not need a render."""
    _, warnings = validate_scenes({**dialogue, "scenes": scenes}, cfg)
    n = len(scenes)
    kinds = [s.get("kind") for s in scenes]
    beats = sum(len(s.get("beats") or []) for s in scenes)
    labels = sum(len(s.get("labels") or []) for s in scenes)
    return {"scenes": n,
            "lines_per_scene": round(len(dialogue["lines"]) / n, 2),
            "closeup_share": round(kinds.count("closeup") / n, 2),
            "walk_share": round(kinds.count("walk") / n, 2),
            "places": len({(s.get("set"), s.get("time")) for s in scenes}),
            "beats_per_scene": round(beats / n, 2),
            "poses": len({b.get("pose") for s in scenes for b in s.get("beats") or [] if b.get("pose")}),
            "emotions": len({x.get("emotion") for s in scenes for x in (s.get("beats") or []) + (s.get("chars") or [])
                             if x.get("emotion")}),
            "label_cover": round(min(1.0, labels / max(1, len(dialogue.get("vocab") or []))), 2),
            "warnings": len(warnings)}


def mean(rows: list[dict]) -> dict:
    keys = rows[0].keys() if rows else []
    return {k: round(sum(r[k] for r in rows) / len(rows), 2) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--models", default="")
    ap.add_argument("--url", default="http://127.0.0.1:11434")
    ap.add_argument("--eval-percent", type=int, default=15)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    cfg = load_config()
    held = args.root.resolve() / "_jsonl" / "eval.jsonl"
    fixed = {json.loads(line)["id"] for line in held.read_text(encoding="utf-8").splitlines()
             if line.strip()} if held.exists() else None
    cases = [(name, read_json(p)) for p in sorted(args.root.resolve().glob("*/*/dialogue.json"))
             for name in [f"{p.parent.parent.name}/{p.parent.name}"]
             if (name in fixed if fixed is not None else in_eval(p.parent.parent.name, args.eval_percent))
             ][:args.limit]
    if not cases:
        print("no held-out episode found")
        return 1
    results: dict = {"cases": [c[0] for c in cases], "rows": {}, "answers": {}, "faults": {}}
    results["rows"]["auto"] = {"n": len(cases), "valid": 1.0, "first_try": 1.0, "tries": 0, "seconds": 0,
                               **mean([describe(d, auto_scenes(d, cfg), cfg) for _, d in cases])}
    results["rows"]["reference"] = {"n": len(cases), "valid": 1.0, "first_try": 1.0, "tries": 0, "seconds": 0,
                                    **mean([describe(d, d["scenes"], cfg) for _, d in cases])}
    for model in [m for m in args.models.split(",") if m]:
        mcfg = {**cfg, "storyboard": {**cfg.get("storyboard", {}), "provider": "ollama", "url": args.url,
                                      "model": model, "retries": args.retries}}
        kept, first, tries, secs, saved, shapes = 0, 0, 0, 0.0, 0, []
        results["answers"][model], results["faults"][model] = {}, {}
        results.setdefault("history", {})[model] = {}
        for name, d in cases:
            bare = {k: v for k, v in d.items() if k != "scenes"}
            stats: dict = {}
            scenes = write_scenes(bare, mcfg, log=lambda s: None, stats=stats)
            tries += stats["tries"]
            secs += stats["seconds"]
            first += bool(stats["first_try"])
            saved += bool(scenes and stats.get("salvaged"))
            results["answers"][model][name] = scenes
            results["faults"][model][name] = stats.get("faults") or []
            results["history"][model][name] = {"tries": stats.get("history"), "salvaged": stats.get("salvaged")}
            if scenes:
                kept += 1
                shapes.append(describe(bare, scenes, cfg))
            note = f", {stats['salvaged']} cue(s) cut" if scenes and stats.get("salvaged") else ""
            print(f"  {model}  {name}: {'ok' if scenes else 'FAILED'} in {stats['tries']} tries, "
                  f"{stats['seconds']}s{note}", flush=True)
        results["rows"][model] = {"n": len(cases), "valid": round(kept / len(cases), 2),
                                  "first_try": round(first / len(cases), 2), "salvaged": round(saved / len(cases), 2),
                                  "tries": round(tries / len(cases), 2),
                                  "seconds": round(secs / len(cases), 1), **mean(shapes)}
    cols = ["valid", "first_try", "salvaged", "tries", "seconds", "scenes", "lines_per_scene", "closeup_share", "walk_share",
            "places", "beats_per_scene", "poses", "emotions", "label_cover", "warnings"]
    print("\n| model | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols))
    for name, row in results["rows"].items():
        print(f"| {name} | " + " | ".join(str(row.get(c, "-")) for c in cols) + " |")
    if args.out:
        write_json(args.out, results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
