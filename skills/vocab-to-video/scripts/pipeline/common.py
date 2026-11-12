"""Shared helpers: paths, config, tokenising French text, vocabulary matching."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "pipeline"
ASSETS = ROOT / "assets"
VIDEO = ROOT / "video"
LEVELS = ("A2", "B1")

# Punctuation French typography sets apart with a space; it is glued back to the previous word.
LONE_PUNCT = re.compile(r"^[?!:;»…”\")\]]+$")
ELISION = re.compile(r"^(?:l|d|j|s|n|m|t|c|qu|jusqu|lorsqu|puisqu)['’]", re.I)


def load_config() -> dict:
    return json.loads((PIPELINE / "config.json").read_text(encoding="utf-8"))


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tokens(text: str) -> list[str]:
    """Display tokens: whitespace-separated words, lone punctuation glued to the word before."""
    out: list[str] = []
    for raw in text.split():
        if out and LONE_PUNCT.match(raw):
            out[-1] += " " + raw
        elif out and out[-1] in ("«", "“", "("):
            out[-1] += " " + raw
        else:
            out.append(raw)
    return out


def norm(word: str) -> str:
    """Lowercase, typographic apostrophes unified, everything but letters/digits/'/- dropped."""
    w = unicodedata.normalize("NFC", word).lower().replace("’", "'")
    w = re.sub(r"[^0-9a-zà-öø-ÿœæ'\-]", "", w)
    return w.strip("'-")


def letters(word: str) -> str:
    """Only letters and digits, for matching TTS word boundaries against script tokens."""
    return re.sub(r"[^0-9a-zà-öø-ÿœæ]", "", unicodedata.normalize("NFC", word).lower())


def word_variants(token: str) -> set[str]:
    """A token as written and with its elided prefix removed: "l'école" -> {"l'école", "école"}."""
    n = norm(token)
    return {n, ELISION.sub("", n)} - {""}


def vocab_hits(toks: list[str], vocab: list[dict]) -> tuple[list[bool], dict[str, int]]:
    """Mark which tokens belong to a vocabulary form; count hits per vocabulary word."""
    marks = [False] * len(toks)
    counts = {v["word"]: 0 for v in vocab}
    variants = [word_variants(t) for t in toks]
    for v in vocab:
        for form in sorted(set(v.get("forms") or [v["word"]]), key=len, reverse=True):
            parts = [norm(p) for p in form.split()]
            parts = [p for p in parts if p]
            if not parts:
                continue
            for i in range(len(toks) - len(parts) + 1):
                if all(p in variants[i + k] or ELISION.sub("", p) in variants[i + k]
                       for k, p in enumerate(parts)):
                    counts[v["word"]] += 1
                    for k in range(len(parts)):
                        marks[i + k] = True
    return marks, counts
