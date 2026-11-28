#!/usr/bin/env python3
"""Assemble a narrated video from a storyboard JSON.

Pipeline: narration -> audio per scene -> frames (Pillow) -> scene clips (ffmpeg)
          -> video.mp4 + captions.srt + chapters.txt + build_report.json

Requires  ffmpeg and ffprobe on PATH, Pillow (pip install pillow).
Optional  edge-tts (pip install edge-tts) for the default voice provider.

Voice providers (--tts)
  edge    Microsoft Edge neural voices through the edge-tts package. Free and
          good for drafts; it is an unofficial endpoint, so use a licensed TTS
          (or your own recording) for anything you monetise.
  cmd     Any TTS you have. --tts-cmd is a shell template with {text_file} and
          {out}, e.g. --tts-cmd "mytts --in {text_file} --out {out}"
  files   Pre-recorded audio in --audio-dir, named <scene id>.mp3|wav|m4a or
          001.mp3, 002.mp3 ... (1-based scene order).
  silent  No voice. Timing is estimated from text length. Use it to check
          layout and pacing quickly before spending TTS time.

Storyboard format: see references/storyboard.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    sys.exit("Pillow is missing: pip install pillow")

FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
}
DEFAULT_STYLE = {
    "bg": "#0f172a",
    "fg": "#f8fafc",
    "muted": "#cbd5e1",
    "accent": "#fbbf24",
    "font": None,
    "font_bold": None,
    "overlay": 0.6,
}
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #
def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
        sys.exit(f"Command failed: {' '.join(shlex.quote(c) for c in cmd[:6])} ...\n{tail}")


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        sys.exit(f"Cannot read the duration of {path}. Is it a valid audio file?")


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def find_font(explicit: str | None, weight: str) -> str | None:
    for path in ([explicit] if explicit else []) + FONT_CANDIDATES[weight]:
        if path and Path(path).exists():
            return path
    return None


def load_font(path: str | None, size: int):
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def timestamp(seconds: float, srt: bool = True) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    if srt:
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# --------------------------------------------------------------------------- #
# Voice
# --------------------------------------------------------------------------- #
def tts_edge(text: str, voice: str, rate: str, out: Path) -> None:
    try:
        import edge_tts
    except ImportError:
        sys.exit("edge-tts is missing: pip install edge-tts (or use --tts cmd | files | silent)")
    import asyncio

    async def go() -> None:
        await edge_tts.Communicate(text, voice, rate=rate).save(str(out))

    try:
        asyncio.run(go())
    except Exception as err:  # network failure, unknown voice, ...
        sys.exit(f"edge-tts failed ({err}). Check the network and the voice name '{voice}'.")


def tts_cmd(template: str, text: str, out: Path) -> None:
    text_file = out.with_suffix(".txt")
    text_file.write_text(text, encoding="utf-8")
    cmd = template.format(text_file=shlex.quote(str(text_file)), out=shlex.quote(str(out)))
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        sys.exit(f"--tts-cmd failed for {out.name}:\n{proc.stderr.strip()[-600:]}")


def find_audio_file(audio_dir: Path, scene: dict, index: int) -> Path:
    names = [str(scene.get("id", "")), f"{index + 1:03d}", f"{index + 1:02d}", str(index + 1)]
    for name in filter(None, names):
        for ext in AUDIO_EXTS:
            candidate = audio_dir / f"{name}{ext}"
            if candidate.exists():
                return candidate
    sys.exit(f"No audio for scene {index + 1} in {audio_dir} (tried {', '.join(filter(None, names))}).")


# --------------------------------------------------------------------------- #
# Frames
# --------------------------------------------------------------------------- #
def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: float) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        words = para.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            if draw.textlength(f"{current} {word}", font=font) <= max_width:
                current = f"{current} {word}"
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def background(scene: dict, style: dict, size: tuple[int, int], base_dir: Path) -> tuple[Image.Image, bool]:
    """Return (RGB background, has_image)."""
    w, h = size
    top = hex_rgb(style["bg"])
    bottom = tuple(int(c * 0.72) for c in top)
    column = Image.new("RGB", (1, 2))
    column.putpixel((0, 0), top)
    column.putpixel((0, 1), bottom)
    canvas = column.resize(size, Image.BILINEAR)
    image_ref = scene.get("image")
    if not image_ref:
        return canvas, False
    path = Path(image_ref)
    if not path.is_absolute():
        path = base_dir / path
    if not path.exists():
        sys.exit(f"Scene image not found: {path}")
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if scene.get("image_fit", "cover") == "contain":
        fitted = ImageOps.contain(img, size, Image.LANCZOS)
        canvas.paste(fitted, ((w - fitted.width) // 2, (h - fitted.height) // 2))
        return canvas, True
    return ImageOps.fit(img, size, Image.LANCZOS), True


def text_layer(scene: dict, style: dict, size: tuple[int, int], has_image: bool) -> Image.Image:
    """RGBA layer with the dimming overlay and all text for one scene."""
    w, h = size
    base = min(w, h)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    layout = scene.get("layout") or ("caption" if has_image and not scene.get("body") else "text")
    kicker, heading, body = (scene.get(k) or "" for k in ("kicker", "heading", "body"))
    regular = find_font(style.get("font"), "regular")
    bold = find_font(style.get("font_bold") or style.get("font"), "bold")
    fg, muted, accent = hex_rgb(style["fg"]), hex_rgb(style["muted"]), hex_rgb(style["accent"])
    margin = int(w * 0.075)

    if layout == "caption":
        if not heading:
            return layer
        font = load_font(bold, int(base * 0.054))
        lines = wrap(draw, heading, font, w - 2 * margin)
        line_h = int(font.size * 1.3)
        block_h = line_h * len(lines)
        # Portrait video is watched as a Short: the bottom fifth sits under the app UI.
        bottom_pad = int(h * 0.2) if h > w else int(base * 0.045)
        fade = int(base * 0.07)
        band_h = block_h + bottom_pad + fade
        band = Image.new("L", (1, band_h))
        for y in range(band_h):
            band.putpixel((0, y), int(225 * min(1.0, y / fade)))
        shade = Image.new("RGBA", (w, band_h), (0, 0, 0, 255))
        shade.putalpha(band.resize((w, band_h)))
        layer.alpha_composite(shade, (0, h - band_h))
        y = h - block_h - bottom_pad
        for line in lines:
            draw.text(((w - draw.textlength(line, font=font)) / 2, y), line, font=font, fill=fg + (255,))
            y += line_h
        return layer

    if has_image:
        alpha = int(255 * float(scene.get("overlay", style.get("overlay", 0.6))))
        layer.alpha_composite(Image.new("RGBA", size, (0, 0, 0, alpha)))

    centered = layout == "title"
    max_w = w - 2 * margin if not centered else int(w * 0.84)
    avail_h = h - 2 * int(h * 0.09)
    specs = [
        (kicker.upper(), regular, 0.032, accent, 1.25, 0.022),
        (heading, bold, 0.105 if centered else 0.08, fg, 1.16, 0.035),
        (body, regular, 0.047, muted, 1.42, 0.0),
    ]
    scale = 1.0
    while True:  # shrink text until the block fits the safe area
        blocks, total = [], 0
        for text, font_path, rel, color, spacing, gap in specs:
            if not text:
                continue
            font = load_font(font_path, max(12, int(base * rel * scale)))
            lines = wrap(draw, text, font, max_w)
            line_h = int(font.size * spacing)
            blocks.append((lines, font, color, line_h, int(base * gap * scale)))
            total += line_h * len(lines) + int(base * gap * scale)
        if blocks:
            total -= blocks[-1][4]
        bar_h, bar_gap = int(base * 0.009), int(base * 0.03)
        total += bar_h + bar_gap
        if total <= avail_h or scale < 0.5:
            break
        scale *= 0.92
    if not blocks:
        return layer

    y = (h - total) // 2
    bar_w = int(base * 0.09)
    bar_x = (w - bar_w) // 2 if centered else margin
    draw.rectangle([bar_x, y, bar_x + bar_w, y + bar_h], fill=accent + (255,))
    y += bar_h + bar_gap
    for lines, font, color, line_h, gap in blocks:
        for line in lines:
            x = (w - draw.textlength(line, font=font)) / 2 if centered else margin
            draw.text((x, y), line, font=font, fill=color + (255,))
            y += line_h
        y += gap
    return layer


# --------------------------------------------------------------------------- #
# Captions
# --------------------------------------------------------------------------- #
def split_captions(text: str, max_chars: int = 84) -> list[str]:
    pieces: list[str] = []
    for sentence in re.split(r"(?<=[.!?…])\s+", " ".join(text.split())):
        while len(sentence) > max_chars:
            cut = max(sentence.rfind(", ", 0, max_chars), sentence.rfind("; ", 0, max_chars))
            cut = cut + 1 if cut > max_chars * 0.4 else sentence.rfind(" ", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if sentence:
            pieces.append(sentence)
    return pieces


# --------------------------------------------------------------------------- #
# Main build
# --------------------------------------------------------------------------- #
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("storyboard", help="path to storyboard.json")
    p.add_argument("--out", default="build", help="output directory (default: build)")
    p.add_argument("--tts", choices=["edge", "cmd", "files", "silent"], default=None)
    p.add_argument("--tts-cmd", help="shell template with {text_file} and {out} (for --tts cmd)")
    p.add_argument("--tts-ext", default="mp3", help="extension your --tts-cmd writes (default mp3)")
    p.add_argument("--audio-dir", help="directory of pre-recorded audio (for --tts files)")
    p.add_argument("--voice", help="override the storyboard voice, e.g. vi-VN-HoaiMyNeural")
    p.add_argument("--rate", default="+0%", help="edge-tts speaking rate, e.g. +8%% or -5%%")
    p.add_argument("--music", help="background music file, looped under the narration")
    p.add_argument("--music-volume", type=float, default=0.08)
    p.add_argument("--motion", choices=["zoom", "none"], default="zoom", help="slow zoom on image scenes")
    p.add_argument("--only-frames", action="store_true", help="render frames only, to review layout fast")
    args = p.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not on PATH. Install ffmpeg first.")

    sb_path = Path(args.storyboard).resolve()
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    scenes = sb.get("scenes") or []
    if not scenes:
        sys.exit("The storyboard has no scenes.")
    w, h = sb.get("resolution", [1920, 1080])
    if w % 2 or h % 2:
        sys.exit("Resolution must use even numbers (e.g. 1920x1080 or 1080x1920).")
    fps = int(sb.get("fps", 30))
    style = {**DEFAULT_STYLE, **(sb.get("style") or {})}
    voice = args.voice or sb.get("voice") or "en-US-AriaNeural"
    provider = args.tts or sb.get("tts") or "edge"
    if provider == "cmd" and not args.tts_cmd:
        sys.exit("--tts cmd needs --tts-cmd.")
    if provider == "files" and not args.audio_dir:
        sys.exit("--tts files needs --audio-dir.")
    if not find_font(style.get("font"), "regular"):
        print("[warn] No TrueType font found; accented characters may not render. "
              "Set style.font to a .ttf path.", file=sys.stderr)

    out = Path(args.out)
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)

    report, srt, chapters, clips = [], [], [], []
    cursor = 0.0
    for i, scene in enumerate(scenes):
        tag = f"scene_{i + 1:03d}"
        narration = " ".join((scene.get("narration") or "").split())

        # 1. Frames -------------------------------------------------------- #
        clip_src: Path | None = None
        if scene.get("video"):
            clip_src = Path(scene["video"])
            if not clip_src.is_absolute():
                clip_src = sb_path.parent / clip_src
            if not clip_src.exists():
                sys.exit(f"Scene video not found: {clip_src}")
            poster = work / f"{tag}_poster.png"
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip_src), "-frames:v", "1", str(poster)])
            scene = {**scene, "image": str(poster), "image_fit": "cover"}
        bg, has_image = background(scene, style, (w, h), sb_path.parent)
        fg_layer = text_layer(scene, style, (w, h), has_image)
        flat = bg.convert("RGBA")
        flat.alpha_composite(fg_layer)
        frame = work / f"{tag}.png"
        flat.convert("RGB").save(frame)
        if args.only_frames:
            print(f"[frame] {frame}")
            continue

        # 2. Audio --------------------------------------------------------- #
        audio: Path | None = None
        if narration and provider != "silent":
            if provider == "files":
                audio = find_audio_file(Path(args.audio_dir), scene, i)
            else:
                key = hashlib.sha1(f"{provider}|{voice}|{args.rate}|{narration}".encode()).hexdigest()[:10]
                ext = "mp3" if provider == "edge" else args.tts_ext
                audio = work / f"{tag}_{key}.{ext}"
                if not audio.exists():  # cache: unchanged narration is not re-synthesised
                    if provider == "edge":
                        tts_edge(narration, voice, args.rate, audio)
                    else:
                        tts_cmd(args.tts_cmd, narration, audio)
            speech = probe_duration(audio)
        elif narration:
            speech = max(1.5, len(narration) / 15)  # roughly 15 characters per second
        else:
            speech = 0.0
        pause = float(scene.get("pause", 0.35))
        duration = max(speech + pause, float(scene.get("duration") or 0), 0 if narration else 3.0)
        frames = math.ceil(duration * fps)
        duration = frames / fps

        # 3. Scene clip (MPEG-TS so clips concatenate without re-encoding) --- #
        clip = work / f"{tag}.ts"
        motion = scene.get("motion", args.motion) == "zoom" and has_image and not clip_src
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        if clip_src:  # b-roll: loop or trim the clip to the scene length, text stays on top
            fg_png = work / f"{tag}_fg.png"
            fg_layer.save(fg_png)
            graph = (
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}[bg];"
                f"[bg][1:v]overlay,format=yuv420p[v]"
            )
            cmd += ["-stream_loop", "-1", "-i", str(clip_src), "-loop", "1", "-framerate", str(fps), "-i", str(fg_png)]
            audio_index = 2
        elif motion:
            bg_png, fg_png = work / f"{tag}_bg.png", work / f"{tag}_fg.png"
            bg.save(bg_png)
            fg_layer.save(fg_png)
            zoom = f"1+0.08*on/{frames}" if i % 2 == 0 else f"1.08-0.08*on/{frames}"
            graph = (
                f"[0:v]scale={w * 2}:{h * 2},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={frames}:s={w}x{h}:fps={fps}[bg];[bg][1:v]overlay=shortest=1,format=yuv420p[v]"
            )
            cmd += ["-i", str(bg_png), "-loop", "1", "-framerate", str(fps), "-i", str(fg_png)]
            audio_index = 2
        else:
            graph = "[0:v]format=yuv420p[v]"
            cmd += ["-loop", "1", "-framerate", str(fps), "-i", str(frame)]
            audio_index = 1
        if audio:
            cmd += ["-i", str(audio)]
        else:
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        cmd += [
            "-filter_complex", graph, "-map", "[v]", "-map", f"{audio_index}:a", "-af", "apad",
            "-t", f"{duration:.4f}", "-r", str(fps),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-g", str(fps * 2),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-f", "mpegts", str(clip),
        ]
        run(cmd)
        clips.append(clip)

        # 4. Captions, chapters, report ------------------------------------ #
        if narration:
            pieces = split_captions(narration)
            total_chars = sum(len(x) for x in pieces) or 1
            t = cursor
            for piece in pieces:
                span = speech * len(piece) / total_chars
                srt.append((t, t + span, piece))
                t += span
        if scene.get("chapter"):
            chapters.append((cursor, scene["chapter"]))
        report.append({"scene": i + 1, "id": scene.get("id"), "start": round(cursor, 2),
                       "duration": round(duration, 2), "speech": round(speech, 2),
                       "audio": str(audio) if audio else None, "motion": motion,
                       "video": str(clip_src) if clip_src else None})
        cursor += duration
        print(f"[scene {i + 1}/{len(scenes)}] {duration:.1f}s", file=sys.stderr)

    if args.only_frames:
        return

    # 5. Concatenate ------------------------------------------------------- #
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8")
    video = out / "video.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing)]
    if args.music:
        if not Path(args.music).exists():
            sys.exit(f"Music file not found: {args.music}")
        cmd += [
            "-stream_loop", "-1", "-i", args.music,
            "-filter_complex",
            f"[1:a]volume={args.music_volume}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        ]
    else:
        cmd += ["-c", "copy", "-bsf:a", "aac_adtstoasc"]
    cmd += ["-movflags", "+faststart", str(video)]
    run(cmd)

    (out / "captions.srt").write_text(
        "".join(f"{n}\n{timestamp(a)} --> {timestamp(b)}\n{text}\n\n" for n, (a, b, text) in enumerate(srt, 1)),
        encoding="utf-8",
    )
    (out / "chapters.txt").write_text(
        "".join(f"{timestamp(t, srt=False)} {name}\n" for t, name in chapters), encoding="utf-8"
    )
    final = probe_duration(video)
    summary = {
        "title": sb.get("title"), "video": str(video), "captions": str(out / "captions.srt"),
        "chapters": str(out / "chapters.txt"), "duration_s": round(final, 2),
        "resolution": [w, h], "fps": fps, "tts": provider, "voice": voice if provider == "edge" else None,
        "music": args.music, "scenes": report,
    }
    (out / "build_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("video", "captions", "chapters", "duration_s", "resolution")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
