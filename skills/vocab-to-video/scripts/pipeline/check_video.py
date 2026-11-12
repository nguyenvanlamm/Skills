"""Hard checks on a rendered video, plus three still frames for a human or agent to look at."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
                          "-show_streams", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def check(video: Path, size: tuple[int, int], expect_s: float, target_lufs: float,
          frames_dir: Path, fps: int) -> tuple[list[str], dict]:
    problems: list[str] = []
    info = probe(video)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    duration = float(info["format"]["duration"])
    stats = {"duration_s": round(duration, 2)}
    if not v:
        return ["no video stream"], stats
    if (v["width"], v["height"]) != size:
        problems.append(f"size {v['width']}x{v['height']}, expected {size[0]}x{size[1]}")
    num, den = (int(x) for x in v["avg_frame_rate"].split("/"))
    stats["fps"] = round(num / den, 2) if den else 0
    if stats["fps"] != fps:
        problems.append(f"frame rate {stats['fps']} fps, expected {fps}")
    if not a:
        problems.append("no audio stream")
    if abs(duration - expect_s) > 0.25:
        problems.append(f"duration {duration:.2f}s, audio track is {expect_s:.2f}s")

    proc = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vf",
                           "blackdetect=d=0.5:pix_th=0.05", "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True)
    black = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", proc.stderr)
    if black:
        problems.append(f"black frames at {black[:3]}")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", proc.stderr)
    if m:
        stats["lufs"] = float(m[-1])
        if abs(stats["lufs"] - target_lufs) > 1.5:
            problems.append(f"loudness {stats['lufs']} LUFS, target {target_lufs}")
    elif a:
        problems.append("could not measure loudness")

    frames_dir.mkdir(parents=True, exist_ok=True)
    stats["frames"] = []
    for frac in (0.15, 0.5, 0.85):
        out = frames_dir / f"{video.stem}_{int(frac * 100):02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{duration * frac:.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "3", str(out)], check=True)
        stats["frames"].append(str(out))
    return problems, stats
