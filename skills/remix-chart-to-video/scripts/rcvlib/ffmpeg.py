"""ffmpeg / ffprobe helpers: probing, loudness, silence, beat alignment, frames, test tones."""
from __future__ import annotations

import array
import json
import re
import subprocess
from pathlib import Path

from .common import RcvError, run


def probe(path) -> dict:
    rc, out, err = run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', path],
                       timeout=120)
    if rc != 0:
        raise RcvError(f'ffprobe không đọc được {path}: {err.strip()[:200]}')
    data = json.loads(out)
    fmt = data.get('format', {})
    info = {'format': fmt.get('format_name'), 'duration': float(fmt.get('duration') or 0),
            'size': int(fmt.get('size') or 0), 'audio': None, 'video': None,
            'tags': {str(k).lower(): str(v).strip() for k, v in (fmt.get('tags') or {}).items()}}   # ID3, RIFF INFO, Vorbis
    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'audio':
            for key, value in (stream.get('tags') or {}).items():
                info['tags'].setdefault(str(key).lower(), str(value).strip())
        kind = stream.get('codec_type')
        if kind == 'audio' and info['audio'] is None:
            rate = int(stream.get('sample_rate') or 0)
            samples = None
            if stream.get('duration_ts') and stream.get('time_base') and rate:
                num, den = (int(x) for x in stream['time_base'].split('/'))
                samples = round(int(stream['duration_ts']) * num * rate / den)
            info['audio'] = {'codec': stream.get('codec_name'), 'sample_rate': rate,
                             'channels': int(stream.get('channels') or 0), 'samples': samples,
                             'duration': float(stream.get('duration') or info['duration'])}
        elif kind == 'video' and info['video'] is None and stream.get('disposition', {}).get('attached_pic') != 1:
            num, _, den = (stream.get('r_frame_rate') or '0/1').partition('/')
            info['video'] = {'codec': stream.get('codec_name'), 'width': int(stream.get('width') or 0),
                             'height': int(stream.get('height') or 0),
                             'fps': float(num) / float(den or 1) if float(den or 1) else 0.0,
                             'duration': float(stream.get('duration') or info['duration']),
                             'pix_fmt': stream.get('pix_fmt')}
    return info


def loudness(path, start: float | None = None, duration: float | None = None) -> dict:
    """Integrated loudness (LUFS), loudness range and true peak (dBTP) by EBU R128."""
    cmd = ['ffmpeg', '-hide_banner', '-nostats']
    if start is not None:
        cmd += ['-ss', f'{start:.3f}']
    if duration is not None:
        cmd += ['-t', f'{duration:.3f}']
    cmd += ['-i', path, '-map', '0:a:0', '-af', 'ebur128=peak=true:framelog=verbose', '-f', 'null', '-']
    rc, _, err = run(cmd, timeout=7200)
    summary = err.split('Summary:')[-1] if 'Summary:' in err else ''
    lufs = re.search(r'\bI:\s+(-?\d+(?:\.\d+)?) LUFS', summary)
    lra = re.search(r'\bLRA:\s+(-?\d+(?:\.\d+)?) LU', summary)
    peak = re.search(r'\bPeak:\s+(-?\d+(?:\.\d+)?|-inf) dBFS', summary)
    if rc != 0 or not lufs or not peak:
        raise RcvError(f'Không đo được loudness của {path}: {err.strip()[-300:]}')
    return {'integrated_lufs': float(lufs.group(1)), 'lra_lu': float(lra.group(1)) if lra else None,
            'true_peak_dbtp': float('-inf') if peak.group(1) == '-inf' else float(peak.group(1))}


def silences(path, noise_db: float = -50, min_s: float = 1.5) -> list[tuple[float, float]]:
    cmd = ['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-map', '0:a:0',
           '-af', f'silencedetect=noise={noise_db}dB:d={min_s}', '-f', 'null', '-']
    rc, _, err = run(cmd, timeout=7200)
    if rc != 0:
        raise RcvError(f'silencedetect lỗi trên {path}: {err.strip()[-300:]}')
    starts = [float(x) for x in re.findall(r'silence_start:\s*(-?\d+(?:\.\d+)?)', err)]
    ends = [float(x) for x in re.findall(r'silence_end:\s*(-?\d+(?:\.\d+)?)', err)]
    return [(s, ends[i] if i < len(ends) else float('inf')) for i, s in enumerate(starts)]


# -- beat alignment ------------------------------------------------------------------------

ENV_RATE = 1000          # envelope samples per second: 1 ms resolution


def onset_envelope(path, start: float, duration: float, lowpass_hz: int = 180) -> list[float]:
    """Low-band onset strength. Kicks carry the beat in a vinahouse intro/outro, so the rises of
    the low band mark the beats."""
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', f'{max(0.0, start):.6f}', '-t', f'{duration:.6f}',
           '-i', str(path), '-map', '0:a:0', '-ac', '1', '-af', f'lowpass=f={lowpass_hz},aresample={ENV_RATE}',
           '-f', 's16le', '-']
    done = subprocess.run(cmd, capture_output=True)
    if done.returncode != 0:
        raise RcvError(f'ffmpeg không giải mã được {path}: {done.stderr.decode(errors="replace")[-200:]}')
    pcm = array.array('h')
    pcm.frombytes(done.stdout[:len(done.stdout) // 2 * 2])
    win = 8                                                  # 8 ms smoothing
    level, acc, out = [], 0, []
    for i, v in enumerate(pcm):
        acc += abs(v)
        if i >= win:
            acc -= abs(pcm[i - win])
        level.append(acc / win)
    for i in range(len(level)):
        rise = level[i] - level[i - win] if i >= win else 0.0
        out.append(rise if rise > 0 else 0.0)
    return out


def beat_lag(env_a: list[float], env_b: list[float], max_lag_ms: int) -> dict:
    """How late the beats of B are against the beats of A, in ms (negative = B early), with the
    normalized correlation at that lag (0..1) and at lag 0."""
    n = min(len(env_a), len(env_b))
    a, b = env_a[:n], env_b[:n]
    norm = (sum(x * x for x in a) * sum(x * x for x in b)) ** 0.5
    if n == 0 or norm == 0:
        return {'lag_ms': 0.0, 'correlation': 0.0, 'correlation_at_zero': 0.0}
    floor = max(a) * 0.08
    peaks = [(i, v) for i, v in enumerate(a) if v > floor]        # sparse: only A's onsets matter
    best_lag, best = 0, -1.0
    zero = 0.0
    for lag in range(-max_lag_ms, max_lag_ms + 1):
        total = 0.0
        for i, v in peaks:
            j = i + lag                                          # B late by `lag` => B[i + lag] ~ A[i]
            if 0 <= j < n:
                total += v * b[j]
        if lag == 0:
            zero = total
        if total > best:
            best, best_lag = total, lag
    return {'lag_ms': best_lag * 1000.0 / ENV_RATE, 'correlation': round(best / norm, 4),
            'correlation_at_zero': round(zero / norm, 4)}


# -- pictures ------------------------------------------------------------------------------

def extract_frame(video, at_s: float, out_png) -> Path:
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    rc, _, err = run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{at_s:.3f}', '-i', video,
                      '-frames:v', '1', out_png], timeout=300)
    if rc != 0 or not out_png.is_file():
        raise RcvError(f'Không trích được khung hình ở {at_s:.1f}s của {video}: {err.strip()[-200:]}')
    return out_png


def image_size(path) -> tuple[int, int]:
    info = probe(path)
    if not info['video']:
        raise RcvError(f'{path} không phải ảnh đọc được')
    return info['video']['width'], info['video']['height']


def ssim(image_a, image_b, size: str = '1280:720', crop: str | None = None) -> float:
    """Structural similarity of two pictures after scaling both to `size` (1.0 = identical).
    `crop` (an ffmpeg crop expression such as "iw*0.28:ih:iw*0.72:0") limits it to one region."""
    pre = f'crop={crop},' if crop else ''
    graph = (f'[0:v]{pre}scale={size}:flags=bicubic,format=gray[a];[1:v]{pre}scale={size}:flags=bicubic,format=gray[b];'
             '[a][b]ssim')
    rc, _, err = run(['ffmpeg', '-hide_banner', '-nostats', '-i', image_a, '-i', image_b, '-lavfi', graph,
                      '-frames:v', '1', '-f', 'null', '-'], timeout=300)
    m = re.search(r'All:(\d+(?:\.\d+)?)', err)
    if rc != 0 or not m:
        raise RcvError(f'Không đo được SSIM: {err.strip()[-200:]}')
    return float(m.group(1))


def luma_diff(image_a, image_b, crop: str) -> float:
    """Mean absolute luma difference (0..255) of two pictures inside `crop`, after averaging both
    down to 12x54 cells. Something drawn on top of one of them (spectrum bars over text) raises it
    sharply; the fringes that video coding leaves around saturated letters average out (at
    1080p: 23 at 96x432, 8 at 12x54, while bars over the text stay at 36-72)."""
    same = 'scale=12:54:flags=area,format=gray'         # also brings two pictures of different sizes to one
    graph = (f'[0:v]crop={crop},{same}[a];[1:v]crop={crop},{same}[b];[a][b]blend=all_mode=difference,'
             'signalstats,metadata=print:file=-')
    rc, out, err = run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', image_a, '-i', image_b, '-lavfi', graph,
                        '-frames:v', '1', '-f', 'null', '-'], timeout=300)
    m = re.search(r'YAVG=([\d.]+)', out)
    if rc != 0 or not m:
        raise RcvError(f'Không đo được độ lệch ảnh: {err.strip()[-200:]}')
    return float(m.group(1))


# -- test material -------------------------------------------------------------------------

def synth_track(out, bpm: float, bars: int, offset_ms: float = 0.0, tone_hz: float = 220.0,
                rate: int = 48000) -> Path:
    """A click track for tests: one kick per beat (late by `offset_ms`), plus a quiet tone so
    two tracks sound different. Whole bars long, 24-bit stereo."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    beat = 60.0 / bpm
    dur = bars * 4 * beat
    off = offset_ms / 1000.0
    expr = (f'0.7*sin(2*PI*55*mod(t-{off:.6f}+{beat:.9f}\\,{beat:.9f}))*exp(-28*mod(t-{off:.6f}+{beat:.9f}\\,{beat:.9f}))'
            f'+0.08*sin(2*PI*{tone_hz}*t)')
    rc, _, err = run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi',
                      '-i', f"aevalsrc=exprs='{expr}|{expr}':s={rate}:d={dur:.9f}",
                      '-c:a', 'pcm_s24le', out], timeout=300)
    if rc != 0:
        raise RcvError(f'Không tạo được track thử: {err.strip()[-300:]}')
    return out
