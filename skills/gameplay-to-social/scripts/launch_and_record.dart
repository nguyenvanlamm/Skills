// Finds a device, runs the game's capture entry at one level and records it.
//
//   dart launch_and_record.dart devices --project DIR [--saved-device ID]
//   dart launch_and_record.dart record  --project DIR --platform android|ios-sim|linux|macos|windows|web
//        --device ID --level N --out <run>/work/takes
//        [--duration 20] [--play-mode bot|replay|replay-record|script|human] [--seed 42]
//        [--takes 1] [--vary-seed] [--build-mode auto|profile|release|debug]
//        [--target lib/main_capture.dart] [--app-id ID] [--hold-ms 3000] [--tail 2]
//        [--boot-timeout 900] [--start-timeout 120] [--audio auto|none|default|isolated]
//        [--display auto|screen|virtual] [--size WxH] [--orientation portrait|landscape]
//        [--replay FILE] [--replay-out FILE] [--window-title TITLE] [--defines K=V,K2=V2]
//        [--game-audio yes|no] [--no-dnd] [--dry-run]
//
// The app prints marker lines (see references/flutter_capture.md § Markers):
//   CAPTURE_READY          first frame drawn: the recorder starts now
//   CAPTURE_LEVEL_START    the level is playable: the cut starts here
//   CAPTURE_EVENT <label>  something worth a look (combo, win, boss…), kept with its time
//   CAPTURE_LEVEL_END <r>  level over (win/lose)
//   CAPTURE_REPLAY* …      input log of a replay-record take
//   CAPTURE_ERROR <msg>    the entry could not set up the level
//
// Every step has a timeout; the app, the recorder, the browser, Xvfb and the audio sink are
// stopped on success, on error and on Ctrl+C, and the phone's Do Not Disturb and stay-awake
// settings are put back. Each take leaves take_N.<mkv|mov>, take_N.json and take_N.log.
//
// Exit codes: 0 all takes recorded, 4 no usable device (guidance printed), 6 a tool is missing,
// 7 build/launch failed, 8 the level never became playable, 1 other error, 2 usage.

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'lib/cdp.dart';
import 'lib/common.dart';
import 'lib/static_server.dart';

// ======================================================================= devices

class Dev {
  Dev(this.id, this.name, this.targetPlatform, this.emulator, this.sdk);

  final String id;
  final String name;
  final String targetPlatform;
  final bool emulator;
  final String sdk;

  String get platform {
    if (targetPlatform.startsWith('android')) return 'android';
    if (targetPlatform == 'ios') return emulator ? 'ios-sim' : 'ios';
    if (targetPlatform.startsWith('linux')) return 'linux';
    if (targetPlatform == 'darwin') return 'macos';
    if (targetPlatform.startsWith('windows')) return 'windows';
    if (targetPlatform.startsWith('web')) return 'web';
    return targetPlatform;
  }

  /// Android API level from "Android 13 (API 33)".
  int? get apiLevel => int.tryParse(RegExp(r'API (\d+)').firstMatch(sdk)?.group(1) ?? '');
}

Future<List<Dev>> flutterDevices() async {
  final r = await runCmd('flutter', ['devices', '--machine', '--device-timeout', '8'], timeout: const Duration(seconds: 90));
  if (r.exitCode == 127) fail('flutter not found on PATH', code: 6);
  final start = r.stdout.indexOf('[');
  if (start < 0) return [];
  try {
    final list = (jsonDecode(r.stdout.substring(start)) as List).cast<Map<String, dynamic>>();
    return [
      for (final d in list)
        Dev('${d['id']}', '${d['name']}', '${d['targetPlatform']}', d['emulator'] == true, '${d['sdk'] ?? ''}'),
    ];
  } on FormatException {
    return [];
  }
}

Future<Map<String, String>> adbStates() async {
  final adb = tool('adb');
  if (adb == null) return {};
  final r = await runCmd(adb, ['devices'], timeout: const Duration(seconds: 15));
  final out = <String, String>{};
  for (final line in r.stdout.split('\n').skip(1)) {
    final parts = line.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2) out[parts[0]] = parts[1];
  }
  return out;
}

Future<List<String>> flutterEmulators() async {
  final r = await runCmd('flutter', ['emulators'], timeout: const Duration(seconds: 60));
  return [
    for (final line in r.stdout.split('\n'))
      if (line.contains('•') && !line.contains('Id ') && line.split('•').length >= 3) line.split('•').first.trim(),
  ];
}

List<String> projectPlatforms(String project) => [
      for (final p in ['android', 'ios', 'web', 'macos', 'windows', 'linux'])
        if (Directory('$project/$p').existsSync()) p,
    ];

bool get onWayland => (Platform.environment['WAYLAND_DISPLAY'] ?? '').isNotEmpty;

/// Unattended takes (bot, replay, script) render on a private Xvfb display at the export size,
/// so nothing appears on the desktop and a locked screen doesn't matter. A human needs to see
/// the game, so human and replay-record takes use a window on the real screen.
bool useVirtualDisplay(String displayMode, String playMode) {
  if (displayMode == 'virtual') return true;
  if (displayMode == 'screen') return false;
  return playMode != 'human' && playMode != 'replay-record' && which('Xvfb') != null;
}

/// Why an on-screen window would render badly right now (locked or blanked screen), or null.
Future<String?> screenUnavailable() async {
  final r = await runCmd('gdbus', [
    'call', '--session', '--dest', 'org.gnome.ScreenSaver', '--object-path', '/org/gnome/ScreenSaver',
    '--method', 'org.gnome.ScreenSaver.GetActive',
  ], timeout: const Duration(seconds: 5));
  if (r.ok && r.stdout.contains('true')) return 'the screen saver is active (screen locked or off)';
  final id = Platform.environment['XDG_SESSION_ID'];
  if (id != null && id.isNotEmpty) {
    final l = await runCmd('loginctl', ['show-session', id, '-p', 'LockedHint'], timeout: const Duration(seconds: 5));
    if (l.ok && l.stdout.trim() == 'LockedHint=yes') return 'the session is locked';
  }
  return null;
}

Future<String?> scrcpyVersion() async {
  final s = tool('scrcpy');
  if (s == null) return null;
  final r = await runCmd(s, ['--version'], timeout: const Duration(seconds: 15));
  return RegExp(r'scrcpy (\d+\.\d+(?:\.\d+)?)').firstMatch(r.stdout + r.stderr)?.group(1) ?? 'unknown';
}

List<String> linuxToolchainMissing() => [
      if (which('clang++') == null) 'clang++',
      if (which('cmake') == null) 'cmake',
      if (which('ninja') == null) 'ninja',
      if (which('pkg-config') == null) 'pkg-config',
      if (which('pkg-config') != null && Process.runSync('pkg-config', ['--exists', 'gtk+-3.0']).exitCode != 0) 'libgtk-3-dev',
    ];

String installHint(String what) {
  final mac = Platform.isMacOS;
  final win = Platform.isWindows;
  switch (what) {
    case 'scrcpy':
      return mac
          ? 'brew install scrcpy'
          : win
              ? 'winget install --exact Genymobile.scrcpy'
              : 'sudo snap install scrcpy (or the GitHub release; distro packages are often 1.x without audio)';
    case 'ffmpeg':
      return mac ? 'brew install ffmpeg' : win ? 'winget install Gyan.FFmpeg' : 'sudo apt install ffmpeg';
    case 'xwininfo':
      return 'sudo apt install x11-utils';
    case 'linux-toolchain':
      return 'sudo apt install clang cmake ninja-build pkg-config libgtk-3-dev';
    case 'chrome':
      return 'install Google Chrome, or point CHROME_EXECUTABLE at a Chromium';
    default:
      return 'install $what';
  }
}

Future<Map<String, Object?>> rankDevices(String project, {String? saved}) async {
  final plats = projectPlatforms(project);
  final devs = await flutterDevices();
  final adb = await adbStates();
  final scrcpy = await scrcpyVersion();
  final ffmpeg = tool('ffmpeg');
  final entries = <Map<String, Object?>>[];
  const rank = {'android-device': 1, 'android-emulator': 2, 'ios-sim': 3, 'linux': 4, 'macos': 4, 'windows': 4, 'web': 5, 'ios': 9};
  for (final d in devs) {
    final kind = d.platform == 'android' ? (d.emulator ? 'android-emulator' : 'android-device') : d.platform;
    final why = <String>[];
    final notes = <String>[];
    var recorder = '';
    var audio = false;
    final needDir = d.platform == 'ios-sim' ? 'ios' : d.platform;
    if (!plats.contains(needDir)) why.add('the project has no $needDir/ folder');
    switch (d.platform) {
      case 'android':
        recorder = 'scrcpy ${scrcpy ?? '(missing)'}';
        if (scrcpy == null) why.add('scrcpy is not installed (${installHint('scrcpy')})');
        final api = d.apiLevel;
        audio = scrcpy != null && !scrcpy.startsWith('1.') && (api ?? 0) >= 30;
        if (!audio) notes.add('no game audio: needs Android 11+ and scrcpy 2+ (device API ${api ?? '?'})');
        notes.add(d.emulator ? 'emulator: --profile works on x86_64/arm64 images; a 1080×1920 AVD (pixel_2) gives 9:16 directly' : 'real device: use --profile');
      case 'ios-sim':
        recorder = 'xcrun simctl io recordVideo';
        if (!Platform.isMacOS || which('xcrun') == null) why.add('needs macOS with Xcode');
        notes.add('simulator: debug builds only, no audio in the recording');
      case 'ios':
        recorder = 'none';
        why.add('a real iPhone cannot be recorded from here: record on the phone (Control Centre → Screen Recording) and pass the file');
      case 'linux':
        recorder = 'ffmpeg x11grab (window)';
        if (ffmpeg == null) why.add('ffmpeg missing (${installHint('ffmpeg')})');
        if (which('xwininfo') == null) why.add('xwininfo missing (${installHint('xwininfo')})');
        final missing = linuxToolchainMissing();
        if (missing.isNotEmpty) why.add('Linux toolchain missing: ${missing.join(', ')} (${installHint('linux-toolchain')})');
        audio = true;
        notes.add('desktop window: portrait games get the window size the runner sets (often 1280×720)');
      case 'macos':
        recorder = 'ffmpeg avfoundation (screen + crop) — untested';
        if (ffmpeg == null) why.add('ffmpeg missing (${installHint('ffmpeg')})');
        notes.add('game audio needs a loopback device such as BlackHole');
      case 'windows':
        recorder = 'ffmpeg gdigrab (window) — untested';
        if (ffmpeg == null) why.add('ffmpeg missing (${installHint('ffmpeg')})');
        notes.add('game audio needs a capture device such as Stereo Mix');
      case 'web':
        if (d.id == 'web-server') why.add('use the chrome device');
        recorder = Platform.isLinux ? 'ffmpeg x11grab of a Chrome window (Xvfb when unattended)' : 'ffmpeg screen capture — untested here';
        if (ffmpeg == null) why.add('ffmpeg missing (${installHint('ffmpeg')})');
        if (tool('chrome') == null) why.add('Chrome not found (${installHint('chrome')})');
        if (Platform.isLinux && which('xwininfo') == null) why.add('xwininfo missing (${installHint('xwininfo')})');
        audio = Platform.isLinux;
        notes.add('a Chrome window on screen (GPU): on a 1080p monitor a portrait window is about 562×1000, so the '
            '1080×1920 export is upscaled ~1.9×; an Android device gives crisp 9:16');
    }
    entries.add({
      'id': d.id,
      'name': d.name,
      'platform': d.platform,
      'kind': kind,
      'rank': rank[kind] ?? 9,
      'usable': why.isEmpty,
      'recorder': recorder,
      'audio': audio,
      if (d.sdk.isNotEmpty) 'sdk': d.sdk,
      if (why.isNotEmpty) 'why_not': why,
      'notes': notes,
    });
  }
  // adb sees devices flutter does not list (unauthorized, offline).
  for (final e in adb.entries) {
    if (e.value != 'device' && !devs.any((d) => d.id == e.key)) {
      entries.add({
        'id': e.key,
        'name': 'Android device (${e.value})',
        'platform': 'android',
        'kind': 'android-device',
        'rank': 1,
        'usable': false,
        'why_not': [
          e.value == 'unauthorized'
              ? 'unauthorized: unlock the phone and accept "Allow USB debugging"'
              : 'adb state "${e.value}": reconnect the cable or run `adb kill-server`',
        ],
        'notes': [],
      });
    }
  }
  entries.sort((a, b) => (a['rank'] as int).compareTo(b['rank'] as int));
  final usable = entries.where((e) => e['usable'] == true).toList();
  final guidance = <String>[];
  final hasAndroidUsable = usable.any((e) => e['platform'] == 'android');
  if (plats.contains('android') && !hasAndroidUsable) {
    final emus = await flutterEmulators();
    final sdk = androidSdk();
    final images = sdk == null ? <String>[] : (Directory('$sdk/system-images').existsSync()
        ? Directory('$sdk/system-images').listSync().map((e) => e.path.split('/').last).toList()
        : <String>[]);
    final adbCmd = tool('adb') ?? 'adb';
    final sdkm = tool('sdkmanager') ?? (sdk != null ? '$sdk/cmdline-tools/latest/bin/sdkmanager' : 'sdkmanager');
    final avdm = tool('avdmanager') ?? (sdk != null ? '$sdk/cmdline-tools/latest/bin/avdmanager' : 'avdmanager');
    guidance.add('Phone: enable Developer options → USB debugging, plug it in, accept the prompt; `$adbCmd devices` must show it as "device".');
    if (emus.isNotEmpty) {
      guidance.add('Emulator: start one with `flutter emulators --launch ${emus.first}` (available: ${emus.join(', ')}), wait for the home screen, then run this again.');
    } else {
      guidance.add('Emulator: none exists yet. For a 1080×1920 (9:16) one, with the Android SDK tools:');
      if (tool('emulator') == null) guidance.add('  $sdkm "emulator"   # the emulator itself is not installed');
      if (images.isEmpty) guidance.add('  $sdkm "system-images;android-35;google_apis;x86_64"');
      guidance.add('  $avdm create avd -n g2s_pixel2 -k "system-images;android-35;google_apis;x86_64" -d pixel_2');
      guidance.add('  flutter emulators --launch g2s_pixel2');
      if (Platform.isLinux && !File('/dev/kvm').existsSync()) {
        guidance.add('  (no /dev/kvm: without hardware acceleration the emulator is very slow)');
      }
      guidance.add('  (the skill never installs these itself)');
    }
    if (tool('scrcpy') == null) guidance.add('Recorder: scrcpy is needed for Android (${installHint('scrcpy')}).');
  }
  if (usable.isEmpty && plats.contains('ios')) {
    guidance.add('iPhone: you play and record on the phone (Control Centre → Screen Recording, microphone off, Do Not Disturb on), '
        'then give me the file; say at which second the level starts if the clip opens on a menu.');
  }
  Map<String, Object?>? savedState;
  if (saved != null && saved.isNotEmpty) {
    final hit = entries.where((e) => e['id'] == saved).toList();
    savedState = {
      'id': saved,
      'connected': hit.isNotEmpty,
      'usable': hit.isNotEmpty && hit.first['usable'] == true,
      if (hit.isEmpty) 'note': 'the device saved in config.yaml is not connected',
    };
  }
  return {
    'project_platforms': plats,
    if (savedState != null) 'saved_device': savedState,
    'devices': entries,
    'usable': usable.length,
    'best': usable.isEmpty ? null : usable.first,
    'choices': usable.length > 1 ? 'more than one usable device: ask the user once, save it in social/config.yaml → capture.device' : null,
    'guidance': guidance,
  };
}

Future<void> cmdDevices(Args args) async {
  final project = Directory(args.str('project', Directory.current.path)).absolute.path;
  final result = await rankDevices(project, saved: args['saved-device']);
  stdout.writeln(prettyJson(result));
  exit((result['usable'] as int) > 0 ? 0 : 4);
}

// ======================================================================= record

/// Everything a take started, stopped in reverse order whatever happens.
class Cleanup {
  final List<(String, Future<void> Function())> _steps = [];
  bool _ran = false;

  void add(String what, Future<void> Function() fn) => _steps.add((what, fn));

  Future<void> run() async {
    if (_ran) return;
    _ran = true;
    for (final (what, fn) in _steps.reversed) {
      try {
        await fn().timeout(const Duration(seconds: 20));
      } on Object catch (e) {
        info('cleanup: $what failed: $e');
      }
    }
    _steps.clear();
  }
}

final Cleanup globalCleanup = Cleanup();

Future<void> stopProcess(Process p, {String? quitLine, ProcessSignal first = ProcessSignal.sigint, Duration grace = const Duration(seconds: 10)}) async {
  if (quitLine != null) {
    try {
      p.stdin.writeln(quitLine);
      await p.stdin.flush();
    } on Object {
      // stdin closed.
    }
    final code = await p.exitCode.timeout(grace, onTimeout: () => -999);
    if (code != -999) return;
  }
  p.kill(first);
  var code = await p.exitCode.timeout(grace, onTimeout: () => -999);
  if (code != -999) return;
  p.kill(ProcessSignal.sigterm);
  code = await p.exitCode.timeout(const Duration(seconds: 5), onTimeout: () => -999);
  if (code == -999) p.kill(ProcessSignal.sigkill);
}

class Take {
  Take(this.n, this.seed);

  final int n;
  final int seed;
  final List<String> log = [];
  final List<Map<String, Object>> events = [];
  final List<String> warnings = [];
  final List<Map<String, Object?>> replay = [];
  Map<String, Object?>? replayMeta;
  double? readyHost;
  double? recStartHost;
  double? levelStartHost;
  double? levelEndHost;
  String levelStartSource = 'log';
  String recorder = '';
  String? gpu;
  final List<int> browserFps = [];
  String? error;
  int errorCode = 1;
  final Completer<void> ready = Completer();
  final Completer<void> levelStart = Completer();
  final Completer<void> appExited = Completer();
  final Completer<void> recStarted = Completer();

  void addLog(String line) {
    log.add(line);
    if (log.length > 4000) log.removeRange(0, 1000);
  }
}

final RegExp _marker = RegExp(r'CAPTURE_(BOOT|READY|LEVEL_START|LEVEL_END|EVENT|REPLAY_META|REPLAY_END|REPLAY|ERROR|FPS|GPU)\b ?(.*)$');
final RegExp _buildError = RegExp(
    r"(Error: |FAILURE: Build failed|BUILD FAILED|Gradle task \S+ failed|Target file .* not found|No supported devices|Error launching application|Could not find an option|Unhandled exception|Failed to build|Exception: )");

void onAppLine(Take take, String raw) {
  final line = raw.trimRight();
  if (line.isEmpty) return;
  take.addLog(line);
  final m = _marker.firstMatch(line);
  if (m == null) {
    if (_buildError.hasMatch(line) && take.levelStartHost == null && take.error == null) {
      take.warnings.add(line.trim());
    }
    return;
  }
  final kind = m.group(1)!;
  final rest = m.group(2)!.trim();
  final t = nowS;
  switch (kind) {
    case 'BOOT':
      break;
    case 'READY':
      take.readyHost ??= t;
      if (!take.ready.isCompleted) take.ready.complete();
    case 'LEVEL_START':
      if (take.levelStartHost == null) {
        take.levelStartHost = t;
        if (!take.ready.isCompleted) take.ready.complete();
        if (!take.levelStart.isCompleted) take.levelStart.complete();
      }
    case 'LEVEL_END':
      take.levelEndHost ??= t;
      take.events.add({'host': t, 'label': 'level_end ${rest.isEmpty ? '' : rest}'.trim()});
    case 'EVENT':
      take.events.add({'host': t, 'label': rest});
    case 'REPLAY_META':
      try {
        take.replayMeta = (jsonDecode(rest) as Map).cast<String, Object?>();
      } on FormatException {
        take.warnings.add('bad CAPTURE_REPLAY_META line');
      }
    case 'REPLAY':
      try {
        take.replay.add((jsonDecode(rest) as Map).cast<String, Object?>());
      } on FormatException {
        take.warnings.add('bad CAPTURE_REPLAY line');
      }
    case 'REPLAY_END':
      break;
    case 'FPS':
      final v = int.tryParse(rest);
      if (v != null) take.browserFps.add(v);
    case 'GPU':
      take.gpu ??= rest;
      if (RegExp('swiftshader|llvmpipe|software|no webgl|error', caseSensitive: false).hasMatch(rest)) {
        take.warnings.add('Chrome draws in software ($rest): frames may be slow or wrong — check the contact sheet; '
            'try --display screen, or set G2S_CHROME_GPU_FLAGS for this GPU');
      }
    case 'ERROR':
      take.error ??= 'the capture entry reported: $rest';
      take.errorCode = 7;
      if (!take.ready.isCompleted) take.ready.completeError(StateError(take.error!));
  }
}

void pipeLines(Stream<List<int>> s, void Function(String) onLine) {
  s.transform(const Utf8Decoder(allowMalformed: true)).transform(const LineSplitter()).listen(onLine, onError: (_) {});
}

// ----------------------------------------------------------------- display + audio (Linux)

class Display {
  Display(this.name, this.virtual, this.width, this.height);

  final String name; // ":0", ":93"
  final bool virtual;
  final int width;
  final int height;
}

Future<Display> startXvfb(int w, int h, Cleanup cleanup) async {
  final xvfb = which('Xvfb') ?? fail('Xvfb not found (sudo apt install xvfb) — or use --display screen', code: 6);
  var n = 90 + (pid % 60);
  while (File('/tmp/.X11-unix/X$n').existsSync() || File('/tmp/.X$n-lock').existsSync()) {
    n++;
  }
  final p = await Process.start(xvfb, [':$n', '-screen', '0', '${w}x${h}x24', '-nolisten', 'tcp', '-noreset']);
  pipeLines(p.stderr, (_) {});
  cleanup.add('Xvfb :$n', () async => stopProcess(p, first: ProcessSignal.sigterm, grace: const Duration(seconds: 3)));
  final deadline = nowS + 10;
  while (!File('/tmp/.X11-unix/X$n').existsSync()) {
    if (nowS > deadline) fail('Xvfb :$n did not start', code: 6);
    await Future<void>.delayed(const Duration(milliseconds: 100));
  }
  return Display(':$n', true, w, h);
}

/// A PipeWire null sink only the game plays into, so the take has the game and nothing else.
Future<String?> startIsolatedSink(Cleanup cleanup) async {
  final pwcli = which('pw-cli');
  if (pwcli == null) return null;
  final name = 'g2s_capture_$pid';
  final r = await runCmd(pwcli, [
    'create-node', 'adapter',
    '{ factory.name=support.null-audio-sink node.name=$name node.description=g2s-capture media.class=Audio/Sink object.linger=true audio.position=[FL FR] }',
  ], timeout: const Duration(seconds: 10));
  if (!r.ok) return null;
  await Future<void>.delayed(const Duration(milliseconds: 400));
  cleanup.add('audio sink $name', () async {
    final ls = await runCmd(pwcli, ['ls', 'Node'], timeout: const Duration(seconds: 10));
    final lines = ls.stdout.split('\n');
    for (var i = 0; i < lines.length; i++) {
      if (lines[i].contains('node.name = "$name"')) {
        for (var j = i; j >= 0 && j > i - 12; j--) {
          final m = RegExp(r'^\s*id (\d+),').firstMatch(lines[j]);
          if (m != null) {
            await runCmd(pwcli, ['destroy', m.group(1)!], timeout: const Duration(seconds: 10));
            break;
          }
        }
      }
    }
  });
  return name;
}

/// The largest mapped X window whose WM_CLASS or name matches.
Future<(String, int, int)?> findWindow(String display, {String? wmClass, String? title}) async {
  final xw = which('xwininfo');
  if (xw == null) return null;
  final r = await runCmd(xw, ['-root', '-tree'], env: {...Platform.environment, 'DISPLAY': display}, timeout: const Duration(seconds: 10));
  (String, int, int)? best;
  for (final line in r.stdout.split('\n')) {
    final m = RegExp(r'^\s*(0x[0-9a-f]+) "([^"]*)": \(("([^"]*)" "([^"]*)")?\)\s+(\d+)x(\d+)\+').firstMatch(line);
    if (m == null) continue;
    final name = m.group(2)!;
    final cls = m.group(5) ?? '';
    final w = int.parse(m.group(6)!);
    final h = int.parse(m.group(7)!);
    if (w < 100 || h < 100) continue;
    final hit = (wmClass != null && cls == wmClass) || (title != null && name == title);
    if (!hit) continue;
    if (best == null || w * h > best.$2 * best.$3) best = (m.group(1)!, w, h);
  }
  return best;
}

// ----------------------------------------------------------------- recorders

class Recorder {
  Recorder(this.process, this.file, this.description, {this.audioProcess, this.videoFile, this.audioFile});

  final Process process;
  final String file; // what the rest of the pipeline reads
  final String description;

  /// On X11 the sound is recorded by a second ffmpeg: one process grabbing both drops the picture
  /// to ~40 fps. The parts are joined on their own start times in [finish].
  final Process? audioProcess;
  final String? videoFile;
  final String? audioFile;
  double? audioStartHost;

  Future<void> stop() async {
    await Future.wait([stopProcess(process), if (audioProcess != null) stopProcess(audioProcess!)]);
  }

  /// Joins the video and audio parts into [file]; returns a warning, or null.
  Future<String?> finish(double? videoStartHost) async {
    final v = videoFile;
    if (v == null) return null;
    if (!File(v).existsSync()) return 'video part missing';
    final a = audioFile;
    if (a == null || !File(a).existsSync() || audioStartHost == null || videoStartHost == null) {
      File(v).renameSync(file);
      return a == null ? null : 'the audio part did not record: the take is silent';
    }
    final offset = audioStartHost! - videoStartHost; // > 0: the sound began after the picture
    final r = await runCmd(tool('ffmpeg')!, [
      '-hide_banner', '-nostdin', '-y', '-i', v,
      if (offset >= 0) ...['-itsoffset', offset.toStringAsFixed(3)] else ...['-ss', (-offset).toStringAsFixed(3)],
      '-i', a, '-map', '0:v', '-map', '1:a', '-c', 'copy', file,
    ], timeout: const Duration(minutes: 2));
    if (!r.ok) {
      File(v).renameSync(file);
      return 'joining picture and sound failed; the take is silent (${r.stderr.trim().split('\n').last})';
    }
    File(v).deleteSync();
    File(a).deleteSync();
    return null;
  }
}

void _watchProgress(Process p, void Function(double t0) onStart) {
  var done = false;
  pipeLines(p.stdout, (l) {
    // -progress: … out_time_us=T … progress=continue, every 0.25 s
    if (done || !l.startsWith('out_time_us=')) return;
    final us = int.tryParse(l.substring(12)) ?? 0;
    if (us > 0) {
      done = true;
      onStart(nowS - us / 1e6);
    }
  });
}

Future<Recorder> startFfmpegX11(Take take, Display display, String file, {String? windowId, String? audioSource, int fps = 60}) async {
  final ffmpeg = tool('ffmpeg') ?? fail('ffmpeg not found (${installHint('ffmpeg')})', code: 6);
  final videoFile = audioSource == null ? file : file.replaceFirst(RegExp(r'\.mkv$'), '.video.mkv');
  final p = await Process.start(ffmpeg, [
    '-hide_banner', '-nostdin', '-y',
    '-thread_queue_size', '1024', '-f', 'x11grab', '-framerate', '$fps', '-draw_mouse', '0',
    if (windowId != null) ...['-window_id', windowId] else ...['-video_size', '${display.width}x${display.height}'],
    '-i', windowId != null ? display.name : '${display.name}.0+0,0',
    // Window sizes can be odd (563x1001); H.264 needs even ones.
    '-vf', 'crop=trunc(iw/2)*2:trunc(ih/2)*2',
    '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency', '-crf', '16', '-pix_fmt', 'yuv420p',
    '-progress', 'pipe:1', '-stats_period', '0.25', '-f', 'matroska', videoFile,
  ]);
  final errTail = <String>[];
  pipeLines(p.stderr, (l) {
    errTail.add(l);
    if (errTail.length > 30) errTail.removeAt(0);
  });
  _watchProgress(p, (t0) {
    take.recStartHost = t0;
    if (!take.recStarted.isCompleted) take.recStarted.complete();
  });
  unawaited(p.exitCode.then((code) {
    if (!take.recStarted.isCompleted) take.recStarted.completeError(StateError('ffmpeg exited ($code): ${errTail.join(' | ')}'));
  }));
  Process? ap;
  String? audioFile;
  Recorder? rec;
  if (audioSource != null) {
    audioFile = file.replaceFirst(RegExp(r'\.mkv$'), '.audio.mka');
    ap = await Process.start(ffmpeg, [
      '-hide_banner', '-nostdin', '-y', '-thread_queue_size', '1024', '-f', 'pulse', '-i', audioSource,
      '-c:a', 'aac', '-b:a', '192k', '-progress', 'pipe:1', '-stats_period', '0.25', '-f', 'matroska', audioFile,
    ]);
    pipeLines(ap.stderr, (_) {});
    _watchProgress(ap, (t0) => rec?.audioStartHost = t0);
  }
  rec = Recorder(p, file,
      'ffmpeg x11grab ${windowId != null ? 'window $windowId' : 'screen'} on ${display.name}${display.virtual ? ' (Xvfb ${display.width}x${display.height})' : ''}${audioSource != null ? ' + separate audio from $audioSource' : ''}',
      audioProcess: ap, videoFile: audioSource == null ? null : videoFile, audioFile: audioFile);
  return rec;
}

Future<Recorder> startScrcpy(Take take, String serial, String file, {required bool audio, String? version}) async {
  final scrcpy = tool('scrcpy') ?? fail('scrcpy not found (${installHint('scrcpy')})', code: 6);
  final v2 = version != null && !version.startsWith('1.');
  final args = [
    '-s', serial, '-N', '-n', '--record=$file', '--max-fps=60',
    if (v2) '--video-bit-rate=16M' else '--bit-rate=16M',
    if (v2 && !audio) '--no-audio',
  ];
  final p = await Process.start(scrcpy, args, environment: {...Platform.environment, if (tool('adb') != null) 'ADB': tool('adb')!});
  void watch(String l) {
    take.addLog('[scrcpy] $l');
    if (take.recStartHost == null && RegExp('Recording started', caseSensitive: false).hasMatch(l)) {
      take.recStartHost = nowS;
      if (!take.recStarted.isCompleted) take.recStarted.complete();
    }
  }

  pipeLines(p.stdout, watch);
  pipeLines(p.stderr, watch);
  unawaited(p.exitCode.then((code) {
    if (!take.recStarted.isCompleted) take.recStarted.completeError(StateError('scrcpy exited ($code) before recording; see take log'));
  }));
  // Older scrcpy prints nothing on start: assume ~1 s.
  unawaited(Future<void>.delayed(const Duration(seconds: 6)).then((_) {
    if (!take.recStarted.isCompleted) {
      take.recStartHost = nowS - 5;
      take.warnings.add('scrcpy did not say "Recording started"; start time estimated');
      take.recStarted.complete();
    }
  }));
  return Recorder(p, file, 'scrcpy ${version ?? ''} ${audio ? '(video + device audio)' : '(video only)'}');
}

Future<Recorder> startSimctl(Take take, String udid, String file) async {
  final p = await Process.start('xcrun', ['simctl', 'io', udid, 'recordVideo', '--codec=h264', '--force', file]);
  void watch(String l) {
    take.addLog('[simctl] $l');
    if (take.recStartHost == null && l.toLowerCase().contains('recording started')) {
      take.recStartHost = nowS;
      if (!take.recStarted.isCompleted) take.recStarted.complete();
    }
  }

  pipeLines(p.stdout, watch);
  pipeLines(p.stderr, watch);
  unawaited(p.exitCode.then((code) {
    if (!take.recStarted.isCompleted) take.recStarted.completeError(StateError('simctl recordVideo exited ($code)'));
  }));
  return Recorder(p, file, 'xcrun simctl recordVideo (no audio)');
}

/// macOS / Windows screen capture. Untested on this skill's dev machine; kept simple.
Future<Recorder> startFfmpegDesktop(Take take, String file, {String? windowTitle}) async {
  final ffmpeg = tool('ffmpeg') ?? fail('ffmpeg not found (${installHint('ffmpeg')})', code: 6);
  final List<String> input;
  if (Platform.isMacOS) {
    input = ['-f', 'avfoundation', '-capture_cursor', '0', '-framerate', '60', '-i', '${Platform.environment['G2S_AVF_SCREEN'] ?? '1'}:none'];
  } else if (Platform.isWindows) {
    input = ['-f', 'gdigrab', '-framerate', '60', '-draw_mouse', '0', '-i', windowTitle != null ? 'title=$windowTitle' : 'desktop'];
  } else {
    fail('no desktop recorder for this OS', code: 6);
  }
  final p = await Process.start(ffmpeg, [
    '-hide_banner', '-nostdin', '-y', ...input,
    '-vf', 'crop=trunc(iw/2)*2:trunc(ih/2)*2',
    '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '16', '-pix_fmt', 'yuv420p',
    '-progress', 'pipe:1', '-stats_period', '0.25', '-f', 'matroska', file,
  ]);
  pipeLines(p.stderr, (_) {});
  pipeLines(p.stdout, (l) {
    if (take.recStartHost == null && l.startsWith('out_time_us=')) {
      final us = int.tryParse(l.substring(12)) ?? 0;
      if (us > 0) {
        take.recStartHost = nowS - us / 1e6;
        if (!take.recStarted.isCompleted) take.recStarted.complete();
      }
    }
  });
  return Recorder(p, file, 'ffmpeg ${Platform.isMacOS ? 'avfoundation screen' : 'gdigrab'} (untested path; crop with process_video --crop)');
}

// ----------------------------------------------------------------- device settings (Android)

Future<void> androidPrepare(String serial, {required bool dnd, required Cleanup cleanup}) async {
  final adb = tool('adb');
  if (adb == null) return;
  Future<String> sh(List<String> a) async => (await runCmd(adb, ['-s', serial, 'shell', ...a], timeout: const Duration(seconds: 15))).stdout.trim();
  await sh(['input', 'keyevent', 'KEYCODE_WAKEUP']);
  final stay = await sh(['settings', 'get', 'global', 'stay_on_while_plugged_in']);
  await sh(['settings', 'put', 'global', 'stay_on_while_plugged_in', '7']);
  cleanup.add('stay-awake setting', () async => sh(['settings', 'put', 'global', 'stay_on_while_plugged_in', stay.isEmpty || stay == 'null' ? '0' : stay]));
  if (dnd) {
    final zen = await sh(['settings', 'get', 'global', 'zen_mode']);
    final r = await sh(['cmd', 'notification', 'set_dnd', 'priority']);
    if (!r.toLowerCase().contains('unknown')) {
      const back = {'0': 'off', '1': 'priority', '2': 'none', '3': 'alarms'};
      cleanup.add('Do Not Disturb', () async => sh(['cmd', 'notification', 'set_dnd', back[zen] ?? 'off']));
    }
  }
}

Future<void> linuxDnd(Cleanup cleanup) async {
  final gs = which('gsettings');
  if (gs == null) return;
  final r = await runCmd(gs, ['get', 'org.gnome.desktop.notifications', 'show-banners'], timeout: const Duration(seconds: 5));
  if (!r.ok) return;
  final before = r.stdout.trim();
  await runCmd(gs, ['set', 'org.gnome.desktop.notifications', 'show-banners', 'false'], timeout: const Duration(seconds: 5));
  cleanup.add('desktop notifications', () async => runCmd(gs, ['set', 'org.gnome.desktop.notifications', 'show-banners', before], timeout: const Duration(seconds: 5)));
}

// ----------------------------------------------------------------- one take

class Plan {
  late String project;
  late String platform;
  late String device;
  late int level;
  late double duration;
  late String outDir;
  late String playMode;
  late String buildMode;
  late String target;
  String? appId;
  late int holdMs;
  late double tail;
  late int bootTimeout;
  late int startTimeout;
  late String audioMode;
  late String displayMode;
  int? width;
  int? height;
  late String orientation;
  String? replayIn;
  String? replayOut;
  String? windowTitle;
  final Map<String, String> defines = {};
  late bool dnd;
  bool gameAudio = true;
  int? apiLevel;
  bool emulator = false;
  String? scrcpyVersion;
  // web
  String? webBuildDir;
  StaticServer? server;
}

List<String> dartDefines(Plan plan, Take take, {String? replayPath}) => [
      '--dart-define=CAPTURE_MODE=true',
      '--dart-define=CAPTURE_LEVEL=${plan.level}',
      '--dart-define=CAPTURE_SEED=${take.seed}',
      '--dart-define=CAPTURE_PLAY_MODE=${plan.playMode}',
      '--dart-define=CAPTURE_HOLD_MS=${plan.holdMs}',
      if (replayPath != null) '--dart-define=CAPTURE_REPLAY_PATH=$replayPath',
      for (final e in plan.defines.entries) '--dart-define=${e.key}=${e.value}',
    ];

bool expectsAudio(Plan plan) {
  if (plan.audioMode == 'none' || !plan.gameAudio) return false;
  switch (plan.platform) {
    case 'android':
      return (plan.apiLevel ?? 0) >= 30 && plan.scrcpyVersion != null && !plan.scrcpyVersion!.startsWith('1.');
    case 'ios-sim':
      return false;
    case 'linux':
    case 'web':
      return Platform.isLinux;
    default:
      return false;
  }
}

Future<void> runTake(Plan plan, Take take) async {
  final cleanup = Cleanup();
  final ext = plan.platform == 'ios-sim' ? 'mov' : 'mkv';
  final file = '${plan.outDir}/take_${take.n}.$ext';
  Recorder? recorder;
  Process? app;
  Cdp? cdp;
  final env = {...Platform.environment};
  String? audioSource;
  Display? display;
  try {
    // ---- where the picture and the sound come from
    if (plan.platform == 'web' || plan.platform == 'linux') {
      if (!Platform.isLinux) fail('web/linux capture is implemented for Linux hosts; on macOS/Windows record the screen yourself and pass the file', code: 6);
      final virtual = useVirtualDisplay(plan.displayMode, plan.playMode);
      if (virtual) {
        display = await startXvfb(plan.width!, plan.height!, cleanup);
      } else {
        display = Display(Platform.environment['DISPLAY'] ?? ':0', false, plan.width!, plan.height!);
      }
      env['DISPLAY'] = display.name;
      if (display.virtual) {
        env.remove('WAYLAND_DISPLAY');
        env['XDG_SESSION_TYPE'] = 'x11';
      } else {
        final why = await screenUnavailable();
        if (why != null) {
          take.error = 'cannot record on screen: $why, and a window there renders at ~1 fps. Unlock the screen, '
              'or record unattended takes on the virtual display (--display virtual)';
          take.errorCode = 6;
          return;
        }
      }
      if (plan.platform == 'linux') env['GDK_BACKEND'] = 'x11';
      final wantIsolated = plan.audioMode == 'isolated' || (plan.audioMode == 'auto' && plan.playMode != 'human' && plan.playMode != 'replay-record');
      if (plan.audioMode != 'none') {
        if (wantIsolated) {
          final sink = await startIsolatedSink(cleanup);
          if (sink != null) {
            env['PULSE_SINK'] = sink;
            audioSource = '$sink.monitor';
          } else {
            take.warnings.add('could not create an isolated audio sink; recording the default output (other apps are audible)');
          }
        }
        audioSource ??= '@DEFAULT_MONITOR@';
      }
    }

    // ---- launch
    String? replayPath;
    if (plan.playMode == 'replay') {
      final r = plan.replayIn ?? fail('--replay FILE is required for play mode replay', code: 2);
      if (!File(r).existsSync()) fail('replay file not found: $r', code: 2);
      if (plan.platform == 'android') {
        final id = plan.appId ?? fail('--app-id is required to push a replay to Android', code: 2);
        replayPath = '/sdcard/Android/data/$id/files/g2s_replay.json';
        final push = await runCmd(tool('adb')!, ['-s', plan.device, 'push', r, replayPath], timeout: const Duration(seconds: 30));
        if (!push.ok) take.warnings.add('adb push of the replay failed: ${push.stderr.trim()}');
      } else if (plan.platform != 'web') {
        replayPath = File(r).absolute.path;
      }
    }

    final t0 = nowS;
    if (plan.platform == 'web') {
      final chrome = tool('chrome') ?? fail('Chrome not found (${installHint('chrome')})', code: 6);
      final profile = Directory('${plan.outDir}/.chrome_profile_${take.n}');
      if (profile.existsSync()) profile.deleteSync(recursive: true);
      profile.createSync(recursive: true);
      cleanup.add('Chrome profile', () async {
        // Chrome's helpers can still write for a moment after it exits.
        for (var i = 0; i < 10 && profile.existsSync(); i++) {
          try {
            profile.deleteSync(recursive: true);
          } on FileSystemException {
            await Future<void>.delayed(const Duration(milliseconds: 300));
          }
        }
      });
      final q = 'capture_level=${plan.level}&capture_seed=${take.seed}&capture_play_mode=${plan.playMode}&capture_hold_ms=${plan.holdMs}';
      final url = 'http://127.0.0.1:${plan.server!.port}/?$q';
      final css = plan.orientation == 'portrait' ? display!.width / 412 : display!.height / 412;
      final cls = 'g2s-capture-$pid-${take.n}';
      final chromeArgs = [
        '--user-data-dir=${profile.path}', '--no-first-run', '--no-default-browser-check', '--disable-extensions',
        '--disable-features=Translate,MediaRouter,OptimizationHints', '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
        '--autoplay-policy=no-user-gesture-required', '--remote-debugging-port=0', '--class=$cls',
        '--force-device-scale-factor=${css.toStringAsFixed(3)}', '--hide-scrollbars', '--ozone-platform=x11',
        // --window-size is in CSS pixels: the display size divided by the scale factor.
        '--window-size=${(display.width / css).round()},${(display.height / css).round()}',
        if (display.virtual) ...[
          '--kiosk', '--window-position=0,0',
          // Xvfb has no GL: draw on the GPU through ANGLE/Vulkan (SwiftShader is slow and drops sprites).
          ...(Platform.environment['G2S_CHROME_GPU_FLAGS'] ??
                  '--ignore-gpu-blocklist --use-angle=vulkan --enable-features=Vulkan,DefaultANGLEVulkan,VulkanFromANGLE')
              .split(' ')
              .where((f) => f.isNotEmpty),
          'about:blank',
        ] else ...['--window-position=40,40', '--app=about:blank'],
      ];
      app = await Process.start(chrome, chromeArgs, environment: env);
      pipeLines(app.stdout, (_) {});
      pipeLines(app.stderr, (_) {});
      final chromeProc = app;
      cleanup.add('Chrome', () async {
        await cdp?.close();
        await stopProcess(chromeProc, first: ProcessSignal.sigterm, grace: const Duration(seconds: 5));
      });
      cdp = await Cdp.connect(profile.path, timeout: const Duration(seconds: 40));
      cdp.console.listen((l) => onAppLine(take, l));
      // Before the game loads: report the page's frame rate every second and the GPU it draws with,
      // to tell a slow game from a slow recorder and GPU drawing from software drawing.
      await cdp.send('Page.enable'); // without it the script below never runs on the first navigation
      await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
        'source': '(()=>{if(window.__g2s)return;window.__g2s=1;let n=0,t=performance.now();'
            'function f(){n++;const d=performance.now()-t;if(d>=1000){console.log("CAPTURE_FPS "+Math.round(n*1000/d));'
            'n=0;t=performance.now()}requestAnimationFrame(f)}requestAnimationFrame(f);'
            'try{const c=document.createElement("canvas");const g=c.getContext("webgl2")||c.getContext("webgl");'
            'const e=g&&g.getExtension("WEBGL_debug_renderer_info");'
            'console.log("CAPTURE_GPU "+(g?(e?g.getParameter(e.UNMASKED_RENDERER_WEBGL):g.getParameter(g.RENDERER)):"no WebGL"))}'
            'catch(x){console.log("CAPTURE_GPU error "+x)}})()',
      });
      await cdp.send('Page.navigate', {'url': url});
      unawaited(app.exitCode.then((_) {
        if (!take.appExited.isCompleted) take.appExited.complete();
      }));
    } else if (plan.playMode == 'script') {
      final args = [
        'drive', '--driver=test_driver/integration_test.dart', '--target=integration_test/capture_test.dart',
        '-d', plan.device, '--${plan.buildMode}', ...dartDefines(plan, take, replayPath: replayPath),
      ];
      app = await Process.start('flutter', args, workingDirectory: plan.project, environment: env, runInShell: Platform.isWindows);
    } else {
      final args = [
        'run', '-d', plan.device, '--${plan.buildMode}', '-t', plan.target, ...dartDefines(plan, take, replayPath: replayPath),
      ];
      app = await Process.start('flutter', args, workingDirectory: plan.project, environment: env, runInShell: Platform.isWindows);
    }
    if (plan.platform != 'web') {
      final flutterProc = app;
      pipeLines(flutterProc.stdout, (l) => onAppLine(take, l));
      pipeLines(flutterProc.stderr, (l) => onAppLine(take, l));
      unawaited(flutterProc.exitCode.then((_) {
        if (!take.appExited.isCompleted) take.appExited.complete();
      }));
      cleanup.add('flutter ${plan.playMode == 'script' ? 'drive' : 'run'}', () async {
        await stopProcess(flutterProc, quitLine: 'q', first: ProcessSignal.sigterm, grace: const Duration(seconds: 10));
        if (plan.platform == 'android' && plan.appId != null && tool('adb') != null) {
          await runCmd(tool('adb')!, ['-s', plan.device, 'shell', 'am', 'force-stop', plan.appId!], timeout: const Duration(seconds: 15));
        }
        if (plan.platform == 'ios-sim' && plan.appId != null) {
          await runCmd('xcrun', ['simctl', 'terminate', plan.device, plan.appId!], timeout: const Duration(seconds: 15));
        }
      });
    }
    info('take ${take.n}: launching on ${plan.platform} ${plan.device} (${plan.buildMode}, seed ${take.seed}) — waiting for CAPTURE_READY (up to ${plan.bootTimeout}s; a first build is slow)');

    // ---- READY → start the recorder
    final bootDeadline = Duration(seconds: plan.bootTimeout);
    final first = await Future.any([
      take.ready.future.then((_) => 'ready'),
      take.appExited.future.then((_) => 'exited'),
    ]).timeout(bootDeadline, onTimeout: () => 'timeout');
    if (first != 'ready') {
      take.error ??= first == 'exited'
          ? 'the app/build exited before CAPTURE_READY — see the log tail'
          : 'no CAPTURE_READY within ${plan.bootTimeout}s (build stuck, or main_capture.dart never prints it)';
      take.errorCode = 7;
      return;
    }
    info('take ${take.n}: app ready after ${fmtS(nowS - t0)}s — recording');
    switch (plan.platform) {
      case 'android':
        recorder = await startScrcpy(take, plan.device, file, audio: expectsAudio(plan), version: plan.scrcpyVersion);
      case 'ios-sim':
        recorder = await startSimctl(take, plan.device, file);
      case 'web':
      case 'linux':
        String? windowId;
        if (!display!.virtual || plan.platform == 'linux') {
          final cls = plan.platform == 'web' ? 'g2s-capture-$pid-${take.n}' : null;
          for (var i = 0; i < 40 && windowId == null; i++) {
            final w = await findWindow(display.name, wmClass: cls, title: plan.platform == 'linux' ? plan.windowTitle : null);
            windowId = w?.$1;
            if (windowId == null) await Future<void>.delayed(const Duration(milliseconds: 250));
          }
          if (windowId == null) {
            take.error = 'could not find the game window on ${display.name}${plan.platform == 'linux' ? ' (pass --window-title)' : ''}';
            take.errorCode = 7;
            return;
          }
        }
        recorder = await startFfmpegX11(take, display, file, windowId: windowId, audioSource: audioSource);
      default:
        recorder = await startFfmpegDesktop(take, file, windowTitle: plan.windowTitle);
    }
    final rec = recorder;
    take.recorder = rec.description;
    // SIGINT makes ffmpeg, scrcpy and simctl finish the file cleanly.
    cleanup.add('recorder', () async {
      await rec.stop();
      final w = await rec.finish(take.recStartHost);
      if (w != null) take.warnings.add(w);
    });
    await take.recStarted.future.timeout(const Duration(seconds: 20), onTimeout: () {
      throw TimeoutException('the recorder did not start within 20s');
    });
    if (plan.playMode == 'human' || plan.playMode == 'replay-record') {
      info('take ${take.n}: RECORDING — play level ${plan.level} on the device after the countdown');
    }

    // ---- LEVEL_START → record duration + tail
    final started = await Future.any([
      take.levelStart.future.then((_) => 'start'),
      take.appExited.future.then((_) => 'exited'),
    ]).timeout(Duration(seconds: plan.startTimeout), onTimeout: () => 'timeout');
    if (started != 'start') {
      if (started == 'timeout' && plan.playMode == 'human' && take.readyHost != null) {
        // No hook in the game: assume the level starts when the hold ends.
        take.levelStartHost = take.readyHost! + plan.holdMs / 1000;
        take.levelStartSource = 'ready + hold (no CAPTURE_LEVEL_START)';
        take.warnings.add('no CAPTURE_LEVEL_START: cut estimated from CAPTURE_READY + hold');
      } else {
        take.error = started == 'exited'
            ? 'the app exited before CAPTURE_LEVEL_START'
            : 'level ${plan.level} never printed CAPTURE_LEVEL_START within ${plan.startTimeout}s';
        take.errorCode = 8;
        return;
      }
    }
    if (take.recStartHost != null && take.levelStartHost! < take.recStartHost!) {
      take.warnings.add('the level started ${fmtS(take.recStartHost! - take.levelStartHost!)}s before the recorder: raise --hold-ms');
    }
    final until = take.levelStartHost! + plan.duration + plan.tail;
    while (nowS < until) {
      if (take.appExited.isCompleted) {
        take.warnings.add('the app exited during the take, ${fmtS(nowS - take.levelStartHost!)}s after the level start');
        break;
      }
      await Future<void>.delayed(const Duration(milliseconds: 200));
    }
  } on Object catch (e) {
    take.error ??= '$e';
  } finally {
    await cleanup.run();
    take.addLog('— take ended ${DateTime.now().toIso8601String()}');
  }
}

Map<String, Object?> takeJson(Plan plan, Take take, String file, String recorder) {
  double? rel(double? host) => host == null || take.recStartHost == null ? null : double.parse((host - take.recStartHost!).toStringAsFixed(3));
  return {
    'take': take.n,
    'ok': take.error == null && File(file).existsSync(),
    'file': File(file).existsSync() ? File(file).absolute.path : null,
    'project': plan.project,
    'platform': plan.platform,
    'device': plan.device,
    'build_mode': plan.buildMode,
    'play_mode': plan.playMode,
    'level': plan.level,
    'seed': take.seed,
    'duration_target_s': plan.duration,
    'recorder': recorder,
    'audio_expected': expectsAudio(plan),
    'ready_s': rel(take.readyHost),
    'level_start_s': rel(take.levelStartHost),
    'level_start_source': take.levelStartSource,
    'level_end_s': rel(take.levelEndHost),
    'events': [
      for (final e in take.events)
        if (rel(e['host'] as double) != null) {'t': rel(e['host'] as double), 'label': e['label']},
    ],
    if (take.gpu != null) 'webgl_renderer': take.gpu,
    if (take.browserFps.isNotEmpty) 'browser_fps': {
      'min': take.browserFps.reduce(math.min),
      'median': (List<int>.of(take.browserFps)..sort())[take.browserFps.length ~/ 2],
    },
    'warnings': take.warnings.toSet().toList(),
    if (take.error != null) 'error': take.error,
    'log': '${plan.outDir}/take_${take.n}.log',
    'recorded_at': DateTime.now().toIso8601String(),
  };
}

Future<void> cmdRecord(Args args) async {
  final plan = Plan()
    ..project = Directory(args.require('project')).absolute.path
    ..platform = args.require('platform')
    ..device = args.require('device')
    ..level = int.tryParse(args.require('level')) ?? fail('--level must be a number', code: 2)
    ..duration = args.number('duration', 20)
    ..outDir = Directory(args.require('out')).absolute.path
    ..playMode = args.str('play-mode', 'human')
    ..target = args.str('target', 'lib/main_capture.dart')
    ..appId = args['app-id']
    ..tail = args.number('tail', 2)
    ..bootTimeout = args.integer('boot-timeout', 900)
    ..startTimeout = args.integer('start-timeout', 120)
    ..audioMode = args.str('audio', 'auto')
    ..displayMode = args.str('display', 'auto')
    ..orientation = args.str('orientation', 'portrait')
    ..replayIn = args['replay']
    ..replayOut = args['replay-out']
    ..windowTitle = args['window-title']
    ..dnd = args.flag('dnd', fallback: true)
    ..gameAudio = args.str('game-audio', 'yes') != 'no';
  plan.holdMs = args.integer('hold-ms', plan.playMode == 'human' || plan.playMode == 'replay-record' ? 5000 : 3000);
  const modes = {'bot', 'replay', 'replay-record', 'script', 'human'};
  if (!modes.contains(plan.playMode)) fail('--play-mode must be one of ${modes.join(', ')}', code: 2);
  for (final kv in args.str('defines', '').split(',').where((s) => s.contains('='))) {
    final i = kv.indexOf('=');
    plan.defines[kv.substring(0, i).trim()] = kv.substring(i + 1).trim();
  }
  if (!File('${plan.project}/pubspec.yaml').existsSync()) fail('${plan.project} is not a Flutter project', code: 2);
  if (plan.playMode == 'script') {
    for (final f in ['integration_test/capture_test.dart', 'test_driver/integration_test.dart']) {
      if (!File('${plan.project}/$f').existsSync()) fail('play mode script needs $f (see references/flutter_capture.md § Script)', code: 2);
    }
  } else if (!File('${plan.project}/${plan.target}').existsSync()) {
    fail('${plan.target} not found: set up the capture entry first (references/flutter_capture.md)', code: 2);
  }
  Directory(plan.outDir).createSync(recursive: true);
  final size = RegExp(r'^(\d+)x(\d+)$').firstMatch(args.str('size', ''));
  final portrait = plan.orientation == 'portrait';

  // Device facts and the build mode.
  final devs = await flutterDevices();
  final dev = devs.where((d) => d.id == plan.device).toList();
  if (dev.isEmpty) {
    final ranked = await rankDevices(plan.project);
    stdout.writeln(prettyJson({'error': 'device ${plan.device} is not connected', ...ranked}));
    exit(4);
  }
  plan.emulator = dev.first.emulator;
  plan.apiLevel = dev.first.apiLevel;
  if (plan.platform == 'android') {
    plan.scrcpyVersion = await scrcpyVersion();
    if (plan.scrcpyVersion == null) fail('scrcpy not found (${installHint('scrcpy')})', code: 6);
  }
  final bm = args.str('build-mode', 'auto');
  plan.buildMode = bm != 'auto'
      ? bm
      : switch (plan.platform) {
          'ios-sim' => 'debug',
          'web' => 'release',
          'android' => dev.first.targetPlatform == 'android-x86' ? 'debug' : 'profile',
          _ => 'profile',
        };
  if (plan.platform == 'ios-sim' && plan.buildMode != 'debug') {
    plan.buildMode = 'debug';
    info('iOS simulator runs debug builds only: using --debug');
  }
  if (plan.platform == 'web' || plan.platform == 'linux') {
    if (tool('ffmpeg') == null) fail('ffmpeg not found (${installHint('ffmpeg')})', code: 6);
    final rootH = int.tryParse(RegExp(r'Height:\s+(\d+)').firstMatch((await runCmd('xwininfo', ['-root'], timeout: const Duration(seconds: 5))).stdout)?.group(1) ?? '') ?? 1080;
    final virtual = useVirtualDisplay(plan.displayMode, plan.playMode);
    if (size != null) {
      plan.width = int.parse(size.group(1)!);
      plan.height = int.parse(size.group(2)!);
    } else if (virtual) {
      plan.width = portrait ? 1080 : 1920;
      plan.height = portrait ? 1920 : 1080;
    } else {
      // A window that fits the monitor (panels and title bar take ~80 px).
      final h = portrait ? rootH - 80 : ((rootH - 80) * 9 / 16).round();
      plan.height = even(h);
      plan.width = even(portrait ? h * 9 / 16 : h * 16 / 9);
    }
  }

  if (args.flag('dry-run')) {
    stdout.writeln(prettyJson({
      'dry_run': true,
      'platform': plan.platform,
      'device': plan.device,
      'build_mode': plan.buildMode,
      'play_mode': plan.playMode,
      'defines': dartDefines(plan, Take(1, args.integer('seed', 42))),
      'size': plan.width == null ? null : '${plan.width}x${plan.height}',
      'audio_expected': expectsAudio(plan),
    }));
    return;
  }

  // Ctrl+C / kill: stop everything, put settings back.
  var interrupted = false;
  for (final sig in [ProcessSignal.sigint, if (!Platform.isWindows) ProcessSignal.sigterm]) {
    sig.watch().listen((_) async {
      if (interrupted) return;
      interrupted = true;
      info('interrupted: cleaning up');
      await globalCleanup.run();
      exit(130);
    });
  }

  try {
    if (plan.platform == 'android') await androidPrepare(plan.device, dnd: plan.dnd, cleanup: globalCleanup);
    if ((plan.platform == 'linux' || plan.platform == 'web') && plan.dnd && !useVirtualDisplay(plan.displayMode, plan.playMode)) {
      await linuxDnd(globalCleanup);
    }
    if (plan.platform == 'web') {
      final out = '${plan.outDir}/web_build';
      info('building web (${plan.buildMode}) → $out');
      final b = await runCmd('flutter', [
        'build', 'web', '--${plan.buildMode}', '-t', plan.target, '--no-web-resources-cdn', '-o', out,
        ...dartDefines(plan, Take(0, args.integer('seed', 42))),
      ], cwd: plan.project, timeout: Duration(seconds: plan.bootTimeout));
      if (!b.ok) {
        final tail = (b.stdout + b.stderr).trim().split('\n');
        stdout.writeln(prettyJson({'ok': false, 'error': 'flutter build web failed${b.timedOut ? ' (timeout)' : ''}', 'log_tail': tail.skip(math.max(0, tail.length - 25)).toList()}));
        exit(7);
      }
      plan.webBuildDir = out;
      plan.server = await StaticServer.start(out, extra: {
        if (plan.replayIn != null) '/assets/g2s_replay.json': File(plan.replayIn!).absolute.path,
      });
      final server = plan.server!;
      // The build is only needed while recording (tens of MB in the run folder otherwise).
      globalCleanup.add('web build', () async {
        if (Directory(out).existsSync()) Directory(out).deleteSync(recursive: true);
      });
      globalCleanup.add('web server', () async => server.close());
    }

    final takes = args.integer('takes', 1).clamp(1, 5);
    final seed = args.integer('seed', 42);
    final results = <Map<String, Object?>>[];
    for (var i = 1; i <= takes; i++) {
      final take = Take(i, args.flag('vary-seed') ? seed + i - 1 : seed);
      await runTake(plan, take);
      final ext = plan.platform == 'ios-sim' ? 'mov' : 'mkv';
      final file = '${plan.outDir}/take_$i.$ext';
      final j = takeJson(plan, take, file, take.recorder);
      writeText('${plan.outDir}/take_$i.log', take.log.join('\n'));
      writeText('${plan.outDir}/take_$i.json', prettyJson(j));
      if (plan.playMode == 'replay-record' && take.replay.isNotEmpty) {
        final out = plan.replayOut ?? '${plan.project}/social/replays/level_${plan.level}.json';
        writeText(out, prettyJson({
          'level': plan.level,
          'seed': take.seed,
          'recorded_at': DateTime.now().toIso8601String(),
          'platform': plan.platform,
          'meta': take.replayMeta,
          'events': take.replay,
        }));
        j['replay_file'] = out;
        writeText('${plan.outDir}/take_$i.json', prettyJson(j));
      }
      results.add(j);
      final tail = take.log.skip(math.max(0, take.log.length - 15)).toList();
      info('take $i: ${j['ok'] == true ? 'recorded' : 'FAILED — ${take.error}'}');
      if (j['ok'] != true) {
        stdout.writeln(prettyJson({'ok': false, 'takes': results, 'log_tail': tail}));
        await globalCleanup.run();
        exit(take.errorCode);
      }
    }
    stdout.writeln(prettyJson({'ok': true, 'takes': results.map((r) => '${plan.outDir}/take_${r['take']}.json').toList(), 'summary': results}));
  } finally {
    await globalCleanup.run();
  }
}

int even(num v) {
  final r = v.round();
  return r.isEven ? r : r - 1;
}

Future<void> main(List<String> argv) async {
  if (argv.isEmpty) {
    stderr.writeln('usage: dart launch_and_record.dart devices|record …  (see the header)');
    exit(2);
  }
  final args = Args.parse(argv.sublist(1), flags: {'json', 'vary-seed', 'dry-run', 'dnd'});
  switch (argv.first) {
    case 'devices':
      await cmdDevices(args);
    case 'record':
      await cmdRecord(args);
    default:
      stderr.writeln('unknown command ${argv.first}');
      exit(2);
  }
  exit(0);
}
