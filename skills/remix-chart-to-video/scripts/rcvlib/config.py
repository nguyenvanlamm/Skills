"""Run configuration. JSON, because the standard library reads and writes it (no YAML there).

The shared config lives at <workspace>/config.json, where <workspace> is the `mixes/` folder
next to the four repos. A trial uses its own file so it never answers the first-run questions
of the real config.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path

from .common import RcvError, read_json, write_json

REPOS = {'downloader': 'tiktok-nct-downloader', 'stemforge': 'StemForge',
         'mixcover': 'm10-mixcover', 'visualizer': 'm10-visualizer'}

# The channel's style. Not a config key: the cover, the YouTube text and its checks all say
# vinahouse, so a remix in another StemForge preset would make them untrue.
GENRE = 'vinahouse'

# `None` on a first-run key means "not asked yet": the agent asks once and saves the answer.
DEFAULTS = {
    'version': 1,
    'repos': {k: None for k in REPOS},
    'nct': {
        'live_access': None,        # first-run question. True only after the human said yes.
        'chart': 'V-REMIX_TOP_50',
        'interval_s': 60,           # seconds between two downloads; never below 60
        'home': None,               # the downloader's data folder; None = its own default
    },
    'selection': {
        'count': 12,
        'min_duration_s': 90,       # shorter originals are snippets, not songs
        'max_duration_s': 600,      # StemForge refuses longer input
        'max_size_mb': 200,
        'on_missing': 'ask',        # ask | backfill | skip
        'max_rank': 50,
    },
    'remix': {
        'target_bpm': 128,          # one tempo for every song, so outros and intros line up
        'target_key': 'auto',
        'quality': 'high',
        'host': '127.0.0.1',
        'port': 8765,
        'acestep_port': 8001,
        'separator': None,          # e.g. "htdemucs_ft" for an MIT-only separation stack
        'max_attempts': 2,          # first try + retries from checkpoints
        'warn_tempo_stretch': 1.25, # a song stretched further than this to reach the tempo gets a WARN
        'job_timeout_s': 2400,
        'stall_s': 600,             # a job whose stage and progress stand still this long is stuck
        'start_timeout_s': 180,
        'poll_s': 3,
        'cleanup_jobs': None,       # first-run question: "keep" | "delete_after_copy"
    },
    'mix': {
        'transition': 'overlap',    # overlap | crossfade | cut
        'overlap_bars': 4,          # bars over which one song hands over to the next
        'lead_in_bars': 4,          # bars kept before a song's first sung bar (also at the start of the mix); None = keep all
        'tail_bars': 4,             # bars kept after a song's last sung bar; None = keep all
        'vocal_activity_min': 0.5,  # a bar counts as sung when StemForge's vocal activity for it reaches this
        'dj_bars': 8,               # StemForge's DJ intro/outro length, used when a remix has no vocal data
        'start_fade_s': 1.0,        # fade-in when the mix starts inside a song
        'curve': 'tri',             # linear gains sum to 1: an overlap can never clip
        'crossfade_s': 4.0,         # used by "crossfade" and as the fallback of "overlap"
        'max_beat_offset_ms': 60,   # every overlap is nudged onto the beat; a first offset beyond this is flagged
        'min_beat_correlation': 0.25,
        'target_lufs': -14.0,
        'lufs_tolerance': 1.5,
        'true_peak_max_dbtp': -1.0,
        'silence_db': -50,
        'silence_min_s': 1.5,
        'preview_pad_s': 10,
    },
    'cover': {
        'title': 'TOP {count} REMIX VIỆT',
        'title_inexact': '{count} BÀI REMIX VIỆT HOT',   # used when the songs are not exactly ranks 1..N
        'subtitle': 'Vinahouse Remix · Tháng {month}/{year}',
        'confirmed': False,         # first-run question: the human saw and accepted the two lines
        'review': True,             # every run stops after the picture stage until the human approves the picture
        'preset': 'm10',
        'thumb_tracks': 10,
        'seed': None,               # None = derived from the chart date
        'seed_retries': 1,
        'label': '{artist} - {title}',
    },
    'video': {
        'look': None,               # first-run question: "cover" | "visualizer"
        'preset': 'm10',
        'fps': 60,
        'size': '1920x1080',
        'workers': 0,
        'background_still': True,   # the background neither shakes nor zooms; the centre logo still pulses on the beat
        'tracklist': 'side',        # "visualizer" look: "side" draws a column at the far side, a title above the numbered song list; "none" = bare picture
        'side_title': 'remix nhạc hot tiktok',  # the title of that column, big and glowing; "" = the list alone
        'side_column_width': 0.24,  # width of that column (fraction of the frame); at 0.24 the ring's farthest bar tip stays clear of it
        'side_title_min_size': 0.037,  # smallest size of the title (fraction of the height, 40 px at 1080p); it grows into the room the list leaves
        'side_track_max': 0.026,    # largest size of a song line (fraction of the height, 28 px at 1080p)
        'side_track_min': 0.016,    # smallest size of a song line (17 px at 1080p); below it, or the title below its minimum, the check fails
        'max_side_diff': 20,        # mean luma difference (0..255) at the side column's inner edge: measured 8-9 clean, 36-72 with the ring over it (1080p)
        'cover_zoom_amount': 0.008, # "cover" look only, when background_still is false
        'min_cover_ssim': 0.80,     # "cover" look, at 640x360: measured 0.89 clean; 0.42 to 0.70 with logo + ring on top
        'duration_tolerance_s': 0.1,
    },
    'panel': {'stall_warn_s': 300},
    'youtube': {'language': 'vi', 'channel': 'M10 Music', 'max_review_rounds': 2},
}

FIRST_RUN = [
    ('nct.live_access', 'Bật truy cập trực tiếp NCT cho skill? (điều khoản 5.15 của NCT cấm script tự động)'),
    ('remix.cleanup_jobs', 'Sau khi chép kết quả, xoá thư mục job StemForge của lượt chạy (keep | delete_after_copy)?'),
    ('cover.confirmed', 'Xác nhận hai dòng chữ trên ảnh bìa (cover.title, cover.subtitle)'),
    ('video.look', 'Chọn kiểu hình: cover (ảnh bìa có tracklist) hay visualizer (ảnh DJ + logo, vòng phổ)'),
]


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (over or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def get(cfg: dict, dotted: str):
    node = cfg
    for part in dotted.split('.'):
        node = node[part]
    return node


def put(cfg: dict, dotted: str, value) -> None:
    node = cfg
    parts = dotted.split('.')
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def find_root(start: Path | None = None) -> Path | None:
    """The folder that holds the four repos, searched upward from `start`."""
    here = Path(start or Path.cwd()).resolve()
    for folder in [here, *here.parents]:
        if all((folder / name).is_dir() for name in REPOS.values()):
            return folder
    return None


def default_path() -> Path | None:
    if os.environ.get('RCV_CONFIG'):
        return Path(os.environ['RCV_CONFIG'])
    root = find_root()
    return root / 'mixes' / 'config.json' if root else None


def load(path=None, must_exist: bool = True) -> dict:
    path = Path(path) if path else default_path()
    if path is None:
        raise RcvError('Không tìm thấy thư mục chứa bốn repo. Truyền --config ĐƯỜNG_DẪN.', 2)
    raw = read_json(path)
    if raw is None:
        if must_exist:
            raise RcvError(f'Chưa có config: {path}. Chạy `pipeline.py init-config` trước.', 2)
        raw = {}
    genre = (raw.get('remix') or {}).get('genre')
    if genre not in (None, GENRE):
        raise RcvError(f'{path} có remix.genre = "{genre}", nhưng skill chỉ phối {GENRE}. '
                       f'Xoá khoá remix.genre khỏi config.', 2)
    cfg = deep_merge(DEFAULTS, raw)
    cfg['_path'] = str(path)
    cfg['_workspace'] = str(path.parent)
    if cfg['nct']['interval_s'] < 60:
        cfg['nct']['interval_s'] = 60      # the human asked for one minute between downloads
    return cfg


def _diff(value, default):
    """What differs from the defaults. Only that is saved, so a later version of the skill can
    change a default without an old config file pinning the old value."""
    if isinstance(value, dict) and isinstance(default, dict):
        out = {}
        for key, item in value.items():
            if key not in default:
                out[key] = item
            else:
                sub = _diff(item, default[key])
                if sub is not _SAME:
                    out[key] = sub
        return out if out else _SAME
    return _SAME if value == default else value


_SAME = object()


def save(cfg: dict, path=None) -> Path:
    path = Path(path or cfg['_path'])
    data = _diff({k: v for k, v in cfg.items() if not k.startswith('_')}, DEFAULTS)
    write_json(path, {'version': DEFAULTS['version'], **({} if data is _SAME else data)})
    return path


def init(path: Path, root: Path) -> dict:
    cfg = deep_merge(DEFAULTS, {'repos': {key: str(root / name) for key, name in REPOS.items()}})
    cfg['_path'], cfg['_workspace'] = str(path), str(path.parent)
    save(cfg)
    return cfg


def unanswered(cfg: dict) -> list[dict]:
    """First-run questions the human has not answered yet."""
    out = []
    for key, question in FIRST_RUN:
        value = get(cfg, key)
        if value is None or value is False and key == 'cover.confirmed':
            out.append({'key': key, 'question': question})
    return out


def repo(cfg: dict, name: str) -> Path:
    path = cfg['repos'].get(name)
    if not path or not Path(path).is_dir():
        raise RcvError(f'Config thiếu đường dẫn repo "{name}" hoặc thư mục không tồn tại: {path}', 2)
    return Path(path)
