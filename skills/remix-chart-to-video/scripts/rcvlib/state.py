"""state.json: one file per run. It drives resume, the steps pane and the final report.

Only the pipeline process (and the small scripts the agent calls between pipeline segments)
write it; every write is atomic. `heartbeat` moves whenever a background stage reports progress,
which is how the pane tells a slow stage from a dead one.
"""
from __future__ import annotations

import fcntl
import os
import time
from pathlib import Path

from .common import RcvError, read_json, worst, write_json

STAGES = [
    ('preflight', 'Kiểm tra máy'),
    ('chart', 'Lấy BXH'),
    ('originals', 'Tải bản gốc'),
    ('art', 'Ảnh gốc'),
    ('remix', 'Phối Vinahouse'),
    ('mix', 'Ghép mix'),
    ('cover', 'Ảnh bìa'),
    ('video', 'Render video'),
    ('youtube', 'Thông tin YouTube'),
    ('report', 'Báo cáo'),
]
STAGE_IDS = [s for s, _ in STAGES]
ACTIVE = ('running',)


class State:
    def __init__(self, run_dir, data: dict):
        self.run_dir = Path(run_dir)
        self.path = self.run_dir / 'state.json'
        self.data = data
        self._last_write = 0.0

    # -- files ---------------------------------------------------------------------------
    @classmethod
    def create(cls, run_dir, run: dict) -> 'State':
        now = time.time()
        data = {
            'version': 1,
            'run': dict(run, created_at=now),
            'stages': [{'id': sid, 'label': label, 'status': 'todo', 'checks': []} for sid, label in STAGES],
            'now': None, 'waiting': None, 'heartbeat': now,
            'nct_commands': [], 'decisions': {}, 'result': {}, 'pids': {},
        }
        state = cls(run_dir, data)
        state.save()
        return state

    @classmethod
    def load(cls, run_dir) -> 'State':
        data = read_json(Path(run_dir) / 'state.json')
        if data is None:
            raise RcvError(f'Không có state.json trong {run_dir}', 2)
        return cls(run_dir, data)

    def save(self) -> None:
        write_json(self.path, self.data)
        self._last_write = time.time()

    # -- lookups -------------------------------------------------------------------------
    def stage(self, sid: str) -> dict:
        for st in self.data['stages']:
            if st['id'] == sid:
                return st
        raise KeyError(sid)

    def index(self, sid: str) -> int:
        return STAGE_IDS.index(sid)

    def tag(self, sid: str) -> str:
        return f'S{self.index(sid)}'

    # -- transitions ---------------------------------------------------------------------
    def start(self, sid: str, inputs_hash: str | None = None) -> None:
        st = self.stage(sid)
        resumed = st['status'] in ('interrupted', 'failed', 'waiting', 'running')
        st['elapsed_s_prev'] = (st.get('elapsed_s') or 0.0) if resumed else 0.0
        st.update(status='running', started_at=time.time(), finished_at=None, checks=[], error=None,
                  progress={}, inputs_hash=inputs_hash)
        self.data['waiting'] = None
        self.data['now'] = f'{self.tag(sid)} · {st["label"]}'
        self.data['heartbeat'] = time.time()
        self.save()

    def progress(self, sid: str, done=None, total=None, text=None, percent=None, force=False) -> None:
        """Called by long stages. Throttled to one write a second unless `force`."""
        st = self.stage(sid)
        prog = st.setdefault('progress', {})
        if done is not None:
            prog['done'] = done
        if total is not None:
            prog['total'] = total
        if percent is not None:
            prog['percent'] = round(float(percent), 1)
        if text is not None:
            prog['text'] = text
            self.data['now'] = f'{self.tag(sid)} · {text}'
        self.data['heartbeat'] = time.time()
        if force or time.time() - self._last_write >= 1.0:
            self.save()

    def _close(self, sid: str, status: str, checks, error=None, outputs=None) -> None:
        st = self.stage(sid)
        now = time.time()
        st.update(status=status, finished_at=now, checks=list(checks or []), error=error)
        st['elapsed_s'] = round(st.get('elapsed_s_prev', 0) + now - (st.get('started_at') or now), 1)
        if outputs is not None:
            st['outputs'] = outputs
        self.data['heartbeat'] = now
        self.save()

    def finish(self, sid: str, checks=None, outputs=None) -> str:
        """Mark a stage done. A FAIL among its checks turns it into a failed stage instead:
        the pane must never show a stage as done when its checks did not pass."""
        verdict = worst(checks or [])
        if verdict == 'FAIL':
            failed = '; '.join(f'{c["name"]}: {c["detail"]}' for c in checks if c['status'] == 'FAIL')
            self._close(sid, 'failed', checks, error=failed, outputs=outputs)
            return 'failed'
        self._close(sid, 'done', checks, outputs=outputs)
        return 'done'

    def fail(self, sid: str, error: str, checks=None) -> None:
        self._close(sid, 'failed', checks, error=error)

    def interrupt(self, sid: str) -> None:
        self._close(sid, 'interrupted', self.stage(sid).get('checks'), error='bị ngắt giữa chừng')

    def wait(self, sid: str, text: str, checks=None) -> None:
        """The run stops for the human. `text` says what they need to do."""
        self._close(sid, 'waiting', checks)
        self.data['waiting'] = text
        self.save()

    def invalidate_from(self, sid: str) -> None:
        """An upstream stage changed: everything from `sid` on has to run again."""
        for later in STAGE_IDS[self.index(sid):]:
            st = self.stage(later)
            if st['status'] != 'todo':
                st.update(status='todo', checks=[], progress={}, error=None, inputs_hash=None)
        self.save()

    def log_nct(self, command: str, live: bool, code: int) -> None:
        self.data['nct_commands'].append({'at': time.time(), 'command': command, 'live': live, 'exit': code})
        self.save()

    # -- views ---------------------------------------------------------------------------
    def current(self) -> dict | None:
        for st in self.data['stages']:
            if st['status'] != 'done':
                return st
        return None

    def elapsed(self) -> float:
        total = 0.0
        for st in self.data['stages']:
            if st['status'] == 'running' and st.get('started_at'):
                total += (st.get('elapsed_s_prev') or 0.0) + time.time() - st['started_at']
            else:
                total += st.get('elapsed_s') or 0.0
        return total

    def finished(self) -> bool:
        return all(st['status'] == 'done' for st in self.data['stages'])


class RunLock:
    """One pipeline process per run folder."""

    def __init__(self, run_dir):
        self.path = Path(run_dir) / '.lock'
        self.fh = None

    def __enter__(self):
        self.fh = open(self.path, 'w')
        try:
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.fh.close()
            raise RcvError(f'Một tiến trình pipeline khác đang chạy trên {self.path.parent}', 1)
        self.fh.write(str(os.getpid()))
        self.fh.flush()
        return self

    def __exit__(self, *exc):
        try:
            fcntl.flock(self.fh, fcntl.LOCK_UN)
        finally:
            self.fh.close()
        return False
