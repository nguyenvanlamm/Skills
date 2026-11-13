"""m10-mixcover: fetch the AI picture early, draw the cover and thumbnail after the mix exists."""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
from pathlib import Path

from . import center
from . import config as cfgmod
from . import ffmpeg
from .common import SKILL_DIR, RcvError, check, digest, fold, parse_ts, read_json, run, sha256_file, write_json, write_text

CACHE_LINE = re.compile(r'(vừa tạo|lấy từ cache \(không tốn tiền\)):\s*(\S.*?)\s+seed=(\d+)')
SIDE_LINE = re.compile(r'cô gái ở (?:1/3 )?bên (trái|phải)')
CUT_LINE = re.compile(r"(\d+) dòng cắt")
SIDE_HELPER = SKILL_DIR / 'scripts' / 'mixcover_helpers' / 'side_text.py'
SIDE_TITLE_FONT = SKILL_DIR / 'assets' / 'fonts' / 'Anton-Regular.ttf'     # OFL, full Vietnamese; licence next to it


def cut_lines(output: str) -> int:
    """How many text lines m10-mixcover had to shorten with an ellipsis."""
    m = CUT_LINE.search(output)
    return int(m.group(1)) if m else 0


def side_title(cfg: dict) -> str:
    """The title above the song list on the video background (`video.side_title`); "" = none."""
    return ' '.join(str(cfg['video'].get('side_title') or '').split())


def wants_side(cfg: dict) -> bool:
    return cfg['video'].get('tracklist', 'side') == 'side'


def side_signature(cfg: dict) -> str:
    """What the side column looks like: its title, its limits and the code that draws it. Part
    of the art and cover stage hashes, so a change to any of them draws it again."""
    vid = cfg['video']
    keys = ('tracklist', 'side_column_width', 'side_title_min_size', 'side_track_max', 'side_track_min')
    return digest([side_title(cfg), {k: vid.get(k) for k in keys}, SIDE_TITLE_FONT.name,
                   sha256_file(SIDE_HELPER) if SIDE_HELPER.is_file() else None])


POSTER_KEYS = ('thumb_style', 'poster_tracks', 'poster_column_width', 'poster_title_min_size', 'poster_track_max', 'poster_track_min')
THUMB_SIZE = (1280, 720)
POSTER_TITLE_MAX_H, POSTER_TITLE_BLOCK_H = 0.30, 0.62       # the title may be this large on a thumbnail


def wants_poster(cfg: dict) -> bool:
    return cfg['cover'].get('thumb_style', 'poster') == 'poster'


def poster_signature(cfg: dict) -> list:
    return [cfg['cover'].get(k) for k in POSTER_KEYS]


def draw_poster(cfg: dict, tracks: list[dict], title: str, out_jpg: Path, raw: Path | None, side: str,
                name: str) -> tuple[dict | None, list[dict]]:
    """The thumbnail as a poster: the picture, and at the side away from the DJ the cover's
    title in large slanted letters above the first `cover.poster_tracks` songs and a line
    "+ N bài khác". A thumbnail is shown about 320 px wide: the cover scaled down has ten song
    lines of 17 px, which nobody reads at that size. Drawn by the same helper as the video's
    side column, at 1280x720."""
    repo, python = _python(cfg)
    cov = cfg['cover']
    w, h = THUMB_SIZE
    px = lambda key: max(1, round(float(cov[key]) * h))  # noqa: E731
    shown = tracks[:max(0, int(cov['poster_tracks']))]
    rest = len(tracks) - len(shown)
    spec = {'repo': str(repo), 'preset': str(cov['preset']), 'out': str(out_jpg), 'size': [w, h],
            'raw': str(raw) if raw and Path(raw).is_file() else None, 'side': side,
            'column_width': float(cov['poster_column_width']), 'title': title, 'title_font': str(SIDE_TITLE_FONT),
            'tracks': [t['title'] for t in shown], 'footer': f'+ {rest} bài khác' if rest and shown else '',
            'title_min_px': px('poster_title_min_size'), 'track_max_px': px('poster_track_max'), 'track_min_px': px('poster_track_min'),
            'title_max_h': POSTER_TITLE_MAX_H, 'title_block_h': POSTER_TITLE_BLOCK_H}
    out_jpg.unlink(missing_ok=True)
    rc, out, err = run([str(python), str(SIDE_HELPER), json.dumps(spec, ensure_ascii=False)], cwd=str(repo), timeout=300)
    try:
        info = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        info = None
    if rc != 0 or not info or not out_jpg.is_file():
        return None, [check(name, 'FAIL', f'không vẽ được thumbnail kiểu poster (mã {rc}): {(err or out).strip()[-200:]}')]
    ok = ffmpeg.image_size(out_jpg) == THUMB_SIZE and info['fits']
    detail = (f'{w}x{h}, tiêu đề "{" / ".join(info["title_lines"])}" cỡ {"–".join(str(s) for s in sorted(set(info["title_sizes"])))} px, '
              f'{len(shown)} bài cỡ {info["track_px"]} px' + (f', "+ {rest} bài khác"' if rest and shown else '')) if ok else \
        (f'tiêu đề "{title}" và {len(shown)} bài không vừa thumbnail kể cả ở cỡ nhỏ nhất: rút ngắn cover.title, giảm cover.poster_tracks, '
         'hoặc `pipeline.py set cover.thumb_style tracklist`')
    checks = [check(name, 'PASS' if ok else 'FAIL', detail)]
    if info['cut']:
        checks.append(check(f'{name}_warnings', 'WARN', f'{info["cut"]} tên bài trên thumbnail bị cắt bằng "…"'))
    return info, checks


def text_side(output: str) -> str:
    """Where the column goes, from m10-mixcover's face detection: away from the DJ."""
    m = SIDE_LINE.search(output)
    return 'left' if m and m.group(1) == 'phải' else 'right'


def draw_side(cfg: dict, tracks: list[dict], out_png: Path, raw: Path | None, side: str,
              name: str) -> tuple[dict | None, list[dict]]:
    """The video background of the "visualizer" look: the picture with a column at the side
    away from the DJ, `video.side_column_width` of the frame inside mixcover's margin so the
    spectrum ring cannot reach it. In it, the title `video.side_title` (a slanted poster block in
    Anton, each line filling the column, white and lime in turn, a solid pink copy behind) above
    the song list, one line per song in playing order: the number in lime and the title in
    white, no artist, no time. The list keeps the largest row size (`video.side_track_max` down
    to `side_track_min`) that leaves the title room with no line below `side_title_min_size`;
    the title takes the rest. Drawn by `scripts/mixcover_helpers/side_text.py` with
    m10-mixcover's Pillow and its list fonts and colours, and the skill's Anton.
    Returns what the helper measured and the checks `name` and `name_warnings`."""
    repo, python = _python(cfg)
    vid = cfg['video']
    w, h = (int(x) for x in vid['size'].lower().split('x'))
    px = lambda key: max(1, round(float(vid[key]) * h))
    spec = {'repo': str(repo), 'preset': str(cfg['cover']['preset']), 'out': str(out_png), 'size': [w, h],
            'raw': str(raw) if raw and Path(raw).is_file() else None, 'side': side,
            'column_width': float(vid['side_column_width']), 'title': side_title(cfg), 'title_font': str(SIDE_TITLE_FONT),
            'tracks': [t['title'] for t in tracks],
            'title_min_px': px('side_title_min_size'), 'track_max_px': px('side_track_max'), 'track_min_px': px('side_track_min')}
    for stale in (out_png, out_png.parent / 'side_preset.yaml', out_png.parent / 'tracks_side.csv'):
        stale.unlink(missing_ok=True)                    # the last two were left by versions that had mixcover draw it
    rc, out, err = run([str(python), str(SIDE_HELPER), json.dumps(spec, ensure_ascii=False)], cwd=str(repo), timeout=300)
    try:
        info = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        info = None
    if rc != 0 or not info or not out_png.is_file():
        return None, [check(name, 'FAIL', f'không vẽ được cột chữ ở mép nền video (mã {rc}): {(err or out).strip()[-200:]}')]
    size = ffmpeg.image_size(out_png)
    where = 'phải' if side == 'right' else 'trái'
    ok = size == (w, h) and info['fits'] and info['tracks'] == len(tracks)
    head = (f'tiêu đề "{" / ".join(info["title_lines"])}" ({info["title_font"]}, '
            f'{"–".join(str(s) for s in sorted(set(info["title_sizes"])))} px) trên ') if info['title_lines'] else ''
    detail = (f'{size[0]}x{size[1]}, {head}{info["tracks"]} bài đánh số cỡ {info["track_px"]} px, '
              f'mép {where}, cột {info["column"][0]}–{info["column"][1]} px')
    if not ok:
        detail = (f'{size[0]}x{size[1]}, tiêu đề và {len(tracks)} bài không vừa cột kể cả ở cỡ nhỏ nhất '
                  f'(tiêu đề {spec["title_min_px"]} px, bài {spec["track_min_px"]} px): rút ngắn video.side_title hoặc bớt bài')
    checks = [check(name, 'PASS' if ok else 'FAIL', detail)]
    notes = []
    if info['cut']:
        notes.append(f'{info["cut"]} tên bài bị cắt bằng "…" (quá dài so với cột)')
    if info['contrast'] is not None and info['contrast'] < 4.5:
        notes.append(f'tương phản thấp nhất của danh sách {info["contrast"]}:1, dưới 4.5:1 dù nền đã tối tới {info["panel_opacity"]}')
    if notes:
        checks.append(check(f'{name}_warnings', 'WARN', '; '.join(notes)))
    return info, checks


def side_geometry(cfg: dict, preset: str | None = None) -> dict | None:
    """Can the spectrum ring reach the side column? Both tools size things as fractions of
    the frame, so this is arithmetic on their presets: the ring's farthest bar tip (radius with
    its bass pulse, the gap, the longest bar and its cap) against the column's inner edge.
    `preset` is the run's own visualizer preset (its centre), else `video.preset`."""
    vz, (mc, mc_python) = cfgmod.repo(cfg, 'visualizer'), _python(cfg)
    ring = ('import json, sys\nfrom visualizer.preset import load_preset\n'
            'c = load_preset(sys.argv[1], [])["effects"]["circular_spectrum"]\n'
            'print(c["radius"] * (1 + c.get("ring_pulse", 0)) + c["inner_ring"]["gap"] + c["min_length"]'
            ' + c["max_length"] * (1 + c.get("peak_cap", 0)))')
    rc1, out1, _ = run([vz / '.venv' / 'bin' / 'python', '-c', ring, preset or cfg['video']['preset']], cwd=str(vz), timeout=120)
    rc2, out2, _ = run([mc_python, '-c', 'import sys\nfrom mixcover.preset import Preset\n'
                                         'print(Preset.load(sys.argv[1]).get("layout.margin"))', cfg['cover']['preset']],
                       cwd=str(mc), timeout=120)
    try:
        reach, margin = float(out1.strip()), float(out2.strip())
    except ValueError:
        return None
    if rc1 != 0 or rc2 != 0:
        return None
    w, h = (int(x) for x in cfg['video']['size'].lower().split('x'))
    column_inner = w - margin * h - float(cfg['video']['side_column_width']) * w       # px from the left, text on the right
    ring_edge = w / 2 + reach * h
    return {'ring_reach_h': round(reach, 4), 'margin_h': margin, 'column_inner_px': round(column_inner),
            'ring_edge_px': round(ring_edge), 'clear_px': round(column_inner - ring_edge),
            'column_inner_frac': round(column_inner / w, 4)}


def _python(cfg: dict) -> tuple[Path, Path]:
    repo = cfgmod.repo(cfg, 'mixcover')
    return repo, repo / '.venv' / 'bin' / 'python'


def texts(cfg: dict, manifest: dict) -> tuple[str, str]:
    date = (manifest.get('chart') or {}).get('date') or ''
    year, month = (date.split('-') + ['', ''])[:2]
    fields = {'count': len(manifest['playlist']), 'year': year, 'month': month.lstrip('0'), 'date': date}
    template = cfg['cover']['title'] if manifest.get('exact_top') else cfg['cover']['title_inexact']
    return template.format(**fields), cfg['cover']['subtitle'].format(**fields)


def seed_for(cfg: dict, manifest: dict) -> int:
    if cfg['cover'].get('seed') is not None:
        return int(cfg['cover']['seed'])
    digits = re.sub(r'\D', '', (manifest.get('chart') or {}).get('date') or '') or '10'
    return int(digits) % 2147483647


def _csv(rows: list[list[str]]) -> str:
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue()


def playlist_tracks(manifest: dict) -> list[dict]:
    by_id = {t['id']: t for t in manifest['tracks']}
    return [by_id[p['track']] for p in manifest['playlist']]


def art_signature(run_dir, cfg: dict, manifest: dict) -> str:
    """What the human approves at the picture stop: this picture with these text lines (the
    cover's two and the video background's title), and the video's centre. A new picture, new
    text or another centre is a new signature, so it is shown again."""
    raw = Path(run_dir) / 'art' / 'raw.png'
    title, subtitle = texts(cfg, manifest)
    own = center.run_files(run_dir, cfg)
    return digest([sha256_file(raw) if raw.is_file() else 'no-picture', title, subtitle, side_title(cfg)]
                  + ([poster_signature(cfg)] if wants_poster(cfg) else [])      # the thumbnail is part of what they approve
                  + ([own['key']] if own else []))


def review_message(run_dir, cfg: dict, manifest: dict, info: dict, checks: list[dict] | None = None) -> str:
    """What the human reads when the run stops after the picture stage."""
    run_dir = Path(run_dir)
    title, subtitle = texts(cfg, manifest)
    how = {'provider': f'ảnh AI, seed {info.get("seed")}' + (' (lấy từ cache)' if info.get('cached') else ' (vừa tạo)'),
           'image': 'ảnh do bạn đưa', 'dry_run': 'nền gradient, không có ảnh DJ'}.get(info.get('mode'), str(info.get('mode')))
    lines = ['Xem ảnh bìa ở S3 rồi trả lời: ok (ưng), redo (ảnh khác), image (dùng ảnh của bạn), hoặc nói chữ cần sửa.',
             f'  Ảnh bìa tạm (có tên bài, chưa có mốc thời gian): {run_dir / "art" / "provisional_cover.png"}']
    if (run_dir / 'art' / 'provisional_side.png').is_file():
        lines.append(f'  Nền video (tiêu đề "{side_title(cfg).upper()}" trên danh sách bài đánh số, không tên ca sĩ, '
                     f'không mốc thời gian, ở mép; logo sẽ nằm giữa): '
                     f'{run_dir / "art" / "provisional_side.png"}')
    if (run_dir / 'art' / 'provisional_thumb.jpg').is_file():
        lines.append(f'  Thumbnail (kiểu poster: tiêu đề lớn và {cfg["cover"]["poster_tracks"]} bài đầu, đọc được ở cỡ YouTube hiển thị): '
                     f'{run_dir / "art" / "provisional_thumb.jpg"}')
    if info.get('raw'):
        lines.append(f'  Ảnh không chữ: {info["raw"]}')
    cen = info.get('center')
    if cen:
        frame = info.get('center_frame')
        lines.append(f'  Phần giữa video (logo M10 giữ nguyên): {cen["labels"]}, còn {cen["unused"]}/{cen["total"]} tổ hợp chưa dùng'
                     + (f'; khung hình: {frame}' if frame else '; khung hình có ở bản xem thử của hai kiểu hình'))
    lines += [f'  Nguồn ảnh: {how}',
              f'  Chữ trên ảnh: "{title}" / "{subtitle}"']
    # Things the human should know before saying "ok": a check of the picture that already
    # failed (approving it would only fail the stage on the next run), and two titles that differ.
    for c in checks or []:
        if c['status'] == 'FAIL':
            lines.append(f'  LỖI cần sửa trước khi duyệt · {c["name"]}: {c["detail"]}')
    video_title = side_title(cfg)
    if video_title and (run_dir / 'art' / 'provisional_side.png').is_file() and fold(video_title) != fold(title):
        lines.append(f'  Lưu ý: tiêu đề trên nền video ("{video_title.upper()}") khác tiêu đề trên ảnh bìa ("{title}"); '
                     'nếu muốn giống nhau: pipeline.py set video.side_title "…"')
    lines += [f'  ok    -> pipeline.py decide --run {run_dir} --art ok',
              f'  redo  -> pipeline.py decide --run {run_dir} --art redo      (ảnh mới với seed khác; tốn 1 ảnh trong hạn mức miễn phí mỗi ngày)',
              f'  image -> pipeline.py decide --run {run_dir} --art image --path FILE',
              *([f'  đổi phần giữa -> pipeline.py decide --run {run_dir} --center redo      (màu và dáng vòng phổ khác; ảnh giữ nguyên)']
                if cen else []),
              '  sửa chữ -> pipeline.py set cover.title "…" hoặc cover.title_inexact / cover.subtitle / video.side_title, rồi chạy lại']
    return '\n'.join(lines)


def fetch_art(run_dir, cfg: dict, manifest: dict, decisions: dict | None = None) -> tuple[list[dict], dict]:
    """Get the text-free AI picture before the long remix stage, so a quota or key problem
    shows up early. Also leaves a provisional cover (no times yet) for the look preview."""
    run_dir = Path(run_dir)
    art = run_dir / 'art'
    art.mkdir(parents=True, exist_ok=True)
    repo, python = _python(cfg)
    title, subtitle = texts(cfg, manifest)
    tracks = playlist_tracks(manifest)
    write_text(art / 'tracks_provisional.csv', _csv([['artist', 'title']] + [[t['artist'] or '', t['title']] for t in tracks]))
    base = [str(python), str(repo / 'main.py'), str(art / 'tracks_provisional.csv'), '--no-chapters',
            '--preset', cfg['cover']['preset'], '--title', title, '--subtitle', subtitle,
            '-o', str(art / 'provisional_cover.png')]
    info = {'seed': None, 'raw': None, 'mode': None, 'generated': 0}
    checks = []
    decisions = decisions or {}
    own = decisions.get('art_image') or cfg['cover'].get('image')        # a picture the human chose for this run, or for all

    if cfg['cover'].get('dry_run'):
        (art / 'raw.png').unlink(missing_ok=True)
        rc, out, err = run(base + ['--dry-run'], cwd=str(repo), timeout=600)
        if rc != 0:
            raise RcvError(f'm10-mixcover --dry-run lỗi (mã {rc}): {err.strip()[-300:]}')
        info['mode'] = 'dry_run'
        checks.append(check('art', 'WARN', 'cover.dry_run đang bật: nền gradient, không có ảnh DJ'))
    elif own:
        src = Path(own).expanduser()
        if not src.is_file():
            raise RcvError(f'Ảnh bạn chọn không tồn tại: {src}')
        shutil.copyfile(src, art / 'raw.png')
        rc, out, err = run(base + ['--image', str(art / 'raw.png')], cwd=str(repo), timeout=600)
        if rc != 0:
            raise RcvError(f'm10-mixcover --image lỗi (mã {rc}): {err.strip()[-300:]}')
        info.update(mode='image', raw=str(art / 'raw.png'))
        checks.append(check('art', 'PASS', f'dùng ảnh có sẵn {src}'))
    else:
        seed = seed_for(cfg, manifest) + 1000 * int(decisions.get('art_seed_offset', 0))     # "redo" asks for another picture
        last_err = ''
        for attempt in range(cfg['cover']['seed_retries'] + 1):
            rc, out, err = run(base + ['--seed', str(seed + attempt)], cwd=str(repo), timeout=900)
            m = CACHE_LINE.search(out)
            if rc == 0 and m and Path(m.group(2)).is_file():
                shutil.copyfile(m.group(2), art / 'raw.png')
                cached = m.group(1).startswith('lấy từ cache')
                info.update(mode='provider', raw=str(art / 'raw.png'), seed=int(m.group(3)), cached=cached,
                            generated=info['generated'] + (0 if cached else 1), cache_path=m.group(2))
                checks.append(check('art', 'PASS', f'seed {m.group(3)}, ' + ('lấy từ cache' if cached else 'vừa tạo')))
                break
            last_err = (err or out).strip()[-300:]
            if rc == 0:
                last_err = 'm10-mixcover không in đường dẫn ảnh gốc (dòng "vừa tạo"/"lấy từ cache")'
                break
            info['generated'] += 1                          # a failed call may still have used quota
        else:
            pass
        if not info['raw']:
            raise RcvError('Không lấy được ảnh từ nhà cung cấp: ' + last_err
                           + '\nCách khác: đặt cover.image thành một ảnh có sẵn, hoặc cover.dry_run=true.', 3)
        w, h = ffmpeg.image_size(art / 'raw.png')
        checks.append(check('art_size', 'PASS' if abs(w / h - 16 / 9) < 0.01 else 'WARN', f'{w}x{h}'))
    cchecks, cinfo = center.pick(run_dir, cfg, decisions)     # the video's centre: ring colours and shape, particles
    checks += cchecks
    info['center'] = cinfo
    own = center.run_files(run_dir, cfg)
    if wants_side(cfg):                                    # what the video will show behind the logo
        side = text_side(out)
        sinfo, schecks = draw_side(cfg, tracks, art / 'provisional_side.png', art / 'raw.png' if info.get('raw') else None,
                                   side, 'side_column')
        if sinfo is None:
            raise RcvError(schecks[0]['detail'])
        checks += schecks
        info.update(text_side=side, side_column=sinfo, side_geometry=side_geometry(cfg, own and own['preset']))
    (art / 'provisional_center.png').unlink(missing_ok=True)
    if own and tracks:                                     # one frame of the centre, on the video background
        src = tracks[0].get('source') or {}
        pchecks, frame = center.preview_frame(run_dir, cfg, src.get('path'), float(src.get('duration') or 0),
                                              info.get('text_side'), info.get('side_geometry'))
        checks += pchecks
        info['center_frame'] = frame
    (art / 'provisional_thumb.jpg').unlink(missing_ok=True)
    if wants_poster(cfg):                                  # the thumbnail needs no chapter times: show it now
        pinfo, pchecks = draw_poster(cfg, tracks, title, art / 'provisional_thumb.jpg', art / 'raw.png' if info.get('raw') else None,
                                     text_side(out), 'thumbnail_poster')
        checks += pchecks
        info.update(text_side=info.get('text_side') or text_side(out), poster=pinfo)
    info['signature'] = art_signature(run_dir, cfg, manifest)
    write_json(art / 'art.json', info)
    return checks, info


def make_cover(run_dir, cfg: dict, manifest: dict, mix: dict, limits: dict | None = None) -> tuple[list[dict], dict]:
    """Draw cover.png + cover_thumb.jpg from the measured mix. mixcover gets durations equal to
    the gaps between the skill's own whole-second marks, with --crossfade 0, so the times it
    draws and writes are exactly the skill's chapter times."""
    run_dir = Path(run_dir)
    out_dir = run_dir / 'cover'
    out_dir.mkdir(parents=True, exist_ok=True)
    repo, python = _python(cfg)
    title, subtitle = texts(cfg, manifest)
    tracks = playlist_tracks(manifest)
    marks = [c['seconds'] for c in mix['chapters']]
    total = mix['total_seconds']
    gaps = [marks[i + 1] - marks[i] for i in range(len(marks) - 1)] + [total - marks[-1]]
    if len(gaps) != len(tracks) or min(gaps) <= 0:
        raise RcvError(f'Mốc chapter không hợp lệ: {marks}, tổng {total}')
    rows = [['artist', 'title', 'duration']] + [[t['artist'] or '', t['title'], str(g)] for t, g in zip(tracks, gaps)]
    write_text(out_dir / 'tracks.csv', _csv(rows))
    art = read_json(run_dir / 'art' / 'art.json') or {}
    cmd = [str(python), str(repo / 'main.py'), str(out_dir / 'tracks.csv'), '--all', '--crossfade', '0',
           '--preset', cfg['cover']['preset'], '--title', title, '--subtitle', subtitle,
           '--thumb-tracks', str(cfg['cover']['thumb_tracks']), '-o', str(out_dir / 'cover.png')]
    cmd += ['--image', art['raw']] if art.get('raw') and Path(art['raw']).is_file() else ['--dry-run']
    for stale in ('cover.png', 'cover_thumb.jpg', 'chapters.txt'):
        (out_dir / stale).unlink(missing_ok=True)
    rc, out, err = run(cmd, cwd=str(repo), timeout=900)
    write_text(out_dir / 'mixcover.log', out + '\n--- stderr ---\n' + err)
    if rc != 0:
        raise RcvError(f'm10-mixcover lỗi (mã {rc}): {err.strip()[-400:]}')

    checks = []
    for name, want in (('cover.png', (1920, 1080)), ('cover_thumb.jpg', (1280, 720))):
        path = out_dir / name
        if not path.is_file():
            checks.append(check(name, 'FAIL', 'không được tạo'))
            continue
        size = ffmpeg.image_size(path)
        checks.append(check(name, 'PASS' if size == want else 'FAIL', f'{size[0]}x{size[1]}, {path.stat().st_size} byte'))
    thumb = out_dir / 'cover_thumb.jpg'
    if wants_poster(cfg):                                  # the thumbnail people see: a poster, not the cover scaled down
        poster = out_dir / 'thumb_poster.jpg'
        side = text_side(out) if SIDE_LINE.search(out) else art.get('text_side', 'right')
        pinfo, pchecks = draw_poster(cfg, tracks, title, poster, Path(art['raw']) if art.get('raw') else None, side, 'thumbnail_poster')
        checks += pchecks
        thumb = poster
    else:
        (out_dir / 'thumb_poster.jpg').unlink(missing_ok=True)
    limit = ((limits or {}).get('thumbnail_max_bytes') or {})
    if thumb.is_file():
        if limit.get('verified') and limit.get('value'):
            ok = thumb.stat().st_size <= limit['value']
            checks.append(check('thumbnail_bytes', 'PASS' if ok else 'FAIL', f'{thumb.stat().st_size} / {limit["value"]} byte'))
        else:
            checks.append(check('thumbnail_bytes', 'SKIP', 'giới hạn dung lượng thumbnail chưa được xác minh'))
        width = ((limits or {}).get('thumbnail_min_width') or {})
        if width.get('verified') and width.get('value'):
            got = ffmpeg.image_size(thumb)[0]
            checks.append(check('thumbnail_width', 'PASS' if got >= width['value'] else 'FAIL',
                                f'rộng {got} px (tối thiểu {int(width["value"])} px; YouTube khuyến nghị 3840x2160)'))
    chap = out_dir / 'chapters.txt'
    if chap.is_file():
        theirs = [parse_ts(line.split(' ', 1)[0]) for line in chap.read_text(encoding='utf-8').splitlines() if line.strip()]
        same = theirs == marks
        checks.append(check('chapters_match', 'PASS' if same else 'FAIL',
                            'mốc của skill trùng chapters.txt của mixcover' if same else f'skill {marks} != mixcover {theirs}'))
    else:
        checks.append(check('chapters_match', 'FAIL', 'mixcover không ghi chapters.txt'))
    notes = [line.strip()[2:].strip() for line in out.splitlines() if line.strip().startswith('! ')]
    if cut_lines(out):
        notes.append(f'{cut_lines(out)} dòng trên ảnh bìa bị cắt bằng "…"')
    if notes:
        checks.append(check('mixcover_warnings', 'WARN', '; '.join(notes[:4])))
    if not art.get('raw'):
        checks.append(check('cover_art', 'WARN', 'ảnh bìa dùng nền gradient (không có ảnh DJ)'))
    (run_dir / 'thumbnail.jpg').unlink(missing_ok=True)   # never an older run's style under the new name
    for path, dest in ((out_dir / 'cover.png', 'cover.png'), (thumb, 'thumbnail.jpg')):
        if path.is_file():
            shutil.copyfile(path, run_dir / dest)
    if wants_side(cfg):                                    # the video background: title and song list at the side
        vdir = run_dir / 'video'
        vdir.mkdir(exist_ok=True)
        bg = vdir / 'background.png'
        for stale in ('background_chapters.txt', 'mixcover_side.log'):    # left by versions that had mixcover draw it
            (vdir / stale).unlink(missing_ok=True)
        side = text_side(out) if SIDE_LINE.search(out) else art.get('text_side', 'right')
        sinfo, schecks = draw_side(cfg, tracks, bg, Path(art['raw']) if art.get('raw') else None, side, 'video_background')
        checks += schecks
        if sinfo is not None:
            own = center.run_files(run_dir, cfg)
            geo = side_geometry(cfg, own and own['preset'])
            if geo is None:
                checks.append(check('side_column_clear', 'SKIP', 'không đọc được preset của visualizer hoặc mixcover để tính khoảng cách'))
            else:
                checks.append(check('side_column_clear', 'PASS' if geo['clear_px'] >= 0 else 'WARN',
                                    f'cột chữ bắt đầu ở {geo["column_inner_px"]} px tính từ mép xa, vòng phổ vươn xa nhất tới '
                                    f'{geo["ring_edge_px"]} px: ' + (f'cách nhau {geo["clear_px"]} px' if geo['clear_px'] >= 0 else
                                                                    f'có thể chạm {-geo["clear_px"]} px khi nhạc to nhất; giảm video.side_column_width')))
            write_json(vdir / 'background.json', {'text_side': side, 'geometry': geo, 'text': sinfo})
    return checks, {'title': title, 'subtitle': subtitle, 'gaps': gaps}
