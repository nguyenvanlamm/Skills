"""StemForge Auto Remix over its HTTP API: start and stop the server, one job per song.

The server is started with STEMFORGE_REMIX_RETENTION_DAYS=0. Left at its default (7), the
server deletes every finished job older than a week, an hour after it starts and hourly after
that, which would remove job folders this skill never created.
"""
from __future__ import annotations

import http.client
import json
import math
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from . import config as cfgmod
from . import ffmpeg
from .common import RcvError, check, digest, read_json, sha256_file, write_json

STAGE_VI = {'queued': 'chờ', 'analyzing': 'phân tích', 'separating': 'tách giọng', 'syncing': 'đồng bộ tempo',
            'generating': 'tạo nhạc nền', 'arranging': 'phối khí', 'mixing': 'trộn', 'mastering': 'master',
            'exporting': 'xuất file', 'completed': 'xong', 'failed': 'lỗi', 'cancelled': 'đã huỷ'}
TERMINAL_BAD = ('failed', 'cancelled')
JOBS_DIR = Path('~/.local/share/stemforge/output/remix/local').expanduser()
API_BPM = (60.0, 200.0)         # target_bpm StemForge's API accepts (AutoRemixRequest._bpm)
# Part of the remix stage's inputs: raise it when verify_remix gains a check, so an unfinished
# run checks its finished remixes again (only the ones that fail it are remixed again).
VERIFY_VERSION = 2


class Interrupted(Exception):
    pass


class Api:
    READ_TRIES, READ_PAUSE_S = 3, 2.0

    def __init__(self, host: str, port: int):
        self.host, self.port = host, int(port)

    def _request(self, method: str, path: str, body=None, timeout: float = 30, tries: int | None = None):
        """One request. A read (GET) that gets no answer is asked again: during a long run one
        slow or dropped answer must not end the stage. A write is sent once."""
        tries = tries or (self.READ_TRIES if method == 'GET' else 1)
        for attempt in range(tries):
            conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
            try:
                headers = {}
                data = None
                if body is not None:
                    data = json.dumps(body).encode()
                    headers['Content-Type'] = 'application/json'
                conn.request(method, path, body=data, headers=headers)
                resp = conn.getresponse()
                raw = resp.read()
                ctype = resp.getheader('Content-Type') or ''
                payload = json.loads(raw) if 'json' in ctype and raw else raw
                return resp.status, payload
            except (OSError, http.client.HTTPException, ValueError) as exc:
                if attempt + 1 >= tries:
                    raise RcvError(f'StemForge không trả lời {method} {path}: {type(exc).__name__}: {exc}')
                time.sleep(self.READ_PAUSE_S)
            finally:
                conn.close()

    def _ok(self, method: str, path: str, body=None, timeout: float = 30):
        status, payload = self._request(method, path, body, timeout)
        if status >= 400:
            detail = payload.get('detail') if isinstance(payload, dict) else str(payload)[:200]
            raise RcvError(f'StemForge {method} {path} trả {status}: {detail}')
        return payload

    def health(self) -> bool:
        try:
            status, payload = self._request('GET', '/api/health', timeout=5, tries=1)
            return status == 200 and isinstance(payload, dict) and payload.get('status') == 'ok'
        except RcvError:
            return False

    def status(self) -> dict:
        return self._ok('GET', '/api/auto-remix/status', timeout=60)

    def upload(self, path, filename: str) -> dict:
        boundary = '----rcv' + os.urandom(8).hex()
        safe = filename.replace('"', '').replace('\r', '').replace('\n', '')
        head = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{safe}"\r\n'
                'Content-Type: application/octet-stream\r\n\r\n').encode()
        tail = f'\r\n--{boundary}--\r\n'.encode()
        size = os.path.getsize(path)
        conn = http.client.HTTPConnection(self.host, self.port, timeout=900)
        try:
            conn.putrequest('POST', '/api/auto-remix/upload')
            conn.putheader('Content-Type', f'multipart/form-data; boundary={boundary}')
            conn.putheader('Content-Length', str(len(head) + size + len(tail)))
            conn.endheaders()
            conn.send(head)
            with open(path, 'rb') as f:
                while block := f.read(1 << 20):
                    conn.send(block)
            conn.send(tail)
            resp = conn.getresponse()
            raw = resp.read()
            payload = json.loads(raw) if raw else {}
            if resp.status >= 400:
                raise RcvError(f'StemForge từ chối file {filename} ({resp.status}): {payload.get("detail")}')
            return payload
        finally:
            conn.close()

    def create(self, payload: dict) -> dict:
        return self._ok('POST', '/api/auto-remix', payload)

    def job(self, job_id: str) -> dict | None:
        status, payload = self._request('GET', f'/api/auto-remix/{job_id}')
        if status == 404:
            return None
        if status >= 400:
            raise RcvError(f'StemForge GET job {job_id} trả {status}')
        return payload

    def retry(self, job_id: str, updates: dict | None = None) -> dict:
        """Re-queue a finished job; StemForge reuses every stage whose inputs did not change.
        `updates` changes job options first (e.g. target_bpm)."""
        return self._ok('POST', f'/api/auto-remix/{job_id}/retry', updates or {})

    def analysis(self, job_id: str) -> dict | None:
        """The analysis summary, available once the job's first stage is done; None before that."""
        status, payload = self._request('GET', f'/api/auto-remix/{job_id}/analysis')
        return payload if status == 200 and isinstance(payload, dict) else None

    def cancel(self, job_id: str) -> None:
        self._request('POST', f'/api/auto-remix/{job_id}/cancel')

    def delete(self, job_id: str) -> None:
        self._ok('DELETE', f'/api/auto-remix/{job_id}')

    def download(self, job_id: str, fmt: str, dest) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + '.partial')
        conn = http.client.HTTPConnection(self.host, self.port, timeout=900)
        try:
            conn.request('GET', f'/api/auto-remix/{job_id}/download?format={fmt}')
            resp = conn.getresponse()
            if resp.status != 200:
                raise RcvError(f'StemForge không trả file {fmt} của job {job_id} ({resp.status})')
            with open(tmp, 'wb') as f:
                while block := resp.read(1 << 20):
                    f.write(block)
        finally:
            conn.close()
        os.replace(tmp, dest)
        return dest


class Server:
    """The StemForge process. The skill stops only a server it started itself."""

    def __init__(self, cfg: dict, run_dir, state=None):
        self.cfg, self.run_dir, self.state = cfg, Path(run_dir), state
        self.rm = cfg['remix']
        self.api = Api(self.rm['host'], self.rm['port'])
        self.repo = cfgmod.repo(cfg, 'stemforge')
        self.pidfile = self.run_dir / 'stemforge.pid.json'
        self.proc: subprocess.Popen | None = None
        self.owned = False

    def _record(self) -> dict | None:
        rec = read_json(self.pidfile)
        if not rec:
            return None
        try:
            os.kill(rec['pid'], 0)
            argv = Path(f'/proc/{rec["pid"]}/cmdline').read_bytes().decode(errors='replace').split('\0')
            cwd = os.readlink(f'/proc/{rec["pid"]}/cwd')
        except (OSError, KeyError):
            return None
        # A pid is reused after a crash. It is this skill's server only when it is StemForge's
        # run.py, started in the StemForge repo, on the port this record names.
        port = str(rec.get('port'))
        ours = 'run.py' in argv and any(a == '--port' and argv[i + 1:i + 2] == [port] for i, a in enumerate(argv)) \
            and Path(cwd) == self.repo.resolve()
        return rec if ours else None

    def ensure(self) -> list[dict]:
        checks = []
        if self.api.health():
            rec = self._record()
            self.owned = bool(rec)
            if rec:
                checks.append(check('stemforge_server', 'PASS', f'dùng lại server do skill khởi động (pid {rec["pid"]})'))
            else:
                checks.append(check('stemforge_server', 'WARN',
                                    'server StemForge đang chạy sẵn, không do skill khởi động: skill sẽ không dừng nó '
                                    'và không kiểm soát được việc nó tự xoá job cũ hơn 7 ngày'))
        else:
            self._start()
            checks.append(check('stemforge_server', 'PASS', f'đã khởi động server (pid {self.proc.pid}), tắt tự dọn job'))
        ready = self.api.status()
        if not ready.get('ready'):
            raise RcvError(f'StemForge chưa sẵn sàng cho Auto Remix: thiếu {ready.get("missing")}; '
                           f'acestep={ready.get("acestep")}')
        gpu = ready.get('gpu') or {}
        if gpu.get('cuda'):
            free = gpu.get('free_vram_mb', 0)
            checks.append(check('gpu_vram', 'PASS' if free >= 10000 else 'WARN',
                                f'{gpu.get("name")}: còn trống {free} MB / {gpu.get("total_vram_mb")} MB'
                                + ('' if free >= 10000 else ' (chặng tạo nhạc cần khoảng 10 GB; hãy đóng app dùng GPU)')))
        else:
            checks.append(check('gpu_vram', 'WARN', f'StemForge không thấy CUDA: {gpu.get("error")}'))
        return checks

    def _start(self) -> None:
        python = self.repo / '.venv' / 'bin' / 'python'
        if not python.is_file():
            raise RcvError(f'Không có {python}. Chạy `uv sync --locked` trong repo StemForge.')
        env = dict(os.environ)
        env['STEMFORGE_REMIX_RETENTION_DAYS'] = '0'
        env['VIRTUAL_ENV'] = str(self.repo / '.venv')
        env['PATH'] = f'{self.repo / ".venv" / "bin"}:{env.get("PATH", "")}'
        if self.rm.get('separator'):
            env['STEMFORGE_REMIX_SEPARATOR'] = str(self.rm['separator'])
        log = self.run_dir / 'logs' / 'stemforge.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        cmd = [str(python), 'run.py', '--offline', '--host', self.rm['host'], '--port', str(self.rm['port']),
               '--acestep-port', str(self.rm['acestep_port'])]
        with open(log, 'ab') as fh:
            self.proc = subprocess.Popen(cmd, cwd=str(self.repo), env=env, stdout=fh, stderr=subprocess.STDOUT,
                                         start_new_session=True)
        self.owned = True
        write_json(self.pidfile, {'pid': self.proc.pid, 'port': self.rm['port'], 'started_at': time.time(),
                                  'started_by_skill': True})
        deadline = time.time() + self.rm['start_timeout_s']
        while time.time() < deadline:
            if self.proc.poll() is not None:
                tail = log.read_text(errors='replace')[-600:]
                self.pidfile.unlink(missing_ok=True)
                self.owned = False
                raise RcvError(f'Server StemForge thoát ngay khi khởi động (mã {self.proc.returncode}):\n{tail}')
            if self.api.health():
                return
            time.sleep(1)
        self.stop()
        raise RcvError(f'Server StemForge không trả lời sau {self.rm["start_timeout_s"]}s; xem {log}')

    def stop(self) -> None:
        """Stop the server this skill started (SIGINT lets it shut ACE-Step down too)."""
        rec = self._record()
        pid = self.proc.pid if self.proc and self.proc.poll() is None else (rec or {}).get('pid')
        if not self.owned and not rec:
            return
        if pid:
            try:
                os.kill(pid, signal.SIGINT)
            except OSError:
                pid = None
        deadline = time.time() + 40
        while pid and time.time() < deadline:
            if self.proc is not None:
                if self.proc.poll() is not None:
                    break
            else:
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
            time.sleep(0.5)
        else:
            if pid:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except OSError:
                    pass
        try:
            self.pidfile.unlink()
        except OSError:
            pass
        self.owned = False


def job_key(source_sha: str, rm: dict) -> str:
    key = {'sha': source_sha, 'genre': cfgmod.GENRE, 'bpm': rm['target_bpm'], 'key': rm['target_key'],
           'quality': rm['quality'], 'separator': rm.get('separator')}
    if source_tempo_mode(rm):
        key['center'] = rm.get('source_center_bpm')
    return digest(key)


# -- each song at its own tempo (remix.target_bpm = "source") ---------------------------------

def source_tempo_mode(rm: dict) -> bool:
    return rm.get('target_bpm') == 'source'


def pick_target(source_bpm: float, center: float, avoid=()) -> float:
    """The tempo that keeps a song at its own speed: its BPM, doubled or halved, whichever lies
    nearest `center`. StemForge then maps the groove x1, x2 or x0.5 and stretches nothing
    (`plan_tempo` in its tempo_sync.py picks the mapping with the smallest stretch). Only tempos
    the API accepts are candidates (API_BPM, see references/repo_contracts.md); `avoid` holds
    tempos whose backing already missed."""
    cands = [round(source_bpm * m, 2) for m in (1.0, 2.0, 0.5) if API_BPM[0] <= source_bpm * m <= API_BPM[1]]
    cands = [t for t in cands if not any(abs(t - a) < 0.02 for a in avoid if a)]
    if not cands:
        raise RcvError(f'Tempo bài gốc {source_bpm} BPM không còn ánh xạ nào vào {API_BPM[0]:g}–{API_BPM[1]:g} BPM '
                       f'của StemForge' + (f' (đã thử {", ".join(f"{a:g}" for a in avoid)} BPM)' if avoid else ''))
    return min(cands, key=lambda t: abs(math.log(t / center)))


def other_octave(source_bpm, rm: dict, tried: list) -> float | None:
    """The song's own tempo at an octave not tried yet, or None."""
    if not source_bpm:
        return None
    try:
        return pick_target(float(source_bpm), rm['source_center_bpm'], tried)
    except RcvError:
        return None


def backing_tempo_check(rep: dict) -> dict:
    """Does the generated backing run at the tempo the remix asked for? StemForge measures it
    (generation.chosen.validation) and, when no attempt passes, keeps the best one anyway. A
    "cover" or "complete" backing is only shifted into place, never conformed to the tempo
    (`_conform` in its pipeline.py), so one that missed stays off the beat of the voice. A
    "text2music" backing is stretched to the tempo after the measurement."""
    chosen = (rep.get('generation') or {}).get('chosen') or {}
    val = chosen.get('validation') or {}
    want = (rep.get('tempo') or {}).get('target_bpm')
    if 'bpm_ok' not in val:
        return check('backing_tempo', 'SKIP', 'remix_report.json không có số đo nhịp của nhạc nền')
    got = val.get('measured_bpm')
    if chosen.get('strategy') == 'text2music':
        return check('backing_tempo', 'PASS', f'nhạc nền text2music đo được {got} BPM, StemForge co giãn về {want} BPM')
    if val['bpm_ok'] is False:
        return check('backing_tempo', 'FAIL', f'nhạc nền đo được {got} BPM, cần {want} BPM: tiếng trống lệch giọng hát')
    align = chosen.get('alignment') or {}
    if align.get('ok') is False:
        return check('backing_tempo', 'WARN', f'nhạc nền {got} BPM nhưng lệch giọng hát tới {align.get("lag_spread_ms")} ms '
                                              f'giữa các đoạn: nên nghe lại')
    return check('backing_tempo', 'PASS', f'nhạc nền đo được {got} BPM (cần {want} BPM)')


def known_source_bpm(tdir: Path, track: dict) -> float | None:
    """A source tempo StemForge already measured for this file: from an earlier attempt
    (source_tempo.json, matched by checksum) or from the remix report a `--from-run` copied
    (matched by the source's duration)."""
    src = track.get('source') or {}
    rec = read_json(tdir / 'source_tempo.json') or {}
    if rec.get('bpm') and rec.get('sha256') == src.get('sha256'):
        return float(rec['bpm'])
    rep = (read_json(tdir / 'remix_report.json') or {}).get('source') or {}
    if rep.get('bpm') and rep.get('duration') and src.get('duration') and abs(rep['duration'] - src['duration']) <= 1.0:
        return float(rep['bpm'])
    return None


def preset_bpm_range(cfg: dict) -> tuple[float, float] | None:
    """The preset's tempo range, to name the songs whose own tempo lies outside it."""
    try:
        bpm = json.loads((cfgmod.repo(cfg, 'stemforge') / 'presets' / 'remix' / f'{cfgmod.GENRE}.json').read_text())['bpm']
        return float(bpm['min']), float(bpm['max'])
    except (OSError, KeyError, ValueError, RcvError):
        return None


def measure_source_bpm(api: Api, job_id: str, rm: dict, should_stop) -> tuple[float | None, tuple | None]:
    """Wait for StemForge's first stage (analysis) of the job and read the source tempo."""
    deadline = time.time() + rm['stall_s']
    while True:
        if should_stop():
            raise Interrupted()
        ana = api.analysis(job_id)
        if ana and ana.get('bpm'):
            return float(ana['bpm']), None
        job = api.job(job_id)
        if job is None:
            return None, ('lost', 'server không còn job này')
        if job['status'] in TERMINAL_BAD or job['status'] == 'completed':
            return None, (job.get('error_type') or 'no_tempo', f'StemForge không đo được tempo bài gốc: {job.get("error") or job["status"]}')
        if time.time() > deadline:
            return None, ('stalled', f'StemForge chưa đo xong tempo sau {rm["stall_s"]}s')
        time.sleep(rm.get('poll_s', 3))


def switch_target(api: Api, job_id: str, target: float, rm: dict, should_stop) -> tuple | None:
    """Stop the job (StemForge stops at the next stage boundary and keeps the finished stages),
    then re-queue it at the song's own tempo; analysis and separation are reused."""
    api.cancel(job_id)                                  # refused when the job already finished: fine
    deadline = time.time() + rm['stall_s']
    while True:
        job = api.job(job_id)
        if job is None:
            return 'lost', 'server không còn job này'
        if job['status'] in TERMINAL_BAD or job['status'] == 'completed':
            break
        if should_stop():
            raise Interrupted()
        if time.time() > deadline:
            return 'stalled', f'job không dừng sau {rm["stall_s"]}s để đổi sang nhịp gốc'
        time.sleep(rm.get('poll_s', 3))
    api.retry(job_id, {'target_bpm': target})
    return None


def halt_job(api: Api, server, job_id: str, rm: dict, should_stop) -> tuple | None:
    """Stop a job that no longer moves, so it can be retried and the next song is not queued
    behind it. StemForge cancels at the next stage boundary and refuses to retry a job that is
    still running, so wait for a finished status. A job that does not stop in
    `remix.cancel_wait_s` is hung inside a stage: a server this skill started is restarted
    (StemForge then marks the job failed); a server it did not start is left alone."""
    finished = TERMINAL_BAD + ('completed',)
    try:
        api.cancel(job_id)                              # refused when the job already finished: fine
    except RcvError:
        pass
    deadline = time.time() + rm['cancel_wait_s']
    while time.time() < deadline:
        if should_stop():
            raise Interrupted()
        job = api.job(job_id)
        if job is None:
            return 'lost', 'server không còn job này'
        if job['status'] in finished:
            return None
        time.sleep(rm.get('poll_s', 3))
    if server is not None and server.owned:
        server.stop()
        server.ensure()
        job = api.job(job_id)
        if job is not None and job['status'] in finished:
            return None
    return 'stalled', (f'job không dừng sau {rm["cancel_wait_s"]}s kể từ khi huỷ'
                       + ('' if server is not None and server.owned else
                          '; server StemForge này không do skill khởi động nên skill không khởi động lại nó'))


def source_range_check(cfg: dict, tracks: list[dict], results: dict) -> dict | None:
    """One line naming the songs whose own tempo lies outside the preset's range: the voice is
    untouched, but the backing runs at a tempo the preset was not tuned for."""
    if not source_tempo_mode(cfg['remix']):
        return None
    rng = preset_bpm_range(cfg)
    if not rng:
        return check('source_tempo_range', 'SKIP', f'không đọc được khoảng tempo của preset {cfgmod.GENRE}')
    lo, hi = rng
    # Most songs lie outside a 16-BPM range, so the list is ordered: the songs furthest from
    # the range first (in octaves), those are the ones to listen to.
    def away(bpm: float) -> float:
        return math.log2(lo / bpm) if bpm < lo else math.log2(bpm / hi)
    outside = sorted(((away(results[t['id']]['bpm']), t['title'], results[t['id']]['bpm']) for t in tracks
                      if (results.get(t['id']) or {}).get('bpm') and not lo <= results[t['id']]['bpm'] <= hi), reverse=True)
    if not outside:
        return check('source_tempo_range', 'PASS', f'nhịp nền của mọi bài nằm trong khoảng {lo:g}–{hi:g} BPM của preset')
    return check('source_tempo_range', 'WARN',
                 f'{len(outside)}/{len(tracks)} bài có nhịp nền ngoài khoảng {lo:g}–{hi:g} BPM của preset {cfgmod.GENRE}; '
                 'xa khoảng đó nhất đứng trước, nên nghe các bài đầu danh sách: '
                 + ', '.join(f'{title} {bpm:g} ({"chậm" if bpm < lo else "nhanh"} hơn {100 * (2 ** d - 1):.0f}%)' for d, title, bpm in outside))


def verify_remix(track_dir: Path, track: dict, rm: dict) -> dict:
    """Measure a finished remix. Nothing is called PASS on the server's word alone."""
    wav = track_dir / 'final.wav'
    rep = read_json(track_dir / 'remix_report.json') or {}
    checks = []
    info = ffmpeg.probe(wav)
    audio = info['audio'] or {}
    ok_format = audio.get('sample_rate') == 48000 and audio.get('channels') == 2
    checks.append(check('format', 'PASS' if ok_format else 'FAIL',
                        f'{audio.get("codec")} {audio.get("sample_rate")} Hz, {audio.get("channels")} kênh'))
    exp = (rep.get('exports') or {}).get('wav') or {}
    if exp:
        same = abs(exp.get('duration', 0) - info['duration']) <= 0.05
        checks.append(check('export', 'PASS' if exp.get('ok') and same else 'FAIL',
                            f'report: ok={exp.get("ok")}, {exp.get("duration")}s; file: {info["duration"]:.3f}s'))
    else:
        checks.append(check('export', 'SKIP', 'remix_report.json không có mục exports.wav'))
    src_dur = (rep.get('source') or {}).get('duration')
    want = (track.get('source') or {}).get('duration')
    if src_dur and want:
        checks.append(check('source_matches', 'PASS' if abs(src_dur - want) <= 1.0 else 'FAIL',
                            f'StemForge đã phối file dài {src_dur:.1f}s, bài nguồn dài {want:.1f}s'))
    tempo = rep.get('tempo') or {}
    bpm = tempo.get('target_bpm')
    if isinstance(rm['target_bpm'], (int, float)) and bpm:
        checks.append(check('target_bpm', 'PASS' if abs(bpm - rm['target_bpm']) < 0.01 else 'FAIL',
                            f'{bpm} BPM (yêu cầu {rm["target_bpm"]})'))
    if source_tempo_mode(rm):
        r = tempo.get('tempo_ratio')
        kept = r is not None and abs(r - 1.0) <= 0.001
        checks.append(check('source_tempo', 'PASS' if kept else 'FAIL',
                            f'giữ tốc độ gốc: nhịp nền {bpm} BPM (bài gốc {tempo.get("source_bpm")} BPM, '
                            f'ánh xạ x{tempo.get("multiplier", 1):g})' if kept else
                            f'giọng bị co giãn {r}× dù đã chọn giữ tốc độ gốc (nhịp nền {bpm} BPM, bài gốc {tempo.get("source_bpm")} BPM)'))
    checks.append(backing_tempo_check(rep))
    bars = None
    if bpm and audio.get('samples'):
        bars = audio['samples'] / audio['sample_rate'] / (240.0 / bpm)
        whole = abs(bars - round(bars)) < 0.01
        # Only a beat-matched overlap needs whole bars. At its own tempo a song hands over
        # with a crossfade, so its length in bars changes nothing a listener hears.
        matters = not source_tempo_mode(rm)
        checks.append(check('whole_bars', 'PASS' if whole or not matters else 'WARN',
                            f'{bars:.3f} ô nhịp' + ('' if whole else ': độ dài không tròn ô nhịp, đoạn chồng có thể lệch' if matters
                                                    else ' (không tròn ô nhịp; không ảnh hưởng vì các bài nối bằng crossfade)')))
    ratio = tempo.get('tempo_ratio')
    if tempo and tempo.get('within_vocal_limit') is False:
        checks.append(check('vocal_stretch', 'WARN', f'giọng bị co giãn {ratio}x, vượt ngưỡng của preset'))
    elif ratio and max(ratio, 1 / ratio) > rm.get('warn_tempo_stretch', 1.25):
        checks.append(check('vocal_stretch', 'WARN', f'bài được {"kéo chậm" if ratio < 1 else "đẩy nhanh"} còn {ratio:.3f}× tempo gốc '
                                                     f'(nguồn {tempo.get("source_bpm")} BPM): nên nghe lại giọng hát'))
    master = rep.get('mastering') or {}
    if master and not (master.get('target_reached') and master.get('true_peak_ok')):
        checks.append(check('mastering', 'WARN', f'target_reached={master.get("target_reached")}, '
                                                 f'true_peak_ok={master.get("true_peak_ok")}'))
    if rep.get('warnings'):
        checks.append(check('stemforge_warnings', 'WARN', '; '.join(str(w) for w in rep['warnings'][:3])))
    after = master.get('after') or {}
    return {'checks': checks, 'bpm': bpm, 'key': rep.get('target_key'), 'duration': info['duration'],
            'samples': audio.get('samples'), 'sample_rate': audio.get('sample_rate'),
            'bars': round(bars, 3) if bars else None, 'lufs': after.get('integrated_lufs'),
            'true_peak_dbtp': after.get('true_peak_dbtp'),
            'processing_seconds': (rep.get('timings_s') or {}).get('total')}


def build_vocals(tdir: Path) -> dict:
    """Where the singing is, on the remix's own bar grid. StemForge's analysis has the vocal
    activity of every source bar; the remix keeps the bars of the body one to one between its
    DJ intro and DJ outro, so the activity can be laid onto the remix bar by bar. The mix stage
    uses it to keep only a few bars of lead-in before the first sung bar and after the last."""
    tdir = Path(tdir)
    rep = read_json(tdir / 'remix_report.json') or {}
    ana = read_json(tdir / 'analysis.json') or {}
    ver = read_json(tdir / 'verify.json') or {}
    secs = (rep.get('arrangement') or {}).get('sections') or []
    dj_in = secs[0].get('bars', 0) if secs and secs[0].get('source') == 'dj_intro' else 0
    dj_out = secs[-1].get('bars', 0) if secs and secs[-1].get('source') == 'dj_outro' else 0
    body = rep.get('body') or {}
    total = round(ver['bars']) if ver.get('bars') else None
    out = {'dj_intro_bars': dj_in if secs else None, 'dj_outro_bars': dj_out if secs else None, 'total_bars': total,
           'bar_activity': None, 'source': 'none'}
    vocals = ana.get('vocals') or {}
    act = vocals.get('bar_activity')
    if act and total and body.get('start_bar') is not None and body.get('end_bar') is not None:
        inner = [float(act[i]) if i < len(act) else 0.0 for i in range(body['start_bar'], body['end_bar'])]
        if dj_in + len(inner) + dj_out == total:                 # the bar count must add up, or the map is not trusted
            out.update(bar_activity=[round(x, 3) for x in [0.0] * dj_in + inner + [0.0] * dj_out], source='analysis',
                       has_vocals=bool(vocals.get('has_vocals', True)))
    write_json(tdir / 'vocals.json', out)
    return out


def ensure_vocals(tdir, job_id: str | None, api: 'Api | None' = None) -> None:
    """Make sure a remix has vocals.json. The analysis comes from the server when it is up,
    else from the job folder if StemForge still has it."""
    tdir = Path(tdir)
    if (tdir / 'vocals.json').is_file():
        return
    target = tdir / 'analysis.json'
    if not target.is_file() and job_id:
        if api is not None:
            try:
                api.download(job_id, 'analysis', target)
            except (RcvError, OSError):
                pass
        local = JOBS_DIR / job_id / 'analysis.json'
        if not target.is_file() and local.is_file():
            shutil.copyfile(local, target)
    build_vocals(tdir)


def remix_tracks(run_dir, cfg: dict, state, manifest: dict, should_stop=lambda: False) -> dict:
    """Remix every track of the manifest that is not verified yet. Returns per-track results;
    failed tracks are reported, not raised, so the good ones still get done."""
    run_dir = Path(run_dir)
    rm = cfg['remix']
    tracks = manifest['tracks']
    results, checks, own_jobs = {}, [], []
    todo = []
    for tr in tracks:
        tdir = run_dir / 'remix' / tr['slug']
        sha = tr['source'].get('sha256') or sha256_file(tr['source']['path'])
        tr['source']['sha256'] = sha
        key = job_key(sha, rm)
        rec = read_json(tdir / 'job.json') or {}
        done = rec.get('key') == key and rec.get('status') == 'verified' and (tdir / 'final.wav').is_file()
        missed = done and backing_tempo_check(read_json(tdir / 'remix_report.json') or {})['status'] == 'FAIL'
        if done and not missed:
            results[tr['id']] = read_json(tdir / 'verify.json')
            ensure_vocals(tdir, rec.get('job_id'))
        else:
            if missed:                                  # verified before the skill checked the backing's tempo
                rec = {**rec, 'tried_bpm': [*(rec.get('tried_bpm') or []), rec.get('target_bpm')]}
            todo.append((tr, tdir, key, rec if rec.get('key') == key else {}))
    if not todo:
        checks = [check('remix_jobs', 'PASS', 'mọi bài đã phối và kiểm xong từ trước')]
        rng = source_range_check(cfg, tracks, results)
        return {'results': results, 'failed': [], 'checks': checks + ([rng] if rng else [])}

    server = Server(cfg, run_dir, state)
    api = server.api
    failed = []
    done_before = len(tracks) - len(todo)
    live = {}                                           # the song in work: how to write its job.json
    try:
        checks += server.ensure()                       # inside the try: a server started here is stopped on any error

        def one(n, tr, tdir, key, rec):
            tdir.mkdir(parents=True, exist_ok=True)
            base = done_before + n

            def report(text, frac=0.0):
                state.progress('remix', done=base, total=len(tracks), text=f'{tr["title"]} ({text})',
                               percent=(base + frac) * 100.0 / len(tracks))

            # "source": the song's own tempo (doubled or halved). Unknown until StemForge has
            # measured it, so a new song starts at "auto" and is switched after the first stage.
            source_mode = source_tempo_mode(rm)
            target = rm['target_bpm']
            tried = [t for t in rec.get('tried_bpm') or [] if t]    # tempos whose backing missed ("source")
            if source_mode:
                known = known_source_bpm(tdir, tr)
                if known and other_octave(known, rm, tried) is None:
                    tried = []                          # every octave missed before: a retry starts over
                target = other_octave(known, rm, tried) if known else None
                if known and target is None:
                    failed.append({'id': tr['id'], 'rank': tr['rank'], 'title': tr['title'], 'error_type': 'source_tempo',
                                   'error': f'tempo bài gốc {known} BPM không ánh xạ được vào {API_BPM[0]:g}–{API_BPM[1]:g} BPM',
                                   'attempts': rec.get('attempts', 0)})
                    return
            attempts = rec.get('attempts', 0)
            job_id = rec.get('job_id')
            job_target = rec.get('target_bpm')          # the tempo the job was last told to use
            if rec.get('fresh') and job_id:
                # The human asked to retry a remix that finished but failed its checks. A retry of
                # that job would reuse every stage and return the same file: start a new job.
                if rm.get('cleanup_jobs') == 'delete_after_copy':
                    try:
                        api.delete(job_id)
                    except RcvError:
                        pass
                job_id = None
            job = api.job(job_id) if job_id else None
            if job is None:
                report('đang nạp file')
                up = api.upload(tr['source']['path'], Path(tr['source']['path']).name)
                job_target = target if target is not None else 'auto'
                created = api.create({'upload_id': up['upload_id'], 'genre': cfgmod.GENRE, 'target_bpm': job_target,
                                      'target_key': rm['target_key'], 'preserve_vocal': True, 'quality': rm['quality'],
                                      'output_format': 'wav'})
                job_id, attempts = created['job_id'], attempts + 1
            elif job['status'] in TERMINAL_BAD:
                switch = source_mode and target is not None and job_target != target
                api.retry(job_id, {'target_bpm': target} if switch else None)   # e.g. a server restart: resume from checkpoints
                job_target = target if switch else job_target
                attempts += 0 if rec.get('interrupted') else 1      # stopping the run is not a failed attempt
            elif source_mode and job['status'] == 'completed' and target is not None and job_target != target:
                api.retry(job_id, {'target_bpm': target})   # its backing missed: the other octave, stages reused
                job_target = target
            own_jobs.append(job_id)

            def remember(status='running', **extra):
                write_json(tdir / 'job.json', {'key': key, 'job_id': job_id, 'attempts': attempts, 'status': status,
                                               'target_bpm': job_target, **({'tried_bpm': tried} if tried else {}),
                                               **extra})
            remember()
            live['remember'] = remember

            error = None
            if source_mode and target is None:
                report('đo tempo bài gốc')
                bpm, error = measure_source_bpm(api, job_id, rm, should_stop)
                if bpm:
                    write_json(tdir / 'source_tempo.json', {'sha256': tr['source']['sha256'], 'bpm': bpm, 'job_id': job_id})
                    target = other_octave(bpm, rm, tried)
                    if target is None:
                        error = ('source_tempo', f'tempo bài gốc {bpm} BPM không ánh xạ được vào '
                                                 f'{API_BPM[0]:g}–{API_BPM[1]:g} BPM')
            if source_mode and not error and job_target != target:
                report(f'chuyển sang nhịp gốc {target:g} BPM')
                error = switch_target(api, job_id, target, rm, should_stop)
                if not error:
                    job_target = target
                    remember()
            if error:
                try:
                    api.cancel(job_id)                  # do not leave it running at "auto" in front of the next song
                except RcvError:
                    pass
                remember('failed', error_type=error[0], error=error[1])
                failed.append({'id': tr['id'], 'rank': tr['rank'], 'title': tr['title'], 'error_type': error[0],
                               'error': error[1][:300], 'attempts': attempts})
                return
            bad_checks = []
            while True:                                 # one pass per tempo the backing is generated at
                started = changed = time.time()
                last = None
                while True:
                    if should_stop():
                        raise Interrupted()
                    job = api.job(job_id)
                    if job is None:
                        error = ('lost', 'server không còn job này')
                        break
                    sig = (job['status'], job.get('stage'), round(job.get('progress') or 0.0, 3))
                    if sig != last:
                        last, changed = sig, time.time()
                    report(f'{STAGE_VI.get(job.get("stage"), job.get("stage"))}, {100 * (job.get("progress") or 0):.0f}%',
                           job.get('progress') or 0.0)
                    if job['status'] == 'completed':
                        break
                    bad = job['status'] in TERMINAL_BAD
                    stuck = time.time() - changed > rm['stall_s'] or time.time() - started > rm['job_timeout_s']
                    if bad or stuck:
                        reason = (job.get('error_type') or job['status'], job.get('error') or '') if bad else \
                            ('stalled', f'không tiến triển trong {int(time.time() - changed)}s')
                        if stuck and not bad:
                            report('job đứng, đang huỷ')
                            halted = halt_job(api, server, job_id, rm, should_stop)
                            if halted:
                                error = halted
                                break
                            if (api.job(job_id) or {}).get('status') == 'completed':
                                continue                # it finished while the cancel was on its way
                        if attempts >= rm['max_attempts']:
                            error = reason
                            break
                        api.retry(job_id)
                        attempts += 1
                        started = changed = time.time()
                        last = None
                        remember()
                    time.sleep(rm.get('poll_s', 3))
                if error:
                    break
                report('chép kết quả', 0.99)
                api.download(job_id, 'report', tdir / 'remix_report.json')
                api.download(job_id, 'wav', tdir / 'final.wav')
                verdict = verify_remix(tdir, tr, rm)
                verdict['job_id'] = job_id
                write_json(tdir / 'verify.json', verdict)
                (tdir / 'vocals.json').unlink(missing_ok=True)
                ensure_vocals(tdir, job_id, api)
                bad_checks = [c for c in verdict['checks'] if c['status'] == 'FAIL']
                if not (source_mode and bad_checks and all(c['name'] == 'backing_tempo' for c in bad_checks)):
                    break
                # The backing missed this tempo. The song's own tempo at the other octave keeps the
                # voice untouched too; StemForge reuses the analysis and the separation.
                tried.append(job_target)
                src_bpm = ((read_json(tdir / 'remix_report.json') or {}).get('tempo') or {}).get('source_bpm')
                alt = other_octave(src_bpm, rm, tried)
                if alt is None:
                    break
                report(f'nhạc nền lệch nhịp ở {job_target:g} BPM, thử {alt:g} BPM')
                api.retry(job_id, {'target_bpm': alt})
                job_target = alt
                remember()

            if error:
                remember('failed', error_type=error[0], error=error[1])
                failed.append({'id': tr['id'], 'rank': tr['rank'], 'title': tr['title'], 'error_type': error[0],
                               'error': error[1][:300], 'attempts': attempts})
                return
            if bad_checks:
                note = f' (đã thử nhịp nền {", ".join(f"{t:g}" for t in tried)} BPM)' if tried else ''
                remember('failed', error_type='verify', error=bad_checks[0]['detail'] + note)
                failed.append({'id': tr['id'], 'rank': tr['rank'], 'title': tr['title'], 'error_type': 'verify',
                               'error': '; '.join(f'{c["name"]}: {c["detail"]}' for c in bad_checks) + note,
                               'attempts': attempts})
                return
            remember('verified')
            results[tr['id']] = verdict
            if rm.get('cleanup_jobs') == 'delete_after_copy':
                try:
                    api.delete(job_id)                  # only a job this run created, only after its copy checked out
                except RcvError:
                    pass                                # the copy is verified; a job left behind is not a failed song

        for n, (tr, tdir, key, rec) in enumerate(todo):
            live.clear()
            if should_stop():
                raise Interrupted()
            try:
                one(n, tr, tdir, key, rec)
                live.clear()
            except RcvError as exc:
                # One song's upload, download or measurement failed. With the server still up the
                # other songs go on and this one joins the failed remixes; a dead server ends the stage.
                if not api.health():
                    raise
                if 'remember' in live:
                    live['remember']('failed', error_type='api', error=str(exc))
                failed.append({'id': tr['id'], 'rank': tr['rank'], 'title': tr['title'], 'error_type': 'api',
                               'error': str(exc)[:300], 'attempts': (read_json(tdir / 'job.json') or rec).get('attempts', 0)})
        state.progress('remix', done=len(tracks) - len(failed), total=len(tracks), text='xong các bài', percent=100, force=True)
    except Interrupted:
        if 'remember' in live:
            live['remember'](interrupted=True)          # the job comes back failed; resuming it is not an attempt
        raise
    finally:
        server.stop()
    rng = source_range_check(cfg, tracks, results)
    return {'results': results, 'failed': failed, 'checks': checks + ([rng] if rng else []), 'jobs': own_jobs}
