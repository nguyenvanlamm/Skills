#!/usr/bin/env python3
"""Run the remix-chart-to-video pipeline stage by stage, resumable, with a state file.

  pipeline.py init-config [--config FILE] [--root DIR]     write a config with the four repo paths
  pipeline.py set KEY VALUE [--config FILE]                save an answer, e.g. `set video.look cover`
  pipeline.py init [--config FILE] [--count N] [--nct-run-id ID | --html FILE] [--sequence 1,2,1] [--new]
                                                           preflight + chart, create or resume a run folder
  pipeline.py init --from-run OLD_RUN [--config FILE]      a new run that reuses OLD_RUN's songs and remixes
                                                           (no NCT request, no GPU): redo the mix, cover and video
  pipeline.py run --run DIR [--until STAGE] [--only STAGE] run the stages that are not done yet
  pipeline.py decide --run DIR --missing backfill|skip|manual
  pipeline.py decide --run DIR --remix-failed retry|skip|backfill
  pipeline.py decide --run DIR --art ok|redo|image [--path FILE]   answer the picture stop after stage `art`
  pipeline.py status --run DIR                             one JSON summary of the run
  pipeline.py stop --run DIR                               stop a StemForge server this run started

Stages: preflight chart originals art remix mix cover video youtube report.
Exit codes: 0 done, 1 a stage failed, 2 usage, 10 waiting for the human (see "waiting"),
20 waiting for the agent (look preview or YouTube metadata), 130 interrupted.
Prints one JSON object. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rcvlib import config as cfgmod  # noqa: E402
from rcvlib import cover, nct, preflight, stemforge  # noqa: E402
from rcvlib.common import (EXIT_FAIL, EXIT_NEED_AGENT, EXIT_NEED_USER, EXIT_OK, EXIT_USAGE, RcvError, check,  # noqa: E402
                           digest, emit, file_sig, read_json, worst, write_json)
from rcvlib.state import STAGE_IDS, RunLock, State  # noqa: E402


class NeedUser(Exception):
    def __init__(self, text: str, checks=None):
        super().__init__(text)
        self.checks = checks or []


class NeedAgent(NeedUser):
    pass


class Ctx:
    def __init__(self, cfg: dict, run_dir: Path, state: State):
        self.cfg, self.run_dir, self.state = cfg, Path(run_dir), state
        self.stopping = False
        self.children: list = []

    def should_stop(self) -> bool:
        return self.stopping

    def manifest(self) -> dict:
        data = read_json(self.run_dir / 'manifest.json')
        if not data:
            raise RcvError('Chưa có manifest.json: chặng chọn bài chưa xong.')
        return data

    def on_signal(self, *_):
        self.stopping = True
        for proc in self.children:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except OSError:
                pass


# -- stages ------------------------------------------------------------------------------

def st_preflight(ctx: Ctx):
    checks = preflight.run_preflight(ctx.cfg, ctx.run_dir, ctx.state.data['run']['count'],
                                     need_server=ctx.state.stage('remix')['status'] != 'done')
    write_json(ctx.run_dir / 'preflight.json', {'checks': checks})
    return checks, None


def st_chart(ctx: Ctx):
    rep = read_json(ctx.run_dir / 'nct' / 'report.json')
    if not rep:
        raise RcvError('Thiếu nct/report.json; tạo lượt chạy bằng `pipeline.py init`.')
    run = rep.get('run', {})
    ok = run.get('status') == 'completed' and len(rep.get('songs', [])) > 0
    src = ctx.state.data['run'].get('chart_source')
    return [check('chart', 'PASS' if ok else 'FAIL',
                  f'{run.get("chart_title")} ngày {run.get("chart_date")}, {len(rep.get("songs", []))} bài, nguồn: {src}')], None


def st_originals(ctx: Ctx):
    cfg, state, run_dir = ctx.cfg, ctx.state, ctx.run_dir
    rep = read_json(run_dir / 'nct' / 'report.json')
    info = state.data['run']
    count, dec = info['count'], state.data['decisions']
    live = cfg['nct'].get('live_access') is True and os.environ.get('RCV_FORBID_NCT') != '1'
    sources = run_dir / 'sources'
    sources.mkdir(exist_ok=True)
    dl = nct.Downloader(cfg, state)
    max_rank = min(cfg['selection']['max_rank'], len(rep['songs']))
    window = min(dec.get('window', count), max_rank)
    while True:
        if live and window > dec.get('searched_window', 0):
            code = dl.fetch_originals(info['nct_run_id'], window, should_stop=ctx.should_stop,
                                      on_progress=lambda d, t, text: state.progress('originals', done=d, total=t, text=text))
            if ctx.should_stop():
                raise stemforge.Interrupted()
            if code != 0:
                raise RcvError(f'Lệnh `originals` của repo NCT thoát mã {code} (2 = NCT không tới được).')
            dec['searched_window'] = window
            rep = dl.report(info['nct_run_id'])
            write_json(run_dir / 'nct' / 'report.json', rep)
            state.save()
        cands = nct.classify(rep, cfg, sources, dec.get('rejected'))
        sel = nct.select(cands, count, window)
        if sel['short_by'] == 0:
            break
        action = dec.get('missing_action') or (cfg['selection']['on_missing'] if cfg['selection']['on_missing'] != 'ask' else None)
        if action == 'skip':
            break
        if action == 'backfill' and window < max_rank:
            window = min(max_rank, window + sel['short_by'])
            dec['window'] = window
            if not live:
                dec.pop('missing_action', None)        # offline: the wider window needs files from the human
            state.save()
            continue
        dec.pop('missing_action', None)
        state.save()
        text = nct.missing_message(sel, sources, live)
        if action == 'backfill':
            text += f'\nĐã xét tới hạng {window}, không còn hạng nào để lấy bù.'
        raise NeedUser(text)
    if not sel['selected']:
        raise RcvError('Không có bài nào dùng được.')
    manifest = nct.build_manifest(rep, sel, cfg, info.get('sequence'))
    previous = read_json(run_dir / 'manifest.json') or {}
    for tr in manifest['tracks']:                          # keep hashes already computed
        old = next((o for o in previous.get('tracks', []) if o['rank'] == tr['rank'] and o['source']['path'] == tr['source']['path']), None)
        if old and old['source'].get('sha256'):
            tr['source']['sha256'] = old['source']['sha256']
    write_json(run_dir / 'selection.json', {'window': window, 'count': count, 'candidates': cands[:max(window, count)]})
    write_json(run_dir / 'manifest.json', manifest)
    ranks = [t['rank'] for t in manifest['tracks']]
    checks = [check('selected', 'PASS' if len(ranks) == count else 'WARN',
                    f'{len(ranks)}/{count} bài, hạng {ranks}' + ('' if manifest['exact_top'] else ' (không phải đúng hạng 1..N liên tục)'))]
    skipped = [f'hạng {c["rank"]}: {c["detail"] or c["reason"]}' for c in cands if c['rank'] <= window and not c['usable']]
    if skipped:
        checks.append(check('not_used', 'WARN', '; '.join(skipped)))
    state.progress('originals', done=len(ranks), total=count, text=f'đã chọn {len(ranks)} bài', force=True)
    return checks, {'ranks': ranks}


def st_art(ctx: Ctx):
    dec = ctx.state.data['decisions']
    manifest = ctx.manifest()
    checks, info = cover.fetch_art(ctx.run_dir, ctx.cfg, manifest, dec)
    if not ctx.cfg['cover'].get('review', True):
        checks.append(check('art_review', 'SKIP', 'cover.review đang tắt: không dừng hỏi duyệt ảnh'))
    elif dec.get('art_approved') != info['signature']:
        raise NeedUser(cover.review_message(ctx.run_dir, ctx.cfg, manifest, info), checks)      # the human looks first
    else:
        checks.append(check('art_review', 'PASS', 'bạn đã duyệt ảnh và chữ trên ảnh bìa'))
    return checks, info


def st_remix(ctx: Ctx):
    manifest = ctx.manifest()
    out = stemforge.remix_tracks(ctx.run_dir, ctx.cfg, ctx.state, manifest, ctx.should_stop)
    write_json(ctx.run_dir / 'manifest.json', manifest)        # source hashes filled in
    checks = list(out['checks'])
    by_id = {t['id']: t for t in manifest['tracks']}
    for tid, res in sorted(out['results'].items()):
        notes = [c for c in res['checks'] if c['status'] in ('WARN', 'FAIL')]
        detail = f'{res["bpm"]} BPM, {res["duration"]:.1f}s, {res["lufs"] and round(res["lufs"], 1)} LUFS'
        if notes:
            detail += ' · ' + '; '.join(f'{c["name"]}: {c["detail"]}' for c in notes)
        checks.append(check(f'remix_{by_id[int(tid)]["slug"]}', worst(res['checks']) if notes else 'PASS', detail))
    if out['failed']:
        ranks = ', '.join(str(f['rank']) for f in out['failed'])
        lines = [f'StemForge không phối được {len(out["failed"])} bài (hạng {ranks}): chọn retry, skip hoặc backfill.']
        lines += [f'  hạng {f["rank"]}: {f["title"]} — {f["error_type"]}: {f["error"]} (đã thử {f["attempts"]} lần)' for f in out['failed']]
        lines.append('Chọn: retry (thử lại), skip (bỏ các bài này), backfill (lấy bù hạng kế tiếp).')
        for f in out['failed']:
            checks.append(check(f'remix_rank_{f["rank"]}', 'FAIL', f'{f["error_type"]}: {f["error"]}'))
        ctx.state.data['decisions']['remix_failed'] = [f['rank'] for f in out['failed']]
        raise NeedUser('\n'.join(lines), checks)
    return checks, {'jobs': out.get('jobs', [])}


def st_mix(ctx: Ctx):
    from rcvlib import mix
    return mix.build(ctx.run_dir, ctx.cfg, ctx.state, ctx.manifest(), ctx)


def st_cover(ctx: Ctx):
    from rcvlib import youtube
    mixinfo = read_json(ctx.run_dir / 'mix' / 'mix_report.json')
    if not mixinfo:
        raise RcvError('Chưa có mix/mix_report.json: chặng ghép mix chưa xong.')
    return cover.make_cover(ctx.run_dir, ctx.cfg, ctx.manifest(), mixinfo, youtube.load_limits())


def st_video(ctx: Ctx):
    from rcvlib import video
    look = ctx.cfg['video'].get('look')
    if look not in ('cover', 'visualizer'):
        raise NeedAgent('Chưa chọn kiểu hình (video.look). Chạy `render_video.py preview --run RUN`, cho người dùng xem '
                        'khung hình của hai kiểu, rồi `pipeline.py set video.look cover|visualizer`.')
    return video.render_final(ctx.run_dir, ctx.cfg, ctx.state, ctx)


def st_youtube(ctx: Ctx):
    from rcvlib import youtube
    if not (ctx.run_dir / 'youtube' / 'youtube.json').is_file():
        raise NeedAgent('Chưa có youtube/youtube.json. Viết nó theo references/youtube_metadata.md rồi chạy '
                        '`youtube_meta.py validate --run RUN`.')
    checks = youtube.validate(ctx.run_dir)
    if worst(checks) != 'FAIL':
        youtube.render_md(ctx.run_dir)
    return checks, None


def st_report(ctx: Ctx):
    from rcvlib import report
    return report.build(ctx.run_dir, ctx.cfg, ctx.state)


STAGE_FN = {'preflight': st_preflight, 'chart': st_chart, 'originals': st_originals, 'art': st_art, 'remix': st_remix,
            'mix': st_mix, 'cover': st_cover, 'video': st_video, 'youtube': st_youtube, 'report': st_report}
ALWAYS = ('preflight', 'report')        # cheap, and their inputs are "the world right now"


def inputs_hash(ctx: Ctx, sid: str) -> str:
    """What a stage depends on. A done stage runs again only when this changes."""
    cfg, run, info, dec = ctx.cfg, ctx.run_dir, ctx.state.data['run'], ctx.state.data['decisions']
    sig = lambda *parts: file_sig(run.joinpath(*parts))  # noqa: E731
    if sid == 'chart':
        return digest([sig('nct', 'report.json') and info.get('nct_run_id'), info.get('chart_source')])
    if sid == 'originals':
        src = run / 'sources'
        return digest([info['count'], info.get('sequence'), cfg['selection'], cfg['cover']['label'],
                       {k: dec.get(k) for k in ('window', 'missing_action', 'rejected', 'searched_window')},
                       sorted(p.name for p in src.iterdir()) if src.is_dir() else []])
    manifest = read_json(run / 'manifest.json') or {}
    tracks = [(t['rank'], t['source']['path'], t['title'], t['artist']) for t in manifest.get('tracks', [])]
    order = [(p['position'], p['track']) for p in manifest.get('playlist', [])]   # not the chapter fields mix adds later
    if sid == 'art':
        keys = ('seed', 'preset', 'dry_run', 'image', 'title', 'title_inexact', 'subtitle', 'label', 'review')
        side = cover.side_signature(cfg)
        return digest([{k: cfg['cover'].get(k) for k in keys}, (manifest.get('chart') or {}).get('date'), tracks,
                       order, manifest.get('exact_top'), side, {k: dec.get(k) for k in ('art_approved', 'art_seed_offset', 'art_image')}])
    if sid == 'remix':
        return digest([cfgmod.GENRE, cfg['remix']['target_bpm'], cfg['remix']['target_key'],
                       cfg['remix']['quality'], cfg['remix'].get('separator'), tracks, dec.get('retry_token')])
    remixes = [(sig('remix', t['slug'], 'final.wav'), sig('remix', t['slug'], 'vocals.json')) for t in manifest.get('tracks', [])]
    if sid == 'mix':
        return digest([cfg['mix'], order, remixes])
    if sid == 'cover':
        return digest([cfg['cover'], cover.side_signature(cfg), sig('mix', 'mix_report.json'),
                       sig('art', 'raw.png'), tracks])
    if sid == 'video':
        keys = ('look', 'preset', 'fps', 'size', 'workers', 'cover_zoom_amount', 'background_still', 'tracklist')   # what changes the picture;
        return digest([{k: cfg['video'].get(k) for k in keys}, sig('mix.wav'),        # a check threshold must not
                       sig('cover', 'cover.png'), sig('art', 'raw.png'), sig('video', 'background.png')])   # cost a 30-minute render
    if sid == 'youtube':
        return digest([sig('youtube', 'youtube.json'), sig('mix', 'mix_report.json'), sig('manifest.json')])
    return digest([time.time()])


def run_stages(ctx: Ctx, until: str | None, only: str | None) -> int:
    state = ctx.state
    first_run = [q for q in cfgmod.unanswered(ctx.cfg) if q['key'] != 'video.look']
    if first_run:
        state.data['waiting'] = 'Câu hỏi lần đầu: ' + '; '.join(q['question'] for q in first_run)
        state.save()
        emit({'exit': EXIT_NEED_USER, 'first_run_questions': first_run,
              'how': 'hỏi người dùng, lưu bằng `pipeline.py set KEY VALUE`, rồi chạy lại'})
        return EXIT_NEED_USER
    if only:
        blockers = [s for s in STAGE_IDS[:STAGE_IDS.index(only)] if state.stage(s)['status'] != 'done']
        if blockers:
            raise RcvError(f'--only {only}: các chặng trước chưa xong: {blockers}', EXIT_USAGE)
    ran = []
    for sid in STAGE_IDS:
        if only and sid != only:
            continue
        st = state.stage(sid)
        want = inputs_hash(ctx, sid)
        if st['status'] == 'done' and st.get('inputs_hash') == want and sid not in ALWAYS:
            if sid == until:
                break
            continue
        if sid == 'remix' and ctx.cfg['video'].get('look') is None:
            state.data['waiting'] = 'Chọn kiểu hình (cover hay visualizer) trước chặng phối nhạc'
            state.save()
            emit({'exit': EXIT_NEED_AGENT, 'stage': 'remix', 'ran': ran,
                  'need': 'Câu hỏi lần đầu video.look: chạy `render_video.py preview --run RUN`, cho người dùng xem khung '
                          'hình hai kiểu, lưu bằng `pipeline.py set video.look cover|visualizer`, rồi chạy lại.'})
            return EXIT_NEED_AGENT
        state.start(sid, want)
        try:
            checks, outputs = STAGE_FN[sid](ctx)
        except NeedAgent as exc:
            state.wait(sid, f'(agent) {exc}', exc.checks)
            emit({'exit': EXIT_NEED_AGENT, 'stage': sid, 'need': str(exc), 'ran': ran})
            return EXIT_NEED_AGENT
        except NeedUser as exc:
            state.wait(sid, str(exc), exc.checks)
            emit({'exit': EXIT_NEED_USER, 'stage': sid, 'waiting': str(exc), 'ran': ran})
            return EXIT_NEED_USER
        except stemforge.Interrupted:
            state.interrupt(sid)
            emit({'exit': 130, 'stage': sid, 'status': 'interrupted', 'ran': ran})
            return 130
        except RcvError as exc:
            state.fail(sid, str(exc))
            emit({'exit': EXIT_FAIL, 'stage': sid, 'error': str(exc), 'ran': ran})
            return EXIT_FAIL
        except Exception as exc:  # a bug or an unexpected tool failure: record it, never look "done"
            state.fail(sid, f'{type(exc).__name__}: {exc}')
            raise
        if ctx.stopping:
            state.interrupt(sid)
            emit({'exit': 130, 'stage': sid, 'status': 'interrupted', 'ran': ran})
            return 130
        state.stage(sid)['inputs_hash'] = inputs_hash(ctx, sid)     # a stage may refine its own inputs (hashes, windows)
        verdict = state.finish(sid, checks, outputs)
        ran.append({'stage': sid, 'status': verdict, 'worst': worst(checks or [])})
        if verdict == 'failed':
            emit({'exit': EXIT_FAIL, 'stage': sid, 'error': state.stage(sid)['error'], 'ran': ran})
            return EXIT_FAIL
        if sid == until:
            break
    if state.finished():
        state.data['now'] = 'Xong tất cả các bước'
        state.save()
    emit({'exit': EXIT_OK, 'ran': ran, 'finished': state.finished(), 'run': str(ctx.run_dir)})
    return EXIT_OK


# -- commands ------------------------------------------------------------------------------

def cmd_init_config(args) -> int:
    path = Path(args.config) if args.config else None
    root = Path(args.root).resolve() if args.root else cfgmod.find_root()
    if root is None:
        raise RcvError('Không thấy thư mục chứa bốn repo; truyền --root.', EXIT_USAGE)
    path = path or root / 'mixes' / 'config.json'
    if path.exists():
        cfg = cfgmod.load(path)
        created = False
    else:
        cfg = cfgmod.init(path, root)
        created = True
    emit({'config': str(path), 'created': created, 'repos': cfg['repos'], 'first_run_questions': cfgmod.unanswered(cfg)})
    return EXIT_OK


def cmd_set(args) -> int:
    cfg = cfgmod.load(args.config)
    try:
        value = json.loads(args.value)
    except ValueError:
        value = args.value
    try:
        cfgmod.get(cfg, args.key)
    except (KeyError, TypeError):
        raise RcvError(f'Config không có khoá {args.key}', EXIT_USAGE)
    cfgmod.put(cfg, args.key, value)
    cfgmod.save(cfg)
    emit({'config': cfg['_path'], 'set': {args.key: value}, 'first_run_questions': cfgmod.unanswered(cfg)})
    return EXIT_OK


def _runs(workspace: Path) -> list[Path]:
    return sorted((p for p in workspace.iterdir() if (p / 'state.json').is_file()),
                  key=lambda p: (p / 'state.json').stat().st_mtime, reverse=True) if workspace.is_dir() else []


def cmd_init(args) -> int:
    cfg = cfgmod.load(args.config)
    first_run = [q for q in cfgmod.unanswered(cfg) if q['key'] != 'video.look']
    if first_run:                                   # nothing starts before the human has answered
        emit({'exit': EXIT_NEED_USER, 'first_run_questions': first_run,
              'how': 'hỏi người dùng trong một tin nhắn, lưu từng câu trả lời bằng `pipeline.py set KEY VALUE`, rồi chạy lại init'})
        return EXIT_NEED_USER
    workspace = Path(cfg['_workspace'])
    sequence = [int(x) for x in args.sequence.split(',')] if args.sequence else None
    carry = old_state = None
    if args.from_run:
        carry = Path(args.from_run).resolve()
        old_state = State.load(carry)
        count = args.count or old_state.data['run']['count']
        sequence = sequence or old_state.data['run'].get('sequence')
    else:
        count = args.count or cfg['selection']['count']
    checks = preflight.run_preflight(cfg, None, count, need_server=not carry)     # a redo reuses the remixes
    if worst(checks) == 'FAIL':
        emit({'exit': EXIT_FAIL, 'preflight': [c for c in checks if c['status'] != 'PASS']})
        return EXIT_FAIL

    # where the chart comes from: a saved run, a saved page, today's saved run, or a live fetch
    dl = nct.Downloader(cfg)
    commands = []
    if carry:
        rep = read_json(carry / 'nct' / 'report.json')
        if not rep:
            raise RcvError(f'{carry} không có nct/report.json', EXIT_USAGE)
        source = f'{old_state.data["run"].get("chart_source")} · làm lại từ lượt {carry.name}'
    elif args.nct_run_id:
        rep, source = dl.report(args.nct_run_id), f'lượt NCT #{args.nct_run_id} đã lưu'
    elif args.html:
        rep, source = dl.refresh_chart(html=args.html), f'trang đã lưu {args.html}'
        commands.append({'at': time.time(), 'command': 'remix --top 50 --no-download --html …', 'live': False, 'exit': 0})
    else:
        rep = None
        try:
            latest = dl.report()
            started = (latest['run'].get('started_at') or '')[:10]
            if latest['run'].get('status') == 'completed' and latest['run'].get('chart_tag') == cfg['nct']['chart'] \
                    and started == time.strftime('%Y-%m-%d', time.gmtime()):
                rep, source = latest, f'lượt NCT #{latest["run"]["id"]} lấy hôm nay'
        except RcvError:
            pass
        if rep is None:
            if cfg['nct'].get('live_access') is None:
                emit({'exit': EXIT_NEED_USER, 'first_run_questions': cfgmod.unanswered(cfg),
                      'how': 'hỏi người dùng, lưu bằng `pipeline.py set KEY VALUE`, rồi chạy lại init'})
                return EXIT_NEED_USER
            if cfg['nct']['live_access'] is not True:
                raise RcvError('NCT đang tắt và chưa có BXH của hôm nay. Lưu trang BXH từ trình duyệt rồi truyền '
                               '--html FILE, hoặc dùng một lượt đã lưu với --nct-run-id ID.', EXIT_USAGE)
            rep, source = dl.refresh_chart(), 'lấy trực tiếp từ NCT (3 request)'
            commands.append({'at': time.time(), 'command': 'remix --top 50 --no-download', 'live': True, 'exit': 0})
    if rep['run'].get('status') != 'completed':
        raise RcvError(f'Lượt NCT #{rep["run"].get("id")} không ở trạng thái completed.')
    chart_date = rep['run'].get('chart_date') or time.strftime('%Y-%m-%d')

    # resume the newest unfinished run of the same chart date, else make a new folder
    if not args.new and not carry:
        for run_dir in _runs(workspace):
            st = State.load(run_dir)
            info = st.data['run']
            if not st.finished() and info.get('chart_date') == chart_date and info.get('count') == count \
                    and info.get('sequence') == sequence:
                emit({'exit': EXIT_OK, 'run': str(run_dir), 'resumed': True, 'chart_date': chart_date,
                      'current_stage': (st.current() or {}).get('id'), 'first_run_questions': cfgmod.unanswered(cfg)})
                return EXIT_OK
    base = args.name or f'{chart_date}_top{count}-remix'
    run_dir, n = workspace / base, 1
    while run_dir.exists():
        n += 1
        run_dir = workspace / f'{base}-{n}'
    (run_dir / 'nct').mkdir(parents=True)
    write_json(run_dir / 'nct' / 'report.json', rep)
    title = f'Top {count} Remix Việt · {chart_date}'
    state = State.create(run_dir, {'name': run_dir.name, 'dir': str(run_dir), 'title': title, 'chart_date': chart_date,
                                   'count': count, 'sequence': sequence, 'nct_run_id': rep['run']['id'],
                                   'chart_source': source, 'config_path': cfg['_path']})
    state.data['nct_commands'] = commands
    ctx = Ctx(cfg, run_dir, state)
    for sid, fn in (('preflight', lambda c: (checks, None)), ('chart', st_chart)):
        state.start(sid, inputs_hash(ctx, sid))
        got, _ = fn(ctx)
        state.finish(sid, got)
    write_json(run_dir / 'preflight.json', {'checks': checks})
    if carry:                                       # same songs, same remixes; only the later stages run again
        state.data['decisions'] = {k: v for k, v in old_state.data.get('decisions', {}).items()
                                   if k not in ('remix_failed', 'retry_token')}
        if (carry / 'sources').is_dir():
            shutil.copytree(carry / 'sources', run_dir / 'sources', dirs_exist_ok=True)
        for src in sorted((carry / 'remix').iterdir()) if (carry / 'remix').is_dir() else []:
            dst = run_dir / 'remix' / src.name
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if f.name == 'final.wav':
                    try:
                        os.link(f, dst / f.name)            # no second copy of the audio
                    except OSError:
                        shutil.copyfile(f, dst / f.name)
                elif f.suffix == '.json' and f.name != 'vocals.json':
                    shutil.copyfile(f, dst / f.name)
        state.save()
    emit({'exit': EXIT_OK, 'run': str(run_dir), 'resumed': False, 'chart_date': chart_date, 'chart_source': source,
          'preflight_warnings': [c for c in checks if c['status'] == 'WARN'],
          'first_run_questions': cfgmod.unanswered(cfg)})
    return EXIT_OK


def cmd_run(args) -> int:
    run_dir = Path(args.run).resolve()
    state = State.load(run_dir)
    cfg = cfgmod.load(args.config or state.data['run'].get('config_path'))
    for name in (args.until, args.only):
        if name and name not in STAGE_IDS:
            raise RcvError(f'Không có chặng "{name}". Các chặng: {" ".join(STAGE_IDS)}', EXIT_USAGE)
    if state.finished():                            # a finished run is never changed; a redo is a new run
        emit({'exit': EXIT_OK, 'finished': True, 'ran': [], 'run': str(run_dir),
              'note': 'Lượt này đã xong và không bị sửa nữa. Muốn làm lại, tạo lượt mới bằng `pipeline.py init --new`.'})
        return EXIT_OK
    ctx = Ctx(cfg, run_dir, state)
    signal.signal(signal.SIGINT, ctx.on_signal)
    signal.signal(signal.SIGTERM, ctx.on_signal)
    with RunLock(run_dir):
        return run_stages(ctx, args.until, args.only)


def cmd_decide(args) -> int:
    run_dir = Path(args.run).resolve()
    state = State.load(run_dir)
    dec = state.data['decisions']
    if args.missing:
        dec['missing_action'] = args.missing
        state.stage('originals')['status'] = 'todo'
    elif args.remix_failed:
        failed = dec.pop('remix_failed', [])
        if args.remix_failed == 'retry':
            dec['retry_token'] = time.time()
            manifest = read_json(run_dir / 'manifest.json') or {}
            for tr in manifest.get('tracks', []):
                rec_path = run_dir / 'remix' / tr['slug'] / 'job.json'
                rec = read_json(rec_path) or {}
                if rec.get('status') == 'failed':
                    rec.update(status='running', attempts=0)
                    write_json(rec_path, rec)
        else:
            dec.setdefault('rejected', {}).update({str(r): 'remix_failed' for r in failed})
            dec['missing_action'] = 'skip' if args.remix_failed == 'skip' else 'backfill'
            state.stage('originals')['status'] = 'todo'
        state.stage('remix')['status'] = 'todo'
    elif args.art:
        if args.art == 'ok':
            art = read_json(run_dir / 'art' / 'art.json') or {}
            if not art.get('signature'):
                raise RcvError('Chưa có ảnh để duyệt: chặng art chưa chạy xong.', EXIT_USAGE)
            dec['art_approved'] = art['signature']
        elif args.art == 'redo':
            dec['art_seed_offset'] = int(dec.get('art_seed_offset', 0)) + 1
            dec.pop('art_image', None)
        else:
            src = Path(args.path).expanduser().resolve() if args.path else None
            if not src or not src.is_file():
                raise RcvError('--art image cần --path trỏ tới một file ảnh có thật', EXIT_USAGE)
            keep = run_dir / 'art' / f'own_picture{src.suffix.lower()}'
            keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, keep)                      # the run keeps its own copy
            dec['art_image'] = str(keep)
        state.stage('art')['status'] = 'todo'
    else:
        raise RcvError('Cần --missing, --remix-failed hoặc --art', EXIT_USAGE)
    state.data['waiting'] = None
    state.save()
    emit({'run': str(run_dir), 'decisions': dec})
    return EXIT_OK


def cmd_status(args) -> int:
    state = State.load(Path(args.run).resolve())
    emit({'run': state.data['run'], 'now': state.data['now'], 'waiting': state.data['waiting'],
          'finished': state.finished(), 'heartbeat_age_s': round(time.time() - state.data['heartbeat'], 1),
          'stages': [{'id': s['id'], 'status': s['status'], 'worst': worst(s.get('checks') or []),
                      'progress': s.get('progress'), 'error': s.get('error')} for s in state.data['stages']],
          'result': state.data.get('result')})
    return EXIT_OK


def cmd_stop(args) -> int:
    run_dir = Path(args.run).resolve()
    state = State.load(run_dir)
    cfg = cfgmod.load(args.config or state.data['run'].get('config_path'))
    server = stemforge.Server(cfg, run_dir, state)
    had = server._record() is not None
    server.stop()
    emit({'stopped_server': had})
    return EXIT_OK


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('init-config'); p.add_argument('--config'); p.add_argument('--root')
    p = sub.add_parser('set'); p.add_argument('key'); p.add_argument('value'); p.add_argument('--config')
    p = sub.add_parser('init'); p.add_argument('--config'); p.add_argument('--count', type=int)
    p.add_argument('--nct-run-id', type=int); p.add_argument('--html'); p.add_argument('--sequence')
    p.add_argument('--name'); p.add_argument('--new', action='store_true'); p.add_argument('--from-run')
    p = sub.add_parser('run'); p.add_argument('--run', required=True); p.add_argument('--config')
    p.add_argument('--until'); p.add_argument('--only')
    p = sub.add_parser('decide'); p.add_argument('--run', required=True)
    p.add_argument('--missing', choices=['backfill', 'skip', 'manual'])
    p.add_argument('--remix-failed', choices=['retry', 'skip', 'backfill'])
    p.add_argument('--art', choices=['ok', 'redo', 'image']); p.add_argument('--path')
    p = sub.add_parser('status'); p.add_argument('--run', required=True)
    p = sub.add_parser('stop'); p.add_argument('--run', required=True); p.add_argument('--config')
    args = ap.parse_args(argv)
    fn = {'init-config': cmd_init_config, 'set': cmd_set, 'init': cmd_init, 'run': cmd_run, 'decide': cmd_decide,
          'status': cmd_status, 'stop': cmd_stop}[args.cmd]
    try:
        return fn(args)
    except RcvError as exc:
        emit({'exit': exc.code, 'error': str(exc)})
        return exc.code


if __name__ == '__main__':
    sys.exit(main())
