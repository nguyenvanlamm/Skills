"""The NhacCuaTui downloader repo: read the chart, fetch originals, pick the usable songs.

Live access is the human's decision (NCT terms 5.15 forbid automated scripts). This module
sends requests only when the config says so, sets NCT_LIVE_ACCESS=true inline per command and
never edits the repo's .env. RCV_FORBID_NCT=1 blocks every live call (builds, tests, evals).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

from . import config as cfgmod
from . import ffmpeg
from .common import RcvError, fold, read_json, run, slugify

AUDIO_EXT = ('.mp3', '.wav', '.flac')        # what StemForge's Auto Remix accepts
REASONS = {
    'not_searched': 'chưa tìm bản gốc (NCT đang tắt)',
    'uncertain': 'không chắc đâu là bản gốc',
    'not_found': 'không tìm thấy bản gốc',
    'skipped': 'bài bị bỏ qua khi tìm bản gốc (mashup…)',
    'not_downloaded': 'tìm thấy bản gốc nhưng NCT không cho tải',
    'file_missing': 'file bản gốc không còn trên đĩa',
    'unsupported_format': 'định dạng không phải mp3/wav/flac',
    'undecodable': 'file hỏng, không giải mã được',
    'too_short': 'quá ngắn',
    'too_long': 'quá dài',
    'too_big': 'file quá lớn',
    'duplicate': 'trùng bản gốc với một bài đã chọn',
    'remix_failed': 'StemForge phối lỗi sau khi thử lại',
    'rejected': 'bạn đã loại bài này',
}


class Downloader:
    def __init__(self, cfg: dict, state=None):
        self.cfg = cfg
        self.state = state
        self.repo = cfgmod.repo(cfg, 'downloader')
        self.python = self.repo / '.venv' / 'bin' / 'python'
        self.home = Path(cfg['nct']['home']).expanduser() if cfg['nct'].get('home') else \
            Path(os.environ.get('NCT_HOME', '~/Music/NhacCuaTuiRemix')).expanduser()

    def _cmd(self, args: list[str]) -> list[str]:
        base = [str(self.python), str(self.repo / 'run.py')]
        if self.cfg['nct'].get('home'):
            base += ['--home', str(self.home)]
        return base + args

    def _env(self, live: bool) -> dict:
        env = dict(os.environ)
        env.pop('NCT_LIVE_ACCESS', None)
        if live:
            if os.environ.get('RCV_FORBID_NCT') == '1':
                raise RcvError('RCV_FORBID_NCT=1: lượt này không được gửi request tới NCT.', 2)
            if self.cfg['nct'].get('live_access') is not True:
                raise RcvError('nct.live_access chưa bật trong config: không gửi request tới NCT.', 2)
            env['NCT_LIVE_ACCESS'] = 'true'
        return env

    def call(self, args: list[str], live: bool = False, timeout: int | None = 600) -> tuple[int, str, str]:
        rc, out, err = run(self._cmd(args), env=self._env(live), timeout=timeout)
        if self.state is not None and args and args[0] != 'report':
            self.state.log_nct(' '.join(args), live, rc)
        return rc, out, err

    def report(self, run_id: int | None = None) -> dict:
        args = ['report', '--json'] + (['--run-id', str(run_id)] if run_id else [])
        rc, out, err = self.call(args)
        if rc == 3 or not out.strip() or out.strip() == '{}':
            raise RcvError('Repo NCT chưa có lượt chạy nào (report trả rỗng).', 1)
        if rc != 0:
            raise RcvError(f'`report --json` lỗi (mã {rc}): {err.strip()[-300:]}', 1)
        return json.loads(out)

    def refresh_chart(self, html: str | None = None, top: int = 50) -> dict:
        """Save the chart as a new run. Live: 3 requests. With `html`: none."""
        args = ['remix', '--top', str(top), '--no-download', '--chart', self.cfg['nct']['chart']]
        if html:
            args += ['--html', str(html)]
        rc, out, err = self.call(args, live=not html)
        if rc != 0:
            raise RcvError(f'`remix --no-download` lỗi (mã {rc}): {(err or out).strip()[-400:]}', 1)
        rep = self.report()
        if rep['run'].get('status') != 'completed':
            raise RcvError(f'Lượt chạy NCT #{rep["run"].get("id")} không ở trạng thái completed: '
                           f'{rep["run"].get("error_message")}', 1)
        return rep

    def fetch_originals(self, run_id: int, limit: int, on_progress=None, should_stop=None) -> int:
        """Find and download the originals of the first `limit` ranks. One long command; its
        JSON log is tailed for progress because a second CLI call on the same data folder
        while it runs would not be safe."""
        interval = max(60, int(self.cfg['nct']['interval_s']))
        args = ['originals', '--run-id', str(run_id), '--limit', str(limit), '--interval', str(interval)]
        self._env(True)                                 # refuse before any waiting when NCT is off
        # The downloader keeps the interval inside one command and forgets it between two. A
        # second command (a wider window) must not download right after the first one's last song.
        last = max((c['at'] for c in (self.state.data['nct_commands'] if self.state is not None else [])
                    if c.get('live') and str(c.get('command', '')).startswith('originals')), default=0)
        while time.time() < last + interval:
            if should_stop and should_stop():
                return 130
            if on_progress:
                on_progress(0, limit, f'chờ {int(last + interval - time.time())}s trước lệnh tải kế tiếp (cách nhau {interval}s)')
            time.sleep(min(2, max(0.1, last + interval - time.time())))
        log = self.home / 'logs' / 'app.jsonl'
        offset = log.stat().st_size if log.is_file() else 0
        proc = subprocess.Popen(self._cmd(args), env=self._env(True), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        seen: set[int] = set()
        try:
            while proc.poll() is None:
                if should_stop and should_stop():
                    proc.terminate()
                    break
                offset = self._tail(log, offset, seen, limit, on_progress)
                time.sleep(2)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            self._tail(log, offset, seen, limit, on_progress)
        finally:
            if proc.poll() is None:
                proc.kill()
        if self.state is not None:
            self.state.log_nct(' '.join(args), True, proc.returncode)
        return proc.returncode

    @staticmethod
    def _tail(log: Path, offset: int, seen: set, limit: int, on_progress) -> int:
        if not log.is_file():
            return offset
        with open(log, encoding='utf-8', errors='replace') as f:
            f.seek(offset)
            chunk = f.read()
            offset = f.tell()
        for line in chunk.splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get('message', '')
            if 'position' in rec and msg.startswith('Kết quả tìm bản gốc'):
                seen.add(rec['position'])
                if on_progress:
                    on_progress(len(seen), limit, f'hạng {rec["position"]}: {rec.get("decision")}')
            elif msg.startswith('Chờ ') and on_progress:
                on_progress(len(seen), limit, msg.lower())
        return offset


# -- selection: pure functions, tested offline ----------------------------------------------

def distributor(release_information: str | None) -> str | None:
    m = re.search(r'Nhà phân phối:\s*([^;]+)', release_information or '')
    return m.group(1).strip() if m else None


def base_title(title: str) -> str:
    """Chart titles carry version marks: "Xin Đừng Rời Xa Anh (Remix Short 1)" -> "Xin Đừng Rời Xa Anh"."""
    out = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]', '', title or '')
    out = re.sub(r'\s+(remix|drill)(\s+version)?\s*$', '', out, flags=re.IGNORECASE)
    return out.strip() or (title or '').strip()


def manual_file(sources_dir, rank: int) -> Path | None:
    """A file the human supplied for a rank: <sources>/NN_anything.mp3|wav|flac."""
    folder = Path(sources_dir)
    if not folder.is_dir():
        return None
    for path in sorted(folder.iterdir()):
        m = re.match(r'0*(\d+)[_\-. ]', path.name)
        if m and int(m.group(1)) == rank and path.suffix.lower() in AUDIO_EXT and path.is_file():
            return path
    return None


def expected_manual_name(rank: int, title: str) -> str:
    return f'{rank:02d}_{slugify(base_title(title), 40)}.mp3'


def classify(report: dict, cfg: dict, sources_dir, rejected: dict | None = None, probe=ffmpeg.probe,
             rejected_at: dict | None = None) -> list[dict]:
    """One record per chart song, in rank order: usable or not, and why. A rank the human
    rejected (its remix failed) stays out, unless they put a file for it into sources/ after
    the rejection (`rejected_at`): another file is another try."""
    sel = cfg['selection']
    rejected = {int(k): v for k, v in (rejected or {}).items()}
    rejected_at = {int(k): float(v) for k, v in (rejected_at or {}).items()}
    seen: dict[str, int] = {}
    out = []
    for song in sorted(report.get('songs', []), key=lambda s: s['position']):
        rank = song['position']
        orig = song.get('original') or {}
        cand = {
            'rank': rank, 'chart_title': song.get('title'), 'chart_artist': song.get('artist'),
            'chart_url': song.get('nct_url'), 'release_information': song.get('release_information'),
            'distributor': distributor(song.get('release_information')),
            'manual_search_url': orig.get('manual_search_url'),
            'usable': False, 'reason': None, 'detail': None,
        }
        out.append(cand)
        manual = manual_file(sources_dir, rank)
        if rank in rejected and not (manual and rank in rejected_at and manual.stat().st_mtime > rejected_at[rank]):
            cand.update(reason=rejected[rank], detail=REASONS.get(rejected[rank], rejected[rank]))
            continue
        if manual:
            path, kind = manual, 'manual'
            title = orig.get('title') if orig.get('decision') == 'matched' else (orig.get('base_title') or base_title(song.get('title')))
            artist = orig.get('artist') if orig.get('decision') == 'matched' else song.get('artist')
            dedupe = fold(f'{title}|{(artist or "").split(",")[0]}')
        else:
            decision = orig.get('decision') or 'not_searched'
            if decision != 'matched':
                cand.update(reason=decision if decision in REASONS else 'not_found', detail=REASONS.get(decision, decision))
                continue
            path = orig.get('local_file_path')
            if not path:
                cand.update(reason='not_downloaded', detail=f'{REASONS["not_downloaded"]} ({orig.get("status")})')
                continue
            path = Path(path)
            if not path.is_file():
                cand.update(reason='file_missing', detail=str(path))
                continue
            kind, title, artist = 'nct_original', orig.get('title'), orig.get('artist')
            dedupe = orig.get('nct_url') or fold(f'{title}|{(artist or "").split(",")[0]}')
        cand.update(title=title, artist=artist,
                    source={'path': str(path), 'kind': kind, 'nct_url': orig.get('nct_url') if kind != 'manual' else None})
        if path.suffix.lower() not in AUDIO_EXT:
            cand.update(reason='unsupported_format', detail=path.suffix)
            continue
        try:
            info = probe(path)
        except RcvError as exc:
            cand.update(reason='undecodable', detail=str(exc)[:160])
            continue
        if not info.get('audio'):
            cand.update(reason='undecodable', detail='không có luồng âm thanh')
            continue
        tagged = (info.get('tags') or {}).get('artist') or (info.get('tags') or {}).get('album_artist')
        if kind == 'manual' and sel.get('manual_artist') == 'tags' and tagged:
            cand.update(artist=tagged, artist_from='tags')               # the human's file names its own singer
            dedupe = fold(f'{title}|{tagged.split(",")[0]}')
        dur = info['duration']
        cand['source'].update(duration=round(dur, 3), size=info['size'], mtime_ns=path.stat().st_mtime_ns)
        if dur < sel['min_duration_s']:
            cand.update(reason='too_short', detail=f'{dur:.0f}s < {sel["min_duration_s"]}s')
        elif dur > sel['max_duration_s']:
            cand.update(reason='too_long', detail=f'{dur:.0f}s > {sel["max_duration_s"]}s')
        elif info['size'] > sel['max_size_mb'] * 1024 * 1024:
            cand.update(reason='too_big', detail=f'{info["size"] / 1048576:.0f} MB')
        elif dedupe in seen:
            cand.update(reason='duplicate', detail=f'trùng với hạng {seen[dedupe]}')
        else:
            seen[dedupe] = rank
            cand['usable'] = True
    return out


def select(candidates: list[dict], count: int, window: int) -> dict:
    """The first `count` usable songs among ranks 1..window, and the ranks in the window that
    are not usable (the "missing" songs the human decides about)."""
    inside = [c for c in candidates if c['rank'] <= window]
    chosen = [c for c in inside if c['usable']][:count]
    missing = [c for c in inside if not c['usable']] if len(chosen) < count else []
    return {'window': window, 'count': count, 'selected': chosen, 'missing': missing,
            'short_by': max(0, count - len(chosen)),
            'exact_top': [c['rank'] for c in chosen] == list(range(1, len(chosen) + 1))}


def build_manifest(report: dict, selection: dict, cfg: dict, sequence: list[int] | None = None) -> dict:
    tracks = []
    for i, c in enumerate(selection['selected'], 1):
        label = cfg['cover']['label'].format(artist=c['artist'] or '', title=c['title'] or '').strip(' -')
        tracks.append({
            'id': i, 'rank': c['rank'], 'title': c['title'], 'artist': c['artist'], 'label': label,
            'chart_title': c['chart_title'], 'chart_artist': c['chart_artist'], 'chart_url': c['chart_url'],
            'distributor': c['distributor'], 'release_information': c['release_information'],
            'source': c['source'], 'slug': f'r{c["rank"]:02d}_{slugify(c["title"], 36)}',   # by rank: stable when the selection changes
        })
    order = sequence or [t['id'] for t in tracks]
    bad = [i for i in order if not 1 <= i <= len(tracks)]
    if bad:
        raise RcvError(f'--sequence nhắc tới bài không có trong danh sách: {bad}', 2)
    run = report.get('run', {})
    return {
        'version': 1,
        'chart': {'tag': run.get('chart_tag'), 'title': run.get('chart_title'), 'date': run.get('chart_date'),
                  'url': run.get('chart_url'), 'nct_run_id': run.get('id')},
        'requested_count': selection['count'], 'window': selection['window'],
        'exact_top': selection['exact_top'] and order == [t['id'] for t in tracks],
        'tracks': tracks,
        'playlist': [{'position': n, 'track': tid} for n, tid in enumerate(order, 1)],
    }


def missing_message(selection: dict, sources_dir, live: bool, rejected: dict | None = None) -> str:
    """What the human reads when the run stops for missing songs."""
    rejected = {int(k) for k in (rejected or {})}
    ranks = ', '.join(str(c['rank']) for c in selection['missing'])
    # the first line stands alone: it is all the steps pane shows
    lines = [f'Thiếu {selection["short_by"]} bài trong {selection["count"]} bài đầu BXH (hạng {ranks} không dùng được): '
             'chọn backfill, skip hoặc manual.']
    for c in selection['missing']:
        lines.append(f'  hạng {c["rank"]}: {c["chart_title"]} — {c["chart_artist"]}: {c["detail"] or c["reason"]}'
                     + (f'\n    tìm tay: {c["manual_search_url"]}' if c.get('manual_search_url') else '')
                     + f'\n    tự đặt file{" khác (file cũ đã phối lỗi)" if c["rank"] in rejected else ""}: '
                       f'{Path(sources_dir) / expected_manual_name(c["rank"], c["chart_title"])}')
    lines.append('Chọn: backfill (lấy bù hạng kế tiếp' + ('' if live else '; NCT đang tắt nên bạn phải tự đặt file')
                 + '), skip (bỏ qua, mix ít bài hơn), manual (bạn tự đặt file rồi chạy tiếp).')
    return '\n'.join(lines)
