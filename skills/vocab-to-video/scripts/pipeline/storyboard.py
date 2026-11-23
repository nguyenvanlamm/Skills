"""Write the storyboard of a dialogue with a language model running on this machine.

The model gets the dialogue and the storyboard rules (prompts/storyboard.md) and answers with
`scenes`. The answer is checked by the same validator as a hand-written storyboard; what the
validator says is sent back to the model until the storyboard passes or the tries run out.
Without a model, or when it never gets there, the pipeline falls back on scenes.auto_scenes.

Usage: uv run python storyboard.py <episodes/NAME/LEVEL>      (writes `scenes` into dialogue.json)
Config: config.json -> "storyboard": {"provider": "ollama", "model": "<name>", ...}
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import PIPELINE, load_config, read_json, write_json
from scenes import RIG, default_cast, pick_hit, validate_scenes

PROMPT = PIPELINE / "prompts" / "storyboard.md"
SIDES = ("left", "right")


def schema(cast_ids: list[str], n_lines: int) -> dict:
    """The shape of the answer. Every name comes from the lists the video code draws from, so
    the model cannot invent a pose, a set or a character."""
    def text(**kw) -> dict:
        return {"type": "string", **kw}

    poses = sorted(p for p in RIG["poses"] if p != "tiphat")
    emotions = sorted(RIG["emotions"])
    char = {"type": "object", "required": ["id"], "properties": {
        "id": text(enum=cast_ids), "pose": text(enum=poses), "emotion": text(enum=emotions),
        "enter": text(enum=list(SIDES)), "exit": text(enum=list(SIDES))}}
    beat = {"type": "object", "required": ["at", "who"], "properties": {
        "at": text(), "who": text(enum=cast_ids), "pose": text(enum=poses), "emotion": text(enum=emotions)}}
    label = {"type": "object", "required": ["at", "text"], "properties": {"at": text(), "text": text()}}
    scene = {"type": "object", "required": ["kind", "lines", "set", "time", "chars"], "properties": {
        "kind": text(enum=[k for k in RIG["kinds"] if k != "dialogue"]),
        "lines": {"type": "array", "minItems": 2, "maxItems": 2,
                  "items": {"type": "integer", "minimum": 1, "maximum": n_lines}},
        "set": text(enum=list(RIG["sets"])), "time": text(enum=list(RIG["times"])),
        "shop": text(), "tag": text(),
        "chars": {"type": "array", "minItems": 1, "items": char},
        "beats": {"type": "array", "items": beat},
        "labels": {"type": "array", "maxItems": 1, "items": label}}}
    return {"type": "object", "required": ["scenes"],
            "properties": {"scenes": {"type": "array", "minItems": 1, "items": scene}}}


def brief(dialogue: dict, cfg: dict) -> str:
    """What the model is told about one dialogue: who stands where, the new words, the lines."""
    cast = default_cast(cfg, dialogue)
    who = [f"{cid} (stands on the {cfg['speakers'][cid].get('side', 'left')})" if cid in cfg["speakers"]
           else f"{cid} (extra, does not speak)" for cid in cast]
    hook, short = dialogue.get("hook") or {}, dialogue.get("short") or {}
    rows = [f"Level: {dialogue.get('level')}", f"Title: {dialogue.get('title')}",
            "Characters: " + ", ".join(who),
            "New words: " + ", ".join(v["word"] for v in dialogue.get("vocab") or []),
            f"Hook, spoken over the first scene by {hook.get('speaker')}: {hook.get('text')}",
            f"Short cut: lines {short.get('from')}-{short.get('to')}", "", "Lines:"]
    rows += [f"{n}. {l['speaker']}: {l['text']}" for n, l in enumerate(dialogue["lines"], 1)]
    return "\n".join(rows)


def tidy(answer) -> list[dict] | None:
    """The scenes of an answer, without the empty fields a model fills in to satisfy a schema."""
    scenes = answer.get("scenes") if isinstance(answer, dict) else answer
    if not isinstance(scenes, list):
        return None

    def strip(v):
        if isinstance(v, dict):
            return {k: strip(x) for k, x in v.items() if x not in (None, "", [], {})}
        return [strip(x) for x in v] if isinstance(v, list) else v
    return [strip(s) for s in scenes]


def ollama_chat(sb: dict, messages: list[dict], fmt: dict) -> str:
    """One answer from Ollama's /api/chat, constrained to the schema."""
    body = {"model": sb["model"], "messages": messages, "format": fmt, "stream": False, "think": False,
            "keep_alive": sb.get("keep_alive", "10m"),
            "options": {"temperature": sb.get("temperature", 0.4), "num_ctx": sb.get("num_ctx", 8192)}}
    req = urllib.request.Request(sb.get("url", "http://127.0.0.1:11434").rstrip("/") + "/api/chat",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=sb.get("timeout_s", 300)) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"the model server answered {e.code}: {e.read().decode(errors='replace')[:300]}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RuntimeError(f"no answer from the model server at {sb.get('url')}: {e}")
    return (data.get("message") or {}).get("content") or ""


PROVIDERS = {"ollama": ollama_chat}


def problems_of(dialogue: dict, scenes: list[dict], cfg: dict) -> tuple[list[str], list[str]]:
    return validate_scenes({**dialogue, "scenes": scenes}, cfg)


def feedback(problems: list[str]) -> str:
    """What the model is told after a check that found problems (training uses the same words)."""
    return ("The storyboard was checked. Fix every point and answer with the whole corrected JSON object again:\n"
            + "\n".join(f"- {p}" for p in problems))


def _says(lines: list[dict], sc: dict, at, who=None) -> bool | None:
    """Whether the scene's lines say the cue word; None when the cue is not a word (a fraction,
    '+seconds') or the scene has no usable line range."""
    rng = sc.get("lines")
    if not (isinstance(at, str) and at.strip() and not at.startswith("+")
            and isinstance(rng, list) and len(rng) == 2 and all(type(v) is int for v in rng)):
        return None
    return pick_hit(at, lines[rng[0] - 1:rng[1]], who)[0] is not None


def salvage(dialogue: dict, scenes: list[dict]) -> tuple[list[dict], int]:
    """The storyboard without the cues it gets wrong: a beat whose word is not said in its scene,
    or that names someone not in the picture, is dropped; such a label moves to the first scene
    that says its word and has no label yet, or is dropped. Returns the scenes and how many cues
    were moved or dropped. Used when the tries run out, so one wrong word does not cost the
    whole storyboard."""
    lines = [l if isinstance(l, dict) else {} for l in dialogue["lines"]]
    out = [dict(sc) for sc in scenes if isinstance(sc, dict)]
    changed, homeless = 0, []
    for sc in out:
        ids = {c.get("id") for c in sc.get("chars") or [] if isinstance(c, dict)}
        beats = [b for b in sc.get("beats") or [] if isinstance(b, dict)]
        keep = [b for b in beats if _says(lines, sc, b.get("at"), b.get("who")) is not False
                and b.get("who") in (None, *ids)]
        labels = [x for x in sc.get("labels") or [] if isinstance(x, dict)]
        stay = [x for x in labels if _says(lines, sc, x.get("at")) is not False]
        homeless += [x for x in labels if x not in stay]
        changed += len(beats) - len(keep)
        for key, kept in (("beats", keep), ("labels", stay)):
            if kept:
                sc[key] = kept
            else:
                sc.pop(key, None)
    for label in homeless:
        changed += 1
        home = next((sc for sc in out if not sc.get("labels") and _says(lines, sc, label.get("at"))), None)
        if home is not None:
            home["labels"] = [label]
    return out, changed


def write_scenes(dialogue: dict, cfg: dict, log=print, chat=None, stats: dict | None = None) -> list[dict] | None:
    """A storyboard for the dialogue, or None when no model is set up or none of its tries
    passes the validator. `stats`, when given, receives how the tries went."""
    sb = cfg.get("storyboard") or {}
    chat = chat or PROVIDERS.get(sb.get("provider"))
    stats = stats if stats is not None else {}
    stats.update(tries=0, first_try=False, errors=None, warnings=None, seconds=0.0, salvaged=0, history=[])
    if not chat or not sb.get("model"):
        return None
    fmt = schema(sorted(default_cast(cfg, dialogue)), len(dialogue["lines"]))
    messages = [{"role": "system", "content": PROMPT.read_text(encoding="utf-8")},
                {"role": "user", "content": brief(dialogue, cfg)}]
    best: tuple[int, list[dict]] | None = None
    closest: tuple[int, list[dict]] | None = None  # the answer with the fewest errors
    began = time.time()
    for attempt in range(1, int(sb.get("retries", 3)) + 2):
        stats["tries"] = attempt
        try:
            raw = chat(sb, messages, fmt)
        except RuntimeError as e:
            log(f"  WARN storyboard model: {e}")
            break
        try:
            scenes = tidy(json.loads(raw))
        except ValueError:
            scenes = None
        if scenes is None:
            errors, warnings = ["the answer was not a JSON object {\"scenes\": [...]}"], []
        else:
            errors, warnings = problems_of(dialogue, scenes, cfg)
        stats["faults"] = (errors + warnings)[:12]
        stats["history"].append([len(errors), len(warnings)])
        if scenes is not None and errors and (closest is None or len(errors) < closest[0]):
            closest = (len(errors), scenes)
        if scenes is not None and not errors and (best is None or len(warnings) < best[0]):
            best = (len(warnings), scenes)
            stats.update(errors=0, warnings=len(warnings))
        if not errors and not warnings:
            stats["first_try"] = attempt == 1
            break
        if best is None:
            stats.update(errors=len(errors), warnings=len(warnings))
        log(f"  storyboard try {attempt}: {len(errors)} error(s), {len(warnings)} warning(s)")
        if len(messages) > 2 and raw.strip() == messages[2]["content"].strip():
            log("  the model gave the same answer again; no more tries")
            break
        # Only the last answer and its faults go back: the talk stays short enough for a small model.
        messages = messages[:2] + [{"role": "assistant", "content": raw},
                                   {"role": "user", "content": feedback(errors + warnings)}]
    if best is None and closest is not None:
        trimmed, changed = salvage(dialogue, closest[1])
        errors, warnings = problems_of(dialogue, trimmed, cfg)
        if not errors:
            log(f"  WARN storyboard: {changed} cue(s) were not said in their scene; the model's storyboard "
                "is kept with those beats dropped and those labels moved or dropped")
            best = (len(warnings), trimmed)
            stats.update(errors=0, warnings=len(warnings), salvaged=changed)
    stats["seconds"] = round(time.time() - began, 1)
    if best is None:
        log("  WARN the model wrote no valid storyboard; a plain one is generated instead")
        return None
    return best[1]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = Path(sys.argv[1]).resolve()
    dialogue, cfg = read_json(d / "dialogue.json"), load_config()
    if (cfg.get("storyboard") or {}).get("provider", "none") == "none":
        print("FAIL no storyboard model is set up: see references/local-model.md")
        return 1
    stats: dict = {}
    scenes = write_scenes(dialogue, cfg, stats=stats)
    if not scenes:
        print("RESULT: FAIL")
        return 1
    write_json(d / "dialogue.json", {**dialogue, "scenes": scenes})
    print(f"RESULT: PASS {len(scenes)} scenes in {stats['tries']} tries, {stats['seconds']}s, "
          f"{stats['warnings']} warning(s) left, {stats['salvaged']} cue(s) dropped or moved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
