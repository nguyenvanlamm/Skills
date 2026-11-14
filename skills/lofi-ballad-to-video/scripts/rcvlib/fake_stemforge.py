"""A stand-in for StemForge's Auto Remix API, for the offline tests only (no GPU, no models).

It answers the same routes the skill calls. A job "runs" for a moment and then returns a
synthetic remix: a click track at the requested tempo, whole bars long. The uploaded file name
steers the outcome: "fail" always fails, "flaky" fails once and succeeds on retry, "late<N>"
shifts the beats N ms late, "nokick" returns a remix with no beat to measure, "bpm<N>" makes the
source tempo N BPM (default 100), "miss<N>" makes the generated backing miss any tempo above N BPM
(StemForge keeps its best attempt and reports bpm_ok false), "stuck" stops moving in its first
run and runs normally after a retry, "hung" stops moving and never reacts to a cancel. Like
StemForge, the analysis is readable once the first stage is done, a cancel is refused for a
finished job and takes effect only a moment later (`cancel_seconds`, StemForge's "next stage
boundary"), a retry is refused while the job is still running, and a retry may change the
job's options.
"""
from __future__ import annotations

import json
import math
import re
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import ffmpeg
from .common import run


def source_bpm(name: str) -> float:
    m = re.search(r'bpm(\d+)', name.lower())
    return float(m.group(1)) if m else 100.0


def plan_tempo(src: float, target) -> tuple[float, float, float]:
    """(target, multiplier, ratio) the way StemForge's tempo_sync.plan_tempo picks them."""
    cands = []
    for i, m in enumerate((1.0, 2.0, 0.5)):
        t = min(max(src * m, 124.0), 140.0) if target in (None, 'auto') else float(target)
        cands.append((abs(math.log(t / (src * m))), i, t, m))
    _, _, t, m = min(cands)
    return t, m, t / (src * m)


class FakeStemForge:
    def __init__(self, job_seconds: float = 0.4, bars: int = 24, cancel_seconds: float = 0.6):
        self.job_seconds, self.bars, self.cancel_seconds = job_seconds, bars, cancel_seconds
        self.dir = Path(tempfile.mkdtemp(prefix='fake_stemforge_'))
        self.uploads: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.deleted: list[str] = []
        self.created = 0
        self.create_targets: list = []                          # target_bpm of every created job, in order
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, payload, ctype='application/json'):
                body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(code)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                path, _, query = self.path.partition('?')
                if path == '/api/health':
                    return self._send(200, {'status': 'ok'})
                if path == '/api/auto-remix/status':
                    return self._send(200, {'ready': True, 'missing': [], 'gpu': {'cuda': False, 'error': 'fake server'}})
                m = re.fullmatch(r'/api/auto-remix/([0-9a-f]+)(/download|/analysis)?', path)
                if not m or m.group(1) not in fake.jobs:
                    return self._send(404, {'detail': 'not found'})
                job = fake.tick(m.group(1))
                if m.group(2) == '/analysis':
                    analysed = job['status'] == 'completed' or job.get('_analysed')
                    if not analysed:
                        return self._send(404, {'detail': 'Analysis not available yet'})
                    return self._send(200, {'bpm': source_bpm(job['_upload']['name']), 'duration': job['_upload']['duration']})
                if not m.group(2):
                    return self._send(200, {k: v for k, v in job.items() if not k.startswith('_')})
                if job['status'] != 'completed':
                    return self._send(409, {'detail': 'not ready'})
                fmt = dict(p.split('=') for p in query.split('&') if '=' in p).get('format', 'mp3')
                if fmt == 'wav':
                    return self._send(200, Path(job['_wav']).read_bytes(), 'audio/wav')
                return self._send(200, job['_analysis'] if fmt == 'analysis' else job['_report'])

            def do_POST(self):
                length = int(self.headers.get('Content-Length') or 0)
                body = self.rfile.read(length)
                if self.path == '/api/auto-remix/upload':
                    name = re.search(rb'filename="([^"]*)"', body)
                    start = body.find(b'\r\n\r\n') + 4
                    end = body.rfind(b'\r\n--')
                    upload_id = uuid.uuid4().hex[:16]
                    filename = name.group(1).decode() if name else 'audio.wav'
                    path = fake.dir / f'{upload_id}{Path(filename).suffix or ".wav"}'
                    path.write_bytes(body[start:end])
                    info = ffmpeg.probe(path)
                    fake.uploads[upload_id] = {'path': path, 'name': filename, 'duration': info['duration']}
                    return self._send(200, {'upload_id': upload_id, 'original_filename': filename, 'duration': info['duration']})
                if self.path == '/api/auto-remix':
                    req = json.loads(body or b'{}')
                    up = fake.uploads.get(req.get('upload_id'))
                    if not up:
                        return self._send(404, {'detail': 'Upload not found'})
                    job_id = uuid.uuid4().hex[:12]
                    fake.created += 1
                    fake.create_targets.append(req.get('target_bpm'))
                    fake.jobs[job_id] = {'job_id': job_id, 'status': 'queued', 'stage': 'queued', 'progress': 0.0,
                                         'error': None, 'error_type': None, 'runs': 1, 'preset_id': req.get('genre'),
                                         'options': req, '_upload': up, '_started': time.time()}
                    return self._send(200, {'job_id': job_id, 'status': 'queued'})
                m = re.fullmatch(r'/api/auto-remix/([0-9a-f]+)/(retry|cancel)', self.path)
                if not m or m.group(1) not in fake.jobs:
                    return self._send(404, {'detail': 'not found'})
                job = fake.tick(m.group(1))
                if m.group(2) == 'cancel':
                    if job['status'] in ('completed', 'failed', 'cancelled'):
                        return self._send(409, {'detail': f'Job is already {job["status"]}.'})
                    if job['status'] == 'queued':
                        job.update(status='cancelled', stage='cancelled')
                    else:                                       # a running job stops at its next stage boundary
                        job.setdefault('_cancel_at', time.time() + fake.cancel_seconds)
                else:
                    if job['status'] not in ('completed', 'failed', 'cancelled'):
                        return self._send(409, {'detail': f'Job is {job["status"]}; only finished jobs can be retried.'})
                    job['options'].update(json.loads(body or b'{}'))
                    job.pop('_cancel_at', None)
                    job.update(status='queued', stage='queued', progress=0.0, error=None, error_type=None,
                               runs=job['runs'] + 1, _started=time.time())
                return self._send(200, {k: v for k, v in job.items() if not k.startswith('_')})

            def do_DELETE(self):
                m = re.fullmatch(r'/api/auto-remix/([0-9a-f]+)', self.path)
                if not m or m.group(1) not in fake.jobs:
                    return self._send(404, {'detail': 'not found'})
                fake.deleted.append(m.group(1))
                del fake.jobs[m.group(1)]
                return self._send(200, {'deleted': True})

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tick(self, job_id: str) -> dict:
        job = self.jobs[job_id]
        if job['status'] in ('completed', 'failed', 'cancelled'):
            return job
        frac = min(1.0, (time.time() - job['_started']) / self.job_seconds)
        name = job['_upload']['name'].lower()
        if frac >= 0.2:
            job['_analysed'] = True                             # the first stage is done
        if 'hung' in name or ('stuck' in name and job['runs'] == 1):
            if '_cancel_at' in job and time.time() >= job['_cancel_at'] and 'hung' not in name:
                job.update(status='cancelled', stage='cancelled')
            else:
                job.update(status='generating', stage='generating', progress=min(frac, 0.5))
            return job
        if '_cancel_at' in job and time.time() >= job['_cancel_at']:
            job.update(status='cancelled', stage='cancelled')
            return job
        if 'fail' in name or ('flaky' in name and job['runs'] == 1):
            if frac >= 0.5:
                job.update(status='failed', stage='generating', error='fake failure', error_type='acestep_crashed')
            else:
                job.update(status='separating', stage='separating', progress=frac)
            return job
        if frac < 1.0:
            job.update(status='generating', stage='generating', progress=frac)
            return job
        src = source_bpm(name)
        bpm, mult, ratio = plan_tempo(src, job['options'].get('target_bpm'))
        late = re.search(r'late(\d+)', name)
        miss = re.search(r'miss(\d+)', name)
        missed = bool(miss) and bpm > float(miss.group(1))
        wav = self.dir / f'{job_id}.wav'
        if 'nokick' in name:
            dur = self.bars * 240.0 / bpm
            run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi',
                 '-i', f'sine=frequency=330:sample_rate=48000:duration={dur:.9f}', '-af', 'volume=0.3',
                 '-ac', '2', '-c:a', 'pcm_s24le', str(wav)])
        else:
            ffmpeg.synth_track(wav, bpm, self.bars, offset_ms=float(late.group(1)) if late else 0.0,
                               tone_hz=200 + 40 * (self.created % 7))
        info = ffmpeg.probe(wav)
        job['_wav'] = str(wav)
        body = self.bars - 16                                   # 8-bar DJ intro, the body, 8-bar DJ outro
        sung = [0.0, 0.0] + [1.0] * max(0, body - 4) + [0.0, 0.0] if 'nokick' not in name else [0.0] * body
        job['_analysis'] = {'bpm': src, 'vocals': {'has_vocals': 'nokick' not in name, 'bar_activity': [0.0] * 4 + sung[:body]}}
        job['_report'] = {
            'arrangement': {'sections': [{'type': 'intro', 'bars': 8, 'source': 'dj_intro'},
                                         {'type': 'verse', 'bars': body, 'source': 'body'},
                                         {'type': 'outro', 'bars': 8, 'source': 'dj_outro'}]},
            'body': {'start_bar': 4, 'end_bar': 4 + body},
            'source': {'duration': job['_upload']['duration'], 'bpm': src},
            'tempo': {'source_bpm': src, 'target_bpm': bpm, 'multiplier': mult, 'tempo_ratio': round(ratio, 6),
                      'within_vocal_limit': 1 / 1.45 <= ratio <= 1.45},
            'generation': {'chosen': {'strategy': 'cover', 'seed': 128, 'validation': {
                'measured_bpm': round(bpm * 0.75, 2) if missed else bpm, 'bpm_ok': not missed,
                'problems': [f'measured {bpm * 0.75:.1f} BPM, requested {bpm:.1f}'] if missed else []},
                'alignment': {'ok': not missed, 'lag_spread_ms': 470.2 if missed else 11.6}}},
            'target_key': 'A minor',
            'warnings': ['No generation attempt passed every check; the best attempt was used'] if missed else [],
            'mastering': {'target_reached': True, 'true_peak_ok': True,
                          'after': {'integrated_lufs': -14.0, 'true_peak_dbtp': -1.2}},
            'exports': {'wav': {'ok': True, 'duration': info['duration'], 'problems': []}},
            'timings_s': {'total': self.job_seconds},
        }
        job.update(status='completed', stage='completed', progress=1.0)
        return job

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
