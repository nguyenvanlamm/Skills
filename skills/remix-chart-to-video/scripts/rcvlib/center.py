"""The centre of the "visualizer" look, different from one video to the next.

m10-visualizer draws the channel logo at the frame centre with a spectrum ring, a glow and
particles around it. The logo keeps the M10 mark; what changes per video is the ring's
colours, its shape and the particles, from three lists in `assets/center_styles.json`:
10 palettes x 7 ring shapes x 3 particle styles = 210 combinations. The three sizes are
pairwise coprime, so taking the least recently used item on each axis walks through all 210
before one comes back.

Which run used what is kept in `<workspace>/center_history.json`, the folder of the config file,
so a trial with its own config keeps its own history. The choice reaches m10-visualizer through
flags it already has (the repo is a tool, never edited): `--preset` with a file that extends
`video.preset` (JSON is YAML), `--logo` with the M10 mark whose lime parts take the palette's
main colour, and `--seed`.
"""
from __future__ import annotations

import colorsys
import hashlib
import itertools
import json
import subprocess
import time
from pathlib import Path

from . import config as cfgmod
from .common import SKILL_DIR, RcvError, check, read_json, run, write_json, write_text

STYLES_FILE = SKILL_DIR / 'assets' / 'center_styles.json'
AXES = ('palette', 'shape', 'particles')
AXIS_LABEL = {'palette': 'màu', 'shape': 'dáng vòng phổ', 'particles': 'kiểu hạt'}
CLASSIC = {'palette': 'chanh-hong', 'shape': 'co-dien', 'particles': 'bay-thang'}     # every video before this feature
FILES = ('center.json', 'center_preset.yaml', 'center_logo.png')
CONFIG_KEYS = ('center', 'center_palette', 'center_shape', 'center_particles', 'center_tint_logo',
               'center_palette_gap', 'center_family_gap', 'center_shape_gap', 'center_particles_gap')
NEVER = 10 ** 6

_CATALOG: dict | None = None


def catalog() -> dict:
    global _CATALOG
    if _CATALOG is None:
        data = read_json(STYLES_FILE)
        if not data or any(not data.get(a) for a in AXES):
            raise RcvError(f'Không đọc được danh mục kiểu phần giữa {STYLES_FILE}')
        _CATALOG = data
    return _CATALOG


def names(axis: str) -> list[str]:
    return [it['name'] for it in catalog()[axis]]


def item(axis: str, name: str) -> dict:
    for it in catalog()[axis]:
        if it['name'] == name:
            return it
    raise RcvError(f'Danh mục kiểu phần giữa không có {AXIS_LABEL[axis]} "{name}"')


def key(combo: dict) -> str:
    return '/'.join(str(combo.get(a)) for a in AXES)


def labels(combo: dict) -> str:
    return ' · '.join(item(a, combo[a])['label'] for a in AXES)


def all_keys() -> set[str]:
    return {key(dict(zip(AXES, t))) for t in itertools.product(*(names(a) for a in AXES))}


def enabled(cfg: dict) -> bool:
    return cfg['video'].get('center', 'rotate') == 'rotate'


def family(palette: str) -> str:
    """Palettes of one colour family (lime and neon green, cyan and ice blue) look alike."""
    return item('palette', palette).get('family') or palette


def primary(combo: dict) -> str:
    return item('palette', combo['palette'])['overrides']['colors']['primary']


def deep_merge(base: dict, over: dict) -> dict:
    out = json.loads(json.dumps(base))
    for k, v in over.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else json.loads(json.dumps(v))
    return out


# -- history -----------------------------------------------------------------------------

def ledger_path(cfg: dict) -> Path:
    return Path(cfg['_workspace']) / 'center_history.json'


def _bootstrap(workspace: Path) -> list[dict]:
    """The first time: runs that already have a video were made before the centre changed, so
    they all used the classic centre. Recording them keeps the next video from repeating it."""
    out = []
    for run_dir in sorted(workspace.iterdir()) if workspace.is_dir() else []:
        vid = run_dir / 'video.mp4'
        if vid.is_file() and not (run_dir / 'art' / 'center.json').is_file():
            out.append({'run': run_dir.name, **CLASSIC, 'status': 'bootstrap', 'at': vid.stat().st_mtime})
    return sorted(out, key=lambda e: e['at'])


def load_history(cfg: dict) -> dict:
    data = read_json(ledger_path(cfg))
    if data is None:
        data = {'version': 1, 'entries': _bootstrap(Path(cfg['_workspace']))}
    data.setdefault('entries', [])
    return data


def _save(cfg: dict, data: dict) -> None:
    data['entries'].sort(key=lambda e: e.get('at', 0))
    write_json(ledger_path(cfg), data)


def reserve(cfg: dict, run_name: str, combo: dict, same_as: str | None = None) -> None:
    """Record this run's choice. A run that chooses again (a redo, new text) keeps its place in
    the order: the history is about which video came after which."""
    data = load_history(cfg)
    old = next((e for e in data['entries'] if e.get('run') == run_name), None)
    entry = {'run': run_name, **{a: combo[a] for a in AXES}, 'status': 'chosen',
             'at': old['at'] if old else time.time()}
    if same_as:
        entry['same_as'] = same_as
    data['entries'] = [e for e in data['entries'] if e.get('run') != run_name] + [entry]
    _save(cfg, data)


def release(cfg: dict, run_name: str) -> None:
    """This run shows no rotating centre after all (`video.center: fixed`, the cover look)."""
    path = ledger_path(cfg)
    data = read_json(path)
    if data and any(e.get('run') == run_name for e in data.get('entries', [])):
        data['entries'] = [e for e in data['entries'] if e.get('run') != run_name]
        _save(cfg, data)


def mark_rendered(cfg: dict, run_name: str) -> None:
    data = load_history(cfg)
    for e in data['entries']:
        if e.get('run') == run_name:
            e['status'], e['rendered_at'] = 'rendered', time.time()
            _save(cfg, data)
            return


# -- choosing --------------------------------------------------------------------------------

def _hsv(rgb) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(*(c / 255.0 for c in rgb))


def _hex_rgb(value: str) -> tuple[int, int, int]:
    s = value.strip().lstrip('#')
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def clashes(primary_hex: str, picture_rgb, rules: dict) -> bool:
    """Would a ring in this colour melt into the picture behind it? Only when the picture
    around the ring has a clear colour of its own and the ring's colour is close to it."""
    if not picture_rgb:
        return False
    ph, ps, _ = _hsv(_hex_rgb(primary_hex))
    h, s, v = _hsv(picture_rgb)
    if ps < rules['primary_min_saturation'] or s < rules['picture_min_saturation'] or v < rules['picture_min_value']:
        return False
    d = abs(ph - h) * 360
    return min(d, 360 - d) < rules['hue_clash_deg']


def picture_color(path) -> tuple[int, int, int] | None:
    """Mean colour of the picture in the square around the ring (0.8 of the height)."""
    if not path or not Path(path).is_file():
        return None
    try:
        done = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(path), '-vf',
                               'crop=ih*0.8:ih*0.8:(iw-ih*0.8)/2:ih*0.1,scale=1:1:flags=area', '-frames:v', '1',
                               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return tuple(done.stdout[:3]) if done.returncode == 0 and len(done.stdout) >= 3 else None


def choose(cfg: dict, run_name: str, history: dict, rejected=(), picture_rgb=None, carry: dict | None = None) -> dict:
    """This run's centre: a combination not used in the current cycle, unlike the last few
    videos on every axis, the least recently used palette first. Same history, same answer."""
    vid, rules = cfg['video'], catalog()['rules']
    past = [e for e in sorted(history.get('entries', []), key=lambda e: e.get('at', 0)) if e.get('run') != run_name]
    pins = {a: vid.get(f'center_{a}') for a in AXES}
    for a, name in pins.items():
        if name is not None:
            item(a, name)                                   # a pinned name that is not in the catalogue fails here
    gone = {key(r) for r in rejected}
    every = all_keys()

    def result(combo: dict, reason: str, notes: list[str], used: set[str]) -> dict:
        return {**combo, 'key': key(combo), 'labels': labels(combo), 'reason': reason, 'notes': notes,
                'unused': len(every - used - {key(combo)}), 'total': len(every)}

    used: set[str] = set()                                  # the current cycle: reset once all were used
    for e in past:
        k = key(e)
        if k in every:
            used.add(k)
            if len(used) == len(every):
                used = set()
    if carry and key(carry) in every and key(carry) not in gone and all(pins[a] in (None, carry[a]) for a in AXES):
        return result({a: carry[a] for a in AXES}, 'giữ kiểu của lượt gốc', [], used)

    cands = [dict(zip(AXES, t)) for t in itertools.product(*(names(a) for a in AXES))]
    cands = [c for c in cands if all(pins[a] in (None, c[a]) for a in AXES) and key(c) not in gone]
    if not cands:
        raise RcvError('Không còn kiểu phần giữa nào để chọn: cả ba trục đang ghim (video.center_palette, center_shape, '
                       'center_particles) và kiểu đó đã bị đổi. Bỏ ghim một trục: `pipeline.py set video.center_shape null`.', 2)
    notes = []
    pool = [c for c in cands if key(c) not in used]
    if not pool:
        pool = cands
        notes.append('mọi tổ hợp hợp lệ (theo các trục đang ghim) đều đã dùng trong chu kỳ này: dùng lại tổ hợp lâu chưa dùng nhất')
    gaps = {a: int(vid.get(f'center_{a}_gap', 0) or 0) for a in AXES}
    recent = {a: {e.get(a) for e in past[-gaps[a]:]} if gaps[a] > 0 else set() for a in AXES}
    fgap = int(vid.get('center_family_gap', 0) or 0)
    families = {family(e['palette']) for e in past[-fgap:] if e.get('palette') in names('palette')} if fgap > 0 else set()

    def far(c: dict, relax: tuple) -> bool:
        if 'family' not in relax and not pins['palette'] and family(c['palette']) in families:
            return False
        return all(a in relax or pins[a] or c[a] not in recent[a] for a in AXES)

    for relax in ((), ('particles',), ('particles', 'family'), ('particles', 'family', 'shape'), ('family', *AXES)):
        ok = [c for c in pool if far(c, relax)]
        if ok:
            break
    if relax:
        notes.append('không còn tổ hợp nào khác đủ xa các video gần đây: đã nới luật cho '
                     + ', '.join({'family': 'họ màu', **AXIS_LABEL}[a] for a in relax))

    def age(axis: str, name: str) -> int:
        for i, e in enumerate(reversed(past)):
            if e.get(axis) == name:
                return i
        return NEVER

    refused = {a: {r[a] for r in rejected} for a in AXES}   # after "đổi kiểu khác", change the colour and the shape too
    clash = {p: clashes(primary({'palette': p}), picture_rgb, rules) for p in names('palette')}
    # Ties go by the catalogue's order, not at random: then each axis cycles in that order, and
    # three coprime cycles meet every combination once (the palettes are ordered so that two of
    # one colour family stay five apart).
    order = {a: {n: i for i, n in enumerate(names(a))} for a in AXES}
    rank = lambda c: (c['palette'] in refused['palette'], c['shape'] in refused['shape'], clash[c['palette']],  # noqa: E731
                      -age('palette', c['palette']), -age('shape', c['shape']), -age('particles', c['particles']),
                      order['palette'][c['palette']], order['shape'][c['shape']], order['particles'][c['particles']])
    combo = min(ok, key=rank)
    if clash[combo['palette']]:
        notes.append('màu vòng phổ gần tông ảnh nền (không còn màu nào khác hợp luật)')
    a = age('palette', combo['palette'])
    reason = 'chưa dùng trong chu kỳ này; màu ' + ('chưa dùng lần nào' if a == NEVER else f'dùng lần cuối cách đây {a + 1} video')
    if any(clash.values()) and not clash[combo['palette']]:
        reason += '; bỏ qua màu trùng tông ảnh nền'
    return result(combo, reason, notes, used)


# -- files for m10-visualizer -----------------------------------------------------------------

def seed_for(run_name: str) -> int:
    return int(hashlib.sha256(run_name.encode()).hexdigest()[:8], 16) % 1_000_000


def tint_logo(src: Path, out: Path, colour: str) -> Path:
    """The M10 mark with its lime parts in `colour`. A pixel's share of "lime" is how green and
    how little blue it has: white letters and the transparent rest keep their colour."""
    r, g, b = _hex_rgb(colour)
    w = '(255-b(X,Y))*g(X,Y)/65025'
    expr = lambda c, ch: f"'{ch}(X,Y)+({c}-{ch}(X,Y))*{w}'"  # noqa: E731
    graph = f"format=rgba,geq=r={expr(r, 'r')}:g={expr(g, 'g')}:b={expr(b, 'b')}:a='alpha(X,Y)',format=rgba"
    out.parent.mkdir(parents=True, exist_ok=True)
    rc, _, err = run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-vf', graph, '-frames:v', '1', out],
                     timeout=300)
    if rc != 0 or not out.is_file():
        raise RcvError(f'Không tô được màu logo: {err.strip()[-200:]}')
    return out


def preset_data(cfg: dict, combo: dict) -> dict:
    data = {'extends': cfg['video']['preset'], 'name': f'M10 · {labels(combo)}'}
    for a in AXES:
        data = deep_merge(data, item(a, combo[a])['overrides'])
    return data


def write_files(run_dir, cfg: dict, choice: dict) -> dict:
    """center.json, center_preset.yaml and center_logo.png in RUN/art/."""
    art = Path(run_dir) / 'art'
    art.mkdir(parents=True, exist_ok=True)
    preset = art / 'center_preset.yaml'
    write_text(preset, '# remix-chart-to-video: phần giữa của video này (JSON cũng là YAML)\n'
               + json.dumps(preset_data(cfg, choice), ensure_ascii=False, indent=2) + '\n')
    logo = art / 'center_logo.png'
    logo.unlink(missing_ok=True)
    if cfg['video'].get('center_tint_logo', True):
        src = cfgmod.repo(cfg, 'visualizer') / 'assets' / 'M10-logo-mark.png'
        if src.is_file():
            tint_logo(src, logo, primary(choice))
    info = {**{k: choice[k] for k in (*AXES, 'key', 'labels', 'reason', 'notes', 'unused', 'total')},
            'primary': primary(choice), 'seed': seed_for(Path(run_dir).name), 'preset': str(preset),
            'logo': str(logo) if logo.is_file() else None}
    write_json(art / 'center.json', info)
    return info


def clear_files(run_dir) -> None:
    for name in FILES:
        (Path(run_dir) / 'art' / name).unlink(missing_ok=True)
    (Path(run_dir) / 'art' / 'provisional_center.png').unlink(missing_ok=True)


def run_files(run_dir, cfg: dict) -> dict | None:
    """What look_args passes for this run's centre, or None: the visualizer's own preset, logo
    and seed (`video.center: fixed`, or a run made before the centre changed)."""
    if not enabled(cfg):
        return None
    art = Path(run_dir) / 'art'
    info = read_json(art / 'center.json')
    if not info or not (art / 'center_preset.yaml').is_file():
        return None
    logo = art / 'center_logo.png'
    return {'preset': str(art / 'center_preset.yaml'), 'logo': str(logo) if logo.is_file() else None,
            'seed': int(info['seed']), 'labels': info.get('labels'), 'key': info.get('key')}


def pick(run_dir, cfg: dict, decisions: dict) -> tuple[list[dict], dict | None]:
    """Choose this run's centre at the picture stage, write its files and record it."""
    run_dir = Path(run_dir)
    if not enabled(cfg):
        clear_files(run_dir)
        release(cfg, run_dir.name)
        return [check('center', 'SKIP', 'video.center là fixed: phần giữa dùng preset và logo gốc của visualizer')], None
    history = load_history(cfg)
    choice = choose(cfg, run_dir.name, history, decisions.get('center_rejected') or (),
                    picture_color(run_dir / 'art' / 'raw.png'), decisions.get('center_carry'))
    info = write_files(run_dir, cfg, choice)
    carried = decisions.get('carried_from')
    reserve(cfg, run_dir.name, choice, Path(carried).name if carried and decisions.get('center_carry') else None)
    detail = f'{info["labels"]} ({info["reason"]}; còn {info["unused"]}/{info["total"]} tổ hợp chưa dùng)'
    checks = [check('center', 'WARN' if info['notes'] else 'PASS', detail + ('; ' + '; '.join(info['notes']) if info['notes'] else ''))]
    return checks, info


def preview_frame(run_dir, cfg: dict, audio, audio_seconds: float, text_side: str | None, geometry: dict | None,
                  seconds: float = 1.5) -> tuple[list[dict], str | None]:
    """One frame of the centre on the provisional video background, for the picture stop, and
    whether the ring stays clear of the side column there. Only for the visualizer look."""
    from . import video
    run_dir = Path(run_dir)
    if cfg['video'].get('look') != 'visualizer' or not audio or not Path(audio).is_file():
        return [], None
    extra, _ = video.look_args(cfg, run_dir, 'visualizer', provisional=True)
    clip = run_dir / 'art' / 'center_preview.mp4'
    start = max(0.0, min(audio_seconds * 0.45, audio_seconds - seconds - 0.5))
    res = video.run_visualizer(cfg, Path(audio), clip, extra, run_dir / 'logs' / 'center_preview.log', start=start, duration=seconds)
    if res['code'] != 0 or not clip.is_file():
        return [check('center_preview', 'WARN', f'không dựng được khung hình phần giữa (mã {res["code"]}): '
                                                f'{res["stderr"].strip()[-200:]}')], None
    bg = Path(extra[extra.index('--bg') + 1]) if '--bg' in extra else None
    try:
        checks, info = video.check_video(cfg, clip, seconds, 'visualizer', bg if bg and bg.name != 'raw.png' else None,
                                         run_dir / 'art' / 'frames', at=seconds * 0.6, text_side=text_side,
                                         column_inner=(geometry or {}).get('column_inner_frac'))
    finally:
        clip.unlink(missing_ok=True)
    frame = run_dir / 'art' / 'provisional_center.png'
    Path(info['frame']).replace(frame)
    side = next((c for c in checks if c['name'] == 'tracklist_readable'), None)
    if side is None:
        return [check('center_preview', 'PASS', f'khung hình phần giữa: {frame}')], str(frame)
    if side['status'] == 'PASS':
        return [check('center_preview', 'PASS', f'vòng phổ không chạm cột chữ ({side["detail"]})')], str(frame)
    return [check('center_preview', 'WARN', f'{side["detail"]}: xem {frame}; đổi kiểu bằng `decide --center redo`')], str(frame)
