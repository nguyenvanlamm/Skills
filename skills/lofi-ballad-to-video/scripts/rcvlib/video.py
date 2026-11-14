"""m10-visualizer: render the video, and check what came out.

The channel has one look: the anime landscape standing still, the song list in a column at its
calm side (`video.tracklist: side`; `none` = the bare picture), and one horizontal bar spectrum
at the bottom centre, from m10-visualizer's `lofi` preset (`effects.bar_spectrum`; ring,
particles, shake and zoom off). The visualizer always draws a logo at the frame centre, so the
skill hands it a fully transparent one (`video.logo`). The picture is not dimmed and has no
vignette, so the frame is the background plus the bars, which is what the checks measure:
`bars_visible` (the strip of the bars differs from the picture), `center_clear` (the centre
does not) and `tracklist_readable` (nothing covers the column).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from . import config as cfgmod
from . import ffmpeg
from .common import SKILL_DIR, RcvError, check, fmt_ts, read_json, run

LOOKS = ('visualizer',)
TQDM = re.compile(r'(\d+)%\|.*?(\d+)/(\d+)\s+\[([^<\]]+)<([^,\]]+)')


def logo_path(cfg: dict) -> Path:
    raw = Path(str(cfg['video'].get('logo') or 'assets/transparent.png')).expanduser()
    return raw if raw.is_absolute() else SKILL_DIR / raw


def look_args(cfg: dict, run_dir: Path, look: str, provisional: bool = False) -> tuple[list[str], list[str]]:
    """Command-line arguments for the look, and notes about anything substituted."""
    if look not in LOOKS:
        raise RcvError(f'Kiểu hình không hợp lệ: {look} (chỉ có visualizer)', 2)
    notes = []
    still = cfg['video'].get('background_still', True)
    sets = ['effects.shake.enabled=false', 'effects.bg_zoom.enabled=false'] if still else []     # the picture does not move
    sets += ['background.dim=0', 'effects.vignette.enabled=false']     # the picture as painted, the text at mixcover's contrast
    raw = run_dir / 'art' / 'raw.png'
    args = []
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
            notes.append('chưa có nền video có danh sách bài: dùng tranh không chữ')
    else:
        notes.append('không có tranh: dùng nền mặc định của visualizer')
    logo = logo_path(cfg)
    if not logo.is_file():
        raise RcvError(f'Không thấy logo trong suốt {logo} (video.logo): không có nó, visualizer vẽ logo M10 ở giữa khung.')
    args += ['--logo', str(logo)]
    for item in sets:
        args += ['--set', item]
    return args, notes


def bar_strip(cfg: dict) -> str:
    """The region of the bar spectrum, from the visualizer preset's numbers (fractions of the
    frame), as an ffmpeg crop expression."""
    vz = cfgmod.repo(cfg, 'visualizer')
    code = ('import json, sys\nfrom visualizer.preset import load_preset\n'
            'b = load_preset(sys.argv[1], [])["effects"]["bar_spectrum"]\n'
            'print(json.dumps([b["width"], b["bottom"], b["min_length"] + b["max_length"]]))')
    rc, out, _ = run([vz / '.venv' / 'bin' / 'python', '-c', code, cfg['video']['preset']], cwd=str(vz), timeout=120)
    try:
        width, bottom, tall = (float(x) for x in json.loads(out.strip().splitlines()[-1]))
    except (ValueError, IndexError, TypeError):
        width, bottom, tall = 0.42, 0.07, 0.094
    if rc != 0:
        width, bottom, tall = 0.42, 0.07, 0.094
    w, h = width * 0.9, tall * 0.8                  # inside the band: the bars' lower part, where even quiet bars are
    return f'iw*{w:.4f}:ih*{h:.4f}:iw*{(1 - w) / 2:.4f}:ih*{1 - bottom - h:.4f}'


def run_visualizer(cfg: dict, audio: Path, out: Path, extra: list[str], log: Path, start: float | None = None,
                   duration: float | None = None, on_progress=None, ctx=None) -> dict:
    vz = cfgmod.repo(cfg, 'visualizer')
    vid = cfg['video']
    preset = [] if '--preset' in extra else ['--preset', vid['preset']]     # look_args may name the run's own preset
    cmd = [str(vz / '.venv' / 'bin' / 'python'), str(vz / 'main.py'), str(audio), *preset,
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
                column_inner: float | None = None, mix_loudness: dict | None = None,
                background: Path | None = None) -> tuple[list[dict], dict]:
    """`cover_png`: the background with the text column (for `tracklist_readable`);
    `background`: the picture the frame was drawn on (for `bars_visible` and `center_clear`)."""
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
    # Each stream against the mix, not the container: a file is as long as its longest stream,
    # so a picture that stopped early would hide behind a complete sound track.
    tol = vid['duration_tolerance_s']
    lens = {'hình': v['duration'] if v else None, 'tiếng': a['duration'] if a else None}
    off = {k: None if d is None else abs(d - expect_duration) for k, d in lens.items()}
    good = all(d is not None and d <= tol for d in off.values())
    checks.append(check('video_length', 'PASS' if good else 'FAIL',
                        f'bản mix {expect_duration:.3f}s; ' + ', '.join(
                            f'luồng {k} {lens[k]:.3f}s (lệch {off[k]:.3f}s)' if lens[k] is not None else f'không có luồng {k}'
                            for k in lens) + f'; cho phép lệch {tol}s'))
    frame = ffmpeg.extract_frame(video, at if at is not None else info['duration'] / 2, frames_dir / f'frame_{look}.png')
    extra = {'frame': str(frame), 'duration': info['duration'], 'size_bytes': info['size']}
    if mix_loudness and a:
        # What people hear is the encoded track, not mix.wav: measure it, against the mix.
        got = ffmpeg.loudness(video)
        extra['loudness'] = got
        drift = abs(got['integrated_lufs'] - mix_loudness['integrated_lufs'])
        notes = []
        if drift > vid['loudness_tolerance_lu']:
            notes.append(f'lệch bản mix {drift:.1f} LU (cho phép {vid["loudness_tolerance_lu"]})')
        if got['true_peak_dbtp'] > vid['true_peak_max_dbtp']:
            # AAC coding overshoots at single loud moments. Say where the worst one is, so the
            # human can listen there instead of guessing whether it matters.
            step, worst_at, worst = 120.0, 0.0, float('-inf')
            t = 0.0
            while t < info['duration']:
                try:
                    peak = ffmpeg.loudness(video, t, step)['true_peak_dbtp']
                except RcvError:
                    peak = float('-inf')
                if peak > worst:
                    worst_at, worst = t, peak
                t += step
            notes.append(f'sau khi nén AAC, true peak vượt {vid["true_peak_max_dbtp"]} dBTP ở vài chỗ (cao nhất trong đoạn '
                         f'{fmt_ts(worst_at)}–{fmt_ts(min(info["duration"], worst_at + step))}): nghe đoạn đó xem có vỡ tiếng không')
        checks.append(check('video_loudness', 'WARN' if notes else 'PASS',
                            f'tiếng trong video {got["integrated_lufs"]:.1f} LUFS, true peak {got["true_peak_dbtp"]:.2f} dBTP '
                            f'(bản mix {mix_loudness["integrated_lufs"]:.1f} LUFS, {mix_loudness["true_peak_dbtp"]:.2f} dBTP)'
                            + ('; ' + '; '.join(notes) if notes else '')))
    if background and Path(background).is_file():
        bars = ffmpeg.luma_diff(frame, background, bar_strip(cfg))
        mid = ffmpeg.luma_diff(frame, background, 'iw*0.2:ih*0.2:iw*0.4:ih*0.4')
        extra.update(bars_diff=round(bars, 1), center_diff=round(mid, 1))
        checks.append(check('bars_visible', 'PASS' if bars >= vid['min_bars_diff'] else 'FAIL',
                            f'dải thanh sóng âm ở giữa cạnh dưới lệch tranh {bars:.1f}/255 (cần ≥ {vid["min_bars_diff"]})'
                            + ('' if bars >= vid['min_bars_diff'] else ': không thấy thanh sóng âm trong khung hình')))
        checks.append(check('center_clear', 'PASS' if mid <= vid['max_center_diff'] else 'FAIL',
                            f'giữa khung lệch tranh {mid:.1f}/255 (cho phép ≤ {vid["max_center_diff"]})'
                            + ('' if mid <= vid['max_center_diff'] else ': có thứ gì đó (logo, vòng phổ) đang vẽ ở giữa khung')))
    if cover_png and cover_png.is_file():
        # Bars that reached the side column would hit its inner edge first. Compare that strip of the
        # frame with the background: bars drawn over it raise the mean difference several times over.
        side = text_side or 'right'
        inner = column_inner if column_inner else 1 - 0.031 - float(vid['side_column_width'])
        x = inner - 0.01 if side == 'right' else 1 - inner - 0.05
        score = ffmpeg.luma_diff(frame, cover_png, f'iw*0.06:ih*0.8:iw*{x:.4f}:ih*0.2')
        extra['side_diff'] = round(score, 1)
        ok = score <= vid['max_side_diff']
        checks.append(check('tracklist_readable', 'PASS' if ok else 'FAIL',
                            f'mép trong của cột chữ (bên {"phải" if side == "right" else "trái"}) lệch nền {score:.0f}/255 '
                            f'(ngưỡng {vid["max_side_diff"]}); ' + ('thanh sóng âm không đè lên cột chữ' if ok else
                                                                   'có gì đó đang đè lên cột chữ')))
    else:
        checks.append(check('tracklist_readable', 'SKIP', f'nền video không có cột chữ: xem khung hình {frame}'))
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
                               text_side=bginfo.get('text_side'), column_inner=(bginfo.get('geometry') or {}).get('column_inner_frac'),
                               mix_loudness=mixinfo.get('loudness'), background=bg)
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
    """A short clip of the look, to show the human before the long stages. Uses whatever exists
    already: the provisional background and any audio at hand."""
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
                                   text_side=bginfo.get('text_side') or art.get('text_side'), column_inner=geo.get('column_inner_frac'),
                                   background=bg)
        out['looks'][look] = {'clip': str(clip), 'frame': info['frame'], 'checks': checks, 'notes': notes,
                              'warnings': res['warnings'], 'render_seconds': res['seconds'],
                              'bars_diff': info.get('bars_diff'), 'center_diff': info.get('center_diff'),
                              'side_diff': info.get('side_diff')}
    return out
