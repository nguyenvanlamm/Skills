# Sound templates

**When:** S4 step 2, while the chosen mockup is built in Flutter. A game leaves S4 with sound; `scripts/sound_check.py`
fails the S4 Verify, the S8 check before G4 and every Final report from S4 on until it has.

Why this exists: 18 of the first 25 pipeline games shipped silent. Sound was two optional-sounding lines in
`references/mockup-to-flutter.md`, no check looked for it, and the gates only look at screenshots, so nobody heard the
games before the Mac build.

## What to copy where

| From `templates/sound/` | To the game repo |
|---|---|
| `tool/gen_sfx.py` | `tool/gen_sfx.py`, then add the game's sounds |
| `lib/ui/sfx.dart` | `lib/ui/sfx.dart`, then extend `ids` and `volumes` |
| `test/sfx_template_test.dart` | `test/sfx_template_test.dart` |

In the test, replace `package:game/` with the app's package name (`name:` in pubspec.yaml). Use Edit; a background
session refuses `sed -i`. The Dart files are formatted at `page_width: 120`.

Then:

```bash
python3 tool/gen_sfx.py        # needs ffmpeg with the aac encoder; writes assets/audio/<id>.m4a (a few KB each)
```

## pubspec.yaml

```yaml
dependencies:
  audioplayers: 6.8.1

flutter:
  assets:
    - assets/audio/
```

An exact pin, the version this template was verified with (audioplayers_darwin 6.5.0, audioplayers_web 5.3.0).

## Wiring

`main()`, after the save has loaded:

```dart
// Sounds load in the background; until then, or if they cannot load, the game is simply silent.
final sfx = Sfx();
unawaited(sfx.init().catchError((Object _) {}));
runApp(GameApp(saved: saved, shop: shop, sound: sfx));
```

The app takes a `SoundSink` defaulting to `const NoSound()` (tests never build `Sfx`: it opens platform players) and
puts the scope in `MaterialApp.builder`, so pushed routes and modal sheets see it:

```dart
builder: (context, child) => SoundScope(sink: sound, enabled: () => progress.soundOn, child: child!),
```

Play with `SoundScope.play(context, 'win')`; wrap button callbacks with `withTapSound(context, onPressed)` inside the
game's button widget, so every button clicks and a disabled one stays silent.

## What each game writes itself

1. **Its sounds.** One function per event in DESIGN.md's differentiation row 7 (feedback words, sounds, signature
   effects): the player's action, each rule's visible reaction (a merge, a capture, a gust, a door), win, lose,
   button taps, purchase delivered. Built from the kit's helpers; never a sample from the reference game or a stock
   pack. Add each to `SOUNDS` and to `Sfx.ids` and `Sfx.volumes`.
2. **The event → sound mapping**, as a pure function over the rules' step events (Popcorn Pigeons:
   `soundsForStep(StepResult) → (now, mid, end)`), with a test per event kind.
3. **Timing.** The action's sound on the tap; a reaction's sound when the animation shows it (an animation listener
   at the matching `value`, not a Timer); the outcome's sound when the step's animation ends. Clear pending sounds
   on restart.
4. **The switch.** A `Sound: On` / `Sound: Off` row in Settings, saved in the progress JSON (`'sound'`, old saves
   default to on). Turning it on clicks once to confirm. Test that it toggles, persists and silences.
5. **CREDITS.** One `assets/CREDITS.md` row: the sound ids, "synthesised by `tool/gen_sfx.py`", own work.
6. **Levels.** Short transients (taps, clicks) sound quieter than their peak suggests; `saturate()` gives them body,
   and the volumes even out the rest. Measure instead of guessing:

   ```bash
   for f in build/sfx/*.wav; do echo -n "$(basename $f) "; ffmpeg -hide_banner -i $f \
     -af astats=metadata=0:measure_overall=RMS_peak -f null - 2>&1 | grep "RMS peak dB" | tail -1 | awk '{print $NF}'; done
   ```

   Frequent sounds (the action) sit a few dB under rare ones (win, lose); taps are the quietest.
7. **No music** unless DESIGN.md asks for it.

## Rules the template already keeps

- `.m4a` (AAC): AVPlayer on iOS cannot play OGG.
- `AVAudioSessionCategory.ambient`: the silent switch mutes the game and the player's own music keeps playing; no
  `UIBackgroundModes`, no microphone, no usage string.
- One player per sound, restarted from the top on each play, so sounds overlap and quick repeats are heard.
- Errors are swallowed: a sound that fails to load or play costs only that sound.
- Web builds play sound only after the first tap (browser autoplay rule); nothing to fix.

## Checks

- `python3 <skill-dir>/scripts/sound_check.py <repo>` exits 0.
- `flutter test` runs the template test and the game's own sound tests.
- Listen once in the web build (`flutter run -d chrome`) before S4's build report is written; the human hears it in
  TestFlight at S8.
