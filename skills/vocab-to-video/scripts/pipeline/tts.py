"""Text to speech, one audio file per dialogue line, with word timings.

Providers are swappable: a provider turns (text, voice, rate) into an MP3 plus a list of
word boundaries {text, start_ms, end_ms}. Only Edge TTS is implemented.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import time
from pathlib import Path

from common import letters, read_json, tokens, write_json


class EdgeProvider:
    name = "edge"

    async def _synth(self, text: str, voice: str, rate: str, out: Path) -> list[dict]:
        import edge_tts

        com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        bounds: list[dict] = []
        with open(out, "wb") as f:
            async for chunk in com.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 10_000  # 100 ns units -> ms
                    bounds.append({"text": chunk["text"], "start_ms": start,
                                   "end_ms": start + chunk["duration"] / 10_000})
        return bounds

    def synth(self, text: str, voice: str, rate: str, out: Path, retries: int = 4) -> list[dict]:
        last: Exception | None = None
        for attempt in range(retries):
            try:
                bounds = asyncio.run(self._synth(text, voice, rate, out))
                if out.stat().st_size > 0 and bounds:
                    return bounds
                last = RuntimeError("empty audio or no word boundaries")
            except Exception as exc:  # network errors from the online service
                last = exc
            time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Edge TTS failed after {retries} tries: {last}")


PROVIDERS = {"edge": EdgeProvider}


def map_words(text: str, bounds: list[dict], clip_ms: float) -> tuple[list[dict], bool]:
    """Give every display token a start/end time from the provider's word boundaries.

    Boundaries and tokens are matched on their letters, so "l'école", "qu'est-ce" or a boundary
    covering two tokens ("25 euros") all work. Returns (words, exact); exact is False when some
    token had to be interpolated.
    """
    toks = tokens(text)
    keys = [letters(t) for t in toks]
    owner: list[int] = []          # for every letter of the script, the token it belongs to
    for i, k in enumerate(keys):
        owner.extend([i] * len(k))
    flat = "".join(keys)
    spans: list[list[float] | None] = [None] * len(toks)
    cursor = 0
    for b in bounds:
        key = letters(b["text"])
        if not key:
            continue
        pos = flat.find(key, cursor)
        if pos < 0 or pos - cursor > 40:
            continue
        covered = sorted({owner[p] for p in range(pos, pos + len(key))})
        total = sum(len(keys[i]) for i in covered) or 1
        t = b["start_ms"]
        for i in covered:  # a boundary over several tokens is shared by letter count
            share = (b["end_ms"] - b["start_ms"]) * len(keys[i]) / total
            if spans[i] is None:
                spans[i] = [t, t + share]
            else:
                spans[i][1] = t + share
            t += share
        cursor = pos + len(key)

    exact = all(s is not None for s in spans)
    if not exact:  # fill gaps evenly between the nearest timed neighbours
        i = 0
        while i < len(spans):
            if spans[i] is not None:
                i += 1
                continue
            j = i
            while j < len(spans) and spans[j] is None:
                j += 1
            left = spans[i - 1][1] if i > 0 else 0.0
            right = spans[j][0] if j < len(spans) else clip_ms
            step = max(right - left, 0.0) / (j - i)
            for k in range(i, j):
                spans[k] = [left + step * (k - i), left + step * (k - i + 1)]
            i = j
    return ([{"text": t, "start_ms": round(s[0]), "end_ms": round(s[1])} for t, s in zip(toks, spans)],
            exact)


def synth_lines(dialogue: dict, cfg: dict, out_dir: Path, provider: str = "edge", log=print) -> list[dict]:
    """Create lines/NNN.mp3 + NNN.json for every line.

    Audio already made is reused by what was said (voice, speed, text), not by line number: a
    turn added in the middle costs one call, not one per line after it. A file is only put in
    place once it is complete, so a failed call never leaves audio that looks finished.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    prov = PROVIDERS[provider]()
    rate = cfg["levels"][dialogue["level"]]["rate"]
    have: dict[str, tuple[bytes, list[dict]]] = {}
    for meta in sorted(out_dir.glob("*.json")):
        mp3 = meta.with_suffix(".mp3")
        try:
            data = read_json(meta)
            if mp3.is_file() and mp3.stat().st_size > 0 and data.get("digest") and data.get("bounds"):
                have[data["digest"]] = (mp3.read_bytes(), data["bounds"])
        except (OSError, ValueError, AttributeError):
            continue  # a broken leftover is simply made again

    def put(path: Path, content: bytes) -> None:
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(content)
        os.replace(tmp, path)

    results = []
    made = 0
    items = list(enumerate(dialogue["lines"], 1))
    if dialogue.get("hook"):
        items.insert(0, (0, dialogue["hook"]))  # the opening hook is stored as line 000
    for i, line in items:
        voice = cfg["speakers"][line["speaker"]]["voice"]
        text = line["text"].strip()
        digest = hashlib.sha256(f"{prov.name}|{voice}|{rate}|{text}".encode()).hexdigest()[:16]
        mp3, meta = out_dir / f"{i:03d}.mp3", out_dir / f"{i:03d}.json"
        if digest in have:
            audio, bounds = have[digest]
        else:
            tmp = out_dir / f"{i:03d}.part"
            try:
                bounds = prov.synth(text, voice, rate, tmp)
                audio = tmp.read_bytes()
            finally:
                tmp.unlink(missing_ok=True)
            have[digest] = (audio, bounds)
            made += 1
            log(f"  tts {i:03d}/{len(dialogue['lines'])} {line['speaker']}")
        data = {"index": i, "speaker": line["speaker"], "text": text, "voice": voice, "rate": rate,
                "digest": digest, "bounds": bounds}
        meta.unlink(missing_ok=True)  # between the two writes the line counts as not made
        put(mp3, audio)
        write_json(meta, data)
        results.append(data)
    if not dialogue.get("hook"):
        (out_dir / "000.mp3").unlink(missing_ok=True)
        (out_dir / "000.json").unlink(missing_ok=True)
    for stale in sorted(out_dir.glob("*.mp3")):  # lines removed from the script
        if int(stale.stem) > len(dialogue["lines"]):
            stale.unlink()
            stale.with_suffix(".json").unlink(missing_ok=True)
    log(f"  tts: {made} new, {len(results) - made} reused")
    return results
