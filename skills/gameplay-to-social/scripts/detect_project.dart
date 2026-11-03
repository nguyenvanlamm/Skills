// Reads a Flutter game project and prints what the skill needs to set up capture, as JSON.
//
//   dart detect_project.dart [--project DIR] [--md]
//
// Everything here is a lead, with file:line, for the agent to confirm by reading the code: the
// level loader and count, a bot or solver, what to switch off while recording (ads, analytics,
// review and purchase prompts, tutorials, consent), randomness to seed, app ids, platforms,
// orientation, audio, and post facts (README, CHANGELOG, git) that the developer must confirm
// before any of them appears in a post.
//
// Exit codes: 0 Flutter project, 3 not a Flutter project (ask the user for the path), 2 usage.

import 'dart:io';

import 'lib/common.dart';

const int _maxHits = 12;

class Hit {
  Hit(this.file, this.line, this.text);

  final String file;
  final int line;
  final String text;

  Map<String, Object> toJson() => {'at': '$file:$line', 'text': text};
}

/// Finds the project root: [start] or the nearest parent with a pubspec.yaml (4 levels up).
Directory? findRoot(Directory start) {
  var d = start.absolute;
  for (var i = 0; i < 5; i++) {
    if (File('${d.path}/pubspec.yaml').existsSync()) return d;
    final parent = d.parent;
    if (parent.path == d.path) break;
    d = parent;
  }
  return null;
}

/// Minimal pubspec reading: top-level scalars and the package names under the dependency maps.
class Pubspec {
  Pubspec(String text) {
    String? section;
    for (final raw in text.split('\n')) {
      if (raw.trim().isEmpty || raw.trimLeft().startsWith('#')) continue;
      final indent = raw.length - raw.trimLeft().length;
      final line = raw.trim();
      if (indent == 0) {
        final colon = line.indexOf(':');
        if (colon < 0) continue;
        final key = line.substring(0, colon);
        final value = line.substring(colon + 1).trim();
        section = key;
        if (value.isNotEmpty) top[key] = _unquote(value);
        if (key == 'flutter') hasFlutterSection = true;
        continue;
      }
      if (indent == 2 && (section == 'dependencies' || section == 'dev_dependencies')) {
        final colon = line.indexOf(':');
        if (colon < 0) continue;
        final name = line.substring(0, colon);
        final value = line.substring(colon + 1).trim();
        (section == 'dependencies' ? deps : devDeps)[name] = _unquote(value);
      }
      if (section == 'dependencies' && line == 'sdk: flutter') flutterSdkDep = true;
    }
  }

  final Map<String, String> top = {};
  final Map<String, String> deps = {};
  final Map<String, String> devDeps = {};
  bool hasFlutterSection = false;
  bool flutterSdkDep = false;

  static String _unquote(String v) => v.replaceAll(RegExp(r'''^["']|["']$'''), '');
}

class Scanner {
  Scanner(this.root);

  final Directory root;
  final Map<String, List<String>> _cache = {};

  String rel(String path) => path.startsWith(root.path) ? path.substring(root.path.length + 1) : path;

  List<File> dartFiles(String dir) {
    final d = Directory('${root.path}/$dir');
    if (!d.existsSync()) return const [];
    return d
        .listSync(recursive: true, followLinks: false)
        .whereType<File>()
        .where((f) => f.path.endsWith('.dart') && !f.path.contains('/generated/') && !f.path.endsWith('.g.dart'))
        .toList()
      ..sort((a, b) => a.path.compareTo(b.path));
  }

  List<String> lines(File f) => _cache.putIfAbsent(f.path, () {
        try {
          return f.readAsLinesSync();
        } on Object {
          return const [];
        }
      });

  List<Hit> grep(List<File> files, RegExp re, {int max = _maxHits}) {
    final hits = <Hit>[];
    for (final f in files) {
      final ls = lines(f);
      for (var i = 0; i < ls.length; i++) {
        if (re.hasMatch(ls[i])) {
          final t = ls[i].trim();
          hits.add(Hit(rel(f.path), i + 1, t.length > 140 ? '${t.substring(0, 140)}…' : t));
          if (hits.length >= max) return hits;
        }
      }
    }
    return hits;
  }

  String? read(String relPath) {
    final f = File('${root.path}/$relPath');
    return f.existsSync() ? f.readAsStringSync() : null;
  }

  String? firstMatch(String? text, RegExp re, [int group = 1]) =>
      text == null ? null : re.firstMatch(text)?.group(group);
}

Future<Map<String, Object?>> gitFacts(Directory root) async {
  Future<String> git(List<String> a) async {
    final r = await runCmd('git', ['-C', root.path, ...a], timeout: const Duration(seconds: 20));
    return r.ok ? r.stdout.trim() : '';
  }

  final inside = await git(['rev-parse', '--is-inside-work-tree']);
  if (inside != 'true') return {'repo': false};
  final first = (await git(['log', '--reverse', '--format=%cs']));
  final subjects = (await git(['log', '-n', '40', '--format=%cs %s'])).split('\n').where((l) => l.isNotEmpty).toList();
  final featureRe = RegExp(r'^\d{4}-\d{2}-\d{2} (feat|add|new|ship|introduce|launch|release)', caseSensitive: false);
  return {
    'repo': true,
    'first_commit': first.split('\n').first,
    'last_commit': await git(['log', '-1', '--format=%cs']),
    'commits': int.tryParse(await git(['rev-list', '--count', 'HEAD'])) ?? 0,
    'authors': (await git(['shortlog', '-sn', '--all', '--no-merges'])).split('\n').where((l) => l.trim().isNotEmpty).length,
    'recent_features': subjects.where(featureRe.hasMatch).take(10).toList(),
    'recent': subjects.take(8).toList(),
    'tags': (await git(['tag', '--sort=-creatordate'])).split('\n').where((l) => l.isNotEmpty).take(5).toList(),
  };
}

String excerpt(String? text, int max) {
  if (text == null) return '';
  final t = text.replaceAll(RegExp(r'\n{3,}'), '\n\n').trim();
  return t.length > max ? '${t.substring(0, max)}…' : t;
}

Future<void> main(List<String> argv) async {
  final args = Args.parse(argv, flags: {'md'});
  final start = Directory(args.str('project', Directory.current.path));
  if (!start.existsSync()) {
    stdout.writeln(prettyJson({'is_flutter': false, 'reason': 'folder not found: ${start.path}'}));
    exit(3);
  }
  final root = findRoot(start);
  if (root == null) {
    stdout.writeln(prettyJson({
      'is_flutter': false,
      'path': start.absolute.path,
      'reason': 'no pubspec.yaml here or in the 4 parent folders — ask the user for the game project path',
    }));
    exit(3);
  }
  final pub = Pubspec(File('${root.path}/pubspec.yaml').readAsStringSync());
  if (!pub.flutterSdkDep && !pub.hasFlutterSection) {
    stdout.writeln(prettyJson({
      'is_flutter': false,
      'path': root.path,
      'reason': 'pubspec.yaml has no flutter SDK dependency (a pure Dart package?) — ask the user for the game project path',
    }));
    exit(3);
  }
  final sc = Scanner(root);
  final lib = sc.dartFiles('lib');
  final toolAndTest = [...sc.dartFiles('tool'), ...sc.dartFiles('test'), ...sc.dartFiles('integration_test')];
  final allDeps = {...pub.deps.keys, ...pub.devDeps.keys};

  // Platforms and ids.
  final platforms = [
    for (final p in ['android', 'ios', 'web', 'macos', 'windows', 'linux'])
      if (Directory('${root.path}/$p').existsSync()) p,
  ];
  final gradle = sc.read('android/app/build.gradle.kts') ?? sc.read('android/app/build.gradle');
  final pbx = sc.read('ios/Runner.xcodeproj/project.pbxproj');
  String? iosId;
  if (pbx != null) {
    for (final m in RegExp(r'PRODUCT_BUNDLE_IDENTIFIER = "?([^";]+)"?;').allMatches(pbx)) {
      final id = m.group(1)!;
      if (!id.contains('Tests') && !id.contains(r'$(')) {
        iosId = id;
        break;
      }
    }
  }
  final ids = {
    'android': sc.firstMatch(gradle, RegExp(r'''applicationId\s*=?\s*["']([^"']+)["']''')) ??
        sc.firstMatch(gradle, RegExp(r'''namespace\s*=?\s*["']([^"']+)["']''')),
    'ios': iosId,
    'macos': sc.firstMatch(sc.read('macos/Runner/Configs/AppInfo.xcconfig'), RegExp(r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*(\S+)')),
    'linux_app_id': sc.firstMatch(sc.read('linux/CMakeLists.txt'), RegExp(r'set\(APPLICATION_ID "([^"]+)"\)')),
    'linux_binary': sc.firstMatch(sc.read('linux/CMakeLists.txt'), RegExp(r'set\(BINARY_NAME "([^"]+)"\)')),
    'windows_binary': sc.firstMatch(sc.read('windows/CMakeLists.txt'), RegExp(r'set\(BINARY_NAME "([^"]+)"\)')),
    'web_title': sc.firstMatch(sc.read('web/index.html'), RegExp(r'<title>([^<]*)</title>')),
    'linux_window_title': sc.firstMatch(sc.read('linux/runner/my_application.cc'), RegExp(r'gtk_window_set_title\(window, "([^"]*)"\)')) ??
        sc.firstMatch(sc.read('linux/my_application.cc'), RegExp(r'gtk_window_set_title\(window, "([^"]*)"\)')),
  };

  // Orientation.
  final manifest = sc.read('android/app/src/main/AndroidManifest.xml');
  final plist = sc.read('ios/Runner/Info.plist');
  final dartOrient = sc.grep(lib, RegExp(r'DeviceOrientation\.(portrait|landscape)'), max: 4);
  final androidOrient = sc.firstMatch(manifest, RegExp(r'android:screenOrientation="([^"]+)"'));
  String guess() {
    final all = [
      androidOrient ?? '',
      ...dartOrient.map((h) => h.text),
      if (plist != null && plist.contains('UIInterfaceOrientationPortrait') && !plist.contains('UIInterfaceOrientationLandscape')) 'portrait',
      if (plist != null && plist.contains('UIInterfaceOrientationLandscape') && !plist.contains('UIInterfaceOrientationPortrait')) 'landscape',
    ].join(' ').toLowerCase();
    final p = all.contains('portrait');
    final l = all.contains('landscape');
    if (p && !l) return 'portrait';
    if (l && !p) return 'landscape';
    return 'unknown (check the first frame)';
  }

  // Flame and physics.
  final flamePkgs = allDeps.where((d) => d == 'flame' || d.startsWith('flame_')).toList()..sort();
  final physics = allDeps.where((d) => {'forge2d', 'flame_forge2d', 'box2d_flame', 'flame_box2d'}.contains(d)).toList();

  // Audio.
  const audioPkgs = {'audioplayers', 'flame_audio', 'just_audio', 'soloud', 'flutter_soloud', 'assets_audio_player', 'soundpool', 'audio_service', 'flutter_sound'};
  var audioFiles = 0;
  final assets = Directory('${root.path}/assets');
  if (assets.existsSync()) {
    audioFiles = assets
        .listSync(recursive: true, followLinks: false)
        .whereType<File>()
        .where((f) => RegExp(r'\.(mp3|ogg|wav|m4a|aac|flac|opus)$', caseSensitive: false).hasMatch(f.path))
        .length;
  }
  final audioHits = sc.grep(lib, RegExp(r'AudioPlayer|FlameAudio|SoLoud|SystemSound\.play|playSfx|Sfx\b'), max: 6);

  // Levels.
  final levelCount = sc.grep(lib, RegExp(
      r'(levelCount|totalLevels|kLevelCount|numLevels|maxLevel|levelsPerChapter|levelsPer\w+|levels\.length|levelTable|kLevels)\b'));
  final levelLoad = sc.grep(lib, RegExp(
      r'(loadLevel|startLevel|openLevel|goToLevel|playLevel|levelId|levelIndex|LevelScreen|GameScreen\s*\(|currentLevel|levels\.load|levelAt\()'));
  final levelAssets = <Map<String, Object>>[];
  if (assets.existsSync()) {
    for (final d in assets.listSync(recursive: true, followLinks: false).whereType<Directory>()) {
      if (!RegExp(r'(level|stage|map|puzzle)s?$', caseSensitive: false).hasMatch(d.path)) continue;
      final n = d.listSync().whereType<File>().where((f) => RegExp(r'\.(json|txt|tmx|yaml|csv)$').hasMatch(f.path)).length;
      if (n > 0) levelAssets.add({'dir': sc.rel(d.path), 'files': n});
    }
  }

  // Bots, solvers, autoplay, self-playing entries.
  final botFiles = [
    ...lib,
    ...toolAndTest,
  ].where((f) => RegExp(r'(bot|autoplay|auto_play|solver|pilot|sim|simulat|demo|ai_player|record_main|ad_main|capture)[^/]*\.dart$', caseSensitive: false)
      .hasMatch(f.path.split('/').last)).map((f) => sc.rel(f.path)).toList();
  final botHits = sc.grep([...lib, ...toolAndTest],
      RegExp(r'class \w*(Bot|Solver|Autoplay|AutoPlay|AutoPilot|Pilot|Simulator|AiPlayer|Demo)\w*\b|\b(demo|autoplay|autoPlay|bot)\s*:'));

  // Things to switch off while recording.
  Map<String, Object> group(Set<String> pkgs, RegExp code) => {
        'packages': allDeps.where(pkgs.contains).toList(),
        'code': [for (final h in sc.grep(lib, code, max: 8)) h.toJson()],
      };
  final disable = {
    'ads': group({'google_mobile_ads', 'applovin_max', 'unity_ads_plugin', 'ironsource_mediation', 'easy_ads_flutter', 'appodeal_flutter', 'yandex_mobileads', 'admob_flutter', 'facebook_audience_network', 'gma_mediation_applovin'},
        RegExp(r'BannerAd|InterstitialAd|RewardedAd|AppOpenAd|MobileAds\.instance|AdService|showAd\b')),
    'analytics': group({'firebase_analytics', 'firebase_crashlytics', 'amplitude_flutter', 'mixpanel_flutter', 'appsflyer_sdk', 'adjust_sdk', 'posthog_flutter', 'sentry_flutter', 'facebook_app_events', 'flutter_branch_sdk', 'onesignal_flutter'},
        RegExp(r'FirebaseAnalytics|logEvent\(|analytics\.(log|track)|Analytics\b|Crashlytics')),
    'review_prompt': group({'in_app_review', 'rate_my_app', 'app_review'},
        RegExp(r'InAppReview|requestReview|RateMyApp|ReviewService|ReviewPolicy|askForReview|maybeAskReview')),
    'purchases': group({'in_app_purchase', 'purchases_flutter', 'flutter_inapp_purchase', 'in_app_purchase_storekit'},
        RegExp(r'InAppPurchase\.instance|Purchases\.|ShopController|StoreBackend|AppStoreBackend|buyNonConsumable|buyConsumable')),
    'tutorial': group(const {},
        RegExp(r'tutorial|onboarding|firstLaunch|first_launch|hasSeen\w*|hintsSeen|coachMark|HowToPlay|showHint|introSeen', caseSensitive: false)),
    'consent_permissions': group({'app_tracking_transparency', 'permission_handler', 'firebase_messaging', 'flutter_local_notifications'},
        RegExp(r'ConsentInformation|ConsentForm|requestTrackingAuthorization|requestPermission|Permission\.\w+\.request')),
    'popups_rewards': group(const {}, RegExp(r'class \w*(Daily|Chest|Reward|Offer|Promo|Rate)\w*(Dialog|Sheet|Popup)\b|showDialog<|showModalBottomSheet<')),
    'debug_overlays': group(const {}, RegExp(r'debugMode\s*=\s*true|showPerformanceOverlay:\s*true|FpsTextComponent|debugPaintSizeEnabled\s*=\s*true')),
    'splash': {'packages': allDeps.where((d) => d == 'flutter_native_splash').toList(), 'code': const []},
  };

  final random = sc.grep(lib, RegExp(r'Random\(|Random\.secure|\bRng\(|seed\s*[:=]'), max: 10);
  final existingHooks = sc.grep(lib.where((f) => !f.path.endsWith('/main_capture.dart')).toList(),
      RegExp(r'CAPTURE_(MODE|LEVEL|SEED|PLAY_MODE)'), max: 10);
  final mains = sc.grep(lib, RegExp(r'^(Future<void>|void)\s+main\s*\('), max: 6);

  // Capture setup in place?
  bool exists(String p) => FileSystemEntity.typeSync('${root.path}/$p') != FileSystemEntityType.notFound;
  final gitignore = sc.read('.gitignore') ?? '';
  final setup = {
    'main_capture': exists('lib/main_capture.dart'),
    'config': exists('social/config.yaml'),
    'integration_test_dir': exists('integration_test'),
    'integration_test_dependency': pub.devDeps.containsKey('integration_test'),
    'capture_test': exists('integration_test/capture_test.dart'),
    'test_driver': exists('test_driver/integration_test.dart'),
    'replays': exists('social/replays') ? Directory('${root.path}/social/replays').listSync().map((e) => e.path.split('/').last).toList() : <String>[],
    'performance_log': exists('social/performance_log.md'),
    'gitignore_ignores_output': RegExp(r'^/?social/output/?\s*$', multiLine: true).hasMatch(gitignore),
  };

  // Facts for posts (unconfirmed until the developer says yes).
  final readme = sc.read('README.md') ?? sc.read('readme.md');
  final changelog = sc.read('CHANGELOG.md');
  final storeLinkRe = RegExp(
      r'''https?://(?:play\.google\.com/store/apps/details\?id=[\w.]+|apps\.apple\.com/[^\s)"'<>]+|store\.steampowered\.com/app/\d+[^\s)"'<>]*|[\w-]+\.itch\.io/[^\s)"'<>]+|[\w-]+\.github\.io/[^\s)"'<>]*)''');
  final links = <String>{};
  for (final t in [readme, changelog, sc.read('web/index.html'), ...lib.take(400).map((f) => sc.lines(f).join('\n'))]) {
    if (t == null) continue;
    for (final m in storeLinkRe.allMatches(t)) {
      links.add(m.group(0)!.replaceAll(RegExp(r'[.,;]+$'), ''));
    }
  }

  // Store listing text and release state: where the public description lives, if anywhere.
  final listingFiles = <String>[];
  for (final d in ['fastlane/metadata', 'ios/fastlane/metadata', 'android/fastlane/metadata', 'metadata', 'store', 'docs']) {
    final dir = Directory('${root.path}/$d');
    if (!dir.existsSync()) continue;
    for (final f in dir.listSync(recursive: true, followLinks: false).whereType<File>()) {
      final name = f.path.split('/').last.toLowerCase();
      if (RegExp(r'(description|promotional|subtitle|keywords|listing|store|aso|release_notes|full_description|short_description)').hasMatch(name)) {
        listingFiles.add(sc.rel(f.path));
      }
      if (listingFiles.length >= 12) break;
    }
  }
  final releaseHints = <String>[];
  for (final t in [readme, changelog]) {
    if (t == null) continue;
    for (final line in t.split('\n')) {
      if (RegExp(r'(coming soon|sắp ra mắt|released|phát hành|testflight|beta|out now|available on|app store|google play|pre-?order|wishlist)', caseSensitive: false).hasMatch(line)) {
        releaseHints.add(line.trim().length > 160 ? '${line.trim().substring(0, 160)}…' : line.trim());
      }
      if (releaseHints.length >= 8) break;
    }
  }

  final result = <String, Object?>{
    'is_flutter': true,
    'project': root.path,
    'name': pub.top['name'],
    'description': pub.top['description'],
    'version': pub.top['version'],
    'platforms': platforms,
    'ids': ids,
    'orientation': {
      'guess': guess(),
      'android_manifest': androidOrient,
      'dart': [for (final h in dartOrient) h.toJson()],
    },
    'flame': {
      'used': flamePkgs.contains('flame'),
      'version': pub.deps['flame'],
      'packages': flamePkgs,
      'physics': physics,
    },
    'audio': {
      'packages': allDeps.where(audioPkgs.contains).toList(),
      'asset_files': audioFiles,
      'code': [for (final h in audioHits) h.toJson()],
      'expect_sound': allDeps.any(audioPkgs.contains) || audioFiles > 0,
    },
    'levels': {
      'count_leads': [for (final h in levelCount) h.toJson()],
      'load_leads': [for (final h in levelLoad) h.toJson()],
      'asset_dirs': levelAssets,
    },
    'autoplay': {
      'files': botFiles.take(_maxHits).toList(),
      'leads': [for (final h in botHits) h.toJson()],
    },
    'disable_while_recording': disable,
    'randomness': [for (final h in random) h.toJson()],
    'entry_points': [for (final h in mains) h.toJson()],
    'existing_capture_hooks': [for (final h in existingHooks) h.toJson()],
    'capture_setup': setup,
    'facts_unconfirmed': {
      'readme': excerpt(readme, 900),
      'changelog_top': excerpt(changelog, 900),
      'git': await gitFacts(root),
      'links_found': links.take(10).toList(),
      'store_listing_files': listingFiles,
      'release_hints': releaseHints,
      'note': 'Leads only. A fact goes into a post only after the developer confirms it (config.yaml → facts).',
    },
  };

  if (args.flag('md')) {
    final b = StringBuffer()
      ..writeln('# ${result['name']} — ${root.path}')
      ..writeln('- Platforms: ${platforms.join(', ')} · orientation: ${guess()} · Flame: ${flamePkgs.contains('flame') ? 'yes ${pub.deps['flame']}' : 'no'}${physics.isNotEmpty ? ' (physics: ${physics.join(', ')})' : ''}')
      ..writeln('- Ids: ${ids.entries.where((e) => e.value != null).map((e) => '${e.key}=${e.value}').join(' · ')}')
      ..writeln('- Sound: ${(result['audio'] as Map)['expect_sound'] == true ? 'yes' : 'none found'} (${allDeps.where(audioPkgs.contains).join(', ')}; $audioFiles audio files)')
      ..writeln('- Capture setup: ${setup.entries.where((e) => e.value == true || (e.value is List && (e.value as List).isNotEmpty)).map((e) => e.key).join(', ').ifEmpty('none')}')
      ..writeln('- Level count leads: ${levelCount.take(4).map((h) => '${h.file}:${h.line}').join(', ').ifEmpty('none')}${levelAssets.isNotEmpty ? ' · level assets ${levelAssets.map((a) => '${a['dir']} (${a['files']})').join(', ')}' : ''}')
      ..writeln('- Bot/autoplay leads: ${[...botFiles.take(6), ...botHits.take(4).map((h) => '${h.file}:${h.line}')].join(', ').ifEmpty('none')}')
      ..writeln('- Switch off while recording: ${disable.entries.where((e) => ((e.value['packages'] as List).isNotEmpty || (e.value['code'] as List).isNotEmpty)).map((e) => e.key).join(', ').ifEmpty('nothing found')}');
    stdout.write(b.toString());
  } else {
    stdout.writeln(prettyJson(result));
  }
}

extension on String {
  String ifEmpty(String other) => isEmpty ? other : this;
}
