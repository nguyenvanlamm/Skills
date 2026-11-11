#!/usr/bin/env python3
"""Helpers for the YouTube package of a run.

  youtube_meta.py facts --run RUN       the facts the metadata may use: tracks, credits, chapter lines,
                                        counts, whether "Top N" is allowed, the limits and their status
  youtube_meta.py validate --run RUN    check youtube/youtube.json + youtube/evidence.json; on success
                                        write youtube.md and youtube.json in the run folder

The model writes RUN/youtube/youtube.json and RUN/youtube/evidence.json (see
references/youtube_metadata.md). This script never edits state.json, so it is safe to run while
the video renders; the pipeline's `youtube` stage runs the same validation afterwards.
Prints JSON. Exit 0 no FAIL, 1 at least one FAIL, 2 usage.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rcvlib import youtube  # noqa: E402
from rcvlib.common import RcvError, emit, read_json, worst  # noqa: E402
from rcvlib.cover import playlist_tracks  # noqa: E402


def facts(run_dir: Path) -> dict:
    manifest = read_json(run_dir / 'manifest.json')
    mixinfo = read_json(run_dir / 'mix' / 'mix_report.json')
    if not manifest or not mixinfo:
        raise RcvError('Cần manifest.json và mix/mix_report.json: chặng ghép mix phải xong trước.', 2)
    tracks = playlist_tracks(manifest)
    limits = youtube.load_limits()
    art = read_json(run_dir / 'art' / 'art.json') or {}
    reminders = []
    if mixinfo['duration'] > 900 and (limits.get('long_video_requirement') or {}).get('verified'):
        reminders.append('Video dài hơn 15 phút: kênh phải được xác minh mới tải lên được (' + limits['long_video_requirement']['source_url'] + ').')
    reminders.append('Thumbnail tuỳ chỉnh cũng cần kênh đã xác minh.')
    return {
        'visuals': {'art_mode': art.get('mode'), 'dj_picture_is_ai': art.get('mode') == 'provider',
                    'note': 'Chỉ viết "ảnh DJ do AI tạo" khi dj_picture_is_ai là true; phần nhạc nền thì luôn do AI tạo.'},
        'account_reminders': reminders,
        'chart': manifest['chart'], 'track_count': len(tracks), 'exact_top': manifest.get('exact_top'),
        'may_say_top_n': bool(manifest.get('exact_top')),
        'mix_duration': mixinfo['duration'], 'chapter_lines': youtube.chapter_lines(run_dir),
        'tracks': [{'position': i, 'chart_rank': t['rank'], 'title': t['title'], 'artist': t['artist'],
                    'chart_title': t['chart_title'], 'distributor': t['distributor'], 'bpm': t.get('bpm'), 'key': t.get('key')}
                   for i, t in enumerate(tracks, 1)],
        'limits': {k: {'value': v.get('value'), 'unit': v.get('unit'), 'verified': bool(v.get('verified'))} for k, v in limits.items()},
        'banned_phrases': [r['why'] for r in youtube.load_rules().get('banned_phrases', [])],
        'write_to': {'metadata': str(run_dir / 'youtube' / 'youtube.json'), 'evidence': str(run_dir / 'youtube' / 'evidence.json')},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('facts', 'validate'):
        sub.add_parser(name).add_argument('--run', required=True)
    args = ap.parse_args(argv)
    run_dir = Path(args.run).resolve()
    try:
        if args.cmd == 'facts':
            (run_dir / 'youtube').mkdir(exist_ok=True)
            emit(facts(run_dir))
            return 0
        checks = youtube.validate(run_dir)
        verdict = worst(checks)
        out = {'worst': verdict, 'checks': [c for c in checks if c['status'] != 'PASS'],
               'passed': sum(c['status'] == 'PASS' for c in checks), 'total': len(checks)}
        if verdict != 'FAIL':
            out['youtube_md'] = str(youtube.render_md(run_dir))
        emit(out)
        return 1 if verdict == 'FAIL' else 0
    except RcvError as exc:
        emit({'exit': exc.code, 'error': str(exc)})
        return exc.code


if __name__ == '__main__':
    sys.exit(main())
