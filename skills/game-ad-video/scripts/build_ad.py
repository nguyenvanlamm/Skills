#!/usr/bin/env python3
"""Cut recorded gameplay takes into an ad or a trailer, driven by a storyboard file (ad.json,
trailer.json).

  build_ad.py storyboard AD.json [--profile ua]          # the shot table with computed times
  build_ad.py board --take T.mp4 --at S --title … --hook … --beats "a|b|c" --out D.png [--ad AD.json] [--wide]
  build_ad.py beats MUSIC [--drop-at S] [--length L] [--json]   # beat grid + sections (beats.py)
  build_ad.py render AD.json --profile PROFILE [--variant V[,V2]] [--out F.mp4] [--force]
  build_ad.py check F.mp4 --profile PROFILE [--ad AD.json] [--variant V[,V2]]
  build_ad.py thumb --take T.mp4 --at S --text "…" --out T.png [--ad AD.json] [--size 1280x720]

Profiles
  ua            1080x1920, 30 fps, 6–60 s, captions + end card + CTA, AAC 192k, ≤ 30 MB
  ua-1x1        1080x1080, the same ad for Meta feed       ua-4x5   1080x1350, Meta feed
  ua-16x9       1920x1080, landscape UA (Unity / AppLovin / Meta desktop)
  app-preview   886x1920, 30 fps, 15–30 s, in-game footage only, no end card, AAC stereo 256k
  play-promo    1080x1920, 15–30 s, Google Play preview video (YouTube): no CTA, no "best"/"#1"
  trailer       1920x1080, 30 fps, 45–120 s, cards + layouts + end card, music-led mix, AAC 320k
  trailer-9x16  1080x1920, 30 fps, 30–60 s, the vertical cut-down of the same trailer.json

A storyboard's top-level "profiles" sets which profiles its shots belong to (default: every ua*
profile + app-preview; "ua" in a list means the whole ua* family). `variants` patch shots for
one cut (hook, length, language); --variant applies them and names the output after them.
Trailers cut on the beat: with music.bpm/beat0/start, an item given in `beats` ends on the beat
grid. Portrait takes go into a 16:9 frame by `layout`: fit, fill, panel, grid (2 takes also in
portrait: "Level 1 vs Level 50"). Captions, cards and the end card animate (`anim`); `touches`
draws the player's taps and swipes from the take's logged inputs.

Audio follows huashu-design's two-layer rule: BGM low-passed at 4 kHz at 0.45, SFX cues
high-passed at 800 Hz, amix normalize=0, BGM fade 0.3 s in / 1.5 s out, then loudnorm to -14 LUFS.
Trailers keep the music full-range at 0.9 and fade it out over 2 s; music.start trims the track.
BGM and SFX names resolve against huashu-design's assets when the skill is installed
($HUASHU_DESIGN_DIR or ~/.claude/skills/huashu-design); a path relative to AD.json always wins.
Text (captions, end card, direction boards) is HTML rendered to PNG with Playwright.
Videos never go to GitHub: `render` writes a .gitignore next to its output and `check` fails a
video that git would push.
"""
import argparse
import base64
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FPS = 30
PROFILES = {
    # UA cuts: Meta wants click-to-play videos under 30 MB; Unity recommends 10, takes up to 100.
    # 6–60 s spans the networks (Snapchat ~6 s … Unity ≤ 60 s); `storyboard` says which fit.
    "ua": {"w": 1080, "h": 1920, "min": 6, "max": 60, "end_card": True, "abr": "192k",
           "max_bytes": 30 * 1000 * 1000, "out": "ad-ua-9x16.mp4"},
    "ua-1x1": {"w": 1080, "h": 1080, "min": 6, "max": 60, "end_card": True, "abr": "192k",
               "max_bytes": 30 * 1000 * 1000, "out": "ad-ua-1x1.mp4"},
    "ua-4x5": {"w": 1080, "h": 1350, "min": 6, "max": 60, "end_card": True, "abr": "192k",
               "max_bytes": 30 * 1000 * 1000, "out": "ad-ua-4x5.mp4"},
    "ua-16x9": {"w": 1920, "h": 1080, "min": 6, "max": 60, "end_card": True, "abr": "192k",
                "max_bytes": 30 * 1000 * 1000, "out": "ad-ua-16x9.mp4"},
    "app-preview": {"w": 886, "h": 1920, "min": 15, "max": 30, "end_card": False, "abr": "256k",
                    "max_bytes": 500 * 1024 * 1024, "store": True, "out": "app-preview-886x1920.mp4"},
    # Google Play's preview video is a YouTube link; only its first 30 s autoplay, muted.
    "play-promo": {"w": 1080, "h": 1920, "min": 15, "max": 30, "end_card": True, "no_cta": True,
                   "abr": "256k", "store": True, "out": "play-promo-9x16.mp4"},
    # Trailers: the music leads, so it stays full-range and loud; the game sits under it.
    "trailer": {"w": 1920, "h": 1080, "min": 45, "max": 120, "end_card": True, "abr": "320k",
                "bgm_volume": 0.9, "bgm_lowpass": None, "bgm_fade_out": 2.0, "out": "trailer-16x9.mp4"},
    "trailer-9x16": {"w": 1080, "h": 1920, "min": 30, "max": 60, "end_card": True, "abr": "320k",
                     "bgm_volume": 0.9, "bgm_lowpass": None, "bgm_fade_out": 2.0, "out": "trailer-9x16.mp4"},
}
AD_PROFILES = ["ua", "app-preview", "play-promo"]  # a storyboard without top-level "profiles" ("ua" = every ua*)
# pick() falls back along these: a ua-1x1 shot uses caption_ua, a Play video uses caption_app_preview.
PICK_FALLBACK = {"ua-1x1": ["ua"], "ua-4x5": ["ua"], "ua-16x9": ["ua"], "play-promo": ["app-preview"]}
# Network sweet spots for a UA cut's length (Meta, TikTok, ironSource, Snapchat, Unity guidance).
NETWORK_LENGTHS = [("Meta", 15, 30), ("TikTok", 21, 34), ("ironSource", 25, 30), ("Snapchat", 0, 8),
                   ("Unity", 0, 60)]
AUDIO_DEFAULTS = {"bgm_volume": 0.45, "bgm_lowpass": 4000, "bgm_fade_out": 1.5}
LAYOUTS = ("fit", "fill", "panel", "grid")
HUASHU = Path(os.environ.get("HUASHU_DESIGN_DIR", Path.home() / ".claude/skills/huashu-design"))
DEFAULT_COLORS = {"bg": "#14102a", "fg": "#ffffff", "accent": "#ffcc33", "stroke": "#000000"}
# Same list as recorder.py: rendered ads, like the takes, never go to GitHub.
MEDIA_IGNORE = ["*.mp4", "*.mov", "*.m4v", "*.webm", "*.mkv", "takes/", "shots/", "sheets/", ".build-*/"]


def die(msg):
    sys.exit(f"✗ {msg}")


def ignore_media(folder):
    gi = Path(folder) / ".gitignore"
    text = gi.read_text() if gi.exists() else ""
    missing = [p for p in MEDIA_IGNORE if p not in text.splitlines()]
    if missing:
        head = "" if text else "# game-ad-video: videos and raw footage stay on this machine, never in git\n"
        sep = "\n" if text and not text.endswith("\n") else ""
        gi.write_text(text + sep + head + "".join(p + "\n" for p in missing))


def git_ignored(path):
    """True/False inside a git work tree, None outside one (or without git)."""
    if not shutil.which("git"):
        return None
    p = Path(path).resolve()
    r = subprocess.run(["git", "-C", str(p.parent), "check-ignore", "-q", p.name], capture_output=True)
    return None if r.returncode == 128 else r.returncode == 0


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                          str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def has_audio(path):
    return any(s["codec_type"] == "audio" for s in probe(path)["streams"])


def video_size(path):
    v = next(s for s in probe(path)["streams"] if s["codec_type"] == "video")
    return v["width"], v["height"]


def frames(s):
    """Seconds rounded to whole frames. Segments are cut in frames, so the timeline is too;
    otherwise every segment's rounding adds up and the cuts drift off the beat."""
    return round(s * FPS) / FPS


# ---------------------------------------------------------------- storyboard model

def load_ad(path, variant=None):
    path = Path(path).resolve()
    ad = json.loads(path.read_text())
    ad["_dir"] = path.parent
    ad.setdefault("game", {})
    ad["game"]["colors"] = {**DEFAULT_COLORS, **ad["game"].get("colors", {})}
    ad["_variant"] = None
    if variant:
        apply_variants(ad, variant)
    return ad


def apply_variants(ad, names):
    """`variants.<name>` rewrites the storyboard for one cut. `shots` maps a shot index to fields
    merged into that shot ({"drop": true} takes it out of every profile, so cue indices hold);
    `end_card`, `audio` and `music` merge. "hook-number,short" applies both in order, which is
    how a hook × length × language matrix is built from one storyboard."""
    table = ad.get("variants", {})
    for name in names.split(","):
        if name not in table:
            die(f"no variant {name!r} in the storyboard (have: {', '.join(table) or 'none'})")
        v = table[name]
        for idx, patch in v.get("shots", {}).items():
            if not 0 <= int(idx) < len(ad["shots"]):
                die(f"variant {name!r} patches shot {idx}, but there are {len(ad['shots'])} shots (0-based)")
            shot = ad["shots"][int(idx)]
            if patch.get("drop"):
                shot["profiles"] = []
            else:
                shot.update(patch)
        for key in ("end_card", "audio", "music"):
            if key in v:
                ad[key] = {**(ad.get(key) or {}), **v[key]}
    ad["_variant"] = names


def variant_name(path, ad):
    """ad-ua-9x16.mp4 → ad-ua-9x16-hook-number-short.mp4 for --variant hook-number,short."""
    v = (ad or {}).get("_variant")
    return Path(path).with_name(f"{Path(path).stem}-{v.replace(',', '-')}{Path(path).suffix}") if v else Path(path)


def resolve(ad, rel, kind=None):
    """Path relative to ad.json, else a huashu-design asset (kind: 'sfx' | 'bgm')."""
    if not rel:
        return None
    p = Path(rel).expanduser()
    p = p if p.is_absolute() else ad["_dir"] / p
    if p.exists():
        return p
    if kind == "sfx" and (HUASHU / "assets/sfx" / rel).exists():
        return HUASHU / "assets/sfx" / rel
    if kind == "bgm":
        for cand in (HUASHU / "assets" / rel, HUASHU / "assets" / f"bgm-{rel}.mp3"):
            if cand.exists():
                return cand
    die(f"{kind or 'file'} not found: {rel}")


def in_profile(item, profile, ad):
    wanted = item.get("profiles", ad.get("profiles", AD_PROFILES))
    return profile in wanted or (is_ua(profile) and "ua" in wanted)


def is_ua(profile):
    return profile == "ua" or profile.startswith("ua-")


def pick(item, key, profile):
    """`<key>_<profile>` (caption_app_preview, layout_trailer_9x16, zoom_trailer, …) overrides
    `key` for that profile; null drops it. Related profiles fall back (PICK_FALLBACK)."""
    for prof in [profile] + PICK_FALLBACK.get(profile, []):
        k = f"{key}_{prof.replace('-', '_')}"
        if k in item:
            return item[k]
    return item.get(key)


def layout_of(shot, profile):
    """fit | fill | panel | grid. panel needs a landscape frame, and so does a grid of 3: in a
    portrait or square profile a portrait take already fills it, so they fall back to fit (grid:
    its first take). A grid of 2 works in every frame: side by side, "Level 1 vs Level 50"."""
    lay = pick(shot, "layout", profile) or "fit"
    if lay not in LAYOUTS:
        die(f"unknown layout {lay!r} (use {', '.join(LAYOUTS)})")
    prof = PROFILES[profile]
    if prof["h"] >= prof["w"] and (lay == "panel" or lay == "grid" and len(shot.get("takes", [])) > 2):
        return "fit"
    return lay


def transition_of(item, profile):
    """The transition into an item; transition_app_preview: "fade" keeps a store video plain."""
    return pick(item, "transition", profile) or "cut"


def primary(shot):
    """(take, in) of a shot; a grid shot's first take stands in when it falls back to fit."""
    src = shot if "take" in shot else shot["takes"][0]
    return src["take"], src["in"]


def music(ad, profile):
    """music, or music_<profile> for that profile (a cut-down usually starts the track later)."""
    return pick(ad, "music", profile) or {}


def beat_grid(ad, profile):
    """(seconds per beat, offset of the first beat in trailer time) from music.bpm / beat0 /
    start (beat0 and start are seconds into the track), or None without music.bpm."""
    m = music(ad, profile)
    if not m.get("bpm"):
        return None
    spb = 60 / m["bpm"]
    # In (-spb/2, spb/2]: a start a hair after a downbeat must not count as a beat early.
    return spb, (m.get("beat0", 0) - m.get("start", 0) + spb / 2) % spb - spb / 2


def timeline(ad, profile):
    """[(kind, item, start, duration, transition_in)] for the profile, plus total length.

    kind is shot, card (an item with "card") or end. Times are whole frames. An item given in
    `beats` ends on the beat grid point nearest to `beats` beats after the previous item ends;
    its transition overlap is added on top, so the next cut stays on the grid."""
    items = [("card" if "card" in s else "shot", s) for s in ad["shots"] if in_profile(s, profile, ad)]
    ec = ad.get("end_card")
    if ec and in_profile(ec, profile, ad) and (PROFILES[profile]["end_card"] or "profiles" in ec):
        items.append(("end", ec))
    grid = beat_grid(ad, profile)
    out, t = [], 0.0
    for i, (kind, it) in enumerate(items):
        tr = 0.0 if i == 0 or transition_of(it, profile) == "cut" else frames(it.get("transition_s", 0.3))
        if "beats" in it:
            if not grid:
                die("an item uses `beats` but the storyboard has no music.bpm (run build_ad.py beats MUSIC)")
            spb, g = grid
            n = round((t + it["beats"] * spb - g) / spb)
            d = frames(g + n * spb) - t + tr
        elif kind == "shot" and "out" in it:
            d = frames((it["out"] - it["in"]) / it.get("speed", 1.0))
        elif kind == "shot" and "seconds" not in it:
            die(f"shot {i + 1} needs out, seconds or beats")
        else:
            d = frames(it.get("seconds", 2.5 if kind == "end" else 1.5))
        if d <= tr:
            die(f"item {i + 1} is {d:.2f}s, no longer than its {tr}s transition")
        t -= tr
        out.append((kind, it, t, d, tr))
        t += d
    return out, t


def landings(ad, profile):
    """Every cut after the first item: (index, time it lands, offset from the nearest beat, hard
    cut?). A fade lands when it completes; a hard cut lands where it is."""
    grid = beat_grid(ad, profile)
    tl, _ = timeline(ad, profile)
    out = []
    for i, (kind, it, start, d, tr) in enumerate(tl[1:], start=1):
        t = start + tr
        off = None
        if grid:
            spb, g = grid
            off = t - (g + round((t - g) / spb) * spb)
        out.append((i, t, off, tr == 0))
    return out


def hook_problems(ad, profile):
    """UA hook rules (Meta, Creatune): gameplay from the first frame, no logo or title card in
    the first 3 s. Returns (failures, warnings); the warning is the sound-off one: most people
    watch muted, so the first 3 s should carry a caption unless the motion explains itself."""
    if not is_ua(profile):
        return [], []
    tl, _ = timeline(ad, profile)
    fails, warns = [], []
    if tl and tl[0][0] != "shot":
        fails.append("the first item is a card: open on gameplay")
    early = [i + 1 for i, (kind, it, start, d, tr) in enumerate(tl) if kind == "card" and start < 3.0]
    if early and tl[0][0] == "shot":
        fails.append(f"card #{early[0]} starts before 3 s: logos and titles go on the end card")
    if not any(kind == "shot" and start < 3.0 and pick(it, "caption", profile)
               for kind, it, start, d, tr in tl):
        warns.append("no caption in the first 3 s: most viewers watch muted, so the hook must read "
                     "without sound (fine for a Satisfying cut whose motion explains itself)")
    return fails, warns


def take_length(ad, rel):
    """(width, height, duration) of a take, or None while it isn't recorded yet."""
    p = Path(rel).expanduser()
    p = p if p.is_absolute() else ad["_dir"] / p
    if not p.exists():
        return None
    info = probe(p)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    return v["width"], v["height"], float(info["format"]["duration"])


def storyboard(ad, profile):
    tl, total = timeline(ad, profile)
    prof, grid = PROFILES[profile], beat_grid(ad, profile)
    lands = {i: (t, off) for i, t, off, _ in landings(ad, profile)}
    rows = ["| # | time | framing | [CAMERA] move + motive | composition | key action | transition in | check frames |"
            + (" lands |" if grid else ""),
            "|---|---|---|---|---|---|---|---|" + ("---|" if grid else "")]
    warn = []
    for i, (kind, it, start, d, tr) in enumerate(tl):
        if kind == "shot":
            z = pick(it, "zoom", profile)
            if not z:
                cam = "static"
            elif z.get("from", 1) == z["to"]:
                cam = f"hold {z['to']}x crop on {z.get('anchor_label', z.get('anchor'))}"
            else:
                cam = f"push {z.get('from', 1)}→{z['to']}x on {z.get('anchor_label', z.get('anchor'))}"
            if z and z.get("punch"):
                cam += f" · punch ×{len(z['punch'])}"
            lay, asked = layout_of(it, profile), pick(it, "layout", profile) or "fit"
            if lay != "fit":
                cam = f"{lay}{' ' + it.get('side', 'left') if lay == 'panel' else ''} · {cam}"
            elif asked != "fit":
                cam += f" · ({asked} → fit in portrait)"
            framing = it.get("framing", f"{z['to']}x" if z else "1x")
            comp = it.get("composition", (pick(it, "caption", profile) or {}).get("text", ""))
            srcs = it["takes"] if lay == "grid" else [{**it, "take": primary(it)[0], "in": primary(it)[1]}]
            taps = sum(len(touch_events(ad, src, it, d, it.get("speed", 1.0))) for src in srcs)
            if taps:
                cam += f" · {taps} touch{'es' if taps > 1 else ''}"
            elif any(src.get("touches", it.get("touches")) and take_length(ad, src["take"]) for src in srcs):
                warn.append(f"⚠ #{i + 1} asks for touches, but its take logs no inputs in that stretch "
                            "(record it with this recorder, or list them: touches: [{t, at, to?, ms?}])")
            cap = pick(it, "caption", profile)
            if cap and cap.get("text"):
                need = max(1.0, len(cap["text"].replace("*", "")) / 15)
                if d < need:
                    warn.append(f"⚠ #{i + 1} caption is on screen {d:.1f}s; \"{cap['text']}\" needs ~{need:.1f}s "
                                "to read (Apple: long enough to read)")
            for src in srcs:
                info = take_length(ad, src["take"])
                if not info:
                    continue
                over = src["in"] + d * it.get("speed", 1.0) - info[2]
                if over > 0.05:
                    warn.append(f"⚠ #{i + 1} runs {over:.2f}s past the end of {src['take']} (the last frame freezes)")
                if lay == "fill":
                    up = max(prof["w"] / info[0], prof["h"] / info[1]) * (z["to"] if z else 1)
                    if up > 2.0:
                        warn.append(f"⚠ #{i + 1} fill blows the take up {up:.1f}x (soft past 2x)")
        elif kind == "card":
            c = it["card"]
            cam, framing = "static, slow settle", f"card {c.get('style', 'feature')}"
            comp = it.get("composition", c.get("text", "logo" if c.get("style") == "logo" else ""))
        else:
            cam, framing, comp = "static, slow settle", "end card", it.get("headline", "")
        why = it.get("why", "")
        checks = " / ".join(f"f{int((start + c) * FPS)}" for c in it.get("check_at", []))
        trans = transition_of(it, profile) + (f" {tr}s" if tr else "")
        row = (f"| {i + 1} | {start:.1f}–{start + d:.1f}s | {framing} | {cam}"
               f"{' · ' + why if why else ''} | {comp} | {it.get('action', '')} | {trans} | {checks} |")
        if grid:
            spb, g = grid
            if i == 0:
                row += " start |"
            else:
                t, off = lands[i]
                n = round((t - g) / spb)
                row += f" {n // 4 + 1}:{n % 4 + 1}{f' ⚠{off:+.2f}s' if abs(off) > 1.01 / FPS else ''} |"
                if abs(off) > 1.01 / FPS:
                    warn.append(f"⚠ #{i + 1} lands {off:+.2f}s off the beat (give it `beats`, or move it)")
        rows.append(row)
    rows.append(f"\n{profile}{' · variant ' + ad['_variant'] if ad.get('_variant') else ''}: "
                f"{total:.1f}s, {len(tl)} shots, "
                f"{int(total * FPS)} frames (allowed {PROFILES[profile]['min']}–{PROFILES[profile]['max']}s)")
    hook_fails, hook_warns = hook_problems(ad, profile)
    warn += [f"✗ hook: {m}" for m in hook_fails] + [f"⚠ {m}" for m in hook_warns]
    store_fails, store_warns = store_problems(ad, profile)
    warn += [f"✗ store: {m}" for m in store_fails] + [f"⚠ store: {m}" for m in store_warns]
    bug = pick(ad, "brand_bug", profile)
    if bug and str(bug.get("pos", "top-left")).startswith("top"):
        until = bug.get("until", "end")
        until = total if until == "end" else float(until)
        def top_caption(it):
            cap = pick(it, "caption", profile)
            pos = cap.get("pos", "top") if cap else None
            return pos == "top" or isinstance(pos, (int, float)) and pos < 0.16
        crowd = [str(i + 1) for i, (kind, it, start, d, tr) in enumerate(tl)
                 if kind == "shot" and start < until and layout_of(it, profile) != "panel" and top_caption(it)]
        if crowd:
            warn.append(f"⚠ the brand bug ({bug.get('pos', 'top-left')}) shares the top edge with the captions of "
                        f"#{', #'.join(crowd)}: look at their check frames; move one, or end the bug sooner "
                        "(brand_bug.until)")
    if is_ua(profile):
        cuts = sum(1 for kind, it, start, d, tr in tl[1:] if start + tr < 5.0)
        fits = " · ".join(f"{name} {lo}–{hi}s {'✓' if lo <= total <= hi else '✗'}" if lo else
                          f"{name} ≤{hi}s {'✓' if total <= hi else '✗'}" for name, lo, hi in NETWORK_LENGTHS)
        rows.append(f"pacing: {cuts} cut{'s' if cuts != 1 else ''} in the first 5 s (Google sees 2+ in "
                    f"successful app ads) · length fits: {fits}")
    if grid:
        on = sum(1 for _, _, off, hard in landings(ad, profile) if hard and abs(off) <= 1.01 / FPS)
        hard = sum(1 for *_, h in landings(ad, profile) if h)
        m = music(ad, profile)
        rows.append(f"music: {m['bpm']} BPM from {m.get('start', 0)}s · lands = bar:beat "
                    f"counted from music.start · hard cuts on the beat {on}/{hard}")
    return "\n".join(rows + warn)


# ---------------------------------------------------------------- HTML → PNG

def data_uri(path):
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if str(path).endswith((".ttf", ".otf")):
        mime = "font/ttf" if str(path).endswith(".ttf") else "font/otf"
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def font_css(ad):
    font = ad["game"].get("font")
    face = ""
    if font:
        face = f"@font-face{{font-family:GameFont;src:url({data_uri(resolve(ad, font))})}}"
    return face + "*{box-sizing:border-box}body{margin:0;font-family:GameFont,Inter,Lato,'Noto Sans',sans-serif}"


def rich(text, accent):
    """*word* → accent colour. Text is the agent's own copy, escaped for HTML."""
    import html
    parts = html.escape(text).split("*")
    return "".join(f"<span style='color:{accent}'>{p}</span>" if i % 2 else p for i, p in enumerate(parts))


def rich_words(text, accent, step=0.07, delay=0.0):
    """Like rich(), with every word its own span so the words can pop in one after another."""
    import html
    out, n = [], 0
    for i, part in enumerate(text.split("*")):
        for word in part.split():
            color = f"color:{accent};" if i % 2 else ""
            out.append(f"<span class=wd style='{color}animation-delay:{delay + n * step:.3f}s'>{html.escape(word)}</span>")
            n += 1
    return " ".join(out), n


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) >= 6 else (255, 255, 255)
    return f"rgba({r},{g},{b},{alpha})"


# Motion for text, as CSS keyframes. Renderer.frames() steps the animations frame by frame, so
# what lands in the video is exactly what Chrome draws: overshoot, stagger and all.
ANIM_CSS = """
@keyframes pop{0%{opacity:0;transform:scale(.5)}55%{opacity:1;transform:scale(1.08)}100%{opacity:1;transform:none}}
@keyframes rise{0%{opacity:0;transform:translateY(38%)}100%{opacity:1;transform:none}}
@keyframes slide{0%{opacity:0;transform:translateY(45%)}100%{opacity:1;transform:none}}
@keyframes wordpop{0%{opacity:0;transform:translateY(35%) scale(.7)}60%{opacity:1;transform:translateY(-5%) scale(1.06)}100%{opacity:1;transform:none}}
@keyframes fadein{0%{opacity:0}100%{opacity:1}}
.wd{display:inline-block;animation:wordpop .3s cubic-bezier(.2,.9,.3,1) both}
"""
CAPTION_ANIMS = ("fade", "pop", "slide", "words")
CARD_ANIMS = ("settle", "rise", "pop", "words")

class Renderer:
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        try:
            self.browser = self.pw.chromium.launch(channel="chrome")
        except Exception:
            self.browser = self.pw.chromium.launch()
        self.page = self.browser.new_page()
        return self

    def png(self, html, w, h, out, transparent=True):
        self.page.set_viewport_size({"width": w, "height": h})
        self.page.set_content(html, wait_until="load")
        self.page.evaluate("document.fonts.ready")
        self.page.screenshot(path=str(out), omit_background=transparent)
        return out

    def frames(self, html, w, h, pattern, n, transparent=True):
        """n frames of the page's CSS animations at 30 fps → pattern % i. Every animation is
        paused and set to the frame's time, so the frames are exact, not a screen recording."""
        self.page.set_viewport_size({"width": w, "height": h})
        self.page.set_content(html, wait_until="load")
        self.page.evaluate("document.fonts.ready")
        for i in range(n):
            self.page.evaluate("""t => { document.body.offsetHeight;
                document.getAnimations().forEach(a => { a.pause(); a.currentTime = t; }); }""", i * 1000 / FPS)
            self.page.screenshot(path=str(pattern) % i, omit_background=transparent)
        return pattern

    def __exit__(self, *exc):
        self.browser.close()
        self.pw.stop()


def caption_html(ad, cap, w, h, anim="fade"):
    """pos: top | center | bottom, or a number = top edge as a fraction of the height.
    plate (default on) puts a dark rounded plate behind the text: gameplay is always busy, and
    the game's own HUD usually sits exactly where a top caption goes. style "sticker" sets the
    text dark on an accent pill, tilted a little, like a TikTok sticker. anim: fade (ffmpeg fades
    the still), pop (scale in with a small overshoot), slide (rises in), words (word by word)."""
    c = ad["game"]["colors"]
    size = int(min(w, h) * cap.get("size", 0.074))
    p = cap.get("pos", "top")
    pos = (f"top:{int(h * p)}px" if isinstance(p, (int, float)) else
           {"top": f"top:{int(h * 0.11)}px", "center": f"top:{int(h * 0.42)}px",
            "bottom": f"bottom:{int(h * (0.22 if h > w else 0.1))}px"}[p])
    stroke = max(2, size // 14)
    sticker = cap.get("style") == "sticker"
    fg, accent = (c["bg"], c["bg"]) if sticker else (c["fg"], c["accent"])
    plate = (f"background:{c['accent'] if sticker else cap.get('plate_color', 'rgba(10,8,20,.62)')};"
             f"padding:{size // 4}px {size // 2}px;border-radius:{size // 3}px;"
             if cap.get("plate", True) or sticker else "")
    look = (f"box-shadow:0 {size // 10}px {size // 3}px rgba(0,0,0,.35);" if sticker else
            f"-webkit-text-stroke:{stroke}px {c['stroke']};paint-order:stroke fill;"
            f"text-shadow:0 {stroke}px {stroke * 3}px rgba(0,0,0,.45);")
    if anim == "words":
        body, _ = rich_words(cap["text"], accent)
        motion = "animation:fadein .12s ease-out both;"
    else:
        body = rich(cap["text"], accent)
        motion = {"pop": "animation:pop .38s cubic-bezier(.2,.9,.3,1) both;",
                  "slide": "animation:slide .32s cubic-bezier(.2,.8,.2,1) both;"}.get(anim, "")
    wrap_rot = "transform:rotate(-2.5deg);" if sticker else ""
    return f"""<html><head><style>{font_css(ad)}{ANIM_CSS}
.w{{position:absolute;left:6%;right:6%;{pos};text-align:center;{wrap_rot}}}
.c{{display:inline-block;{plate}color:{fg};font-size:{size}px;
font-weight:900;line-height:1.08;letter-spacing:-.01em;text-wrap:balance;{look}{motion}}}</style></head>
<body style="background:transparent"><div class=w><div class=c>{body}</div></div></body></html>"""


def caption_frames(cap, anim):
    """How many frames a caption's intro takes (the last one is then held)."""
    if anim == "words":
        n = len(cap["text"].replace("*", " ").split())
        return int((0.07 * max(n - 1, 0) + 0.3) * FPS) + 2
    return {"pop": int(0.38 * FPS) + 2, "slide": int(0.32 * FPS) + 2}.get(anim, 1)


def logo_img(ad, w, h):
    """game.logo, a wordmark image, sized for a title card; None when the game has none."""
    logo = ad["game"].get("logo")
    if not logo:
        return None
    return f"<img src='{data_uri(resolve(ad, logo))}' class=l style='max-width:{int(w * 0.62)}px;max-height:{int(h * 0.3)}px'>"


def endcard_html(ad, ec, w, h, anim="rise", cta=True):
    """Sizes follow the short side, so a 16:9 card matches a 9:16 one. A trailer end card adds
    `date` ("Out now", "Coming 2027") and `platforms` as plain text chips: no store badge art.
    anim "rise" (default): the icon pops, the lines rise in one after another, then the CTA
    pulses; "none" is the still card. Store videos (cta=False) never show a CTA."""
    c, g, m = ad["game"]["colors"], ad["game"], min(w, h)
    icon = resolve(ad, ec.get("icon") or g.get("icon"))
    isz = int(m * (0.34 if h > w else 0.24))
    gap = int(h * 0.025) if h > w else int(m * 0.025)
    icon_tag = f"<img src='{data_uri(icon)}' class=i>" if icon else ""
    name = f"<div class=n>{rich(ec.get('headline', g.get('name', '')), c['accent'])}</div>"
    logo = logo_img(ad, w, h) if ec.get("logo", True) else None
    head = logo or icon_tag + name
    cta = f"<div class=b>{rich(ec['cta'], c['bg'])}</div>" if ec.get("cta") and cta else ""
    sub = f"<div class=s>{rich(ec['subline'], c['accent'])}</div>" if ec.get("subline") else ""
    date = f"<div class=d>{rich(ec['date'], c['accent'])}</div>" if ec.get("date") else ""
    plats = "".join(f"<span>{rich(p, c['accent'])}</span>" for p in ec.get("platforms", []))
    plats = f"<div class=p>{plats}</div>" if plats else ""
    motion = "" if anim == "none" else f"""
.i,.l{{animation:pop .45s cubic-bezier(.2,.9,.3,1) both}}
.n{{animation:rise .45s .08s cubic-bezier(.2,.8,.2,1) both}}
.s{{animation:rise .45s .16s cubic-bezier(.2,.8,.2,1) both}}
.d{{animation:rise .45s .22s cubic-bezier(.2,.8,.2,1) both}}
.p{{animation:rise .45s .28s cubic-bezier(.2,.8,.2,1) both}}
.b{{animation:pop .45s .34s cubic-bezier(.2,.9,.3,1) both,pulse 1.1s .95s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{transform:scale(1);box-shadow:0 0 0 0 {rgba(c['accent'], .55)}}}
50%{{transform:scale(1.06);box-shadow:0 0 0 {int(m * 0.025)}px {rgba(c['accent'], 0)}}}}}"""
    return f"""<html><head><style>{font_css(ad)}{ANIM_CSS}
body{{width:{w}px;height:{h}px;display:flex;flex-direction:column;align-items:center;justify-content:center;
gap:{gap}px;color:{c['fg']};background:radial-gradient(120% 80% at 50% 38%,{c.get('bg2', c['bg'])},{c['bg']})}}
.i{{width:{isz}px;height:{isz}px;border-radius:22%;box-shadow:0 {int(m * .03)}px {int(m * .08)}px rgba(0,0,0,.45)}}
.n{{font-size:{int(m * 0.105)}px;font-weight:900;letter-spacing:-.02em;text-align:center;padding:0 6%}}
.s{{font-size:{int(m * 0.045)}px;opacity:.85;text-align:center;padding:0 10%}}
.d{{font-size:{int(m * 0.05)}px;font-weight:800;letter-spacing:.04em;text-transform:uppercase}}
.p{{display:flex;flex-wrap:wrap;justify-content:center;gap:{int(m * 0.015)}px;padding:0 8%}}
.p span{{font-size:{int(m * 0.032)}px;padding:{int(m * 0.008)}px {int(m * 0.022)}px;border:{max(2, m // 360)}px solid rgba(255,255,255,.45);border-radius:999px}}
.b{{margin-top:{int(h * 0.02) if h > w else int(m * 0.036)}px;background:{c['accent']};color:{c['bg']};font-weight:900;font-size:{int(m * 0.055)}px;
padding:{int(m * 0.03)}px {int(m * 0.09)}px;border-radius:999px}}{motion}</style></head>
<body>{head}{sub}{date}{plats}{cta}</body></html>"""


def endcard_frames(d, anim):
    """Frames to draw for an end card: all of it while it animates (the CTA keeps pulsing), up
    to a pulse rest point before 6 s; the last frame is then held."""
    if anim == "none":
        return 1
    t = d if d <= 6.0 else 0.95 + int((6.0 - 0.95) / 1.1) * 1.1
    return max(int(round(t * FPS)), 1)


def card_html(ad, card, w, h, bg=None):
    """A full-frame text card: style title (big), feature (a verb or two) or logo. The background
    is the game's gradient, or `bg` (a still from a take), blurred and darkened. anim: rise
    (default: the line rises in, `sub` after it), pop, words (word by word), settle (still)."""
    c, g, m = ad["game"]["colors"], ad["game"], min(w, h)
    style = card.get("style", "feature")
    anim = card.get("anim", "rise")
    if style == "logo":
        icon = resolve(ad, g.get("icon")) if g.get("icon") else None
        body = logo_img(ad, w, h) or (
            (f"<img src='{data_uri(icon)}' class=i>" if icon else "")
            + f"<div class=t style='font-size:{int(m * 0.12)}px'>{rich(g.get('name', ''), c['accent'])}</div>")
    else:
        size = int(m * card.get("size", 0.12 if style == "title" else 0.09))
        text = rich_words(card.get("text", ""), c["accent"])[0] if anim == "words" else rich(card.get("text", ""), c["accent"])
        body = f"<div class=t style='font-size:{size}px'>{text}</div>"
    if card.get("sub"):
        body += f"<div class=s>{rich(card['sub'], c['accent'])}</div>"
    bg_tag = f"<img class=bg src='{data_uri(bg)}'>" if bg else ""
    motion = {"rise": ".t{animation:rise .5s cubic-bezier(.2,.8,.2,1) both}",
              "pop": ".t{animation:pop .45s cubic-bezier(.2,.9,.3,1) both}",
              "words": ""}.get(anim, "")
    if anim != "settle":
        motion += (".s{animation:rise .5s .15s cubic-bezier(.2,.8,.2,1) both}"
                   ".i,.l{animation:pop .5s cubic-bezier(.2,.9,.3,1) both}")
    return f"""<html><head><style>{font_css(ad)}{ANIM_CSS}
body{{width:{w}px;height:{h}px;position:relative;overflow:hidden;display:flex;flex-direction:column;
align-items:center;justify-content:center;gap:{int(m * 0.03)}px;color:{c['fg']};
background:radial-gradient(120% 90% at 50% 42%,{c.get('bg2', c['bg'])},{c['bg']})}}
.bg{{position:absolute;left:-6%;top:-6%;width:112%;height:112%;object-fit:cover;filter:blur({int(m * 0.03)}px) brightness(.4)}}
.t,.s,.i,.l{{position:relative}}
.t{{font-weight:900;letter-spacing:-.02em;line-height:1.05;text-align:center;padding:0 8%;text-wrap:balance;
text-shadow:0 {max(2, m // 200)}px {m // 50}px rgba(0,0,0,.45)}}
.s{{font-size:{int(m * 0.042)}px;opacity:.85;text-align:center;padding:0 10%}}
.i{{width:{int(m * 0.24)}px;height:{int(m * 0.24)}px;border-radius:22%;box-shadow:0 {int(m * .03)}px {int(m * .08)}px rgba(0,0,0,.45)}}
{motion}</style></head><body>{bg_tag}{body}</body></html>"""


def card_frames(card):
    anim = card.get("anim", "rise")
    if anim == "settle":
        return 1
    end = 0.65 if card.get("sub") else 0.5
    if anim == "words":
        end = max(end, 0.07 * max(len(card.get("text", "").replace("*", " ").split()) - 1, 0) + 0.3)
    return int(end * FPS) + 2


def stage_geometry(n, iw, ih, w, h, side="left", top_caption=False):
    """Rectangles (x, y, pw, ph) for n takes standing side by side on a w×h stage, plus the free
    box (x0, x1) for a panel's text. One take: ~88% of the height, centred in its half. A grid
    with a top caption sits lower and a little smaller, so the caption clears the panels."""
    ph = h * (0.88 if n == 1 else 0.78 if top_caption else 0.84)
    pw = ph * iw / ih
    gap = w * 0.025
    limit = w * (0.5 if n == 1 else 0.92)
    total = n * pw + (n - 1) * gap
    if total > limit:
        k = limit / total
        ph, pw, gap = ph * k, pw * k, gap * k
    pw, ph = int(pw) // 2 * 2, int(ph) // 2 * 2
    # Landscape: a top caption pushes the row down. Portrait: two panels are short enough that
    # centring them leaves the top free, and keeps them clear of TikTok's bottom 20%.
    y = int(h * 0.95) - ph if top_caption and w > h else (h - ph) // 2
    if n == 1:
        x = int(w * (0.3 if side == "left" else 0.7) - pw / 2) // 2 * 2
        box = (int(w * 0.53), int(w * 0.95)) if side == "left" else (int(w * 0.05), int(w * 0.47))
        return [(x, y, pw, ph)], box
    x0 = (w - (n * pw + (n - 1) * gap)) / 2
    return [(int(x0 + i * (pw + gap)) // 2 * 2, y, pw, ph) for i in range(n)], None


def stage_html(ad, w, h, rects, radius, cap=None, box=None, labels=None):
    """Background for panel / grid: the game's gradient, a soft shadow where each take goes and,
    for a panel, the caption as large text in the free half (`caption.sub` under it). A grid's
    `labels` sit above its panels ("Level 1", "Level 50"; "Noob", "Pro")."""
    c, m = ad["game"]["colors"], min(w, h)
    shadows = "".join(f"<div class=p style='left:{x}px;top:{y}px;width:{pw}px;height:{ph}px'></div>"
                      for x, y, pw, ph in rects)
    text = ""
    if cap and box:
        size = int(m * cap.get("size", 0.1))
        sub = f"<div class=s>{rich(cap['sub'], c['accent'])}</div>" if cap.get("sub") else ""
        text = (f"<div class=x style='left:{box[0]}px;width:{box[1] - box[0]}px'>"
                f"<div class=t style='font-size:{size}px'>{rich(cap['text'], c['accent'])}</div>{sub}</div>")
    lsize = int(m * 0.045)
    tags = "".join(f"<div class=lb style='left:{x}px;width:{pw}px;top:{y - int(lsize * 2.1)}px'>"
                   f"<span>{rich(lab, c['accent'])}</span></div>"
                   for (x, y, pw, ph), lab in zip(rects, labels or []) if lab)
    return f"""<html><head><style>{font_css(ad)}
body{{width:{w}px;height:{h}px;position:relative;overflow:hidden;color:{c['fg']};
background:radial-gradient(110% 90% at 50% 45%,{c.get('bg2', c['bg'])},{c['bg']})}}
.p{{position:absolute;border-radius:{radius}px;background:#000;box-shadow:0 {int(m * .02)}px {int(m * .07)}px rgba(0,0,0,.6)}}
.x{{position:absolute;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;align-items:center;
gap:{int(m * 0.025)}px;text-align:center}}
.t{{font-weight:900;letter-spacing:-.02em;line-height:1.05;text-wrap:balance;text-shadow:0 {max(2, m // 200)}px {m // 50}px rgba(0,0,0,.45)}}
.s{{font-size:{int(m * 0.042)}px;opacity:.85}}
.lb{{position:absolute;text-align:center}}
.lb span{{display:inline-block;font-size:{lsize}px;font-weight:900;padding:{lsize // 5}px {lsize // 2}px;
border-radius:999px;background:rgba(10,8,20,.7)}}</style></head><body>{shadows}{text}{tags}</body></html>"""


def vs_html(ad, w, h, rects):
    """A round "VS" badge over the gap between two grid panels (a layer above the footage)."""
    c, m = ad["game"]["colors"], min(w, h)
    (x0, y0, pw, ph), (x1, *_), = rects[:2]
    r = int(m * 0.065)
    cx, cy = (x0 + pw + x1) // 2, y0 + ph // 2
    return f"""<html><head><style>{font_css(ad)}
.v{{position:absolute;left:{cx - r}px;top:{cy - r}px;width:{2 * r}px;height:{2 * r}px;border-radius:50%;
display:flex;align-items:center;justify-content:center;background:{c['accent']};color:{c['bg']};
font-weight:900;font-size:{int(r * 0.8)}px;letter-spacing:-.03em;box-shadow:0 {r // 6}px {r // 2}px rgba(0,0,0,.5);
border:{max(3, r // 12)}px solid {c['fg']}}}</style></head><body style="background:transparent"><div class=v>VS</div></body></html>"""


def mask_html(pw, ph, radius):
    return (f"<html><body style='margin:0;background:#000'><div style='width:{pw}px;height:{ph}px;"
            f"border-radius:{radius}px;background:#fff'></div></body></html>")


# Touch indicators, sized from the take's width: a ring that ripples out where a finger lands,
# a fingertip dot that travels with a drag (or stays for a hold), or a drawn hand pointing.
TOUCH_RING, TOUCH_DOT, TOUCH_HAND = 0.24, 0.075, 0.17
# The hand's fingertip, as fractions of its square image (see hand_html's path).
HAND_TIP = (0.38, 0.06)


def ripple_html(size):
    b = max(3, size // 28)
    d = int(size * TOUCH_DOT / TOUCH_RING)
    return f"""<html><head><style>
body{{margin:0;width:{size}px;height:{size}px;background:transparent;position:relative;overflow:hidden}}
.r{{position:absolute;left:{b}px;top:{b}px;width:{size - 2 * b}px;height:{size - 2 * b}px;box-sizing:border-box;
border-radius:50%;border:{b}px solid rgba(255,255,255,.95);box-shadow:0 0 {b * 2}px rgba(255,255,255,.6);
animation:ring .45s cubic-bezier(.2,.7,.3,1) both}}
.d{{position:absolute;left:{(size - d) // 2}px;top:{(size - d) // 2}px;width:{d}px;height:{d}px;border-radius:50%;
background:rgba(255,255,255,.88);box-shadow:0 0 0 {b}px rgba(0,0,0,.22);animation:dot .45s ease-out both}}
@keyframes ring{{0%{{transform:scale(.25);opacity:.95}}100%{{transform:scale(1);opacity:0}}}}
@keyframes dot{{0%{{transform:scale(.6);opacity:0}}25%{{transform:scale(1);opacity:1}}100%{{transform:scale(.9);opacity:0}}}}
</style></head><body><div class=r></div><div class=d></div></body></html>"""


def dot_html(size):
    b = max(3, size // 9)
    return f"""<html><body style="margin:0;background:transparent"><div style="width:{size - 2 * b}px;height:{size - 2 * b}px;
margin:{b}px;border-radius:50%;background:rgba(255,255,255,.88);box-shadow:0 0 0 {b // 2}px rgba(0,0,0,.25),0 0 {b * 2}px rgba(255,255,255,.55)"></div></body></html>"""


def hand_html(size):
    return f"""<html><body style="margin:0;background:transparent">
<svg width="{size}" height="{size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
<path d="M38 6c-5 0-9 4-9 9v38l-6-6c-4-4-10-4-13 0s-3 9 0 13l20 22c5 6 12 9 20 9h12c13 0 23-10 23-23V50
c0-5-4-9-9-9-2 0-4 1-5 2 0-5-4-8-9-8-3 0-5 1-6 3-1-4-4-6-8-6-2 0-4 1-5 2V15c0-5-4-9-9-9z"
fill="#fff" stroke="#151515" stroke-width="4.5" stroke-linejoin="round"/></svg></body></html>"""


def bug_html(ad, w, h, bug):
    """A small brand "bug": icon + name in a corner, so the game is named in the first seconds
    (Meta, Google ABCD) without spending the hook on a logo card."""
    c, g, m = ad["game"]["colors"], ad["game"], min(w, h)
    icon = resolve(ad, g.get("icon")) if g.get("icon") else None
    isz, fs = int(m * 0.065), int(m * 0.036)
    pos = bug.get("pos", "top-left")
    css = ({"top-left": f"left:{int(w * 0.04)}px;top:{int(h * 0.045)}px",
            "top-right": f"right:{int(w * 0.04)}px;top:{int(h * 0.045)}px",
            "bottom-left": f"left:{int(w * 0.04)}px;bottom:{int(h * 0.06)}px",
            "bottom-right": f"right:{int(w * 0.04)}px;bottom:{int(h * 0.06)}px"}.get(pos)
           if isinstance(pos, str) else f"left:{int(w * pos[0])}px;top:{int(h * pos[1])}px")
    img = f"<img src='{data_uri(icon)}' style='width:{isz}px;height:{isz}px;border-radius:22%'>" if icon else ""
    return f"""<html><head><style>{font_css(ad)}</style></head><body style="background:transparent">
<div style="position:absolute;{css};display:flex;align-items:center;gap:{fs // 2}px;padding:{fs // 4}px {fs // 2}px {fs // 4}px {fs // 4}px;
border-radius:999px;background:rgba(10,8,20,.55);color:{c['fg']};font-size:{fs}px;font-weight:800">{img}<span>{rich(g.get('name', ''), c['accent'])}</span></div></body></html>"""


def thumb_html(ad, frame, fw, fh, w, h, text, sub=None):
    """A video thumbnail (YouTube, landing page): the frame blurred behind, the frame itself on
    a card (portrait takes) or full-bleed (landscape), big text and the game's icon + name. A
    landscape thumbnail puts the text left of the card; a portrait one puts it above."""
    c, g, m = ad["game"]["colors"], ad["game"], min(w, h)
    icon = resolve(ad, g.get("icon")) if g.get("icon") else None
    portrait_take, tall = fh > fw, h > w
    card_h = int(h * (0.58 if tall else 0.86))
    card_w = int(card_h * fw / fh)
    card_pos = (f"left:{(w - card_w) // 2}px;bottom:{int(h * 0.04)}px" if tall else
                f"right:{int(w * 0.07)}px;top:{(h - card_h) // 2}px")
    shot = (f"<img class=k src='{data_uri(frame)}' style='width:{card_w}px;height:{card_h}px;{card_pos}'>"
            if portrait_take else "")
    text_pos = (f"left:{int(w * 0.07)}px;right:{int(w * 0.07)}px;top:{int(h * 0.05)}px;height:{int(h * 0.33)}px" if tall else
                f"left:{int(w * 0.06)}px;top:0;bottom:0;width:{int(w * (0.55 if portrait_take else 0.6))}px")
    shade = (f"linear-gradient(180deg,{rgba(c['bg'], .95)} 0%,{rgba(c['bg'], .6)} 40%,{rgba(c['bg'], 0)} 70%)" if tall else
             f"linear-gradient(90deg,{rgba(c['bg'], .92)} 0%,{rgba(c['bg'], .55)} 45%,{rgba(c['bg'], 0)} 75%)")
    img = f"<img src='{data_uri(icon)}'>" if icon else ""
    brand = f"<div class=br>{img}<span>{rich(g.get('name', ''), c['accent'])}</span></div>"
    subline = f"<div class=s>{rich(sub, c['accent'])}</div>" if sub else ""
    return f"""<html><head><style>{font_css(ad)}
body{{width:{w}px;height:{h}px;position:relative;overflow:hidden;color:{c['fg']};background:{c['bg']}}}
.bgi{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
filter:{'blur(' + str(int(m * 0.03)) + 'px) brightness(.45)' if portrait_take else 'brightness(.8)'};transform:scale(1.08)}}
.sh{{position:absolute;inset:0;background:{shade}}}
.k{{position:absolute;border-radius:{int(card_w * 0.07)}px;object-fit:cover;
box-shadow:0 {int(m * .03)}px {int(m * .09)}px rgba(0,0,0,.6);transform:rotate(3deg)}}
.tx{{position:absolute;{text_pos};display:flex;flex-direction:column;justify-content:center;gap:{int(m * 0.03)}px}}
.t{{font-size:{int(m * 0.15)}px;font-weight:900;line-height:1;letter-spacing:-.03em;text-wrap:balance;
-webkit-text-stroke:{max(2, m // 120)}px {c['stroke']};paint-order:stroke fill;text-shadow:0 {m // 80}px {m // 25}px rgba(0,0,0,.5)}}
.s{{font-size:{int(m * 0.055)}px;font-weight:700;opacity:.9}}
.br{{display:flex;align-items:center;gap:{int(m * 0.02)}px;font-size:{int(m * 0.05)}px;font-weight:800}}
.br img{{width:{int(m * 0.1)}px;height:{int(m * 0.1)}px;border-radius:22%;box-shadow:0 {m // 100}px {m // 30}px rgba(0,0,0,.5)}}
</style></head><body><img class=bgi src='{data_uri(frame)}'><div class=sh></div>{shot}
<div class=tx>{brand}<div class=t>{rich(text, c['accent'])}</div>{subline}</div></body></html>"""


# ---------------------------------------------------------------- render

def atempo_chain(speed):
    parts, s = [], speed
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


class Inputs:
    """ffmpeg inputs that hand out their indices, so a graph can grow optional layers."""

    def __init__(self):
        self.args, self.n = [], 0

    def add(self, *args):
        self.args += list(args)
        self.n += 1
        return self.n - 1


def look_filter(ad, profile):
    """`look` grades the footage a little ({"saturation": 1.1, "contrast": 1.05, "brightness":
    0.02}): dark games read badly in a feed (Voodoo). Store videos keep the true colours unless
    the storyboard sets look_app_preview / look_play_promo itself."""
    key = f"look_{profile.replace('-', '_')}"
    look = ad.get(key) if PROFILES[profile].get("store") else pick(ad, "look", profile)
    if not look:
        return ""
    return (f",eq=contrast={look.get('contrast', 1.0)}:brightness={look.get('brightness', 0.0)}"
            f":saturation={look.get('saturation', 1.0)}")


def zoom_chain(take, z):
    """The push-in (smoothstep from `from` to `to`, starting `at`, lasting `dur`) plus `punch`:
    quick 8 % bumps at the given shot seconds that settle back, for hits and beats."""
    if not z:
        return ""
    iw, ih = video_size(take)
    f, to = z.get("from", 1.0), z.get("to", z.get("from", 1.0))
    at, dur = z.get("at", 0.0), max(z.get("dur", 0.6), 0.04)
    ax, ay = z.get("anchor", [0.5, 0.5])
    p = f"clip((it-{at})/{dur},0,1)"
    zexpr = f"{f}+({to}-{f})*{p}*{p}*(3-2*{p})"
    amt = z.get("punch_amount", 0.08)
    for t in z.get("punch", []):
        zexpr += f"+{amt}*exp(-pow((it-{t})/0.07,2))"
    # zoompan rounds x/y to whole pixels: run it at 2x so the push stays smooth.
    return (f"scale={iw * 2}:{ih * 2},zoompan=z='{zexpr}':d=1:fps={FPS}:s={iw}x{ih}"
            f":x='clip({ax}*iw-iw/zoom/2,0,iw-iw/zoom)':y='clip({ay}*ih-ih/zoom/2,0,ih-ih/zoom)',")


def touch_events(ad, src, shot, d, speed):
    """Taps and swipes inside this stretch of a take, in shot time: [(t, kind, at, to, dur)],
    positions as fractions of the take's frame. From the shot's own `touches: [{t, at, to?, ms?}]`
    (take seconds), or with `touches: true` from the take's marks.json, where recorder.py logs
    every input. A swipe that doesn't move is a hold."""
    spec = src.get("touches", shot.get("touches"))
    if not spec:
        return []
    if spec is True:
        p = Path(src["take"]).expanduser()
        marks = (p if p.is_absolute() else ad["_dir"] / p).with_suffix(".marks.json")
        spec = json.loads(marks.read_text()).get("inputs", []) if marks.exists() else []
    t_in, span, out = src["in"], d * speed, []
    for e in spec:
        dur = e.get("ms", 0) / 1000
        if e["t"] + dur < t_in or e["t"] > t_in + span:
            continue
        kind = e.get("kind", "swipe" if "to" in e else "tap")
        out.append(((e["t"] - t_in) / speed, kind, e["at"], e.get("to", e["at"]), dur / speed))
    return out


def touch_assets(r, tmp, iw, style):
    """Ripple frames, the fingertip dot and the hand, drawn once per take width."""
    key = (iw, style)
    cache = r.__dict__.setdefault("touch_cache", {})
    if key not in cache:
        ring, dot, hand = (int(iw * f) // 2 * 2 for f in (TOUCH_RING, TOUCH_DOT, TOUCH_HAND))
        pat = tmp / f"ripple{iw}_%02d.png"
        r.frames(ripple_html(ring), ring, ring, pat, int(0.45 * FPS) + 1)
        cache[key] = {"ring": ring, "ripple": pat, "dot": dot, "hand": hand,
                      "dot_png": r.png(dot_html(dot), dot, dot, tmp / f"dot{iw}.png"),
                      "hand_png": r.png(hand_html(hand), hand, hand, tmp / f"hand{iw}.png")}
    return cache[key]


def touch_layers(inp, g, cur, events, iw, ih, a, style, d, tag):
    """Overlay the indicators on the raw take (before the push-in, so they zoom with it).
    Each tap or press gets a ripple; a drag moves the dot (or hand) along its path."""
    ripples = [e for e in events if e[0] >= -0.05]
    movers = [e for e in events if e[1] == "swipe" or style == "hand"]
    if ripples:
        k = inp.add("-framerate", FPS, "-i", a["ripple"])
        g.append(f"[{k}:v]format=rgba,split={len(ripples)}" + "".join(f"[{tag}r{j}]" for j in range(len(ripples))))
    if movers:
        png, size = (a["hand_png"], a["hand"]) if style == "hand" else (a["dot_png"], a["dot"])
        ox, oy = (size * HAND_TIP[0], size * HAND_TIP[1]) if style == "hand" else (size / 2, size / 2)
        k = inp.add("-framerate", FPS, "-loop", "1", "-t", d, "-i", png)
        g.append(f"[{k}:v]format=rgba,split={len(movers)}" + "".join(f"[{tag}m{j}]" for j in range(len(movers))))
    n = 0
    for j, (t, kind, at, to, dur) in enumerate(ripples):
        x, y = at[0] * iw - a["ring"] / 2, at[1] * ih - a["ring"] / 2
        g.append(f"[{tag}r{j}]setpts=PTS-STARTPTS+{max(t, 0):.4f}/TB[{tag}rr{j}];"
                 f"{cur}[{tag}rr{j}]overlay=x={x:.1f}:y={y:.1f}:eof_action=pass[{tag}t{n}]")
        cur, n = f"[{tag}t{n}]", n + 1
    for j, (t, kind, at, to, dur) in enumerate(movers):
        x1, y1, x2, y2 = at[0] * iw - ox, at[1] * ih - oy, to[0] * iw - ox, to[1] * ih - oy
        if kind == "tap":  # the hand comes in just before the tap and leaves after it
            win, xe, ye = f"between(t,{t - 0.18:.3f},{t + 0.32:.3f})", f"{x1:.1f}", f"{y1:.1f}"
        else:
            prog = f"clip((t-{t:.3f})/{max(dur, 0.01):.3f},0,1)"
            win = f"between(t,{t:.3f},{t + dur + 0.08:.3f})"
            xe, ye = f"{x1:.1f}+({x2 - x1:.1f})*{prog}", f"{y1:.1f}+({y2 - y1:.1f})*{prog}"
        g.append(f"{cur}[{tag}m{j}]overlay=x='{xe}':y='{ye}':enable='{win}'[{tag}t{n}]")
        cur, n = f"[{tag}t{n}]", n + 1
    return cur


def take_graph(inp, g, ad, r, tmp, k, take, src, shot, profile, d, label):
    """[k:v] → [label]: retime to 30 fps, `look`, touch indicators on the raw take, the push-in
    (with punches), then hold the last frame so a segment never comes up short (the encoder stops
    it at its frame count)."""
    speed = shot.get("speed", 1.0)
    g.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{speed},fps={FPS}{look_filter(ad, profile)}[{label}0]")
    cur = f"[{label}0]"
    events = touch_events(ad, src, shot, d, speed)
    if events:
        style = "ring" if PROFILES[profile].get("store") else pick(shot, "touch_style", profile) or \
            pick(ad, "touch_style", profile) or "ring"
        iw, ih = video_size(take)
        cur = touch_layers(inp, g, cur, events, iw, ih, touch_assets(r, tmp, iw, style), style, d, label)
    z = pick(shot, "zoom", profile) if "takes" not in shot or len(shot["takes"]) == 1 else None
    g.append(f"{cur}{zoom_chain(take, z)}tpad=stop_mode=clone:stop=-1[{label}]")


def take_audio(inp, shot, take, k, speed, d):
    """Audio graph for a shot: the take's own sound (input k), or added silence."""
    if has_audio(take) and not shot.get("mute"):
        return f"[{k}:a]asetpts=PTS-STARTPTS,{atempo_chain(speed)},aresample=48000,aformat=channel_layouts=stereo,apad[aout]"
    n = inp.add("-f", "lavfi", "-t", d, "-i", "anullsrc=r=48000:cl=stereo")
    return f"[{n}:a]anull[aout]"


def add_caption(inp, g, layer, vin, d):
    """layer: ("png", path) faded in by ffmpeg, or ("seq", pattern) of animated frames whose last
    frame overlay then holds."""
    if not layer:
        return vin
    kind, path = layer
    if kind == "png":
        k = inp.add("-loop", "1", "-t", d, "-i", path)
        g.append(f"[{k}:v]format=rgba,fade=in:st=0:d=0.18:alpha=1[cap];{vin}[cap]overlay=0:0[vcap]")
    else:
        k = inp.add("-framerate", FPS, "-i", path)
        g.append(f"[{k}:v]format=rgba[cap];{vin}[cap]overlay=0:0[vcap]")
    return "[vcap]"


def render_shot(ad, shot, d, prof, profile, layout, cap_layer, r, tmp, i, out):
    """fit: the take scaled into the frame over a blurred copy of itself. fill: the frame cut out
    of the take around fill_y (0 top … 1 bottom) and scaled up to cover it."""
    rel, t_in = primary(shot)
    take = resolve(ad, rel)
    src = shot if "take" in shot else shot["takes"][0]
    w, h, speed = prof["w"], prof["h"], shot.get("speed", 1.0)
    inp, g = Inputs(), []
    k = inp.add("-ss", t_in, "-t", d * speed, "-i", take)
    take_graph(inp, g, ad, r, tmp, k, take, src, shot, profile, d, "tk")
    if layout == "fill":
        fy = shot.get("fill_y", 0.5)
        g.append(f"[tk]scale={w}:{h}:force_original_aspect_ratio=increase,"
                 f"crop={w}:{h}:(iw-{w})/2:'clip({fy}*ih-{h}/2,0,ih-{h})',setsar=1[v0]")
    else:
        g.append(f"[tk]split[a][b];[b]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                 f"gblur=sigma=40,eq=brightness=-0.12[bg];[a]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
                 f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v0]")
    vout = add_caption(inp, g, cap_layer, "[v0]", d)
    a = take_audio(inp, shot, take, k, speed, d)
    encode_segment(inp.args, ";".join(g) + f";{a}", vout, d, out)


def render_staged(ad, shot, d, prof, profile, layout, r, tmp, i, cap_layer, out):
    """panel: one take as a rounded card on the game's gradient, the caption as big text beside
    it. grid: 2–3 takes (`takes: [{take, in}]`) side by side, with `labels` above them and an
    optional `vs` badge between two; a caption overlays as usual."""
    w, h, speed = prof["w"], prof["h"], shot.get("speed", 1.0)
    srcs = shot["takes"] if layout == "grid" else [{**shot, "take": primary(shot)[0], "in": primary(shot)[1]}]
    if layout == "grid" and not 2 <= len(srcs) <= 3:
        die(f"a grid shot takes 2–3 takes, got {len(srcs)}")
    takes = [resolve(ad, s["take"]) for s in srcs]
    n = len(takes)
    cap = pick(shot, "caption", profile)
    pos = (cap or {}).get("pos", "top")
    top = layout == "grid" and bool(cap) and (pos == "top" or isinstance(pos, (int, float)) and pos < 0.3)
    rects, box = stage_geometry(n, *video_size(takes[0]), w, h, shot.get("side", "left"), top)
    pw, ph = rects[0][2], rects[0][3]
    radius = int(pw * 0.06)
    bg = r.png(stage_html(ad, w, h, rects, radius, cap if layout == "panel" else None, box,
                          shot.get("labels") if layout == "grid" else None),
               w, h, tmp / f"stage{i:02d}.png", transparent=False)
    mask = r.png(mask_html(pw, ph, radius), pw, ph, tmp / f"mask{i:02d}.png", transparent=False)
    inp, g = Inputs(), []
    ks = [inp.add("-ss", src["in"], "-t", d * speed, "-i", take) for src, take in zip(srcs, takes)]
    # 30 fps stills: the stage is overlay's main input, so its rate is the segment's rate.
    kb = inp.add("-framerate", FPS, "-loop", "1", "-t", d, "-i", bg)
    km = inp.add("-framerate", FPS, "-loop", "1", "-t", d, "-i", mask)
    g.append(f"[{km}:v]format=gray,split={n}" + "".join(f"[m{j}]" for j in range(n)))
    g.append(f"[{kb}:v]format=rgba[o]")
    cur = "[o]"
    for j, (src, take) in enumerate(zip(srcs, takes)):
        take_graph(inp, g, ad, r, tmp, ks[j], take, src, shot, profile, d, f"tk{j}")
        g.append(f"[tk{j}]scale={pw}:{ph}:force_original_aspect_ratio=increase,crop={pw}:{ph},format=rgba[t{j}];"
                 f"[t{j}][m{j}]alphamerge[p{j}];{cur}[p{j}]overlay={rects[j][0]}:{rects[j][1]}[o{j}]")
        cur = f"[o{j}]"
    if layout == "grid" and shot.get("vs") and n == 2:
        kv = inp.add("-loop", "1", "-t", d, "-i", r.png(vs_html(ad, w, h, rects), w, h, tmp / f"vs{i:02d}.png"))
        g.append(f"{cur}[{kv}:v]overlay=0:0[ovs]")
        cur = "[ovs]"
    g.append(f"{cur}setsar=1[v0]")
    vout = add_caption(inp, g, cap_layer, "[v0]", d)
    a = take_audio(inp, shot, takes[0], ks[0], speed, d)
    encode_segment(inp.args, ";".join(g) + f";{a}", vout, d, out)


def render_still(d, prof, img, out, seq=False):
    """A card or the end card with a slow 1.06x → 1x settle, so it lands, not pops. img is one
    PNG, or with seq=True a pattern of animated frames whose last frame is held."""
    w, h = prof["w"], prof["h"]
    # -framerate: zoompan emits one frame per input frame, and a still loops at 25 fps by
    # default, which made every card (and the end card) a sixth shorter than its slot.
    src = ["-framerate", FPS, "-i", img] if seq else ["-framerate", FPS, "-loop", "1", "-t", d, "-i", img]
    args = src + ["-f", "lavfi", "-t", d, "-i", "anullsrc=r=48000:cl=stereo"]
    hold = "tpad=stop_mode=clone:stop=-1," if seq else ""
    v = (f"[0:v]{hold}scale={w * 2}:{h * 2},zoompan=z='1.06-0.06*clip(it/0.6,0,1)*(2-clip(it/0.6,0,1))':d=1:fps={FPS}"
         f":s={w}x{h}:x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2',setsar=1[v0]")
    encode_segment(args, f"{v};[1:a]anull[aout]", "[v0]", d, out)


def encode_segment(args, graph, vout, d, out):
    """Exactly round(d × 30) frames. Audio stays PCM until the final mix: AAC pads every
    segment to whole 1024-sample frames, and over a dozen joins the game sound drifts late."""
    n = round(d * FPS)
    graph += f";{vout}scale=out_range=tv,format=yuv420p[vtv]"
    ffmpeg(*args, "-filter_complex", graph, "-map", "[vtv]", "-map", "[aout]", "-frames:v", n,
           "-t", f"{n / FPS:.6f}", "-r", FPS, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-preset", "medium", "-crf", "17", "-color_range", "tv", "-c:a", "pcm_s16le", "-ar", "48000",
           "-ac", "2", out)


def join(segments, out, fade_in=0, bug=None):
    """segments: [(path, duration, transition, transition_s)]; cut = concat, else xfade.
    fade_in > 0 opens the whole video from black. bug = (png, until): the brand bug on top from
    the start until `until` seconds (when the end card takes over)."""
    args, graph = [], []
    for i, (p, *_) in enumerate(segments):
        args += ["-i", p]
        # Timestamps rebuilt from frame and sample counts: a container that rounds them (mkv
        # keeps milliseconds) makes xfade start a frame late and every later cut slip. AVTB
        # because xfade refuses inputs whose timebases differ (concat output vs. a segment).
        graph.append(f"[{i}:v]settb=AVTB,setpts=N/{FPS}/TB[i{i}];[{i}:a]asetpts=N/SR/TB[s{i}]")
    cur_v, cur_a, cur_d = "[i0]", "[s0]", segments[0][1]
    for i, (_, d, tr, td) in enumerate(segments[1:], start=1):
        nv, na = f"[v{i}]", f"[a{i}]"
        if tr == "cut" or td <= 0:
            graph.append(f"{cur_v}{cur_a}[i{i}][s{i}]concat=n=2:v=1:a=1[c{i}]{na};[c{i}]settb=AVTB{nv}")
            cur_d += d
        else:
            graph.append(f"{cur_v}[i{i}]xfade=transition={tr}:duration={td}:offset={cur_d - td:.6f}{nv}")
            graph.append(f"{cur_a}[s{i}]acrossfade=d={td}{na}")
            cur_d += d - td
        cur_v, cur_a = nv, na
    if len(segments) > 1 or fade_in or bug:
        fade = f"fade=t=in:st=0:d={fade_in}," if fade_in else ""
        # A closing xfade can hold one extra frame past the end; the timeline is the length.
        graph.append(f"{cur_v}{fade}trim=end_frame={round(cur_d * FPS)}[vt]")
        cur_v = "[vt]"
        if bug:
            # -t: overlay runs as long as either input has frames, so a looped still must end.
            args += ["-loop", "1", "-t", f"{cur_d:.3f}", "-i", bug[0]]
            graph.append(f"[{len(segments)}:v]format=rgba,fade=in:st=0.15:d=0.25:alpha=1[bug];"
                         f"{cur_v}[bug]overlay=0:0:enable='lt(t,{bug[1]:.3f})':shortest=1[vb]")
            cur_v = "[vb]"
        graph.append(f"{cur_v}scale=out_range=tv,format=yuv420p[vtv]")
        graph.append(f"{cur_a}atrim=end={cur_d:.6f}[aj]")
        cur_a = "[aj]"
        ffmpeg(*args, "-filter_complex", ";".join(graph), "-map", "[vtv]", "-map", cur_a,
               "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "17", "-r", FPS,
               "-color_range", "tv", "-c:a", "pcm_s16le", out)
    else:
        shutil.copy(segments[0][0], out)
    return cur_d


def landing_of(tl, item):
    """When an item lands (fully on screen) in the timeline, or None if it isn't in it."""
    for kind, it, start, d, tr in tl:
        if it is item:
            return start + tr
    return None


def music_gain(ad, profile, tl):
    """music.stops silence the music (only the music) for a moment: {"before": shot index,
    "beats": 1} cuts it for the beats before that shot lands, {"at": s, "for": s} anywhere. The
    "music stop" before a drop or a title is the oldest trick in trailer editing. Returns a
    volume expression, or None."""
    m, grid = music(ad, profile), beat_grid(ad, profile)
    terms = []
    for st in m.get("stops", []):
        if "before" in st:
            t = landing_of(tl, ad["shots"][st["before"]]) if 0 <= st["before"] < len(ad["shots"]) else None
            if t is None:
                continue
            a, b = t - st.get("beats", 1) * (grid[0] if grid else 0.5), t
        else:
            a, b = st["at"], st["at"] + st["for"]
        terms.append(f"(1-clip((t-{a:.4f})/0.012,0,1)+clip((t-{b - 0.004:.4f})/0.008,0,1))")
    return "*".join(terms) or None


def mix(ad, profile, tl, total, joined, out):
    prof = PROFILES[profile]
    audio = ad.get("audio", {})

    def opt(k):  # the storyboard's audio.<k>, else the profile's, else the ad default
        return audio[k] if k in audio else prof.get(k, AUDIO_DEFAULTS[k])
    args, graph, labels = ["-i", joined], [], []
    graph.append(f"[0:a]volume={audio.get('game_volume', 1.0)}[g]")
    labels.append("[g]")
    n = 1
    bgm_name = audio.get("bgm", "ad" if HUASHU.exists() else None)
    if bgm_name:
        bgm = resolve(ad, bgm_name, "bgm")
        m = music(ad, profile)
        start, end = m.get("start", 0), m.get("end", "fade")
        length = float(probe(bgm)["format"]["duration"])
        lp, fo = opt("bgm_lowpass"), opt("bgm_fade_out")
        tail = f"{f'lowpass=f={lp},' if lp else ''}volume={opt('bgm_volume')}"
        if end not in ("fade", "stop", "outro"):
            die(f"music.end is fade, stop or outro, not {end!r}")
        if end == "outro":
            # The track's own ending: play from `start`, then jump on a bar line to `outro_at`
            # (a downbeat) so the track ends where the trailer ends, on its last hit.
            if "outro_at" not in m:
                die('music.end "outro" needs music.outro_at (build_ad.py beats MUSIC prints it)')
            outro = m["outro_at"]
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import beats
            # Line the track's last sound up just before the video ends, then move the splice to
            # the nearest bar line so the beat runs on through it.
            ending = max(beats.sound_end(bgm) - outro, 0.1)
            cut, grid = max(total - 0.3 - ending, 0.0), beat_grid(ad, profile)
            if grid:
                bar = 4 * grid[0]
                cut = max(grid[1] + round((cut - grid[1]) / bar) * bar, 0.0)
            args += ["-i", bgm]
            graph.append(f"[{n}:a]asplit=2[ma][mb];[ma]atrim={start:.4f}:{start + cut + 0.02:.4f},asetpts=PTS-STARTPTS[mpa];"
                         f"[mb]atrim={outro:.4f}:{outro + total - cut:.4f},asetpts=PTS-STARTPTS[mpb];"
                         f"[mpa][mpb]acrossfade=d=0.02:c1=tri:c2=tri,afade=in:st=0:d=0.3,apad,atrim=0:{total:.4f},"
                         f"afade=out:st={max(total - 0.25, 0):.3f}:d=0.25[mus]")
            print(f"  ♪ music {start:.2f}s → {start + cut:.2f}s, then the ending from {outro:.2f}s: it starts at "
                  f"{cut:.2f}s and its sound ends at {cut + ending:.2f}s of {total:.2f}s")
        else:
            if start + total > length + 0.05:
                print(f"  ⚠ the music runs out at {length - start:.1f}s of {total:.1f}s and loops; pick an earlier music.start")
            ends = [st + tr for kind, it, st, d, tr in tl if kind == "end"]
            stop = ends[0] if end == "stop" and ends else total
            fade = (f"afade=out:st={max(stop - 0.03, 0):.3f}:d=0.03" if end == "stop"
                    else f"afade=out:st={max(total - fo, 0):.3f}:d={fo}")
            args += ["-stream_loop", "-1", "-i", bgm]
            graph.append(f"[{n}:a]atrim={start:.4f}:{start + total:.4f},asetpts=PTS-STARTPTS,"
                         f"afade=in:st=0:d=0.3,{fade}[mus]")
        gain = music_gain(ad, profile, tl)
        gain_f = f"asetnsamples=n=256,volume=eval=frame:volume='{gain}'," if gain else ""
        graph.append(f"[mus]{gain_f}{tail}[bgm]")
        labels.append("[bgm]")
        n += 1
    shot_starts = {id(it): start for kind, it, start, *_ in tl}
    ends = [start for kind, it, start, *_ in tl if kind == "end"]
    for cue in ad.get("cues", []):
        if "shot" in cue:
            shot = ad["shots"][cue["shot"]]
            if id(shot) not in shot_starts:
                continue
            t = shot_starts[id(shot)] + cue.get("at", 0)
        elif cue.get("end_card"):
            if not ends:
                continue
            t = ends[0] + cue.get("at", 0)
        else:
            t = cue["t"]
        args += ["-i", resolve(ad, cue["sfx"], "sfx")]
        ms = int(t * 1000)
        graph.append(f"[{n}:a]aresample=48000,adelay={ms}:all=1,volume={cue.get('db', -12)}dB,highpass=f=800[s{n}]")
        labels.append(f"[s{n}]")
        n += 1
    graph.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0,"
                 f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,aformat=channel_layouts=stereo[a]")
    ffmpeg(*args, "-filter_complex", ";".join(graph), "-map", "0:v", "-map", "[a]", "-c:v", "copy",
           "-c:a", "aac", "-b:a", prof["abr"], "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
           "-t", f"{total:.3f}", out)


SELL_WORDS = ("download", "free", "$", "price", "install", "tải")
CTA_WORDS = ("download", "install", "play now", "get it", "tải", "chơi ngay")
RANK_WORDS = ("best", "#1", "no. 1", "number one", "top 1", "top-rated")
DATED = ("new for", "christmas", "halloween", "black friday", "holiday", "this spring", "this summer",
         "this fall", "this autumn", "this winter", "valentine")
STORE_TRANSITIONS = ("cut", "fade", "dissolve", "fadeblack", "fadewhite")


def store_problems(ad, profile):
    """Store video rules. App Store previews: no prices or "free" (Apple). Google Play: no CTA and
    no ranking words such as "best" or "#1". Both: no dates or seasons that age the video, and
    (Apple) plain transitions, "like dissolves and fades". Returns (failures, warnings)."""
    if not PROFILES[profile].get("store"):
        return [], []
    import re
    tl, _ = timeline(ad, profile)
    texts = [(i + 1, (pick(it, "caption", profile) or {}).get("text", "")) for i, (kind, it, *_) in enumerate(tl)
             if kind == "shot"]
    texts += [(i + 1, it["card"].get("text", "")) for i, (kind, it, *_) in enumerate(tl) if kind == "card"]
    texts += [(i + 1, " ".join(str(it.get(k, "")) for k in ("headline", "subline", "date")))
              for i, (kind, it, *_) in enumerate(tl) if kind == "end"]
    banned = SELL_WORDS if profile == "app-preview" else CTA_WORDS + RANK_WORDS
    fails, warns = [], []
    for i, t in texts:
        low = t.lower().replace("*", "")
        hit = [w for w in banned if w in low]
        if hit:
            fails.append(f"#{i} \"{t}\" uses {', '.join(hit)}")
        if re.search(r"\b(19|20)\d\d\b", low) or any(w in low for w in DATED):
            warns.append(f"#{i} \"{t}\" is dated: a year or a season ages a store video")
    if profile == "app-preview":
        odd = [f"#{i + 1} {transition_of(it, profile)}" for i, (kind, it, st, d, tr) in enumerate(tl)
               if tr and transition_of(it, profile) not in STORE_TRANSITIONS]
        if odd:
            warns.append(f"transitions {', '.join(odd)}: Apple asks for plain ones, like dissolves and fades")
    return fails, warns


def caption_layer(ad, r, tmp, i, shot, profile, w, h):
    """The caption of a shot as a still (anim "fade") or as animated frames (pop, slide, words)."""
    cap = pick(shot, "caption", profile)
    if not cap:
        return None
    anim = cap.get("anim", pick(ad, "caption_anim", profile) or "pop")
    if anim not in CAPTION_ANIMS:
        die(f"unknown caption anim {anim!r} (use {', '.join(CAPTION_ANIMS)})")
    html = caption_html(ad, cap, w, h, anim)
    if anim == "fade":
        return "png", r.png(html, w, h, tmp / f"cap{i:02d}.png")
    return "seq", r.frames(html, w, h, tmp / f"cap{i:02d}_%03d.png", caption_frames(cap, anim))


def render(ad, profile, out, force=False):
    prof = PROFILES[profile]
    tl, total = timeline(ad, profile)
    if not tl:
        die(f"no shots for profile {profile}")
    if not prof["min"] <= total <= prof["max"] and not force:
        print(storyboard(ad, profile))
        die(f"{profile} is {total:.1f}s; it must be {prof['min']}–{prof['max']}s. "
            "Adjust in/out/speed/beats (or --force for a draft).")
    store_fails, _ = store_problems(ad, profile)
    if store_fails and not force:
        die(f"{profile} text breaks the store's rules: {'; '.join(store_fails)}. Give those items a "
            f"caption_{profile.replace('-', '_')} (or change the end card) for this profile.")
    w, h = prof["w"], prof["h"]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    ignore_media(Path(out).parent)
    tmp = Path(tempfile.mkdtemp(prefix=f".build-{profile}-", dir=Path(out).parent))
    segs, bug = [], None
    with Renderer() as r:
        for i, (kind, it, start, d, tr) in enumerate(tl):
            seg = tmp / f"seg{i:02d}.mov"
            if kind == "shot":
                layout = layout_of(it, profile)
                cap_layer = caption_layer(ad, r, tmp, i, it, profile, w, h) if layout != "panel" else None
                if layout in ("panel", "grid"):
                    render_staged(ad, it, d, prof, profile, layout, r, tmp, i, cap_layer, seg)
                else:
                    render_shot(ad, it, d, prof, profile, layout, cap_layer, r, tmp, i, seg)
            elif kind == "card":
                card = it["card"]
                if card.get("anim", "rise") not in CARD_ANIMS:
                    die(f"unknown card anim {card.get('anim')!r} (use {', '.join(CARD_ANIMS)})")
                bg = None
                if card.get("bg_take"):
                    bg = tmp / f"cardbg{i:02d}.png"
                    ffmpeg("-ss", card.get("bg_at", 0), "-i", resolve(ad, card["bg_take"]), "-frames:v", "1", bg)
                html, nf = card_html(ad, card, w, h, bg), card_frames(card)
                if nf > 1:
                    render_still(d, prof, r.frames(html, w, h, tmp / f"card{i:02d}_%03d.png", nf, False), seg, True)
                else:
                    render_still(d, prof, r.png(html, w, h, tmp / f"card{i:02d}.png", transparent=False), seg)
            else:
                anim = it.get("anim", "rise")
                if anim not in ("rise", "none"):
                    die(f"end_card.anim is rise or none, not {anim!r}")
                html = endcard_html(ad, it, w, h, anim, cta=not prof.get("no_cta"))
                nf = endcard_frames(d, anim)
                if nf > 1:
                    render_still(d, prof, r.frames(html, w, h, tmp / "endcard_%03d.png", nf, False), seg, True)
                else:
                    render_still(d, prof, r.png(html, w, h, tmp / "endcard.png", transparent=False), seg)
            segs.append((seg, d, transition_of(it, profile), tr))
            print(f"  ✓ {kind} {i + 1}/{len(tl)}  {start:.1f}–{start + d:.1f}s")
        bug_spec = pick(ad, "brand_bug", profile)
        if bug_spec:
            ends = [st + tr for kind, it, st, d, tr in tl if kind == "end"]
            until = bug_spec.get("until", "end")
            until = (ends[0] if ends else total) if until == "end" else float(until)
            bug = (r.png(bug_html(ad, w, h, bug_spec), w, h, tmp / "bug.png"), until)
    joined = tmp / "joined.mov"
    join(segs, joined, pick(ad, "fade_in", profile) or 0, bug)
    mix(ad, profile, tl, total, joined, out)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"◇ {out}  ({total:.1f}s, {w}x{h})")


# ---------------------------------------------------------------- check

def check(path, profile, ad=None):
    prof, fails = PROFILES[profile], []
    info = probe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur, size = float(info["format"]["duration"]), int(info["format"]["size"])
    num, den = map(int, v["avg_frame_rate"].split("/"))
    fps = num / den if den else 0

    def rule(ok, msg):
        print(f"  {'✓' if ok else '✗'} {msg}")
        if not ok:
            fails.append(msg)

    print(f"▸ {path} as {profile}")
    rule((v["width"], v["height"]) == (prof["w"], prof["h"]), f"size {v['width']}x{v['height']} (want {prof['w']}x{prof['h']})")
    rule(abs(fps - FPS) <= 0.5, f"fps {fps:.2f} (want {FPS})")
    rule(prof["min"] <= dur <= prof["max"] + 0.05, f"duration {dur:.2f}s (want {prof['min']}–{prof['max']}s)")
    rule(v["codec_name"] == "h264" and v.get("pix_fmt") == "yuv420p", f"video {v['codec_name']} {v.get('pix_fmt')}")
    rule(a is not None and a["codec_name"] == "aac" and a.get("channels") == 2,
         f"audio {a['codec_name'] + ' ' + str(a.get('channels')) + 'ch' if a else 'missing'} (want AAC stereo)")
    if "max_bytes" in prof:
        rule(size <= prof["max_bytes"], f"file {size / 1e6:.1f} MB (max {prof['max_bytes'] / 1e6:.0f} MB)")
    ignored = git_ignored(path)
    if ignored is not None:
        rule(ignored, "git-ignored, so it is never pushed")
        if not ignored:
            print("    fix: add *.mp4 to that folder's .gitignore; if git tracks it, git rm --cached it")
    if ad and is_ua(profile):
        hook_fails, hook_warns = hook_problems(ad, profile)
        rule(not hook_fails, "hook: gameplay from the first frame, no card in the first 3 s"
             + (f" ({'; '.join(hook_fails)})" if hook_fails else ""))
        for m in hook_warns:
            print(f"  ⚠ {m}")
    if ad and PROFILES[profile].get("store"):
        store_fails, store_warns = store_problems(ad, profile)
        rule(not store_fails, "store text: no selling, CTA or ranking words"
             + (f" ({'; '.join(store_fails)})" if store_fails else ""))
        for m in store_warns:
            print(f"  ⚠ {m}")
    if ad and beat_grid(ad, profile) and music(ad, profile).get("sync", True):
        hard = [(i, off) for i, _, off, is_hard in landings(ad, profile) if is_hard]
        off = [f"#{i + 1} {o:+.2f}s" for i, o in hard if abs(o) > 1.01 / FPS]
        rule(not off, f"hard cuts on the beat {len(hard) - len(off)}/{len(hard)}"
             + (f" (off: {', '.join(off)})" if off else ""))
    verify = HUASHU / "scripts/verify-video.sh"
    if verify.exists():
        black_open = ["--allow-black-open"] if ad and pick(ad, "fade_in", profile) else []
        r = subprocess.run(["bash", str(verify), str(path), f"--width={prof['w']}", f"--height={prof['h']}",
                            f"--fps={FPS}", *black_open], capture_output=True, text=True)
        print("  ── huashu-design verify-video.sh")
        print("\n".join("    " + line for line in r.stdout.strip().splitlines()))
        rule(r.returncode == 0, "verify-video.sh passes")
    else:
        print("  (huashu-design not installed — skipped verify-video.sh: black frames, loudness)")
    if ad:
        tl, _ = timeline(ad, profile)
        sheet_dir = ad["_dir"] / "sheets"
        sheet_dir.mkdir(exist_ok=True)
        for kind, it, start, *_ in tl:
            for c in it.get("check_at", []):
                f = int((start + c) * FPS)
                if f / FPS >= dur - 0.5 / FPS:
                    rule(False, f"check frame f{f} is past the end ({dur:.2f}s)")
                    continue
                tag = f"{profile}-{ad['_variant'].replace(',', '-')}" if ad.get("_variant") else profile
                img = sheet_dir / f"check-{tag}-f{f:04d}.jpg"
                ffmpeg("-ss", f / FPS, "-i", path, "-frames:v", "1", "-q:v", 3, img)
                print(f"  ◦ check frame f{f} → {img}")
        if PROFILES[profile].get("store"):
            # The poster frame shows when autoplay is off (Apple) and comes from the video itself.
            pt = float(ad.get("poster_at", 0.5))
            img = sheet_dir / f"poster-{profile}.jpg"
            ffmpeg("-ss", pt, "-i", path, "-frames:v", "1", "-q:v", 2, img)
            where = ("set the same time in App Store Connect" if profile == "app-preview" else
                     "Google Play covers the video with the feature graphic: build it from this frame")
            print(f"  ◦ poster frame at {pt:.2f}s → {img} ({where})")
    print(f"◇ {'PASS' if not fails else f'{len(fails)} FAIL'}")
    return not fails


# ---------------------------------------------------------------- thumbnail

def thumb(args):
    ad = load_ad(args.ad) if args.ad else {"_dir": Path.cwd(), "game": {"colors": DEFAULT_COLORS}}
    w, h = (int(v) for v in args.size.lower().split("x"))
    tmp = Path(tempfile.mkdtemp(prefix="game-ad-thumb-"))
    frame = tmp / "frame.png"
    ffmpeg("-ss", args.at, "-i", args.take, "-frames:v", "1", frame)
    fw, fh = video_size(frame)
    with Renderer() as r:
        r.png(thumb_html(ad, frame, fw, fh, w, h, args.text, args.sub), w, h, args.out, transparent=False)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"◇ {args.out}  ({w}x{h})")


# ---------------------------------------------------------------- direction board

def board(args):
    ad = load_ad(args.ad) if args.ad else {"_dir": Path.cwd(), "game": {"colors": DEFAULT_COLORS}}
    c = ad["game"]["colors"]
    tmp = Path(tempfile.mkdtemp(prefix="game-ad-board-"))
    frame = tmp / "frame.png"
    ffmpeg("-ss", args.at, "-i", args.take, "-frames:v", "1", frame)
    # --wide: a 16:9 hook frame for a trailer, the take centred over a blurred copy of itself.
    fw, fh, bw = (880, 495, 1600) if args.wide else (540, 960, 1440)
    blur = f"<img class=bl src='{data_uri(frame)}'>" if args.wide else ""
    beats = "".join(f"<li>{rich(b.strip(), c['accent'])}</li>" for b in args.beats.split("|") if b.strip())
    html = f"""<html><head><style>{font_css(ad)}
body{{width:{bw}px;height:1040px;background:{c['bg']};color:{c['fg']};display:flex;gap:56px;padding:40px 56px;align-items:center}}
.f{{position:relative;width:{fw}px;height:{fh}px;border-radius:28px;overflow:hidden;flex:none;background:#000}}
.f img{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}}
.f img.bl{{object-fit:cover;filter:blur(24px) brightness(.55);transform:scale(1.1)}}
.h{{position:absolute;left:6%;right:6%;top:3.5%;text-align:center}}
.h span.p{{display:inline-block;background:rgba(10,8,20,.62);padding:10px 20px;border-radius:14px;font-size:40px;
font-weight:900;line-height:1.08;-webkit-text-stroke:3px {c['stroke']};paint-order:stroke fill}}
.t{{font-size:56px;font-weight:900;letter-spacing:-.02em}}.k{{opacity:.7;font-size:24px;margin:8px 0 28px}}
li{{font-size:28px;line-height:1.35;margin:10px 0}}</style></head>
<body><div class=f>{blur}<img src='{data_uri(frame)}'><div class=h><span class=p>{rich(args.hook, c['accent'])}</span></div></div>
<div><div class=t>{rich(args.title, c['accent'])}</div><div class=k>hook frame from {Path(args.take).name} @ {args.at}s</div>
<ol>{beats}</ol></div></body></html>"""
    with Renderer() as r:
        r.png(html, bw, 1040, args.out, transparent=False)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"◇ {args.out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("storyboard")
    s.add_argument("ad")
    s.add_argument("--profile", choices=PROFILES, default="ua")
    s.add_argument("--variant", help="apply variants.<name>[,<name>…] first")
    b = sub.add_parser("board")
    b.add_argument("--take", required=True)
    b.add_argument("--at", type=float, required=True)
    b.add_argument("--title", required=True)
    b.add_argument("--hook", required=True)
    b.add_argument("--beats", default="", help="beats separated by |")
    b.add_argument("--out", required=True)
    b.add_argument("--ad")
    b.add_argument("--wide", action="store_true", help="16:9 hook frame, for a trailer direction")
    bt = sub.add_parser("beats")
    bt.add_argument("music", help="a path, or a huashu-design BGM name (ad, tech, …)")
    bt.add_argument("--drop-at", type=float, help="trailer second where the drop should land")
    bt.add_argument("--length", type=float, help="trailer length: the drop must leave this much track")
    bt.add_argument("--json", action="store_true")
    bt.add_argument("--ad", help="resolve MUSIC relative to this storyboard")
    th = sub.add_parser("thumb")
    th.add_argument("--take", required=True)
    th.add_argument("--at", type=float, required=True)
    th.add_argument("--text", required=True, help="one short promise; *word* takes the accent")
    th.add_argument("--sub")
    th.add_argument("--ad")
    th.add_argument("--size", default="1280x720", help="1280x720 (YouTube) or e.g. 1080x1920")
    th.add_argument("--out", required=True)
    r = sub.add_parser("render")
    r.add_argument("ad")
    r.add_argument("--profile", choices=PROFILES, required=True)
    r.add_argument("--out")
    r.add_argument("--force", action="store_true")
    r.add_argument("--variant", help="apply variants.<name>[,<name>…]; the output is named after them")
    c = sub.add_parser("check")
    c.add_argument("file")
    c.add_argument("--profile", choices=PROFILES, required=True)
    c.add_argument("--ad")
    c.add_argument("--variant", help="the variant the video was rendered with (for its timeline)")
    a = p.parse_args()

    if a.cmd == "storyboard":
        print(storyboard(load_ad(a.ad, a.variant), a.profile))
    elif a.cmd == "board":
        board(a)
    elif a.cmd == "thumb":
        thumb(a)
    elif a.cmd == "beats":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import beats
        ad = load_ad(a.ad) if a.ad else {"_dir": Path.cwd()}
        res = beats.analyze(resolve(ad, a.music, "bgm"), a.drop_at, a.length)
        print(json.dumps(res, indent=2) if a.json else beats.report(res))
    elif a.cmd == "render":
        ad = load_ad(a.ad, a.variant)
        out = Path(a.out) if a.out else variant_name(ad["_dir"] / PROFILES[a.profile]["out"], ad)
        render(ad, a.profile, out, a.force)
    elif a.cmd == "check":
        sys.exit(0 if check(a.file, a.profile, load_ad(a.ad, a.variant) if a.ad else None) else 1)


if __name__ == "__main__":
    main()
