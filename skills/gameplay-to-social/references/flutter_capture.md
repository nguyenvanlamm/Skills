# Flutter capture

Read at first-run setup (§1–3) and when recording (§4–8). For the reasons behind the defaults,
see §8 (what went wrong before).

## 1. Reading a project

`detect_project.dart` prints leads with file:line. Confirm each one in the code before it goes
into `config.yaml`:

- **Level loading and count.** Follow the leads to the place where the game turns a number into
  a playable level. That can be a screen constructor (`GameScreen(level: …)`), a router call, a
  `loadLevel(n)`, or a JSON asset under `assets/levels/`. Note:
  - whether the user-facing numbering starts at 0 or at 1;
  - how levels are grouped (world/chapter "1-10" against a flat 10);
  - the total (`levelCount`, `levels.length`, the number of asset files).
- **A bot.** Look for:
  - `lib/sim/`, `*bot*.dart`, `solver.dart`, `autoplay.dart`, `pilots.dart`;
  - stored solutions (`level.plan`, `level_solutions.dart`);
  - a `demo:` or `autoplay:` parameter on the level screen;
  - self-playing entries in `tool/` (`record_main.dart`, `ad_main.dart`).

  A solver that only returns moves still makes a bot: main_capture can feed the moves to the
  game at human pace.
- **How long the bot takes.** Time it with a throwaway script that imports the game's package
  and runs the plan off screen, the same loop `captureLevelLength` uses. Put it outside the
  project and run it with the project's package config:
  ```
  dart --packages=<project>/.dart_tool/package_config.json /tmp/bot_length.dart
  ```
  The script plays the level like the capture entry does, for example
  `while (!sim.isOver) { auto.drive(sim); sim.tick(); }`, then prints `sim.time`.
- **What to switch off while recording.**
  - Ads: banner, interstitial, rewarded, app-open.
  - Analytics and crash reporting.
  - Review prompts (`in_app_review`, a review policy).
  - Purchase sheets and the store backend.
  - Consent and ATT dialogs, push-permission prompts.
  - Tutorials, first-run hints, daily-reward and chest pop-ups.
  - Debug overlays (Flame `debugMode`, FPS counters, `showPerformanceOverlay`).
  - Prefer the game's own seams: a services object, a fake backend used by tests, a flag.
- **Randomness.** Find every `Random(` and seed parameter. The capture entry passes
  `captureSeed` in, so a take can be repeated.
- **Ids.** Note the Android `applicationId` (for `am force-stop`) and the iOS bundle id (for the
  simulator).
- **Orientation.** Read it from `setPreferredOrientations`, the manifest or Info.plist. Portrait
  games export to 9:16 directly; landscape games go to 16:9.
- **Sound.** Look for audio packages and audio assets. If there are none, set
  `game.has_audio: false` and pass `--game-audio no`, so a silent track is expected rather than
  a failure.

Tests and `tool/` entries often already build a level screen with fakes. Copy the *set-up*, but
never `import` from `test/` into `lib/`. If you need a fake, write a small capture-only fake inside
`main_capture.dart`. Some projects have tests that fail when lib/ mentions a test fake.

## 2. lib/main_capture.dart

Start from `assets/main_capture.dart` and fill in its four `GAME` sections:

1. **Imports**: the level screen, the level data and the services.
2. **Level start**: decide whether the game signals the playable moment itself.
   - Set `kGameSignalsLevelStart = true` when a guarded hook prints `CAPTURE_LEVEL_START` after
     loading or an intro. That is the exact moment, and it beats the default.
   - The default prints the marker after the level's first frame plus `kLevelStartDelayMs`.
     That is enough when the level is interactive from its first frame.
3. **Start-up without the extras**:
   - the same orientation as `main.dart`;
   - the seed;
   - fakes or skipped init for ads, analytics, prompts and purchases;
   - **in-memory saves** (a capture build shares the app id with production, so a real save
     would overwrite the developer's progress on the phone);
   - tutorials marked as seen.
4. **The level screen for each play mode, and the level count.** When the bot is deterministic,
   also write `captureLevelLength`: play the plan off screen and return how long it lasts. The
   host then shows the end card for 1.5 s and continues into the next level, so a level shorter
   than the clip still fills the take. Each switch is logged as `CAPTURE_EVENT next level N`.
   Report the switch in the brief.

Rules:

- `lib/main.dart` is never touched. Production code only changes through hooks the developer
  approved, each wrapped in `const bool.fromEnvironment('CAPTURE_MODE')` so release builds
  compile them out:
  ```dart
  if (const bool.fromEnvironment('CAPTURE_MODE')) print('CAPTURE_LEVEL_START');
  ```
- **End card marker**: keep `navigatorObservers: [CaptureRouteObserver()]` on the capture
  entry's MaterialApp. Every dialog opened during the level is logged as `CAPTURE_EVENT popup`,
  which `export --end-card` uses to end the clip on the win/lose card. A game that draws its end
  card in the widget tree instead prints `CAPTURE_EVENT end card` from a guarded hook. Without
  either, the export estimates the card at `CAPTURE_LEVEL_END + clip.end_card_delay_s`.
- **No DEBUG ribbon**: profile and release builds never show one. For debug builds (emulator
  fallback, iOS simulator) the template sets `WidgetsApp.debugAllowBannerOverride = false`.
  That hides the ribbon whatever the game's MaterialApp says.
- **Flame**: `debugMode` belongs to each component and defaults to false. Turn off any place the
  game sets it to true, and any `FpsTextComponent`.
- **Web**: the recorder passes `capture_level`, `capture_seed`, `capture_play_mode` and
  `capture_hold_ms` in the URL, so one build serves every take.
- **Check it** once the developer has agreed and the file is written:
  - `dart format lib/main_capture.dart`. Pre-commit gates often format-check all of lib/, and
    the project's page width applies.
  - `dart analyze lib/main_capture.dart`.
  - The project's tests, once.
  - Then do one dry take before the real one.

## 3. Markers

The app prints these lines; `launch_and_record.dart` reads them from `flutter run`, `flutter
drive` or the browser console.

| Line | When | Used for |
|---|---|---|
| `CAPTURE_BOOT level=N seed=S mode=M` | `main()` starts | the log |
| `CAPTURE_READY` | first frame | start the recorder (the hold screen covers the recorder's start-up) |
| `CAPTURE_LEVEL_START level=N` | the level is playable | the cut point (snapped to the scene change within 0.9 s before it) |
| `CAPTURE_EVENT <label>` | a moment worth a look | peak and cover hints, the brief |
| `CAPTURE_EVENT popup <route>` | a dialog opened after the level start (the template's `CaptureRouteObserver`) | the end card's time for `export --end-card`; a game without dialog routes prints `CAPTURE_EVENT end card` from a guarded hook |
| `CAPTURE_LEVEL_END …` | level over | the brief; "lost early" ranks a take down |
| `CAPTURE_REPLAY_META {…}` / `CAPTURE_REPLAY {…}` | replay-record takes | written to `social/replays/level_<N>.json` |
| `CAPTURE_ERROR <msg>` | set-up failed (no such level, unreadable replay) | stops the take with that message |
| `CAPTURE_FPS <n>` | web only, injected by the recorder | `browser_fps` in take.json: tells a slow game from a slow recorder |

## 4. Who plays

Pick the best one that works, in this order:

- **a. `bot`**: the game's own bot, solver or demo plays. No human needed, and the result is
  repeatable with the seed. Several takes with `--vary-seed` give different runs of a random game.
- **b. `replay`**: the developer plays once with `--play-mode replay-record`. That writes
  `social/replays/level_<N>.json`, and every later take plays it back through `GestureBinding`
  with the same seed. Don't use it when the game is physics-driven: Forge2D or anything that
  integrates with frame time drifts, and the replay walks into walls. How the file reaches the
  app:
  - Android: `adb push` to `/sdcard/Android/data/<appId>/files/g2s_replay.json`, plus `CAPTURE_REPLAY_PATH`.
  - Desktop and iOS simulator: a host path.
  - Web: served at `/assets/g2s_replay.json`, loaded with `rootBundle`.
- **c. `script`**: an integration test drives taps. This needs `integration_test` in
  dev_dependencies, so ask first. It also needs `assets/capture_test.dart` copied to
  `integration_test/capture_test.dart` and `assets/integration_test_driver.dart` copied to
  `test_driver/integration_test.dart`. The test sets
  `binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive`, so the game runs
  in real time. The recorder runs `flutter drive --driver=test_driver/integration_test.dart
  --target=integration_test/capture_test.dart -d <device> --profile --dart-define=…`. On web,
  `flutter drive` needs a running chromedriver.
- **d. `human`** (default until something else is set up): the hold screen counts down 3-2-1 on
  the device, recording runs from the countdown, and the developer plays. Before the command
  starts, tell them in chat to watch the device and play for about `duration + 2` seconds. Allow
  2–3 takes and keep the best.

## 5. Devices and build modes

- **Choosing a device**: `launch_and_record.dart devices` ranks them as real Android phone →
  Android emulator → iOS simulator → desktop → web. It drops any device whose platform folder
  the project lacks, or whose recorder is missing. If more than one is usable, ask once and save
  the choice in `config.yaml → capture.device`.
- **Build mode** (Flutter 3.47 `flutter run` checks `supportsRuntimeMode`):

  | Device | Mode |
  |---|---|
  | Real phone | `--profile`: smooth, no DEBUG ribbon |
  | Android emulator, x86_64 or arm64 image | `--profile` and `--release` are accepted; only 32-bit x86 images are debug-only |
  | iOS simulator | debug only, so expect lower fps |
  | Desktop | `--profile` |
  | Web | `--release` |

- **A 9:16 emulator**: the `pixel_2` profile is 1080×1920. The skill never runs these commands
  itself; give them to the developer:
  ```
  sdkmanager "emulator" "system-images;android-35;google_apis;x86_64"
  avdmanager create avd -n g2s_pixel2 -k "system-images;android-35;google_apis;x86_64" -d pixel_2
  flutter emulators --launch g2s_pixel2
  ```
- **No device at all**: `devices` exits 4 and lists what to do: plug in a phone, start an
  emulator, or create one. Show that list and stop. Never wait for a device to appear.

## 6. Recorders

- **Android, real phone or emulator**: `scrcpy -N -n --record=take.mkv --max-fps=60 --video-bit-rate=16M`.
  - Audio is captured on Android 11+ with scrcpy 2.0+. Distro packages are often 1.x, which has
    no audio, so prefer snap or the GitHub release.
  - The phone may go quiet while scrcpy captures its sound.
  - The recorder turns on Do Not Disturb (`cmd notification set_dnd priority`) and stay-awake,
    and puts both back afterwards.
  - Takes are MKV, so a killed recorder still leaves a playable file.
- **iOS simulator**: `xcrun simctl io <udid> recordVideo --codec=h264 --force take.mov`. There
  is no sound; pick a sound in the TikTok app or use the silent cut.
- **Real iPhone**: it can't be driven from here. The developer records with Control Centre →
  Screen Recording (microphone off, Do Not Disturb on) and hands over the file. The skill then
  starts at Step 3 with `--in`.
- **Linux desktop or web**: Chrome (or the GTK window, with `GDK_BACKEND=x11`) on X11/XWayland,
  recorded with `ffmpeg -f x11grab`.
  - **Unattended takes** (`bot`, `replay`, `script`, `--display auto`) go to a private
    **Xvfb** display at the export size, normally 1080×1920:
    - Chrome runs in kiosk mode with `--window-size` given in CSS pixels (the display size
      divided by the scale factor).
    - Chrome draws on the GPU through ANGLE/Vulkan
      (`--ignore-gpu-blocklist --use-angle=vulkan --enable-features=Vulkan,DefaultANGLEVulkan,VulkanFromANGLE`).
      If this machine's GPU stack needs other flags, set `G2S_CHROME_GPU_FLAGS`.
    - `webgl_renderer` in the take JSON names the GPU. A name with SwiftShader or llvmpipe
      means software drawing, which is slow and can drop sprites; the take gets a warning.
    - Nothing appears on the desktop, so a locked screen doesn't matter.
  - **Human takes** (`human`, `replay-record`) use a window on the real screen
    (`--display screen`). The recorder refuses to start when the screen is locked or blanked:
    a window there renders at about 1 fps.
  - `browser_fps` in the take JSON is the page's own frame rate. It's rough (it reads low on
    Xvfb while the capture still changes ~56 times a second), so trust the QC smoothness
    figure instead.
  - **Separate audio**: sound is recorded by a second ffmpeg from a PipeWire null sink that
    only the game plays into (`PULSE_SINK`), and the two parts are joined on their start
    times. One ffmpeg grabbing both dropped the picture from 60 to about 40 fps.
  - **Human takes** use the default output monitor, so the player can hear the game. Mute other
    apps.
  - **Web without Playwright**: Chrome is started directly with `--remote-debugging-port`, and
    the recorder reads the console over the DevTools protocol, which is the same protocol
    Playwright uses. Playwright's own video has no sound, so it is never the recorder.
  - **Window size on a real monitor**: the window has to fit the screen. On a 1080p monitor a
    portrait window is about 562×1000, so the 1080×1920 export is upscaled about 1.9× (QC
    warns). Unattended takes avoid this on Xvfb, and an Android device is crisp too.
- **macOS desktop/web**: ffmpeg `avfoundation` screen capture, cropped later with
  `process_video --crop`. Game sound needs a loopback device such as BlackHole. Untested.
- **Windows**: ffmpeg `gdigrab title=<window>`. Untested.

Do Not Disturb: Android is handled by the recorder; GNOME banners are switched off while a
window is on screen. On macOS and iOS, ask the developer to turn on Focus.

## 7. Timeouts and clean-up

Every step has a limit:

| Step | Limit |
|---|---|
| `flutter devices` | 90 s |
| First `CAPTURE_READY` (a first Gradle or web build is slow) | `--boot-timeout` 900 s |
| `CAPTURE_LEVEL_START` after READY | `--start-timeout` 120 s |
| Recorder start | 20 s |
| Each clean-up step | 20 s |

On success, on error and on Ctrl+C, the recorder stops the processes in reverse order and puts
the device settings back:
- the recorder gets SIGINT, so the file is finalised;
- `flutter run` gets `q`, then SIGTERM;
- `am force-stop <appId>`;
- Chrome, the web server, Xvfb and the audio sink are shut down;
- Do Not Disturb and stay-awake are restored.

Exit codes:

| Code | Meaning |
|---|---|
| 4 | no device |
| 6 | a tool is missing |
| 7 | build or launch failed |
| 8 | the level never became playable |

## 8. What went wrong before

| Symptom | Cause | Fix |
|---|---|---|
| ffmpeg from the shell says "Either text, a valid file… must be provided" | zsh reads `$F:t` in `fontfile=$F:text=…` as a modifier | write `${F}:text`; the scripts call ffmpeg without a shell |
| Take drops to ~40 fps with sound | one ffmpeg grabbing X11 and pulse together | the recorder uses two processes (built in) |
| `width not divisible by 2` | odd window size | the recorder crops to even (built in) |
| Xvfb take shows only the top-left of a huge page | `--window-size` passed in device pixels | CSS pixels = display ÷ scale factor (built in) |
| Web take cut off on the right (pause button, last booster missing) | Chrome lays a window out at least ~500 CSS px wide; a 412-px window rendered 500 wide | the window is 540 CSS px wide (scale 2.0 on 1080) (built in, 2026-11-04) |
| Xvfb take at single-digit fps, sprites missing | Chrome fell back to SwiftShader | GPU flags through ANGLE/Vulkan (built in); check `webgl_renderer`, set `G2S_CHROME_GPU_FLAGS` if needed |
| On-screen take at 1 fps, QC "choppy" | the desktop was locked or blanked | unattended takes use Xvfb; the recorder refuses a locked screen (built in) |
| Cut opens on the blank hold screen | the marker printed before the first level frame reached the screen | the snap looks 1.6 s ahead as well as back (built in) |
| Cover is a blank wall | a uniform frame scores as "sharp" | covers skip low-entropy frames (built in) |
| A user's file opens on a loading screen | no marker in a user file | `export --in` trims a blank/still lead-in; check the first frame |
| Page script never ran (no `CAPTURE_FPS`) | `Page.addScriptToEvaluateOnNewDocument` without `Page.enable` | enable the Page domain first (built in) |
| A filter's `metadata=print` gave nothing to parse | without `file=` it logs lines prefixed `[Parsed_metadata…]` | always print to a file (built in) |
| Level done in 7 s, then a still end card | the bot is faster than the clip | `captureLevelLength` + continue to the next level; or a shorter `--duration` with the user's OK |
| Recording 10 s longer than asked | ffmpeg ran with `-nostdin` and ignored `q` | stop with SIGINT (built in) |
| No CAPTURE_READY | the capture entry crashed before the first frame, or the build failed | read the log tail in the take JSON; run `flutter run -t lib/main_capture.dart` once by hand |
| Silent take from a game with sound | wrong sink, or scrcpy 1.x / Android < 11 | see `audio` in take.json; check `pw-cli ls Node` / `scrcpy --version` |

## 9. Tools

The skill never installs system tools. When one is missing, name it and give the install line:

| Tool | Linux | macOS | Windows |
|---|---|---|---|
| ffmpeg | `sudo apt install ffmpeg` | `brew install ffmpeg` | `winget install Gyan.FFmpeg` |
| scrcpy (2+ for game audio; 1.x records video only) | `sudo snap install scrcpy` or the GitHub release | `brew install scrcpy` | `winget install --exact Genymobile.scrcpy` |
| Linux desktop builds | `sudo apt install clang cmake ninja-build pkg-config libgtk-3-dev` | | |
| xwininfo, Xvfb | `sudo apt install x11-utils xvfb` | | |

adb is found in `$ANDROID_HOME/platform-tools` or `~/Android/Sdk/platform-tools` even when it
is not on PATH.

## 10. config.yaml

`assets/config.example.yaml` is the schema, with comments. Only confirmed values go in.
Anything unknown stays `null` and gets asked once.
