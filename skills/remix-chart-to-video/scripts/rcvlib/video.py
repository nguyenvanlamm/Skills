"""m10-visualizer: render the video in one of two looks, and check what came out.

The visualizer always draws its logo at the frame centre with a spectrum ring around it, which
sits on top of the tracklist that m10-mixcover draws on the cover. Two looks deal with that:

  visualizer   the channel's look, as in m10-visualizer's own output: the logo in the centre
               growing and shrinking on the beat, the spectrum ring and particles around it,
               over the AI picture. With `video.tracklist: side` (the default) the picture has a
               column at the far side, clear of the ring: the title `video.side_title` ("remix
               nhạc hot tiktok") above the numbered song list; with `none` it carries no text.
  cover        cover.png (with tracklist) as background, overlays off and a fully transparent
               logo, so the text stays readable.

In both the background stands still (`video.background_still`): no shake and no beat zoom.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from . import config as cfgmod
from . import ffmpeg
from .common import SKILL_DIR, RcvError, check, read_json

LOOKS = ('cover', 'visualizer')
TQDM = re.compile(r'(\d+)%\|.*?(\d+)/(\d+)\s+\[([^<\]]+)<([^,\]]+)')


def look_args(cfg: dict, run_dir: Path, look: str, provisional: bool = False) -> tuple[list[str], list[str]]:
    """Command-line arguments for a look, and notes about anything substituted."""
    vz = cfgmod.repo(cfg, 'visualizer')
    notes = []
    still = cfg['video'].get('background_still', True)
    hold = ['effects.shake.enabled=false', 'effects.bg_zoom.enabled=false'] if still else []     # the picture does not move
    if look == 'cover':
        bg = run_dir / 'cover' / 'cover.png'
        if not bg.is_file() or provisional:
            bg = run_dir / 'art' / 'provisional_cover.png'
            notes.append('ảnh bìa tạm (chưa có mốc thời gian)')
        if not bg.is_file():
            raise RcvError('Chưa có ảnh bìa để dùng cho kiểu hình "cover".')
        sets = ['background.dim=0', 'effects.vignette.enabled=false', 'effects.circular_spectrum.enabled=false',
                'effects.particles.enabled=false', 'effects.logo_pulse.enabled=false']
        sets += hold if still else ['effects.shake.enabled=false', f'effects.bg_zoom.amount={cfg["video"]["cover_zoom_amount"]}']
        args = ['--bg', str(bg), '--logo', str(SKILL_DIR / 'assets' / 'transparent.png')]
    elif look == 'visualizer':
        raw = run_dir / 'art' / 'raw.png'
        logo = vz / 'assets' / 'M10-logo-mark.png'
        args, sets = [], list(hold)                          # the logo keeps its pulse: only the background is held
        final_bg, draft_bg = run_dir / 'video' / 'background.png', run_dir / 'art' / 'provisional_side.png'
        side = cfg['video'].get('tracklist', 'side') == 'side'
        if side and final_bg.is_file() and not provisional:
            args += ['--bg', str(final_bg)]
        elif side and draft_bg.is_file():
            args += ['--bg', str(draft_bg)]
            notes.append('nền video tạm vẽ ở S3')
        elif raw.is_file():
            args += ['--bg', str(raw)]
            if side:
                notes.append('chưa có nền video có danh sách bài: dùng ảnh không chữ')
        else:
            notes.append('không có ảnh DJ gốc: dùng nền mặc định của visualizer')
        if '--bg' in args and args[args.index('--bg') + 1] != str(raw):
            sets += ['background.dim=0', 'effects.vignette.enabled=false']     # keep the text at the contrast mixcover gave it
        if logo.is_file():
            args += ['--logo', str(logo)]
    else:
        raise RcvError(f'Kiểu hình không hợp lệ: {look} (cover | visualizer)', 2)
    for item in sets:
        args += ['--set', item]
    return args, notes


def run_visualizer(cfg: dict, audio: Path, out: Path, extra: list[str], log: Path, start: float | None = None,
                   duration: float | None = None, on_progress=None, ctx=None) -> dict:
    vz = cfgmod.repo(cfg, 'visualizer')
    vid = cfg['video']
    cmd = [str(vz / '.venv' / 'bin' / 'python'), str(vz / 'main.py'), str(audio), '--preset', vid['preset'],
           '--fps', str(vid['fps']), '--size', vid['size'], '-o', str(out), *extra]
    if vid.get('workers'):
        cmd += ['--workers', str(vid['workers'])]
    if start is not None:
        cmd += ['--start', f'{start:.3f}']
    if duration is not None:
        cmd += ['--duration', f'{duration:.3f}']
    out.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(cmd, cwd=str(vz), stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    if ctx is not None:
        ctx.children.append(proc)
    captured = {'out': b'', 'err_tail': b'', 'warnings': []}

    def read_out():
        captured['out'] = proc.stdout.read()

    def read_err():
        buf = b''
        while chunk := proc.stderr.read(4096):
            buf = (buf + chunk)[-65536:]
            captured['err_tail'] = buf
            last = re.split(rb'[\r\n]', buf)[-2:] if b'%|' in buf else []
            for piece in last:
                m = TQDM.search(piece.decode(errors='replace'))
                if m and on_progress:
                    on_progress(int(m.group(1)), m.group(5).strip())
            for line in re.findall(rb'C\xe1\xba\xa3nh b\xc3\xa1o: [^\r\n]+', chunk):
                text = line.decode(errors='replace')
                if text not in captured['warnings']:
                    captured['warnings'].append(text)

    threads = [threading.Thread(target=read_out, daemon=True), threading.Thread(target=read_err, daemon=True)]
    for t in threads:
        t.start()
    started = time.time()
    try:
        proc.wait()
    finally:
        if ctx is not None and proc in ctx.children:
            ctx.children.remove(proc)
    for t in threads:
        t.join(timeout=10)
    text = captured['out'].decode(errors='replace')
    err = captured['err_tail'].decode(errors='replace')
    log.write_text(text + '\n--- stderr (tail) ---\n' + re.sub(r'[^\n]*\r', '', err)[-6000:], encoding='utf-8')
    return {'code': proc.returncode, 'stdout': text, 'stderr': err, 'warnings': captured['warnings'],
            'seconds': round(time.time() - started, 1), 'cmd': cmd}


def check_video(cfg: dict, video: Path, expect_duration: float, look: str, cover_png: Path | None,
                frames_dir: Path, at: float | None = None, text_side: str | None = None,
                column_inner: float | None = None) -> tuple[list[dict], dict]:
    vid = cfg['video']
    checks = []
    info = ffmpeg.probe(video)
    v, a = info['video'], info['audio']
    want_w, want_h = (int(x) for x in vid['size'].lower().split('x'))
    ok = bool(v) and v['codec'] == 'h264' and (v['width'], v['height']) == (want_w, want_h) and abs(v['fps'] - vid['fps']) < 0.01
    checks.append(check('video_stream', 'PASS' if ok else 'FAIL',
                        f'{v and v["codec"]} {v and v["width"]}x{v and v["height"]} @ {v and round(v["fps"], 2)} fps'))
    checks.append(check('audio_stream', 'PASS' if a and a['codec'] == 'aac' else 'FAIL',
                        f'{a and a["codec"]} {a and a["sample_rate"]} Hz' if a else 'không có luồng âm thanh'))
    diff = abs(info['duration'] - expect_duration)
    checks.append(check('video_length', 'PASS' if diff <= vid['duration_tolerance_s'] else 'FAIL',
                        f'video {info["duration"]:.3f}s, âm thanh {expect_duration:.3f}s, lệch {diff:.3f}s'))
    frame = ffmpeg.extract_frame(video, at if at is not None else info['duration'] / 2, frames_dir / f'frame_{look}.png')
    extra = {'frame': str(frame), 'duration': info['duration'], 'size_bytes': info['size']}
    if look == 'cover' and cover_png and cover_png.is_file():
        score = ffmpeg.ssim(frame, cover_png, '640:360')     # coarse scale: the slight zoom barely moves it, an overlay does
        extra['cover_ssim'] = round(score, 4)
        checks.append(check('cover_readable', 'PASS' if score >= vid['min_cover_ssim'] else 'FAIL',
                            f'khung hình giống cover.png {score:.3f} (ngưỡng {vid["min_cover_ssim"]}); '
                            + ('chữ không bị lớp phủ che' if score >= vid['min_cover_ssim'] else 'lớp phủ có thể đang che chữ')))
    elif look == 'visualizer' and cover_png and cover_png.is_file():
        # A ring that reached the side column would hit its inner edge first. Compare that strip of the
        # frame with the background: bars drawn over it raise the mean difference several times over.
        side = text_side or 'right'
        inner = column_inner if column_inner else 1 - 0.031 - float(vid['side_column_width'])
        x = inner - 0.01 if side == 'right' else 1 - inner - 0.05
        score = ffmpeg.luma_diff(frame, cover_png, f'iw*0.06:ih*0.8:iw*{x:.4f}:ih*0.2')
        extra['side_diff'] = round(score, 1)
        ok = score <= vid['max_side_diff']
        checks.append(check('tracklist_readable', 'PASS' if ok else 'FAIL',
                            f'mép trong của cột chữ (bên {"phải" if side == "right" else "trái"}) lệch nền {score:.0f}/255 '
                            f'(ngưỡng {vid["max_side_diff"]}); ' + ('vòng phổ không đè lên cột chữ' if ok else
                                                                   'có gì đó đang đè lên cột chữ')))
    else:
        checks.append(check('cover_readable', 'SKIP', f'kiểu "{look}" không có chữ trên nền: xem khung hình {frame}'))
    return checks, extra


def render_final(run_dir, cfg: dict, state, ctx=None):
    run_dir = Path(run_dir)
    look = cfg['video']['look']
    audio = run_dir / 'mix.wav'
    mixinfo = read_json(run_dir / 'mix' / 'mix_report.json')
    if not audio.is_file() or not mixinfo:
        raise RcvError('Chưa có mix.wav: chặng ghép mix chưa xong.')
    extra, notes = look_args(cfg, run_dir, look)
    out = run_dir / 'video' / 'video.mp4'
    out.unlink(missing_ok=True)

    def progress(percent, eta):
        state.progress('video', percent=percent, text=f'render {percent}% · còn khoảng {eta}')

    state.progress('video', text='phân tích nhạc', percent=0, force=True)
    res = run_visualizer(cfg, audio, out, extra, run_dir / 'logs' / 'visualizer.log', on_progress=progress, ctx=ctx)
    if ctx is not None and ctx.should_stop():
        from .stemforge import Interrupted
        raise Interrupted()
    if res['code'] != 0 or not out.is_file():
        raise RcvError(f'm10-visualizer lỗi (mã {res["code"]}): {res["stderr"].strip()[-400:]}')
    bg = Path(extra[extra.index('--bg') + 1]) if '--bg' in extra else None
    with_text = bg if bg and bg.name != 'raw.png' else None                  # the background the frame is compared with
    bginfo = read_json(run_dir / 'video' / 'background.json') or {}
    checks, info = check_video(cfg, out, mixinfo['duration'], look, with_text, run_dir / 'video' / 'frames',
                               text_side=bginfo.get('text_side'), column_inner=(bginfo.get('geometry') or {}).get('column_inner_frac'))
    if res['warnings']:
        checks.append(check('visualizer_warnings', 'WARN', '; '.join(res['warnings'][:3])))
    for note in notes:
        checks.append(check('look_substitution', 'WARN', note))
    top = run_dir / 'video.mp4'
    top.unlink(missing_ok=True)
    try:
        os.link(out, top)
    except OSError:
        shutil.copyfile(out, top)
    info.update(look=look, render_seconds=res['seconds'], video=str(top))
    return checks, info


def preview(run_dir, cfg: dict, looks=LOOKS, seconds: float = 8.0) -> dict:
    """Short clips of each look, for the first-run choice. Uses whatever exists already: the
    provisional cover and any audio at hand, so it can run before the long stages."""
    run_dir = Path(run_dir)
    manifest = read_json(run_dir / 'manifest.json') or {}
    mixinfo = read_json(run_dir / 'mix' / 'mix_report.json')
    provisional = not (run_dir / 'cover' / 'cover.png').is_file()
    audio, start, source = None, 45.0, None
    if (run_dir / 'mix.wav').is_file() and mixinfo:
        audio, source = run_dir / 'mix.wav', 'bản mix'
        if len(mixinfo['tracks']) > 1:
            start = max(0.0, mixinfo['tracks'][1]['start_seconds'] - seconds / 2)
    else:
        for tr in manifest.get('tracks', []):
            remix = run_dir / 'remix' / tr['slug'] / 'final.wav'
            if remix.is_file():
                audio, source = remix, f'bản phối "{tr["title"]}"'
                break
        if audio is None and manifest.get('tracks'):
            audio, source = Path(manifest['tracks'][0]['source']['path']), f'bản gốc "{manifest["tracks"][0]["title"]}" (chưa phối)'
    if audio is None or not Path(audio).is_file():
        raise RcvError('Chưa có đoạn nhạc nào để dựng bản xem thử.')
    out = {'audio': str(audio), 'audio_is': source, 'provisional': provisional or source != 'bản mix', 'looks': {}}
    for look in looks:
        extra, notes = look_args(cfg, run_dir, look, provisional)
        clip = run_dir / 'video' / f'preview_{look}.mp4'
        res = run_visualizer(cfg, Path(audio), clip, extra, run_dir / 'logs' / f'preview_{look}.log', start=start, duration=seconds)
        if res['code'] != 0 or not clip.is_file():
            raise RcvError(f'Không dựng được bản xem thử "{look}": {res["stderr"].strip()[-300:]}')
        bg = Path(extra[extra.index('--bg') + 1]) if '--bg' in extra else None
        bginfo = read_json(run_dir / 'video' / 'background.json') or {}
        art = read_json(run_dir / 'art' / 'art.json') or {}
        geo = bginfo.get('geometry') or art.get('side_geometry') or {}
        checks, info = check_video(cfg, clip, seconds, look, bg if bg and bg.name != 'raw.png' else None,
                                   run_dir / 'video' / 'frames', at=seconds / 2,
                                   text_side=bginfo.get('text_side') or art.get('text_side'), column_inner=geo.get('column_inner_frac'))
        out['looks'][look] = {'clip': str(clip), 'frame': info['frame'], 'checks': checks, 'notes': notes,
                              'warnings': res['warnings'], 'render_seconds': res['seconds'],
                              'cover_ssim': info.get('cover_ssim'), 'side_diff': info.get('side_diff')}
    return out
