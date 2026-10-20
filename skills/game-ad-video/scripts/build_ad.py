#!/usr/bin/env python3
"""Cut recorded gameplay takes into an ad, driven by a storyboard file (ad.json).

  build_ad.py storyboard AD.json [--profile ua]          # the shot table with computed times
  build_ad.py board --take T.mp4 --at S --title … --hook … --beats "a|b|c" --out D.png [--ad AD.json]
  build_ad.py render AD.json --profile ua|app-preview [--out F.mp4] [--force]
  build_ad.py check F.mp4 --profile ua|app-preview [--ad AD.json]

Profiles
  ua           1080x1920, 30 fps, 15–30 s, captions + end card + CTA, AAC 192k
  app-preview  886x1920, 30 fps, 15–30 s, in-game footage only, no end card, AAC stereo 256k

Audio follows huashu-design's two-layer rule: BGM low-passed at 4 kHz at 0.45, SFX cues
high-passed at 800 Hz, amix normalize=0, BGM fade 0.3 s in / 1.5 s out, then loudnorm to -14 LUFS.
BGM and SFX names resolve against huashu-design's assets when the skill is installed
($HUASHU_DESIGN_DIR or ~/.claude/skills/huashu-design); a path relative to AD.json always wins.
Text (captions, end card, direction boards) is HTML rendered to PNG with Playwright.
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
    "ua": {"w": 1080, "h": 1920, "min": 15, "max": 30, "end_card": True, "abr": "192k"},
    "app-preview": {"w": 886, "h": 1920, "min": 15, "max": 30, "end_card": False, "abr": "256k",
                    "max_bytes": 500 * 1024 * 1024},
}
HUASHU = Path(os.environ.get("HUASHU_DESIGN_DIR", Path.home() / ".claude/skills/huashu-design"))
DEFAULT_COLORS = {"bg": "#14102a", "fg": "#ffffff", "accent": "#ffcc33", "stroke": "#000000"}


def die(msg):
    sys.exit(f"✗ {msg}")


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                          str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def has_audio(path):
    return any(s["codec_type"] == "audio" for s in probe(path)["streams"])


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


def in_profile(item, profile):
    return profile in item.get("profiles", PROFILES.keys())


def shot_caption(shot, profile):
    """caption_app_preview (etc.) overrides caption for that profile; null drops it."""
    key = f"caption_{profile.replace('-', '_')}"
    return shot[key] if key in shot else shot.get("caption")


def timeline(ad, profile):
    """[(kind, item, start, duration, transition_in)] for the profile, plus total length."""
    items = [("shot", s) for s in ad["shots"] if in_profile(s, profile)]
    ec = ad.get("end_card")
    if ec and in_profile(ec, profile) and (PROFILES[profile]["end_card"] or "profiles" in ec):
        items.append(("end", ec))
    out, t = [], 0.0
    for i, (kind, it) in enumerate(items):
        if kind == "shot":
            d = (it["out"] - it["in"]) / it.get("speed", 1.0)
        else:
            d = it.get("seconds", 2.5)
        tr = 0.0 if i == 0 or it.get("transition", "cut") == "cut" else it.get("transition_s", 0.3)
        t -= tr
        out.append((kind, it, t, d, tr))
        t += d
    return out, t


def storyboard(ad, profile):
    tl, total = timeline(ad, profile)
    rows = ["| # | time | framing | [CAMERA] move + motive | composition | key action | transition in | check frames |",
            "|---|---|---|---|---|---|---|---|"]
    for i, (kind, it, start, d, tr) in enumerate(tl):
        if kind == "shot":
            z = it.get("zoom")
            if not z:
                cam = "static"
            elif z.get("from", 1) == z["to"]:
                cam = f"hold {z['to']}x crop on {z.get('anchor_label', z.get('anchor'))}"
            else:
                cam = f"push {z.get('from', 1)}→{z['to']}x on {z.get('anchor_label', z.get('anchor'))}"
            framing = it.get("framing", f"{z['to']}x" if z else "1x")
            comp = it.get("composition", (shot_caption(it, profile) or {}).get("text", ""))
        else:
            cam, framing, comp = "static, slow settle", "end card", it.get("headline", "")
        why = it.get("why", "")
        checks = " / ".join(f"f{int((start + c) * FPS)}" for c in it.get("check_at", []))
        trans = it.get("transition", "cut") + (f" {tr}s" if tr else "")
        rows.append(f"| {i + 1} | {start:.1f}–{start + d:.1f}s | {framing} | {cam}"
                    f"{' · ' + why if why else ''} | {comp} | {it.get('action', '')} | {trans} | {checks} |")
    rows.append(f"\n{profile}: {total:.1f}s, {len(tl)} shots, "
                f"{int(total * FPS)} frames (allowed {PROFILES[profile]['min']}–{PROFILES[profile]['max']}s)")
    return "\n".join(rows)


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
    size = int(w * cap.get("size", 0.074))
    p = cap.get("pos", "top")
    pos = (f"top:{int(h * p)}px" if isinstance(p, (int, float)) else
           {"top": f"top:{int(h * 0.11)}px", "center": f"top:{int(h * 0.42)}px",
            "bottom": f"bottom:{int(h * 0.22)}px"}[p])
    stroke = max(2, size // 14)
    plate = (f"background:{cap.get('plate_color', 'rgba(10,8,20,.62)')};padding:{size // 4}px {size // 2}px;"
             f"border-radius:{size // 3}px;" if cap.get("plate", True) else "")
    return f"""<html><head><style>{font_css(ad)}
.w{{position:absolute;left:6%;right:6%;{pos};text-align:center}}
.c{{display:inline-block;{plate}color:{c['fg']};font-size:{size}px;
font-weight:900;line-height:1.08;letter-spacing:-.01em;-webkit-text-stroke:{stroke}px {c['stroke']};
paint-order:stroke fill;text-shadow:0 {stroke}px {stroke * 3}px rgba(0,0,0,.45)}}</style></head>
<body style="background:transparent"><div class=w><div class=c>{rich(cap['text'], c['accent'])}</div></div></body></html>"""


def endcard_html(ad, ec, w, h):
    c, g = ad["game"]["colors"], ad["game"]
    icon = resolve(ad, ec.get("icon") or g.get("icon"))
    icon_tag = f"<img src='{data_uri(icon)}' class=i>" if icon else ""
    cta = f"<div class=b>{rich(ec['cta'], c['bg'])}</div>" if ec.get("cta") else ""
    sub = f"<div class=s>{rich(ec['subline'], c['accent'])}</div>" if ec.get("subline") else ""
    return f"""<html><head><style>{font_css(ad)}
body{{width:{w}px;height:{h}px;display:flex;flex-direction:column;align-items:center;justify-content:center;
gap:{int(h * 0.025)}px;color:{c['fg']};background:radial-gradient(120% 80% at 50% 38%,{c.get('bg2', c['bg'])},{c['bg']})}}
.i{{width:{int(w * 0.34)}px;height:{int(w * 0.34)}px;border-radius:22%;box-shadow:0 {int(w * .03)}px {int(w * .08)}px rgba(0,0,0,.45)}}
.n{{font-size:{int(w * 0.105)}px;font-weight:900;letter-spacing:-.02em;text-align:center;padding:0 6%}}
.s{{font-size:{int(w * 0.045)}px;opacity:.85;text-align:center;padding:0 10%}}
.b{{margin-top:{int(h * 0.02)}px;background:{c['accent']};color:{c['bg']};font-weight:900;font-size:{int(w * 0.055)}px;
padding:{int(w * 0.03)}px {int(w * 0.09)}px;border-radius:999px}}</style></head>
<body>{icon_tag}<div class=n>{rich(ec.get('headline', g.get('name', '')), c['accent'])}</div>{sub}{cta}</body></html>"""


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


def render_shot(ad, shot, d, prof, cap_png, out):
    take = resolve(ad, shot["take"])
    w, h, speed = prof["w"], prof["h"], shot.get("speed", 1.0)
    args = ["-ss", shot["in"], "-t", shot["out"] - shot["in"], "-i", take]
    v = f"[0:v]setpts=(PTS-STARTPTS)/{speed},fps={FPS}"
    z = shot.get("zoom")
    if z:
        src = next(s for s in probe(take)["streams"] if s["codec_type"] == "video")
        iw, ih = src["width"], src["height"]
        f, to = z.get("from", 1.0), z["to"]
        at, dur = z.get("at", 0.0), max(z.get("dur", 0.6), 0.04)
        ax, ay = z.get("anchor", [0.5, 0.5])
        p = f"clip((it-{at})/{dur},0,1)"
        zexpr = f"{f}+({to}-{f})*{p}*{p}*(3-2*{p})"
        # zoompan rounds x/y to whole pixels: run it at 2x so the push stays smooth.
        v += (f",scale={iw * 2}:{ih * 2},zoompan=z='{zexpr}':d=1:fps={FPS}:s={iw}x{ih}"
              f":x='clip({ax}*iw-iw/zoom/2,0,iw-iw/zoom)':y='clip({ay}*ih-ih/zoom/2,0,ih-ih/zoom)'")
    v += (f",split[a][b];[b]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
          f"gblur=sigma=40,eq=brightness=-0.12[bg];[a]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
          f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v0]")
    vout = "[v0]"
    if cap_png:
        args += ["-loop", "1", "-t", d, "-i", cap_png]
        v += ";[1:v]format=rgba,fade=in:st=0:d=0.18:alpha=1[cap];[v0][cap]overlay=0:0[v1]"
        vout = "[v1]"
    if has_audio(take) and not shot.get("mute"):
        a = f"[0:a]asetpts=PTS-STARTPTS,{atempo_chain(speed)},aresample=48000,aformat=channel_layouts=stereo[aout]"
    else:
        args += ["-f", "lavfi", "-t", d, "-i", "anullsrc=r=48000:cl=stereo"]
        a = f"[{2 if cap_png else 1}:a]anull[aout]"
    encode_segment(args, f"{v};{a}", vout, d, out)


def render_end(ad, ec, d, prof, card_png, out):
    w, h = prof["w"], prof["h"]
    args = ["-loop", "1", "-t", d, "-i", card_png, "-f", "lavfi", "-t", d, "-i", "anullsrc=r=48000:cl=stereo"]
    # A slow 1.06x → 1x settle so the card lands rather than pops.
    v = (f"[0:v]scale={w * 2}:{h * 2},zoompan=z='1.06-0.06*clip(it/0.6,0,1)*(2-clip(it/0.6,0,1))':d=1:fps={FPS}"
         f":s={w}x{h}:x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2',setsar=1[v0]")
    encode_segment(args, f"{v};[1:a]anull[aout]", "[v0]", d, out)


def encode_segment(args, graph, vout, d, out):
    graph += f";{vout}scale=out_range=tv,format=yuv420p[vtv]"
    ffmpeg(*args, "-filter_complex", graph, "-map", "[vtv]", "-map", "[aout]", "-t", f"{d:.3f}",
           "-r", FPS, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "medium",
           "-crf", "17", "-color_range", "tv", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", out)


def join(segments, out):
    """segments: [(path, duration, transition, transition_s)]; cut = concat, else xfade."""
    args, graph = [], []
    for i, (p, *_) in enumerate(segments):
        args += ["-i", p]
        # xfade refuses inputs whose timebases differ (concat output vs. a fresh segment).
        graph.append(f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[i{i}]")
    cur_v, cur_a, cur_d = "[i0]", "[0:a]", segments[0][1]
    for i, (_, d, tr, td) in enumerate(segments[1:], start=1):
        nv, na = f"[v{i}]", f"[a{i}]"
        if tr == "cut" or td <= 0:
            graph.append(f"{cur_v}{cur_a}[i{i}][{i}:a]concat=n=2:v=1:a=1[c{i}]{na};[c{i}]settb=AVTB{nv}")
            cur_d += d
        else:
            graph.append(f"{cur_v}[i{i}]xfade=transition={tr}:duration={td}:offset={cur_d - td:.3f}{nv}")
            graph.append(f"{cur_a}[{i}:a]acrossfade=d={td}{na}")
            cur_d += d - td
        cur_v, cur_a = nv, na
    if len(segments) > 1:
        graph.append(f"{cur_v}scale=out_range=tv,format=yuv420p[vtv]")
        ffmpeg(*args, "-filter_complex", ";".join(graph), "-map", "[vtv]", "-map", cur_a,
               "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "17", "-r", FPS,
               "-color_range", "tv", "-c:a", "aac", "-b:a", "256k", out)
    else:
        shutil.copy(segments[0][0], out)
    return cur_d


def mix(ad, tl, total, joined, prof, out):
    audio = ad.get("audio", {})
    args, graph, labels = ["-i", joined], [], []
    graph.append(f"[0:a]volume={audio.get('game_volume', 1.0)}[g]")
    labels.append("[g]")
    n = 1
    bgm_name = audio.get("bgm", "ad" if HUASHU.exists() else None)
    if bgm_name:
        args += ["-stream_loop", "-1", "-i", resolve(ad, bgm_name, "bgm")]
        graph.append(f"[{n}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,afade=in:st=0:d=0.3,"
                     f"afade=out:st={max(total - 1.5, 0):.3f}:d=1.5,lowpass=f=4000,"
                     f"volume={audio.get('bgm_volume', 0.45)}[bgm]")
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
            "Adjust in/out/speed (or --force for a draft).")
    if profile == "app-preview":
        caps = [(shot_caption(s, profile) or {}).get("text", "") for kind, s, *_ in tl if kind == "shot"]
        bad = [t for t in caps if any(w in t.lower() for w in ("download", "free", "$", "price", "install", "tải"))]
        if bad and not force:
            die(f"App Preview captions must not sell (price/download/free): {bad}. "
                "Give those shots a caption_app_preview or drop the caption for this profile.")
    w, h = prof["w"], prof["h"]
    tmp = Path(tempfile.mkdtemp(prefix=f".build-{profile}-", dir=Path(out).parent))
    segs = []
    with Renderer() as r:
        for i, (kind, it, start, d, tr) in enumerate(tl):
            seg = tmp / f"seg{i:02d}.mp4"
            if kind == "shot":
                cap = shot_caption(it, profile)
                cap_png = r.png(caption_html(ad, cap, w, h), w, h, tmp / f"cap{i:02d}.png") if cap else None
                render_shot(ad, it, d, prof, cap_png, seg)
            else:
                card = r.png(endcard_html(ad, it, w, h), w, h, tmp / "endcard.png", transparent=False)
                render_end(ad, it, d, prof, card, seg)
            segs.append((seg, d, it.get("transition", "cut"), tr))
            print(f"  ✓ {kind} {i + 1}/{len(tl)}  {start:.1f}–{start + d:.1f}s")
    joined = tmp / "joined.mp4"
    join(segs, joined)
    mix(ad, tl, total, joined, prof, out)
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
    verify = HUASHU / "scripts/verify-video.sh"
    if verify.exists():
        r = subprocess.run(["bash", str(verify), str(path), f"--width={prof['w']}", f"--height={prof['h']}",
                            f"--fps={FPS}"], capture_output=True, text=True)
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
    fw, fh = 540, 960
    beats = "".join(f"<li>{rich(b.strip(), c['accent'])}</li>" for b in args.beats.split("|") if b.strip())
    html = f"""<html><head><style>{font_css(ad)}
body{{width:1440px;height:1040px;background:{c['bg']};color:{c['fg']};display:flex;gap:56px;padding:40px 56px;align-items:center}}
.f{{position:relative;width:{fw}px;height:{fh}px;border-radius:28px;overflow:hidden;flex:none;background:#000}}
.f img{{width:100%;height:100%;object-fit:contain}}
.h{{position:absolute;left:6%;right:6%;top:3.5%;text-align:center}}
.h span.p{{display:inline-block;background:rgba(10,8,20,.62);padding:10px 20px;border-radius:14px;font-size:40px;
font-weight:900;line-height:1.08;-webkit-text-stroke:3px {c['stroke']};paint-order:stroke fill}}
.t{{font-size:56px;font-weight:900;letter-spacing:-.02em}}.k{{opacity:.7;font-size:24px;margin:8px 0 28px}}
li{{font-size:28px;line-height:1.35;margin:10px 0}}</style></head>
<body><div class=f><img src='{data_uri(frame)}'><div class=h><span class=p>{rich(args.hook, c['accent'])}</span></div></div>
<div><div class=t>{rich(args.title, c['accent'])}</div><div class=k>hook frame from {Path(args.take).name} @ {args.at}s</div>
<ol>{beats}</ol></div></body></html>"""
    with Renderer() as r:
        r.png(html, 1440, 1040, args.out, transparent=False)
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
    elif a.cmd == "render":
        ad = load_ad(a.ad)
        name = {"ua": "ad-ua-9x16.mp4", "app-preview": "app-preview-886x1920.mp4"}[a.profile]
        render(ad, a.profile, Path(a.out) if a.out else ad["_dir"] / name, a.force)
    elif a.cmd == "check":
        sys.exit(0 if check(a.file, a.profile, load_ad(a.ad) if a.ad else None) else 1)


if __name__ == "__main__":
    main()
