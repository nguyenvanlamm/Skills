// Hard checks for posts.json, then (optionally) posts.md rendered from it.
//
//   dart validate_posts.dart <run>/posts.json [--json] [--render <run>/posts.md] [--skip-files]
//
// --skip-files: don't require the video files (checking an example or a draft before export).
//
// Limits come from references/platform_specs.md (g2s-specs), required fields from
// references/posts_format.md (g2s-fields), editorial rules from references/review_rubric.md
// (g2s-rules) and off-game trend hashtags from references/trend_words.md. Nothing is hard-coded
// here, so a platform change is a one-line edit in a reference file.
//
// Exit codes: 0 no errors (warnings allowed), 1 errors found, 2 usage or unreadable input.

import 'dart:convert';
import 'dart:io';

import 'lib/common.dart';
import 'lib/specs.dart';
import 'lib/text_metrics.dart';

class Issue {
  Issue(this.level, this.where, this.message);

  final String level; // error | warning
  final String where;
  final String message;

  Map<String, String> toJson() => {'level': level, 'where': where, 'message': message};
}

class Checker {
  Checker(this.doc, this.spec, this.baseDir, this.offGameTags, {this.skipFiles = false});

  final bool skipFiles;
  final Map<String, dynamic> doc;
  final Spec spec;
  final String baseDir;
  final Set<String> offGameTags;
  final List<Issue> issues = [];
  final Map<String, Map<String, int>> totals = {}; // platform -> variant id -> weighted score

  void error(String where, String msg) => issues.add(Issue('error', where, msg));
  void warn(String where, String msg) => issues.add(Issue('warning', where, msg));

  bool get xPremium => (doc['accounts'] as Map?)?['x_premium'] == true;
  Map<String, dynamic> get game => (doc['game'] as Map?)?.cast<String, dynamic>() ?? {};
  bool get hasLinks =>
      ((game['links'] as Map?)?.values ?? const []).any((v) => v is String && v.trim().isNotEmpty);

  List<Map<String, dynamic>> get facts => [
        for (final f in (doc['facts'] as List?) ?? const [])
          if (f is Map) f.cast<String, dynamic>(),
      ];

  // ---------------------------------------------------------------- helpers

  String s(Map v, String k) => (v[k] ?? '').toString();

  List<String> strList(Object? v) => v is List ? [for (final e in v) e.toString()] : const [];

  bool present(Map v, String key) {
    if (!v.containsKey(key) || v[key] == null) return false;
    final x = v[key];
    if (x is String) return x.trim().isNotEmpty;
    if (x is List) return x.isNotEmpty;
    return true;
  }

  void requireFields(String where, Map v, String specKey) {
    final mayBeEmpty = spec.csv('$specKey.may_be_empty').toSet();
    for (final f in spec.csv('$specKey.required')) {
      if (f.contains('|')) {
        // "body|first_comment": at least one of them.
        final alts = f.split('|');
        if (!alts.any((a) => present(v, a))) error(where, 'needs one of: ${alts.join(', ')}');
        continue;
      }
      if (!v.containsKey(f)) {
        error(where, 'missing field "$f"');
      } else if (!mayBeEmpty.contains(f) && !present(v, f)) {
        error(where, 'field "$f" is empty');
      }
    }
  }

  /// Every text the reader will see in a variant, joined, for phrase checks.
  String visibleText(Map v, List<String> fields) {
    final parts = <String>[];
    for (final f in fields) {
      final x = v[f];
      if (x is String) parts.add(x);
      if (x is List) parts.addAll(x.map((e) => e.toString()));
    }
    return parts.join('\n');
  }

  void checkVideo(String where, Map v) {
    final video = s(v, 'video');
    if (video.isEmpty || skipFiles) return;
    final path = video.startsWith('/') ? video : '$baseDir/$video';
    if (!File(path).existsSync()) error(where, 'video file not found: $video');
  }

  void checkPhrases(String where, String text) {
    final lower = normalizeForMatch(text);
    for (final p in spec.list('banned')) {
      if (lower.contains(normalizeForMatch(p))) {
        error(where, 'stock ad phrase "$p" (review_rubric.md: no AI-ad clichés)');
      }
    }
    for (final p in spec.list('sensitive')) {
      if (RegExp('(^|[^\\p{L}])${RegExp.escape(normalizeForMatch(p))}(\$|[^\\p{L}])', unicode: true)
          .hasMatch(lower)) {
        warn(where, 'sensitive topic word "$p": make sure the post does not ride a disaster, '
            'politics, religion or an accident');
      }
    }
    for (final p in spec.list('promise')) {
      if (lower.contains(normalizeForMatch(p))) {
        warn(where, 'promises a payoff ("$p"): the clip must deliver it, or drop the line '
            '(viewers who feel tricked swipe away and completion drops)');
      }
    }
    if (looksDecomposed(text)) {
      warn(where, 'text has combining marks (NFD); paste-ready text should be NFC, counts assume NFC');
    }
  }

  /// Hard facts (downloads, ratings, awards, prices, dev time, team size, content counts) must be
  /// backed by a claim that points at a confirmed fact.
  void checkClaims(String where, Map v, String text) {
    final claims = [
      for (final c in (v['claims'] as List?) ?? const [])
        if (c is Map) c.cast<String, dynamic>(),
    ];
    final confirmed = {
      for (final f in facts)
        if (f['confirmed'] == true) f['id'].toString(),
    };
    for (final c in claims) {
      final id = (c['fact_id'] ?? '').toString();
      if (id.isEmpty || !confirmed.contains(id)) {
        error(where, 'claim "${c['text']}" points at fact "$id", which is not a confirmed fact in posts.json → facts');
      }
    }
    // A line break ends a phrase: "…màn 10\nmàn này…" is not "10 màn".
    final lower = text.toLowerCase().replaceAll(RegExp(r'[ \t]*\n[ \t\n]*'), ' • ');
    for (final e in spec.section('hardfact.').entries) {
      for (final pattern in e.value) {
        final re = RegExp(pattern, caseSensitive: false, unicode: true);
        for (final m in re.allMatches(lower)) {
          final hit = m.group(0)!.trim();
          final covered = claims.any((c) {
            final ct = (c['text'] ?? '').toString().toLowerCase();
            return ct.isNotEmpty && (ct.contains(hit) || hit.contains(ct));
          });
          if (!covered) {
            error(where, 'hard fact "$hit" (${e.key}) has no claim backed by a confirmed fact: '
                'ask the developer for the real number, add it to facts and claims, or cut it');
          }
        }
      }
    }
  }

  void checkHashtags(String platform, String where, Map v, List<String> tags, String body) {
    final min = spec.integer('$platform.hashtags.min', 0);
    final max = spec.integer('$platform.hashtags.max', 99);
    if (tags.length < min || tags.length > max) {
      error(where, '${tags.length} hashtags; $platform takes $min–$max (review_rubric.md)');
    }
    final lowerTags = tags.map((t) => t.toLowerCase()).toList();
    final dupes = lowerTags.toSet().length != lowerTags.length;
    if (dupes) error(where, 'duplicate hashtags');
    for (final t in tags) {
      if (!hashtagPattern.hasMatch(t) || hashtagPattern.firstMatch(t)!.group(0) != t) {
        error(where, 'not a valid hashtag: "$t" (no spaces or punctuation; needs a letter)');
      }
    }
    // Dev hashtags only on a technical or behind-the-scenes angle.
    final devTags = spec.list('dev_hashtag').map((t) => t.toLowerCase()).toSet();
    final devAngles = spec.csv('dev_angle_types').toSet();
    final angleType = s(v, 'angle_type');
    for (final t in lowerTags) {
      if (devTags.contains(t) && !devAngles.contains(angleType)) {
        error(where, '$t is a dev hashtag but angle_type is "$angleType" '
            '(dev tags only on ${devAngles.join('/')} angles)');
      }
    }
    // Generic reach tags (#fyp, #xuhuong…): at most N.
    final generic = spec.list('generic_hashtag').map((t) => t.toLowerCase()).toSet();
    final genericMax = spec.integer('$platform.generic_hashtags.max', 99);
    final g = lowerTags.where(generic.contains).length;
    if (g > genericMax) error(where, '$g generic hashtags (${generic.join(' ')}); at most $genericMax');
    // The game's own hashtag, used everywhere it fits.
    final own = (game['own_hashtag'] ?? '').toString().toLowerCase();
    if (own.isNotEmpty && max > 0 && !lowerTags.contains(own)) {
      warn(where, 'the game\'s own hashtag ${game['own_hashtag']} is missing (use it consistently)');
    }
    // Trend hashtags outside the game need a bridge sentence in the text.
    final bridges = <String, String>{};
    for (final b in (v['trend_hashtags'] as List?) ?? const []) {
      if (b is Map) bridges[(b['tag'] ?? '').toString().toLowerCase()] = (b['bridge'] ?? '').toString();
    }
    for (final e in bridges.entries) {
      if (!lowerTags.contains(e.key)) {
        error(where, 'trend_hashtags lists ${e.key} but it is not in hashtags');
      }
      if (e.value.trim().isEmpty) {
        error(where, '${e.key} has no bridge sentence');
      } else if (!normalizeForMatch(body).contains(normalizeForMatch(e.value))) {
        error(where, 'bridge for ${e.key} ("${e.value}") does not appear in the post text');
      }
    }
    for (final t in lowerTags) {
      if (offGameTags.contains(t) && !bridges.containsKey(t)) {
        error(where, '$t is an off-game trend tag (trend_words.md): add it to trend_hashtags with the '
            'sentence that bridges the post to it, or drop it');
      }
    }
  }

  void checkScores(String platform, String where, Map v) {
    final scores = v['scores'];
    if (scores is! Map) {
      error(where, 'missing scores (review_rubric.md criteria)');
      return;
    }
    final weights = spec.section('weights.');
    var total = 0;
    for (final e in weights.entries) {
      final raw = scores[e.key];
      final n = raw is num ? raw.toInt() : int.tryParse('$raw');
      if (n == null || n < 1 || n > 5) {
        error(where, 'score "${e.key}" must be 1–5 (got $raw)');
        continue;
      }
      total += n * int.parse(e.value.last);
    }
    final stated = scores['total'];
    if (stated is num && stated.toInt() != total) {
      warn(where, 'scores.total says $stated but the weighted sum is $total');
    }
    totals.putIfAbsent(platform, () => {})[s(v, 'id')] = total;
  }

  void checkChosen(String platform, String where, Map block, List<Map> variants) {
    final chosen = s(block, 'chosen');
    final ids = variants.map((v) => s(v, 'id')).toList();
    if (ids.toSet().length != ids.length) error(where, 'variant ids repeat');
    if (!ids.contains(chosen)) {
      error(where, 'chosen "$chosen" is not one of ${ids.join(', ')}');
      return;
    }
    // Compare with the variants of this block only (a subreddit has its own).
    final t = {for (final e in (totals[platform] ?? <String, int>{}).entries) if (ids.contains(e.key)) e.key: e.value};
    if (t.isEmpty) return;
    final best = t.values.reduce((a, b) => a > b ? a : b);
    if ((t[chosen] ?? 0) < best && s(block, 'chosen_reason').isEmpty) {
      warn(where, 'chosen $chosen scores ${t[chosen]} but ${t.entries.firstWhere((e) => e.value == best).key} scores $best; '
          'say why in chosen_reason or pick the best');
    }
  }

  void checkAngles(String where, List<Map> variants) {
    final min = spec.integer('variants.min', 3);
    if (variants.length < min) error(where, '${variants.length} variants; write at least $min');
    final angles = variants.map((v) => normalizeForMatch(s(v, 'angle'))).where((a) => a.isNotEmpty).toSet();
    if (angles.length < min) error(where, 'only ${angles.length} distinct angles; need $min different ones');
    final allowed = spec.csv('angle_types').toSet();
    for (final v in variants) {
      final at = s(v, 'angle_type');
      if (allowed.isNotEmpty && !allowed.contains(at)) {
        error('$where/${s(v, 'id')}', 'angle_type "$at" is not one of ${allowed.join(', ')}');
      }
    }
  }

  // ---------------------------------------------------------------- platforms

  void tiktok(Map block) {
    final variants = [for (final v in (block['variants'] as List?) ?? const []) if (v is Map) v];
    checkAngles('tiktok', variants);
    for (final v in variants) {
      final where = 'tiktok/${s(v, 'id')}';
      requireFields(where, v, 'tiktok');
      checkVideo(where, v);
      final tags = strList(v['hashtags']);
      final caption = s(v, 'caption');
      final full = tags.isEmpty ? caption : '$caption\n\n${tags.join(' ')}';
      final max = spec.integer('tiktok.caption.max_chars');
      final len = plainLength(full);
      if (len > max) error(where, 'caption + hashtags is $len characters; TikTok allows $max');
      final inline = hashtagsIn(caption);
      if (inline.isNotEmpty) {
        warn(where, 'caption already has hashtags ${inline.join(' ')}; keep them in "hashtags" only');
      }
      final firstLine = caption.split('\n').first.trim();
      if (firstLine.isEmpty) error(where, 'caption must open with the hook line');
      final lang = s(block, 'language');
      final hookWords = wordCount(s(v, 'on_screen_hook'));
      final maxWords = spec.integer('tiktok.on_screen_hook.max_words.$lang',
          spec.integer('tiktok.on_screen_hook.max_words', 8));
      if (hookWords > maxWords) {
        error(where, 'on_screen_hook has $hookWords words; keep it to about $maxWords');
      }
      final coverWords = wordCount(s(v, 'cover_text'));
      final coverMax = spec.integer('tiktok.cover_text.max_words', 8);
      if (coverWords > coverMax) warn(where, 'cover_text has $coverWords words; $coverMax reads better');
      final ts = v['cover_timestamp'];
      if (ts is! num || ts < 0) error(where, 'cover_timestamp must be seconds into the video');
      final sound = v['sound'];
      if (sound is Map) {
        final choice = (sound['choice'] ?? '').toString();
        if (!{'original', 'trending'}.contains(choice)) {
          error(where, 'sound.choice must be "original" or "trending"');
        }
        final business = (doc['accounts'] as Map?)?['tiktok'] == 'business';
        if (business && choice == 'trending' && (sound['commercial_library'] != true)) {
          error(where, 'business account: a trending sound must come from the Commercial Music '
              'Library (set sound.commercial_library: true once checked)');
        }
      }
      final body = visibleText(v, ['caption', 'on_screen_hook', 'title', 'cover_text', 'pinned_comment']);
      checkHashtags('tiktok', where, v, tags, body);
      checkPhrases(where, body);
      checkClaims(where, v, body);
      checkScores('tiktok', where, v);
    }
    checkChosen('tiktok', 'tiktok', block, variants);
  }

  void reddit(Map block) {
    final subs = [for (final v in (block['subreddits'] as List?) ?? const []) if (v is Map) v];
    final minSubs = spec.integer('reddit.subreddits.min', 2);
    final maxSubs = spec.integer('reddit.subreddits.max', 3);
    if (subs.length < minSubs || subs.length > maxSubs) {
      error('reddit', '${subs.length} subreddits; write for $minSubs–$maxSubs');
    }
    final all = <Map>[];
    final times = <String, String>{};
    for (final sub in subs) {
      final name = s(sub, 'subreddit');
      final where = 'reddit/$name';
      requireFields(where, sub, 'reddit.sub');
      if (!RegExp(r'^r/[A-Za-z0-9_]{2,21}$').hasMatch(name)) error(where, 'subreddit must look like r/Name');
      final t = normalizeForMatch(s(sub, 'post_time'));
      if (t.isNotEmpty) {
        if (times.containsKey(t)) {
          error(where, 'same post_time as ${times[t]}: space the subreddits out');
        }
        times[t] = name;
      }
      final variants = [for (final v in (sub['variants'] as List?) ?? const []) if (v is Map) v];
      all.addAll(variants);
      for (final v in variants) {
        final vw = '$where/${s(v, 'id')}';
        requireFields(vw, v, 'reddit');
        checkVideo(vw, v);
        final title = s(v, 'title');
        final maxTitle = spec.integer('reddit.title.max_chars');
        if (plainLength(title) > maxTitle) error(vw, 'title is ${plainLength(title)} characters; max $maxTitle');
        if (hasEmoji(title)) error(vw, 'title has emoji; Reddit titles read as a real person without them');
        final caps = RegExp(r'\b[A-Z]{3,}\b').allMatches(title).where((m) => m.group(0) != 'OC').length;
        if (caps > 1) warn(vw, 'title shouts ($caps all-caps words); reads as hype');
        if ('!'.allMatches(title).length > 1) warn(vw, 'title has several "!"; reads as hype');
        final text = visibleText(v, ['title', 'body', 'first_comment']);
        final tags = hashtagsIn(text);
        if (tags.isNotEmpty) error(vw, 'hashtags on Reddit: ${tags.join(' ')}');
        if (hasEmoji(s(v, 'body'))) warn(vw, 'emoji in the body; most game subs read that as marketing');
        final maxBody = spec.integer('reddit.body.max_chars');
        if (plainLength(s(v, 'body')) > maxBody) error(vw, 'body over $maxBody characters');
        if (sub['link_in_comment'] == true && urlsIn(s(v, 'body')).isNotEmpty) {
          error(vw, '$name wants the link in a comment, but the body has one');
        }
        checkPhrases(vw, text);
        checkClaims(vw, v, text);
        checkScores('reddit', vw, v);
      }
      checkChosen('reddit', where, sub, variants);
    }
    checkAngles('reddit', all);
  }

  void linkedin(Map block) {
    final variants = [for (final v in (block['variants'] as List?) ?? const []) if (v is Map) v];
    checkAngles('linkedin', variants);
    for (final v in variants) {
      final where = 'linkedin/${s(v, 'id')}';
      requireFields(where, v, 'linkedin');
      checkVideo(where, v);
      final tags = strList(v['hashtags']);
      final hook = s(v, 'hook');
      final full = [hook, s(v, 'body'), s(v, 'cta'), tags.join(' ')].where((x) => x.trim().isNotEmpty).join('\n\n');
      final max = spec.integer('linkedin.post.max_chars');
      if (plainLength(full) > max) error(where, 'post is ${plainLength(full)} characters; LinkedIn allows $max');
      final seeMore = spec.integer('linkedin.see_more.chars');
      final seeLines = spec.integer('linkedin.see_more.lines', 3);
      if (plainLength(hook) > seeMore || hook.split('\n').length > seeLines) {
        warn(where, 'hook is ${plainLength(hook)} characters / ${hook.split('\n').length} lines; '
            'only about $seeMore characters or $seeLines lines show before "…see more"');
      }
      if (urlsIn(visibleText(v, ['hook', 'body', 'cta'])).isNotEmpty) {
        warn(where, 'link in the post body; put it in first_comment');
      }
      if (hasLinks && urlsIn(s(v, 'first_comment')).isEmpty) {
        warn(where, 'first_comment has no link although the game has links in config');
      }
      final inline = hashtagsIn(visibleText(v, ['hook', 'body', 'cta']));
      final allTags = {...tags.map((t) => t.toLowerCase()), ...inline.map((t) => t.toLowerCase())}.toList();
      final body = visibleText(v, ['hook', 'body', 'cta', 'first_comment']);
      checkHashtags('linkedin', where, v, allTags, body);
      checkPhrases(where, body);
      checkClaims(where, v, body);
      checkScores('linkedin', where, v);
    }
    checkChosen('linkedin', 'linkedin', block, variants);
  }

  void x(Map block) {
    final variants = [for (final v in (block['variants'] as List?) ?? const []) if (v is Map) v];
    checkAngles('x', variants);
    final max = xPremium ? spec.integer('x.post.max_weighted.premium') : spec.integer('x.post.max_weighted');
    for (final v in variants) {
      final where = 'x/${s(v, 'id')}';
      requireFields(where, v, 'x');
      checkVideo(where, v);
      final post = s(v, 'post');
      final w = twitterWeightedLength(post);
      if (w > max) error(where, 'post weighs $w (twitter-text v3); limit $max${xPremium ? ' (Premium)' : ''}');
      final thread = strList(v['thread']);
      final threadMax = spec.integer('x.thread.max_posts', 4);
      if (thread.length > threadMax) error(where, 'thread has ${thread.length} posts; keep it to 2–$threadMax');
      for (var i = 0; i < thread.length; i++) {
        final tw = twitterWeightedLength(thread[i]);
        if (tw > max) error('$where/thread[$i]', 'weighs $tw; limit $max');
      }
      final reply = s(v, 'reply_with_link');
      final rw = twitterWeightedLength(reply);
      if (rw > max) error('$where/reply', 'weighs $rw; limit $max');
      if (hasLinks && urlsIn(reply).isEmpty) warn(where, 'reply_with_link has no link');
      if (urlsIn(post).isNotEmpty) warn(where, 'link in the main post; X shows it less, keep it in the reply');
      final declared = strList(v['hashtags']).map((t) => t.toLowerCase()).toList();
      final inPost = hashtagsIn(post).map((t) => t.toLowerCase()).toList();
      for (final t in declared) {
        if (!inPost.contains(t)) error(where, '$t is listed in hashtags but not used in the post');
      }
      for (final t in inPost) {
        if (!declared.contains(t)) error(where, '$t is in the post but not listed in hashtags');
      }
      final alt = s(v, 'alt_text');
      final altMax = spec.integer('x.alt_text.max_chars');
      if (plainLength(alt) > altMax) error(where, 'alt_text over $altMax characters');
      final body = visibleText(v, ['post', 'thread', 'reply_with_link']);
      checkHashtags('x', where, v, inPost, body);
      checkPhrases(where, body);
      checkClaims(where, v, body);
      checkScores('x', where, v);
    }
    checkChosen('x', 'x', block, variants);
  }

  void run() {
    if (doc['schema'] != 'gameplay-to-social/posts@1') {
      error('posts.json', 'schema must be "gameplay-to-social/posts@1"');
    }
    final runInfo = (doc['run'] as Map?) ?? {};
    final platforms = strList(runInfo['platforms']);
    if (platforms.isEmpty) error('run', 'run.platforms lists no platform');
    final known = spec.csv('platforms').toSet();
    for (final p in platforms) {
      if (!known.contains(p)) {
        error('run', 'unknown platform "$p" (one of ${known.join(', ')})');
        continue;
      }
      final block = doc[p];
      if (block is! Map) {
        error(p, 'requested in run.platforms but missing');
        continue;
      }
      if ((block['language'] ?? '').toString().isEmpty) error(p, 'missing language');
      switch (p) {
        case 'tiktok':
          tiktok(block);
        case 'reddit':
          reddit(block);
        case 'linkedin':
          linkedin(block);
        case 'x':
          x(block);
      }
    }
    final trend = runInfo['trend_check'];
    if (trend is! Map || trend['verified'] is! bool) {
      error('run', 'run.trend_check.verified must say whether trends were checked online this run');
    } else if (trend['verified'] != true) {
      warn('run', 'trends were not checked online this run; say so in review_report.md');
    }
    final own = (game['own_hashtag'] ?? '').toString();
    if (own.isEmpty) warn('game', 'game.own_hashtag is empty (config.yaml → hashtags.own)');
  }
}

/// Hashtags that trend_words.md marks as off-game (events, seasons, memes): they need a bridge.
Set<String> offGameHashtags() {
  final f = File('$referencesDir/trend_words.md');
  if (!f.existsSync()) return {};
  final tags = <String>{};
  for (final line in f.readAsLinesSync()) {
    if (!line.trim().startsWith('|')) continue;
    final cells = line.split('|').map((c) => c.trim()).toList();
    if (cells.length < 4) continue;
    final type = cells.length > 2 ? cells[2].toLowerCase() : '';
    if (type.contains('offgame') || type.contains('event') || type.contains('season')) {
      tags.addAll(hashtagsIn(cells[1]).map((t) => t.toLowerCase()));
    }
  }
  return tags;
}

// ------------------------------------------------------------------ posts.md

String renderMarkdown(Map<String, dynamic> doc, Map<String, Map<String, int>> totals) {
  final b = StringBuffer();
  final game = (doc['game'] as Map?) ?? {};
  final run = (doc['run'] as Map?) ?? {};
  String s(Map v, String k) => (v[k] ?? '').toString();
  String fence(String text) => '```text\n${text.trim()}\n```\n';
  b.writeln('# ${game['name'] ?? 'Game'} — level ${run['level'] ?? '?'} — social drafts');
  b.writeln();
  b.writeln('Drafts only: nothing has been posted. The chosen variant of each platform comes first; '
      'the others follow with their scores. Paths are relative to this folder.');
  if (run['trend_check'] is Map && (run['trend_check'] as Map)['verified'] != true) {
    b.writeln();
    b.writeln('> Trends were **not** checked online for this run — see review_report.md.');
  }
  b.writeln();
  int? score(String p, Map v) => totals[p]?[s(v, 'id')];
  String scoreText(String p, Map v) => score(p, v) == null ? '' : ' · ${score(p, v)}/60';

  void variantsOf(String platform, Map block, void Function(Map v, bool chosen) write) {
    final vs = [for (final v in (block['variants'] as List?) ?? const []) if (v is Map) v];
    final chosen = s(block, 'chosen');
    for (final v in vs.where((v) => s(v, 'id') == chosen)) {
      write(v, true);
    }
    final rest = vs.where((v) => s(v, 'id') != chosen).toList();
    if (rest.isNotEmpty) {
      b.writeln('<details><summary>Other variants (${rest.length})</summary>\n');
      for (final v in rest) {
        write(v, false);
      }
      b.writeln('</details>\n');
    }
  }

  if (doc['tiktok'] is Map) {
    final block = doc['tiktok'] as Map;
    b.writeln('## TikTok (${block['language']})\n');
    variantsOf('tiktok', block, (v, chosen) {
      b.writeln('### ${chosen ? '✅ ' : ''}${s(v, 'id')} — ${s(v, 'angle')}${scoreText('tiktok', v)}\n');
      b.writeln('- **Video:** `${s(v, 'video')}` · cover at ${v['cover_timestamp']} s, text: "${s(v, 'cover_text')}"');
      b.writeln('- **On-screen hook (first 2 s):** ${s(v, 'on_screen_hook')}');
      if (s(v, 'title').isNotEmpty) b.writeln('- **Title:** ${s(v, 'title')}');
      final sound = v['sound'] is Map ? v['sound'] as Map : {};
      b.writeln('- **Sound:** ${sound['choice'] ?? ''}${sound['name'] != null ? ' — ${sound['name']}' : ''}${sound['note'] != null ? ' (${sound['note']})' : ''}');
      b.writeln('- **Post time:** ${s(v, 'post_time')}');
      b.writeln('\nCaption:\n');
      final tags = (v['hashtags'] as List?)?.join(' ') ?? '';
      b.write(fence('${s(v, 'caption')}\n\n$tags'));
      b.writeln('\nPinned comment:\n');
      b.write(fence(s(v, 'pinned_comment')));
      if (s(v, 'notes').isNotEmpty) b.writeln('\n_Why: ${s(v, 'notes')}_\n');
    });
  }
  if (doc['reddit'] is Map) {
    final block = doc['reddit'] as Map;
    b.writeln('## Reddit (${block['language']})\n');
    for (final sub in (block['subreddits'] as List?) ?? const []) {
      if (sub is! Map) continue;
      b.writeln('### ${s(sub, 'subreddit')} — post ${s(sub, 'post_time')}\n');
      b.writeln('- **Why this sub:** ${s(sub, 'why')}');
      b.writeln('- **Rules to follow:** ${(sub['rules'] as List?)?.join('; ') ?? ''}');
      b.writeln('- **Rules checked:** ${s(sub, 'rules_checked')}');
      b.writeln();
      variantsOf('reddit', sub, (v, chosen) {
        b.writeln('#### ${chosen ? '✅ ' : ''}${s(v, 'id')} — ${s(v, 'angle')}${scoreText('reddit', v)}\n');
        b.writeln('- **Video:** `${s(v, 'video')}` · flair: ${s(v, 'flair')}${v['oc'] == true ? ' · mark OC' : ''}${v['spoiler'] == true ? ' · mark spoiler' : ''}');
        b.writeln('\nTitle:\n');
        b.write(fence(s(v, 'title')));
        if (s(v, 'body').isNotEmpty) {
          b.writeln('\nBody:\n');
          b.write(fence(s(v, 'body')));
        }
        if (s(v, 'first_comment').isNotEmpty) {
          b.writeln('\nFirst comment:\n');
          b.write(fence(s(v, 'first_comment')));
        }
      });
    }
  }
  if (doc['linkedin'] is Map) {
    final block = doc['linkedin'] as Map;
    b.writeln('## LinkedIn (${block['language']})\n');
    variantsOf('linkedin', block, (v, chosen) {
      b.writeln('### ${chosen ? '✅ ' : ''}${s(v, 'id')} — ${s(v, 'angle')}${scoreText('linkedin', v)}\n');
      b.writeln('- **Video:** `${s(v, 'video')}` (${s(v, 'video_version')}) · post ${s(v, 'post_time')}');
      final tags = (v['hashtags'] as List?)?.join(' ') ?? '';
      b.writeln('\nPost:\n');
      b.write(fence([s(v, 'hook'), s(v, 'body'), s(v, 'cta'), tags].where((x) => x.trim().isNotEmpty).join('\n\n')));
      b.writeln('\nFirst comment:\n');
      b.write(fence(s(v, 'first_comment')));
    });
  }
  if (doc['x'] is Map) {
    final block = doc['x'] as Map;
    b.writeln('## X (${block['language']})\n');
    variantsOf('x', block, (v, chosen) {
      b.writeln('### ${chosen ? '✅ ' : ''}${s(v, 'id')} — ${s(v, 'angle')}${scoreText('x', v)}\n');
      b.writeln('- **Video:** `${s(v, 'video')}` · post ${s(v, 'post_time')}${s(v, 'community').isNotEmpty ? ' · community: ${s(v, 'community')}' : ''}');
      b.writeln('- **Weighted length:** ${twitterWeightedLength(s(v, 'post'))}');
      b.writeln('\nPost:\n');
      b.write(fence(s(v, 'post')));
      final thread = (v['thread'] as List?) ?? const [];
      for (var i = 0; i < thread.length; i++) {
        b.writeln('\nThread ${i + 2}:\n');
        b.write(fence(thread[i].toString()));
      }
      b.writeln('\nReply with link:\n');
      b.write(fence(s(v, 'reply_with_link')));
      b.writeln('\nAlt text:\n');
      b.write(fence(s(v, 'alt_text')));
    });
  }
  return b.toString();
}

void main(List<String> argv) {
  final args = Args.parse(argv, flags: {'json', 'skip-files'});
  if (args.positional.isEmpty) {
    stderr.writeln('usage: dart validate_posts.dart <posts.json> [--json] [--render posts.md]');
    exit(2);
  }
  final path = args.positional.first;
  Map<String, dynamic> doc;
  try {
    doc = (jsonDecode(File(path).readAsStringSync()) as Map).cast<String, dynamic>();
  } on Object catch (e) {
    stderr.writeln('error: cannot read $path: $e');
    exit(2);
  }
  final spec = loadSpec(['platform_specs.md', 'posts_format.md', 'review_rubric.md']);
  final checker = Checker(doc, spec, File(path).parent.path, offGameHashtags(), skipFiles: args.flag('skip-files'))..run();
  final errors = checker.issues.where((i) => i.level == 'error').toList();
  final warnings = checker.issues.where((i) => i.level == 'warning').toList();
  final specsDate = updatedDate('platform_specs.md');
  if (args.flag('json')) {
    stdout.writeln(prettyJson({
      'ok': errors.isEmpty,
      'errors': errors.length,
      'warnings': warnings.length,
      'specs_updated': specsDate,
      'scores': checker.totals,
      'issues': [for (final i in checker.issues) i.toJson()],
    }));
  } else {
    stdout.writeln('validate_posts: ${errors.length} error(s), ${warnings.length} warning(s) '
        '— limits from platform_specs.md (updated ${specsDate ?? '?'})');
    for (final i in [...errors, ...warnings]) {
      stdout.writeln('  ${i.level == 'error' ? '✗' : '⚠'} ${i.where}: ${i.message}');
    }
    for (final p in checker.totals.entries) {
      final ranked = p.value.entries.toList()..sort((a, b) => b.value.compareTo(a.value));
      stdout.writeln('  scores ${p.key}: ${ranked.map((e) => '${e.key}=${e.value}').join('  ')}');
    }
  }
  final render = args['render'];
  if (render != null && errors.isEmpty) {
    writeText(render, renderMarkdown(doc, checker.totals));
    stdout.writeln('wrote $render');
  } else if (render != null) {
    stdout.writeln('posts.md not written: fix the errors first');
  }
  exit(errors.isEmpty ? 0 : 1);
}
