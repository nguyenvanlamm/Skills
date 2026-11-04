// posts.txt: a plain-text, copy-ready report of the posts to publish. Only the chosen variant of
// each platform (one per subreddit on Reddit), a posting schedule in the developer's local time,
// then short notes. The other variants stay in posts.json / posts.md.
// Rendered by validate_posts.dart --render-txt FILE [--txt-lang vi|en] [--local-tz ICT].

import 'dart:io';

const int _width = 72;
const int _labelW = 16;

const Map<String, Map<String, String>> _l = {
  'vi': {
    'title': 'BÀI ĐĂNG NHÁP',
    'created': 'Tạo ngày',
    'not_posted': 'Chưa đăng gì cả',
    'language': 'Ngôn ngữ',
    'videos': 'Video',
    'videos_where': 'thư mục video/ cạnh file này',
    'intro1': 'Mỗi nền tảng chỉ có bài được chọn để đăng.',
    'intro2': 'Phần nằm dưới dòng gạch là chữ để copy nguyên văn.',
    'schedule': 'LỊCH ĐĂNG',
    'video': 'Video',
    'post_at': 'Đăng lúc',
    'sound': 'Âm thanh',
    'sound_original': 'Âm thanh gốc của game',
    'sound_trending': 'Nhạc trend',
    'cover': 'Ảnh bìa',
    'cover_at': 'giây {t}',
    'text': 'chữ',
    'hook': 'Chữ trên video',
    'first_2s': '2 giây đầu',
    'hook_burned': 'đã có chữ hook',
    'hook_add': 'thêm chữ hook trong app',
    'caption': 'Caption',
    'pinned': 'Bình luận ghim',
    'reddit_note': 'mỗi subreddit một bài, cách nhau vài ngày',
    'rules': 'Luật',
    'rules_checked': 'Kiểm tra luật',
    'flair': 'Flair',
    'none': '(không có)',
    'r_title': 'Tiêu đề',
    'body': 'Nội dung',
    'first_comment': 'Bình luận đầu tiên (chứa link)',
    'li_post': 'Bài viết',
    'x_post': 'Bài đăng',
    'thread': 'Thread',
    'reply': 'Trả lời đầu tiên (chứa link)',
    'alt': 'Alt text cho video',
    'notes': 'LƯU Ý TRƯỚC KHI ĐĂNG',
    'n_trends': 'Trend chưa được kiểm tra online cho lượt này (xem review_report.md).',
    'n_rules': 'Luật subreddit chỉ biết gián tiếp qua kết quả tìm kiếm: đọc sidebar trước khi đăng',
    'n_sound': 'Chọn nhạc trong app trước khi đăng',
    'n_backup': 'Bài dự phòng nằm trong posts.md và posts.json',
    'assumptions': 'Giả định của lượt này:',
    'local_ICT': 'giờ VN',
    'lang_en': 'tiếng Anh',
    'lang_vi': 'tiếng Việt',
    'days': 'Thứ Hai,Thứ Ba,Thứ Tư,Thứ Năm,Thứ Sáu,Thứ Bảy,Chủ Nhật',
  },
  'en': {
    'title': 'SOCIAL POST DRAFTS',
    'created': 'Created',
    'not_posted': 'Nothing has been posted',
    'language': 'Language',
    'videos': 'Videos',
    'videos_where': 'the video/ folder next to this file',
    'intro1': 'Each platform lists only the post chosen for publishing.',
    'intro2': 'Text under a dashed line is meant to be copied as is.',
    'schedule': 'SCHEDULE',
    'video': 'Video',
    'post_at': 'Post at',
    'sound': 'Sound',
    'sound_original': 'Original game audio',
    'sound_trending': 'Trending sound',
    'cover': 'Cover',
    'cover_at': 'at {t} s',
    'text': 'text',
    'hook': 'On-screen hook',
    'first_2s': 'first 2 s',
    'hook_burned': 'hook already burned in',
    'hook_add': 'add the hook text in the app',
    'caption': 'Caption',
    'pinned': 'Pinned comment',
    'reddit_note': 'one post per subreddit, a few days apart',
    'rules': 'Rules',
    'rules_checked': 'Rules checked',
    'flair': 'Flair',
    'none': '(none)',
    'r_title': 'Title',
    'body': 'Body',
    'first_comment': 'First comment (with the link)',
    'li_post': 'Post',
    'x_post': 'Post',
    'thread': 'Thread',
    'reply': 'First reply (with the link)',
    'alt': 'Video alt text',
    'notes': 'BEFORE POSTING',
    'n_trends': 'Trends were not checked online for this run (see review_report.md).',
    'n_rules': 'Subreddit rules are second-hand (search results only): read the sidebar first',
    'n_sound': 'Pick the sound in the app before posting',
    'n_backup': 'The other variants are in posts.md and posts.json',
    'assumptions': 'Assumptions for this run:',
    'local_ICT': 'ICT',
    'lang_en': 'English',
    'lang_vi': 'Vietnamese',
    'days': 'Mon,Tue,Wed,Thu,Fri,Sat,Sun',
  },
};

// ------------------------------------------------------------------ time zones

DateTime _nthSunday(int year, int month, int n) {
  var d = DateTime.utc(year, month, 1);
  while (d.weekday != DateTime.sunday) {
    d = d.add(const Duration(days: 1));
  }
  return d.add(Duration(days: 7 * (n - 1)));
}

/// US daylight time: second Sunday of March to first Sunday of November (02:00 local).
bool _usDst(DateTime local) {
  final start = _nthSunday(local.year, 3, 2).add(const Duration(hours: 2));
  final end = _nthSunday(local.year, 11, 1).add(const Duration(hours: 2));
  final t = DateTime.utc(local.year, local.month, local.day, local.hour, local.minute);
  return !t.isBefore(start) && t.isBefore(end);
}

/// Offset in hours of [zone] for a wall-clock time [local] in that zone; null when unknown.
int? _offset(String zone, DateTime local) => switch (zone) {
      'UTC' || 'GMT' => 0,
      'ICT' => 7,
      'EST' => -5,
      'EDT' => -4,
      'PST' => -8,
      'PDT' => -7,
      'CET' => 1,
      'CEST' => 2,
      'ET' => _usDst(local) ? -4 : -5,
      'PT' => _usDst(local) ? -7 : -8,
      _ => null,
    };

final RegExp _when = RegExp(r'(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})\s*([A-Z]{2,4})');

/// (instant in UTC, source wall clock, source zone) from "2026-11-05 19:00 ET (Thu) …".
(DateTime, DateTime, String)? _parse(String s) {
  final m = _when.firstMatch(s);
  if (m == null) return null;
  final wall = DateTime.utc(int.parse(m[1]!), int.parse(m[2]!), int.parse(m[3]!), int.parse(m[4]!), int.parse(m[5]!));
  final off = _offset(m[6]!, wall);
  if (off == null) return null;
  return (wall.subtract(Duration(hours: off)), wall, m[6]!);
}

/// The instant as a wall clock in [zone] (ET/PT follow US daylight time).
DateTime _toZone(DateTime utc, String zone) {
  final std = _offset(zone, utc) ?? 0;
  var local = utc.add(Duration(hours: std));
  final real = _offset(zone, local) ?? std;
  if (real != std) local = utc.add(Duration(hours: real));
  return local;
}

String _two(int n) => n.toString().padLeft(2, '0');

// ------------------------------------------------------------------ renderer

class _Txt {
  _Txt(this.lang, this.localTz);

  final String lang;
  final String localTz;
  final List<String> out = [];

  String t(String key) => _l[lang]?[key] ?? _l['en']![key] ?? key;
  List<String> get days => t('days').split(',');
  String get localName => _l[lang]?['local_$localTz'] ?? localTz;

  void line([String s = '']) => out.add(s);
  void rule([String ch = '=']) => line(ch * _width);
  void head(String title) {
    line();
    rule();
    line(title);
    rule();
  }

  void field(String k, String v) => line('${k.padRight(_labelW)}$v');
  void block(String label, String text) {
    if (text.trim().isEmpty) return;
    line();
    line('$label:');
    line('-' * (label.length + 1));
    for (final l in text.trimRight().split('\n')) {
      line(l);
    }
  }

  /// Wrapped "- text" with a hanging indent (notes only; post text is never wrapped).
  void bullet(String text) {
    var cur = '- ';
    for (final w in text.split(' ')) {
      if (cur.length + w.length > _width && cur.trim().length > 1) {
        line(cur.trimRight());
        cur = '  ';
      }
      cur += '$w ';
    }
    line(cur.trimRight());
  }

  String clock(DateTime d) => '${_two(d.hour)}:${_two(d.minute)}';
  String day(DateTime d) => days[d.weekday - 1];

  /// "07:00 Thứ Sáu 06/11/2026 giờ VN  (= 19:00 ET Thứ Năm 05/11)"
  String when(String raw) {
    final p = _parse(raw);
    if (p == null) return raw;
    final local = _toZone(p.$1, localTz);
    final head = '${clock(local)} ${day(local)} ${_two(local.day)}/${_two(local.month)}/${local.year} $localName';
    if (p.$3 == localTz) return head;
    return '$head  (= ${clock(p.$2)} ${p.$3} ${day(p.$2)} ${_two(p.$2.day)}/${_two(p.$2.month)})';
  }

  /// "07:00 Thứ Sáu 06/11" for the schedule; sortable instant.
  (String, DateTime?) short(String raw) {
    final p = _parse(raw);
    if (p == null) return (raw, null);
    final local = _toZone(p.$1, localTz);
    return ('${clock(local)} ${day(local)} ${_two(local.day)}/${_two(local.month)}', p.$1);
  }
}

String _s(Map v, String k) => (v[k] ?? '').toString();

Map? _chosen(Map block, Map<String, int>? scores) {
  final vs = [for (final v in (block['variants'] as List?) ?? const []) if (v is Map) v];
  if (vs.isEmpty) return null;
  final id = _s(block, 'chosen');
  for (final v in vs) {
    if (_s(v, 'id') == id) return v;
  }
  vs.sort((a, b) => (scores?[_s(b, 'id')] ?? 0).compareTo(scores?[_s(a, 'id')] ?? 0));
  return vs.first;
}

String renderText(Map<String, dynamic> doc, Map<String, Map<String, int>> totals,
    {String lang = 'vi', String localTz = 'ICT', required String baseDir}) {
  final r = _Txt(_l.containsKey(lang) ? lang : 'en', localTz);
  final game = (doc['game'] as Map?) ?? {};
  final run = (doc['run'] as Map?) ?? {};
  String score(String p, Map v) => totals[p]?[_s(v, 'id')] == null ? '' : ' · ${totals[p]![_s(v, 'id')]}/60';
  String header(String p, Map v) => '${_s(v, 'id')} · ${_s(v, 'angle')}${score(p, v)}';

  // ---- top
  final created = DateTime.tryParse(_s(doc, 'created'));
  final langs = <String>{
    for (final p in ['tiktok', 'reddit', 'linkedin', 'x'])
      if (doc[p] is Map && (doc[p] as Map)['language'] != null) _l[r.lang]!['lang_${(doc[p] as Map)['language']}'] ?? '${(doc[p] as Map)['language']}',
  };
  r.line('${_s(game, 'name').toUpperCase()} · LEVEL ${run['level'] ?? '?'} · ${r.t('title')}');
  r.line([
    if (created != null) '${r.t('created')} ${_two(created.day)}/${_two(created.month)}/${created.year}',
    r.t('not_posted'),
    if (langs.isNotEmpty) '${r.t('language')}: ${langs.join(', ')}',
  ].join(' · '));
  r.line('${'${r.t('videos')}:'.padRight(11)}${r.t('videos_where')}');
  final links = (game['links'] as Map?) ?? {};
  for (final e in links.entries) {
    if (e.value != null && '${e.value}'.isNotEmpty) {
      final name = switch ('${e.key}') { 'app_store' => 'App Store', 'play_store' => 'Google Play', 'website' => 'Website', _ => '${e.key}' };
      r.line('${'$name:'.padRight(11)}${e.value}');
    }
  }
  r.line();
  r.line(r.t('intro1'));
  r.line(r.t('intro2'));

  // ---- picks
  final tiktok = doc['tiktok'] is Map ? _chosen(doc['tiktok'] as Map, totals['tiktok']) : null;
  final subs = [
    if (doc['reddit'] is Map)
      for (final sub in ((doc['reddit'] as Map)['subreddits'] as List?) ?? const [])
        if (sub is Map && _chosen(sub, totals['reddit']) != null) (sub, _chosen(sub, totals['reddit'])!),
  ];
  final linkedin = doc['linkedin'] is Map ? _chosen(doc['linkedin'] as Map, totals['linkedin']) : null;
  final x = doc['x'] is Map ? _chosen(doc['x'] as Map, totals['x']) : null;

  // ---- schedule
  (String, DateTime?, String, String, String) row(String when, String platform, Map v, String what) {
    final (label, at) = r.short(when);
    return (label, at, platform, _s(v, 'id'), what);
  }

  final rows = [
    if (tiktok != null) row(_s(tiktok, 'post_time'), 'TikTok', tiktok, _s(tiktok, 'angle')),
    for (final (sub, v) in subs) row(_s(sub, 'post_time'), 'Reddit', v, _s(sub, 'subreddit')),
    if (linkedin != null) row(_s(linkedin, 'post_time'), 'LinkedIn', linkedin, _s(linkedin, 'angle')),
    if (x != null) row(_s(x, 'post_time'), 'X', x, _s(x, 'angle')),
  ]..sort((a, b) => (a.$2 ?? DateTime.utc(9999)).compareTo(b.$2 ?? DateTime.utc(9999)));
  r.head('${r.t('schedule')} (${r.localName})');
  r.line();
  for (final row in rows) {
    r.line('${row.$1.padRight(21)}${row.$3.padRight(10)}${row.$4.padRight(7)}${row.$5}');
  }

  var n = 0;
  // ---- TikTok
  if (tiktok != null) {
    final v = tiktok;
    r.head('${++n}. TIKTOK');
    r.line();
    r.line(header('tiktok', v));
    r.line();
    var video = _s(v, 'video');
    final hookFile = 'video/tiktok_9x16_hook.mp4';
    if (video.endsWith('tiktok_9x16.mp4') && File('$baseDir/$hookFile').existsSync()) {
      video = '$hookFile (${r.t('hook_burned')})';
    } else if (_s(v, 'on_screen_hook').isNotEmpty) {
      video = '$video (${r.t('hook_add')})';
    }
    r.field(r.t('video'), video);
    r.field(r.t('post_at'), r.when(_s(v, 'post_time')));
    final sound = (v['sound'] as Map?) ?? {};
    r.field(r.t('sound'), _s(sound, 'choice') == 'trending' ? '${r.t('sound_trending')}: ${_s(sound, 'name')}' : r.t('sound_original'));
    if (_s(v, 'cover_timestamp').isNotEmpty) {
      r.field(r.t('cover'), '${r.t('cover_at').replaceAll('{t}', _s(v, 'cover_timestamp'))} · ${r.t('text')}: ${_s(v, 'cover_text')}');
    }
    r.field(r.t('hook'), '${_s(v, 'on_screen_hook')}  (${r.t('first_2s')})');
    final tags = [for (final h in (v['hashtags'] as List?) ?? const []) '$h'].join(' ');
    r.block(r.t('caption'), '${_s(v, 'caption').trimRight()}${tags.isEmpty ? '' : '\n\n$tags'}');
    r.block(r.t('pinned'), _s(v, 'pinned_comment'));
  }

  // ---- Reddit
  if (subs.isNotEmpty) {
    r.head('${++n}. REDDIT  (${r.t('reddit_note')})');
    for (var i = 0; i < subs.length; i++) {
      final (sub, v) = subs[i];
      if (i > 0) {
        r.line();
        r.rule('-');
      }
      r.line();
      r.line('${_s(sub, 'subreddit')} · ${header('reddit', v)}');
      r.line();
      r.field(r.t('video'), _s(v, 'video'));
      r.field(r.t('post_at'), r.when(_s(sub, 'post_time')));
      r.field(r.t('flair'), _s(v, 'flair').isEmpty ? r.t('none') : _s(v, 'flair'));
      final rules = [for (final x in (sub['rules'] as List?) ?? const []) '$x'];
      for (var k = 0; k < rules.length; k++) {
        r.field(k == 0 ? r.t('rules') : '', rules[k]);
      }
      if (_s(sub, 'rules_checked').isNotEmpty) r.field(r.t('rules_checked'), _s(sub, 'rules_checked'));
      r.block(r.t('r_title'), _s(v, 'title'));
      r.block(r.t('body'), _s(v, 'body'));
      r.block(r.t('first_comment'), _s(v, 'first_comment'));
    }
  }

  // ---- LinkedIn
  if (linkedin != null) {
    final v = linkedin;
    r.head('${++n}. LINKEDIN');
    r.line();
    r.line(header('linkedin', v));
    r.line();
    r.field(r.t('video'), _s(v, 'video'));
    r.field(r.t('post_at'), r.when(_s(v, 'post_time')));
    final tags = [for (final h in (v['hashtags'] as List?) ?? const []) '$h'].join(' ');
    r.block(r.t('li_post'), [_s(v, 'hook'), _s(v, 'body'), _s(v, 'cta'), tags].where((p) => p.trim().isNotEmpty).join('\n\n'));
    r.block(r.t('first_comment'), _s(v, 'first_comment'));
  }

  // ---- X
  if (x != null) {
    final v = x;
    r.head('${++n}. X (TWITTER)');
    r.line();
    r.line(header('x', v));
    r.line();
    r.field(r.t('video'), _s(v, 'video'));
    r.field(r.t('post_at'), r.when(_s(v, 'post_time')));
    r.block(r.t('x_post'), _s(v, 'post'));
    final thread = [for (final p in (v['thread'] as List?) ?? const []) '$p'];
    for (var k = 0; k < thread.length; k++) {
      r.block('${r.t('thread')} ${k + 2}', thread[k]);
    }
    r.block(r.t('reply'), _s(v, 'reply_with_link'));
    r.block(r.t('alt'), _s(v, 'alt_text'));
  }

  // ---- notes
  r.head(r.t('notes'));
  r.line();
  final trend = run['trend_check'];
  if (trend is Map && trend['verified'] != true) r.bullet(r.t('n_trends'));
  final secondHand = [for (final (sub, _) in subs) if (_s(sub, 'rules_checked').contains('second-hand')) _s(sub, 'subreddit')];
  if (secondHand.isNotEmpty) r.bullet('${r.t('n_rules')} (${secondHand.join(', ')}).');
  if (tiktok != null && _s((tiktok['sound'] as Map?) ?? {}, 'choice') == 'trending') {
    r.bullet('${r.t('n_sound')}: ${_s(tiktok['sound'] as Map, 'name')}.');
  }
  final others = <String>[
    for (final p in ['tiktok', 'linkedin', 'x'])
      if (doc[p] is Map && (((doc[p] as Map)['variants'] as List?)?.length ?? 0) > 1) '$p ${((doc[p] as Map)['variants'] as List).length - 1}',
  ];
  final redditOthers = [for (final (sub, _) in subs) ((sub['variants'] as List?)?.length ?? 1) - 1].fold(0, (a, b) => a + b);
  if (redditOthers > 0) others.add('reddit $redditOthers');
  if (others.isNotEmpty) r.bullet('${r.t('n_backup')} (${others.join(', ')}).');
  final assumptions = [for (final a in (run['assumptions'] as List?) ?? const []) '$a'];
  if (assumptions.isNotEmpty) {
    r.line();
    r.line(r.t('assumptions'));
    for (final a in assumptions) {
      r.bullet(a);
    }
  }
  r.line();
  return '${r.out.join('\n')}\n';
}
