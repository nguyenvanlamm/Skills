// Shared helpers for the gameplay-to-social scripts.
//
// Only dart: libraries are used, so every script runs with `dart <skill>/scripts/<name>.dart`
// from any directory, without `pub get`.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// The skill's root folder (the parent of `scripts/`). Kept as the path the script was started
/// with, so a symlinked skill (`~/.claude/skills/gameplay-to-social`) still finds its references.
Directory get skillDir => File.fromUri(Platform.script).parent.parent;

String get referencesDir => '${skillDir.path}/references';
String get assetsDir => '${skillDir.path}/assets';

/// `--key value`, `--key=value`, `--flag`, `--no-flag` and positionals.
class Args {
  Args._(this.options, this.positional);

  final Map<String, String> options;
  final List<String> positional;

  /// [flags] are options that never take a value (`--json`, `--dry-run`).
  static Args parse(List<String> argv, {Set<String> flags = const {}}) {
    final options = <String, String>{};
    final positional = <String>[];
    for (var i = 0; i < argv.length; i++) {
      final a = argv[i];
      if (a == '--') {
        positional.addAll(argv.skip(i + 1));
        break;
      }
      if (!a.startsWith('--')) {
        positional.add(a);
        continue;
      }
      final body = a.substring(2);
      final eq = body.indexOf('=');
      if (eq >= 0) {
        options[body.substring(0, eq)] = body.substring(eq + 1);
      } else if (flags.contains(body)) {
        options[body] = 'true';
      } else if (body.startsWith('no-') && flags.contains(body.substring(3))) {
        options[body.substring(3)] = 'false';
      } else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
        options[body] = argv[++i];
      } else {
        options[body] = 'true';
      }
    }
    return Args._(options, positional);
  }

  String? operator [](String key) => options[key];
  String str(String key, String fallback) => options[key] ?? fallback;
  bool flag(String key, {bool fallback = false}) {
    final v = options[key];
    if (v == null) return fallback;
    return v != 'false' && v != '0' && v != 'no';
  }

  int integer(String key, int fallback) => int.tryParse(options[key] ?? '') ?? fallback;
  double number(String key, double fallback) => double.tryParse(options[key] ?? '') ?? fallback;

  String require(String key) {
    final v = options[key];
    if (v == null || v.isEmpty) fail('missing --$key', code: 2);
    return v;
  }
}

/// Prints [message] to stderr and exits with [code].
Never fail(String message, {int code = 1}) {
  stderr.writeln('error: $message');
  exit(code);
}

void info(String message) => stderr.writeln(message);

const JsonEncoder _pretty = JsonEncoder.withIndent('  ');
String prettyJson(Object? value) => _pretty.convert(value);

/// Monotonic seconds since this script started; all timing in the scripts uses it.
final Stopwatch clock = Stopwatch()..start();
double get nowS => clock.elapsedMicroseconds / 1e6;

class CmdResult {
  CmdResult(this.exitCode, this.stdout, this.stderr, {this.timedOut = false});

  final int exitCode;
  final String stdout;
  final String stderr;
  final bool timedOut;

  bool get ok => exitCode == 0 && !timedOut;
}

const Utf8Decoder _utf8 = Utf8Decoder(allowMalformed: true);

/// Runs a command to completion, killing it after [timeout]. Never throws for a missing binary:
/// that comes back as exit code 127.
Future<CmdResult> runCmd(
  String exe,
  List<String> args, {
  Duration timeout = const Duration(seconds: 60),
  String? cwd,
  Map<String, String>? env,
  String? stdinText,
}) async {
  Process p;
  try {
    p = await Process.start(exe, args,
        workingDirectory: cwd, environment: env, runInShell: Platform.isWindows);
  } on ProcessException catch (e) {
    return CmdResult(127, '', '${e.message}: $exe');
  }
  final out = StringBuffer();
  final err = StringBuffer();
  final so = p.stdout.transform(_utf8).listen(out.write);
  final se = p.stderr.transform(_utf8).listen(err.write);
  if (stdinText != null) {
    p.stdin.write(stdinText);
  }
  unawaited(p.stdin.close().catchError((_) {}));
  var timedOut = false;
  final code = await p.exitCode.timeout(timeout, onTimeout: () async {
    timedOut = true;
    p.kill(ProcessSignal.sigterm);
    return p.exitCode.timeout(const Duration(seconds: 5), onTimeout: () {
      p.kill(ProcessSignal.sigkill);
      return -9;
    });
  });
  // A background child (git's fsmonitor, a daemon) can inherit the pipes and keep them open long
  // after the command exited: drain briefly, then stop listening.
  await Future.wait([so.asFuture<void>(), se.asFuture<void>()]).timeout(
    const Duration(milliseconds: 500),
    onTimeout: () => const [],
  );
  await so.cancel();
  await se.cancel();
  return CmdResult(code, out.toString(), err.toString(), timedOut: timedOut);
}

String get home => Platform.environment['HOME'] ?? Platform.environment['USERPROFILE'] ?? '';

/// The Android SDK root, from the usual variables and default install folders.
String? androidSdk() {
  final env = Platform.environment;
  for (final c in [
    env['ANDROID_HOME'],
    env['ANDROID_SDK_ROOT'],
    '$home/Android/Sdk',
    '$home/Library/Android/sdk',
    if (env['LOCALAPPDATA'] != null) '${env['LOCALAPPDATA']}\\Android\\Sdk',
  ]) {
    if (c != null && c.isNotEmpty && Directory(c).existsSync()) return c;
  }
  return null;
}

/// Finds an executable on PATH, then in [extra] candidate paths. Null when absent.
String? which(String name, {List<String> extra = const []}) {
  final sep = Platform.isWindows ? ';' : ':';
  final exts = Platform.isWindows
      ? (Platform.environment['PATHEXT'] ?? '.EXE;.BAT;.CMD').toLowerCase().split(';')
      : [''];
  for (final dir in (Platform.environment['PATH'] ?? '').split(sep)) {
    if (dir.isEmpty) continue;
    for (final ext in exts) {
      final f = File('$dir${Platform.pathSeparator}$name$ext');
      if (f.existsSync()) return f.path;
    }
  }
  for (final c in extra) {
    if (File(c).existsSync()) return c;
  }
  return null;
}

/// Known tools and where they hide when they are not on PATH.
String? tool(String name) {
  final sdk = androidSdk();
  final brew = ['/opt/homebrew/bin/$name', '/usr/local/bin/$name', '/snap/bin/$name'];
  switch (name) {
    case 'adb':
      return which('adb', extra: [if (sdk != null) '$sdk/platform-tools/adb', ...brew]);
    case 'emulator':
      return which('emulator', extra: [if (sdk != null) '$sdk/emulator/emulator']);
    case 'avdmanager':
      return which('avdmanager', extra: [
        if (sdk != null) '$sdk/cmdline-tools/latest/bin/avdmanager',
        if (sdk != null) '$sdk/tools/bin/avdmanager',
      ]);
    case 'sdkmanager':
      return which('sdkmanager', extra: [
        if (sdk != null) '$sdk/cmdline-tools/latest/bin/sdkmanager',
        if (sdk != null) '$sdk/tools/bin/sdkmanager',
      ]);
    case 'chrome':
      final env = Platform.environment['CHROME_EXECUTABLE'];
      if (env != null && File(env).existsSync()) return env;
      for (final n in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome']) {
        final w = which(n);
        if (w != null) return w;
      }
      for (final c in [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
      ]) {
        if (File(c).existsSync()) return c;
      }
      // Playwright's own Chromium, if Playwright is installed.
      final pw = Directory('$home/.cache/ms-playwright');
      if (pw.existsSync()) {
        final hits = pw
            .listSync()
            .whereType<Directory>()
            .where((d) => d.path.split('/').last.startsWith('chromium-'))
            .map((d) => '${d.path}/chrome-linux/chrome')
            .where((p) => File(p).existsSync())
            .toList()
          ..sort();
        if (hits.isNotEmpty) return hits.last;
      }
      return null;
    default:
      return which(name, extra: brew);
  }
}

/// A local timestamp like 20261103-1720 for output folder names.
String stamp([DateTime? t]) {
  final d = t ?? DateTime.now();
  String two(int v) => v.toString().padLeft(2, '0');
  return '${d.year}${two(d.month)}${two(d.day)}-${two(d.hour)}${two(d.minute)}';
}

String fmtS(double s) => s.toStringAsFixed(2);

/// Writes [content] atomically enough for our purposes (temp file + rename).
void writeText(String path, String content) {
  final f = File(path);
  f.parent.createSync(recursive: true);
  final tmp = File('$path.tmp');
  tmp.writeAsStringSync(content);
  tmp.renameSync(path);
}

Object? readJson(String path) => jsonDecode(File(path).readAsStringSync());
