#!/usr/bin/env python3
"""Offline tests for the lofi-ballad-to-video scripts. No GPU, no network, no NCT request, no
image provider call.

  selftest.py [--only NAME[,NAME]] [--root DIR] [--keep]

Tests: help, draw, init, selection, ask_flow, art_review, mix, trim, cover, video, scene, scene_render,
metadata, resume, source_tempo, backing_tempo, stall, decide, set, guards, from_run, pane.
`cover` and `video` call the real m10-mixcover (--dry-run) and m10-visualizer on a few seconds
of synthetic audio, and the tests that run the pipeline need its preflight to pass; they are
SKIP when the repos are not found (pass --root DIR, the folder that holds the four repos). StemForge is replaced by a fake server. Prints JSON.
Exit 0 when every test ran and passed, 1 when one failed, 2 usage, 3 when none failed but
some were skipped (the summary then says INCOMPLETE and names them).
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
from rcvlib import cover, ffmpeg, mix, nct, preflight, scenery, songlist, video, youtube  # noqa: E402
from rcvlib.common import read_json, round_half_up, worst, write_json  # noqa: E402
from rcvlib.fake_stemforge import FakeStemForge  # noqa: E402
from rcvlib.state import STAGE_IDS, RunLock, State  # noqa: E402

RATE = 48000
LIMITS = {'title_max_chars': {'value': 100, 'unit': 'characters', 'verified': True},
          'description_max_chars': {'value': 5000, 'unit': 'characters', 'verified': True},
          'description_max_bytes': {'value': 5000, 'unit': 'bytes', 'verified': True},
          'thumbnail_min_width': {'value': 640, 'unit': 'pixels', 'verified': True},
          'tags_max_chars': {'value': 500, 'unit': 'characters', 'verified': True},
          'hashtags_max_count': {'value': 60, 'unit': 'hashtags', 'verified': True},
          'chapters_min_count': {'value': 3, 'unit': 'timestamps', 'verified': True},
          'chapter_min_seconds': {'value': 10, 'unit': 'seconds', 'verified': True},
          'thumbnail_max_bytes': {'value': 2000000, 'unit': 'bytes', 'verified': True}}


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


FIXTURE = HERE / 'testdata' / 'list_report.json'


class Lab:
    """A temporary workspace: config, fake StemForge, synthetic sources, a drawn-list fixture and
    a small ballad list (two periods, one song listed twice)."""

    def __init__(self, tmp: Path, root: Path | None):
        self.tmp, self.root = tmp, root
        self.fake = FakeStemForge(job_seconds=0.3)
        self.src = tmp / 'sources_pool'
        self.src.mkdir(parents=True)
        self.n = 0
        songs = read_json(FIXTURE)['songs']
        entry = lambda i, s: {'stt': i, 'bai_hat': s['title'], 'ca_si': s['artist'].split(', '), 'nhac_si': s.get('composers') or []}  # noqa: E731
        first = [entry(i, x) for i, x in enumerate(songs, 1)]
        second = [{'stt': 100 + i, 'bai_hat': f'Bài Thử {i}', 'ca_si': [f'Ca Sĩ Thử {i}'], 'nhac_si': ['Nhạc Sĩ Thử']} for i in range(1, 16)]
        second[0]['nhac_si'] = 'Chưa xác minh'                     # the human's list writes "not checked yet" as a string
        second[1]['nhac_si'] = 'Một Nhạc Sĩ'                       # and a single composer as a string
        second.append({'stt': 199, 'bai_hat': 'Bài Không Rõ Ca Sĩ', 'ca_si': ['Chưa xác minh'], 'nhac_si': 'Chưa xác minh'})
        self.list_path = tmp / 'ballads.json'
        write_json(self.list_path, {'the_loai': 'Ballad Việt Nam', 'cac_giai_doan': [
            {'giai_doan': 'Giai đoạn 2010–2014', 'danh_sach_bai_hat': first + [dict(first[0], stt=99)]},
            {'giai_doan': 'Giai đoạn 2015–2019', 'danh_sach_bai_hat': second}]})

    def source(self, name: str, bars: int = 8) -> Path:
        return ffmpeg.synth_track(self.src / name, 100, bars)

    def config(self, name: str = 'ws', **over) -> dict:
        repos = {k: str(self.root / v) if self.root else '/nonexistent' for k, v in cfgmod.REPOS.items()}
        base = {'repos': repos, 'nct': {'live_access': False, 'home': str(self.tmp / 'nct_home')},
                'songlist': {'path': str(self.list_path)},
                'selection': {'count': 3, 'min_duration_s': 5},
                'remix': {'cleanup_jobs': 'keep', 'port': self.fake.port, 'poll_s': 0.2, 'stall_s': 20, 'job_timeout_s': 60,
                          'target_bpm': 128},          # one tempo; t_source_tempo tests the default "source"
                'cover': {'confirmed': True, 'dry_run': True, 'review': False},
                'video': {'fps': 10, 'size': '640x360'}}
        cfg = cfgmod.deep_merge(cfgmod.deep_merge(cfgmod.DEFAULTS, base), over)
        path = self.tmp / name / 'config.json'
        cfg['_path'], cfg['_workspace'] = str(path), str(path.parent)
        cfgmod.save(cfg)
        return cfg

    def report(self, plan: dict) -> dict:
        """The drawn-list fixture with NCT's answer set per position: plan[pos] = ('file', path) |
        ('other_title', path) | ('same_as', (pos, path)) | ('no_download', None) | decision | None."""
        rep = copy.deepcopy(read_json(FIXTURE))
        for song in rep['songs']:
            rank = song['position']
            what = plan.get(rank)
            if what is None:
                song['original'] = None
                continue
            orig = {'base_title': song['title'], 'title': song['title'], 'artist': song['artist'],
                    'nct_url': f'https://example.invalid/song/orig{rank}', 'manual_search_url': f'https://example.invalid/search?{rank}',
                    'release_information': f'Phát hành: 2012-01-01; Nhà phân phối: Hãng Thử {rank}',
                    'status': None, 'local_file_path': None}
            if isinstance(what, tuple):
                kind, value = what
                orig.update(decision='matched', status='downloaded', local_file_path=str(value) if kind in ('file', 'other_title') else None)
                if kind == 'other_title':
                    orig['title'] = song['title'] + ' 2'           # a sequel NCT matched by mistake
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
        drawn = [{'position': x['position'], 'title': x['title'], 'artists': x['artist'].split(', '),
                  'composers': x.get('composers') or [], 'key': songlist.song_key(x['title'], x['artist'].split(', '))}
                 for x in rep['songs']]
        songlist.write_run_files(run, {'period': 'Giai đoạn 2010–2014', 'slug': '2010-2014', 'label': '2010–2014', 'seed': 1,
                                       'count': count, 'fresh': len(drawn), 'period_size': len(drawn), 'notes': [],
                                       'songs': drawn}, self.list_path)
        State.create(run, {'name': name, 'dir': str(run), 'title': f'Test {name}', 'chart_date': rep['run']['chart_date'],
                           'period': 'Giai đoạn 2010–2014', 'period_label': '2010–2014', 'seed': 1,
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
            6: ('no_download', None), 7: ('file', short), 8: ('same_as', (1, a)), 9: None, 10: ('file', c),
            11: ('other_title', c)}
    rep = lab.report(plan)
    cfg = lab.config('sel')
    srcdir = lab.tmp / 'sel' / 'manual'
    cands = {x['rank']: x for x in nct.classify(rep, cfg, srcdir)}
    want = {1: None, 2: None, 3: 'file_missing', 4: 'uncertain', 5: 'not_found', 6: 'not_downloaded', 7: 'too_short',
            8: 'duplicate', 9: 'not_searched', 10: None, 11: 'title_mismatch'}
    for rank, reason in want.items():
        expect(cands[rank]['reason'] == reason and cands[rank]['usable'] == (reason is None),
               f'bài số {rank}: muốn {reason}, được {cands[rank]["reason"]}')
    sel = nct.select(list(cands.values()), 3, 3)
    expect(sel['short_by'] == 1 and [m['rank'] for m in sel['missing']] == [3], f'thiếu bài sai: {sel["short_by"]}')
    text = nct.missing_message(sel, srcdir, live=False)
    expect('03_' in text and 'backfill' in text and 'skip' in text and 'manual' in text, 'lời hỏi thiếu tên file hoặc lựa chọn')
    wide = nct.select(list(cands.values()), 3, 10)
    expect([x['rank'] for x in wide['selected']] == [1, 2, 10] and not wide['exact_top'], 'lấy bù sai')
    srcdir.mkdir(parents=True)
    shutil.copyfile(c, srcdir / '03_bai_tu_dat.wav')              # the human supplies rank 3
    again = {x['rank']: x for x in nct.classify(rep, cfg, srcdir)}
    expect(again[3]['usable'] and again[3]['source']['kind'] == 'manual', 'không nhận file tự đặt cho bài số 3')
    top = nct.select(list(again.values()), 3, 3)
    expect(not top['exact_top'] and top['short_by'] == 0 and [x['rank'] for x in top['selected']] == [1, 2, 3],
           'đủ bài 1–3, nhưng một lần bốc ngẫu nhiên không bao giờ là exact_top')
    expect(again[3]['artist'] == rep['songs'][2]['artist'] and again[3]['title'] == rep['songs'][2]['title'],
           'mặc định phải ghi tên bài và ca sĩ theo danh sách')
    tagged = srcdir / '03_bai_tu_dat.flac'                          # the same rank, now with an artist tag
    (srcdir / '03_bai_tu_dat.wav').unlink()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(c), '-metadata', 'artist=Ca Sĩ Trong Thẻ', str(tagged)], check=True)
    expect(nct.classify(rep, cfg, srcdir)[2]['artist'] == rep['songs'][2]['artist'], 'manual_artist=list vẫn đọc thẻ')
    cfg_tags = {**cfg, 'selection': {**cfg['selection'], 'manual_artist': 'tags'}}
    by_tag = {x['rank']: x for x in nct.classify(rep, cfg_tags, srcdir)}
    expect(by_tag[3]['artist'] == 'Ca Sĩ Trong Thẻ' and by_tag[3]['artist_from'] == 'tags' and by_tag[3]['usable'],
           f'manual_artist=tags phải ghi ca sĩ theo thẻ, được {by_tag[3].get("artist")}')
    expect(by_tag[1]['artist'] == cands[1]['artist'], 'manual_artist=tags chỉ đổi file người dùng tự đặt')
    rej = {x['rank']: x for x in nct.classify(rep, cfg, srcdir, {'2': 'remix_failed'})}
    expect(rej[2]['reason'] == 'remix_failed' and not rej[2]['usable'], 'bài bị loại vẫn được chọn')
    man = nct.build_manifest(rep, top, cfg, [1, 2, 1], {1: {'composers': ['Nhạc Sĩ A']}})
    expect([p['track'] for p in man['playlist']] == [1, 2, 1] and not man['exact_top'], 'sequence không vào playlist')
    expect(man['tracks'][0]['composers'] == ['Nhạc Sĩ A'] and man['tracks'][1]['composers'] == [], 'thiếu nhạc sĩ trong manifest')
    expect(cands[1]['distributor'] == 'Hãng Thử 1', f'nhà phân phối phải lấy từ bài NCT tìm được: {cands[1]["distributor"]}')
    expect(nct.distributor('Phát hành: 2026-04-29; Nhà phân phối: BELIEVE MUSIC') == 'BELIEVE MUSIC', 'không tách được nhà phân phối')
    for listed, found, same in (('3107', '3107-2', False), ('Tình Đơn Phương', 'Tình Đơn Phương 2', False),
                                ('Anh Nhớ Ra', 'ANH NHỚ RA (feat. Trang)', True), ('Đừng Như Thói Quen', 'Dung Nhu Thoi Quen', True),
                                ('Ghen', None, False)):
        expect(nct.same_title(listed, found) is same, f'same_title({listed!r}, {found!r}) phải là {same}')
    return 'đủ 9 lý do loại bài (cả tên lệch), file tự đặt, ca sĩ theo thẻ, lấy bù, loại bài, sequence, nhạc sĩ, không bao giờ Top N'


def t_ask_flow(lab: Lab):
    if not lab.root:
        raise Skip('cần --root để chạy preflight thật')
    a, b, c = lab.source('f1.wav'), lab.source('f2.wav'), lab.source('f3.wav')
    rep = lab.report({1: ('file', a), 2: ('file', b), 3: 'uncertain', 4: ('file', c)})
    cfg = lab.config('ask')
    run = lab.run_dir(cfg, rep, 3, 'ask-run')
    code, out = pipeline('run', '--run', run, '--until', 'originals')
    expect(code == 10 and 'bài số 3' in out.get('waiting', ''), f'phải dừng hỏi (exit 10), được {code}: {out}')
    st = State.load(run)
    expect(st.stage('originals')['status'] == 'waiting' and st.data['waiting'], 'state không ghi "Chờ bạn"')
    expect(not (run / 'manifest.json').exists(), 'đã tự quyết khi chưa hỏi')
    pipeline('decide', '--run', run, '--missing', 'backfill')
    code, out = pipeline('run', '--run', run, '--until', 'originals')
    expect(code == 0, f'lấy bù offline với bài số 4 có sẵn file phải qua: {code} {out}')
    man = read_json(run / 'manifest.json')
    expect([t['rank'] for t in man['tracks']] == [1, 2, 4] and not man['exact_top'], 'lấy bù phải ra bài số 1, 2, 4')
    hist = read_json(Path(cfg['_workspace']) / 'song_history.json')
    expect(hist['runs']['ask-run']['titles'] == [t['title'] for t in man['tracks']], f'sổ bài đã dùng phải ghi 3 bài của video: {hist}')
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
    expect(code == 0 and [t['rank'] for t in read_json(run3 / 'manifest.json')['tracks']] == [1, 2, 3], 'manual có file phải ra bài số 1–3')
    # another file under the same name is another song: the stage runs again and sees the new file
    size = read_json(run3 / 'manifest.json')['tracks'][2]['source']['size']
    shutil.copyfile(lab.source('f3_longer.wav', bars=12), run3 / 'sources' / '03_tu_dat.wav')
    code, out = pipeline('run', '--run', run3, '--until', 'originals')
    again = read_json(run3 / 'manifest.json')['tracks'][2]['source']
    expect(code == 0 and 'originals' in [r['stage'] for r in out.get('ran', [])] and again['size'] != size and 'sha256' not in again,
           f'thay file cùng tên trong sources/ phải được chọn lại: {out.get("ran")} {again}')
    return 'dừng hỏi (exit 10), backfill, skip, manual, thay file cùng tên'


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
                       'slug': slug, 'chart_title': f'Bài {i}', 'chart_artist': f'Ca sĩ {i}', 'distributor': 'Test',
                       'composers': [f'Nhạc sĩ {i}'], 'source': {'path': 'x', 'duration': 30.0}})
    manifest = {'version': 1, 'chart': {'title': 'Ballad Việt · Giai đoạn 2010–2014', 'date': '2026-11-13', 'period': '2010–2014'},
                'exact_top': False,
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
    # the mix is brought to the target loudness by one gain, as far as the true peak allows
    loud = next(c for c in checks if c['name'] == 'loudness')
    at_target = abs(rep['loudness']['integrated_lufs'] - cfg['mix']['target_lufs']) <= 0.2
    expect(at_target or 'true peak' in loud['detail'], f'bản mix phải về đích loudness hoặc nói rõ vì sao không: {loud} gain {rep["gain_db"]}')
    expect(rep['gain_db'] == 0 or 'đã chỉnh' in loud['detail'], f'đã chỉnh gain thì phải ghi: {loud}')
    expect((run / 'transitions_preview.mp3').is_file() and len(rep['preview']['index']) == 4, 'thiếu file nghe thử đoạn chuyển')
    man = read_json(run / 'manifest.json')
    expect(man['playlist'][1]['chapter'] == rep['chapters'][1]['stamp'], 'manifest không có mốc chapter')
    stamps = [c["stamp"] for c in rep["chapters"]]

    # "cut": back to back, with a few milliseconds of overlap so the join does not click
    cut = {**cfg, 'mix': {**cfg['mix'], 'transition': 'cut'}}
    mix.build(run, cut, None, manifest)
    rep = read_json(run / 'mix' / 'mix_report.json')
    ns = round(cfg['mix']['cut_fade_ms'] * RATE / 1000)
    expect(all(t['mode'] == 'cut' and t['ns'] == ns for t in rep['transitions']), f'nối thẳng phải chồng {ns} mẫu: {rep["transitions"]}')
    got = ffmpeg.probe(run / 'mix.wav')['audio']['samples']
    expect(got == sum(t['samples'] for t in rep['tracks']) - ns * len(rep['transitions']) == rep['total_samples'],
           f'độ dài mix nối thẳng {got} != dự tính {rep["total_samples"]}')
    return f'5 bài, mốc {stamps}, dài đúng dự tính; nối thẳng chồng {cfg["mix"]["cut_fade_ms"]} ms'


def t_trim(lab: Lab):
    """Songs are cut around the singing: 4 bars before the first sung bar, 4 after the last,
    4 bars of overlap, so the wait between two voices is 4 bars (7.5 s at 128 BPM)."""
    cfg = lab.config('trimws', mix={'lead_in_bars': 4, 'tail_bars': 4, 'dj_bars': 8})
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
    # no lead-in, no tail: straight into the voice, but a pickup bar and a last-note bar stay
    edge = [0.0] * 8 + [0.05, 0.2] + [1.0] * 6 + [0.3, 0.05] + [0.0] * 6
    ents = [{'bar_samples': 1000, 'samples': 24000, 'head': 0, 'end': 24000,
             'vocals': {'total_bars': 24, 'bar_activity': edge}} for _ in range(2)]
    mix.apply_trims(ents, {**cfg['mix'], 'lead_in_bars': 0, 'tail_bars': 0})
    expect((ents[0]['head'], ents[0]['end']) == (9000, 17000),
           f'không lead-in, không đuôi: phải giữ ô nhịp có tiếng hát lấn vào (9) và nốt cuối (16): {ents[0]}')
    return f'cắt quanh giọng hát: chờ đầu {rep["waits"]["start_s"]}s, giữa các bài {rep["waits"]["gaps_s"]}s; thiếu dữ liệu thì cắt theo đoạn DJ; giữ ô nhịp lấn và nốt cuối'


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
    # the thumbnail is the poster (large title, first songs), not the cover scaled down
    expect(status_of(checks, 'thumbnail_poster') == 'PASS' and ffmpeg.image_size(run / 'thumbnail.jpg') == (1280, 720)
           and (run / 'thumbnail.jpg').read_bytes() == (run / 'cover' / 'thumb_poster.jpg').read_bytes(),
           f'thumbnail phải là bản poster: {[c for c in checks if c["name"].startswith("thumbnail")]}')
    plain = cfgmod.deep_merge(cfg, {'cover': {'thumb_style': 'tracklist'}})
    checks_t, _ = cover.make_cover(run, plain, manifest, read_json(run / 'mix' / 'mix_report.json'), LIMITS)
    expect(status_of(checks_t, 'thumbnail_poster') is None
           and (run / 'thumbnail.jpg').read_bytes() == (run / 'cover' / 'cover_thumb.jpg').read_bytes(), 'thumb_style tracklist phải dùng thumbnail của mixcover')
    too_long = 'một tiêu đề dài quá mức cho một thumbnail nhỏ ' * 3
    long = cfgmod.deep_merge(cfg, {'cover': {'title': too_long, 'title_inexact': too_long}})
    checks_l, _ = cover.make_cover(run, long, manifest, read_json(run / 'mix' / 'mix_report.json'), LIMITS)
    expect(status_of(checks_l, 'thumbnail_poster') == 'FAIL', f'tiêu đề không vừa thumbnail phải FAIL: {[c for c in checks_l if c["name"] == "thumbnail_poster"]}')
    checks, info = cover.make_cover(run, cfg, manifest, read_json(run / 'mix' / 'mix_report.json'), LIMITS)
    expect((run / 'video' / 'background.png').is_file() and read_json(run / 'video' / 'background.json')['geometry']['clear_px'] >= 0,
           'thiếu nền video có danh sách bài ở mép, hoặc thanh sóng âm chạm được cột bài')
    bg_json = read_json(run / 'video' / 'background.json')
    bgi, height = bg_json['text'], int(cfg['video']['size'].split('x')[1])
    (x0, x1), box = bgi['column'], bgi['box']
    expect(' '.join(bgi['title_lines']) == cover.side_title(cfg).upper() and bgi['fits']
           and bgi['title_px'] >= round(cfg['video']['side_title_min_size'] * height)
           and bgi['tracks'] == len(manifest['playlist']) and bgi['track_px'] >= round(cfg['video']['side_track_min'] * height),
           f'nền video: tiêu đề "{cover.side_title(cfg)}" trên đủ {len(manifest["playlist"])} bài, đủ to: {bgi}')
    expect(x0 <= box[0] and box[2] <= x1 and x0 >= bg_json['geometry']['column_inner_px'] - 1,
           f'cột chữ phải nằm ngoài vùng thanh sóng âm: {bgi}')
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
    gone = preflight.mixcover_preset_check(broken)
    expect(gone['status'] == 'FAIL' and 'layout.margin' in gone['detail'] and 'colors.primary' not in gone['detail'],
           f'preset mất khoá layout phải làm phép kiểm FAIL và nêu đúng khoá: {gone}')
    person = copy.deepcopy(cfg)
    person['cover']['preset'] = 'm10'                              # a DJ picture, not a landscape
    expect(preflight.mixcover_preset_check(person)['status'] == 'FAIL', 'preset vẽ người (m10) phải bị preflight từ chối')
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
    res = video.preview(run, cfg, video.LOOKS, seconds=3.0)
    vis = res['looks']['visualizer']
    bad = [c for c in vis['checks'] if c['status'] == 'FAIL']
    expect(not bad, f'kiểu hình lofi: {bad}')
    for name in ('bars_visible', 'center_clear', 'tracklist_readable'):
        expect(status_of(vis['checks'], name) == 'PASS', f'{name}: {[c for c in vis["checks"] if c["name"] == name]}')
    args, _ = video.look_args(cfg, run, 'visualizer')
    expect(args[args.index('--logo') + 1] == str(video.logo_path(cfg)) and 'background.dim=0' in args, f'look_args: {args}')
    bg = run / 'video' / 'background.png'
    geo = read_json(run / 'video' / 'background.json')
    vz = Path(cfg['repos']['visualizer'])

    def render(name, extra):
        clip = run / 'video' / f'{name}.mp4'
        got = video.run_visualizer(cfg, run / 'mix.wav', clip, extra, run / 'logs' / f'{name}.log', start=30.0, duration=3.0)
        expect(got['code'] == 0, f'không render được đối chứng {name}: {got["stderr"][-200:]}')
        return video.check_video(cfg, clip, 3.0, 'visualizer', bg, run / 'video' / 'neg_frames', at=1.5, text_side=geo['text_side'],
                                 column_inner=geo['geometry']['column_inner_frac'], background=bg)

    logo = list(args)
    logo[logo.index('--logo') + 1] = str(vz / 'assets' / 'M10-logo-mark.png')
    c1, i1 = render('neg_logo', logo)
    expect(status_of(c1, 'center_clear') == 'FAIL', f'logo M10 ở giữa khung phải làm center_clear FAIL: lệch {i1.get("center_diff")}')
    clip = run / 'video' / 'neg_logo.mp4'
    heard = ffmpeg.loudness(clip)                              # the encoded sound track is measured against the mix
    same, _ = video.check_video(cfg, clip, 3.0, 'visualizer', None, run / 'video' / 'neg_frames', at=1.5, mix_loudness=heard)
    off, _ = video.check_video(cfg, clip, 3.0, 'visualizer', None, run / 'video' / 'neg_frames', at=1.5,
                               mix_loudness={**heard, 'integrated_lufs': heard['integrated_lufs'] - 3})
    expect(status_of(same, 'video_loudness') == 'PASS' and status_of(off, 'video_loudness') == 'WARN',
           f'tiếng trong video phải được đo và so với bản mix: {[c for c in same + off if c["name"] == "video_loudness"]}')
    c2, i2 = render('neg_nobars', args + ['--set', 'effects.bar_spectrum.enabled=false'])
    expect(status_of(c2, 'bars_visible') == 'FAIL', f'tắt thanh sóng âm phải làm bars_visible FAIL: lệch {i2.get("bars_diff")}')
    c3, i3 = render('neg_side', args + ['--set', 'effects.bar_spectrum.width=1.0', '--set', 'effects.bar_spectrum.max_length=0.8',
                                        '--set', 'effects.bar_spectrum.min_length=0.5'])
    expect(status_of(c3, 'tracklist_readable') == 'FAIL', f'thanh sóng âm đè lên cột chữ phải FAIL: lệch {i3.get("side_diff")}')
    return (f'thanh sóng âm lệch tranh {vis["bars_diff"]} (đối chứng tắt thanh {i2["bars_diff"]}), giữa khung {vis["center_diff"]} '
            f'(đối chứng logo M10 {i1["center_diff"]}), cột chữ {vis["side_diff"]} (đối chứng thanh đè lên {i3["side_diff"]})')


def t_draw(lab: Lab):
    """The draw: one period, its songs once each, in an order the seed fixes; songs of earlier
    videos last; never more than the pool or 50."""
    periods = songlist.load(lab.list_path)
    expect([p['slug'] for p in periods] == ['2010-2014', '2015-2019'] and periods[0]['duplicates'] == 1
           and len(periods[0]['songs']) == 20, f'đọc danh sách sai: {[(p["slug"], len(p["songs"]), p["duplicates"]) for p in periods]}')
    by_title = {s['title']: s for s in periods[1]['songs']}
    expect(by_title['Bài Thử 1']['composers'] == [] and by_title['Bài Thử 2']['composers'] == ['Một Nhạc Sĩ'],
           f'nhạc sĩ ghi bằng chuỗi phải đọc đúng: {by_title["Bài Thử 1"]["composers"]} {by_title["Bài Thử 2"]["composers"]}')
    expect('Bài Không Rõ Ca Sĩ' not in by_title and periods[1]['no_singer'] == ['Bài Không Rõ Ca Sĩ'],
           'bài chưa rõ ca sĩ phải bị bỏ khỏi lượt bốc, không làm hỏng cả danh sách')
    # the list's current shape: two-year periods, names joined in one string, a year per song, an open last period
    new_path = lab.tmp / 'ballads_periods.json'
    write_json(new_path, {'title': 'Ballad', 'periods': [
        {'period': '2010-2011', 'era_note': '…', 'songs': [
            {'rank': 1, 'title': 'Một Vòng Trái Đất', 'artist': 'Tim & Minh Hằng', 'songwriter': 'Nhất Trung', 'year': 2010},
            {'rank': 2, 'title': 'Bài Ba Người', 'artist': 'A, B & C', 'songwriter': 'X & Y', 'year': 2011},
            {'rank': 3, 'title': '3107', 'artist': 'W/n', 'songwriter': 'Nhiều nhạc sĩ', 'year': 2011},
            {'rank': 4, 'title': 'Một Vòng Trái Đất', 'artist': 'Tim & Minh Hằng', 'songwriter': 'Nhất Trung', 'year': 2010}]},
        {'period': '2026-present', 'songs': [{'rank': 1, 'title': 'Bài Mới', 'artist': 'Emcee L (Da LAB)', 'songwriter': 'Emcee L', 'year': 2026}]}]})
    new = songlist.load(new_path)
    first = {s['title']: s for s in new[0]['songs']}
    expect([(p['name'], p['slug'], p['label']) for p in new] == [('Giai đoạn 2010–2011', '2010-2011', '2010–2011'),
                                                               ('Giai đoạn 2026–nay', '2026-nay', '2026–nay')],
           f'đọc giai đoạn kiểu mới sai: {[(p["name"], p["slug"], p["label"]) for p in new]}')
    expect(new[0]['duplicates'] == 1 and first['Một Vòng Trái Đất']['artists'] == ['Tim', 'Minh Hằng']
           and first['Bài Ba Người']['artists'] == ['A', 'B', 'C'] and first['Bài Ba Người']['composers'] == ['X', 'Y']
           and first['3107']['artists'] == ['W/n'] and first['3107']['composers'] == [] and first['3107']['year'] == 2011
           and new[1]['songs'][0]['artists'] == ['Emcee L (Da LAB)'],
           f'tách tên ca sĩ, nhạc sĩ kiểu mới sai: {new[0]["songs"]}')
    expect(songlist.find_period(new, '2026-present')['slug'] == '2026-nay' and songlist.find_period(new, '2026-nay')['slug'] == '2026-nay',
           'giai đoạn mở phải gọi được bằng 2026-present và 2026-nay')
    # an earlier video's key names the singer the old list put first
    swapped = songlist.draw(new, {songlist.song_key('Một Vòng Trái Đất', ['Minh Hằng'])}, 7, 2, '2010-2011')
    expect(swapped['fresh'] == 2 and swapped['songs'][-1]['title'] == 'Một Vòng Trái Đất',
           f'bài song ca đã dùng (ca sĩ đổi thứ tự) phải xếp sau: {[x["title"] for x in swapped["songs"]]}')
    try:
        write_json(lab.tmp / 'bad.json', {'songs': []})
        songlist.load(lab.tmp / 'bad.json')
        expect(False, 'danh sách sai kiểu phải bị từ chối')
    except Exception as exc:  # noqa: BLE001
        expect(getattr(exc, 'code', None) == 2, f'danh sách sai kiểu phải là lỗi cách dùng: {exc}')
    d1 = songlist.draw(periods, set(), 42, 3)
    d2 = songlist.draw(periods, set(), 42, 3)
    expect(d1 == d2, 'cùng seed, cùng lịch sử phải ra cùng lần bốc')
    expect([x['position'] for x in d1['songs']] == list(range(1, len(d1['songs']) + 1)), 'vị trí phải là 1..M')
    by_seed = {songlist.draw(periods, set(), seed, 3)['slug'] for seed in range(1, 40)}
    expect(by_seed == {'2010-2014', '2015-2019'}, f'bốc giai đoạn phải ra cả hai giai đoạn: {by_seed}')
    named = songlist.draw(periods, set(), 7, 3, '2010–2014')
    expect(named['slug'] == '2010-2014' and len(named['songs']) == 20, 'chọn giai đoạn theo tên phải được')
    try:
        songlist.draw(periods, set(), 7, 3, '1990-1999')
        expect(False, 'giai đoạn không có phải bị từ chối')
    except Exception as exc:  # noqa: BLE001
        expect(getattr(exc, 'code', None) == 2, f'giai đoạn lạ phải là lỗi cách dùng: {exc}')
    used = {x['key'] for x in named['songs'][:17]}
    again = songlist.draw(periods, used, 7, 3, '2010-2014')
    expect({x['key'] for x in again['songs'][:3]}.isdisjoint(used) and again['fresh'] == 3 and not again['notes'],
           'bài video trước đã dùng phải xếp sau cùng')
    worn = songlist.draw(periods, {x['key'] for x in named['songs']}, 7, 3, '2010-2014')
    expect(worn['fresh'] == 0 and worn['notes'] and len(worn['songs']) == 20, 'giai đoạn đã dùng hết phải báo và vẫn bốc')
    expect(len(songlist.draw(periods, set(), 7, 3, '2010-2014', pool=5)['songs']) == 5, 'giới hạn pool')
    cfg = lab.config('drawws')
    ws = Path(cfg['_workspace'])
    (ws / 'r1').mkdir()
    songlist.record(cfg, 'r1', named['songs'][:3])
    expect(songlist.used_keys(cfg) == {x['key'] for x in named['songs'][:3]} and not songlist.used_keys(cfg, exclude_run='r1'),
           'sổ bài đã dùng sai')
    shutil.rmtree(ws / 'r1')
    expect(not songlist.used_keys(cfg), 'xoá thư mục lượt chạy thì trả bài của nó lại')
    return 'đọc cả hai kiểu danh sách và bỏ trùng, bốc theo seed, chọn giai đoạn, bài cũ xếp sau, báo khi hết bài mới, sổ bài đã dùng'


def t_init(lab: Lab):
    """`init` draws once, stores the draw with the downloader (no request to NCT), and an
    unfinished run is continued, never drawn again."""
    if not lab.root:
        raise Skip('cần --root (repo NCT thật cho lệnh songs, preflight)')
    cfg = lab.config('initws')
    code, out = pipeline('init', '--config', cfg['_path'], '--period', '2015-2019', '--seed', '7')
    expect(code == 0 and not out.get('resumed') and out['period'] == 'Giai đoạn 2015–2019' and len(out['drawn']) == 3,
           f'init phải bốc giai đoạn 2015–2019: {code} {str(out)[:400]}')
    run = Path(out['run'])
    rep = read_json(run / 'nct' / 'report.json')
    pick = read_json(run / 'songlist' / 'pick.json')
    expect(run.name.endswith('_lofi-ballad-2015-2019') and rep['run']['input'] == 'song_list'
           and [x['title'] for x in rep['songs']] == [x['title'] for x in pick['songs']] and len(rep['songs']) == 15,
           f'lượt NCT phải giữ đúng thứ tự bốc: {rep["run"]} {len(rep["songs"])}')
    st = State.load(run)
    expect(st.stage('chart')['status'] == 'done' and not [c for c in st.data['nct_commands'] if c['live']],
           f'init không được gửi request nào tới NCT: {st.data["nct_commands"]}')
    code, out2 = pipeline('init', '--config', cfg['_path'])
    expect(code == 0 and out2.get('resumed') and out2['run'] == str(run), f'lượt dở phải được chạy tiếp, không bốc lại: {out2}')
    code, out3 = pipeline('init', '--config', cfg['_path'], '--new', '--seed', '7', '--period', '2015-2019')
    expect(code == 0 and out3['run'] != str(run) and out3['drawn'] == out['drawn'], f'--new với cùng seed phải ra cùng lần bốc: {out3}')
    return f'bốc {out["period"]} (seed 7) thành lượt NCT kiểu danh sách, không request; init lại thì chạy tiếp lượt dở'


def _picture(path: Path, source: str) -> Path:
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', source, '-frames:v', '1', str(path)],
                   check=True)
    return path


def t_scene(lab: Lab):
    """Scenes: no combination twice, the place unlike the last few videos, the same answer for
    the same history; a picture like an earlier video's fails `art_unique`."""
    cfg = lab.config('scenews')
    history = {'entries': []}
    seq = []
    for i in range(40):
        got = scenery.choose(cfg, f'sim{i:03d}', history)
        seq.append(got)
        history['entries'].append({'run': f'sim{i:03d}', **{a: got[a] for a in scenery.AXES}, 'key': got['key'], 'at': 1000 + i})
    keys = [c['key'] for c in seq]
    gap = cfg['cover']['scene_place_gap']
    expect(len(set(keys)) == 40, f'40 video phải là 40 tổ hợp cảnh khác nhau: {len(set(keys))}')
    for i, c in enumerate(seq):
        expect(c['place'] not in {seq[j]['place'] for j in range(max(0, i - gap), i)}, f'video {i}: nơi chốn {c["place"]} lặp lại quá gần')
    expect({c['side'] for c in seq} == {'left', 'right'}, 'bên đặt điểm nhấn phải đổi')
    expect(scenery.choose(cfg, 'sim005', {'entries': history['entries'][:5]})['key'] == seq[5]['key'], 'cùng lịch sử phải ra cùng cảnh')
    first = scenery.choose(cfg, 'x', history)
    other = scenery.choose(cfg, 'x', history, rejected=[first['key']], offset=1)
    expect(other['key'] != first['key'] and other['seed'] != first['seed'], 'redo phải đổi cả cảnh lẫn seed')
    carry = {**{a: seq[3][a] for a in scenery.AXES}, 'key': seq[3]['key'], 'side': 'left', 'seed': 99, 'run': 'sim003'}
    kept = scenery.choose(cfg, 'y', history, carry=carry)
    expect(kept['key'] == seq[3]['key'] and kept['seed'] == 99, 'lượt làm lại phải giữ cảnh và seed của lượt gốc')
    text = scenery.scene_text(seq[0])
    blocked = ('child', 'kid', 'teen', 'minor', 'girl', 'woman', 'person', 'people')
    words = {w.strip('.,') for it in (it for a in scenery.AXES for it in scenery.catalog()[a]) for w in it['text'].lower().split()}
    expect(not words & set(blocked), f'danh mục cảnh có chữ bị chặn hoặc nhắc tới người: {words & set(blocked)}')
    expect(text.count(',') >= 3, f'câu cảnh phải gồm 4 phần: {text}')
    # art_unique against approved pictures of other runs
    ws = Path(cfg['_workspace'])

    def run_with(name, source):
        (ws / name / 'art').mkdir(parents=True, exist_ok=True)
        return _picture(ws / name / 'art' / 'raw.png', source).parent.parent

    a = run_with('vid-a', 'testsrc2=size=640x360')
    expect(scenery.unique_check(a, cfg)['status'] == 'PASS', 'chưa có video nào thì PASS')
    scenery.approve(cfg, a)
    expect((ws / 'art_history' / 'vid-a.jpg').is_file() and scenery.load_history(cfg)['entries'][-1]['status'] == 'approved',
           'duyệt ảnh phải lưu bản nhỏ và ghi approved')
    b = run_with('vid-b', 'testsrc2=size=640x360')
    expect(scenery.unique_check(b, cfg)['status'] == 'FAIL', 'ảnh giống hệt video trước phải FAIL')
    c = run_with('vid-c', 'testsrc2=size=640x360,hue=h=20,eq=brightness=0.03')
    got_c = scenery.unique_check(c, cfg)
    expect(got_c['status'] == 'FAIL', f'ảnh gần giống video trước phải FAIL: {got_c}')
    d = run_with('vid-d', 'mandelbrot=size=640x360')
    got_d = scenery.unique_check(d, cfg)
    expect(got_d['status'] == 'PASS', f'ảnh khác hẳn phải PASS: {got_d}')
    expect(scenery.unique_check(b, cfg, {'carried_from': str(a)})['status'] == 'PASS', 'lượt làm lại từ vid-a được giữ đúng tranh đó')
    scenery.mark_rendered(cfg, 'vid-a')
    expect(scenery.load_history(cfg)['entries'][-1]['status'] == 'rendered', 'render xong phải ghi rendered')
    data = scenery.preset_data(cfg, {**seq[0], 'side': 'right'})
    expect(data['extends'] == 'lofi' and data['image']['scene'] == text and data['layout']['default_side'] == 'right', f'{data}')
    return (f'40 cảnh khác nhau, nơi chốn khác {gap} video gần nhất, redo đổi cảnh và seed, giữ cảnh khi làm lại; '
            f'ảnh trùng và gần giống FAIL ({got_c["detail"][:40]}…), ảnh khác PASS')


def t_scene_render(lab: Lab):
    """The scene reaches m10-mixcover through the run's own preset (checked with --print-prompt,
    no image call), and a picture an earlier video used stops the run and cannot be approved."""
    if not lab.root:
        raise Skip('cần repo m10-mixcover (--root)')
    cfg = lab.config('scenerender')
    run = Path(cfg['_workspace']) / 'scene-run'
    checks, info = scenery.pick(run, cfg, {})
    expect(status_of(checks, 'scene') == 'PASS' and Path(info['preset']).is_file(), f'chọn cảnh: {checks}')
    mc = Path(cfg['repos']['mixcover'])
    csv = lab.tmp / 'one.csv'
    csv.write_text('artist,title\nA,B\n', encoding='utf-8')
    done = subprocess.run([str(mc / '.venv' / 'bin' / 'python'), str(mc / 'main.py'), str(csv), '--preset', info['preset'], '--print-prompt'],
                          cwd=str(mc), capture_output=True, text=True, timeout=120)
    expect(done.returncode == 0 and info['scene'] in done.stdout and 'The woman' not in done.stdout and 'No people' in done.stdout
           and (('left third' if info['side'] == 'left' else 'right third') in done.stdout),
           f'mixcover phải nhận cảnh của lượt, không có câu về người: {done.returncode} {(done.stdout + done.stderr)[-500:]}')
    # the same picture for two videos: the second one stops with art_unique FAIL and "ok" is refused
    pic = _picture(lab.tmp / 'same.png', 'testsrc2=size=1792x1008')
    cfg2 = lab.config('uniquews', cover={'review': True, 'dry_run': False, 'image': str(pic)})
    a, b = lab.source('u1.wav'), lab.source('u2.wav')
    rep = lab.report({1: ('file', a), 2: ('file', b)})
    first = lab.run_dir(cfg2, rep, 2, 'first-video')
    code, out = pipeline('run', '--run', first, '--until', 'art')
    expect(code == 10 and out.get('stage') == 'art', f'lượt đầu phải dừng ở S3: {code} {str(out)[:300]}')
    code, out = pipeline('decide', '--run', first, '--art', 'ok')
    expect(code == 0, f'lượt đầu duyệt được: {code} {out}')
    second = lab.run_dir(cfg2, rep, 2, 'second-video')
    code, out = pipeline('run', '--run', second, '--until', 'art')
    expect(code == 10 and 'art_unique' in out.get('waiting', '') and 'LỖI' in out.get('waiting', ''),
           f'tranh trùng video trước phải được nêu ở S3: {code} {str(out)[:400]}')
    code, out = pipeline('decide', '--run', second, '--art', 'ok')
    expect(code == 2 and 'art_unique' in out.get('error', ''), f'không được duyệt tranh trùng: {code} {out}')
    # cover.review off (the default): the model's picture is taken without asking and joins the history;
    # a picture that repeats an earlier video's still stops the run
    expect(cfgmod.DEFAULTS['cover']['review'] is False, 'cover.review mặc định phải tắt')
    pic3 = _picture(lab.tmp / 'auto.png', 'mandelbrot=size=1792x1008')
    cfg3 = lab.config('autows', cover={'review': False, 'dry_run': False, 'image': str(pic3)})
    one = lab.run_dir(cfg3, rep, 2, 'auto-first')
    code, out = pipeline('run', '--run', one, '--until', 'art')
    st = State.load(one)
    hist = read_json(Path(cfg3['_workspace']) / 'art_history.json') or {}
    expect(code == 0 and status_of(st.stage('art')['checks'], 'art_review') == 'PASS' and st.data['decisions'].get('art_approved')
           and (Path(cfg3['_workspace']) / 'art_history' / 'auto-first.jpg').is_file()
           and [e.get('status') for e in hist.get('entries', []) if e.get('run') == 'auto-first'] == ['approved'],
           f'cover.review tắt: phải nhận ảnh, không dừng, ghi vào lịch sử tranh: {code} {str(out)[:300]} {hist}')
    two = lab.run_dir(cfg3, rep, 2, 'auto-second')
    code, out = pipeline('run', '--run', two, '--until', 'art')
    expect(code == 10 and 'art_unique' in out.get('waiting', '') and not State.load(two).data['decisions'].get('art_approved'),
           f'cover.review tắt: tranh trùng video trước vẫn phải dừng: {code} {str(out)[:400]}')
    return ('preset của lượt đưa cảnh vào prompt (không câu về người, đúng bên); tranh trùng video trước dừng ở S3 và không duyệt được; '
            'cover.review tắt thì nhận ảnh không hỏi, tranh trùng vẫn dừng')


def good_meta(run: Path) -> dict:
    lines = youtube.chapter_lines(run)
    man = read_json(run / 'manifest.json')
    credits = '\n'.join(f'{i}. {t["title"]} – {t["artist"]}' for i, t in enumerate(cover.playlist_tracks(man), 1))
    desc = ('Ballad lofi Việt nhẹ nhàng để thư giãn, học bài và ngủ ngon.\nNghe trọn bản mix ballad lofi chill của M10 lofi chill.\n\n'
            'Tracklist:\n' + '\n'.join(lines) + '\n\nBài gốc và nghệ sĩ:\n' + credits +
            '\n\nNhạc nền lofi do AI tạo, giọng hát giữ nguyên từ bản gốc; tranh phong cảnh do AI vẽ.\n\n#balladlofi #lofichill')
    form = {k: {'value': 'Có' if k == 'altered_content' else 'x', 'why': 'y'} for k in youtube.FORM_KEYS}
    scores = {k: 4 for k in youtube.SCORE_KEYS}
    return {'primary_keyword': 'ballad lofi', 'secondary_keywords': ['lofi chill'],
            'titles': [{'text': '5 Bản Ballad Lofi Chill Nhẹ Nhàng | M10 lofi chill', 'angle': 'số bài', 'scores': scores, 'why': 'rõ'},
                       {'text': 'Ballad Lofi Việt Thư Giãn – Mix Liền Mạch', 'angle': 'thời gian', 'scores': scores, 'why': 'rõ'},
                       {'text': 'Ballad Lofi Chill Cho Đêm Mưa', 'angle': 'cảm xúc', 'scores': scores, 'why': 'rõ'}],
            'description': desc, 'tags': ['ballad lofi', 'lofi chill', 'ballad việt', 'nhac lofi', 'm10 lofi chill'],
            'hashtags': ['#balladlofi', '#lofichill'],
            'form': form, 'pinned_comment': 'Bạn thích bài nào nhất trong mix?', 'playlist': 'Ballad Việt Lofi – M10 lofi chill'}


def t_metadata(lab: Lab):
    cfg, run, manifest = mix_run(lab, 'meta-run')
    mix.build(run, cfg, None, manifest)
    write_json(run / 'nct' / 'report.json', read_json(FIXTURE))
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
            ('title_length', lambda m: m['titles'][0].update(text='Ballad lofi ' + 'x' * 95), None),
            ('description_length', lambda m: m.update(description=m['description'] + '\n' + 'nhạc điện tử ' * 260), None),   # < 5000 chars, > 5000 bytes
            ('chapter_rules', None, late_start(base_mix)),
            ('chapter_rules', None, short_chapter(base_mix)),
            ('count_claims', lambda m: m['titles'][0].update(text='Top 5 Ballad Lofi Việt Hay Nhất'), None),
            ('count_claims', lambda m: m['titles'][1].update(text='7 bài ballad lofi nghe là nhớ'), None),
            ('search_volume_claims', lambda m: m.update(description=m['description'] + '\n50.000 lượt tìm kiếm mỗi tháng'), None),
            ('banned_phrases', lambda m: m['tags'].append('nhạc no copyright'), None),
            ('banned_phrases', lambda m: m['titles'][2].update(text='Ballad Lofi Việt (Official Audio)'), None),
            ('banned_phrases', lambda m: m['hashtags'].append('#EDM'), None),
            ('banned_phrases', lambda m: m['titles'][2].update(text='Ballad Lofi Remix Cực Chill'), None),
            ('banned_phrases', lambda m: m['tags'].append('vinahouse'), None),
            ('banned_phrases', lambda m: m.update(description=m['description'] + '\nTuyển chọn từ BXH ballad.'), None),
            ('tags_artists', lambda m: m['tags'].append('Hiền Thục'), None),
            ('description_credits', lambda m: m.update(description=m['description'].replace('Ca sĩ 3', 'ai đó')), None),
            ('description_chapters', lambda m: m.update(description=m['description'].replace('00:00 ', '00:01 ')), None),
            ('ai_disclosure', lambda m: m.update(description=m['description'].replace('AI', 'máy')), None),
            ('ai_disclosure', lambda m: m.update(description=m['description'].replace('Nhạc nền lofi do AI tạo', 'Nhạc nền không dùng AI')), None),
            ('ai_disclosure', lambda m: m['form']['altered_content'].update(value='Không'), None),
            ('count_claims', lambda m: m['tags'].append('top 5 ballad lofi'), None),
            ('count_claims', lambda m: m['hashtags'].append('#top5lofi'), None),
            ('count_claims', lambda m: m.update(description=m['description'] + '\nTop 5 bản ballad hay nhất tuần'), None),
            ('tags_artists', lambda m: m['tags'].append('Hiền Thục lofi'), None),
            ('description_credits', lambda m: m.update(description=m['description'].replace('Bài 2 – Ca sĩ 2', 'Bài 2').replace('Ca sĩ 2 - Bài 2', 'Bài 2')), None),
            ('tags_unique', lambda m: m['tags'].append('BALLAD LOFI'), None),
            ('title_keyword', lambda m: m['titles'][0].update(text='5 Bản Nhạc Chill Nhẹ Nhàng Cho Đêm Mưa'), None),
        ]
        for name, change, mixinfo in cases:
            got = verdict(change, mixinfo)
            expect(status_of(got, name) == 'FAIL', f'mẫu sai phải FAIL ở {name}: {[c for c in got if c["name"] == name]}')
        ranked = copy.deepcopy(read_json(run / 'manifest.json'))
        ranked['exact_top'] = True                                  # even a manifest that says so: a draw is never a ranking
        write_json(run / 'manifest.json', ranked)
        named = verdict(lambda m: m['titles'][0].update(text='Top 5 Ballad Lofi Việt'))
        expect(status_of(named, 'count_claims') == 'FAIL', f'"Top 5" luôn FAIL với danh sách bốc ngẫu nhiên: {named}')
        two = copy.deepcopy(base_mix)
        two['chapters'] = two['chapters'][:2]
        expect(status_of(verdict(None, two), 'chapter_rules') == 'WARN', 'mix dưới 3 mốc: YouTube không tạo chapter, là WARN chứ không FAIL')
        expect(status_of(good, 'evidence') == 'WARN', 'bằng chứng không có video YouTube nào phải là WARN')
        tube = {**evidence, 'queries': [{'query': f'q{i}', 'results': [{'title': 't', 'url': 'https://www.youtube.com/watch?v=x'}]} for i in range(3)]}
        expect(status_of(verdict(ev=tube), 'evidence') == 'PASS', 'bằng chứng có video YouTube phải PASS')
        rules = youtube.load_rules
        youtube.load_rules = lambda: None
        try:
            expect(status_of(verdict(), 'banned_phrases') == 'FAIL', 'thiếu metadata_rules.json thì không được PASS rỗng')
        finally:
            youtube.load_rules = rules
        inexact = copy.deepcopy(read_json(run / 'manifest.json'))
        inexact['exact_top'] = False
        write_json(run / 'manifest.json', inexact)
        got = verdict(lambda m: m['titles'][0].update(text='Top 5 Ballad Lofi Việt'))
        expect(status_of(got, 'count_claims') == 'FAIL', '"Top 5" phải FAIL')
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
    cfg['mix']['overlap_bars'] = 1                         # below the 2 voiceless bars kept at each side: a different mix
    cfgmod.save(cfg)
    code, out = pipeline('run', '--run', run)
    ran = [r['stage'] for r in out.get('ran', [])]
    expect(ran == ['preflight', 'mix', 'cover', 'video'] and lab.fake.created == made, f'đổi đầu vào của mix phải làm lại mix, cover, video: {ran}')
    ydir = run / 'youtube'
    ydir.mkdir(exist_ok=True)
    meta = good_meta(run)
    meta['titles'][0]['text'] = '3 Bản Ballad Lofi Chill Nhẹ Nhàng | M10 lofi chill'
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
    expect(code == 10 and 'bài số 2' in out.get('waiting', ''), f'bài phối lỗi phải dừng hỏi: {code} {out}')
    expect(sum(1 for p in (run2 / 'remix').glob('*/verify.json')) == 2, 'các bài tốt phải vẫn được phối xong')
    tries = sum(j['runs'] for j in lab.fake.jobs.values())
    code, out = pipeline('run', '--run', run2, '--until', 'remix')
    expect(code == 10 and 'bài số 2' in out.get('waiting', '') and sum(j['runs'] for j in lab.fake.jobs.values()) == tries,
           f'chạy lại khi chưa trả lời phải hỏi lại, không tự thử lại: {code} {out}')
    pipeline('decide', '--run', run2, '--remix-failed', 'skip')
    code, out = pipeline('run', '--run', run2, '--until', 'mix')
    man = read_json(run2 / 'manifest.json')
    expect(code == 0 and [t['rank'] for t in man['tracks']] == [1, 3], f'skip phải bỏ bài số 2: {code} {out}')

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


def t_source_tempo(lab: Lab):
    """remix.target_bpm = "source": StemForge measures each song, the job is switched to the
    song's own tempo (doubled or halved towards source_center_bpm), nothing is stretched, and
    two tempos meet in a planned crossfade."""
    if not lab.root:
        raise Skip('cần --root (preflight, preset StemForge, mixcover thật)')
    from rcvlib import stemforge
    expect(stemforge.pick_target(171.995, 128) == 172.0 and stemforge.pick_target(89.524, 128) == 179.05
           and stemforge.pick_target(240, 128) == 120.0, 'pick_target chọn sai bội số')
    a, b = lab.source('st1_bpm100.wav'), lab.source('st2_bpm172.wav')
    cfg = lab.config('srcws', remix={'target_bpm': 'source', 'source_center_bpm': 128})
    run = lab.run_dir(cfg, lab.report({1: ('file', a), 2: ('file', b)}), 2, 'source-run')
    made = lab.fake.created
    code, out = pipeline('run', '--run', run, '--until', 'mix')
    expect(code == 0, f'chế độ giữ tốc độ gốc phải chạy tới mix: {code} {out}')
    expect(lab.fake.created == made + 2 and lab.fake.create_targets[-2:] == ['auto', 'auto'],
           f'mỗi bài một job, bắt đầu ở auto để đo tempo: {lab.fake.create_targets[-2:]}')
    jobs = {p.parent.name[:3]: read_json(p) for p in (run / 'remix').glob('*/job.json')}
    expect(jobs['r01']['target_bpm'] == 100.0 and jobs['r02']['target_bpm'] == 172.0,
           f'nhịp nền phải là tempo gốc: {[(k, v.get("target_bpm")) for k, v in sorted(jobs.items())]}')
    for p in (run / 'remix').glob('*/remix_report.json'):
        expect(abs(read_json(p)['tempo']['tempo_ratio'] - 1.0) < 1e-3, f'{p.parent.name}: giọng bị co giãn')
        expect(read_json(p.parent / 'source_tempo.json')['bpm'] in (100.0, 172.0), 'thiếu source_tempo.json')
    st = State.load(run)
    rchecks = {c['name']: c for c in st.stage('remix')['checks']}
    expect(all('vocal_stretch' not in c['detail'] for c in rchecks.values()), 'không được có WARN vocal_stretch')
    expect(rchecks['source_tempo_range']['status'] == 'WARN' and '172' in rchecks['source_tempo_range']['detail'],
           f'phải nêu bài ngoài khoảng tempo của preset: {rchecks.get("source_tempo_range")}')
    tr = {c['name']: c for c in st.stage('mix')['checks']}['transition_1_2']
    expect(tr['status'] == 'PASS' and 'giữ tempo gốc' in tr['detail'], f'hai tempo phải nối bằng crossfade đã định: {tr}')

    # a known tempo (an earlier measurement, or the report a --from-run copied) skips the "auto" start
    cfg['remix']['source_center_bpm'] = 150
    cfgmod.save(cfg)
    made = lab.fake.created
    code, out = pipeline('run', '--run', run, '--until', 'remix')
    expect(code == 0 and lab.fake.create_targets[-2:] == [200.0, 172.0],
           f'tempo đã biết phải tạo job thẳng ở nhịp gốc: {code} {lab.fake.create_targets[-2:]}')
    tdir = lab.tmp / 'carried'
    tdir.mkdir()
    write_json(tdir / 'remix_report.json', {'source': {'bpm': 171.995, 'duration': 293.2}})
    expect(stemforge.known_source_bpm(tdir, {'source': {'sha256': 'x', 'duration': 293.19}}) == 171.995
           and stemforge.known_source_bpm(tdir, {'source': {'sha256': 'x', 'duration': 250.0}}) is None,
           'tempo trong remix_report.json chép sang chỉ dùng khi độ dài bài nguồn khớp')
    return 'đo tempo rồi đổi job sang nhịp gốc, không co giãn, crossfade giữa hai tempo, nêu bài ngoài khoảng preset, dùng lại tempo đã đo'


def t_backing_tempo(lab: Lab):
    """A backing StemForge generated off the requested tempo is a FAIL. In "source" mode the job
    is re-queued at the song's own tempo one octave over; a remix verified before the check is
    checked again and redone; when every octave misses, the run stops for the human."""
    if not lab.root:
        raise Skip('cần --root (preflight, preset StemForge, mixcover thật)')
    from rcvlib import stemforge
    expect(stemforge.pick_target(89.524, 128, avoid=[179.05]) == 89.52, 'pick_target phải bỏ tempo đã trượt')
    rep = {'tempo': {'target_bpm': 179.05},
           'generation': {'chosen': {'strategy': 'cover', 'validation': {'measured_bpm': 134.26, 'bpm_ok': False}}}}
    expect(stemforge.backing_tempo_check(rep)['status'] == 'FAIL', 'nhạc nền trượt tempo phải FAIL')
    rep['generation']['chosen']['strategy'] = 'text2music'
    expect(stemforge.backing_tempo_check(rep)['status'] == 'PASS', 'text2music được StemForge co giãn về đúng tempo')
    expect(stemforge.backing_tempo_check({})['status'] == 'SKIP', 'không có số đo thì SKIP')

    a, b = lab.source('bk1_bpm90_miss150.wav'), lab.source('bk2_bpm90_miss80.wav')
    cfg = lab.config('bkws', remix={'target_bpm': 'source', 'source_center_bpm': 128})
    run = lab.run_dir(cfg, lab.report({1: ('file', a), 2: ('file', b)}), 2, 'backing-run')
    made = lab.fake.created
    code, out = pipeline('run', '--run', run, '--until', 'remix')
    expect(code == 10 and 'bài số 2' in out.get('waiting', ''), f'trượt cả hai quãng tám phải dừng hỏi: {code} {out}')
    expect(lab.fake.created == made + 2, f'đổi quãng tám phải dùng lại job: tạo {lab.fake.created - made} job')
    d1, d2 = sorted(p for p in (run / 'remix').iterdir() if p.is_dir())
    j1, j2 = read_json(d1 / 'job.json'), read_json(d2 / 'job.json')
    expect(j1['status'] == 'verified' and j1['target_bpm'] == 90.0 and j1.get('tried_bpm') == [180.0],
           f'180 BPM trượt thì phải phối ở 90 BPM, vẫn tốc độ gốc: {j1}')
    v1 = {c['name']: c for c in read_json(d1 / 'verify.json')['checks']}
    expect(v1['backing_tempo']['status'] == 'PASS' and v1['source_tempo']['status'] == 'PASS', f'{v1.get("backing_tempo")}')
    expect(j2['status'] == 'failed' and sorted(j2.get('tried_bpm') or []) == [90.0, 180.0] and 'đã thử' in j2.get('error', ''),
           f'bài trượt cả hai quãng tám phải ghi đã thử những tempo nào: {j2}')

    # a remix verified by a skill without this check (here: at 180 BPM, backing off) is redone
    runs = lab.fake.jobs[j1['job_id']]['runs']
    old = read_json(d1 / 'remix_report.json')
    old['tempo']['target_bpm'] = 180.0
    old['generation']['chosen']['validation'].update(bpm_ok=False, measured_bpm=135.0)
    write_json(d1 / 'remix_report.json', old)
    write_json(d1 / 'job.json', {k: v for k, v in {**j1, 'target_bpm': 180.0}.items() if k != 'tried_bpm'})
    pipeline('decide', '--run', run, '--remix-failed', 'skip')
    code, out = pipeline('run', '--run', run, '--until', 'remix')
    j1 = read_json(d1 / 'job.json')
    expect(code == 0 and j1['status'] == 'verified' and j1['target_bpm'] == 90.0 and j1.get('tried_bpm') == [180.0]
           and lab.fake.jobs[j1['job_id']]['runs'] == runs + 1 and lab.fake.created == made + 2,
           f'bản phối cũ có nhạc nền trượt tempo phải được phối lại ở quãng tám kia, cùng job: {code} {j1}')
    # "retry" for a remix that finished but failed its checks: a new job, not the same file again
    c = lab.source('bk3_bpm100_miss120.wav')
    cfg2 = lab.config('bkfixed', remix={'target_bpm': 128})
    run2 = lab.run_dir(cfg2, lab.report({1: ('file', c)}), 1, 'fixed-run')
    code, out = pipeline('run', '--run', run2, '--until', 'remix')
    expect(code == 10 and 'backing_tempo' in out.get('waiting', ''), f'nhạc nền trượt ở tempo cố định phải dừng hỏi: {code} {out}')
    made = lab.fake.created
    code, out = pipeline('decide', '--run', run2, '--remix-failed', 'retry')
    expect(code == 0, f'decide retry: {code} {out}')
    code, out = pipeline('run', '--run', run2, '--until', 'remix')
    expect(code == 10 and lab.fake.created == made + 1, f'retry sau khi bản phối trượt phép kiểm phải tạo job mới: tạo {lab.fake.created - made}')
    return 'nhạc nền trượt tempo là FAIL, tự thử quãng tám kia, phối lại bản cũ chưa được kiểm, dừng hỏi khi trượt cả hai, retry tạo job mới'


def t_stall(lab: Lab):
    """A job that stops moving is cancelled, waited for and retried; one that never stops
    becomes a failed remix the human decides about. The other songs are still remixed."""
    if not lab.root:
        raise Skip('cần --root (preflight thật)')
    a, b, c = lab.source('q1.wav'), lab.source('q2_stuck.wav'), lab.source('q3_hung.wav')
    cfg = lab.config('stallws', remix={'stall_s': 1.5, 'cancel_wait_s': 2.5})
    run = lab.run_dir(cfg, lab.report({1: ('file', a), 2: ('file', b), 3: ('file', c)}), 3, 'stall-run')
    code, out = pipeline('run', '--run', run, '--until', 'remix')
    jobs = [read_json(p) for p in sorted((run / 'remix').glob('*/job.json'))]
    expect(code == 10 and 'bài số 3' in out.get('waiting', '') and 'bài số 2' not in out['waiting'].splitlines()[0],
           f'job đứng không dừng được phải thành bài phối lỗi (exit 10), không làm hỏng cả chặng: {code} {out}')
    expect([j['status'] for j in jobs] == ['verified', 'verified', 'failed'] and jobs[1]['attempts'] == 2
           and jobs[2]['error_type'] == 'stalled', f'bài đứng phải được huỷ, chờ dừng rồi thử lại: {jobs}')
    return 'job đứng: huỷ, chờ dừng hẳn, thử lại; job không dừng: thành bài phối lỗi, các bài khác vẫn xong'


def t_decide(lab: Lab):
    """`decide` answers a question the run is waiting with. It never changes a finished run,
    never answers a question nobody asked, and never writes while a stage is running."""
    cfg = lab.config('decidews')
    run = lab.run_dir(cfg, lab.report({}), 2, 'decide-run')
    code, out = pipeline('decide', '--run', run, '--missing', 'skip')
    st = State.load(run)
    expect(code == 2 and st.data['decisions'] == {} and st.stage('originals')['status'] == 'todo', f'không có gì đang chờ thì decide phải từ chối: {code} {out}')
    st.start('originals')
    st.wait('originals', 'thiếu bài')
    with RunLock(run):                                       # a stage is running
        code, out = pipeline('decide', '--run', run, '--missing', 'skip')
    expect(code == 2 and State.load(run).data['decisions'] == {}, f'đang có tiến trình chạy thì decide phải từ chối: {code} {out}')
    code, out = pipeline('decide', '--run', run, '--missing', 'skip')
    expect(code == 0 and State.load(run).data['decisions'].get('missing_action') == 'skip', f'đang chờ thì decide phải ghi: {code} {out}')
    st = State.load(run)
    for sid in STAGE_IDS:
        st.start(sid)
        st.finish(sid, [])
    code, out = pipeline('decide', '--run', run, '--art', 'redo')
    expect(code == 2 and State.load(run).finished() and '--from-run' in out.get('error', ''), f'lượt đã xong không được sửa: {code} {out}')
    return 'từ chối khi không có gì chờ, khi đang chạy, khi lượt đã xong; ghi khi đang chờ'


def t_set(lab: Lab):
    """`set` refuses a value of the wrong type instead of saving a config no command can load."""
    cfg = lab.config('setws')
    path = cfg['_path']
    for key, value in (('nct.interval_s', '60s'), ('nct.interval_s', '5'), ('nct.live_access', 'True'), ('remix.target_bpm', '300'),
                       ('remix.source_center_bpm', '0'), ('video.look', 'both'), ('video.look', 'cover'), ('mix', '{}'), ('no.such', '1'),
                       ('songlist.pool', '60'), ('songlist.pool', '2.5'), ('cover.max_art_similarity', '1.5'), ('video.center', 'rotate')):
        code, out = pipeline('set', key, value, '--config', path)
        expect(code == 2, f'set {key} {value} phải bị từ chối: {code} {out}')
    expect(cfgmod.load(path)['nct']['interval_s'] == 60, 'config phải còn đọc được sau các lần set sai')
    for key, value in (('cover.image', '/tmp/x.png'), ('cover.dry_run', 'false'), ('cover.title', '2026'), ('mix.lead_in_bars', 'null'),
                       ('remix.target_bpm', 'source'), ('nct.live_access', 'true'), ('songlist.pool', '30'),
                       ('cover.max_art_similarity', '0.8'), ('songlist.path', '/tmp/ballads.json')):
        code, out = pipeline('set', key, value, '--config', path)
        expect(code == 0, f'set {key} {value} phải được nhận: {code} {out}')
    got = cfgmod.load(path)
    expect(got['cover']['title'] == '2026' and got['cover']['image'] == '/tmp/x.png' and got['mix']['lead_in_bars'] is None
           and got['nct']['live_access'] is True and got['cover']['dry_run'] is False, f'giá trị lưu sai: {got["cover"]}')
    return 'từ chối sai kiểu, sai khoảng, khoá lạ; nhận cover.image, cover.dry_run, chữ, null'


def t_guards(lab: Lab):
    """Small guards: a timed-out tool, an interrupt in the mix, a fade that would reach a voice."""
    from rcvlib import stemforge
    from rcvlib.common import run as run_cmd
    rc, out, err = run_cmd(['sh', '-c', 'echo hi; echo oops >&2; sleep 5'], timeout=0.5)
    expect(rc == 124 and isinstance(out, str) and isinstance(err, str) and 'timeout' in err, f'lệnh quá hạn phải trả 124 và chữ: {rc} {out!r} {err!r}')

    class Stopped:
        children: list = []

        def should_stop(self):
            return True
    try:
        mix.render([{'path': str(lab.tmp / 'gone.wav'), 'head': 0, 'end': 10, 'samples': 10}], [], lab.tmp / 'never.wav', Stopped())
        expect(False, 'ffmpeg bị dừng giữa chừng phải là Interrupted')
    except stemforge.Interrupted:
        pass

    def song(pos, bpm, lead_s, tail_s):
        n = 20 * RATE
        return {'position': pos, 'path': 'x', 'bpm': bpm, 'samples': n, 'head': 0, 'end': n, 'basis': 'vocals',
                'voice_start': int(lead_s * RATE), 'voice_stop': n - int(tail_s * RATE)}
    mx = dict(cfgmod.DEFAULTS['mix'], crossfade_s=4.0)
    full = mix.plan_transition(song(1, 172, 6, 6), song(2, 130, 6, 6), mx, own_tempo=True)
    short = mix.plan_transition(song(1, 172, 6, 6), song(2, 130, 2.8, 6), mx, own_tempo=True)
    none = mix.plan_transition(song(1, 172, 6, 0), song(2, 130, 6, 6), mx, own_tempo=True)
    expect(full['mode'] == 'crossfade' and full['ns'] == 4 * RATE, f'đủ chỗ thì crossfade 4 s: {full}')
    expect(short['mode'] == 'crossfade' and short['ns'] == int(2.8 * RATE) and 'rút còn' in short['detail'], f'crossfade không được phủ câu hát đầu: {short}')
    expect(none['mode'] == 'cut' and none['ns'] == 960, f'không còn đoạn không lời thì nối thẳng: {none}')
    same = mix.plan_transition(song(1, 128, 6, 0), song(2, 128, 6, 6), dict(mx, tail_bars=0), own_tempo=False)
    expect(same['mode'] == 'cut' and same['status'] == 'PASS', f'cùng tempo, không giữ ô nhịp không lời: nối thẳng, không crossfade qua giọng: {same}')
    return 'lệnh quá hạn trả 124; ngắt giữa lúc ghép là Interrupted; fade không bao giờ phủ giọng hát'


def t_from_run(lab: Lab):
    """A run made from a finished one keeps its own copy of the human's picture, carries the
    old answers, and is marked as a run that sends nothing to NCT."""
    if not lab.root:
        raise Skip('cần --root (preflight thật)')
    a, b = lab.source('c1.wav'), lab.source('c2.wav')
    cfg = lab.config('carryws')
    old = lab.run_dir(cfg, lab.report({1: ('file', a), 2: ('file', b)}), 2, 'old-run')
    (old / 'art').mkdir()
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=0x334455:s=640x360',
                    '-frames:v', '1', str(old / 'art' / 'raw.png')], check=True)
    write_json(old / 'art' / 'scene.json', {'place': 'hoi-an', 'time': 'dem-trang', 'weather': 'mua-nhe', 'detail': 'den-long',
                                            'key': 'hoi-an/dem-trang/mua-nhe/den-long', 'side': 'right', 'seed': 4242})
    st = State.load(old)
    st.data['decisions'] = {'art_image': str(lab.tmp / 'deleted-run' / 'art' / 'own_picture.png'), 'retry_token': 1.0}
    st.save()
    code, out = pipeline('init', '--from-run', old, '--config', cfg['_path'], '--name', 'new-run')
    expect(code == 0 and not out.get('resumed'), f'init --from-run: {code} {out}')
    new = Path(out['run'])
    dec = State.load(new).data['decisions']
    pic = Path(dec.get('art_image', ''))
    expect(pic.is_file() and pic.parent == new / 'art' and dec.get('carried_from') == str(old) and 'retry_token' not in dec,
           f'lượt mới phải giữ bản sao ảnh của riêng nó: {dec}')
    carried = dec.get('scene_carry') or {}
    expect(carried.get('key') == 'hoi-an/dem-trang/mua-nhe/den-long' and carried.get('seed') == 4242 and carried.get('run') == 'old-run',
           f'lượt mới phải giữ cảnh và seed của lượt cũ (cùng tranh): {dec}')
    expect((new / 'songlist' / 'pick.json').is_file(), 'lượt mới phải có bản sao danh sách bốc')
    shutil.rmtree(old)
    code, out = pipeline('run', '--run', new, '--until', 'originals')
    expect(code == 0 and Path(State.load(new).data['decisions']['art_image']).is_file(), f'xoá lượt cũ rồi lượt mới vẫn phải chạy: {code} {out}')
    return 'chép ảnh của người dùng và danh sách bốc sang lượt mới, mang theo câu trả lời cũ và cảnh, không phụ thuộc thư mục lượt cũ'


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


TESTS = {'help': t_help, 'draw': t_draw, 'init': t_init, 'selection': t_selection, 'ask_flow': t_ask_flow, 'art_review': t_art_review,
         'mix': t_mix, 'trim': t_trim, 'cover': t_cover, 'video': t_video, 'scene': t_scene, 'scene_render': t_scene_render,
         'metadata': t_metadata, 'resume': t_resume, 'source_tempo': t_source_tempo,
         'backing_tempo': t_backing_tempo, 'stall': t_stall, 'decide': t_decide, 'set': t_set, 'guards': t_guards,
         'from_run': t_from_run, 'pane': t_pane}


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
    tmp = Path(tempfile.mkdtemp(prefix='lofi_selftest_'))
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
    skipped = [r['test'] for r in results if r['status'] == 'SKIP']
    # A skipped test verified nothing: the summary says INCOMPLETE and the exit code is not 0.
    print(json.dumps({'worst': 'FAIL' if failed else 'INCOMPLETE' if skipped else 'PASS', 'skipped': skipped,
                      'root': str(root) if root else None, 'kept': str(tmp) if args.keep else None, 'tests': results},
                     ensure_ascii=False, indent=2))
    return 1 if failed else 3 if skipped else 0


if __name__ == '__main__':
    sys.exit(main())
