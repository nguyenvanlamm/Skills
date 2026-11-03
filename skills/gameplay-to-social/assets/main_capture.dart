// Capture entry point for the gameplay-to-social skill — template.
//
// Copy to lib/main_capture.dart, then fill in the four `GAME` sections. Production never imports
// this file: lib/main.dart stays the app's entry point, and none of this ships unless a build is
// made with `-t lib/main_capture.dart`.
//
//   flutter run -t lib/main_capture.dart --profile \
//     --dart-define=CAPTURE_MODE=true --dart-define=CAPTURE_LEVEL=10 \
//     --dart-define=CAPTURE_SEED=42 --dart-define=CAPTURE_PLAY_MODE=bot
//
// What it does for the recorder (scripts/launch_and_record.dart):
//   - prints CAPTURE_READY on its first frame, holds a neutral screen (a 3-2-1 countdown in human
//     mode) for CAPTURE_HOLD_MS so recording is already running, then opens the level;
//   - prints CAPTURE_LEVEL_START once when the level is playable (after its first frame, or from a
//     hook in the game when [kGameSignalsLevelStart] is true): the clip is cut from that line;
//   - replay-record mode logs every touch (CAPTURE_REPLAY …) for social/replays/level_<N>.json;
//     replay mode plays such a file back through the real gesture system;
//   - hides the system bars and keeps the DEBUG ribbon off even in debug builds.
//
// On web the recorder builds once and passes level/seed/mode in the URL, so several takes need
// one build.
//
// ignore_for_file: avoid_print

import 'dart:async';
import 'dart:convert';
import 'dart:io' show File;

import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';

// GAME 1 ── imports: the game's level screen, level data and the services it needs.
// import 'package:my_game/ui/game_screen.dart';

// ─────────────────────────────────────────────────────────────── capture settings

const bool kCaptureMode = bool.fromEnvironment('CAPTURE_MODE');
const int _defineLevel = int.fromEnvironment('CAPTURE_LEVEL', defaultValue: 1);
const int _defineSeed = int.fromEnvironment('CAPTURE_SEED', defaultValue: 42);
const String _defineMode = String.fromEnvironment(
  'CAPTURE_PLAY_MODE',
  defaultValue: 'human',
);
const int _defineHoldMs = int.fromEnvironment(
  'CAPTURE_HOLD_MS',
  defaultValue: 3000,
);
const String kCaptureReplayPath = String.fromEnvironment('CAPTURE_REPLAY_PATH');

String? _query(String key) => kIsWeb ? Uri.base.queryParameters[key] : null;

/// Level number as the player sees it (1-based).
final int captureLevel =
    int.tryParse(_query('capture_level') ?? '') ?? _defineLevel;
final int captureSeed =
    int.tryParse(_query('capture_seed') ?? '') ?? _defineSeed;

/// bot | replay | replay-record | script | human
final String capturePlayMode = _query('capture_play_mode') ?? _defineMode;
final int captureHoldMs =
    int.tryParse(_query('capture_hold_ms') ?? '') ?? _defineHoldMs;

bool get _humanPlays =>
    capturePlayMode == 'human' || capturePlayMode == 'replay-record';

// GAME 2 ── when does the level become playable?
/// True when a hook in the game prints `CAPTURE_LEVEL_START` itself, at the moment the level is
/// playable (after loading, after an intro animation). The hook is one guarded line:
///   if (const bool.fromEnvironment('CAPTURE_MODE')) print('CAPTURE_LEVEL_START');
/// False: this file prints it after the level's first frame plus [kLevelStartDelayMs].
const bool kGameSignalsLevelStart = false;
const int kLevelStartDelayMs = 0;

/// When a bot finishes the level before the clip is long enough, keep the end card on screen for
/// [kEndCardMs], then open the next level so the take still has play in it (the recorder logs the
/// switch as `CAPTURE_EVENT next level N`). Needs [captureLevelLength]; never used for replays.
const bool kContinueToNextLevel = true;
const int kEndCardMs = 1500;

void captureLog(String line) => print(line);

/// Marks a moment worth a look in the clip (combo, near miss, boss, win). Safe to call from a
/// guarded hook in the game: `if (const bool.fromEnvironment('CAPTURE_MODE')) captureEvent('combo x3');`
/// (or print('CAPTURE_EVENT combo x3') without importing this file).
void captureEvent(String label) => captureLog('CAPTURE_EVENT $label');

bool _levelStarted = false;
final Stopwatch _levelClock = Stopwatch();
final List<VoidCallback> _onLevelStart = [];

void markLevelStart() {
  if (_levelStarted) return;
  _levelStarted = true;
  _levelClock.start();
  captureLog('CAPTURE_LEVEL_START level=$captureLevel');
  for (final f in List.of(_onLevelStart)) {
    f();
  }
}

// ─────────────────────────────────────────────────────────────── entry

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (!kCaptureMode) {
    // Never mistaken for the app: without the define this entry only says how to run it.
    runApp(
      const Directionality(
        textDirection: TextDirection.ltr,
        child: Center(child: Text('Run with --dart-define=CAPTURE_MODE=true')),
      ),
    );
    return;
  }
  WidgetsApp.debugAllowBannerOverride =
      false; // no DEBUG ribbon, even in debug builds
  captureLog(
    'CAPTURE_BOOT level=$captureLevel seed=$captureSeed mode=$capturePlayMode',
  );
  unawaited(SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky));

  // GAME 3 ── the game's own start-up, minus what must not run while recording:
  //   • orientation exactly as lib/main.dart sets it;
  //   • randomness fixed: hand captureSeed to the game's RNG (or seed it in a guarded hook);
  //   • ads, analytics, crash reporting, review prompts, purchases, consent, push permission:
  //     skip their init or pass the game no-op fakes;
  //   • saved progress in memory only, so a capture run never changes the device's real save;
  //   • tutorials, first-run hints and daily/reward pop-ups: marked as seen / not scheduled;
  //   • Flame: debugMode = false on the game and its components, no FPS counter.
  if (!validCaptureLevel(captureLevel)) {
    captureLog('CAPTURE_ERROR level $captureLevel does not exist');
  }

  runApp(
    MaterialApp(
      debugShowCheckedModeBanner: false,
      // GAME: the game's theme, localizations and providers, as its own MaterialApp has them.
      home: CaptureHost(
        background: const Color(
          0xFF000000,
        ), // GAME: the game's background colour
        buildLevel: (context, level) =>
            buildCaptureLevel(context, level, capturePlayMode),
      ),
    ),
  );
}

// GAME 4 ── the level count, and the level screen for each play mode.
bool validCaptureLevel(int level) =>
    level >= 1; // e.g. level <= levelTable.length

Widget buildCaptureLevel(BuildContext context, int level, String mode) {
  // bot:    the game's own bot / solver / demo plays (e.g. GameScreen(level: …, demo: plan)).
  // human, replay-record, replay, script: the normal level screen; touches come from the player,
  //         the replay file or the integration test.
  throw UnimplementedError(
    'GAME 4: return the screen for level $level ($mode)',
  );
}

/// How long [level] runs in [mode], when that is known ahead (a deterministic bot or solver plan:
/// simulate it off screen). Null when unknown — then the clip simply ends where the recorder stops.
Duration? captureLevelLength(int level, String mode) => null;

// ─────────────────────────────────────────────────────────────── host: hold, countdown, level

class CaptureHost extends StatefulWidget {
  const CaptureHost({
    super.key,
    required this.buildLevel,
    this.background = const Color(0xFF000000),
  });

  final Widget Function(BuildContext context, int level) buildLevel;
  final Color background;

  @override
  State<CaptureHost> createState() => _CaptureHostState();
}

class _CaptureHostState extends State<CaptureHost> {
  bool _live = false;
  int? _count;
  int _level = captureLevel;

  @override
  void initState() {
    super.initState();
    _onLevelStart.add(_scheduleEnd);
    SchedulerBinding.instance.addPostFrameCallback((_) {
      captureLog('CAPTURE_READY');
      unawaited(_hold());
    });
  }

  /// Known level length: log the end, hold the end card, then open the next level.
  void _scheduleEnd() {
    final length = captureLevelLength(_level, capturePlayMode);
    if (length == null || capturePlayMode != 'bot') return;
    Timer(length, () {
      captureLog('CAPTURE_LEVEL_END level=$_level');
      if (!kContinueToNextLevel || !validCaptureLevel(_level + 1)) return;
      Timer(const Duration(milliseconds: kEndCardMs), () {
        if (!mounted) return;
        setState(() => _level++);
        captureEvent('next level $_level');
        SchedulerBinding.instance.addPostFrameCallback((_) => _scheduleEnd());
      });
    });
  }

  Future<void> _hold() async {
    if (_humanPlays) {
      final secs = (captureHoldMs / 1000).ceil().clamp(1, 10);
      for (var i = secs; i > 0; i--) {
        if (!mounted) return;
        setState(() => _count = i);
        await Future<void>.delayed(const Duration(seconds: 1));
      }
    } else {
      await Future<void>.delayed(Duration(milliseconds: captureHoldMs));
    }
    if (!mounted) return;
    setState(() {
      _live = true;
      _count = null;
    });
    if (!kGameSignalsLevelStart) {
      SchedulerBinding.instance.addPostFrameCallback((_) async {
        if (kLevelStartDelayMs > 0) {
          await Future<void>.delayed(
            const Duration(milliseconds: kLevelStartDelayMs),
          );
        }
        markLevelStart();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_live) {
      final level = KeyedSubtree(
        key: ValueKey(_level),
        child: widget.buildLevel(context, _level),
      );
      return switch (capturePlayMode) {
        'replay-record' => _ReplayRecorder(child: level),
        'replay' => _ReplayPlayer(child: level),
        _ => level,
      };
    }
    // Material gives the countdown a real text style (no red, underlined fallback).
    return Material(
      color: widget.background,
      child: Center(
        child: _count == null
            ? const SizedBox.shrink()
            : Text(
                '$_count',
                style: TextStyle(
                  fontSize: 120,
                  fontWeight: FontWeight.w800,
                  // Readable on any background colour.
                  color: widget.background.computeLuminance() > 0.5
                      ? const Color(0xFF000000)
                      : const Color(0xFFFFFFFF),
                ),
              ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────── replay: record

/// Logs every touch while the developer plays, relative to CAPTURE_LEVEL_START, in logical
/// pixels with the screen size, so the same take can be played back on another run.
class _ReplayRecorder extends StatefulWidget {
  const _ReplayRecorder({required this.child});

  final Widget child;

  @override
  State<_ReplayRecorder> createState() => _ReplayRecorderState();
}

class _ReplayRecorderState extends State<_ReplayRecorder> {
  @override
  void initState() {
    super.initState();
    _onLevelStart.add(_meta);
    if (_levelStarted) _meta();
  }

  void _meta() {
    final view = View.of(context);
    final size = view.physicalSize / view.devicePixelRatio;
    captureLog(
      'CAPTURE_REPLAY_META ${jsonEncode({'w': size.width, 'h': size.height, 'dpr': view.devicePixelRatio, 'level': captureLevel, 'seed': captureSeed})}',
    );
  }

  void _log(String kind, PointerEvent e) {
    if (!_levelStarted) return;
    captureLog(
      'CAPTURE_REPLAY ${jsonEncode({'t': _levelClock.elapsedMilliseconds, 'k': kind, 'p': e.pointer, 'x': double.parse(e.position.dx.toStringAsFixed(1)), 'y': double.parse(e.position.dy.toStringAsFixed(1))})}',
    );
  }

  @override
  Widget build(BuildContext context) => Listener(
    behavior: HitTestBehavior.translucent,
    onPointerDown: (e) => _log('d', e),
    onPointerMove: (e) => _log('m', e),
    onPointerUp: (e) => _log('u', e),
    onPointerCancel: (e) => _log('c', e),
    child: widget.child,
  );
}

// ─────────────────────────────────────────────────────────────── replay: play back

/// Plays `social/replays/level_<N>.json` back through GestureBinding, frame by frame, from
/// CAPTURE_LEVEL_START. Fixed seed + same level = same game, unless physics drifts with frame
/// timing (then use the bot or a script instead).
class _ReplayPlayer extends StatefulWidget {
  const _ReplayPlayer({required this.child});

  final Widget child;

  @override
  State<_ReplayPlayer> createState() => _ReplayPlayerState();
}

class _ReplayPlayerState extends State<_ReplayPlayer>
    with SingleTickerProviderStateMixin {
  List<Map<String, dynamic>> _events = [];
  Size _recorded = Size.zero;
  int _next = 0;
  final Map<int, Offset> _last = {};
  late final Ticker _ticker = createTicker(_tick);

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  Future<void> _load() async {
    try {
      final text = kIsWeb
          ? await rootBundle.loadString(
              kCaptureReplayPath.isEmpty
                  ? 'g2s_replay.json'
                  : kCaptureReplayPath,
            )
          : await File(kCaptureReplayPath).readAsString();
      final j = jsonDecode(text) as Map<String, dynamic>;
      final meta = (j['meta'] as Map?) ?? {};
      _recorded = Size(
        (meta['w'] as num?)?.toDouble() ?? 0,
        (meta['h'] as num?)?.toDouble() ?? 0,
      );
      _events = [
        for (final e in (j['events'] as List))
          (e as Map).cast<String, dynamic>(),
      ];
      captureLog('CAPTURE_EVENT replay loaded ${_events.length} events');
      if (_levelStarted) {
        _ticker.start();
      } else {
        _onLevelStart.add(_ticker.start);
      }
    } on Object catch (e) {
      captureLog('CAPTURE_ERROR replay file not readable: $e');
    }
  }

  void _tick(Duration _) {
    final now = _levelClock.elapsedMilliseconds;
    final view = View.of(context);
    final size = view.physicalSize / view.devicePixelRatio;
    final sx = _recorded.width > 0 ? size.width / _recorded.width : 1.0;
    final sy = _recorded.height > 0 ? size.height / _recorded.height : 1.0;
    while (_next < _events.length && (_events[_next]['t'] as num) <= now) {
      final e = _events[_next++];
      final id = 1000 + (e['p'] as num).toInt();
      final pos = Offset(
        (e['x'] as num).toDouble() * sx,
        (e['y'] as num).toDouble() * sy,
      );
      final ts = Duration(milliseconds: (e['t'] as num).toInt());
      final PointerEvent ev = switch (e['k']) {
        'd' => PointerDownEvent(
          viewId: view.viewId,
          pointer: id,
          position: pos,
          timeStamp: ts,
          kind: PointerDeviceKind.touch,
        ),
        'm' => PointerMoveEvent(
          viewId: view.viewId,
          pointer: id,
          position: pos,
          timeStamp: ts,
          kind: PointerDeviceKind.touch,
          delta: pos - (_last[id] ?? pos),
        ),
        'u' => PointerUpEvent(
          viewId: view.viewId,
          pointer: id,
          position: pos,
          timeStamp: ts,
          kind: PointerDeviceKind.touch,
        ),
        _ => PointerCancelEvent(
          viewId: view.viewId,
          pointer: id,
          position: pos,
          timeStamp: ts,
          kind: PointerDeviceKind.touch,
        ),
      };
      _last[id] = pos;
      GestureBinding.instance.handlePointerEvent(ev);
    }
    if (_next >= _events.length) {
      _ticker.stop();
      captureEvent('replay finished');
    }
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
