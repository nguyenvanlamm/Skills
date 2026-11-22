"""Hard checks on a rendered video, plus still frames for a human or agent to look at:
one frame per shot, tiled into a few contact sheets."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

SHEET = 12  # frames per contact sheet


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
                          "-show_streams", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def shot_moments(timeline: dict) -> list[float]:
    """One moment per shot (seconds) at which its picture is settled: late in the shot, when
    the characters have arrived, the label is out and the last line's bubble is up."""
    out = []
    for shot in timeline.get("shots") or []:
        a, b = shot["startMs"], shot["endMs"]
        out.append(round((a + (b - a) * (0.2 if any(c.get("exit") for c in shot.get("chars", [])) else 0.7)) / 1000, 2))
    return out


def contact_sheets(video: Path, moments: list[float], frames_dir: Path, portrait: bool) -> tuple[list[str], list[str]]:
    """(sheets, single frames). Every frame is also kept on its own, named by its second."""
    folder = frames_dir / video.stem
    folder.mkdir(parents=True, exist_ok=True)
    for old in list(folder.glob("*.jpg")) + list(frames_dir.glob(f"{video.stem}_sheet*.jpg")):
        old.unlink()
    singles = []
    for n, sec in enumerate(moments, 1):
        out = folder / f"{n:02d}_{sec:07.2f}s.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{sec:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", f"scale={'540:-2' if portrait else '960:-2'}", "-q:v", "3", str(out)], check=True)
        singles.append(str(out))
    cols, cell = (6, "320:-2") if portrait else (3, "640:-2")
    sheets = []
    for k in range(0, len(singles), SHEET):
        group = singles[k:k + SHEET]
        rows = -(-len(group) // cols)
        out = frames_dir / f"{video.stem}_sheet{k // SHEET + 1}.jpg"
        cmd = ["ffmpeg", "-v", "error", "-y"]
        for f in group:
            cmd += ["-i", f]
        chain = "".join(f"[{i}:v]scale={cell}[s{i}];" for i in range(len(group)))
        chain += "".join(f"[s{i}]" for i in range(len(group)))
        chain += f"concat=n={len(group)}:v=1:a=0,tile={cols}x{rows}:padding=6:color=white"
        subprocess.run(cmd + ["-filter_complex", chain, "-frames:v", "1", "-q:v", "3", str(out)], check=True)
        sheets.append(str(out))
    return sheets, singles


def check(video: Path, size: tuple[int, int], expect_s: float, target_lufs: float,
          frames_dir: Path, fps: int, moments: list[float] | None = None) -> tuple[list[str], dict]:
    """`moments` are the seconds to take stills at (see shot_moments); without them, three."""
    problems: list[str] = []
    info = probe(video)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    duration = float(info["format"]["duration"])
    stats = {"duration_s": round(duration, 2), "frames": [], "sheets": []}
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

    moments = [m for m in (moments or []) if 0 <= m < duration] or [duration * f for f in (0.15, 0.5, 0.85)]
    stats["sheets"], stats["frames"] = contact_sheets(video, moments, frames_dir, size[1] > size[0])
    return problems, stats
