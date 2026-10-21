---
name: game-ad-video
description: >-
  Run a Flutter game, let the agent play it while recording real gameplay, and cut the takes into
  a 9:16 UA ad (TikTok/Reels/Shorts, 15–30 s), an App Store App Preview (886x1920, 15–30 s), or a
  16:9 gameplay trailer (45–120 s, cut on the music's beat, full-frame cards, logo and end card,
  plus a 9:16 cut-down): facts from the repo → run on web (or Android via adb) → explore and
  record scripted takes → 3 directions, human picks one → storyboard (ad.json / trailer.json) →
  render with captions, push-ins, layouts for portrait footage in 16:9, BGM + SFX → hard checks.
  Borrows huashu-design's three-direction gate, storyboard card, camera rules, two-layer audio
  and verify-video.sh. Use when asked to "make an ad video for my game", "record gameplay for an
  ad", "app preview video", "make a game trailer", "làm video quảng cáo game", "quay gameplay
  làm quảng cáo", "làm trailer game". Don't use for still screenshots (appstore-assets,
  flutter-store-metadata), animated motion design built from scratch (huashu-design), or games
  that are not playable on this machine.
license: MIT
metadata:
  version: 1.2.0
  author: "Nguyen Van Lam"
permissions:
  filesystem: { read: true, write: true }
  shell: { enabled: true }
  network: { enabled: false }
---

# game-ad-video: play the game, record it, cut an ad or a trailer

The footage is the product. An ad for a game shows real play — anything else is a promise the
game doesn't keep, and the App Store rejects previews that aren't captured from the app.

## Rules

1. **Real footage only.** Every frame of gameplay comes from a take recorded by `recorder.py`.
   Never mock up a level, a score or a feature the game doesn't have. Captions state what the
   footage shows.
2. **Three directions, then stop.** Before rendering the final cut, show three direction boards
   and wait for the human's choice (huashu-design rule: a style word narrows the choice, it never
   removes it).
3. **Storyboard before render.** `ad.json` is the shot card. Each shot has its check frames written
   *before* rendering; after rendering you look at exactly those frames.
4. **The checks decide, not your eyes alone.** `build_ad.py check` must PASS for each profile
   before you report it done. Report failures with their output.
5. **Videos never go to GitHub.** Takes and rendered ads stay on this machine, git-ignored. Never
   `git add -f` a video, and never commit one some other way. The human gets the file path.

## Tools

| Script | Does |
|---|---|
| `scripts/recorder.py` | Holds the game open (Playwright + Chrome, or adb) and records takes: `serve`, `shot`, `tap`, `swipe`, `key`, `wait`, `rec start/stop`, `mark`, `play`, `status`, `stop` |
| `scripts/build_ad.py` | `storyboard` (shot table), `board` (direction board PNG; `--wide` for a trailer), `beats` (music beat grid), `render` (profile `ua` / `app-preview` / `trailer` / `trailer-9x16`), `check` (hard checks + check frames) |
| `scripts/beats.py` | BPM, first downbeat, sections and drop of a music track (numpy only), so trailer cuts land on the beat. `build_ad.py beats` calls it |
| `../game-clone-pipeline/scripts/contact-sheet.sh` | Take or final video → timestamped contact sheets you can read |
| `huashu-design` (sibling skill, optional) | `assets/bgm-ad.mp3`, `assets/sfx/**`, `scripts/verify-video.sh`. Found at `$HUASHU_DESIGN_DIR` or `~/.claude/skills/huashu-design`. Without it, pass `audio.bgm` yourself; the checks skip black-frame and loudness tests |

Needs: ffmpeg, Python 3 with `playwright` (Chrome or Playwright's Chromium), Flutter for the
game. Trailers also need `numpy` (beat detection). Android path: `adb`
(`~/Android/Sdk/platform-tools/adb`) and a device or emulator.

Output, all in the game repo under `marketing/video/`:

```
.gitignore    written by the scripts: every video, takes/, shots/, sheets/, .build-*/
takes/        NAME.mp4 + NAME.marks.json + the action scripts   (git-ignored)
shots/        screenshots taken while exploring                 (git-ignored)
sheets/       contact sheets and check frames                   (git-ignored)
directions/   a.png b.png c.png — the three direction boards
ad.json       the ad storyboard           trailer.json   the trailer storyboard
ad-ua-9x16.mp4  app-preview-886x1920.mp4                        (git-ignored)
trailer-16x9.mp4  trailer-9x16.mp4                              (git-ignored)
```

Only `.gitignore`, `directions/`, `ad.json` and `trailer.json` get committed. `recorder.py serve` and
`build_ad.py render` create or extend the folder's `.gitignore` (`*.mp4 *.mov *.m4v *.webm *.mkv`
plus the folders above). `build_ad.py check` fails a video that git would push. If a video was
committed before, run `git rm --cached <file>` and commit; it stays in history until the human
decides to rewrite it.

## Workflow

### 1. Facts

Read `pubspec.yaml` (name), the app icon, `SPEC.md` / `DESIGN.md` / `README.md` if present. Write
down:

- **Selling points the code proves**: the core loop, combos, levels, modes.
- **Design tokens**: font file, background, foreground and accent colours. These go in
  `ad.json → game` so the captions and end card look like the game.
- **Store name.** It must match the in-app name.

If the game has a deterministic seed, a debug level picker or a bot (`tool/simulate.dart` in
game-clone-pipeline games), note it. These are the fastest way to reach good moments on cue.

### 2. Run the game

Web is the default; it records sharply on Wayland and headless:

```bash
flutter build web --release && python3 -m http.server 8080 -d build/web   # in the background
# or: flutter run -d web-server --web-port 8080 --release
python3 <skill>/scripts/recorder.py serve --url http://localhost:8080 &   # wait for {"ready": true}
```

The viewport defaults to 430×932 CSS px at DPR 2.5, so takes come out at about 1075×2330. That
aspect matches 886×1920 exactly, so the App Preview needs no letterboxing. Flutter/canvaskit needs
a few seconds to boot (`--boot-ms`, default 3000).

`--audio` records the system audio monitor alongside the video, to keep the game's own sound
effects. It hears every app on the machine, so keep everything else quiet. Without it, takes are
silent and the ad gets BGM + SFX only.

Android: `recorder.py serve --android [--serial X]`. It uses device-pixel coordinates and
`screenrecord` (max 180 s per take). There's no `reload`, so restart the app with
`adb shell am start`.

### 3. Explore

Learn the game before recording anything:

```bash
recorder.py shot start          # → marketing/video/shots/start.png ; Read it
recorder.py tap 215 640         # CSS px = pixels of the shot image
recorder.py swipe 100 600 330 600 --ms 200
recorder.py shot after-tap
```

Find the core loop, the most satisfying moment (combo, clear, chain), a near-miss or fail state,
and a win. Note coordinates. If the game has onboarding, play through it once so takes start in
real gameplay.

### 4. Record takes

Write action scripts in `marketing/video/takes/` (see `templates/take.example.json`):

```json
{"lead_in_ms": 500, "tail_ms": 1200, "actions": [
  {"tap": [96, 271], "after": 180},
  {"mark": "combo"},
  {"repeat": 5, "actions": [{"swipe": [100, 600, 330, 600], "ms": 160, "after": 250}]},
  {"wait": 800}, {"key": "Space"}, {"shot": "end-state.png"}]}
```

```bash
recorder.py play takes/clear-rows.json --take take-01 --reload
```

Record each beat several times, with different pacing and different starting states. 5–10 takes
of 5–20 s is normal. Pace taps like a good human player (150–300 ms apart). A bot that taps every
16 ms reads as fake.

For moments you can't script, record manually: `rec start take-07`, then play with
`shot`/`tap` while you look, marking moments with `mark combo`, then `rec stop`. Thinking time
becomes dead footage; cut around the marks.

Every take returns its `duration` and `marks`. Review each with a contact sheet:

```bash
FPS=2 COLS=8 ROWS=4 bash <skills>/game-clone-pipeline/scripts/contact-sheet.sh takes/take-01.mp4 sheets/take-01
```

From the timestamps, list candidate clips as `take @ in–out: what happens`.

### 5. Three directions — human gate

Read `references/ad-structure.md` § Directions. Pick three directions that fit *this* game. For
each one, render a board from a real hook frame:

```bash
build_ad.py board --ad ad.json --take takes/take-03.mp4 --at 4.2 \
  --title "B · *Challenge*" --hook "Can you clear *all 35*?" \
  --beats "0–3s dare: full board|3–8s push onto a x20 combo|8–13s refill, score climbs|13–15s end card" \
  --out directions/b-challenge.png
```

Show the three PNGs, with one line each on the idea and why it fits. **Stop and wait for the
choice.** A mix is fine ("B's hook with A's pacing").

### 6. Storyboard

Write `marketing/video/ad.json` for the chosen direction. Start from `templates/ad.example.json`;
fields are in `references/ad-structure.md` § ad.json. Then print the shot card:

```bash
build_ad.py storyboard ad.json --profile ua
build_ad.py storyboard ad.json --profile app-preview
```

Check the card against the camera rules (`references/ad-structure.md` § Camera, from
huashu-design `camera-language.md` and `storyboard-basics.md`):

- the hook lands in the first 3 s;
- every push-in names its anchor;
- no two shots in a row at the same framing;
- one action per shot;
- each profile is 15–30 s;
- every shot has a check frame.

`render` refuses a profile outside 15–30 s. The App Preview drops the end card and refuses
selling words (download, free, price) in its captions. Give a shot `caption_app_preview` to
override its caption for that profile.

### 7. Render

```bash
build_ad.py render ad.json --profile ua
build_ad.py render ad.json --profile app-preview
```

### 8. Check and look

```bash
build_ad.py check ad-ua-9x16.mp4 --profile ua --ad ad.json
build_ad.py check app-preview-886x1920.mp4 --profile app-preview --ad ad.json
FPS=2 COLS=8 ROWS=4 WIDTH=200 bash <skills>/game-clone-pipeline/scripts/contact-sheet.sh ad-ua-9x16.mp4 sheets/ua
```

`check` tests size, fps, duration, H.264 yuv420p, AAC stereo, the 500 MB cap and that git
ignores the file (inside a git repo), then runs
huashu-design's `verify-video.sh` (black frames, -14 LUFS loudness). It also extracts every check
frame to `sheets/check-<profile>-fNNNN.jpg`.

Read the check frames and the contact sheet. For each one, confirm:

- the caption is readable and doesn't cover the game's HUD or the action;
- each push-in ends on its anchor;
- the end card shows;
- there are no frozen or black stretches.

Fix `ad.json` and re-render until both checks PASS and the frames look right.

### 9. Report

```
GAME AD VIDEO — <READY | NEEDS WORK>
Direction   B · Challenge (chosen by <human>)
UA          ad-ua-9x16.mp4          1080x1920 · 15.3s · -14 LUFS · check PASS
Preview     app-preview-886x1920.mp4 886x1920 · 15.4s · check PASS
Takes       7 recorded, 4 used
Audio       BGM huashu bgm-ad · 3 SFX cues · game audio: no (--audio off)
Git         videos git-ignored, not pushed · files at marketing/video/
Open        <anything unresolved: music licence for a user track, a caption to confirm, …>
```

App Store Connect takes the preview per device size. 886×1920 covers the 6.9"/6.5" iPhone
slots. Uploading is the human's job, or `game-clone-pipeline` stage 8's.

## Trailer mode

A trailer is a 16:9 gameplay trailer, 45–120 s, plus a 9:16 cut-down of 30–60 s, both from one
`marketing/video/trailer.json`. The model is a showcase trailer such as *Constance – Official
Gameplay Trailer*:

- it opens cold;
- the title lands on the music's drop;
- three verbs show how to play;
- a montage speeds up on the beat;
- it holds on the payoff;
- it ends on logo, platforms and date.

The same rules hold: real footage only, three directions, storyboard first, checks decide.
Steps 1–4 (facts, run, explore, record) are unchanged. Record more variety than for an ad: a
trailer burns through 15–25 shots. Then:

**T5. Music.** Choose the track (`audio.bgm`; huashu `ad` by default). Then find its grid:

```bash
build_ad.py beats ad --drop-at 9.5 --length 60
```

It prints `bpm`, `beat0`, the sections and the rises. It suggests a `music.start` that lands the
drop 9.5 s in and still leaves 60 s of track. Copy these into
`trailer.json → music: {"bpm", "beat0", "start"}`. A cut-down usually starts later (at the drop):
give it its own `music_trailer_9x16`. Low `confidence` (< 1.5) means a weak beat; check it by
ear, or set `music.sync: false`.

**T6. Three directions — human gate.** Read `references/trailer-structure.md` § Directions and
pick three that fit the game. Render a board for each with
`build_ad.py board --wide --take … --at … --title … --hook … --beats "…"`. Show them, then
**stop and wait** for the choice.

**T7. Storyboard.** Write `trailer.json` from `templates/trailer.example.json`.

- **Top level:** `"profiles": ["trailer", "trailer-9x16"]`.
- **Timing:** give every item `beats` instead of `out` / `seconds`. It then ends on the beat grid,
  so every cut lands on a beat.
- **Cards:** `{"card": {"text", "style": "title|feature|logo", "sub", "bg_take", "bg_at"}, "beats": 4}`.
  The logo card uses `game.logo` (a wordmark PNG) if set, else icon + name.
- **Layout** places portrait footage in 16:9: `fit` (blurred fill), `fill` (cut a band, montage),
  `panel` (take on one side, the verb big on the other; `side`), `grid`
  (`takes: [{take, in}]`, 2–3 side by side). In 9:16, `panel` and `grid` fall back to `fit`.
  Check their captions against the game's HUD and give them `caption_trailer_9x16` where needed.
- **End card:** add `date` and `platforms` (text chips, never store badge art). Only true claims.
- **Cut-down:** mark cold-open shots `"profiles": ["trailer"]`, add a hook shot with
  `"profiles": ["trailer-9x16"]`, and set `"fade_in": 0.6` with `"fade_in_trailer_9x16": 0`.

```bash
build_ad.py storyboard trailer.json --profile trailer        # `lands` column: bar:beat of each cut
build_ad.py storyboard trailer.json --profile trailer-9x16
```

Fix every `⚠` line: a cut off the beat, a shot running past its take, a `fill` blown up past 2×.

**T8. Render, check, look.**

```bash
build_ad.py render trailer.json --profile trailer          # → trailer-16x9.mp4
build_ad.py render trailer.json --profile trailer-9x16     # → trailer-9x16.mp4
build_ad.py check trailer-16x9.mp4 --profile trailer --ad trailer.json
build_ad.py check trailer-9x16.mp4 --profile trailer-9x16 --ad trailer.json
FPS=1 COLS=6 ROWS=8 WIDTH=320 bash <skills>/game-clone-pipeline/scripts/contact-sheet.sh trailer-16x9.mp4 sheets/t16
```

`check` adds a rule for trailers: hard cuts must land on the beat (±1 frame). Read the check
frames and the contact sheet. Confirm that:

- panel text is beside the take, not over it;
- grid captions clear the panels;
- cards are readable;
- the logo lands on the drop;
- there are no frozen or black stretches other than intended `fadeblack`s.

Then report as in step 9, with lines `Trailer` / `Cut-down` (size · length · BPM · cuts on the
beat · check PASS). Trailers go to YouTube, Steam, the landing page and the press kit. The App
Store takes App Previews, not trailers.

## Reference files

| File | Read at |
|---|---|
| `references/ad-structure.md` | steps 5–8: beats, the three-direction menu, camera rules, captions, audio, App Preview rules, `ad.json` fields |
| `references/trailer-structure.md` | T5–T8: trailer acts, cut-down, trailer directions, beat-cut editing, cards, layouts, audio, specs |
| `templates/ad.example.json` | step 6: a complete storyboard to copy |
| `templates/trailer.example.json` | T7: a complete 16:9 + 9:16 trailer storyboard to copy |
| `templates/take.example.json` | step 4: every action type |
| huashu-design `references/storyboard-basics.md` §5, `camera-language.md` §4–7, `audio-design-rules.md` | step 6 when a shot or the mix needs more than the summary here |

## Scope

Does: record real gameplay of a game that runs on this machine, then cut and check a UA ad, an
App Preview, and a 16:9 trailer with its 9:16 cut-down.

Does not: upload to App Store Connect, YouTube, Steam or ad networks, make still screenshots (`appstore-assets`),
build motion graphics from scratch (`huashu-design`), or license music. A user-supplied
`audio.bgm` track is the user's responsibility. huashu-design's SFX were generated with
ElevenLabs; the human confirms that commercial use is OK.
