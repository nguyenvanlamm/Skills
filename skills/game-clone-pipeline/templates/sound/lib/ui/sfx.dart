import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/widgets.dart';

/// Where sound effects go: the app plays them through [Sfx]; tests record them or drop them.
abstract interface class SoundSink {
  void play(String id);
}

/// Plays nothing (the default where no player is wired, e.g. tests).
class NoSound implements SoundSink {
  const NoSound();

  @override
  void play(String id) {}
}

/// The game's own synthesised effects (`tool/gen_sfx.py` → `assets/audio/<id>.m4a`), one player each so they
/// overlap. iOS's ambient category mixes with the player's music and stays quiet with the silent switch on.
class Sfx implements SoundSink {
  Sfx() : _players = {for (final id in ids) id: AudioPlayer(playerId: 'sfx-$id')};

  /// One id per sound; keep in step with `SOUNDS` in tool/gen_sfx.py (a test checks both and the files).
  static const ids = ['step', 'tap', 'win', 'lose', 'chime'];

  /// Balanced by ear and by measured level (README: the astats one-liner). Frequent sounds sit under rare ones.
  static const volumes = {'step': 0.7, 'tap': 0.25, 'win': 0.9, 'lose': 0.35, 'chime': 0.55};

  static final audioContext = AudioContext(
    iOS: AudioContextIOS(category: AVAudioSessionCategory.ambient, options: const {}),
    android: const AudioContextAndroid(usageType: AndroidUsageType.game, audioFocus: AndroidAudioFocus.none),
  );

  final Map<String, AudioPlayer> _players;
  bool _ready = false;

  /// Loads every sound; until it finishes (or if it fails) [play] is silent.
  Future<void> init() async {
    await AudioPlayer.global.setAudioContext(audioContext);
    for (final MapEntry(key: id, value: p) in _players.entries) {
      await p.setPlayerMode(PlayerMode.lowLatency);
      await p.setReleaseMode(ReleaseMode.stop);
      await p.setSource(AssetSource('audio/$id.m4a'));
      await p.setVolume(volumes[id] ?? 0.6);
    }
    _ready = true;
  }

  @override
  void play(String id) {
    final p = _players[id];
    if (!_ready || p == null) return;
    // Restart from the top so quick repeats are not swallowed; a failure only costs the sound.
    p.stop().then((_) => p.resume()).catchError((Object _) {});
  }
}

/// Gives every route the sound player and the player's Sound switch. Put it in `MaterialApp.builder` so pushed
/// routes and modal sheets see it too.
class SoundScope extends InheritedWidget {
  const SoundScope({super.key, required this.sink, required this.enabled, required super.child});

  final SoundSink sink;

  /// Read at each play, so the Settings switch takes effect at once.
  final bool Function() enabled;

  /// Plays [id] when Sound is on; silent where there is no scope.
  static void play(BuildContext context, String id) {
    final scope = context.getInheritedWidgetOfExactType<SoundScope>();
    if (scope != null && scope.enabled()) scope.sink.play(id);
  }

  @override
  bool updateShouldNotify(SoundScope oldWidget) => sink != oldWidget.sink;
}

/// Wraps [action] so a press plays the soft click first; null stays null (a disabled control makes no sound).
VoidCallback? withTapSound(BuildContext context, VoidCallback? action) => action == null
    ? null
    : () {
        SoundScope.play(context, 'tap');
        action();
      };
