"""The picture of each video: an anime chill landscape no earlier video has used.

A scene is one place, one time, one weather and one detail from `assets/lofi_scenes.json`
(20 x 5 x 6 x 8 = 4800 combinations). The choice keeps three promises:
  - a combination is never used twice, by any run of this workspace;
  - the place differs from those of the last `cover.scene_place_gap` videos;
  - the seed comes from the run's name, so two runs never ask for the same picture.
The picture itself is then measured: `unique_check` compares it with the picture of every
earlier video (SSIM on a small copy, and the file hash), and a picture at or above
`cover.max_art_similarity` fails, so the human is asked for another one.

The scene reaches m10-mixcover through flags it already has: `--preset` with a small file of the
run (`art/mixcover_preset.yaml`, JSON is YAML) that extends `cover.preset` (`lofi`, a scenery
preset with a `{scene}` placeholder) and sets `image.scene` and `layout.default_side`.

History: `<workspace>/art_history.json` (which run chose what, and whether the human approved
it) and `<workspace>/art_history/<run>.jpg` (a small copy of every approved picture). An entry
stays when its run folder is deleted: the video may be online.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import shutil
import time
from pathlib import Path

from . import ffmpeg
from .common import SKILL_DIR, RcvError, check, read_json, run, sha256_file, write_json, write_text

SCENES_FILE = SKILL_DIR / 'assets' / 'lofi_scenes.json'
AXES = ('place', 'time', 'weather', 'detail')
AXIS_LABEL = {'place': 'nơi chốn', 'time': 'thời điểm', 'weather': 'thời tiết', 'detail': 'chi tiết'}
SIDES = ('left', 'right')
THUMB = '640:360'
SIM_SIZE = '320:180'

_CATALOG: dict | None = None


def catalog() -> dict:
    global _CATALOG
    if _CATALOG is None:
        data = read_json(SCENES_FILE)
        if not data or any(not data.get(a) for a in AXES):
            raise RcvError(f'Không đọc được danh mục cảnh {SCENES_FILE}')
        _CATALOG = data
    return _CATALOG


def item(axis: str, name: str) -> dict:
    for it in catalog()[axis]:
        if it['name'] == name:
            return it
    raise RcvError(f'Danh mục cảnh không có {AXIS_LABEL[axis]} "{name}"')


def key(combo: dict) -> str:
    return '/'.join(str(combo.get(a)) for a in AXES)


def labels(combo: dict) -> str:
    return ' · '.join(item(a, combo[a])['label'] for a in AXES)


def scene_text(combo: dict) -> str:
    """The sentence m10-mixcover puts in place of `{scene}`."""
    place, when, weather, detail = (item(a, combo[a])['text'] for a in AXES)
    return f'{place}, {when}, {weather}, {detail}'


def total() -> int:
    return 1 if not catalog() else len(list(itertools.product(*(catalog()[a] for a in AXES))))


# -- history ---------------------------------------------------------------------------------------

def ledger_path(cfg: dict) -> Path:
    return Path(cfg['_workspace']) / 'art_history.json'


def thumbs_dir(cfg: dict) -> Path:
    return Path(cfg['_workspace']) / 'art_history'


def load_history(cfg: dict) -> dict:
    data = read_json(ledger_path(cfg)) or {}
    data.setdefault('version', 1)
    data.setdefault('entries', [])
    return data


def _save(cfg: dict, data: dict) -> None:
    data['entries'].sort(key=lambda e: e.get('at', 0))
    write_json(ledger_path(cfg), data)


def _entry(data: dict, run_name: str) -> dict | None:
    return next((e for e in data['entries'] if e.get('run') == run_name), None)


def reserve(cfg: dict, run_name: str, choice: dict) -> None:
    """Record this run's scene. A run that chooses again (redo) keeps its place in the order."""
    data = load_history(cfg)
    old = _entry(data, run_name)
    entry = {'run': run_name, **{a: choice[a] for a in AXES}, 'key': choice['key'], 'side': choice['side'],
             'seed': choice['seed'], 'status': 'chosen', 'at': old['at'] if old else time.time()}
    if choice.get('same_as'):
        entry['same_as'] = choice['same_as']
    data['entries'] = [e for e in data['entries'] if e.get('run') != run_name] + [entry]
    _save(cfg, data)


def approve(cfg: dict, run_dir) -> dict | None:
    """The human said ok: this picture is now the run's, a small copy joins the comparison set."""
    run_dir = Path(run_dir)
    raw = run_dir / 'art' / 'raw.png'
    data = load_history(cfg)
    entry = _entry(data, run_dir.name)
    if entry is None:                                   # an own picture (`--art image`) or a dry run: no scene, still compared
        entry = {'run': run_dir.name, 'status': 'chosen', 'at': time.time()}
        data['entries'].append(entry)
    if raw.is_file():
        thumbs_dir(cfg).mkdir(parents=True, exist_ok=True)
        thumb = thumbs_dir(cfg) / f'{run_dir.name}.jpg'
        rc, _, err = run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', raw, '-vf', f'scale={THUMB}',
                          '-q:v', '3', thumb], timeout=120)
        if rc != 0:
            raise RcvError(f'Không lưu được bản nhỏ của ảnh vào lịch sử: {err.strip()[-200:]}')
        entry.update(thumb=thumb.name, sha256=sha256_file(raw))
    entry.update(status='approved', approved_at=time.time())
    _save(cfg, data)
    return entry


def mark_rendered(cfg: dict, run_name: str) -> None:
    data = load_history(cfg)
    entry = _entry(data, run_name)
    if entry is not None:
        entry.update(status='rendered', rendered_at=time.time())
        _save(cfg, data)


# -- choosing ---------------------------------------------------------------------------------------

def seed_for(run_name: str, offset: int = 0) -> int:
    return (int(hashlib.sha256(run_name.encode()).hexdigest()[:8], 16) + 1000 * offset) % 2_000_000_000


def choose(cfg: dict, run_name: str, history: dict, rejected=(), offset: int = 0, carry: dict | None = None) -> dict:
    """This run's scene: a combination no other run has used, at a place none of the last
    `cover.scene_place_gap` videos used, at random from the rest with a seed from the run's
    name. Same history, same answer."""
    past = [e for e in sorted(history.get('entries', []), key=lambda e: e.get('at', 0)) if e.get('run') != run_name]
    used = {e['key'] for e in past if e.get('key')}
    gone = set(rejected)
    seed = seed_for(run_name, offset)
    if carry and carry.get('key') and carry['key'] not in gone:
        return {**{a: carry[a] for a in AXES}, 'key': carry['key'], 'side': carry.get('side', 'left'),
                'seed': int(carry['seed']), 'same_as': carry.get('run'), 'reason': f'giữ cảnh của lượt gốc {carry.get("run")}',
                'notes': [], 'unused': None}
    names = {a: [it['name'] for it in catalog()[a]] for a in AXES}
    every = [dict(zip(AXES, t)) for t in itertools.product(*(names[a] for a in AXES))]
    free = [c for c in every if key(c) not in used and key(c) not in gone]
    if not free:
        raise RcvError(f'Đã dùng hết {len(every)} tổ hợp cảnh trong {SCENES_FILE.name}: thêm nơi chốn, thời điểm, '
                       'thời tiết hoặc chi tiết vào file đó.', 2)
    gap = int(cfg['cover'].get('scene_place_gap', 0) or 0)
    recent = [e.get('place') for e in past[-gap:]] if gap > 0 else []
    notes = []
    pool = [c for c in free if c['place'] not in recent]
    while not pool and recent:                        # fewer places than the gap asks for: relax from the oldest
        recent = recent[1:]
        pool = [c for c in free if c['place'] not in recent]
        notes.append('không còn nơi chốn nào khác các video gần đây: nới luật nơi chốn')
    rng = random.Random(seed)
    combo = rng.choice(pool)
    side = rng.choice(SIDES)
    return {**combo, 'key': key(combo), 'side': side, 'seed': seed,
            'reason': f'chưa video nào dùng tổ hợp này; nơi chốn khác {len(recent)} video gần nhất',
            'notes': notes[:1], 'unused': len(free) - 1}


def preset_data(cfg: dict, choice: dict) -> dict:
    return {'extends': cfg['cover']['preset'], 'name': f'Lofi · {labels(choice)}',
            'image': {'scene': scene_text(choice)}, 'layout': {'default_side': choice['side']}}


def write_files(run_dir, cfg: dict, choice: dict) -> dict:
    art = Path(run_dir) / 'art'
    art.mkdir(parents=True, exist_ok=True)
    preset = art / 'mixcover_preset.yaml'
    write_text(preset, '# lofi-ballad-to-video: cảnh của video này (JSON cũng là YAML)\n'
               + json.dumps(preset_data(cfg, choice), ensure_ascii=False, indent=2) + '\n')
    info = {**{k: choice.get(k) for k in (*AXES, 'key', 'side', 'seed', 'reason', 'notes', 'unused', 'same_as')},
            'labels': labels(choice), 'scene': scene_text(choice), 'total': total(), 'preset': str(preset)}
    write_json(art / 'scene.json', info)
    return info


def preset_for(run_dir, cfg: dict) -> str:
    """The m10-mixcover preset this run draws with: its own file once the scene is chosen."""
    own = Path(run_dir) / 'art' / 'mixcover_preset.yaml'
    return str(own) if own.is_file() else str(cfg['cover']['preset'])


def with_run_preset(run_dir, cfg: dict) -> dict:
    """A copy of the config whose `cover.preset` is the run's own preset, for every helper that
    passes it to m10-mixcover (picture, cover, thumbnail, side column)."""
    return {**cfg, 'cover': {**cfg['cover'], 'preset': preset_for(run_dir, cfg)}}


def pick(run_dir, cfg: dict, decisions: dict) -> tuple[list[dict], dict]:
    """Choose this run's scene at the picture stage, write its preset and record it."""
    run_dir = Path(run_dir)
    choice = choose(cfg, run_dir.name, load_history(cfg), decisions.get('scene_rejected') or (),
                    int(decisions.get('art_seed_offset', 0)), decisions.get('scene_carry'))
    if cfg['cover'].get('seed') is not None:
        choice['seed'] = int(cfg['cover']['seed']) + 1000 * int(decisions.get('art_seed_offset', 0))
    info = write_files(run_dir, cfg, choice)
    reserve(cfg, run_dir.name, choice)
    left = '' if info['unused'] is None else f'; còn {info["unused"]}/{info["total"]} tổ hợp chưa dùng'
    detail = f'{info["labels"]} (bên {"trái" if info["side"] == "left" else "phải"}, seed {info["seed"]}; {info["reason"]}{left})'
    return [check('scene', 'WARN' if info['notes'] else 'PASS', detail + ('; ' + '; '.join(info['notes']) if info['notes'] else ''))], info


def clear_files(run_dir) -> None:
    for name in ('scene.json', 'mixcover_preset.yaml'):
        (Path(run_dir) / 'art' / name).unlink(missing_ok=True)


# -- is the picture new? -----------------------------------------------------------------------------

def unique_check(run_dir, cfg: dict, decisions: dict | None = None) -> dict:
    """The new picture against the picture of every other video of this workspace (approved or
    rendered), except the run this one was made from (`--from-run` keeps its picture)."""
    run_dir = Path(run_dir)
    raw = run_dir / 'art' / 'raw.png'
    if not raw.is_file():
        return check('art_unique', 'SKIP', 'không có ảnh để so (dry run)')
    carried = Path((decisions or {}).get('carried_from') or '').name or None
    data = load_history(cfg)
    family = {run_dir.name, carried} | {e['run'] for e in data['entries'] if carried and e.get('same_as') == carried}
    others = [e for e in data['entries'] if e.get('run') not in family and e.get('status') in ('approved', 'rendered')]
    if not others:
        return check('art_unique', 'PASS', 'chưa có video nào trước để so')
    limit = float(cfg['cover']['max_art_similarity'])
    mine = sha256_file(raw)
    worst = (0.0, None)
    for e in others:
        if e.get('sha256') == mine:
            return check('art_unique', 'FAIL', f'ảnh giống hệt ảnh của video {e["run"]}: chọn redo để có ảnh khác')
        thumb = thumbs_dir(cfg) / (e.get('thumb') or '')
        if not e.get('thumb') or not thumb.is_file():
            continue
        try:
            sim = ffmpeg.ssim(raw, thumb, size=SIM_SIZE)
        except RcvError:
            continue
        if sim > worst[0]:
            worst = (sim, e['run'])
    if worst[1] is None:
        return check('art_unique', 'PASS', 'không có bản nhỏ nào của video trước để so')
    detail = f'giống nhất là video {worst[1]}: SSIM {worst[0]:.2f} (ngưỡng {limit:.2f}), so với {len(others)} video'
    if worst[0] >= limit:
        return check('art_unique', 'FAIL', detail + ': quá giống, chọn redo để có ảnh khác')
    return check('art_unique', 'PASS', detail)


def carry_from(cfg: dict, old_run: Path) -> dict | None:
    """What a `--from-run` copy keeps: the old run's scene and seed, so mixcover's cache gives
    back the same picture without asking the provider."""
    info = read_json(Path(old_run) / 'art' / 'scene.json')
    if not info or not info.get('key'):
        return None
    return {**{a: info[a] for a in AXES}, 'key': info['key'], 'side': info.get('side'), 'seed': info.get('seed'),
            'run': Path(old_run).name}


def copy_thumb(cfg: dict, src_run: str, dst_run: str) -> None:
    src = thumbs_dir(cfg) / f'{src_run}.jpg'
    if src.is_file():
        shutil.copyfile(src, thumbs_dir(cfg) / f'{dst_run}.jpg')
