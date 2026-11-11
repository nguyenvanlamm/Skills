"""The YouTube upload package: hard checks on youtube.json, then youtube.md for copy-paste.

The model writes youtube/youtube.json and youtube/evidence.json (references/youtube_metadata.md
says how). This module checks them against the manifest and against limits that carry an
official source; a limit that is not verified makes its check SKIP, never PASS.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .common import SKILL_DIR, check, fold, read_json, worst, write_text
from .cover import playlist_tracks

REQUIRED = ('primary_keyword', 'titles', 'description', 'tags', 'hashtags', 'form', 'pinned_comment', 'playlist')
FORM_KEYS = ('category', 'video_language', 'audience', 'altered_content', 'license', 'embedding')
SCORE_KEYS = ('keyword', 'clarity', 'honesty', 'appeal')
VOLUME_KEYS = ('volume', 'search_volume', 'monthly_searches', 'searches')
VOLUME_TEXT = re.compile(
    r'\d[\d.,]*\s*(k|nghìn|ngàn|triệu|tr|m)?\s*(lượt\s*tìm|lượt\s*tra|searches|search(es)?\s*/|tìm\s*kiếm\s*(/|mỗi|một|hàng)\s*tháng)'
    r'|search\s*volume|lượng\s*tìm\s*kiếm\s*[:=]?\s*\d', re.IGNORECASE)
COUNT_CLAIM = re.compile(r'(?<![\d:.,])(\d{1,3})\s*(bài|ca khúc|bản|track|tracks|songs?|hits?)\b', re.IGNORECASE)
TOP_CLAIM = re.compile(r'\btop\s*(\d{1,3})\b', re.IGNORECASE)


def load_limits() -> dict:
    data = read_json(SKILL_DIR / 'references' / 'youtube_limits.json') or {}
    return data.get('limits') or {}


def load_rules() -> dict:
    return read_json(SKILL_DIR / 'assets' / 'metadata_rules.json') or {'banned_phrases': []}


def chapter_lines(run_dir) -> list[str]:
    mixinfo = read_json(Path(run_dir) / 'mix' / 'mix_report.json') or {}
    return [f'{c["stamp"]} {c["label"]}' for c in mixinfo.get('chapters', [])]


def tags_length(tags: list[str]) -> int:
    """Conservative count: every tag, a comma between tags, and two quote marks around a tag
    that contains a space."""
    return sum(len(t) + (2 if ' ' in t else 0) for t in tags) + max(0, len(tags) - 1)


def _limit(limits: dict, key: str):
    item = limits.get(key) or {}
    return (item.get('value'), True) if item.get('verified') and isinstance(item.get('value'), (int, float)) else (item.get('value'), False)


def _texts(meta: dict) -> dict:
    return {'titles': ' \n '.join(t.get('text', '') for t in meta.get('titles', []) if isinstance(t, dict)),
            'description': meta.get('description', ''), 'tags': ' , '.join(meta.get('tags', [])),
            'hashtags': ' '.join(meta.get('hashtags', [])), 'pinned_comment': meta.get('pinned_comment', ''),
            'playlist': meta.get('playlist', '')}


def _has_key(obj, names) -> bool:
    if isinstance(obj, dict):
        return any(k.lower() in names or _has_key(v, names) for k, v in obj.items())
    if isinstance(obj, list):
        return any(_has_key(v, names) for v in obj)
    return False


def validate(run_dir) -> list[dict]:
    run_dir = Path(run_dir)
    ydir = run_dir / 'youtube'
    meta = read_json(ydir / 'youtube.json')
    manifest = read_json(run_dir / 'manifest.json') or {}
    mixinfo = read_json(run_dir / 'mix' / 'mix_report.json') or {}
    limits, rules = load_limits(), load_rules()
    checks = []
    if not isinstance(meta, dict):
        return [check('schema', 'FAIL', 'không đọc được youtube/youtube.json')]
    missing = [k for k in REQUIRED if not meta.get(k)]
    titles = [t for t in meta.get('titles', []) if isinstance(t, dict) and t.get('text')]
    if len(titles) != 3:
        missing.append('titles (cần đúng 3 phương án)')
    elif any(not all(k in (t.get('scores') or {}) for k in SCORE_KEYS) or not t.get('why') or not t.get('angle') for t in titles):
        missing.append(f'titles[*].angle/why/scores ({", ".join(SCORE_KEYS)})')
    form = meta.get('form') or {}
    missing += [f'form.{k}' for k in FORM_KEYS if not (isinstance(form.get(k), dict) and form[k].get('value') and form[k].get('why'))]
    checks.append(check('schema', 'FAIL' if missing else 'PASS', f'thiếu: {missing}' if missing else 'đủ các trường'))
    if missing and not titles:
        return checks
    tracks = playlist_tracks(manifest) if manifest.get('playlist') else []
    n = len(tracks)
    primary = fold(meta.get('primary_keyword', ''))
    chosen = titles[0]['text'] if titles else ''
    desc = meta.get('description', '')
    tags = [t for t in meta.get('tags', []) if isinstance(t, str)]
    hashtags = [h for h in meta.get('hashtags', []) if isinstance(h, str)]

    # lengths
    cap, ok = _limit(limits, 'title_max_chars')
    if ok:
        long = [f'"{t["text"][:30]}…" ({len(t["text"])})' for t in titles if len(t['text']) > cap]
        checks.append(check('title_length', 'FAIL' if long else 'PASS', f'vượt {cap} ký tự: {long}' if long else
                            f'dài nhất {max(len(t["text"]) for t in titles)}/{cap} ký tự'))
    else:
        checks.append(check('title_length', 'SKIP', 'giới hạn độ dài tiêu đề chưa được xác minh'))
    bad_chars = [t['text'] for t in titles if re.search(r'[<>]', t['text'])] + (['mô tả'] if re.search(r'[<>]', desc) else [])
    checks.append(check('forbidden_chars', 'FAIL' if bad_chars else 'PASS', f'có ký tự < hoặc >: {bad_chars}' if bad_chars else 'không có < >'))
    # YouTube Help states the description limit in characters, the Data API reference in bytes.
    # Both are enforced; Vietnamese text reaches the byte limit first.
    cap, ok = _limit(limits, 'description_max_chars')
    cap_b, ok_b = _limit(limits, 'description_max_bytes')
    n_chars, n_bytes = len(desc), len(desc.encode('utf-8'))
    if ok or ok_b:
        over = ([f'{n_chars}/{int(cap)} ký tự'] if ok and n_chars > cap else []) + ([f'{n_bytes}/{int(cap_b)} byte'] if ok_b and n_bytes > cap_b else [])
        checks.append(check('description_length', 'FAIL' if over else 'PASS', 'vượt giới hạn: ' + ', '.join(over) if over else
                            f'{n_chars} ký tự' + (f'/{int(cap)}' if ok else '') + f', {n_bytes} byte' + (f'/{int(cap_b)}' if ok_b else '')))
    else:
        checks.append(check('description_length', 'SKIP', 'giới hạn độ dài mô tả chưa được xác minh'))
    cap, ok = _limit(limits, 'tags_max_chars')
    if ok:
        checks.append(check('tags_length', 'PASS' if tags_length(tags) <= cap else 'FAIL', f'{tags_length(tags)}/{cap} ký tự (tính cả dấu phẩy và ngoặc kép)'))
    else:
        checks.append(check('tags_length', 'SKIP', 'giới hạn tổng độ dài tags chưa được xác minh'))

    # keyword placement
    checks.append(check('title_keyword', 'PASS' if primary and primary in fold(chosen) else 'FAIL',
                        f'từ khoá chính "{meta.get("primary_keyword")}" ' + ('có' if primary and primary in fold(chosen) else 'không có') + ' trong tiêu đề được chọn'))
    opening = ' '.join([line for line in desc.splitlines() if line.strip()][:2])
    checks.append(check('description_opening', 'PASS' if primary and primary in fold(opening) else 'FAIL',
                        'từ khoá chính ' + ('có' if primary and primary in fold(opening) else 'không có') + ' trong hai dòng đầu của mô tả'))

    # honest numbers
    wrong = []
    for label, text in (('tiêu đề', '\n'.join(t['text'] for t in titles)), ('mô tả (5 dòng đầu)', '\n'.join(desc.splitlines()[:5])),
                        ('bình luận ghim', meta.get('pinned_comment', '')), ('playlist', meta.get('playlist', ''))):
        for m in COUNT_CLAIM.finditer(text):
            if int(m.group(1)) != n:
                wrong.append(f'{label}: "{m.group(0)}" nhưng mix có {n} bài')
        for m in TOP_CLAIM.finditer(text):
            if int(m.group(1)) != n:
                wrong.append(f'{label}: "{m.group(0)}" nhưng mix có {n} bài')
            elif not manifest.get('exact_top'):
                wrong.append(f'{label}: "{m.group(0)}" nhưng các bài không phải đúng hạng 1–{n} của BXH')
    checks.append(check('count_claims', 'FAIL' if wrong else 'PASS', '; '.join(wrong[:4]) if wrong else f'các con số về số bài khớp manifest ({n} bài)'))

    # chapters
    want = chapter_lines(run_dir)
    lines = [line.strip() for line in desc.splitlines()]
    have = [line for line in lines if re.match(r'^(\d+:)?\d{1,2}:\d{2}\s', line)]
    checks.append(check('description_chapters', 'PASS' if want and have == want else 'FAIL',
                        'chapter trong mô tả trùng mốc của bản mix' if want and have == want else
                        f'mô tả có {len(have)} dòng mốc, bản mix có {len(want)}; dòng đầu lệch: '
                        + next((f'"{h}" ≠ "{w}"' for h, w in zip(have + [''] * len(want), want) if h != w), 'thiếu hoặc thừa dòng')))
    marks = [c['seconds'] for c in mixinfo.get('chapters', [])]
    total = mixinfo.get('total_seconds')
    problems = []
    if marks:
        if marks[0] != 0:
            problems.append('mốc đầu không phải 00:00')
        cap, ok = _limit(limits, 'chapters_min_count')
        if ok and len(marks) < cap:
            problems.append(f'chỉ có {len(marks)} mốc, YouTube cần ít nhất {int(cap)}')
        cap2, ok2 = _limit(limits, 'chapter_min_seconds')
        gaps = [b - a for a, b in zip(marks, marks[1:] + [total])]
        if ok2 and min(gaps) < cap2:
            problems.append(f'có chapter dài {min(gaps)}s, ngắn hơn {int(cap2)}s')
        if marks != sorted(set(marks)):
            problems.append('các mốc không tăng dần')
        status = 'FAIL' if problems else 'PASS' if ok and ok2 else 'SKIP'
        checks.append(check('chapter_rules', status, '; '.join(problems) if problems else
                            f'{len(marks)} mốc, bắt đầu 00:00' if status == 'PASS' else 'quy tắc chapter chưa được xác minh'))

    # credits and disclosure
    low = fold(desc)
    uncredited = []
    for tr in tracks:
        if fold(tr['title']) not in low:
            uncredited.append(tr['title'])
        for artist in re.split(r'\s*[,&]\s*', tr['artist'] or ''):
            if artist and fold(artist) not in low:
                uncredited.append(f'{artist} ({tr["title"]})')
    checks.append(check('description_credits', 'FAIL' if uncredited else 'PASS',
                        f'mô tả chưa ghi: {sorted(set(uncredited))[:6]}' if uncredited else 'mô tả ghi đủ tên bài và nghệ sĩ gốc'))
    checks.append(check('ai_disclosure', 'PASS' if re.search(r'\bAI\b', desc) else 'FAIL',
                        'mô tả có nói về việc dùng AI' if re.search(r'\bAI\b', desc) else 'mô tả chưa nói bản phối và ảnh DJ có dùng AI'))

    # tags and hashtags
    seen, dupes = set(), []
    for t in tags:
        key = ' '.join(t.split()).casefold()        # "nhạc remix" and "nhac remix" are two tags, not a duplicate
        if key in seen:
            dupes.append(t)
        seen.add(key)
    checks.append(check('tags_unique', 'FAIL' if dupes else 'PASS', f'trùng: {dupes[:5]}' if dupes else f'{len(tags)} tag, không trùng'))
    report = read_json(run_dir / 'nct' / 'report.json') or {}
    in_mix = {fold(a) for tr in tracks for a in re.split(r'\s*[,&]\s*', (tr['artist'] or '') + ',' + (tr.get('chart_artist') or '')) if a}
    others = {fold(a) for s in report.get('songs', []) for a in re.split(r'\s*[,&]\s*', s.get('artist') or '') if a} - in_mix
    strangers = [t for t in tags + [h.lstrip('#') for h in hashtags] if fold(t) in others or fold(t).replace(' ', '') in {o.replace(' ', '') for o in others}]
    checks.append(check('tags_artists', 'FAIL' if strangers else 'PASS',
                        f'tag nhắc nghệ sĩ không có trong mix: {strangers[:5]}' if strangers else 'không gắn tên nghệ sĩ ngoài bản mix'))
    bad_form = [h for h in hashtags if not re.fullmatch(r'#[^\s#]+', h)]
    cap, ok = _limit(limits, 'hashtags_max_count')
    total_tags = len(hashtags) + len(set(re.findall(r'(?<!\S)#[^\s#]+', desc)) - set(hashtags))
    if bad_form or not hashtags:
        checks.append(check('hashtags', 'FAIL', f'hashtag sai dạng: {bad_form}' if bad_form else 'chưa có hashtag'))
    elif ok:
        checks.append(check('hashtags', 'PASS' if total_tags <= cap else 'FAIL', f'{total_tags} hashtag (YouTube bỏ qua tất cả khi vượt {int(cap)})'))
    else:
        checks.append(check('hashtags', 'SKIP', f'{total_tags} hashtag; giới hạn số hashtag chưa được xác minh'))
    stuffed = len(re.findall(r'[,;]', next((line for line in reversed(lines) if line.count(',') >= 12), '')))
    checks.append(check('tag_stuffing', 'FAIL' if stuffed else 'PASS',
                        'mô tả có một dòng nhồi từ khoá ngăn bằng dấu phẩy' if stuffed else 'mô tả không nhồi danh sách từ khoá'))

    # claims
    texts = _texts(meta)
    hits = []
    for rule in rules.get('banned_phrases', []):
        rx = re.compile(rule['pattern'], re.IGNORECASE)
        for field, text in texts.items():
            if rule.get('fields') and field not in rule['fields']:
                continue
            m = rx.search(text)
            if m:
                hits.append(f'{field}: "{m.group(0)}" ({rule["why"]})')
    checks.append(check('banned_phrases', 'FAIL' if hits else 'PASS', '; '.join(hits[:4]) if hits else 'không có cụm bị cấm'))
    evidence = read_json(ydir / 'evidence.json')
    invented = [f for f, text in texts.items() if VOLUME_TEXT.search(text)]
    if _has_key(meta, VOLUME_KEYS) or _has_key(evidence, VOLUME_KEYS):
        invented.append('trường volume trong JSON')
    checks.append(check('search_volume_claims', 'FAIL' if invented else 'PASS',
                        f'có con số tìm kiếm không nguồn ở: {invented}' if invented else 'không có con số lượng tìm kiếm'))
    if not isinstance(evidence, dict):
        checks.append(check('evidence', 'FAIL', 'thiếu youtube/evidence.json'))
    elif evidence.get('live') is False:
        checks.append(check('evidence', 'WARN', f'lượt này không có dữ liệu trực tiếp: {evidence.get("reason", "không rõ lý do")}'))
    else:
        queries = [q for q in evidence.get('queries', []) if q.get('query') and any(r.get('url') and r.get('title') for r in q.get('results', []))]
        ok_ev = len(queries) >= 3 and bool(evidence.get('collected_on'))
        checks.append(check('evidence', 'PASS' if ok_ev else 'FAIL',
                            f'{len(queries)} truy vấn có kết quả kèm URL, ngày {evidence.get("collected_on")}' if ok_ev else
                            'cần ít nhất 3 truy vấn, mỗi truy vấn có kết quả kèm title + url, và collected_on'))
    write_text(ydir / 'validation.json', json.dumps({'worst': worst(checks), 'checks': checks}, ensure_ascii=False, indent=2) + '\n')
    return checks


def render_md(run_dir) -> Path:
    """youtube.md for copy-paste, written only when validation has no FAIL."""
    run_dir = Path(run_dir)
    ydir = run_dir / 'youtube'
    meta = read_json(ydir / 'youtube.json')
    val = read_json(ydir / 'validation.json') or {'checks': []}
    evidence = read_json(ydir / 'evidence.json') or {}
    fence = '```'
    titles = meta['titles']
    out = ['# Thông tin đăng YouTube', '', f'Bản mix: `{run_dir.name}` · từ khoá chính: **{meta["primary_keyword"]}**'
           + (f' · phụ: {", ".join(meta.get("secondary_keywords", []))}' if meta.get('secondary_keywords') else ''), '',
           '## Tiêu đề', '', fence, titles[0]['text'], fence, '',
           f'Lý do chọn: {titles[0]["why"]}', '', '| # | Phương án | Góc | Điểm | Ký tự |', '|---|---|---|---|---|']
    for i, t in enumerate(titles, 1):
        score = ' · '.join(f'{k} {t["scores"].get(k)}' for k in SCORE_KEYS)
        out.append(f'| {i} | {t["text"]} | {t["angle"]} | {score} | {len(t["text"])} |')
    out += ['', '## Mô tả', '', fence, meta['description'].rstrip(), fence, '', f'{len(meta["description"])} ký tự.', '',
            '## Tags', '', fence, ', '.join(meta['tags']), fence, '', f'{tags_length(meta["tags"])} ký tự.', '',
            '## Hashtag', '', fence, ' '.join(meta['hashtags']), fence, '', '## Chapter', '', fence, *chapter_lines(run_dir), fence, '',
            '## Các lựa chọn trong form', '', '| Mục | Chọn | Lý do |', '|---|---|---|']
    names = {'category': 'Danh mục', 'video_language': 'Ngôn ngữ video', 'audience': 'Đối tượng người xem',
             'altered_content': 'Nội dung được chỉnh sửa hoặc tổng hợp (AI)', 'license': 'Giấy phép', 'embedding': 'Cho phép nhúng'}
    for key in FORM_KEYS:
        out.append(f'| {names[key]} | {meta["form"][key]["value"]} | {meta["form"][key]["why"]} |')
    out += ['', f'Thumbnail: `{run_dir / "thumbnail.jpg"}`', f'Video: `{run_dir / "video.mp4"}`', '',
            '## Bình luận ghim', '', fence, meta['pinned_comment'].rstrip(), fence, '', '## Playlist gợi ý', '', meta['playlist'], '',
            '## Căn cứ từ khoá', '']
    if evidence.get('live') is False:
        out.append(f'Lượt này không có dữ liệu trực tiếp ({evidence.get("reason", "không rõ lý do")}); từ khoá lấy từ danh sách nền.')
    else:
        out.append(f'Quan sát ngày {evidence.get("collected_on")}:')
        for q in evidence.get('queries', []):
            out.append(f'- `{q.get("query")}`: ' + '; '.join(f'[{r.get("title", "")[:60]}]({r.get("url")})' for r in q.get('results', [])[:3]))
    out += ['', '## Kết quả kiểm tra', '', '| Phép kiểm | Kết quả | Chi tiết |', '|---|---|---|']
    out += [f'| {c["name"]} | {c["status"]} | {c["detail"]} |' for c in val['checks']]
    path = run_dir / 'youtube.md'
    write_text(path, '\n'.join(out) + '\n')
    shutil.copyfile(ydir / 'youtube.json', run_dir / 'youtube.json')
    return path
