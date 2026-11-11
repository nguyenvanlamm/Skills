"""StemForge Auto Remix over its HTTP API: start and stop the server, one job per song.

The server is started with STEMFORGE_REMIX_RETENTION_DAYS=0. Left at its default (7), the
server deletes every finished job older than a week, an hour after it starts and hourly after
that, which would remove job folders this skill never created.
"""
from __future__ import annotations

import http.client
import json
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


class Interrupted(Exception):
    pass


class Api:
    def __init__(self, host: str, port: int):
        self.host, self.port = host, int(port)

    def _request(self, method: str, path: str, body=None, timeout: float = 30):
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
            status, payload = self._request('GET', '/api/health', timeout=5)
            return status == 200 and isinstance(payload, dict) and payload.get('status') == 'ok'
        except (OSError, ValueError):
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

    def retry(self, job_id: str) -> dict:
        return self._ok('POST', f'/api/auto-remix/{job_id}/retry', {})

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
            cmdline = Path(f'/proc/{rec["pid"]}/cmdline').read_bytes().decode(errors='replace')
        except (OSError, KeyError):
            return None
        return rec if 'run.py' in cmdline else None

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
    return digest({'sha': source_sha, 'genre': cfgmod.GENRE, 'bpm': rm['target_bpm'], 'key': rm['target_key'],
                   'quality': rm['quality'], 'separator': rm.get('separator')})


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
    bars = None
    if bpm and audio.get('samples'):
        bars = audio['samples'] / audio['sample_rate'] / (240.0 / bpm)
        whole = abs(bars - round(bars)) < 0.01
        checks.append(check('whole_bars', 'PASS' if whole else 'WARN',
                            f'{bars:.3f} ô nhịp' + ('' if whole else ': độ dài không tròn ô nhịp, đoạn chồng có thể lệch')))
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
        if rec.get('key') == key and rec.get('status') == 'verified' and (tdir / 'final.wav').is_file():
            results[tr['id']] = read_json(tdir / 'verify.json')
            ensure_vocals(tdir, rec.get('job_id'))
        else:
            todo.append((tr, tdir, key, rec if rec.get('key') == key else {}))
    if not todo:
        return {'results': results, 'failed': [], 'checks': [check('remix_jobs', 'PASS', 'mọi bài đã phối và kiểm xong từ trước')]}

    server = Server(cfg, run_dir, state)
    checks += server.ensure()
    api = server.api
    failed = []
    done_before = len(tracks) - len(todo)
    try:
        for n, (tr, tdir, key, rec) in enumerate(todo):
            tdir.mkdir(parents=True, exist_ok=True)
            base = done_before + n

            def report(text, frac=0.0):
                state.progress('remix', done=base, total=len(tracks), text=f'{tr["title"]} ({text})',
                               percent=(base + frac) * 100.0 / len(tracks))

            attempts = rec.get('attempts', 0)
            job_id = rec.get('job_id')
            job = api.job(job_id) if job_id else None
            if job is None:
                report('đang nạp file')
                up = api.upload(tr['source']['path'], Path(tr['source']['path']).name)
                created = api.create({'upload_id': up['upload_id'], 'genre': cfgmod.GENRE, 'target_bpm': rm['target_bpm'],
                                      'target_key': rm['target_key'], 'preserve_vocal': True, 'quality': rm['quality'],
                                      'output_format': 'wav'})
                job_id, attempts = created['job_id'], attempts + 1
            elif job['status'] in TERMINAL_BAD:
                api.retry(job_id)                       # e.g. interrupted by a server restart: resume from checkpoints
                attempts += 1
            own_jobs.append(job_id)
            write_json(tdir / 'job.json', {'key': key, 'job_id': job_id, 'attempts': attempts, 'status': 'running'})

            error = None
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
                        api.cancel(job_id)
                        time.sleep(3)
                    if attempts >= rm['max_attempts']:
                        error = reason
                        break
                    api.retry(job_id)
                    attempts += 1
                    started = changed = time.time()
                    last = None
                    write_json(tdir / 'job.json', {'key': key, 'job_id': job_id, 'attempts': attempts, 'status': 'running'})
                time.sleep(rm.get('poll_s', 3))

            if error:
                write_json(tdir / 'job.json', {'key': key, 'job_id': job_id, 'attempts': attempts, 'status': 'failed',
                                               'error_type': error[0], 'error': error[1]})
                failed.append({'id': tr['id'], 'rank': tr['rank'], 'title': tr['title'], 'error_type': error[0],
                               'error': error[1][:300], 'attempts': attempts})
                continue
            report('chép kết quả', 0.99)
            api.download(job_id, 'report', tdir / 'remix_report.json')
            api.download(job_id, 'wav', tdir / 'final.wav')
            verdict = verify_remix(tdir, tr, rm)
            verdict['job_id'] = job_id
            write_json(tdir / 'verify.json', verdict)
            (tdir / 'vocals.json').unlink(missing_ok=True)
            ensure_vocals(tdir, job_id, api)
            bad_checks = [c for c in verdict['checks'] if c['status'] == 'FAIL']
            if bad_checks:
                write_json(tdir / 'job.json', {'key': key, 'job_id': job_id, 'attempts': attempts, 'status': 'failed',
                                               'error_type': 'verify', 'error': bad_checks[0]['detail']})
                failed.append({'id': tr['id'], 'rank': tr['rank'], 'title': tr['title'], 'error_type': 'verify',
                               'error': '; '.join(f'{c["name"]}: {c["detail"]}' for c in bad_checks), 'attempts': attempts})
                continue
            write_json(tdir / 'job.json', {'key': key, 'job_id': job_id, 'attempts': attempts, 'status': 'verified'})
            results[tr['id']] = verdict
            if rm.get('cleanup_jobs') == 'delete_after_copy':
                api.delete(job_id)                      # only a job this run created, only after its copy checked out
        state.progress('remix', done=len(tracks) - len(failed), total=len(tracks), text='xong các bài', percent=100, force=True)
    finally:
        server.stop()
    return {'results': results, 'failed': failed, 'checks': checks, 'jobs': own_jobs}
