#!/usr/bin/env python3
"""Cut recorded gameplay takes into an ad or a trailer, driven by a storyboard file (ad.json,
trailer.json).

  build_ad.py storyboard AD.json [--profile ua]          # the shot table with computed times
  build_ad.py board --take T.mp4 --at S --title … --hook … --beats "a|b|c" --out D.png [--ad AD.json] [--wide]
  build_ad.py beats MUSIC [--drop-at S] [--length L] [--json]   # beat grid + sections (beats.py)
  build_ad.py render AD.json --profile PROFILE [--out F.mp4] [--force]
  build_ad.py check F.mp4 --profile PROFILE [--ad AD.json]

Profiles
  ua            1080x1920, 30 fps, 15–30 s, captions + end card + CTA, AAC 192k
  app-preview   886x1920, 30 fps, 15–30 s, in-game footage only, no end card, AAC stereo 256k
  trailer       1920x1080, 30 fps, 45–120 s, cards + layouts + end card, music-led mix, AAC 320k
  trailer-9x16  1080x1920, 30 fps, 30–60 s, the vertical cut-down of the same trailer.json

A storyboard's top-level "profiles" sets which profiles its shots belong to (default ua +
app-preview). Trailers cut on the beat: with music.bpm/beat0/start, an item given in `beats`
ends on the beat grid. Portrait takes go into a 16:9 frame by `layout`: fit, fill, panel, grid.

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
    "ua": {"w": 1080, "h": 1920, "min": 15, "max": 30, "end_card": True, "abr": "192k",
           "out": "ad-ua-9x16.mp4"},
    "app-preview": {"w": 886, "h": 1920, "min": 15, "max": 30, "end_card": False, "abr": "256k",
                    "max_bytes": 500 * 1024 * 1024, "out": "app-preview-886x1920.mp4"},
    # Trailers: the music leads, so it stays full-range and loud; the game sits under it.
    "trailer": {"w": 1920, "h": 1080, "min": 45, "max": 120, "end_card": True, "abr": "320k",
                "bgm_volume": 0.9, "bgm_lowpass": None, "bgm_fade_out": 2.0, "out": "trailer-16x9.mp4"},
    "trailer-9x16": {"w": 1080, "h": 1920, "min": 30, "max": 60, "end_card": True, "abr": "320k",
                     "bgm_volume": 0.9, "bgm_lowpass": None, "bgm_fade_out": 2.0, "out": "trailer-9x16.mp4"},
}
AD_PROFILES = ["ua", "app-preview"]  # a storyboard without top-level "profiles"
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

def load_ad(path):
    path = Path(path).resolve()
    ad = json.loads(path.read_text())
    ad["_dir"] = path.parent
    ad.setdefault("game", {})
    ad["game"]["colors"] = {**DEFAULT_COLORS, **ad["game"].get("colors", {})}
    return ad


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
    return profile in item.get("profiles", ad.get("profiles", AD_PROFILES))


def pick(item, key, profile):
    """`<key>_<profile>` (caption_app_preview, layout_trailer_9x16, zoom_trailer, …) overrides
    `key` for that profile; null drops it."""
    k = f"{key}_{profile.replace('-', '_')}"
    return item[k] if k in item else item.get(key)


def layout_of(shot, profile):
    """fit | fill | panel | grid. panel and grid need a landscape frame: in a portrait profile a
    portrait take already fills the frame, so they fall back to fit (grid: its first take)."""
    lay = pick(shot, "layout", profile) or "fit"
    if lay not in LAYOUTS:
        die(f"unknown layout {lay!r} (use {', '.join(LAYOUTS)})")
    prof = PROFILES[profile]
    return "fit" if lay in ("panel", "grid") and prof["h"] > prof["w"] else lay


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
        tr = 0.0 if i == 0 or it.get("transition", "cut") == "cut" else frames(it.get("transition_s", 0.3))
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
            lay, asked = layout_of(it, profile), pick(it, "layout", profile) or "fit"
            if lay != "fit":
                cam = f"{lay}{' ' + it.get('side', 'left') if lay == 'panel' else ''} · {cam}"
            elif asked != "fit":
                cam += f" · ({asked} → fit in portrait)"
            framing = it.get("framing", f"{z['to']}x" if z else "1x")
            comp = it.get("composition", (pick(it, "caption", profile) or {}).get("text", ""))
            srcs = it["takes"] if lay == "grid" else [dict(zip(("take", "in"), primary(it)))]
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
        trans = it.get("transition", "cut") + (f" {tr}s" if tr else "")
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
    rows.append(f"\n{profile}: {total:.1f}s, {len(tl)} shots, "
                f"{int(total * FPS)} frames (allowed {PROFILES[profile]['min']}–{PROFILES[profile]['max']}s)")
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

    def __exit__(self, *exc):
        self.browser.close()
        self.pw.stop()


def caption_html(ad, cap, w, h):
    """pos: top | center | bottom, or a number = top edge as a fraction of the height.
    plate (default on) puts a dark rounded plate behind the text: gameplay is always busy, and
    the game's own HUD usually sits exactly where a top caption goes."""
    c = ad["game"]["colors"]
    size = int(min(w, h) * cap.get("size", 0.074))
    p = cap.get("pos", "top")
    pos = (f"top:{int(h * p)}px" if isinstance(p, (int, float)) else
           {"top": f"top:{int(h * 0.11)}px", "center": f"top:{int(h * 0.42)}px",
            "bottom": f"bottom:{int(h * (0.22 if h > w else 0.1))}px"}[p])
    stroke = max(2, size // 14)
    plate = (f"background:{cap.get('plate_color', 'rgba(10,8,20,.62)')};padding:{size // 4}px {size // 2}px;"
             f"border-radius:{size // 3}px;" if cap.get("plate", True) else "")
    return f"""<html><head><style>{font_css(ad)}
.w{{position:absolute;left:6%;right:6%;{pos};text-align:center}}
.c{{display:inline-block;{plate}color:{c['fg']};font-size:{size}px;
font-weight:900;line-height:1.08;letter-spacing:-.01em;text-wrap:balance;-webkit-text-stroke:{stroke}px {c['stroke']};
paint-order:stroke fill;text-shadow:0 {stroke}px {stroke * 3}px rgba(0,0,0,.45)}}</style></head>
<body style="background:transparent"><div class=w><div class=c>{rich(cap['text'], c['accent'])}</div></div></body></html>"""


def logo_img(ad, w, h):
    """game.logo, a wordmark image, sized for a title card; None when the game has none."""
    logo = ad["game"].get("logo")
    if not logo:
        return None
    return f"<img src='{data_uri(resolve(ad, logo))}' class=l style='max-width:{int(w * 0.62)}px;max-height:{int(h * 0.3)}px'>"


def endcard_html(ad, ec, w, h):
    """Sizes follow the short side, so a 16:9 card matches a 9:16 one. A trailer end card adds
    `date` ("Out now", "Coming 2027") and `platforms` as plain text chips: no store badge art."""
    c, g, m = ad["game"]["colors"], ad["game"], min(w, h)
    icon = resolve(ad, ec.get("icon") or g.get("icon"))
    isz = int(m * (0.34 if h > w else 0.24))
    gap = int(h * 0.025) if h > w else int(m * 0.025)
    icon_tag = f"<img src='{data_uri(icon)}' class=i>" if icon else ""
    name = f"<div class=n>{rich(ec.get('headline', g.get('name', '')), c['accent'])}</div>"
    logo = logo_img(ad, w, h) if ec.get("logo", True) else None
    head = logo or icon_tag + name
    cta = f"<div class=b>{rich(ec['cta'], c['bg'])}</div>" if ec.get("cta") else ""
    sub = f"<div class=s>{rich(ec['subline'], c['accent'])}</div>" if ec.get("subline") else ""
    date = f"<div class=d>{rich(ec['date'], c['accent'])}</div>" if ec.get("date") else ""
    plats = "".join(f"<span>{rich(p, c['accent'])}</span>" for p in ec.get("platforms", []))
    plats = f"<div class=p>{plats}</div>" if plats else ""
    return f"""<html><head><style>{font_css(ad)}
body{{width:{w}px;height:{h}px;display:flex;flex-direction:column;align-items:center;justify-content:center;
gap:{gap}px;color:{c['fg']};background:radial-gradient(120% 80% at 50% 38%,{c.get('bg2', c['bg'])},{c['bg']})}}
.i{{width:{isz}px;height:{isz}px;border-radius:22%;box-shadow:0 {int(m * .03)}px {int(m * .08)}px rgba(0,0,0,.45)}}
.n{{font-size:{int(m * 0.105)}px;font-weight:900;letter-spacing:-.02em;text-align:center;padding:0 6%}}
.s{{font-size:{int(m * 0.045)}px;opacity:.85;text-align:center;padding:0 10%}}
.d{{font-size:{int(m * 0.05)}px;font-weight:800;letter-spacing:.04em;text-transform:uppercase}}
.p{{display:flex;flex-wrap:wrap;justify-content:center;gap:{int(m * 0.015)}px;padding:0 8%}}
.p span{{font-size:{int(m * 0.032)}px;padding:{int(m * 0.008)}px {int(m * 0.022)}px;border:{max(2, m // 360)}px solid rgba(255,255,255,.45);border-radius:999px}}
.b{{margin-top:{int(h * 0.02) if h > w else int(m * 0.036)}px;background:{c['accent']};color:{c['bg']};font-weight:900;font-size:{int(m * 0.055)}px;
padding:{int(m * 0.03)}px {int(m * 0.09)}px;border-radius:999px}}</style></head>
<body>{head}{sub}{date}{plats}{cta}</body></html>"""


def card_html(ad, card, w, h, bg=None):
    """A full-frame text card: style title (big), feature (a verb or two) or logo. The background
    is the game's gradient, or `bg` (a still from a take), blurred and darkened."""
    c, g, m = ad["game"]["colors"], ad["game"], min(w, h)
    style = card.get("style", "feature")
    if style == "logo":
        icon = resolve(ad, g.get("icon")) if g.get("icon") else None
        body = logo_img(ad, w, h) or (
            (f"<img src='{data_uri(icon)}' class=i>" if icon else "")
            + f"<div class=t style='font-size:{int(m * 0.12)}px'>{rich(g.get('name', ''), c['accent'])}</div>")
    else:
        size = int(m * card.get("size", 0.12 if style == "title" else 0.09))
        body = f"<div class=t style='font-size:{size}px'>{rich(card.get('text', ''), c['accent'])}</div>"
    if card.get("sub"):
        body += f"<div class=s>{rich(card['sub'], c['accent'])}</div>"
    bg_tag = f"<img class=bg src='{data_uri(bg)}'>" if bg else ""
    return f"""<html><head><style>{font_css(ad)}
body{{width:{w}px;height:{h}px;position:relative;overflow:hidden;display:flex;flex-direction:column;
align-items:center;justify-content:center;gap:{int(m * 0.03)}px;color:{c['fg']};
background:radial-gradient(120% 90% at 50% 42%,{c.get('bg2', c['bg'])},{c['bg']})}}
.bg{{position:absolute;left:-6%;top:-6%;width:112%;height:112%;object-fit:cover;filter:blur({int(m * 0.03)}px) brightness(.4)}}
.t,.s,.i,.l{{position:relative}}
.t{{font-weight:900;letter-spacing:-.02em;line-height:1.05;text-align:center;padding:0 8%;text-wrap:balance;
text-shadow:0 {max(2, m // 200)}px {m // 50}px rgba(0,0,0,.45)}}
.s{{font-size:{int(m * 0.042)}px;opacity:.85;text-align:center;padding:0 10%}}
.i{{width:{int(m * 0.24)}px;height:{int(m * 0.24)}px;border-radius:22%;box-shadow:0 {int(m * .03)}px {int(m * .08)}px rgba(0,0,0,.45)}}
</style></head><body>{bg_tag}{body}</body></html>"""


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
    y = int(h * 0.95) - ph if top_caption else (h - ph) // 2
    if n == 1:
        x = int(w * (0.3 if side == "left" else 0.7) - pw / 2) // 2 * 2
        box = (int(w * 0.53), int(w * 0.95)) if side == "left" else (int(w * 0.05), int(w * 0.47))
        return [(x, y, pw, ph)], box
    x0 = (w - (n * pw + (n - 1) * gap)) / 2
    return [(int(x0 + i * (pw + gap)) // 2 * 2, y, pw, ph) for i in range(n)], None


def stage_html(ad, w, h, rects, radius, cap=None, box=None):
    """Background for panel / grid: the game's gradient, a soft shadow where each take goes and,
    for a panel, the caption as large text in the free half (`caption.sub` under it)."""
    c, m = ad["game"]["colors"], min(w, h)
    shadows = "".join(f"<div class=p style='left:{x}px;top:{y}px;width:{pw}px;height:{ph}px'></div>"
                      for x, y, pw, ph in rects)
    text = ""
    if cap and box:
        size = int(m * cap.get("size", 0.1))
        sub = f"<div class=s>{rich(cap['sub'], c['accent'])}</div>" if cap.get("sub") else ""
        text = (f"<div class=x style='left:{box[0]}px;width:{box[1] - box[0]}px'>"
                f"<div class=t style='font-size:{size}px'>{rich(cap['text'], c['accent'])}</div>{sub}</div>")
    return f"""<html><head><style>{font_css(ad)}
body{{width:{w}px;height:{h}px;position:relative;overflow:hidden;color:{c['fg']};
background:radial-gradient(110% 90% at 50% 45%,{c.get('bg2', c['bg'])},{c['bg']})}}
.p{{position:absolute;border-radius:{radius}px;background:#000;box-shadow:0 {int(m * .02)}px {int(m * .07)}px rgba(0,0,0,.6)}}
.x{{position:absolute;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;align-items:center;
gap:{int(m * 0.025)}px;text-align:center}}
.t{{font-weight:900;letter-spacing:-.02em;line-height:1.05;text-wrap:balance;text-shadow:0 {max(2, m // 200)}px {m // 50}px rgba(0,0,0,.45)}}
.s{{font-size:{int(m * 0.042)}px;opacity:.85}}</style></head><body>{shadows}{text}</body></html>"""


def mask_html(pw, ph, radius):
    return (f"<html><body style='margin:0;background:#000'><div style='width:{pw}px;height:{ph}px;"
            f"border-radius:{radius}px;background:#fff'></div></body></html>")


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


def motion(take, speed, z):
    """Filter chain for one take input: retime, 30 fps, the push-in, then hold the last frame so
    a segment never comes up short (the encoder stops it at its frame count)."""
    v = f"setpts=(PTS-STARTPTS)/{speed},fps={FPS}"
    if z:
        iw, ih = video_size(take)
        f, to = z.get("from", 1.0), z["to"]
        at, dur = z.get("at", 0.0), max(z.get("dur", 0.6), 0.04)
        ax, ay = z.get("anchor", [0.5, 0.5])
        p = f"clip((it-{at})/{dur},0,1)"
        zexpr = f"{f}+({to}-{f})*{p}*{p}*(3-2*{p})"
        # zoompan rounds x/y to whole pixels: run it at 2x so the push stays smooth.
        v += (f",scale={iw * 2}:{ih * 2},zoompan=z='{zexpr}':d=1:fps={FPS}:s={iw}x{ih}"
              f":x='clip({ax}*iw-iw/zoom/2,0,iw-iw/zoom)':y='clip({ay}*ih-ih/zoom/2,0,ih-ih/zoom)'")
    return v + ",tpad=stop_mode=clone:stop=-1"


def take_audio(shot, take, speed, idx, d, args):
    """Audio graph for a shot: the take's own sound, or silence (appended to args) at input idx."""
    if has_audio(take) and not shot.get("mute"):
        return f"[0:a]asetpts=PTS-STARTPTS,{atempo_chain(speed)},aresample=48000,aformat=channel_layouts=stereo,apad[aout]"
    args += ["-f", "lavfi", "-t", d, "-i", "anullsrc=r=48000:cl=stereo"]
    return f"[{idx}:a]anull[aout]"


def render_shot(ad, shot, d, prof, profile, layout, cap_png, out):
    """fit: the take scaled into the frame over a blurred copy of itself. fill: the frame cut out
    of the take around fill_y (0 top … 1 bottom) and scaled up to cover it."""
    rel, t_in = primary(shot)
    take = resolve(ad, rel)
    w, h, speed = prof["w"], prof["h"], shot.get("speed", 1.0)
    args = ["-ss", t_in, "-t", d * speed, "-i", take]
    v = f"[0:v]{motion(take, speed, pick(shot, 'zoom', profile))}"
    if layout == "fill":
        fy = shot.get("fill_y", 0.5)
        v += (f",scale={w}:{h}:force_original_aspect_ratio=increase,"
              f"crop={w}:{h}:(iw-{w})/2:'clip({fy}*ih-{h}/2,0,ih-{h})',setsar=1[v0]")
    else:
        v += (f",split[a][b];[b]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
              f"gblur=sigma=40,eq=brightness=-0.12[bg];[a]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v0]")
    vout = "[v0]"
    if cap_png:
        args += ["-loop", "1", "-t", d, "-i", cap_png]
        v += ";[1:v]format=rgba,fade=in:st=0:d=0.18:alpha=1[cap];[v0][cap]overlay=0:0[v1]"
        vout = "[v1]"
    a = take_audio(shot, take, speed, 2 if cap_png else 1, d, args)
    encode_segment(args, f"{v};{a}", vout, d, out)


def render_staged(ad, shot, d, prof, profile, layout, r, tmp, i, cap_png, out):
    """panel: one take as a rounded card on the game's gradient, the caption as big text beside
    it. grid: 2–3 takes (`takes: [{take, in}]`) side by side; a caption overlays as usual."""
    w, h, speed = prof["w"], prof["h"], shot.get("speed", 1.0)
    srcs = shot["takes"] if layout == "grid" else [dict(zip(("take", "in"), primary(shot)))]
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
    bg = r.png(stage_html(ad, w, h, rects, radius, cap if layout == "panel" else None, box), w, h,
               tmp / f"stage{i:02d}.png", transparent=False)
    mask = r.png(mask_html(pw, ph, radius), pw, ph, tmp / f"mask{i:02d}.png", transparent=False)
    args = []
    for src, take in zip(srcs, takes):
        args += ["-ss", src["in"], "-t", d * speed, "-i", take]
    # 30 fps stills: the stage is overlay's main input, so its rate is the segment's rate.
    args += ["-framerate", FPS, "-loop", "1", "-t", d, "-i", bg, "-framerate", FPS, "-loop", "1", "-t", d, "-i", mask]
    z = pick(shot, "zoom", profile) if n == 1 else None
    graph = [f"[{n + 1}:v]format=gray,split={n}" + "".join(f"[m{k}]" for k in range(n)), f"[{n}:v]format=rgba[o]"]
    cur = "[o]"
    for k, take in enumerate(takes):
        graph.append(f"[{k}:v]{motion(take, speed, z)},scale={pw}:{ph}:force_original_aspect_ratio=increase,"
                     f"crop={pw}:{ph},format=rgba[t{k}];[t{k}][m{k}]alphamerge[p{k}];"
                     f"{cur}[p{k}]overlay={rects[k][0]}:{rects[k][1]}[o{k}]")
        cur = f"[o{k}]"
    graph.append(f"{cur}setsar=1[v0]")
    vout, nxt = "[v0]", n + 2
    if cap_png:
        args += ["-loop", "1", "-t", d, "-i", cap_png]
        graph.append(f"[{nxt}:v]format=rgba,fade=in:st=0:d=0.18:alpha=1[cap];[v0][cap]overlay=0:0[v1]")
        vout, nxt = "[v1]", nxt + 1
    a = take_audio(shot, takes[0], speed, nxt, d, args)
    encode_segment(args, ";".join(graph) + f";{a}", vout, d, out)


def render_still(d, prof, png, out):
    """A card or the end card: one image with a slow 1.06x → 1x settle, so it lands, not pops."""
    w, h = prof["w"], prof["h"]
    # -framerate: zoompan emits one frame per input frame, and a still loops at 25 fps by
    # default, which made every card (and the end card) a sixth shorter than its slot.
    args = ["-framerate", FPS, "-loop", "1", "-t", d, "-i", png,
            "-f", "lavfi", "-t", d, "-i", "anullsrc=r=48000:cl=stereo"]
    v = (f"[0:v]scale={w * 2}:{h * 2},zoompan=z='1.06-0.06*clip(it/0.6,0,1)*(2-clip(it/0.6,0,1))':d=1:fps={FPS}"
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


def join(segments, out, fade_in=0):
    """segments: [(path, duration, transition, transition_s)]; cut = concat, else xfade.
    fade_in > 0 opens the whole video from black."""
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
    if len(segments) > 1 or fade_in:
        fade = f"fade=t=in:st=0:d={fade_in}," if fade_in else ""
        # A closing xfade can hold one extra frame past the end; the timeline is the length.
        graph.append(f"{cur_v}{fade}trim=end_frame={round(cur_d * FPS)},scale=out_range=tv,format=yuv420p[vtv]")
        graph.append(f"{cur_a}atrim=end={cur_d:.6f}[aj]")
        cur_a = "[aj]"
        ffmpeg(*args, "-filter_complex", ";".join(graph), "-map", "[vtv]", "-map", cur_a,
               "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "17", "-r", FPS,
               "-color_range", "tv", "-c:a", "pcm_s16le", out)
    else:
        shutil.copy(segments[0][0], out)
    return cur_d


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
        start = music(ad, profile).get("start", 0)
        length = float(probe(bgm)["format"]["duration"])
        if start + total > length + 0.05:
            print(f"  ⚠ the music runs out at {length - start:.1f}s of {total:.1f}s and loops; pick an earlier music.start")
        lp, fo = opt("bgm_lowpass"), opt("bgm_fade_out")
        args += ["-stream_loop", "-1", "-i", bgm]
        graph.append(f"[{n}:a]atrim={start:.4f}:{start + total:.4f},asetpts=PTS-STARTPTS,afade=in:st=0:d=0.3,"
                     f"afade=out:st={max(total - fo, 0):.3f}:d={fo},{f'lowpass=f={lp},' if lp else ''}"
                     f"volume={opt('bgm_volume')}[bgm]")
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


def render(ad, profile, out, force=False):
    prof = PROFILES[profile]
    tl, total = timeline(ad, profile)
    if not tl:
        die(f"no shots for profile {profile}")
    if not prof["min"] <= total <= prof["max"] and not force:
        print(storyboard(ad, profile))
        die(f"{profile} is {total:.1f}s; it must be {prof['min']}–{prof['max']}s. "
            "Adjust in/out/speed/beats (or --force for a draft).")
    if profile == "app-preview":
        caps = [(pick(s, "caption", profile) or {}).get("text", "") for kind, s, *_ in tl if kind == "shot"]
        bad = [t for t in caps if any(w in t.lower() for w in ("download", "free", "$", "price", "install", "tải"))]
        if bad and not force:
            die(f"App Preview captions must not sell (price/download/free): {bad}. "
                "Give those shots a caption_app_preview or drop the caption for this profile.")
    w, h = prof["w"], prof["h"]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    ignore_media(Path(out).parent)
    tmp = Path(tempfile.mkdtemp(prefix=f".build-{profile}-", dir=Path(out).parent))
    segs = []
    with Renderer() as r:
        for i, (kind, it, start, d, tr) in enumerate(tl):
            seg = tmp / f"seg{i:02d}.mov"
            if kind == "shot":
                cap, layout = pick(it, "caption", profile), layout_of(it, profile)
                cap_png = (r.png(caption_html(ad, cap, w, h), w, h, tmp / f"cap{i:02d}.png")
                           if cap and layout != "panel" else None)
                if layout in ("panel", "grid"):
                    render_staged(ad, it, d, prof, profile, layout, r, tmp, i, cap_png, seg)
                else:
                    render_shot(ad, it, d, prof, profile, layout, cap_png, seg)
            elif kind == "card":
                bg = None
                if it["card"].get("bg_take"):
                    bg = tmp / f"cardbg{i:02d}.png"
                    ffmpeg("-ss", it["card"].get("bg_at", 0), "-i", resolve(ad, it["card"]["bg_take"]),
                           "-frames:v", "1", bg)
                card = r.png(card_html(ad, it["card"], w, h, bg), w, h, tmp / f"card{i:02d}.png", transparent=False)
                render_still(d, prof, card, seg)
            else:
                card = r.png(endcard_html(ad, it, w, h), w, h, tmp / "endcard.png", transparent=False)
                render_still(d, prof, card, seg)
            segs.append((seg, d, it.get("transition", "cut"), tr))
            print(f"  ✓ {kind} {i + 1}/{len(tl)}  {start:.1f}–{start + d:.1f}s")
    joined = tmp / "joined.mov"
    join(segs, joined, pick(ad, "fade_in", profile) or 0)
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
                img = sheet_dir / f"check-{profile}-f{f:04d}.jpg"
                ffmpeg("-ss", f / FPS, "-i", path, "-frames:v", "1", "-q:v", 3, img)
                print(f"  ◦ check frame f{f} → {img}")
    print(f"◇ {'PASS' if not fails else f'{len(fails)} FAIL'}")
    return not fails


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
    r = sub.add_parser("render")
    r.add_argument("ad")
    r.add_argument("--profile", choices=PROFILES, required=True)
    r.add_argument("--out")
    r.add_argument("--force", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("file")
    c.add_argument("--profile", choices=PROFILES, required=True)
    c.add_argument("--ad")
    a = p.parse_args()

    if a.cmd == "storyboard":
        print(storyboard(load_ad(a.ad), a.profile))
    elif a.cmd == "board":
        board(a)
    elif a.cmd == "beats":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import beats
        ad = load_ad(a.ad) if a.ad else {"_dir": Path.cwd()}
        res = beats.analyze(resolve(ad, a.music, "bgm"), a.drop_at, a.length)
        print(json.dumps(res, indent=2) if a.json else beats.report(res))
    elif a.cmd == "render":
        ad = load_ad(a.ad)
        render(ad, a.profile, Path(a.out) if a.out else ad["_dir"] / PROFILES[a.profile]["out"], a.force)
    elif a.cmd == "check":
        sys.exit(0 if check(a.file, a.profile, load_ad(a.ad) if a.ad else None) else 1)


if __name__ == "__main__":
    main()
