#!/usr/bin/env python3
"""Run the lofi-ballad-to-video pipeline stage by stage, resumable, with a state file.

  pipeline.py init-config [--config FILE] [--root DIR]     write a config with the four repo paths
  pipeline.py set KEY VALUE [--config FILE]                save an answer, e.g. `set cover.confirmed true`
  pipeline.py init [--config FILE] [--count N] [--period 2010-2014] [--seed N] [--sequence 1,2,1] [--new]
                                                           resume the unfinished run, else draw a period and its
                                                           songs from the ballad list and create a run folder
  pipeline.py init --from-run OLD_RUN [--config FILE]      a new run that reuses OLD_RUN's songs, remixes and scene
                                                           (no NCT request, no GPU): redo the mix, cover and video
  pipeline.py run --run DIR [--until STAGE] [--only STAGE] run the stages that are not done yet
  pipeline.py decide --run DIR --missing backfill|skip|manual
  pipeline.py decide --run DIR --remix-failed retry|skip|backfill
  pipeline.py decide --run DIR --art ok|redo|image [--path FILE]   answer the picture stop after stage `art`
  pipeline.py status --run DIR                             one JSON summary of the run
  pipeline.py stop --run DIR                               stop a StemForge server this run started

Stages: preflight chart (the draw) originals art remix mix cover video youtube report.
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
from rcvlib import cover, nct, preflight, scenery, songlist, stemforge  # noqa: E402
from rcvlib.common import (EXIT_FAIL, EXIT_NEED_AGENT, EXIT_NEED_USER, EXIT_OK, EXIT_USAGE, RcvError, check,  # noqa: E402
                           content_sig, digest, emit, file_sig, read_json, worst, write_json)
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

def needs_stemforge(ctx: Ctx) -> bool:
    """Will this run still start StemForge? Not once the remix stage is done, and not when every
    song already has a verified remix (a run made with --from-run starts that way)."""
    if ctx.state.stage('remix')['status'] == 'done':
        return False
    manifest = read_json(ctx.run_dir / 'manifest.json') or {}
    slugs = [t['slug'] for t in manifest.get('tracks', [])]
    if not slugs and ctx.state.data['decisions'].get('carried_from'):
        slugs = [p.name for p in (ctx.run_dir / 'remix').iterdir() if p.is_dir()] if (ctx.run_dir / 'remix').is_dir() else []
    done = [(read_json(ctx.run_dir / 'remix' / s / 'job.json') or {}).get('status') == 'verified'
            and (ctx.run_dir / 'remix' / s / 'final.wav').is_file() for s in slugs]
    return not (done and all(done))


def st_preflight(ctx: Ctx):
    checks = preflight.run_preflight(ctx.cfg, ctx.run_dir, ctx.state.data['run']['count'], need_server=needs_stemforge(ctx))
    write_json(ctx.run_dir / 'preflight.json', {'checks': checks})
    return checks, None


def st_chart(ctx: Ctx):
    """The draw: the list of songs the downloader stored for this run (`songs --file`)."""
    rep = read_json(ctx.run_dir / 'nct' / 'report.json')
    if not rep:
        raise RcvError('Thiếu nct/report.json; tạo lượt chạy bằng `pipeline.py init`.')
    run = rep.get('run', {})
    pick = read_json(ctx.run_dir / 'songlist' / 'pick.json') or {}
    ok = run.get('status') == 'completed' and len(rep.get('songs', [])) > 0 and run.get('input') == 'song_list'
    src = ctx.state.data['run'].get('chart_source')
    checks = [check('chart', 'PASS' if ok else 'FAIL',
                    f'{run.get("chart_title")}: {len(rep.get("songs", []))} bài theo thứ tự bốc (seed {pick.get("seed")}), '
                    f'{pick.get("fresh")}/{pick.get("period_size")} bài của giai đoạn chưa có trong video nào; nguồn: {src}')]
    if pick.get('notes'):
        checks.append(check('draw_notes', 'WARN', '; '.join(pick['notes'])))
    return checks, None


def st_originals(ctx: Ctx):
    cfg, state, run_dir = ctx.cfg, ctx.state, ctx.run_dir
    rep = read_json(run_dir / 'nct' / 'report.json')
    info = state.data['run']
    count, dec = info['count'], state.data['decisions']
    # A run made with --from-run reuses the old run's songs: it never sends a request to NCT.
    live = cfg['nct'].get('live_access') is True and os.environ.get('RCV_FORBID_NCT') != '1' and not dec.get('carried_from')
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
        cands = nct.classify(rep, cfg, sources, dec.get('rejected'), rejected_at=dec.get('rejected_at'))
        sel = nct.select(cands, count, window)
        if sel['short_by'] == 0:
            break
        missing = sorted(c['rank'] for c in sel['missing'])
        if dec.get('missing_action') == 'skip' and not set(missing) <= set(dec.get('missing_asked') or missing):
            dec.pop('missing_action')                   # "skip" answered another question: other songs are missing now
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
        dec['missing_asked'] = missing
        state.save()
        text = nct.missing_message(sel, sources, live, dec.get('rejected'))
        if action == 'backfill':
            text += f'\nĐã xét tới bài số {window} của danh sách bốc, không còn bài nào để lấy bù.'
        raise NeedUser(text)
    if not sel['selected']:
        raise RcvError('Không có bài nào dùng được.')
    manifest = nct.build_manifest(rep, sel, cfg, info.get('sequence'), songlist.by_position(run_dir))
    manifest['chart']['period'] = info.get('period_label')
    previous = read_json(run_dir / 'manifest.json') or {}
    same_file = ('path', 'size', 'mtime_ns')
    for tr in manifest['tracks']:                          # keep hashes already computed, for a file that did not change
        old = next((o for o in previous.get('tracks', []) if o['rank'] == tr['rank']
                    and all(o['source'].get(k) == tr['source'].get(k) for k in same_file)), None)
        if old and old['source'].get('sha256'):
            tr['source']['sha256'] = old['source']['sha256']
        if old:                                            # what the mix stage measured stays with the song
            tr.update({k: old[k] for k in ('bpm', 'key') if k in old})
    ident = lambda m: ([(t['rank'], t['label'], [t['source'].get(k) for k in same_file]) for t in m.get('tracks', [])],  # noqa: E731
                       [(i['position'], i['track']) for i in m.get('playlist', [])])
    if previous.get('mix') and ident(previous) == ident(manifest):
        # Same songs, same labels, same order: the chapter times the mix wrote are still true.
        manifest['mix'] = previous['mix']
        for item, old in zip(manifest['playlist'], previous['playlist']):
            item.update({k: old[k] for k in ('chapter', 'chapter_seconds') if k in old})
    write_json(run_dir / 'selection.json', {'window': window, 'count': count, 'candidates': cands[:max(window, count)]})
    write_json(run_dir / 'manifest.json', manifest)
    drawn = songlist.by_position(run_dir)
    songlist.record(cfg, run_dir.name, [drawn[t['rank']] for t in manifest['tracks'] if t['rank'] in drawn])
    ranks = [t['rank'] for t in manifest['tracks']]
    checks = [check('selected', 'PASS' if len(ranks) == count else 'WARN',
                    f'{len(ranks)}/{count} bài, vị trí trong danh sách bốc {ranks}')]
    skipped = [f'bài số {c["rank"]} ({c["chart_title"]}): {c["detail"] or c["reason"]}' for c in cands if c['rank'] <= window and not c['usable']]
    if skipped:
        checks.append(check('not_used', 'WARN', '; '.join(skipped)))
    state.progress('originals', done=len(ranks), total=count, text=f'đã chọn {len(ranks)} bài', force=True)
    return checks, {'ranks': ranks}


def st_art(ctx: Ctx):
    dec = ctx.state.data['decisions']
    manifest = ctx.manifest()
    checks, info = cover.fetch_art(ctx.run_dir, ctx.cfg, manifest, dec)
    if dec.get('art_approved') != info['signature'] and not ctx.cfg['cover'].get('review', False):
        if worst(checks) == 'FAIL':                     # a repeat of an earlier video's picture: not a matter of taste, the human answers
            raise NeedUser(cover.review_message(ctx.run_dir, ctx.cfg, manifest, info, checks), checks)
        dec['art_approved'] = info['signature']         # the human takes the model's picture as it is (cover.review off)
        scenery.approve(ctx.cfg, ctx.run_dir)           # it still joins the set no later video may repeat
        checks.append(check('art_review', 'PASS', 'cover.review đang tắt: nhận ảnh model vẽ, không dừng hỏi; ảnh đã vào lịch sử tranh'))
    elif dec.get('art_approved') != info['signature']:
        raise NeedUser(cover.review_message(ctx.run_dir, ctx.cfg, manifest, info, checks), checks)      # the human looks first
    else:
        checks.append(check('art_review', 'PASS', 'bạn đã duyệt ảnh và chữ trên ảnh bìa'))
    return checks, info


def _remix_question(failed: list[dict]) -> str:
    ranks = ', '.join(str(f['rank']) for f in failed)
    lines = [f'StemForge không phối được {len(failed)} bài (bài số {ranks}): chọn retry, skip hoặc backfill.']
    lines += [f'  bài số {f["rank"]}: {f["title"]} — {f["error_type"]}: {f["error"]} (đã thử {f["attempts"]} lần)' for f in failed]
    lines.append('Chọn: retry (thử lại), skip (bỏ các bài này), backfill (lấy bù bài kế tiếp trong danh sách bốc).')
    return '\n'.join(lines)


def st_remix(ctx: Ctx):
    manifest = ctx.manifest()
    asked = ctx.state.data['decisions'].get('remix_failed')
    if asked:
        # The run already stopped for these songs and nobody has answered: ask again. Running
        # the stage would retry them, which is one of the three answers.
        failed = []
        for tr in manifest['tracks']:
            rec = read_json(ctx.run_dir / 'remix' / tr['slug'] / 'job.json') or {}
            if tr['rank'] in asked and rec.get('status') == 'failed':
                failed.append({'rank': tr['rank'], 'title': tr['title'], 'error_type': rec.get('error_type'),
                               'error': str(rec.get('error'))[:300], 'attempts': rec.get('attempts', 0)})
        if failed:
            raise NeedUser(_remix_question(failed), [check(f'remix_rank_{f["rank"]}', 'FAIL', f'{f["error_type"]}: {f["error"]}') for f in failed])
        ctx.state.data['decisions'].pop('remix_failed')         # the songs it named are gone: nothing left to ask
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
        for f in out['failed']:
            checks.append(check(f'remix_rank_{f["rank"]}', 'FAIL', f'{f["error_type"]}: {f["error"]}'))
        ctx.state.data['decisions']['remix_failed'] = [f['rank'] for f in out['failed']]
        raise NeedUser(_remix_question(out['failed']), checks)
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
    checks, info = video.render_final(ctx.run_dir, ctx.cfg, ctx.state, ctx)
    if worst(checks) != 'FAIL':
        scenery.mark_rendered(ctx.cfg, ctx.run_dir.name)        # this picture is now in a video
    return checks, info


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
        pick = read_json(run / 'songlist' / 'pick.json') or {}
        return digest([info['count'], info.get('sequence'), cfg['selection'], cfg['cover']['label'],
                       file_sig(run / 'songlist' / 'pick.json'), file_sig(Path(pick['list_path'])) if pick.get('list_path') else None,
                       songlist.SCHEMA,
                       {k: dec.get(k) for k in ('window', 'missing_action', 'rejected', 'searched_window')},
                       # name, size and time: a file replaced under the same name is a new song
                       sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in src.iterdir()) if src.is_dir() else []])
    manifest = read_json(run / 'manifest.json') or {}
    tracks = [(t['rank'], t['source']['path'], t['title'], t['artist']) for t in manifest.get('tracks', [])]
    order = [(p['position'], p['track']) for p in manifest.get('playlist', [])]   # not the chapter fields mix adds later
    if sid == 'art':
        keys = ('seed', 'preset', 'dry_run', 'image', 'title', 'title_inexact', 'subtitle', 'label', 'review',
                'max_art_similarity', 'scene_place_gap') + cover.POSTER_KEYS
        side = cover.side_signature(cfg)
        return digest([{k: cfg['cover'].get(k) for k in keys}, (manifest.get('chart') or {}).get('period'), tracks,
                       order, side, {k: dec.get(k) for k in ('art_approved', 'art_seed_offset', 'art_image', 'scene_rejected', 'scene_carry')},
                       cfg['video'].get('preset'), file_sig(scenery.SCENES_FILE)])
    if sid == 'remix':
        center_bpm = [cfg['remix'].get('source_center_bpm')] if cfg['remix']['target_bpm'] == 'source' else []
        return digest([cfgmod.GENRE, cfg['remix']['target_bpm'], cfg['remix']['target_key'],
                       cfg['remix']['quality'], cfg['remix'].get('separator'), tracks, dec.get('retry_token'),
                       stemforge.VERIFY_VERSION] + center_bpm)
    remixes = [(sig('remix', t['slug'], 'final.wav'), sig('remix', t['slug'], 'vocals.json')) for t in manifest.get('tracks', [])]
    if sid == 'mix':
        # labels: the chapters carry them. "mix" in the manifest: a rebuilt manifest lost the chapter times.
        return digest([cfg['mix'], order, remixes, [(t['id'], t['label']) for t in manifest.get('tracks', [])],
                       bool(manifest.get('mix'))])
    if sid == 'cover':
        return digest([cfg['cover'], cover.side_signature(cfg), sig('mix', 'mix_report.json'),
                       sig('art', 'raw.png'), tracks])
    if sid == 'video':
        # What changes the picture or the sound, by content: a stage that ran again and wrote the
        # same bytes (a check threshold, a thumbnail setting) must not cost a 30-minute render.
        keys = ('look', 'preset', 'logo', 'fps', 'size', 'background_still', 'tracklist')
        csig = lambda *parts: content_sig(run.joinpath(*parts), run / '.content_sig.json')  # noqa: E731
        return digest([{k: cfg['video'].get(k) for k in keys}, csig('mix.wav'), csig('video', 'background.png'), csig('art', 'raw.png')])
    if sid == 'youtube':
        return digest([sig('youtube', 'youtube.json'), sig('mix', 'mix_report.json'), sig('manifest.json')])
    return digest([time.time()])


def run_stages(ctx: Ctx, until: str | None, only: str | None) -> int:
    state = ctx.state
    first_run = cfgmod.unanswered(ctx.cfg)
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
            if ctx.stopping:                        # a tool killed by the stop reports an error: that is the interrupt
                state.interrupt(sid)
                emit({'exit': 130, 'stage': sid, 'status': 'interrupted', 'ran': ran})
                return 130
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
    path = path or root / cfgmod.WORKSPACE / 'config.json'
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
    value = cfgmod.validate(args.key, value)        # a wrong type or value is refused here, not hours later
    cfgmod.put(cfg, args.key, value)
    cfgmod.save(cfg)
    emit({'config': cfg['_path'], 'set': {args.key: value}, 'first_run_questions': cfgmod.unanswered(cfg)})
    return EXIT_OK


def _runs(workspace: Path) -> list[Path]:
    return sorted((p for p in workspace.iterdir() if (p / 'state.json').is_file()),
                  key=lambda p: (p / 'state.json').stat().st_mtime, reverse=True) if workspace.is_dir() else []


def cmd_init(args) -> int:
    cfg = cfgmod.load(args.config)
    first_run = cfgmod.unanswered(cfg)
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

    # An unfinished run is continued, never drawn again: the draw is the run's, made once.
    if not args.new and not carry and not args.period and args.seed is None:
        for run_dir in _runs(workspace):
            st = State.load(run_dir)
            info = st.data['run']
            if not st.finished() and info.get('count') == count and info.get('sequence') == sequence:
                emit({'exit': EXIT_OK, 'run': str(run_dir), 'resumed': True, 'period': info.get('period'),
                      'current_stage': (st.current() or {}).get('id'), 'first_run_questions': cfgmod.unanswered(cfg)})
                return EXIT_OK

    checks = preflight.run_preflight(cfg, None, count, need_server=not carry)     # a redo reuses the remixes
    if worst(checks) == 'FAIL':
        emit({'exit': EXIT_FAIL, 'preflight': [c for c in checks if c['status'] != 'PASS']})
        return EXIT_FAIL

    dl = nct.Downloader(cfg)
    today = time.strftime('%Y-%m-%d')
    if carry:
        rep = read_json(carry / 'nct' / 'report.json')
        pick = read_json(carry / 'songlist' / 'pick.json')
        if not rep or not pick:
            raise RcvError(f'{carry} không có nct/report.json hoặc songlist/pick.json', EXIT_USAGE)
        source = f'{old_state.data["run"].get("chart_source")} · làm lại từ lượt {carry.name}'
        slug = pick['slug']
    else:
        list_path = songlist.default_path(cfg)
        if not list_path or not list_path.is_file():
            raise RcvError(f'Không thấy danh sách bài: {list_path} (songlist.path)', EXIT_USAGE)
        periods = songlist.load(list_path)
        seed = args.seed if args.seed is not None else songlist.new_seed()
        pick = songlist.draw(periods, songlist.used_keys(cfg), seed, count, args.period, int(cfg['songlist']['pool']))
        slug = pick['slug']
    base = args.name or f'{today}_lofi-ballad-{slug}'
    run_dir, n = workspace / base, 1
    while run_dir.exists():
        n += 1
        run_dir = workspace / f'{base}-{n}'
    (run_dir / 'nct').mkdir(parents=True)
    commands = []
    if carry:
        shutil.copytree(carry / 'songlist', run_dir / 'songlist')
    else:
        list_file = songlist.write_run_files(run_dir, pick, list_path)
        title = f'Ballad Việt · {pick["period"]}'
        try:
            rep = dl.list_run(list_file, title)       # stores the draw; no request to NCT
        except RcvError:
            shutil.rmtree(run_dir, ignore_errors=True)  # the folder this call made, nothing else
            raise
        source = f'bốc từ {list_path.name}: {pick["period"]}, seed {pick["seed"]} (lượt NCT #{rep["run"]["id"]})'
        commands.append({'at': time.time(), 'command': f'songs --file {list_file.name} --title …', 'live': False, 'exit': 0})
    write_json(run_dir / 'nct' / 'report.json', rep)
    title = f'{count} bài Ballad Việt {pick["label"]} · Lofi Chill'
    state = State.create(run_dir, {'name': run_dir.name, 'dir': str(run_dir), 'title': title, 'chart_date': today,
                                   'period': pick['period'], 'period_label': pick['label'], 'seed': pick['seed'],
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
        dec = {k: v for k, v in old_state.data.get('decisions', {}).items()
               if k not in ('remix_failed', 'retry_token', 'art_approved', 'scene_rejected')}
        dec['carried_from'] = str(carry)                # this run reuses songs: it sends nothing to NCT
        if args.count and args.count != old_state.data['run']['count']:
            for k in ('missing_action', 'missing_asked', 'window'):     # answers to the old run's question
                dec.pop(k, None)
        # The picture the human chose lives in the old run's folder, which may be deleted later:
        # this run keeps its own copy.
        own = Path(dec['art_image']) if dec.get('art_image') else None
        if own is not None:
            src = own if own.is_file() else carry / 'art' / own.name if (carry / 'art' / own.name).is_file() else carry / 'art' / 'raw.png'
            if src.is_file():
                keep = run_dir / 'art' / f'own_picture{src.suffix.lower()}'
                keep.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, keep)
                dec['art_image'] = str(keep)
        # The same songs make the same video again: it keeps the old run's scene and seed, so
        # m10-mixcover's cache gives back the same picture, which is no repeat of another video.
        dec.pop('scene_carry', None)
        dec.pop('art_seed_offset', None)
        old_scene = scenery.carry_from(cfg, carry)
        if old_scene:
            dec['scene_carry'] = old_scene
        state.data['decisions'] = dec
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
    emit({'exit': EXIT_OK, 'run': str(run_dir), 'resumed': False, 'period': pick['period'], 'seed': pick['seed'],
          'drawn': [f'{s["position"]:02d}. {s["title"]} — {", ".join(s["artists"])}' for s in pick['songs'][:count]],
          'draw_notes': pick.get('notes', []), 'chart_source': source,
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
              'note': 'Lượt này đã xong và không bị sửa nữa. Muốn ghép, vẽ bìa hay render lại với cài đặt khác: '
                      f'`pipeline.py init --from-run {run_dir}` (dùng lại bài và bản phối). Muốn làm từ đầu: `pipeline.py init --new`.'})
        return EXIT_OK
    ctx = Ctx(cfg, run_dir, state)
    signal.signal(signal.SIGINT, ctx.on_signal)
    signal.signal(signal.SIGTERM, ctx.on_signal)
    with RunLock(run_dir):
        return run_stages(ctx, args.until, args.only)


def cmd_decide(args) -> int:
    run_dir = Path(args.run).resolve()
    with RunLock(run_dir):                              # never while a stage is running: its next save would drop the answer
        return _decide(args, run_dir)


def _decide(args, run_dir: Path) -> int:
    state = State.load(run_dir)
    dec = state.data['decisions']
    if state.finished():
        raise RcvError(f'Lượt {run_dir.name} đã xong và không bị sửa nữa. Tạo lượt mới từ nó: '
                       f'`pipeline.py init --from-run {run_dir}`, rồi trả lời ở lượt mới.', EXIT_USAGE)

    def waiting(sid: str, what: str) -> None:
        if state.stage(sid)['status'] != 'waiting':
            raise RcvError(f'Lượt này không đang chờ {what} (chặng {sid}: {state.stage(sid)["status"]}). '
                           'Xem `pipeline.py status --run RUN`.', EXIT_USAGE)

    if args.missing:
        waiting('originals', 'câu trả lời về bài thiếu')
        dec['missing_action'] = args.missing
        state.stage('originals')['status'] = 'todo'
    elif args.remix_failed:
        waiting('remix', 'câu trả lời về bài phối lỗi')
        failed = dec.pop('remix_failed', [])
        if args.remix_failed == 'retry':
            dec['retry_token'] = time.time()
            manifest = read_json(run_dir / 'manifest.json') or {}
            for tr in manifest.get('tracks', []):
                rec_path = run_dir / 'remix' / tr['slug'] / 'job.json'
                rec = read_json(rec_path) or {}
                if rec.get('status') == 'failed':
                    # A remix that finished but failed its checks, or an API error on a finished
                    # job: retrying that job returns the same file, so a new job is made.
                    fresh = rec.get('error_type') in ('verify', 'api')
                    rec.update(status='running', attempts=0, **({'fresh': True} if fresh else {}))
                    write_json(rec_path, rec)
        else:
            dec.setdefault('rejected', {}).update({str(r): 'remix_failed' for r in failed})
            dec.setdefault('rejected_at', {}).update({str(r): time.time() for r in failed})
            dec['missing_action'] = 'skip' if args.remix_failed == 'skip' else 'backfill'
            dec.pop('missing_asked', None)
            state.stage('originals')['status'] = 'todo'
        state.stage('remix')['status'] = 'todo'
    elif args.art:
        if args.art == 'ok':
            waiting('art', 'bạn duyệt ảnh')
            art = read_json(run_dir / 'art' / 'art.json') or {}
            if not art.get('signature'):
                raise RcvError('Chưa có ảnh để duyệt: chặng art chưa chạy xong.', EXIT_USAGE)
            bad = [c for c in state.stage('art').get('checks') or [] if c['status'] == 'FAIL']
            if bad:                                         # e.g. art_unique: approving would put a repeat into the history
                raise RcvError('Ảnh này có lỗi, chưa duyệt được: ' + '; '.join(f'{c["name"]}: {c["detail"]}' for c in bad)
                               + '. Chọn --art redo (cảnh và ảnh khác) hoặc --art image --path FILE.', EXIT_USAGE)
            dec['art_approved'] = art['signature']
            cfg = cfgmod.load(getattr(args, 'config', None) or state.data['run'].get('config_path'))
            scenery.approve(cfg, run_dir)                   # its picture joins the set no later video may repeat
        elif args.art == 'redo':
            if ctx_cfg_picture(state, args):
                raise RcvError('Config đang đặt sẵn một ảnh (cover.image), nên "redo" sẽ cho lại đúng ảnh đó. '
                               'Bỏ nó trước: `pipeline.py set cover.image null`.', EXIT_USAGE)
            dec['art_seed_offset'] = int(dec.get('art_seed_offset', 0)) + 1
            dec.pop('art_image', None)
            cur = read_json(run_dir / 'art' / 'scene.json') or {}
            if cur.get('key'):                              # another scene too, not only another seed
                dec['scene_rejected'] = sorted(set(dec.get('scene_rejected') or []) | {cur['key']})
            dec.pop('scene_carry', None)
        else:
            src = Path(args.path).expanduser().resolve() if args.path else None
            if not src or not src.is_file():
                raise RcvError('--art image cần --path trỏ tới một file ảnh có thật', EXIT_USAGE)
            keep = run_dir / 'art' / f'own_picture{src.suffix.lower()}'
            keep.parent.mkdir(parents=True, exist_ok=True)
            if src != keep:
                shutil.copyfile(src, keep)                  # the run keeps its own copy
            dec['art_image'] = str(keep)
        state.stage('art')['status'] = 'todo'
    else:
        raise RcvError('Cần --missing, --remix-failed hoặc --art', EXIT_USAGE)
    state.data['waiting'] = None
    state.save()
    emit({'run': str(run_dir), 'decisions': dec})
    return EXIT_OK


def ctx_cfg_picture(state: State, args) -> bool:
    """Is a picture fixed in the config (cover.image), so a new seed changes nothing?"""
    cfg = cfgmod.load(getattr(args, 'config', None) or state.data['run'].get('config_path'))
    return bool(cfg['cover'].get('image'))


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
    p.add_argument('--period', help='giai đoạn muốn dùng, ví dụ 2010-2014 (mặc định: bốc ngẫu nhiên)')
    p.add_argument('--seed', type=int, help='seed của lần bốc (mặc định: ngẫu nhiên, được lưu trong lượt chạy)')
    p.add_argument('--sequence')
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
