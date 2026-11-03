# Changelog

## v1.0.0 — 2026-11-03

First version. You ask in plain words ("chạy game ở level 10, quay đoạn đầu tầm 20s"); the
skill records real gameplay, checks it, exports four ratios, and drafts TikTok, Reddit,
LinkedIn and X posts with scores. Videos and drafts are written to `social/output/`. Nothing is
posted.

### Added

- **Project detection** (`detect_project.dart`). It reports:
  - whether the project uses Flutter and Flame, its platforms, ids, orientation and sound;
  - leads with file:line for the level loader and count, a bot or solver, and what to switch off;
  - RNG and existing capture hooks;
  - unconfirmed post facts from README, CHANGELOG and git.
- **Capture entry template** (`assets/main_capture.dart`):
  - markers: `CAPTURE_READY`, `CAPTURE_LEVEL_START`, `CAPTURE_EVENT`, `CAPTURE_LEVEL_END`,
    `CAPTURE_REPLAY*`, `CAPTURE_ERROR`;
  - a hold screen, with a 3-2-1 countdown in human mode;
  - immersive mode, and no DEBUG ribbon in any build;
  - URL overrides on web, so one build serves every take;
  - touch replay recording and playback through `GestureBinding`;
  - when the bot finishes early, a 1.5 s end card and then the next level.
- **Recorder** (`launch_and_record.dart`):
  - `devices` ranks Android phone → emulator → iOS simulator → desktop → web, and gives the
    emulator and phone steps when nothing is usable.
  - `record` supports scrcpy, simctl, ffmpeg x11grab on a window or Xvfb, and Chrome driven
    over CDP. It also handles DND and stay-awake on Android and an isolated PipeWire sink.
  - Video and audio are recorded by separate ffmpeg processes and joined on their start times.
  - Every step has a timeout, and clean-up runs on Ctrl+C.
- **Video** (`process_video.dart`):
  - QC checks: duration ±2 s, black, freeze, audio, unique frames per second, upscale.
  - With several takes, it picks the best one.
  - It snaps the cut to the scene change at the level start.
  - Exports 9:16, 16:9 and 4:5 over a blurred copy of the clip, so there are no black bars.
  - Cover candidates, a TikTok UI-zone preview, a peak-first cut, and a burned-in hook in
    Be Vietnam Pro.
- **Frames** (`extract_frames.dart`): 1 fps plus scene changes, and timestamped contact sheets.
- **Validator** (`validate_posts.dart`):
  - limits read from `platform_specs.md`, `posts_format.md` and `review_rubric.md`;
  - X counted with the twitter-text v3 weighting;
  - hashtag layers and counts, off-game trend tags that need a bridge, dev tags only on tech
    angles;
  - stock-phrase ban, hard-fact patterns that need confirmed claims, Reddit hygiene;
  - weighted scores;
  - renders `posts.md` from `posts.json`.
- **References**:
  - platform specs with sources, checked 2026-11-03;
  - the viral playbook and the review rubric;
  - trend words for Nov–Dec 2026 (VN and EN, with the calendar: GTA VI 19/11, Nhà giáo 20/11,
    Black Friday 27/11, TGA 10/12, thi học kỳ, Tết 6/2/2027);
  - flutter_capture with a failure table.

### Decisions that differ from the brief

- **TikTok hashtags are 4–5, not 4–6.** TikTok has reportedly capped posts at 5 in the app since
  2025-08. TikTok hasn't confirmed it.
- **X `community` stays null.** X shut Communities down in 2026 (announced 2026-04-23).
- **The web path drives Chrome over the DevTools protocol instead of through Playwright.** It is
  the same protocol and needs no Node or Python. The sound still comes from ffmpeg, and
  Playwright's silent video is never used.
- **Profile mode on emulators.** The brief says profile builds don't run on emulators. Flutter
  3.47's `flutter run` accepts `--profile` and `--release` on x86_64 and arm64 Android
  emulators. Only the iOS simulator, and 32-bit x86 Android images, are debug-only.

### Fixed after the first test round (4 cases, a copy of tiptoe-tabby, 2026-11-03)

- **Xvfb.**
  - `--window-size` was passed in device pixels, so the page was 2.6× too big and only its
    top-left was recorded. An earlier "SwiftShader draws CanvasKit wrongly" diagnosis was really
    this bug.
  - Chrome on Xvfb now draws on the GPU through ANGLE/Vulkan, a tip from the baseline run.
  - Unattended takes default to Xvfb at 1080×1920 (crisp, nothing on the desktop). A locked
    screen had made the on-screen window render at 1 fps.
  - Screen mode now refuses to start on a locked or blanked screen.
- **The scene snap never worked.** `metadata=print` without `file=` logs `[Parsed_metadata…]`
  lines, so every cut fell back to marker − 0.1 s. It now writes to a file, and it looks 1.6 s
  ahead as well as 0.9 s back, because a slow renderer shows the first level frame after the
  marker.
- **Covers skip blank frames**, which a uniform wall used to win as "sharp". Each export ratio
  now gets its own cover, `cover_<ratio>.jpg`.
- **User files.** A blank or still lead-in (a 0.47 s loading screen) is trimmed automatically.
  `--platforms` exports only the ratios those platforms need.
- **Exports run at the content's real frame rate** (30 when the picture changes only 30 times a
  second).
- **Browser reporting.** Page scripts are installed before the game loads (`Page.enable` first),
  so `browser_fps` and `webgl_renderer` are reported.
- **The Chrome profile** lives in the take folder and is removed with retries.
- **`devices`.** It prints full SDK tool paths when they aren't on PATH, takes
  `--saved-device`, notes a missing `/dev/kvm`, and the iPhone hint says microphone off.
- **SKILL.md.**
  - The first run also lists devices, times the bot's level and asks about generative-AI use.
  - Never import test fakes into `lib/`; run `dart format`, `analyze` and the tests after
    writing the capture entry.
  - There is now a no-link rule, a who-played rule, and a split between code-verified facts and
    dev-story facts.
  - Stop after "no device".
  - Read the level from the HUD for user files.
  - Make small edits to the shared trend file.
- **`posts.example.json`** no longer models unbacked dev-story lines: every one has a confirmed
  fact and a claim.
- **The overlay** reads `tiktok.ui.top_px`; the key it used to read no longer existed.

### Fixed after the second test round

- **extract_frames** no longer exits 1 when no cut passes the 0.3 scene threshold. It retries
  at half the threshold and reports the one it used.
- **`cover --at`** now redoes `cover_<ratio>.jpg` for every exported ratio as well as `cover.jpg`.
  It had grabbed from the low-res raw clip when there was no 9:16 export.
- **The resolution check** measures the ratios actually exported. A Reddit + LinkedIn run used
  to warn about a 9:16 file it never made.
- **Smoothness** ignores seconds that are mostly a still end card. The 60/30 fps export choice
  uses the busy seconds (75th percentile).
- **Hook text** is wrapped into balanced lines, with no lone last word.
- **The template's countdown** sits on a `Material`, so it no longer shows the red underlined
  fallback style. It also braces a multi-line `if`, which tripped the
  `curly_braces_in_flow_control_structures` lint at 80 columns.
- **detect_project**:
  - lists store-listing files (fastlane/metadata, `store/`, `docs/`) and release-state lines;
  - no longer reports the capture entry's own lines as existing hooks.
- **The web build** is deleted after recording; it was ~60 MB left in the run folder.
- **SKILL.md**:
  - when the level is shorter than the clip, offer the right choices;
  - warn that `flutter run` can uninstall a store build (signature mismatch) and wipe its save;
  - "coming soon" needs a confirmed release state;
  - for a user file, who played is unknown;
  - the HUD under TikTok's top bar is usually fine (`240,0,0,0` when it isn't);
  - remind about `.gitignore`.
- **config.example.yaml** gains `ai_use` and `release_state`.

### Tested (dev machine: Linux, Wayland, NVIDIA, no Android device)

Four cases from the brief, run by fresh subagents on copies of tiptoe-tabby (60 levels, demo
bot, no sound), with no-skill baselines for cases 1 and 4.

- **Round 1:** 30/30 assertions with the skill against 27 % without. The run notes found the
  bugs fixed above.
- **Round 2:** 30/30 assertions again against 20 % without (the no-writes assertion was
  tightened). The recording case now needs one take on Xvfb at 1080×1920 with the GPU, passes
  QC and has no resolution warning.

| Case | With skill | Baseline |
|---|---|---|
| First run on an unset-up project | asks, proposes `main_capture.dart` (dart format/analyze/123 tests OK in a throwaway copy), writes nothing | wrote `social/tools`, videos and `build/` files unasked; read "4 platforms" as TikTok/Instagram/X/LinkedIn |
| Level 10, 20 s, all four platforms | clip + 4 ratios + covers + brief + 16 drafts, `validate_posts` exit 0 | — (shares the desktop) |
| No device | exit 4 in 2.6 s, full-path emulator steps, stops | — |
| User video → Reddit + LinkedIn | blank lead-in trimmed, only 16:9 + 4:5 exported, validate exit 0 | 4:5 for Reddit, 4–5 LinkedIn hashtags, no structured output |

Also checked by hand:
- spoolway: detection found Flame, the review prompt, IAP, analytics, a solver and the
  fastlane listing.
- The validator: the example passes, and 11 planted violations are all caught.

### Not tested yet

- Android (scrcpy) and the iOS simulator: no device on the dev machine.
- macOS and Windows desktop capture.
- Linux desktop builds: no toolchain on the dev machine.
- Replay and script play modes.
