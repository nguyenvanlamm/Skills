"""Small helpers shared by every script: JSON I/O, hashing, time formats, check records."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
RANK = {'FAIL': 3, 'WARN': 2, 'PASS': 1, 'SKIP': 0}

# Exit codes shared by the scripts.
EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2
EXIT_NEED_USER = 10      # the run stopped for a human decision (see state.json "waiting")
EXIT_NEED_AGENT = 20     # the run stopped for work only the agent can do (previews, metadata)


class RcvError(Exception):
    """An expected failure: message for the human, exit code for the caller."""

    def __init__(self, message: str, code: int = EXIT_FAIL):
        super().__init__(message)
        self.code = code


def read_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_text(path, text: str) -> None:
    """Atomic write: a reader (the steps pane) never sees a half-written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.' + path.name + '.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json(path, data) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def emit(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def sha256_file(path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


def file_sig(path) -> dict | None:
    """Cheap identity of a file (size + mtime); None when it is missing."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    return {'path': str(path), 'size': st.st_size, 'mtime_ns': st.st_mtime_ns}


_CONTENT: dict[str, dict] = {}


def content_sig(path, cache_file=None) -> str | None:
    """Identity of a file by what is in it (SHA-256); None when it is missing. A file written
    again with the same bytes keeps its identity, unlike `file_sig`. The hash of a large file is
    remembered by size and time, in memory and in `cache_file`, so it is computed once."""
    sig = file_sig(path)
    if sig is None:
        return None
    key = str(path)
    if not _CONTENT and cache_file is not None:
        _CONTENT.update(read_json(cache_file, {}) or {})
    hit = _CONTENT.get(key)
    if hit and hit.get('size') == sig['size'] and hit.get('mtime_ns') == sig['mtime_ns']:
        return hit['sha256']
    sha = sha256_file(path)
    _CONTENT[key] = {'size': sig['size'], 'mtime_ns': sig['mtime_ns'], 'sha256': sha}
    if cache_file is not None:
        try:
            write_json(cache_file, _CONTENT)
        except OSError:
            pass
    return sha


def slugify(text: str, maxlen: int = 48) -> str:
    text = (text or '').replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r'[^a-zA-Z0-9]+', '_', text).strip('_').lower()
    return text[:maxlen].strip('_') or 'x'


def fold(text: str) -> str:
    """Case- and accent-insensitive form used to compare titles, artists, tags."""
    text = (text or '').replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', text).strip().lower()


def round_half_up(x: float) -> int:
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def fmt_ts(seconds: float) -> str:
    """YouTube chapter stamp: MM:SS below one hour, H:MM:SS from one hour."""
    s = round_half_up(max(0.0, seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f'{h}:{m:02d}:{sec:02d}' if h else f'{m:02d}:{sec:02d}'


def parse_ts(text: str) -> int | None:
    m = re.fullmatch(r'(?:(\d+):)?(\d{1,2}):(\d{2})', text.strip())
    if not m:
        return None
    return int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))


def fmt_hms(seconds: float) -> str:
    s = int(max(0.0, seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f'{h}:{m:02d}:{sec:02d}'


def clock(ts: float | None = None) -> str:
    return time.strftime('%H:%M:%S', time.localtime(ts if ts is not None else time.time()))


def iso(ts: float | None = None) -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(ts if ts is not None else time.time()))


def check(name: str, status: str, detail: str = '', **extra) -> dict:
    assert status in RANK, status
    rec = {'name': name, 'status': status, 'detail': detail}
    rec.update(extra)
    return rec


def worst(checks: list[dict]) -> str:
    """FAIL beats WARN beats PASS; a list with only SKIPs is SKIP, an empty list is PASS."""
    if not checks:
        return 'PASS'
    top = max(checks, key=lambda c: RANK[c['status']])['status']
    return top


def run(cmd, cwd=None, env=None, timeout=None, stdin=None) -> tuple[int, str, str]:
    """Run a command and capture text output. Never raises on a non-zero exit."""
    try:
        done = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, timeout=timeout, input=stdin,
                              capture_output=True, text=True, errors='replace')
        return done.returncode, done.stdout, done.stderr
    except FileNotFoundError as exc:
        return 127, '', str(exc)
    except subprocess.TimeoutExpired as exc:
        # What was captured before the timeout comes back as bytes, even with text=True.
        def text(value) -> str:
            return value.decode(errors='replace') if isinstance(value, bytes) else (value or '')
        return 124, text(exc.stdout), text(exc.stderr) + f'\ntimeout after {timeout}s'


def die(message: str, code: int = EXIT_FAIL) -> 'NoReturn':  # noqa: F821
    print(message, file=sys.stderr)
    sys.exit(code)
