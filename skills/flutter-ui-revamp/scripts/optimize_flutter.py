#!/usr/bin/env python3
"""Optimise downloaded assets for a Flutter bundle.

Three jobs, all optional and all skippable when the tool is missing:

  images  a source file treated as @3x becomes the Flutter density set
          (1.0x at the declared path, 2.0x/ and 3.0x/ beside it), in WebP.
          EXCEPT sprites: files in a Flame project, under sprites/ tiles/
          atlas/ …, or with atlas metadata beside them (same stem .json/.xml/
          .atlas/…) are only recompressed losslessly in place — same pixels,
          same size, same filename. Flame does not read density buckets, atlas
          and tile maps address pixels and filenames, and 9-slice insets are
          measured in source pixels; resizing or renaming any of them breaks it.
  svg     svgo pass, plus the vector_graphics_compiler command to emit .vec
  audio   ffmpeg — SFX mono 44.1 kHz, music ~128 kbps. OGG Vorbis only when
          the project has no ios/ or macos/ folder: Apple's AVPlayer (used by
          audioplayers / flame_audio) cannot decode Vorbis, so OGG is silent
          on iOS. Otherwise AAC in .m4a, which every Flutter target plays.

    python3 optimize_flutter.py --project . --dir assets --apply

Dry run is the default. Pillow, svgo and ffmpeg are each optional: when one is
absent the corresponding job is skipped with a warning, never a crash.
"""

from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HEAVY_IMAGE = 500 * 1024
HEAVY_AUDIO = 1024 * 1024
HEAVY_SFX = 50 * 1024
BUNDLE_BUDGET = 30 * 1024 * 1024

RASTER = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
AUDIO = {".wav", ".mp3", ".aiff", ".flac", ".m4a", ".aac", ".ogg"}
BUCKETS = ("1.5x", "2.0x", "3.0x", "4.0x")
SPRITE_DIRS = {"sprites", "sprite", "spritesheets", "tiles", "tilesets", "tilemaps",
               "atlas", "atlases", "particles", "game"}
ATLAS_META = (".json", ".xml", ".atlas", ".plist", ".fnt", ".tsx", ".tmx", ".txt")


def log(msg: str) -> None:
    print(f"[opt] {msg}", file=sys.stderr)


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n} B"


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def run(cmd: List[str]) -> Tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return p.returncode == 0, (p.stderr or p.stdout or "").strip()
    except FileNotFoundError:
        return False, f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return False, f"{cmd[0]} timed out"
    except Exception as exc:  # never let a helper tool kill the run
        return False, str(exc)


# ── images ───────────────────────────────────────────────────────────────────

def is_flame_project(project: Path) -> bool:
    pubspec = project / "pubspec.yaml"
    return pubspec.is_file() and re.search(
        r"^\s+flame\s*:", pubspec.read_text(encoding="utf-8", errors="replace"), re.M) is not None


def sprite_reason(src: Path, root: Path, args) -> Optional[str]:
    """Why this raster must keep its pixels and filename, or None."""
    if args.sprite_mode == "off":
        return None
    if args.sprite_mode == "on":
        return "--sprite-mode on"
    if any(src.with_suffix(ext).exists() for ext in ATLAS_META):
        return "atlas metadata beside it"
    if any(p.lower() in SPRITE_DIRS for p in src.relative_to(root).parts[:-1]):
        return "sprite/tile directory"
    if args.flame:
        return "Flame project (no density buckets)"
    return None


def recompress_in_place(src: Path, args, results: List[Dict], project: Path, why: str) -> None:
    """Lossless PNG re-encode: identical pixels, dimensions and filename."""
    from PIL import Image  # type: ignore

    before = src.stat().st_size
    after = before
    if src.suffix.lower() == ".png":
        with Image.open(src) as im:
            im.load()
            buf = io.BytesIO()
            im.save(buf, "PNG", optimize=True)
        if buf.tell() < before:
            after = buf.tell()
            if args.apply:
                src.write_bytes(buf.getvalue())
    results.append({"file": str(src.relative_to(project)), "kind": "sprite",
                    "before": before, "after": after,
                    "note": f"kept size + name ({why})", "heavy": after > HEAVY_IMAGE})


def optimise_images(files: List[Path], project: Path, root: Path, args, results: List[Dict],
                    renamed: List[Tuple[str, str]]) -> None:
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        log("WARN: Pillow not installed — image job SKIPPED. `pip install Pillow` to enable it.")
        return

    for src in files:
        if any(f"/{b}/" in str(src).replace("\\", "/") for b in BUCKETS):
            continue  # already a density variant
        try:
            why = sprite_reason(src, root, args)
            if why:
                recompress_in_place(src, args, results, project, why)
                continue
            with Image.open(src) as im:
                im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
                w, h = im.size
                scale = {"3x": 3, "2x": 2, "1x": 1}[args.assume]
                base_w, base_h = max(1, round(w / scale)), max(1, round(h / scale))
                if scale == 1 and not args.allow_upscale:
                    log(f"WARN: {src.name} treated as @1x — 2.0x/3.0x would be upscaled; "
                        f"emitting 1.0x only. Re-download at 3x, or pass --allow-upscale.")
                    targets = [(1, base_w, base_h)]
                else:
                    targets = [(1, base_w, base_h), (2, base_w * 2, base_h * 2), (3, base_w * 3, base_h * 3)]
                    targets = [(m, tw, th) for m, tw, th in targets
                               if args.allow_upscale or (tw <= w and th <= h)]

                before = src.stat().st_size
                after_total = 0
                out_paths = []
                for mult, tw, th in targets:
                    out_dir = src.parent if mult == 1 else src.parent / f"{mult}.0x"
                    out = out_dir / (src.stem + ".webp")
                    resized = im if (tw, th) == (w, h) else im.resize((tw, th), Image.LANCZOS)
                    if args.apply:
                        out_dir.mkdir(parents=True, exist_ok=True)
                        resized.save(out, "WEBP", quality=args.quality,
                                     lossless=args.lossless, method=6)
                        after_total += out.stat().st_size
                    else:
                        buf = io.BytesIO()
                        resized.save(buf, "WEBP", quality=args.quality,
                                     lossless=args.lossless, method=6)
                        after_total += buf.tell()
                    out_paths.append(out)

                if args.replace and after_total and after_total < before:
                    renamed.append((str(src.relative_to(project)),
                                    str(out_paths[0].relative_to(project))))
                    if args.apply:
                        src.unlink()
                results.append({
                    "file": str(src.relative_to(project)), "kind": "image",
                    "before": before, "after": after_total,
                    "note": f"{w}x{h} -> {len(out_paths)} bucket(s)",
                    "heavy": max((p.stat().st_size if args.apply and p.exists() else 0)
                                 for p in out_paths) > HEAVY_IMAGE if out_paths else False,
                })
        except Exception as exc:
            log(f"WARN: image job failed on {src}: {exc}")


# ── svg ──────────────────────────────────────────────────────────────────────

def optimise_svgs(files: List[Path], project: Path, args, results: List[Dict]) -> None:
    if not files:
        return
    if not have("svgo"):
        log("WARN: svgo not installed — SVG minification SKIPPED. "
            "`npm i -g svgo` to enable it.")
    for src in files:
        before = src.stat().st_size
        after = before
        if have("svgo") and args.apply:
            ok, err = run(["svgo", "--multipass", "-i", str(src), "-o", str(src)])
            if ok:
                after = src.stat().st_size
            else:
                log(f"WARN: svgo failed on {src.name}: {err}")
        results.append({"file": str(src.relative_to(project)), "kind": "svg",
                        "before": before, "after": after,
                        "note": "svgo" if have("svgo") else "not minified",
                        "heavy": after > HEAVY_IMAGE})
    log("SVG rendered at runtime costs CPU on every frame it appears. Precompile:")
    log("    dart run vector_graphics_compiler --input-dir assets/icons --out-dir assets/icons")
    log("  then load with `vector_graphics`'s VectorGraphic + AssetBytesLoader('....vec').")


# ── audio ────────────────────────────────────────────────────────────────────

def audio_format(project: Path, choice: str) -> str:
    if choice != "auto":
        return choice
    apple = (project / "ios").is_dir() or (project / "macos").is_dir()
    return "m4a" if apple else "ogg"


def optimise_audio(files: List[Path], project: Path, args, results: List[Dict],
                   renamed: List[Tuple[str, str]]) -> None:
    if not files:
        return
    if not have("ffmpeg"):
        log("WARN: ffmpeg not found — audio job SKIPPED. Install ffmpeg to enable it.")
        return
    fmt = audio_format(project, args.audio_format)
    log(f"audio target: {fmt}" + (" (ios/ or macos/ present — AVPlayer cannot play OGG Vorbis)"
                                  if fmt == "m4a" and args.audio_format == "auto" else ""))
    for src in files:
        if src.suffix.lower() == f".{fmt}":
            continue  # already in the target format; re-encoding only loses quality
        if fmt == "m4a" and src.suffix.lower() == ".ogg":
            log(f"WARN: {src.name} is OGG and this project builds for iOS/macOS, where it "
                f"will not play — converting to .m4a.")
        rel = str(src).replace("\\", "/")
        is_sfx = "/sfx/" in rel or args.audio_profile == "sfx"
        out = src.with_suffix(f".{fmt}")
        codec = ["-c:a", "libvorbis"] if fmt == "ogg" else ["-c:a", "aac", "-movflags", "+faststart"]
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn"]
        if is_sfx:
            cmd += ["-ac", "1", "-ar", "44100"] + codec + (["-q:a", "3"] if fmt == "ogg" else ["-b:a", "64k"])
        else:
            # Keep the source channel count (≤ 2); upmixing mono music doubles its bytes.
            cmd += ["-ar", "44100"] + codec + ["-b:a", "128k"]
        cmd.append(str(out))
        before = src.stat().st_size
        after = before
        if args.apply:
            ok, err = run(cmd)
            if not ok:
                log(f"WARN: ffmpeg failed on {src.name}: {err}")
                continue
            after = out.stat().st_size
            if args.replace and after < before:
                src.unlink()
        if args.replace and (not args.apply or not src.exists()):
            renamed.append((str(src.relative_to(project)), str(out.relative_to(project))))
        results.append({"file": str(src.relative_to(project)), "kind": "audio",
                        "before": before, "after": after,
                        "note": f"sfx mono {fmt}" if is_sfx else f"music {fmt} 128k",
                        "heavy": after > (HEAVY_SFX if is_sfx else HEAVY_AUDIO)})


# ── pubspec snippet ──────────────────────────────────────────────────────────

def pubspec_snippet(project: Path, root: Path) -> str:
    dirs = set()
    for p in root.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            rel_dir = str(p.parent.relative_to(project)).replace("\\", "/") + "/"
            if any(rel_dir.rstrip("/").endswith(b) for b in BUCKETS):
                continue  # Flutter resolves buckets from the parent entry
            dirs.add(rel_dir)
    lines = ["flutter:", "  assets:"] + [f"    - {d}" for d in sorted(dirs)]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Optimise assets for a Flutter bundle.")
    ap.add_argument("--project", default=".")
    ap.add_argument("--dir", default="assets", help="Directory to process, relative to --project")
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    ap.add_argument("--replace", action="store_true",
                    help="Delete the source file once the optimised one is smaller")
    ap.add_argument("--assume", choices=["1x", "2x", "3x"], default="3x",
                    help="Density of the source images (default: 3x)")
    ap.add_argument("--allow-upscale", action="store_true")
    ap.add_argument("--quality", type=int, default=85)
    ap.add_argument("--lossless", action="store_true", help="Lossless WebP (flat art, UI, sprites)")
    ap.add_argument("--audio-profile", choices=["auto", "sfx", "music"], default="auto")
    ap.add_argument("--audio-format", choices=["auto", "ogg", "m4a"], default="auto",
                    help="auto: m4a when ios/ or macos/ exists (AVPlayer has no Vorbis), else ogg")
    ap.add_argument("--sprite-mode", choices=["auto", "on", "off"], default="auto",
                    help="auto: keep pixels+names for Flame projects, sprite/tile dirs and "
                         "atlas-backed images; on: for everything; off: never")
    ap.add_argument("--skip", default="", help="Comma list: images,svg,audio")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    root = (project / args.dir).resolve()
    if not root.is_dir():
        log(f"FATAL: {root} does not exist.")
        return 2
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    args.flame = is_flame_project(project)
    if args.flame and args.sprite_mode == "auto":
        log("Flame project: images keep their pixels and filenames (Flame reads no density "
            "buckets). Pass --sprite-mode off for widget-only images in a separate --dir.")

    everything = [p for p in sorted(root.rglob("*")) if p.is_file() and not p.name.startswith(".")]
    images = [p for p in everything if p.suffix.lower() in RASTER]
    svgs = [p for p in everything if p.suffix.lower() == ".svg"]
    audio = [p for p in everything if p.suffix.lower() in AUDIO]
    log(f"{len(everything)} file(s) under {root.relative_to(project)} — "
        f"{len(images)} raster, {len(svgs)} svg, {len(audio)} audio")

    results: List[Dict] = []
    renamed: List[Tuple[str, str]] = []
    if images and "images" not in skip:
        optimise_images(images, project, root, args, results, renamed)
    if svgs and "svg" not in skip:
        optimise_svgs(svgs, project, args, results)
    if audio and "audio" not in skip:
        optimise_audio(audio, project, args, results, renamed)

    print("")
    print("| File | Kind | Before | After | Δ | Note |")
    print("|---|---|---:|---:|---:|---|")
    tb = ta = 0
    for r in sorted(results, key=lambda x: -(x["before"])):
        tb += r["before"]
        ta += r["after"]
        delta = (r["after"] - r["before"]) / r["before"] * 100 if r["before"] else 0
        flag = " ⚠ heavy" if r.get("heavy") else ""
        print(f"| `{r['file']}` | {r['kind']} | {human(r['before'])} | {human(r['after'])} "
              f"| {delta:+.0f}% | {r['note']}{flag} |")
    if results:
        print(f"| **total** | | **{human(tb)}** | **{human(ta)}** "
              f"| **{((ta - tb) / tb * 100) if tb else 0:+.0f}%** | |")
    print("")

    grand = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    log(f"total under {args.dir}: {human(grand)}")
    if grand > BUNDLE_BUDGET:
        log(f"WARN: over the {human(BUNDLE_BUDGET)} asset budget. Drop unused packs, "
            f"or move the heavy ones behind deferred components.")
    heavy = [r for r in results if r.get("heavy")]
    if heavy:
        log(f"WARN: {len(heavy)} file(s) still over threshold — review them individually.")

    if renamed:
        verb = "replaced" if args.apply else "would be replaced"
        log(f"{len(renamed)} source file(s) {verb} by a new filename. Every Dart reference, "
            f"flutter_gen accessor and metadata file pointing at the old name must be updated; "
            f"re-run scan_project.py — its 'referenced in code but absent from disk' list "
            f"must be empty:")
        for old, new in renamed[:30]:
            print(f"        {old}  ->  {new}", file=sys.stderr)

    print("# pubspec.yaml — paste under the existing `flutter:` key")
    print(pubspec_snippet(project, root))
    print("")

    if not args.apply:
        log("DRY RUN — nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
