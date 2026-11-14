"""Draw a video's songs from the human's ballad list: one period at random, then its songs in a
random order.

The list is a JSON file the human keeps (`songlist.path`):
    {"periods": [{"period": "2010-2011",
                  "songs": [{"rank": 1, "title": "…", "artist": "A & B", "songwriter": "…", "year": 2010}]}]}
`artist` and `songwriter` are strings; several names are joined with "&" or ",". A last period
may be open ("2026-present"). The first shape of the list is still read:
    {"cac_giai_doan": [{"giai_doan": "Giai đoạn 2010–2014",
                        "danh_sach_bai_hat": [{"stt": 41, "bai_hat": "…", "ca_si": ["…"], "nhac_si": ["…"]}]}]}
A period may list a song twice; it counts once. Songs an earlier video of this workspace used
(`song_history.json` next to the config) come last, so a period is used up before any song
returns. The draw is a pure function of the list, the history and a seed the run keeps, so the
same run always shows the same songs.

The drawn order goes to the downloader as a plain song list (`songs --file`), positions 1..M:
the first `count` are the video's songs, the rest are what "backfill" takes when a song cannot
be found or fetched. The downloader searches at most 50 positions (its MAX_CHART_SIZE).
"""
from __future__ import annotations

import random
import re
import time
from pathlib import Path

from .common import RcvError, fold, read_json, slugify, write_json

MAX_POOL = 50
SCHEMA = 3                      # how the list is read; raise it when that changes, so runs re-read their composers
PERIOD_RANGE = re.compile(r'(\d{4})\s*[–—-]\s*(\d{4})')
PERIOD_OPEN = re.compile(r'(\d{4})\s*[–—-]\s*(present|now|nay|hiện tại|hien tai)\b', re.IGNORECASE)   # "2026-present"


def default_path(cfg: dict) -> Path | None:
    """`songlist.path` as given, or relative to the folder that holds the four repos."""
    raw = cfg.get('songlist', {}).get('path')
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        root = Path(cfg['repos'].get('downloader') or '.').parent
        path = root / path
    return path


def period_slug(name: str) -> str:
    m = PERIOD_RANGE.search(name or '')
    if m:
        return f'{m.group(1)}-{m.group(2)}'
    m = PERIOD_OPEN.search(name or '')
    return f'{m.group(1)}-nay' if m else slugify(name or 'giai-doan', 24)


def period_label(name: str) -> str:
    """"Giai đoạn 2010–2014" -> "2010–2014": the part a cover line or title can carry."""
    m = PERIOD_RANGE.search(name or '')
    if m:
        return f'{m.group(1)}–{m.group(2)}'
    m = PERIOD_OPEN.search(name or '')
    return f'{m.group(1)}–nay' if m else (name or '').strip()


UNKNOWN = re.compile(r'^\s*((chưa|cần|chua|can)\s+(xác|xac)\s+(minh)\b|(nhiều|nhieu)\s+(nhạc sĩ|nhac si|tác giả|tac gia|ca sĩ|ca si)\b'
                     r'|(không|khong|chưa|chua)\s+(rõ|ro)\b)', re.IGNORECASE)
JOINED = re.compile(r'\s*(?:,|&)\s*')       # "A & B", "A, B & C"; never "/" (W/n) or brackets (Emcee L (Da LAB))


def names(value) -> list[str]:
    """A list of names from a list or a single string. "Chưa xác minh" / "Cần xác minh" (not
    checked yet) is no name: a string is never split into its letters."""
    items = [value] if isinstance(value, str) else (value or [])
    return [str(x).strip() for x in items if str(x).strip() and not UNKNOWN.match(str(x))]


def split_names(value) -> list[str]:
    """The names in one string of the list ("Tim & Minh Hằng", "A, B & C"), each once. "Nhiều
    nhạc sĩ" (many, none named) is no name."""
    if not isinstance(value, str) or UNKNOWN.match(value):
        return []
    out = []
    for part in JOINED.split(value):
        if part.strip() and part.strip() not in out:
            out.append(part.strip())
    return names(out)


def song_key(title: str, artists: list[str]) -> str:
    return fold(f'{title}|{(artists or [""])[0]}')


def song_keys(title: str, artists: list[str]) -> list[str]:
    """One key per singer: an earlier video's key names only its first singer, and the list may
    since have put the singers of a duet in another order."""
    return [fold(f'{title}|{a}') for a in (artists or [''])]


def is_used(song: dict, used: set[str]) -> bool:
    return any(k in used for k in song.get('keys') or [song['key']])


def _blocks(path: Path, data) -> list[tuple[str, list[dict]]]:
    """(period name, its songs as title/artists/composers/stt/year) for either shape of the list."""
    if isinstance(data, dict) and isinstance(data.get('periods'), list) and data['periods']:
        out = []
        for i, block in enumerate(data['periods'], 1):
            raw = str((block or {}).get('period') or '').strip()
            songs = (block or {}).get('songs')
            if not raw or not isinstance(songs, list):
                raise RcvError(f'{path}: giai đoạn thứ {i} thiếu "period" hoặc "songs"', 2)
            name = raw if raw.lower().startswith('giai') else f'Giai đoạn {period_label(raw)}'
            out.append((name, [{'title': str((s or {}).get('title') or '').strip(), 'artists': split_names((s or {}).get('artist')),
                                'composers': split_names((s or {}).get('songwriter')), 'stt': (s or {}).get('rank'),
                                'year': (s or {}).get('year') if isinstance((s or {}).get('year'), int) else None,
                                '_field': 'title'} for s in songs]))
        return out
    if isinstance(data, dict) and isinstance(data.get('cac_giai_doan'), list) and data['cac_giai_doan']:
        out = []
        for i, block in enumerate(data['cac_giai_doan'], 1):
            name = str((block or {}).get('giai_doan') or '').strip()
            songs = (block or {}).get('danh_sach_bai_hat')
            if not name or not isinstance(songs, list):
                raise RcvError(f'{path}: giai đoạn thứ {i} thiếu "giai_doan" hoặc "danh_sach_bai_hat"', 2)
            out.append((name, [{'title': str((s or {}).get('bai_hat') or '').strip(), 'artists': names((s or {}).get('ca_si')),
                                'composers': names((s or {}).get('nhac_si')), 'stt': (s or {}).get('stt'), 'year': None,
                                '_field': 'bai_hat'} for s in songs]))
        return out
    raise RcvError(f'{path}: cần một object có "periods" (mỗi giai đoạn có "period" và "songs"), '
                   f'hoặc kiểu cũ "cac_giai_doan"', 2)


def load(path) -> list[dict]:
    """The periods of the list, each song once. A malformed file is a usage error that names
    the entry, never a half-read list."""
    path = Path(path)
    data = read_json(path)
    periods = []
    for name, songs in _blocks(path, data):
        seen, kept, dupes, unsung = set(), [], 0, []
        for j, s in enumerate(songs, 1):
            title, artists = s['title'], s['artists']
            if not title:
                raise RcvError(f'{path}: {name}, bài thứ {j} thiếu "{s["_field"]}"', 2)
            if not artists:                     # "Chưa xác minh": NCT cannot be searched by singer, the video cannot credit one
                unsung.append(title)
                continue
            key = song_key(title, artists)
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            kept.append({'title': title, 'artists': artists, 'stt': s['stt'], 'key': key, 'keys': song_keys(title, artists),
                         'composers': s['composers'], 'year': s['year']})
        periods.append({'name': name, 'slug': period_slug(name), 'label': period_label(name), 'songs': kept, 'duplicates': dupes,
                        'no_singer': unsung})
    slugs = [p['slug'] for p in periods]
    if len(set(slugs)) != len(slugs):
        raise RcvError(f'{path}: hai giai đoạn có cùng khoảng năm ({", ".join(slugs)})', 2)
    return periods


def find_period(periods: list[dict], wanted: str) -> dict:
    w = fold(wanted).replace('–', '-')
    w = period_slug(wanted) if PERIOD_OPEN.search(wanted or '') else w      # "2026-present" is "2026-nay"
    for p in periods:
        if w in (p['slug'], fold(p['name']).replace('–', '-'), fold(p['label']).replace('–', '-')):
            return p
    raise RcvError(f'Không có giai đoạn "{wanted}". Các giai đoạn: {", ".join(p["slug"] for p in periods)}', 2)


# -- history: which songs earlier videos used ---------------------------------------------------

def history_path(cfg: dict) -> Path:
    return Path(cfg['_workspace']) / 'song_history.json'


def load_history(cfg: dict) -> dict:
    data = read_json(history_path(cfg)) or {}
    data.setdefault('version', 1)
    data.setdefault('runs', {})
    return data


def used_keys(cfg: dict, exclude_run: str | None = None) -> set[str]:
    """Songs of the other runs that still exist in the workspace. A run folder the human
    deleted gives its songs back."""
    workspace = Path(cfg['_workspace'])
    out = set()
    for run, rec in load_history(cfg)['runs'].items():
        if run != exclude_run and (workspace / run).is_dir():
            out.update(rec.get('keys', []))
    return out


def record(cfg: dict, run_name: str, songs: list[dict]) -> None:
    """The songs this run's video uses (titles and keys), replacing what it recorded before."""
    data = load_history(cfg)
    old = data['runs'].get(run_name) or {}
    data['runs'][run_name] = {'at': old.get('at') or time.time(), 'updated': time.time(),
                              'keys': [s['key'] for s in songs], 'titles': [s['title'] for s in songs]}
    write_json(history_path(cfg), data)


# -- the draw -------------------------------------------------------------------------------------

def draw(periods: list[dict], used: set[str], seed: int, count: int, period: str | None = None,
         pool: int = MAX_POOL) -> dict:
    """The period (given, or one at random) and up to `pool` of its songs in a random order:
    songs no earlier video used first, then the used ones. Same inputs, same answer."""
    rng = random.Random(seed)
    chosen = find_period(periods, period) if period else rng.choice(periods)
    fresh = [s for s in chosen['songs'] if not is_used(s, used)]
    old = [s for s in chosen['songs'] if is_used(s, used)]
    rng.shuffle(fresh)
    rng.shuffle(old)
    notes = []
    if len(fresh) < count:
        notes.append(f'{chosen["name"]} chỉ còn {len(fresh)} bài chưa có trong video nào; '
                     f'{min(count, len(chosen["songs"])) - len(fresh)} bài sẽ lặp lại bài của video trước')
    if len(chosen['songs']) < count:
        notes.append(f'{chosen["name"]} chỉ có {len(chosen["songs"])} bài, ít hơn {count}')
    songs = (fresh + old)[:max(count, min(pool, MAX_POOL))]
    return {'period': chosen['name'], 'slug': chosen['slug'], 'label': chosen['label'], 'seed': seed,
            'count': count, 'fresh': len(fresh), 'period_size': len(chosen['songs']),
            'duplicates_dropped': chosen['duplicates'], 'notes': notes,
            'songs': [{**s, 'position': i} for i, s in enumerate(songs, 1)]}


def new_seed() -> int:
    return random.SystemRandom().randrange(1, 2 ** 31 - 1)


def write_run_files(run_dir, picked: dict, list_path) -> Path:
    """RUN/songlist/pick.json (what was drawn, from where) and list.json (what the downloader reads)."""
    folder = Path(run_dir) / 'songlist'
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / 'pick.json', {**picked, 'list_path': str(list_path)})
    out = folder / 'list.json'
    write_json(out, [{'title': s['title'], 'artists': s['artists']} for s in picked['songs']])
    return out


def by_position(run_dir) -> dict[int, dict]:
    """The drawn songs by position. Their composers and years are read from the list again when
    it is still there, so a corrected list (or a corrected reader) reaches the manifest."""
    pick = read_json(Path(run_dir) / 'songlist' / 'pick.json') or {}
    out = {int(s['position']): dict(s) for s in pick.get('songs', [])}
    path = Path(pick.get('list_path') or '')
    if path.is_file():
        try:
            known = {k: s for p in load(path) for s in p['songs'] for k in s['keys']}
        except RcvError:
            known = {}
        for s in out.values():
            if s.get('key') in known:
                s['composers'] = known[s['key']]['composers']
                s['year'] = known[s['key']]['year']
    return out
