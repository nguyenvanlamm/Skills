"""Join the remixes into one long mix and work out the chapter times from the result.

StemForge writes every remix as an 8-bar DJ intro, the song, and an 8-bar DJ outro, and the
song itself often has several instrumental bars before the first sung line and after the last.
Played back to back that is half a minute without a voice at every handover. So the join is cut
around the singing: of each song only `mix.lead_in_bars` bars before its first sung bar and
`mix.tail_bars` bars after its last are kept, and the handover overlaps `mix.overlap_bars` bars.
The wait between two voices is then lead_in + tail − overlap bars.

Nothing here is taken on trust: all cuts are on whole bars of songs that share one tempo, the
beat offset of every overlap is measured and corrected, an overlap that cannot be shown to line
up falls back to a short crossfade, and the joined file is measured for length, loudness, true
peak and silence. Chapter times come from the sample positions of the joined file.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import ffmpeg
from .common import RcvError, check, fmt_ts, read_json, round_half_up, write_json
from .cover import playlist_tracks

RATE = 48000


def load_entries(run_dir: Path, manifest: dict) -> list[dict]:
    from .stemforge import ensure_vocals
    entries = []
    for pos, tr in enumerate(playlist_tracks(manifest), 1):
        tdir = run_dir / 'remix' / tr['slug']
        ver = read_json(tdir / 'verify.json')
        wav = tdir / 'final.wav'
        if not ver or not wav.is_file():
            raise RcvError(f'Thiếu bản phối của "{tr["title"]}" ({tdir}).')
        if ver.get('sample_rate') != RATE or not ver.get('samples'):
            raise RcvError(f'Bản phối {wav} không phải 48 kHz hoặc không đọc được số mẫu.')
        ensure_vocals(tdir, (read_json(tdir / 'job.json') or {}).get('job_id'))
        bpm = ver.get('bpm')
        entries.append({'position': pos, 'track': tr['id'], 'title': tr['title'], 'label': tr['label'],
                        'path': str(wav), 'samples': int(ver['samples']), 'bpm': bpm, 'key': ver.get('key'),
                        'bar_samples': 240.0 / bpm * RATE if bpm else None, 'vocals': read_json(tdir / 'vocals.json') or {},
                        'head': 0, 'end': int(ver['samples']), 'basis': 'none'})
    return entries


def sung_bars(entry: dict, mx: dict) -> dict | None:
    """First sung bar and the bar after the last sung one, on the remix's bar grid. Without
    vocal data the DJ intro and outro stand in for "before the singing" and "after it"."""
    if not entry.get('bar_samples'):
        return None
    voc = entry['vocals']
    total = voc.get('total_bars') or round(entry['samples'] / entry['bar_samples'])
    act = voc.get('bar_activity')
    strong = [i for i, a in enumerate(act or []) if a >= mx['vocal_activity_min']]
    if strong:
        return {'first': strong[0], 'last_end': strong[-1] + 1, 'total': total, 'basis': 'vocals'}
    dj_in = voc.get('dj_intro_bars') if voc.get('dj_intro_bars') is not None else mx['dj_bars']
    dj_out = voc.get('dj_outro_bars') if voc.get('dj_outro_bars') is not None else mx['dj_bars']
    if dj_in + dj_out >= total:
        return None
    return {'first': dj_in, 'last_end': total - dj_out, 'total': total, 'basis': 'dj_sections'}


def apply_trims(entries: list[dict], mx: dict) -> None:
    """Set the part of each song that goes into the mix: `head`..`end`, in samples, on bars."""
    if mx.get('lead_in_bars') is None and mx.get('tail_bars') is None:
        return
    for i, e in enumerate(entries):
        b = sung_bars(e, mx)
        if not b:
            continue
        e['basis'] = b['basis']
        e['first_sung'] = round(b['first'] * e['bar_samples'])
        e['last_sung_end'] = round(b['last_end'] * e['bar_samples'])
        if mx.get('lead_in_bars') is not None:
            e['head'] = round(max(0, b['first'] - mx['lead_in_bars']) * e['bar_samples'])
        if mx.get('tail_bars') is not None and i < len(entries) - 1:        # the last song keeps its own ending
            e['end'] = min(e['samples'], round(min(b['total'], b['last_end'] + mx['tail_bars']) * e['bar_samples']))


def plan_transition(a: dict, b: dict, mx: dict) -> dict:
    """Decide how song A hands over to song B, and measure it."""
    fallback = round(mx['crossfade_s'] * RATE)
    limit = min(a['end'] - a['head'], b['end'] - b['head']) // 2
    out = {'from': a['position'], 'to': b['position'], 'curve': mx['curve']}
    if mx['transition'] == 'cut':
        return dict(out, mode='cut', ns=0, status='PASS', detail='nối thẳng')
    if mx['transition'] == 'crossfade':
        return dict(out, mode='crossfade', ns=min(fallback, limit), status='PASS', detail=f'crossfade {mx["crossfade_s"]}s')

    def fall(reason: str) -> dict:
        return dict(out, mode='crossfade', ns=min(fallback, limit), status='WARN',
                    detail=f'{reason}; dùng crossfade {mx["crossfade_s"]}s thay cho đoạn chồng')

    if not a['bpm'] or not b['bpm'] or abs(a['bpm'] - b['bpm']) > 0.01:
        return fall(f'hai bài khác tempo ({a["bpm"]} và {b["bpm"]} BPM)')
    bars = mx['overlap_bars']
    if a['basis'] != 'none' and b['basis'] != 'none':        # never fade a voice: stay inside the kept lead-in and tail
        bars = min(bars, *(x for x in (mx.get('lead_in_bars'), mx.get('tail_bars')) if x is not None))
    beat_s = 60.0 / a['bpm']
    ns = round(bars * 4 * beat_s * RATE)
    if ns <= 0 or ns >= limit:
        return fall('bài quá ngắn so với đoạn chồng')
    window = int(beat_s * 1000 / 4)                           # search a quarter beat either side

    def measure(n: int) -> dict:
        ea = ffmpeg.onset_envelope(a['path'], (a['end'] - n) / RATE, n / RATE)
        eb = ffmpeg.onset_envelope(b['path'], b['head'] / RATE, n / RATE)
        return ffmpeg.beat_lag(ea, eb, window)

    first = measure(ns)
    out.update(overlap_bars=bars, measured_lag_ms=first['lag_ms'], correlation=first['correlation'])
    if first['correlation'] < mx['min_beat_correlation']:
        return fall(f'không đo được nhịp ở đoạn chồng (tương quan {first["correlation"]:.2f})')
    if abs(first['lag_ms']) >= window:
        return fall(f'nhịp lệch quá {window} ms')
    nudge = round(first['lag_ms'] * RATE / 1000)              # B late => start B earlier => longer overlap
    residual = first
    if abs(first['lag_ms']) > 1:
        ns += nudge
        residual = measure(ns)
        if abs(residual['lag_ms']) > 3 or residual['correlation'] < mx['min_beat_correlation']:
            return fall(f'dời {first["lag_ms"]:.0f} ms vẫn còn lệch {residual["lag_ms"]:.0f} ms')
    big = abs(first['lag_ms']) > mx['max_beat_offset_ms']
    detail = (f'chồng {bars} ô nhịp ({ns / RATE:.2f}s), lệch nhịp đo được {first["lag_ms"]:+.0f} ms'
              + (f', đã dời cho khớp (còn {residual["lag_ms"]:+.0f} ms)' if abs(first['lag_ms']) > 1 else '')
              + f', tương quan {residual["correlation"]:.2f}')
    return dict(out, mode='overlap', ns=ns, nudge_ms=round(first['lag_ms'], 1) if abs(first['lag_ms']) > 1 else 0.0,
                residual_lag_ms=residual['lag_ms'], status='WARN' if big else 'PASS',
                detail=detail + (f' — lệch ban đầu vượt {mx["max_beat_offset_ms"]} ms, nên nghe lại' if big else ''))


def layout(entries: list[dict], transitions: list[dict]) -> dict:
    """Sample position of every song's kept part in the mix, and the chapter marks (whole
    seconds). A chapter starts in the middle of the overlap, where the incoming song takes over."""
    starts, marks = [0], [0]
    for i, tr in enumerate(transitions):
        start = starts[i] + (entries[i]['end'] - entries[i]['head']) - tr['ns']
        starts.append(start)
        marks.append(round_half_up((start + tr['ns'] / 2) / RATE))
    total = starts[-1] + entries[-1]['end'] - entries[-1]['head']
    return {'starts': starts, 'marks': marks, 'total_samples': total, 'total_seconds': round_half_up(total / RATE)}


def waits(entries: list[dict], lay: dict) -> dict:
    """Seconds without a voice: from the start of the mix to the first sung bar, and from the
    last sung bar of each song to the first sung bar of the next. None where it is not known."""
    def sung_at(i, key):
        e = entries[i]
        return lay['starts'][i] + e[key] - e['head'] if e['basis'] == 'vocals' else None

    first = sung_at(0, 'first_sung')
    gaps = []
    for i in range(len(entries) - 1):
        a, b = sung_at(i, 'last_sung_end'), sung_at(i + 1, 'first_sung')
        gaps.append(round((b - a) / RATE, 1) if a is not None and b is not None else None)
    return {'start_s': round(first / RATE, 1) if first is not None else None, 'gaps_s': gaps}


def _ffmpeg(cmd: list[str], ctx, on_time=None) -> tuple[int, str]:
    proc = subprocess.Popen(cmd + ['-progress', 'pipe:1', '-nostats'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    if ctx is not None:
        ctx.children.append(proc)
    try:
        for line in proc.stdout:
            if on_time and line.startswith('out_time_us='):
                try:
                    on_time(int(line.split('=', 1)[1]) / 1e6)
                except ValueError:
                    pass
        err = proc.stderr.read()
        proc.wait()
    finally:
        if ctx is not None and proc in ctx.children:
            ctx.children.remove(proc)
    return proc.returncode, err


def render(entries: list[dict], transitions: list[dict], out: Path, ctx=None, on_time=None, gain_db: float = 0.0,
           start_fade_s: float = 0.0) -> None:
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']
    for e in entries:
        cmd += ['-i', e['path']]
    graph = []
    for i, e in enumerate(entries):
        chain = f'[{i}:a]'
        if e['head'] > 0 or e['end'] < e['samples']:
            chain += f'atrim=start_sample={e["head"]}:end_sample={e["end"]},asetpts=PTS-STARTPTS,'
        chain += f'aformat=sample_fmts=fltp:sample_rates={RATE}:channel_layouts=stereo'
        if i == 0 and e['head'] > 0 and start_fade_s > 0:
            chain += f',afade=t=in:st=0:d={start_fade_s:.3f}'
        graph.append(chain + f'[a{i}]')
    last = 'a0'
    for i, tr in enumerate(transitions, 1):
        if tr['ns'] > 0:
            graph.append(f'[{last}][a{i}]acrossfade=ns={tr["ns"]}:c1={tr["curve"]}:c2={tr["curve"]}[x{i}]')
        else:
            graph.append(f'[{last}][a{i}]concat=n=2:v=0:a=1[x{i}]')
        last = f'x{i}'
    if gain_db:
        graph.append(f'[{last}]volume={gain_db:.2f}dB[g]')
        last = 'g'
    cmd += ['-filter_complex', ';'.join(graph), '-map', f'[{last}]', '-c:a', 'pcm_s24le', '-ar', str(RATE), str(out)]
    rc, err = _ffmpeg(cmd, ctx, on_time)
    if rc != 0:
        raise RcvError(f'ffmpeg ghép mix lỗi (mã {rc}): {err.strip()[-400:]}')


def transitions_preview(mix_wav: Path, lay: dict, transitions: list[dict], out: Path, pad_s: float) -> list[dict]:
    """One short file with every handover, so the human can listen to the joins quickly."""
    if not transitions:
        return []
    total = lay['total_samples'] / RATE
    graph = [f'[0:a]asplit={len(transitions)}' + ''.join(f'[s{i}]' for i in range(len(transitions)))]
    index, offset = [], 0.0
    for i, tr in enumerate(transitions):
        a = max(0.0, lay['starts'][i + 1] / RATE - pad_s)
        b = min(total, (lay['starts'][i + 1] + tr['ns']) / RATE + pad_s)
        dur = b - a
        graph.append(f'[s{i}]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,'
                     f'afade=t=in:d=0.25,afade=t=out:st={max(0.0, dur - 0.25):.3f}:d=0.25[c{i}]')
        index.append({'from': tr['from'], 'to': tr['to'], 'at_in_preview': fmt_ts(offset), 'at_in_mix': fmt_ts(a)})
        offset += dur
    graph.append(''.join(f'[c{i}]' for i in range(len(transitions))) + f'concat=n={len(transitions)}:v=0:a=1[out]')
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mix_wav), '-filter_complex', ';'.join(graph),
           '-map', '[out]', '-c:a', 'libmp3lame', '-b:a', '192k', str(out)]
    rc, err = _ffmpeg(cmd, None)
    if rc != 0:
        raise RcvError(f'Không tạo được file nghe thử đoạn chuyển: {err.strip()[-300:]}')
    return index


def build(run_dir, cfg: dict, state, manifest: dict, ctx=None):
    run_dir = Path(run_dir)
    mx = cfg['mix']
    out_dir = run_dir / 'mix'
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = load_entries(run_dir, manifest)
    apply_trims(entries, mx)
    checks = []

    def progress(text, percent=None):
        if state is not None:
            state.progress('mix', text=text, percent=percent)

    transitions = []
    for i in range(len(entries) - 1):
        progress(f'đo đoạn chuyển {i + 1}/{len(entries) - 1}', 30.0 * i / max(1, len(entries) - 1))
        transitions.append(plan_transition(entries[i], entries[i + 1], mx))
    lay = layout(entries, transitions)
    wait = waits(entries, lay)
    for tr, gap in zip(transitions, wait['gaps_s']):
        tr['voice_gap_s'] = gap
        if gap is not None:
            tr['detail'] += f'; không lời giữa hai bài {gap:.1f}s'
        checks.append(check(f'transition_{tr["from"]}_{tr["to"]}', tr['status'], tr['detail']))
    trimmed = mx.get('lead_in_bars') is not None or mx.get('tail_bars') is not None
    if trimmed:
        if wait['start_s'] is not None:
            checks.append(check('start_wait', 'PASS', f'từ đầu bản mix tới câu hát đầu tiên {wait["start_s"]:.1f}s '
                                                      f'(giữ {mx.get("lead_in_bars")} ô nhịp dạo)'))
        blind = [e['title'] for e in entries if e['basis'] != 'vocals']
        if blind:
            checks.append(check('vocal_data', 'WARN', 'không có dữ liệu giọng hát, cắt theo đoạn DJ đầu và cuối bài: ' + ', '.join(sorted(set(blind)))))
    gaps = [b - a for a, b in zip(lay['marks'], lay['marks'][1:] + [lay['total_seconds']])]
    if min(gaps) <= 0:
        raise RcvError(f'Mốc chapter không tăng dần: {lay["marks"]}')
    write_json(out_dir / 'mix_plan.json', {'entries': [{k: v for k, v in e.items() if k != 'vocals'} for e in entries],
                                           'transitions': transitions, 'layout': lay, 'waits': wait})

    partial = out_dir / 'mix.partial.wav'
    total_s = lay['total_samples'] / RATE
    fade = mx.get('start_fade_s') or 0.0
    render(entries, transitions, partial, ctx, lambda t: progress('đang ghép', 30 + 50 * min(1.0, t / total_s)), start_fade_s=fade)
    if ctx is not None and ctx.should_stop():
        partial.unlink(missing_ok=True)
        from .stemforge import Interrupted
        raise Interrupted()

    progress('đo loudness', 82)
    loud = ffmpeg.loudness(partial)
    gain = 0.0
    if loud['true_peak_dbtp'] > mx['true_peak_max_dbtp']:
        gain = mx['true_peak_max_dbtp'] - loud['true_peak_dbtp'] - 0.1      # one global trim, then measure again
        render(entries, transitions, partial, ctx, None, gain_db=gain, start_fade_s=fade)
        loud = ffmpeg.loudness(partial)
    info = ffmpeg.probe(partial)
    got = info['audio']['samples']
    checks.append(check('mix_length', 'PASS' if got is not None and abs(got - lay['total_samples']) <= 0.02 * RATE else 'FAIL',
                        f'{got} mẫu, dự tính {lay["total_samples"]} ({total_s:.3f}s)'))
    off = abs(loud['integrated_lufs'] - mx['target_lufs'])
    checks.append(check('loudness', 'PASS' if off <= mx['lufs_tolerance'] else 'WARN',
                        f'{loud["integrated_lufs"]:.1f} LUFS (đích {mx["target_lufs"]} ± {mx["lufs_tolerance"]})'))
    checks.append(check('true_peak', 'PASS' if loud['true_peak_dbtp'] <= mx['true_peak_max_dbtp'] else 'FAIL',
                        f'{loud["true_peak_dbtp"]:.2f} dBTP (tối đa {mx["true_peak_max_dbtp"]})'
                        + (f', đã giảm gain {gain:.2f} dB' if gain else '')))
    progress('tìm khoảng lặng', 90)
    quiet = [(a, b) for a, b in ffmpeg.silences(partial, mx['silence_db'], mx['silence_min_s']) if a < total_s - 2.0]
    checks.append(check('silence', 'WARN' if quiet else 'PASS',
                        'khoảng lặng ở ' + ', '.join(f'{fmt_ts(a)}–{fmt_ts(min(b, total_s))}' for a, b in quiet[:5]) if quiet
                        else f'không có khoảng lặng dài hơn {mx["silence_min_s"]}s'))
    if [g for g in gaps if g < 10]:
        checks.append(check('chapter_gaps', 'WARN', f'có chapter ngắn hơn 10 giây: {gaps}'))

    final = out_dir / 'mix.wav'
    os.replace(partial, final)
    top = run_dir / 'mix.wav'
    top.unlink(missing_ok=True)
    try:
        os.link(final, top)                                    # same data, no second gigabyte
    except OSError:
        shutil.copyfile(final, top)
    progress('tạo file nghe thử đoạn chuyển', 95)
    preview = run_dir / 'transitions_preview.mp3'
    index = transitions_preview(final, lay, transitions, preview, mx['preview_pad_s'])

    chapters = [{'position': e['position'], 'track': e['track'], 'seconds': m, 'stamp': fmt_ts(m), 'label': e['label'],
                 'title': e['title']} for e, m in zip(entries, lay['marks'])]
    report = {'tracks': [dict(position=e['position'], track=e['track'], title=e['title'], bpm=e['bpm'], key=e['key'],
                              start_samples=s, start_seconds=round(s / RATE, 3), samples=e['end'] - e['head'],
                              cut_from_start_s=round(e['head'] / RATE, 2), cut_from_end_s=round((e['samples'] - e['end']) / RATE, 2),
                              trim_basis=e['basis'])
                         for e, s in zip(entries, lay['starts'])],
              'transitions': transitions, 'chapters': chapters, 'waits': wait, 'total_samples': lay['total_samples'],
              'total_seconds': lay['total_seconds'], 'duration': round(total_s, 3), 'loudness': loud, 'gain_db': gain,
              'preview': {'file': str(preview) if index else None, 'index': index}, 'checks': checks}
    write_json(out_dir / 'mix_report.json', report)
    by_id = {t['id']: t for t in manifest['tracks']}
    for e in entries:
        by_id[e['track']].update(bpm=e['bpm'], key=e['key'])
    for item, ch in zip(manifest['playlist'], chapters):
        item.update(chapter=ch['stamp'], chapter_seconds=ch['seconds'])
    manifest['mix'] = {'total_seconds': lay['total_seconds'], 'duration': round(total_s, 3),
                       'integrated_lufs': loud['integrated_lufs'], 'true_peak_dbtp': loud['true_peak_dbtp']}
    write_json(run_dir / 'manifest.json', manifest)
    return checks, {'mix': str(top), 'duration': round(total_s, 3), 'chapters': [c['stamp'] for c in chapters], 'waits': wait}
