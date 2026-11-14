"""REPORT.md: what the run produced, every check with its result, and what the human still
has to listen to or look at. Nothing here is a claim the scripts did not measure."""
from __future__ import annotations

import os
import time
from pathlib import Path

from .common import check, fmt_hms, read_json, worst, write_text
from .cover import playlist_tracks
from .stemforge import JOBS_DIR

DELIVERABLES = ('video.mp4', 'thumbnail.jpg', 'cover.png', 'mix.wav', 'transitions_preview.mp3', 'youtube.md',
                'youtube.json', 'manifest.json')
OPTIONAL = ('transitions_preview.mp3',)           # a one-song run has no handover


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file()) if path.is_dir() else 0


def _mb(n: int) -> str:
    return f'{n / 1e3:.0f} KB' if n < 1e6 else f'{n / 1e6:.0f} MB' if n < 1e9 else f'{n / 1e9:.2f} GB'


def _waits(mixinfo: dict, cfg: dict) -> list[str]:
    wait = mixinfo.get('waits') or {}
    out = []
    if wait.get('start_s') is not None:
        out.append(f'- Từ đầu bản mix tới câu hát đầu tiên: {wait["start_s"]:.1f} giây')
    gaps = [g for g in wait.get('gaps_s') or [] if g is not None]
    if gaps:
        out.append(f'- Không lời giữa hai bài: {min(gaps):.1f}–{max(gaps):.1f} giây' if min(gaps) != max(gaps) else
                   f'- Không lời giữa hai bài: {gaps[0]:.1f} giây')
    if out:
        mx = cfg['mix']
        modes = {t.get('mode') for t in mixinfo.get('transitions') or []}
        join = [f'`mix.transition` = {mx.get("transition")}']             # only the keys that shaped this mix
        if 'overlap' in modes:
            join.append(f'`mix.overlap_bars` = {mx.get("overlap_bars")}')
        if 'crossfade' in modes:
            join.append(f'`mix.crossfade_s` = {mx.get("crossfade_s")}')
        out.append(f'  (đổi bằng `mix.lead_in_bars` = {mx.get("lead_in_bars")}, `mix.tail_bars` = {mx.get("tail_bars")}, '
                   + ', '.join(join) + '; rồi `pipeline.py init --from-run` để ghép lại)')
    return out


def _verdict(checks: list[dict]) -> str:
    """A stage's result for the table. A SKIP is something nobody verified: it is named next to
    the result, never folded into PASS."""
    skipped = sum(c['status'] == 'SKIP' for c in checks)
    return worst(checks) + (f' ({skipped} SKIP)' if skipped and worst(checks) != 'SKIP' else '')


def build(run_dir, cfg: dict, state):
    run_dir = Path(run_dir)
    data = state.data
    info = data['run']
    manifest = read_json(run_dir / 'manifest.json') or {}
    mixinfo = read_json(run_dir / 'mix' / 'mix_report.json') or {}
    tracks = playlist_tracks(manifest) if manifest.get('playlist') else []
    chart = manifest.get('chart') or {}
    checks = []
    for name in DELIVERABLES:
        path = run_dir / name
        if path.is_file() and path.stat().st_size > 0:
            checks.append(check(name, 'PASS', _mb(path.stat().st_size)))
        elif name in OPTIONAL and len(tracks) < 2:
            checks.append(check(name, 'SKIP', 'bản mix chỉ có một bài'))
        else:
            checks.append(check(name, 'FAIL', 'thiếu file'))

    stages = [s for s in data['stages'] if s['id'] != 'report']
    every = [c for s in stages for c in s.get('checks') or []] + checks
    counts = {k: sum(c['status'] == k for c in every) for k in ('PASS', 'WARN', 'FAIL', 'SKIP')}
    video = stages[[s['id'] for s in stages].index('video')].get('outputs') or {}

    out = [f'# Báo cáo lượt chạy `{info["name"]}`', '',
           f'- Danh sách bốc: {chart.get("title")} ngày {chart.get("date")} ({info.get("chart_source")})',
           f'- Số bài: {len(tracks)} (bốc ngẫu nhiên, không phải bảng xếp hạng: không ghi "Top N")',
           f'- Độ dài bản mix: {fmt_hms(mixinfo.get("duration", 0))}',
           *_waits(mixinfo, cfg),
           f'- Phép kiểm: {counts["PASS"]} PASS, {counts["WARN"]} WARN, {counts["FAIL"]} FAIL, {counts["SKIP"]} SKIP',
           f'- Lập lúc: {time.strftime("%Y-%m-%d %H:%M")}', '', '## Sản phẩm', '']
    for name in DELIVERABLES:
        path = run_dir / name
        out.append(f'- `{path}`' + (f' ({_mb(path.stat().st_size)})' if path.is_file() else ' — **thiếu**'))

    out += ['', '## Việc bạn nên tự nghe hoặc xem', '']
    preview = mixinfo.get('preview') or {}
    if preview.get('index'):
        out.append(f'- Nghe các đoạn chuyển bài: `{preview["file"]}`')
        for item, tr in zip(preview['index'], mixinfo.get('transitions', [])):
            out.append(f'  - {item["at_in_preview"]} trong file nghe thử (≈ {item["at_in_mix"]} trong bản mix): bài {item["from"]} → {item["to"]}: {tr["detail"]}')
    if video.get('frame'):
        out.append(f'- Xem khung hình video (kiểu `{video.get("look")}`): `{video["frame"]}`')
    scene = read_json(run_dir / 'art' / 'scene.json')
    if scene:
        out.append(f'- Tranh: {scene["labels"]} ({scene["reason"]}). Sổ các cảnh và tranh đã dùng: `art_history.json` '
                   'và thư mục `art_history/` cạnh file config')
    out.append(f'- Xem thumbnail: `{run_dir / "thumbnail.jpg"}`')
    warned = [(s['label'], c) for s in stages for c in s.get('checks') or [] if c['status'] == 'WARN']
    for label, c in warned:
        out.append(f'- WARN ở "{label}" · {c["name"]}: {c["detail"]}')

    out += ['', '## Các chặng', '', '| Chặng | Trạng thái | Kết quả kiểm | Thời gian |', '|---|---|---|---|']
    for n, s in enumerate(stages):
        out.append(f'| S{n} {s["label"]} | {s["status"]} | {_verdict(s.get("checks") or [])} | {fmt_hms(s.get("elapsed_s") or 0)} |')
    carried = (data.get('decisions') or {}).get('carried_from')
    if carried:
        out += ['', f'Lượt này dùng lại bài gốc và bản phối của lượt `{Path(carried).name}`, nên thời gian của chặng tải và chặng phối '
                    'ở trên không phải thời gian đã bỏ ra để làm chúng.']
    out += ['', '## Phép kiểm', '', '| Chặng | Phép kiểm | Kết quả | Chi tiết |', '|---|---|---|---|']
    for s in stages:
        for c in s.get('checks') or []:
            out.append(f'| {s["label"]} | {c["name"]} | {c["status"]} | {str(c["detail"]).replace("|", "/").replace(chr(10), " ")} |')
    for c in checks:
        out.append(f'| Báo cáo | {c["name"]} | {c["status"]} | {c["detail"]} |')
    skipped = [f'{s["label"]} · {c["name"]}: {c["detail"]}' for s in stages for c in s.get('checks') or [] if c['status'] == 'SKIP']
    skipped += [f'Báo cáo · {c["name"]}: {c["detail"]}' for c in checks if c['status'] == 'SKIP']
    if skipped:
        out += ['', '## Chưa xác minh', ''] + [f'- {line}' for line in skipped]

    out += ['', '## Danh sách bài', '', '| # | Mốc | Số trong danh sách bốc | Bài | Nghệ sĩ | Sáng tác | Nhà phân phối | BPM | Tông | Co giãn tempo |', '|---|---|---|---|---|---|---|---|---|---|']
    for item, tr in zip(manifest.get('playlist', []), tracks):
        rep = read_json(run_dir / 'remix' / tr['slug'] / 'remix_report.json') or {}
        ratio = (rep.get('tempo') or {}).get('tempo_ratio')
        out.append(f'| {item["position"]} | {item.get("chapter", "")} | {tr["rank"]} | {tr["title"]} | {tr["artist"]} | '
                   f'{", ".join(tr.get("composers") or []) or "?"} | '
                   f'{tr.get("distributor") or "?"} | {tr.get("bpm") or "?"} | {tr.get("key") or "?"} | {f"{ratio:.3f}×" if ratio else "?"} |')
    out += ['', 'Bài gốc là tác phẩm có bản quyền, nên video có thể bị claim Content ID; cột "Nhà phân phối" cho biết bên '
            'nhiều khả năng đứng tên claim. Skill không đăng video và không quyết thay bạn việc đăng.', '',
            '## Lệnh NCT đã chạy', '']
    cmds = data.get('nct_commands') or []
    if cmds:
        out += [f'- {time.strftime("%H:%M:%S", time.localtime(c["at"]))} `{c["command"]}` — '
                f'{"gửi request tới NCT" if c["live"] else "không gửi request"}, mã thoát {c["exit"]}' for c in cmds]
        out.append(f'\nTổng: {sum(1 for c in cmds if c["live"])} lệnh có gửi request, {sum(1 for c in cmds if not c["live"])} lệnh offline.')
    elif carried:
        out.append(f'- Lượt này không gửi request nào tới NCT: danh sách bốc và bài hát lấy lại từ lượt `{Path(carried).name}` '
                   f'(nguồn của lượt đó: {info.get("chart_source")}).')
    else:
        out.append('- Không chạy lệnh NCT nào gửi request (dùng dữ liệu đã lưu).')

    out += ['', '## Job StemForge của lượt này', '']
    root = JOBS_DIR
    jobs = []
    for tr in manifest.get('tracks', []):
        rec = read_json(run_dir / 'remix' / tr['slug'] / 'job.json') or {}
        if rec.get('job_id'):
            folder = root / rec['job_id']
            jobs.append((tr['title'], rec['job_id'], _size(folder) if folder.is_dir() else None))
    policy = cfg['remix'].get('cleanup_jobs')
    for title, job_id, size in jobs:
        gone = 'đã xoá sau khi chép' if policy == 'delete_after_copy' else f'không thấy thư mục job trong `{root}` (skill không xoá nó)'
        out.append(f'- {title}: job `{job_id}` — ' + (f'còn trên đĩa, {_mb(size)}' if size is not None else gone))
    kept = sum(s for _, _, s in jobs if s)
    out.append(f'\nChính sách dọn: `{policy}`.' + (f' Đang giữ {_mb(kept)}; xoá bằng tay các thư mục trong `{root}` nếu không cần nữa.' if kept else ''))
    path = run_dir / 'REPORT.md'
    write_text(path, '\n'.join(out) + '\n')
    data['result'] = {'video': str(run_dir / 'video.mp4'), 'thumbnail': str(run_dir / 'thumbnail.jpg'),
                      'youtube_md': str(run_dir / 'youtube.md'), 'report': str(path)}
    checks.append(check('report', 'PASS', str(path)))
    return checks, {'report': str(path), 'counts': counts}
