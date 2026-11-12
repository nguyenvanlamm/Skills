"""Join the per-line audio into one track and write the timeline Remotion renders from."""
from __future__ import annotations

import re
import shutil
import subprocess
import wave
from pathlib import Path

from common import ASSETS, tokens, vocab_hits, write_json
from tts import map_words

RATE = 48_000


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed:\n{proc.stderr[-1500:]}")
    return proc


def decode(mp3: Path) -> bytes:
    """MP3 -> raw 48 kHz mono 16-bit PCM."""
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-f", "s16le", "-ac", "1",
                           "-ar", str(RATE), "-"], capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(f"could not decode {mp3}: {proc.stderr.decode()[-500:]}")
    return proc.stdout


def silence(ms: float) -> bytes:
    return b"\x00\x00" * round(RATE * ms / 1000)


def integrated_lufs(path: Path) -> float:
    proc = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"])
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", proc.stderr)[-1])


def normalise(src: Path, dst: Path, target: float) -> float:
    """Mono master -> stereo track at the target loudness.

    Plain gain plus a limiter at -1.5 dB, so timing is untouched. Loudness is measured on the
    stereo result (what the video will carry) and the gain corrected until it is within 0.3 LU.
    Returns the final integrated loudness.
    """
    gain = 0.0
    got = target
    for _ in range(4):
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af",
             f"volume={gain:.2f}dB,alimiter=limit=0.84:level=disabled", "-ar", str(RATE), "-ac", "2",
             "-c:a", "pcm_s16le", str(dst)])
        got = integrated_lufs(dst)
        if abs(got - target) <= 0.3:
            break
        gain += target - got
    return got


def build(level_dir: Path, dialogue: dict, line_meta: list[dict], cfg: dict, log=print,
          name: str = "episode") -> dict:
    """Write <name>.json and public/<name>.wav from the given lines (index 0 is the opening hook)."""
    t = cfg["timing_ms"]
    public = level_dir / "public"
    (public / "fonts").mkdir(parents=True, exist_ok=True)

    pcm = bytearray(silence(t["lead_in"]))
    lines_out = []
    inexact = []
    for meta in line_meta:
        clip = decode(level_dir / "lines" / f"{meta['index']:03d}.mp3")
        clip_ms = len(clip) / 2 / RATE * 1000
        words, exact = map_words(meta["text"], meta["bounds"], clip_ms)
        if not exact:
            inexact.append(meta["index"])
        keep_ms = min(clip_ms, words[-1]["end_ms"] + t["tail_keep"])
        clip = clip[: round(RATE * keep_ms / 1000) * 2]
        start = len(pcm) / 2 / RATE * 1000
        pcm += clip
        marks, _ = vocab_hits(tokens(meta["text"]), dialogue["vocab"])
        lines_out.append({
            "speaker": meta["speaker"],
            "text": meta["text"],
            "startMs": round(start),
            "endMs": round(start + keep_ms),
            "words": [{"text": w["text"], "startMs": round(start + w["start_ms"]),
                       "endMs": round(start + min(w["end_ms"], keep_ms)), "isVocab": mark}
                      for w, mark in zip(words, marks)],
        })
        if meta["index"] == 0:
            lines_out[-1]["kind"] = "hook"
        last_gap = t["hook_gap"] if meta["index"] == 0 else t["gap"]
        pcm += silence(last_gap)
    pcm += silence(max(0, t["outro"] - last_gap))

    raw = level_dir / f"{name}_raw.wav"
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(pcm))
    audio = f"{name}.wav"
    lufs = normalise(raw, public / audio, cfg["loudness_lufs"])
    raw.unlink()
    with wave.open(str(public / audio)) as w:
        duration_ms = round(w.getnframes() / w.getframerate() * 1000)

    speakers = []
    for sid, s in cfg["speakers"].items():
        src = ASSETS / "speakers" / s["image"]
        if not src.is_file():
            raise RuntimeError(f"missing portrait {src}; run portraits.py first")
        shutil.copy2(src, public / s["image"])
        speakers.append({"id": sid, "name": s["name"], "image": s["image"], "color": s["color"],
                         "side": s["side"]})
    for font in sorted((ASSETS / "fonts").glob("*.ttf")):
        shutil.copy2(font, public / "fonts" / font.name)

    episode = {
        "title": dialogue["title"],
        "level": dialogue["level"],
        "fps": cfg["fps"],
        "durationMs": duration_ms,
        "audio": audio,
        "speakers": speakers,
        "vocab": [v["word"] for v in dialogue["vocab"]],
        "lines": lines_out,
    }
    write_json(level_dir / f"{name}.json", episode)
    if inexact:
        log(f"  WARN word timings interpolated on lines {inexact}")
    log(f"  {name}: {duration_ms / 1000:.1f}s, {len(lines_out)} lines, {lufs:.1f} LUFS")
    return episode
