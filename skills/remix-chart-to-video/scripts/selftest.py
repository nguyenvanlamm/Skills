#!/usr/bin/env python3
"""Offline tests for the remix-chart-to-video scripts. No GPU, no network, no NCT request.

  selftest.py [--only NAME[,NAME]] [--root DIR] [--keep]

Tests: help, selection, ask_flow, art_review, mix, trim, cover, video, metadata, resume, pane.
`cover` and `video` call the real m10-mixcover (--dry-run) and m10-visualizer on a few seconds
of synthetic audio; they are SKIP when the repos are not found (pass --root DIR, the folder
that holds the four repos). StemForge is replaced by a fake server. Prints JSON.
Exit 0 when nothing failed, 1 otherwise, 2 usage.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ['RCV_FORBID_NCT'] = '1'

from rcvlib import config as cfgmod  # noqa: E402
from rcvlib import cover, ffmpeg, mix, nct, preflight, video, youtube  # noqa: E402
from rcvlib.common import read_json, round_half_up, worst, write_json  # noqa: E402
from rcvlib.fake_stemforge import FakeStemForge  # noqa: E402
from rcvlib.state import State  # noqa: E402

RATE = 48000
LIMITS = {'title_max_chars': {'value': 100, 'unit': 'characters', 'verified': True},
          'description_max_chars': {'value': 5000, 'unit': 'characters', 'verified': True},
          'description_max_bytes': {'value': 5000, 'unit': 'bytes', 'verified': True},
          'thumbnail_min_width': {'value': 640, 'unit': 'pixels', 'verified': True},
          'tags_max_chars': {'value': 500, 'unit': 'characters', 'verified': True},
          'hashtags_max_count': {'value': 60, 'unit': 'hashtags', 'verified': True},
          'chapters_min_count': {'value': 3, 'unit': 'timestamps', 'verified': True},
          'chapter_min_seconds': {'value': 10, 'unit': 'seconds', 'verified': True},
          'thumbnail_max_bytes': {'value': 2097152, 'unit': 'bytes', 'verified': True}}


class Skip(Exception):
    pass


def expect(cond, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def status_of(checks, name):
    return next((c['status'] for c in checks if c['name'] == name), None)


def pipeline(*args, env=None, timeout=600):
    done = subprocess.run([sys.executable, str(HERE / 'pipeline.py'), *map(str, args)], capture_output=True, text=True,
                          env=env or os.environ, timeout=timeout)
    try:
        payload = json.loads(done.stdout)
    except ValueError:
        payload = {'raw': done.stdout[-400:], 'stderr': done.stderr[-600:]}
    return done.returncode, payload


class Lab:
    """A temporary workspace: config, fake StemForge, synthetic sources, a chart fixture."""

    def __init__(self, tmp: Path, root: Path | None):
        self.tmp, self.root = tmp, root
        self.fake = FakeStemForge(job_seconds=0.3)
        self.src = tmp / 'sources_pool'
        self.src.mkdir(parents=True)
        self.n = 0

    def source(self, name: str, bars: int = 8) -> Path:
        return ffmpeg.synth_track(self.src / name, 100, bars)

    def config(self, name: str = 'ws', **over) -> dict:
        repos = {k: str(self.root / v) if self.root else '/nonexistent' for k, v in cfgmod.REPOS.items()}
        base = {'repos': repos, 'nct': {'live_access': False},
                'selection': {'count': 3, 'min_duration_s': 5},
                'remix': {'cleanup_jobs': 'keep', 'port': self.fake.port, 'poll_s': 0.2, 'stall_s': 20, 'job_timeout_s': 60},
                'cover': {'confirmed': True, 'dry_run': True, 'review': False},
                'video': {'look': 'cover', 'fps': 10, 'size': '640x360'}}
        cfg = cfgmod.deep_merge(cfgmod.deep_merge(cfgmod.DEFAULTS, base), over)
        path = self.tmp / name / 'config.json'
        cfg['_path'], cfg['_workspace'] = str(path), str(path.parent)
        cfgmod.save(cfg)
        return cfg

    def report(self, plan: dict) -> dict:
        """The chart fixture with originals set per rank: plan[rank] = ('file', path) | decision | None."""
        rep = copy.deepcopy(read_json(HERE / 'testdata' / 'nct_report.json'))
        for song in rep['songs']:
            rank = song['position']
            what = plan.get(rank)
            if what is None:
                song['original'] = None
                continue
            orig = {'base_title': nct.base_title(song['title']), 'title': nct.base_title(song['title']), 'artist': song['artist'],
                    'nct_url': f'https://example.invalid/song/orig{rank}', 'manual_search_url': f'https://example.invalid/search?{rank}',
                    'status': None, 'local_file_path': None}
            if isinstance(what, tuple):
                kind, value = what
                orig.update(decision='matched', status='downloaded', local_file_path=str(value) if kind == 'file' else None)
                if kind == 'same_as':
                    orig.update(local_file_path=str(value[1]), nct_url=f'https://example.invalid/song/orig{value[0]}')
                if kind == 'no_download':
                    orig.update(status='manual_action_required')
            else:
                orig['decision'] = what
            song['original'] = orig
        return rep

    def run_dir(self, cfg: dict, rep: dict, count: int, name: str, sequence=None) -> Path:
        run = Path(cfg['_workspace']) / name
        (run / 'nct').mkdir(parents=True)
        write_json(run / 'nct' / 'report.json', rep)
        State.create(run, {'name': name, 'dir': str(run), 'title': f'Test {name}', 'chart_date': rep['run']['chart_date'],
                           'count': count, 'sequence': sequence, 'nct_run_id': rep['run']['id'],
                           'chart_source': 'fixture', 'config_path': cfg['_path']})
        return run

    def close(self) -> None:
        self.fake.close()
        shutil.rmtree(self.fake.dir, ignore_errors=True)


# -- tests -----------------------------------------------------------------------------------

def t_help(lab: Lab):
    for script in ('pipeline.py', 'preflight.py', 'render_video.py', 'youtube_meta.py', 'steps_pane.py', 'selftest.py'):
        done = subprocess.run([sys.executable, str(HERE / script), '--help'], capture_output=True, text=True)
        expect(done.returncode == 0 and len(done.stdout) > 80, f'{script} --help: exit {done.returncode}')
    return 'mọi script có --help'


def t_selection(lab: Lab):
    a, b, c = lab.source('a.wav'), lab.source('b.wav'), lab.source('c.wav')
    short = lab.source('short.wav', bars=1)                       # 2.4 s
    plan = {1: ('file', a), 2: ('file', b), 3: ('file', lab.tmp / 'gone.wav'), 4: 'uncertain', 5: 'not_found',
            6: ('no_download', None), 7: ('file', short), 8: ('same_as', (1, a)), 9: None, 10: ('file', c)}
    rep = lab.report(plan)
    cfg = lab.config('sel')
    srcdir = lab.tmp / 'sel' / 'manual'
    cands = {x['rank']: x for x in nct.classify(rep, cfg, srcdir)}
    want = {1: None, 2: None, 3: 'file_missing', 4: 'uncertain', 5: 'not_found', 6: 'not_downloaded', 7: 'too_short',
            8: 'duplicate', 9: 'not_searched', 10: None}
    for rank, reason in want.items():
        expect(cands[rank]['reason'] == reason and cands[rank]['usable'] == (reason is None),
               f'hạng {rank}: muốn {reason}, được {cands[rank]["reason"]}')
    sel = nct.select(list(cands.values()), 3, 3)
    expect(sel['short_by'] == 1 and [m['rank'] for m in sel['missing']] == [3], f'thiếu bài sai: {sel["short_by"]}')
    text = nct.missing_message(sel, srcdir, live=False)
    expect('03_' in text and 'backfill' in text and 'skip' in text and 'manual' in text, 'lời hỏi thiếu tên file hoặc lựa chọn')
    wide = nct.select(list(cands.values()), 3, 10)
    expect([x['rank'] for x in wide['selected']] == [1, 2, 10] and not wide['exact_top'], 'lấy bù sai')
    srcdir.mkdir(parents=True)
    shutil.copyfile(c, srcdir / '03_bai_tu_dat.wav')              # the human supplies rank 3
    again = {x['rank']: x for x in nct.classify(rep, cfg, srcdir)}
    expect(again[3]['usable'] and again[3]['source']['kind'] == 'manual', 'không nhận file tự đặt cho hạng 3')
    top = nct.select(list(again.values()), 3, 3)
    expect(top['exact_top'] and top['short_by'] == 0, 'đủ hạng 1–3 phải là exact_top')
    rej = {x['rank']: x for x in nct.classify(rep, cfg, srcdir, {'2': 'remix_failed'})}
    expect(rej[2]['reason'] == 'remix_failed' and not rej[2]['usable'], 'bài bị loại vẫn được chọn')
    man = nct.build_manifest(rep, top, cfg, [1, 2, 1])
    expect([p['track'] for p in man['playlist']] == [1, 2, 1] and not man['exact_top'], 'sequence không vào playlist')
    expect(nct.distributor('Phát hành: 2026-04-29; Nhà phân phối: BELIEVE MUSIC') == 'BELIEVE MUSIC', 'không tách được nhà phân phối')
    return 'đủ 8 lý do loại bài, file tự đặt, lấy bù, loại bài, sequence'


def t_ask_flow(lab: Lab):
    if not lab.root:
        raise Skip('cần --root để chạy preflight thật')
    a, b, c = lab.source('f1.wav'), lab.source('f2.wav'), lab.source('f3.wav')
    rep = lab.report({1: ('file', a), 2: ('file', b), 3: 'uncertain', 4: ('file', c)})
    cfg = lab.config('ask')
    run = lab.run_dir(cfg, rep, 3, 'ask-run')
    code, out = pipeline('run', '--run', run, '--until', 'originals')
    expect(code == 10 and 'hạng 3' in out.get('waiting', ''), f'phải dừng hỏi (exit 10), được {code}: {out}')
    st = State.load(run)
    expect(st.stage('originals')['status'] == 'waiting' and st.data['waiting'], 'state không ghi "Chờ bạn"')
    expect(not (run / 'manifest.json').exists(), 'đã tự quyết khi chưa hỏi')
    pipeline('decide', '--run', run, '--missing', 'backfill')
    code, out = pipeline('run', '--run', run, '--until', 'originals')
    expect(code == 0, f'lấy bù offline với hạng 4 có sẵn file phải qua: {code} {out}')
    man = read_json(run / 'manifest.json')
    expect([t['rank'] for t in man['tracks']] == [1, 2, 4] and not man['exact_top'], 'lấy bù phải ra hạng 1, 2, 4')
    run2 = lab.run_dir(cfg, rep, 3, 'ask-run-skip')
    pipeline('run', '--run', run2, '--until', 'originals')
    pipeline('decide', '--run', run2, '--missing', 'skip')
    code, out = pipeline('run', '--run', run2, '--until', 'originals')
    expect(code == 0 and len(read_json(run2 / 'manifest.json')['tracks']) == 2, 'skip phải cho mix 2 bài')
    run3 = lab.run_dir(cfg, rep, 3, 'ask-run-manual')
    pipeline('run', '--run', run3, '--until', 'originals')
    pipeline('decide', '--run', run3, '--missing', 'manual')
    code, out = pipeline('run', '--run', run3, '--until', 'originals')
    expect(code == 10, 'manual khi chưa có file phải hỏi lại')
    shutil.copyfile(c, run3 / 'sources' / '03_tu_dat.wav')
    pipeline('decide', '--run', run3, '--missing', 'manual')
    code, out = pipeline('run', '--run', run3, '--until', 'originals')
    expect(code == 0 and read_json(run3 / 'manifest.json')['exact_top'], 'manual có file phải ra đúng hạng 1–3')
    return 'dừng hỏi (exit 10), backfill, skip, manual'


def t_art_review(lab: Lab):
    """After the picture stage the run stops until the human has looked: ok, redo, an own
    picture, or other text. Nothing after it runs before that."""
    if not lab.root:
        raise Skip('cần repo m10-mixcover (--root)')
    a, b = lab.source('ar1.wav'), lab.source('ar2.wav')
    cfg = lab.config('artws', cover={'review': True})
    run = lab.run_dir(cfg, lab.report({1: ('file', a), 2: ('file', b)}), 2, 'art-run')

    def go():
        return pipeline('run', '--run', run, '--until', 'remix')

    made = lab.fake.created
    code, out = go()
    st = State.load(run)
    expect(code == 10 and out.get('stage') == 'art' and st.stage('art')['status'] == 'waiting', f'phải dừng ở S3 chờ duyệt ảnh: {code} {out}')
    expect('provisional_cover.png' in out['waiting'] and '--art ok' in out['waiting'] and out['waiting'].splitlines()[0].startswith('Xem ảnh bìa'),
           f'lời hỏi thiếu đường dẫn ảnh hoặc lựa chọn: {out["waiting"][:200]}')
    expect((run / 'art' / 'provisional_cover.png').is_file() and lab.fake.created == made, 'chưa duyệt ảnh mà đã sang chặng phối')
    code, out = go()
    expect(code == 10, 'chạy lại khi chưa trả lời vẫn phải dừng')
    pipeline('decide', '--run', run, '--art', 'redo')
    code, out = go()
    expect(code == 10 and State.load(run).data['decisions'].get('art_seed_offset') == 1, 'redo phải tạo ảnh khác rồi hỏi lại')
    pic = lab.tmp / 'own.png'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=0x334455:s=1792x1008',
                    '-frames:v', '1', str(pic)], check=True)
    cfg['cover']['dry_run'] = False                          # an own picture is drawn on, not replaced by the gradient
    cfgmod.save(cfg)
    pipeline('decide', '--run', run, '--art', 'image', '--path', pic)
    code, out = go()
    art = read_json(run / 'art' / 'art.json')
    expect(code == 10 and art['mode'] == 'image' and (run / 'art' / 'raw.png').is_file(), f'ảnh của người dùng phải được dùng rồi hỏi lại: {code} {art}')
    pipeline('decide', '--run', run, '--art', 'ok')
    code, out = go()
    ran = [r['stage'] for r in out.get('ran', [])]
    expect(code == 0 and 'art' in ran and 'remix' in ran and lab.fake.created == made + 2, f'duyệt xong phải chạy tiếp sang phối: {code} {ran}')
    expect(status_of(State.load(run).stage('art')['checks'], 'art_review') == 'PASS', 'thiếu phép kiểm art_review')
    cfg['cover']['subtitle'] = 'Chữ mới'
    cfgmod.save(cfg)
    code, out = pipeline('run', '--run', run, '--until', 'mix')
    expect(code == 10 and out.get('stage') == 'art' and 'Chữ mới' in out['waiting'], 'đổi chữ trên ảnh phải cho xem lại')
    return 'dừng ở S3; redo, ảnh của người dùng, ok; đổi chữ thì cho xem lại; chưa duyệt thì không phối'


def fake_remix(run: Path, slug: str, bpm: float, bars: int = 24, late: float = 0.0, kick: bool = True) -> dict:
    tdir = run / 'remix' / slug
    wav = tdir / 'final.wav'
    if kick:
        ffmpeg.synth_track(wav, bpm, bars, offset_ms=late, tone_hz=180 + 37 * len(slug))
    else:
        tdir.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i',
                        f'sine=frequency=300:sample_rate={RATE}:duration={bars * 240.0 / bpm:.9f}', '-af', 'volume=0.3',
                        '-ac', '2', '-c:a', 'pcm_s24le', str(wav)], check=True)
    info = ffmpeg.probe(wav)
    write_json(tdir / 'verify.json', {'bpm': bpm, 'key': 'A minor', 'samples': info['audio']['samples'], 'sample_rate': RATE,
                                      'duration': info['duration'], 'checks': []})
    return info


KEEP_ALL = {'lead_in_bars': None, 'tail_bars': None, 'overlap_bars': 8}      # whole songs, 8-bar overlaps


def mix_run(lab: Lab, name: str = 'mix-run', mix_over: dict | None = None):
    cfg = lab.config('mixws', mix=KEEP_ALL if mix_over is None else mix_over)
    run = Path(cfg['_workspace']) / name
    spec = [('r01_a', 128, 0.0, True), ('r02_b', 128, 12.0, True), ('r03_c', 128, 0.0, True),
            ('r04_tone', 128, 0.0, False), ('r05_fast', 140, 0.0, True)]
    tracks = []
    for i, (slug, bpm, late, kick) in enumerate(spec, 1):
        fake_remix(run, slug, bpm, late=late, kick=kick)
        tracks.append({'id': i, 'rank': i, 'title': f'Bài {i}', 'artist': f'Ca sĩ {i}', 'label': f'Ca sĩ {i} - Bài {i}',
                       'slug': slug, 'chart_title': f'Bài {i} (Remix)', 'chart_artist': f'Ca sĩ {i}', 'distributor': 'Test',
                       'source': {'path': 'x', 'duration': 30.0}})
    manifest = {'version': 1, 'chart': {'title': 'Top 50 Nhạc Remix Việt', 'date': '2026-11-09'}, 'exact_top': True,
                'tracks': tracks, 'playlist': [{'position': i, 'track': i} for i in range(1, 6)]}
    write_json(run / 'manifest.json', manifest)
    return cfg, run, manifest


def t_mix(lab: Lab):
    cfg, run, manifest = mix_run(lab)
    checks, out = mix.build(run, cfg, None, manifest)
    rep = read_json(run / 'mix' / 'mix_report.json')
    tr = rep['transitions']
    expect(tr[0]['mode'] == 'overlap' and abs(tr[0]['nudge_ms'] - 12) <= 1.5, f'1→2 phải chồng và dời ≈ +12 ms: {tr[0]}')
    expect(tr[1]['mode'] == 'overlap' and abs(tr[1]['nudge_ms'] + 12) <= 1.5, f'2→3 phải dời ≈ −12 ms: {tr[1]}')
    expect(abs(tr[0]['ns'] - (720000 + 576)) <= 72, f'đoạn chồng 1→2 sai số mẫu: {tr[0]["ns"]}')
    expect(tr[2]['mode'] == 'crossfade' and tr[2]['status'] == 'WARN' and 'không đo được nhịp' in tr[2]['detail'], f'3→4: {tr[2]}')
    expect(tr[3]['mode'] == 'crossfade' and 'khác tempo' in tr[3]['detail'], f'4→5: {tr[3]}')
    lens = [t['samples'] for t in rep['tracks']]
    starts, marks = [0], [0]
    for i, t in enumerate(tr):
        starts.append(starts[i] + lens[i] - t['ns'])
        marks.append(round_half_up((starts[-1] + t['ns'] / 2) / RATE))
    total = starts[-1] + lens[-1]
    expect([c['seconds'] for c in rep['chapters']] == marks, f'mốc chapter sai: {[c["seconds"] for c in rep["chapters"]]} != {marks}')
    got = ffmpeg.probe(run / 'mix.wav')['audio']['samples']
    expect(got == total == rep['total_samples'], f'độ dài mix {got} != dự tính {total}')
    expect(status_of(checks, 'mix_length') == 'PASS' and status_of(checks, 'true_peak') == 'PASS', f'{checks}')
    expect(rep['loudness']['true_peak_dbtp'] <= cfg['mix']['true_peak_max_dbtp'], 'true peak vượt ngưỡng')
    expect((run / 'transitions_preview.mp3').is_file() and len(rep['preview']['index']) == 4, 'thiếu file nghe thử đoạn chuyển')
    man = read_json(run / 'manifest.json')
    expect(man['playlist'][1]['chapter'] == rep['chapters'][1]['stamp'], 'manifest không có mốc chapter')
    return f'5 bài, mốc {[c["stamp"] for c in rep["chapters"]]}, dài {got} mẫu đúng dự tính'


def t_trim(lab: Lab):
    """Songs are cut around the singing: 4 bars before the first sung bar, 4 after the last,
    4 bars of overlap, so the wait between two voices is 4 bars (7.5 s at 128 BPM)."""
    cfg = lab.config('trimws')
    run = Path(cfg['_workspace']) / 'trim-run'
    bar = 90000                                              # samples per bar at 128 BPM
    act = [0.0] * 9 + [0.2] + [1.0] * 6 + [0.0] * 8          # a faint pickup in bar 9, sung bars 10..15, 24 bars
    tracks = []
    for i, late in enumerate((0.0, 12.0, 0.0), 1):
        slug = f'r0{i}_t'
        fake_remix(run, slug, 128, late=late)
        write_json(run / 'remix' / slug / 'vocals.json', {'dj_intro_bars': 8, 'dj_outro_bars': 8, 'total_bars': 24,
                                                          'bar_activity': act, 'source': 'analysis', 'has_vocals': True})
        tracks.append({'id': i, 'rank': i, 'title': f'Bài {i}', 'artist': f'Ca sĩ {i}', 'label': f'Ca sĩ {i} - Bài {i}', 'slug': slug})
    manifest = {'chart': {'date': '2026-11-09'}, 'exact_top': True, 'tracks': tracks,
                'playlist': [{'position': i, 'track': i} for i in (1, 2, 3)]}
    checks, out = mix.build(run, cfg, None, manifest)
    rep = read_json(run / 'mix' / 'mix_report.json')
    tr = rep['transitions']
    expect([t['mode'] for t in tr] == ['overlap', 'overlap'] and all(t['overlap_bars'] == 4 for t in tr), f'phải chồng 4 ô nhịp: {tr}')
    expect(abs(tr[0]['ns'] - (4 * bar + 576)) <= 72 and abs(tr[1]['ns'] - (4 * bar - 576)) <= 72, f'số mẫu đoạn chồng sai: {[t["ns"] for t in tr]}')
    cuts = [(t['cut_from_start_s'], t['cut_from_end_s']) for t in rep['tracks']]
    expect(cuts == [(11.25, 7.5), (11.25, 7.5), (11.25, 0.0)], f'cắt sai: {cuts} (muốn 6 ô nhịp đầu, 4 ô nhịp cuối, bài cuối giữ đuôi)')
    lens = [14 * bar, 14 * bar, 18 * bar]
    starts = [0, lens[0] - tr[0]['ns']]
    starts.append(starts[1] + lens[1] - tr[1]['ns'])
    total = starts[2] + lens[2]
    marks = [0] + [round_half_up((starts[i + 1] + tr[i]['ns'] / 2) / RATE) for i in range(2)]
    expect([c['seconds'] for c in rep['chapters']] == marks, f'mốc chapter sai: {[c["seconds"] for c in rep["chapters"]]} != {marks}')
    got = ffmpeg.probe(run / 'mix.wav')['audio']['samples']
    expect(got == total == rep['total_samples'], f'độ dài mix {got} != dự tính {total}')
    expect(rep['waits']['start_s'] == 7.5 and all(abs(g - 7.5) < 0.05 for g in rep['waits']['gaps_s']), f'khoảng không lời sai: {rep["waits"]}')
    expect(status_of(checks, 'start_wait') == 'PASS' and status_of(checks, 'vocal_data') is None, f'{checks}')
    # a remix without vocal data is cut on its DJ intro and outro, and says so
    run2 = Path(cfg['_workspace']) / 'trim-blind'
    for slug in ('r01_x', 'r02_y'):
        fake_remix(run2, slug, 128)
    man2 = {'chart': {}, 'exact_top': True, 'playlist': [{'position': 1, 'track': 1}, {'position': 2, 'track': 2}],
            'tracks': [{'id': i, 'rank': i, 'title': f'Bài {i}', 'artist': 'x', 'label': f'x - Bài {i}', 'slug': s}
                       for i, s in ((1, 'r01_x'), (2, 'r02_y'))]}
    checks2, _ = mix.build(run2, cfg, None, man2)
    rep2 = read_json(run2 / 'mix' / 'mix_report.json')
    expect(status_of(checks2, 'vocal_data') == 'WARN' and rep2['tracks'][1]['cut_from_start_s'] == 7.5
           and rep2['tracks'][0]['trim_basis'] == 'dj_sections', f'thiếu dữ liệu giọng hát phải cắt theo đoạn DJ và báo WARN: {rep2["tracks"]}')
    return f'cắt quanh giọng hát: chờ đầu {rep["waits"]["start_s"]}s, giữa các bài {rep["waits"]["gaps_s"]}s; thiếu dữ liệu thì cắt theo đoạn DJ'


def t_cover(lab: Lab):
    if not lab.root:
        raise Skip('cần repo m10-mixcover (--root)')
    cfg, run, manifest = mix_run(lab, 'cover-run')
    mix.build(run, cfg, None, manifest)
    manifest = read_json(run / 'manifest.json')
    checks, info = cover.make_cover(run, cfg, manifest, read_json(run / 'mix' / 'mix_report.json'), LIMITS)
    for name in ('cover.png', 'cover_thumb.jpg', 'chapters_match', 'thumbnail_bytes', 'thumbnail_width', 'video_background', 'side_column_clear'):
        expect(status_of(checks, name) == 'PASS', f'{name}: {[c for c in checks if c["name"] == name]}')
    expect((run / 'thumbnail.jpg').is_file() and (run / 'cover.png').is_file(), 'không chép cover/thumbnail ra thư mục lượt chạy')
    expect((run / 'video' / 'background.png').is_file() and read_json(run / 'video' / 'background.json')['geometry']['clear_px'] >= 0,
           'thiếu nền video có danh sách bài ở mép, hoặc vòng phổ chạm được cột bài')
    bg_json = read_json(run / 'video' / 'background.json')
    bgi, height = bg_json['text'], int(cfg['video']['size'].split('x')[1])
    (x0, x1), box = bgi['column'], bgi['box']
    expect(' '.join(bgi['title_lines']) == cover.side_title(cfg).upper() and bgi['fits']
           and bgi['title_px'] >= round(cfg['video']['side_title_min_size'] * height)
           and bgi['tracks'] == len(manifest['playlist']) and bgi['track_px'] >= round(cfg['video']['side_track_min'] * height),
           f'nền video: tiêu đề "{cover.side_title(cfg)}" trên đủ {len(manifest["playlist"])} bài, đủ to: {bgi}')
    expect(x0 <= box[0] and box[2] <= x1 and x0 >= bg_json['geometry']['column_inner_px'] - 1,
           f'cột chữ phải nằm trong vùng vòng phổ không với tới: {bgi}')
    long_cfg = copy.deepcopy(cfg)
    long_cfg['video']['side_title'] = 'một câu rất rất dài không thể nào vừa được cột chữ hẹp ở mép video này đâu'
    long_cfg['video']['side_title_min_size'] = 0.25
    info_long, got = cover.draw_side(long_cfg, cover.playlist_tracks(manifest), lab.tmp / 'long_side.png', None, 'right',
                                     'video_background')
    expect(status_of(got, 'video_background') == 'FAIL', f'tiêu đề quá dài không vừa cột phải FAIL: {got}')
    expect(preflight.mixcover_preset_check(cfg)['status'] == 'PASS', 'preset thật của m10-mixcover phải có đủ khoá của cột bài')
    broken = copy.deepcopy(cfg)
    broken['cover']['preset'] = str(lab.tmp / 'no_layout.yaml')
    (lab.tmp / 'no_layout.yaml').write_text('layout: null\n', encoding='utf-8')
    broken['video']['look'] = 'visualizer'
    gone = preflight.mixcover_preset_check(broken)
    expect(gone['status'] == 'FAIL' and 'layout.margin' in gone['detail'] and 'colors.primary' not in gone['detail'],
           f'preset mất khoá layout phải làm phép kiểm FAIL và nêu đúng khoá: {gone}')
    broken['video']['look'] = 'cover'                              # that look does not show the side text
    expect(preflight.mixcover_preset_check(broken)['status'] == 'WARN', 'với kiểu cover, preset mất khoá chỉ là WARN')
    skipped, _ = cover.make_cover(run, cfg, manifest, read_json(run / 'mix' / 'mix_report.json'), {})
    expect(status_of(skipped, 'thumbnail_bytes') == 'SKIP', 'giới hạn chưa xác minh phải là SKIP')
    lab.cover_run = (cfg, run)
    return 'cover 1920x1080, thumbnail 1280x720, chapters.txt trùng mốc của skill'


def t_video(lab: Lab):
    if not lab.root:
        raise Skip('cần repo m10-visualizer (--root)')
    if not getattr(lab, 'cover_run', None):
        t_cover(lab)
    cfg, run = lab.cover_run
    res = video.preview(run, cfg, ('cover', 'visualizer'), seconds=3.0)
    for look in ('cover', 'visualizer'):
        bad = [c for c in res['looks'][look]['checks'] if c['status'] == 'FAIL']
        expect(not bad, f'kiểu {look}: {bad}')
    expect(status_of(res['looks']['cover']['checks'], 'cover_readable') == 'PASS', 'kiểu cover: chữ phải đọc được')
    expect(status_of(res['looks']['visualizer']['checks'], 'tracklist_readable') == 'PASS',
           f'kiểu visualizer: cột chữ ở mép phải đọc được: {res["looks"]["visualizer"]["checks"]}')
    vz = Path(cfg['repos']['visualizer'])
    clip = run / 'video' / 'negative.mp4'
    got = video.run_visualizer(cfg, run / 'mix.wav', clip, ['--bg', str(run / 'cover' / 'cover.png'),
                                                           '--logo', str(vz / 'assets' / 'M10-logo-mark.png')],
                               run / 'logs' / 'negative.log', start=30.0, duration=3.0)
    expect(got['code'] == 0, f'không render được đối chứng: {got["stderr"][-200:]}')
    checks, info = video.check_video(cfg, clip, 3.0, 'cover', run / 'cover' / 'cover.png', run / 'video' / 'neg_frames', at=1.5)
    expect(status_of(checks, 'cover_readable') == 'FAIL', f'lớp phủ mặc định phải làm phép kiểm FAIL: SSIM {info.get("cover_ssim")}')
    # the same for the side column: a ring blown up over it must fail the check
    args, _ = video.look_args(cfg, run, 'visualizer')
    wide = run / 'video' / 'negative_side.mp4'
    got = video.run_visualizer(cfg, run / 'mix.wav', wide, args + ['--set', 'effects.circular_spectrum.radius=0.42'],
                               run / 'logs' / 'negative_side.log', start=30.0, duration=3.0)
    expect(got['code'] == 0, f'không render được đối chứng cột bài: {got["stderr"][-200:]}')
    geo = read_json(run / 'video' / 'background.json')
    checks2, info2 = video.check_video(cfg, wide, 3.0, 'visualizer', run / 'video' / 'background.png', run / 'video' / 'neg_frames',
                                       at=1.5, text_side=geo['text_side'], column_inner=geo['geometry']['column_inner_frac'])
    expect(status_of(checks2, 'tracklist_readable') == 'FAIL', f'vòng phổ đè lên cột chữ phải làm phép kiểm FAIL: {info2.get("side_diff")}')
    return (f'cover SSIM {res["looks"]["cover"]["cover_ssim"]} (đối chứng {info["cover_ssim"]}); '
            f'cột chữ lệch nền {res["looks"]["visualizer"]["side_diff"]} (đối chứng vòng phổ đè lên {info2["side_diff"]}, ngưỡng {cfg["video"]["max_side_diff"]})')


def good_meta(run: Path) -> dict:
    lines = youtube.chapter_lines(run)
    man = read_json(run / 'manifest.json')
    credits = '\n'.join(f'{i}. {t["title"]} – {t["artist"]}' for i, t in enumerate(cover.playlist_tracks(man), 1))
    desc = ('Nhạc remix Việt phối lại kiểu vinahouse, nghe liền mạch một lèo.\nBật loa và nghe trọn bản mix nhạc remix của M10 Music.\n\n'
            'Tracklist:\n' + '\n'.join(lines) + '\n\nBài gốc và nghệ sĩ:\n' + credits +
            '\n\nĐây là bản phối vinahouse của M10 Music, có dùng công cụ AI. Ảnh DJ do AI tạo, không phải người thật.\n\n#nhacremix #vinahouse')
    form = {k: {'value': 'x', 'why': 'y'} for k in youtube.FORM_KEYS}
    scores = {k: 4 for k in youtube.SCORE_KEYS}
    return {'primary_keyword': 'nhạc remix', 'secondary_keywords': ['vinahouse remix'],
            'titles': [{'text': '5 Bài Nhạc Remix Việt Phối Vinahouse Nghe Là Nghiện | M10 Music', 'angle': 'số bài', 'scores': scores, 'why': 'rõ'},
                       {'text': 'Nhạc Remix Vinahouse Tháng 11/2026 – Mix Liền Mạch', 'angle': 'thời gian', 'scores': scores, 'why': 'rõ'},
                       {'text': 'Nhạc Remix Việt Cực Căng – Vinahouse Mix', 'angle': 'cảm xúc', 'scores': scores, 'why': 'rõ'}],
            'description': desc, 'tags': ['nhạc remix', 'vinahouse remix', 'nhac remix', 'm10 music'], 'hashtags': ['#nhacremix', '#vinahouse'],
            'form': form, 'pinned_comment': 'Bạn thích bài nào nhất trong mix?', 'playlist': 'Nhạc Remix Vinahouse – M10 Music'}


def t_metadata(lab: Lab):
    cfg, run, manifest = mix_run(lab, 'meta-run')
    mix.build(run, cfg, None, manifest)
    write_json(run / 'nct' / 'report.json', read_json(HERE / 'testdata' / 'nct_report.json'))
    ydir = run / 'youtube'
    ydir.mkdir()
    evidence = {'collected_on': '2026-11-10', 'live': True,
                'queries': [{'query': f'q{i}', 'results': [{'title': 't', 'url': 'https://example.invalid/v'}]} for i in range(3)]}
    real_limits = youtube.load_limits
    youtube.load_limits = lambda: LIMITS
    base_mix = read_json(run / 'mix' / 'mix_report.json')
    try:
        def verdict(change=None, mixinfo=None, ev=evidence, limits=None):
            meta = good_meta(run)
            if change:
                change(meta)
            write_json(ydir / 'youtube.json', meta)
            write_json(ydir / 'evidence.json', ev)
            write_json(run / 'mix' / 'mix_report.json', mixinfo or base_mix)
            if limits is not None:
                youtube.load_limits = lambda: limits
            try:
                return youtube.validate(run)
            finally:
                youtube.load_limits = lambda: LIMITS
                write_json(run / 'mix' / 'mix_report.json', base_mix)

        good = verdict()
        expect(worst(good) != 'FAIL', f'mẫu tốt bị FAIL: {[c for c in good if c["status"] == "FAIL"]}')
        youtube.render_md(run)
        expect((run / 'youtube.md').is_file() and (run / 'youtube.json').is_file(), 'không xuất youtube.md')

        def late_start(m):
            m = copy.deepcopy(m)
            for c in m['chapters']:
                c['seconds'] += 5
            return m

        def short_chapter(m):
            m = copy.deepcopy(m)
            m['chapters'][1]['seconds'] = 8
            return m

        cases = [
            ('title_length', lambda m: m['titles'][0].update(text='Nhạc remix ' + 'x' * 95), None),
            ('description_length', lambda m: m.update(description=m['description'] + '\n' + 'nhạc điện tử ' * 260), None),   # < 5000 chars, > 5000 bytes
            ('chapter_rules', None, late_start(base_mix)),
            ('chapter_rules', None, short_chapter(base_mix)),
            ('count_claims', lambda m: m['titles'][0].update(text='Top 12 Nhạc Remix Việt Hay Nhất'), None),
            ('count_claims', lambda m: m['titles'][1].update(text='7 bài nhạc remix nghe là nghiện'), None),
            ('search_volume_claims', lambda m: m.update(description=m['description'] + '\n50.000 lượt tìm kiếm mỗi tháng'), None),
            ('banned_phrases', lambda m: m['tags'].append('nhạc no copyright'), None),
            ('banned_phrases', lambda m: m['titles'][2].update(text='Nhạc Remix Việt (Official Audio)'), None),
            ('banned_phrases', lambda m: m['hashtags'].append('#EDM'), None),
            ('tags_artists', lambda m: m['tags'].append('Nguyễn Vĩ'), None),
            ('description_credits', lambda m: m.update(description=m['description'].replace('Ca sĩ 3', 'ai đó')), None),
            ('description_chapters', lambda m: m.update(description=m['description'].replace('00:00 ', '00:01 ')), None),
            ('ai_disclosure', lambda m: m.update(description=m['description'].replace('AI', 'máy')), None),
            ('tags_unique', lambda m: m['tags'].append('NHẠC REMIX'), None),
            ('title_keyword', lambda m: m['titles'][0].update(text='5 Bài Vinahouse Việt Nghe Là Nghiện'), None),
        ]
        for name, change, mixinfo in cases:
            got = verdict(change, mixinfo)
            expect(status_of(got, name) == 'FAIL', f'mẫu sai phải FAIL ở {name}: {[c for c in got if c["name"] == name]}')
        inexact = copy.deepcopy(read_json(run / 'manifest.json'))
        inexact['exact_top'] = False
        write_json(run / 'manifest.json', inexact)
        got = verdict(lambda m: m['titles'][0].update(text='Top 5 Nhạc Remix Việt'))
        expect(status_of(got, 'count_claims') == 'FAIL', '"Top 5" khi không đúng hạng 1–5 phải FAIL')
        loose = verdict(limits={})
        expect(status_of(loose, 'title_length') == 'SKIP' and status_of(loose, 'tags_length') == 'SKIP',
               'giới hạn chưa xác minh phải SKIP, không PASS')
        offline = verdict(ev={'live': False, 'reason': 'không có công cụ web'})
        expect(status_of(offline, 'evidence') == 'WARN', 'không có dữ liệu trực tiếp phải WARN')
        bad_ev = verdict(ev={'live': True, 'collected_on': '2026-11-10', 'queries': [{'query': 'q', 'volume': 5000, 'results': []}]})
        expect(status_of(bad_ev, 'search_volume_claims') == 'FAIL' and status_of(bad_ev, 'evidence') == 'FAIL', 'volume bịa trong evidence')
    finally:
        youtube.load_limits = real_limits
    return f'mẫu tốt đạt; {len(cases) + 4} mẫu sai đều bị bắt đúng phép kiểm'


def t_resume(lab: Lab):
    if not lab.root:
        raise Skip('cần --root (preflight, mixcover, visualizer thật)')
    files = {1: lab.source('s1.wav'), 2: lab.source('s2_flaky.wav'), 3: lab.source('s3.wav'), 4: lab.source('s4_fail.wav')}
    cfg = lab.config('resume')
    rep = lab.report({1: ('file', files[1]), 2: ('file', files[2]), 3: ('file', files[3])})
    run = lab.run_dir(cfg, rep, 3, 'resume-run')
    code, out = pipeline('run', '--run', run)
    expect(code == 20 and out.get('stage') == 'youtube', f'lần đầu phải chạy tới youtube rồi chờ agent: {code} {out}')
    st = State.load(run)
    expect(all(st.stage(s)['status'] == 'done' for s in ('originals', 'art', 'remix', 'mix', 'cover', 'video')), 'các chặng máy chưa xong')
    job2 = read_json(run / 'remix' / 'r02_' + nct.slugify(nct.base_title(rep['songs'][1]['title']), 36) / 'job.json') \
        if False else None
    made = lab.fake.created
    attempts = [read_json(p)['attempts'] for p in sorted((run / 'remix').glob('*/job.json'))]
    expect(sorted(attempts) == [1, 1, 2], f'bài flaky phải được thử lại một lần: {attempts}')
    video_sig = (run / 'video.mp4').stat().st_mtime_ns
    code, out = pipeline('run', '--run', run)
    ran = [r['stage'] for r in out.get('ran', [])]
    expect(code == 20 and ran == ['preflight'] and lab.fake.created == made, f'chạy lại không được làm lại chặng đã đạt: {ran}')
    expect((run / 'video.mp4').stat().st_mtime_ns == video_sig, 'video bị render lại dù không có gì đổi')
    cfg['mix']['overlap_bars'] = 2
    cfgmod.save(cfg)
    code, out = pipeline('run', '--run', run)
    ran = [r['stage'] for r in out.get('ran', [])]
    expect(ran == ['preflight', 'mix', 'cover', 'video'] and lab.fake.created == made, f'đổi đầu vào của mix phải làm lại mix, cover, video: {ran}')
    ydir = run / 'youtube'
    ydir.mkdir(exist_ok=True)
    meta = good_meta(run)
    meta['titles'][0]['text'] = '3 Bài Nhạc Remix Việt Phối Vinahouse | M10 Music'
    write_json(ydir / 'youtube.json', meta)
    write_json(ydir / 'evidence.json', {'live': False, 'reason': 'selftest'})
    code, out = pipeline('run', '--run', run)
    st = State.load(run)
    expect(code == 0 and out.get('finished') and st.finished(), f'lượt chạy phải xong: {code} {out}')
    expect((run / 'REPORT.md').is_file() and st.data['result'].get('video'), 'thiếu REPORT.md hoặc result')

    # a failed remix stops for the human; "skip" carries on without it
    rep2 = lab.report({1: ('file', files[1]), 2: ('file', files[4]), 3: ('file', files[3])})
    run2 = lab.run_dir(cfg, rep2, 3, 'fail-run')
    code, out = pipeline('run', '--run', run2, '--until', 'remix')
    expect(code == 10 and 'hạng 2' in out.get('waiting', ''), f'bài phối lỗi phải dừng hỏi: {code} {out}')
    expect(sum(1 for p in (run2 / 'remix').glob('*/verify.json')) == 2, 'các bài tốt phải vẫn được phối xong')
    pipeline('decide', '--run', run2, '--remix-failed', 'skip')
    code, out = pipeline('run', '--run', run2, '--until', 'mix')
    man = read_json(run2 / 'manifest.json')
    expect(code == 0 and [t['rank'] for t in man['tracks']] == [1, 3], f'skip phải bỏ hạng 2: {code} {out}')

    # an interrupt in the remix stage: resume picks the same job up instead of submitting a new one
    lab.fake.job_seconds = 6.0
    run3 = lab.run_dir(cfg, lab.report({1: ('file', files[1]), 2: ('file', files[3])}), 2, 'interrupt-run')
    code, _ = pipeline('run', '--run', run3, '--until', 'art')
    before = lab.fake.created
    proc = subprocess.Popen([sys.executable, str(HERE / 'pipeline.py'), 'run', '--run', str(run3), '--until', 'remix'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(2.5)
    proc.send_signal(signal.SIGINT)
    proc.communicate(timeout=60)
    expect(proc.returncode == 130 and State.load(run3).stage('remix')['status'] == 'interrupted', f'ngắt phải cho exit 130: {proc.returncode}')
    lab.fake.job_seconds = 0.3
    code, out = pipeline('run', '--run', run3, '--until', 'remix')
    expect(code == 0 and lab.fake.created == before + 2, f'chạy tiếp phải dùng lại job đang dở: tạo {lab.fake.created - before} job')
    return 'bỏ qua chặng đã đạt, làm lại khi đầu vào đổi, thử lại bài flaky, dừng hỏi khi phối lỗi, ngắt rồi chạy tiếp'


def t_pane(lab: Lab):
    cfg = lab.config('pane')
    rep = lab.report({1: ('file', lab.source('p1.wav'))})
    run = lab.run_dir(cfg, rep, 1, 'pane-run')

    def once():
        done = subprocess.run([sys.executable, str(HERE / 'steps_pane.py'), 'once', str(run)], capture_output=True, text=True)
        expect(done.returncode == 0, f'once thoát {done.returncode}')
        return done.stdout

    st = State.load(run)
    st.start('preflight')
    st.finish('preflight', [])
    st.start('chart')
    st.finish('chart', [])
    st.start('remix')
    st.progress('remix', done=1, total=3, text='Bài Hai (trộn, 62%)', force=True)
    text = once()
    expect('▶ S4' in text and '1/3' in text and 'Đang làm: S4 · Bài Hai' in text and 'Chờ bạn: —' in text, f'đang chạy:\n{text}')
    st.data['heartbeat'] = time.time() - 4000
    st.save()
    expect('⚠ Không có cập nhật' in once(), 'không cảnh báo khi treo lâu')
    st.wait('remix', 'Thiếu 1 bài: chọn backfill | skip | manual')
    text = once()
    expect('⏸ S4' in text and 'Chờ bạn: Thiếu 1 bài' in text, f'đang chờ:\n{text}')
    st.fail('remix', 'cổng 8765 bị chiếm')
    expect('✗ S4' in once() and 'Lỗi: cổng 8765' in once(), 'không hiện lỗi')
    for sid in [s['id'] for s in st.data['stages']]:
        st.start(sid)
        st.finish(sid, [])
    st.data['result'] = {'video': '/x/video.mp4', 'thumbnail': '/x/thumbnail.jpg', 'youtube_md': '/x/youtube.md'}
    st.save()
    text = once()
    expect('Xong tất cả các bước' in text and '/x/video.mp4' in text and '▶' not in text, f'đã xong:\n{text}')
    st.start('mix')
    st.finish('mix', [{'name': 'x', 'status': 'FAIL', 'detail': 'hỏng'}])
    expect('✗ S5' in once(), 'chặng có phép kiểm FAIL không được hiện là xong')
    env = {k: v for k, v in os.environ.items() if k != 'HERDR_PANE_ID'}
    done = subprocess.run([sys.executable, str(HERE / 'steps_pane.py'), 'open', str(run)], capture_output=True, text=True, env=env)
    expect(done.returncode == 69 and 'S0' in done.stdout, f'không có herdr thì open phải thoát 69, được {done.returncode}')
    return 'đang chạy, treo, chờ bạn, lỗi, xong, FAIL không hiện là xong, open thoát 69 khi không có herdr'


TESTS = {'help': t_help, 'selection': t_selection, 'ask_flow': t_ask_flow, 'art_review': t_art_review, 'mix': t_mix, 'trim': t_trim, 'cover': t_cover, 'video': t_video,
         'metadata': t_metadata, 'resume': t_resume, 'pane': t_pane}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only')
    ap.add_argument('--root')
    ap.add_argument('--keep', action='store_true')
    args = ap.parse_args(argv)
    names = [n.strip() for n in args.only.split(',')] if args.only else list(TESTS)
    unknown = [n for n in names if n not in TESTS]
    if unknown:
        print(f'không có test: {unknown}; có: {" ".join(TESTS)}', file=sys.stderr)
        return 2
    root = Path(args.root).resolve() if args.root else cfgmod.find_root()
    tmp = Path(tempfile.mkdtemp(prefix='rcv_selftest_'))
    lab = Lab(tmp, root)
    results = []
    try:
        for name in names:
            t0 = time.time()
            try:
                detail, status = TESTS[name](lab), 'PASS'
            except Skip as exc:
                detail, status = str(exc), 'SKIP'
            except AssertionError as exc:
                detail, status = str(exc), 'FAIL'
            except Exception as exc:                       # a crash is a failure, with where it happened
                detail, status = f'{type(exc).__name__}: {exc} @ {traceback.format_exc().splitlines()[-3].strip()}', 'FAIL'
            results.append({'test': name, 'status': status, 'detail': detail, 'seconds': round(time.time() - t0, 1)})
    finally:
        lab.close()
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    failed = [r for r in results if r['status'] == 'FAIL']
    print(json.dumps({'worst': 'FAIL' if failed else 'PASS', 'root': str(root) if root else None,
                      'kept': str(tmp) if args.keep else None, 'tests': results}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
