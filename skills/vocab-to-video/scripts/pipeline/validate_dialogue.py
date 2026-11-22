"""Check a dialogue.json before any audio is made.

Usage: uv run python validate_dialogue.py <episode>/<LEVEL>/dialogue.json
Exit code 0 = pass (warnings allowed), 1 = errors.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from common import LEVELS, letters, load_config, read_json, tokens, vocab_hits
from scenes import validate_scenes

ALLOWED = re.compile(r"^[0-9A-Za-zÀ-ÖØ-öø-ÿŒœÆæ\s'’\-.,;:!?«»…()€%]+$")


def validate(dialogue: dict, cfg: dict) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    level = dialogue.get("level")
    if level not in LEVELS:
        return [f"level must be one of {LEVELS}, got {level!r}"], [], {}
    rules = cfg["levels"][level]
    lines = dialogue.get("lines") or []
    vocab = dialogue.get("vocab") or []
    title = dialogue.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("title is missing")
    elif len(title) > 44:
        warnings.append(f"title is {len(title)} characters; over about 40 it crowds the top of the video")
    if not isinstance(vocab, list) or not vocab:
        return errors + ["vocab is empty: it must be a list of {\"word\": ..., \"forms\": [...]}"], warnings, {}
    for n, v in enumerate(vocab, 1):
        if not (isinstance(v, dict) and isinstance(v.get("word"), str) and v["word"].strip()
                and isinstance(v.get("forms") or [], list) and all(isinstance(f, str) for f in v.get("forms") or [])):
            return errors + [f"vocab entry {n} must be {{\"word\": \"...\", \"forms\": [\"...\"]}}"], warnings, {}
    if not isinstance(lines, list) or not lines:
        return errors + ["lines is empty"], warnings, {}
    for i, line in enumerate(lines, 1):
        if not (isinstance(line, dict) and isinstance(line.get("text") or "", str)):
            return errors + [f"line {i} must be {{\"speaker\": \"...\", \"text\": \"...\"}}"], warnings, {}
    if not isinstance(dialogue.get("hook") or {}, dict) or not isinstance(dialogue.get("short") or {}, dict):
        return errors + ["hook and short must be objects"], warnings, {}

    known = set(cfg["speakers"])
    total_words = 0
    all_counts = {v["word"]: 0 for v in vocab}
    for i, line in enumerate(lines, 1):
        speaker, text = line.get("speaker"), (line.get("text") or "").strip()
        if speaker not in known:
            errors.append(f"line {i}: unknown speaker {speaker!r} (use {sorted(known)})")
        if not text:
            errors.append(f"line {i}: empty text")
            continue
        if not ALLOWED.match(text):
            bad = sorted({c for c in text if not ALLOWED.match(c)})
            errors.append(f"line {i}: characters not allowed {bad}")
        if i > 1 and speaker == lines[i - 2].get("speaker"):
            errors.append(f"line {i}: same speaker as line {i - 1}; speakers must alternate")
        if not letters(text):
            errors.append(f"line {i}: no words, only punctuation")
        if re.search(r"\d", re.sub(r"\b(?:A[12]|B[12]|C[12])\b", "", text)):
            warnings.append(f"line {i}: digits are read unpredictably by the voice; write the number as words")
        if re.search(r"[()]", text):
            warnings.append(f"line {i}: brackets are spoken as a pause at best; no asides or stage directions")
        toks = tokens(text)
        total_words += len(toks)
        if len(toks) > rules["max_words_per_line"]:
            errors.append(f"line {i}: {len(toks)} words, limit is {rules['max_words_per_line']}")
        _, counts = vocab_hits(toks, vocab)
        fresh = [word for word, n in counts.items() if n and not all_counts[word]]
        if len(fresh) > 2:
            warnings.append(f"line {i}: {len(fresh)} new words at once {fresh}; at most two per turn, "
                            "or the learner cannot tell them apart")
        for word, n in counts.items():
            all_counts[word] += n

    hook = dialogue.get("hook") or {}
    hook_text = hook.get("text").strip() if isinstance(hook.get("text"), str) else ""
    if not hook_text:
        errors.append("hook is missing: one short spoken line that opens the video")
    else:
        n_hook = len(tokens(hook_text))
        if hook.get("speaker") not in known:
            errors.append(f"hook: unknown speaker {hook.get('speaker')!r}")
        if not ALLOWED.match(hook_text):
            errors.append("hook: characters not allowed")
        if n_hook > cfg["hook"]["max_words"]:
            errors.append(f"hook: {n_hook} words, limit is {cfg['hook']['max_words']} (about 3 seconds)")
        if not hook_text.endswith(("?", "!")):
            errors.append("hook must end with ? or !")

    short = dialogue.get("short") or {}
    a, b = short.get("from"), short.get("to")
    if not (isinstance(a, int) and isinstance(b, int) and 1 <= a < b <= len(lines)):
        errors.append(f"short must be {{\"from\": n, \"to\": m}} with 1 <= n < m <= {len(lines)}")
    else:
        _, in_cut = vocab_hits([t for l in lines[a - 1:b] for t in tokens(l.get("text") or "")], vocab)
        used = [w for w, n in in_cut.items() if n]
        if len(used) < 2:
            errors.append(f"short (lines {a}-{b}) uses {len(used)} vocabulary word(s); it needs at least 2")

    for word, n in all_counts.items():
        if n == 0:
            errors.append(f"vocabulary word never used: {word!r} (check its 'forms')")
        elif n == 1:
            warnings.append(f"vocabulary word used only once: {word!r}")
    lo, hi = rules["words"]
    if not lo <= total_words <= hi:
        errors.append(f"{total_words} words; {level} needs {lo}-{hi} for a 2-3 minute video")
    lo, hi = rules["turns"]
    if not lo <= len(lines) <= hi:
        warnings.append(f"{len(lines)} turns; {level} usually has {lo}-{hi}")
    scene_errors, scene_warnings = validate_scenes(dialogue, cfg)
    errors += scene_errors
    warnings += scene_warnings
    return errors, warnings, {"words": total_words, "turns": len(lines), "vocab_uses": all_counts}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    errors, warnings, stats = validate(read_json(Path(sys.argv[1])), load_config())
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"FAIL  {e}")
    if stats:
        print(f"words={stats['words']} turns={stats['turns']} vocab_uses={stats['vocab_uses']}")
    print("RESULT: FAIL" if errors else "RESULT: PASS")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
