---
name: gameplay-to-social
description: >-
  Turn a Flutter game's real gameplay into organic social posts: run the current project's game
  at the requested level (bot, replay, test script or the developer playing), record it (scrcpy,
  simctl, ffmpeg), check the clip (black, frozen, silent, choppy), export 9:16, 16:9 and 4:5 with
  a cover, read the frames, check live trends, then write and score 3+ variants each for TikTok,
  Reddit, LinkedIn and X and keep the strongest, validated against platform limits and the
  game's confirmed facts. Reads the project itself and remembers setup in social/config.yaml;
  also works from an existing video file. Use whenever someone wants gameplay clips or social
  posts for a game, even without naming the skill: "chạy game level X rồi quay video", "quay
  clip gameplay", "làm bài đăng TikTok/Reddit/LinkedIn/X cho game này", "viết caption cho clip
  game", "record gameplay for social posts". Don't use for paid UA ads, store previews or
  trailers (game-ad-video), store screenshots (appstore-assets) or auto-posting.
license: MIT
metadata:
  version: 1.1.0
  author: "Nguyen Van Lam"
---

# gameplay-to-social

The user asks in plain words, for example "level 10, about 20 s, all four platforms". The skill
records a checked clip, exports it in four ratios, and drafts validated posts for TikTok,
Reddit, LinkedIn and X with the best variant first.

## Rules

1. **Drafts only.** Never post, schedule or upload anything. Posting for real needs an explicit
   request and an API the user has configured.
2. **The project stays the user's.**
   - Never edit `lib/main.dart` or production logic.
   - Never commit, and never change the version in pubspec.yaml.
   - Ask first, then do it only on a yes: creating `lib/main_capture.dart`, adding a guarded
     hook in game code, adding a package (`integration_test`), editing `.gitignore`.
3. **Never install system tools** (ffmpeg, scrcpy, emulator images). Say what's missing and give
   the install line from `references/flutter_capture.md` § 9.
4. **Hard facts only from the project and `config.yaml → facts`.** Hard facts are features,
   numbers (downloads, ratings, the share of players who clear a level), awards, prices and
   giveaways, and dev-story facts. Everything else may be playful and exaggerated. To use a
   number as a hook, ask the user for the real one.
5. **No promise of going viral.** Explain why the chosen variant has an edge.
6. **Every limit, size and threshold lives in `references/platform_specs.md`.** Never hard-code one.
7. **Output goes to `social/output/lv<level>_<YYYYMMDD-HHMM>/` in the project.** Never use `build/`
   (`flutter clean` wipes it) and never overwrite an earlier run.

## Scripts

Run them as `dart <skill>/scripts/<name>.dart …`. They use dart: libraries only, so no
`pub get`. Each one prints JSON and documents its options in its header.

| Script | Does |
|---|---|
| `detect_project.dart [--project DIR] [--md]` | Flutter? Flame? platforms, ids, orientation, sound, leads with file:line for the level loader/count, bot/solver, what to switch off (ads, analytics, review/IAP prompts, tutorials), RNG, and unconfirmed facts (README, CHANGELOG, git). Exit 3 = not Flutter |
| `launch_and_record.dart devices --project DIR` | ranks usable devices (Android phone → emulator → iOS simulator → desktop → web) with the reason each one is out. Exit 4 = none, plus what to do |
| `launch_and_record.dart record …` | builds and runs `lib/main_capture.dart` with the `CAPTURE_*` defines, records from `CAPTURE_READY`, marks `CAPTURE_LEVEL_START`, stops after duration + tail, cleans up everything. Writes `take_N.mkv/.json/.log` |
| `process_video.dart export …` | cuts at the level start, checks the clip, keeps the best take, writes the 4 MP4s + cover + `work/qc.json`, cover candidates and a TikTok UI preview. Also `cover`, `hookcut`, `overlay`, `probe` |
| `extract_frames.dart --in video/raw.mp4` | 1 fps + scene-change frames, contact sheets with timestamps, `frames.json` |
| `validate_posts.dart posts.json --render posts.md` | hard checks; renders posts.md only when there are no errors |

## Step 0: project and config

1. Run `detect_project.dart` in the current folder. On exit 3 (not a Flutter project), ask the
   user for the game's path, and use `--project` from then on.
2. If `social/config.yaml` exists, read it and don't ask its questions again. Otherwise do the
   **first run** below, then continue.
3. When the user gives a video file, skip Step 2. Run `process_video.dart probe`, then go to
   Step 3 with `export --in FILE`. A first run in that case only needs the post questions of
   first-run step 3; the capture questions can wait.

### First run (no social/config.yaml)

1. Confirm what detection found by reading the code at its leads:
   - Flame, and the platforms;
   - how a level is loaded, how many there are, and how they are numbered;
   - a bot, solver or demo;
   - what to switch off while recording;
   - the RNG, the ids and the orientation.

   `references/flutter_capture.md` § 1 says what to look for. Also run
   `launch_and_record.dart devices`, which is read-only, so the device situation goes into the
   same summary. If a bot exists, work out how long it takes to play the requested level. When
   that is shorter than the clip, the take will continue into the next level, and the user
   should know that up front.
2. Collect post facts from README, CHANGELOG and git (first commit, recent features). They stay
   **unconfirmed**, and out of every post, until the user says yes.
3. Show the user a short summary of the above. Then ask for what's still missing, in one
   message, with a proposed default for each question:
   - language and market per platform;
   - store, wishlist or landing links (none yet is a valid answer: posts then say "coming soon"
     or ask for feedback, and never invent a link);
   - brand voice;
   - the game's own hashtag and its core hashtags (propose them; the user confirms);
   - TikTok personal or business account;
   - X Premium or not;
   - who plays while recording (Step 2 options, recommending the best one available);
   - whether generative AI was used for code, art or audio (some subreddits require disclosure);
   - which facts from step 2 may be used.
4. Propose `lib/main_capture.dart` from `assets/main_capture.dart`, with the four `GAME`
   sections filled in for this game (flutter_capture.md § 2), and any guarded hooks it needs.
   - Never import from `test/` into `lib/`. When a test fake is what you need, write a small
     capture-only fake inside the file.
   - Show the code or a diff. **Write nothing until the user agrees.**
   - Once the file is written, run `dart format`, `dart analyze` and the project's tests on it,
     so the project's own gates still pass.
5. Suggest adding `social/output/` to `.gitignore` (videos never go to git).
6. Save every confirmed answer to `social/config.yaml`, using `assets/config.example.yaml` as
   the template. Copy `assets/performance_log.md` to `social/performance_log.md`.

## Step 1: request → parameters

| Parameter | Rule | Default |
|---|---|---|
| level | check that it exists (`game.levels.count`); for a user's file, read it from the HUD | none: ask if missing |
| duration | allowed error ±2 s; a user's file is cut to it, or kept whole if shorter | 20 s |
| clip | starts at `CAPTURE_LEVEL_START`, so loading is never in it | the start of the level |
| end card | when the clip ends on a win/lose card (popup), the card fills only the last S seconds; the rest is play | `capture.end_card_s` in config, else `clip.end_card_s` in platform_specs (2 s) |
| platforms | | all four |
| languages | | from config |

Fill gaps with the defaults and write every assumption into `run.assumptions`.

**Level shorter than the clip.** A bot often clears a level faster than the clip runs. If
`captureLevelLength` knows how long the level takes (flutter_capture.md § 1 shows how to time
it), the take continues into the next level and the switch goes into the assumptions. If the
user clearly wants only this level, offer three options: a duration that ends on the level's
end card (within ±2 s of the request), the level alone (shorter), or a human take.

## Step 2: run and record

1. Run `launch_and_record.dart devices --project P --saved-device <config capture.device.id>`.
   - If it exits 4, there is no usable device. Show its `guidance` lines (connect a phone, start
     an emulator, or create one at 1080×1920 with the pixel_2 profile) and stop the run there.
     Don't wait, and don't write posts without footage. Offer the user-file route instead.
   - If more than one device is usable and config has none, ask once and save the answer.
   - If the saved device is gone, say so and offer what is available now.
2. Play mode, best available first: `bot` → `replay` (needs a `social/replays/level_<N>.json`
   recorded with `--play-mode replay-record`) → `script` (an integration_test with `fullyLive`)
   → `human`. Details are in flutter_capture.md § 4. In human mode, tell the user before the
   command starts that the device will count down 3-2-1 and they then play for about
   `duration + 2` s.
3. Record:
   ```
   dart <skill>/scripts/launch_and_record.dart record --project P --platform <android|ios-sim|linux|web|…> \
     --device <id> --level N --duration D --out <run>/work/takes --play-mode M --seed S \
     [--takes 2 --vary-seed] [--app-id ID] [--game-audio no] [--build-mode auto]
   ```
   - The build mode is chosen for you: profile on phones and x86_64/arm64 emulators, debug on
     the iOS simulator, release on web.
   - On web/Linux, unattended takes (bot, replay, script) render on a private Xvfb display at
     1080×1920, with Chrome on the GPU. Nothing shows on the desktop, and a locked screen
     doesn't matter. Human takes need a window on the real screen. The recorder refuses to
     start when that screen is locked.
   - Read `warnings`, `webgl_renderer` and `browser_fps` in the take JSON.
   - Use 2–3 takes when the game is random or a human plays.
   - When the level ends inside the clip (a win or a loss), record `--duration D+3`: the export
     then picks the exact length that puts the end card in the last S seconds.
   - On web, the take JSON has `page_px` (the page in device pixels) and `capture_px`. A page
     larger than the capture lost its right or bottom edge; export fails the take on it.
   - Exit codes: 6 means a tool is missing, 7 a build or launch failure (show the log tail),
     8 means `CAPTURE_LEVEL_START` never came.
4. A real iPhone can't be recorded from here. Ask the user to screen-record on the phone and
   hand over the file. It needs to run for the requested duration from the level start, and
   the user is then the player, so posts speak as a person playing.
5. On an Android phone that has a store or release build of the game installed, `flutter run`
   may uninstall it because the signatures differ. That wipes the phone's real save. Warn the
   user once before the first recording on that phone.

## Step 3: check and export

```
dart <skill>/scripts/process_video.dart export --run <run> --take <run>/work/takes/take_1.json[,take_2.json] --duration D \
  [--end-card S]                               # when the level ends inside the clip
# or a user's file:  --in FILE [--start S]     # optional: --platforms reddit,linkedin
```

**End card.** With `--end-card S`, the clip ends S seconds after the win/lose card appears, as
long as that stays within `D ± 2 s`. The card's time comes from a `CAPTURE_EVENT popup` (the
template's route observer logs every dialog), an `end card` event from a game hook, or else
`CAPTURE_LEVEL_END + clip.end_card_delay_s` (`end_card_source: estimated`). `qc.json` holds
`end_card_at` and `end_card_shown_s`. If the `end_card` check warns, the card came too early or
too late for the asked length: retune the bot so the card appears near `D − S` (an off-screen
sweep of its timing, flutter_capture.md § 1), re-record and export again.

`--platforms` exports only the ratios those platforms need. A user's file that opens on a blank
or still screen is trimmed automatically (`start` in the output says so). Check the first frame
of the contact sheet anyway, and pass `--start` when a menu is still in the cut.

1. **Checks.** Duration ±2 s, no black stretch, no still stretch, sound present (unless the
   game or source has none), smoothness, resolution, `viewport` (web: the whole page was
   captured) and `end_card` (with `--end-card`). With several takes, the script keeps
   the best one that passes: the most motion and no early loss.
2. **On exit 5 (QC failed).** Re-record, at most 2 more times. If it still fails, stop and
   report each failed check.
3. **Ratios.**
   - Portrait sources sit over a blurred copy of themselves in 16:9 and 4:5, with no black bars.
     Landscape sources get the same treatment in 9:16.
   - Look at `work/safezone_tiktok.jpg`. In portrait games the HUD row often sits under TikTok's
     top bar, and that is usually fine. Re-export with margins when the key moment, or what the
     post talks about (a step counter in a dare), is under the UI (red/orange):
     - `--tiktok-layout 240,0,0,0` clears the top bar at about 88 % size;
     - `safe` clears everything at about half size.

     Config `tiktok_layout` is the default. A per-run override goes in the report, with an offer
     to save it.
4. **Cover.** `cover.jpg` comes from the sharpest action frame (blank frames are skipped).
   There is also a `cover_<ratio>.jpg` for each export. Look at `work/cover_candidates.jpg` and
   change it with `process_video.dart cover --at T` if a better frame is there.
5. **Dull opening.** If `opening_dull` is true, also make
   `process_video.dart hookcut --peak <peak_at>`, which opens on 1.5 s of the best moment. The
   as-asked cut stays.
6. **Level shorter than the clip.** If the capture entry continued into the next level
   (`CAPTURE_EVENT next level`), say so in the assumptions. A user's file has no events: read
   the level number from the HUD at the start and at each scene change.

## Step 4: understand the clip

1. Run `extract_frames.dart --in <run>/video/raw.mp4`.
2. Read the contact sheets first, then single frames where something happens. Combine them
   with `qc.json → events` and `pacing`, and with what the code says about the level (new
   mechanic, boss, par).
3. Write `<run>/brief.md` with:
   - what happens, second by second in short;
   - the standout moment and its time;
   - the emotions it can trigger (hype, salt, suspense, surprise, laughter, "đã mắt");
   - ideas that go beyond the clip: everyday player situations, POV, memes, comparisons,
     dares, behind-the-scenes of making it in Flutter.

The brief is a source of ideas, not a limit. Only hard facts must be true.

## Step 5: trends

1. **If web search works**, check the following and note each source and the time of the check:
   - hashtags and sounds on TikTok Creative Center for the market (Games industry);
   - current slang, memes and formats;
   - events, holidays and exam seasons worth bridging to;
   - what's rising in the target subreddits, and their rules today;
   - game and game-dev topics on X and LinkedIn.

   Then update `references/trend_words.md` (each entry with its seen date and source; move dead
   ones to *Stale*) and set `run.trend_check.verified: true`. The file is shared by every game,
   so change single rows with small edits; never rewrite the whole file.
   - reddit.com can't be fetched from here. Subreddit rules come from search results, so mark
     them second-hand in `rules_checked`.
2. **Without search**, use `trend_words.md` within its freshness window and
   `viral_playbook.md`, set `verified: false`, and say so in the report.

## Step 6: write

Read `references/viral_playbook.md` (angles, hooks, voice, hashtag layers) and
`references/posts_format.md` (every field). If `social/performance_log.md` has results, rank
what worked and lean on it.

- Write **at least 3 variants per platform, each from a different angle.** Each variant names
  its video file and fills every field. Reddit gets a separate post for each of 2–3 fitting
  subreddits, each with its own posting time.
- **Voice**: an excited player telling friends, not an ad. Hype is highest on TikTok, high and
  short on X, medium on LinkedIn (tied to the making-of) and low on Reddit (a real person,
  self-deprecating).
- **Use live trend words.** Drop stale ones. Don't promise a scene the clip doesn't have.
- **Hashtags.**
  - Mix the layers: the game's own tag (every post), genre and platform, gaming community, a
    famous game only when compared, emotion, and live trends.
  - A trend outside the game needs a bridge sentence and an entry in `trend_hashtags`.
  - Dev tags (#Flutter #FlutterDev #indiedev #gamedev) go only on `tech` or
    `behind_the_scenes` angles.
- **Hard facts** go in `claims`, pointing at `facts`. Some details need no confirmation:
  mechanics you verified in the code, and what the clip shows. Business and dev-story claims
  do need it: downloads, ratings, price, release state, awards, team size, time spent, AI use,
  playtest results.
- **No links yet** (all config links null): no URL anywhere. First comments carry context or a
  question ("no store link yet"). "Coming soon" is itself a release-state claim, so use it only
  once the user has confirmed it.
- **Who played**: if a bot played, never word it as "I cleared it first try". For a user's
  file the player is unknown: don't claim it, and ask if it matters for the angle.

Save `<run>/posts.json`.

## Step 7: review

Follow `references/review_rubric.md`:

1. Knock-out round.
2. Weighted scores (hook ×3, emotion ×2, trend ×2, engagement ×2, platform fit ×2, hashtags ×1).
3. Pick the best variant.
4. One polish pass as a fast scroller (on Reddit, as an ad-hating redditor).
5. Then run:

```
dart <skill>/scripts/validate_posts.dart <run>/posts.json --render <run>/posts.md \
  --render-txt <run>/posts.txt --txt-lang <L> --local-tz <TZ>
```

`L` is `posts.report_language` from config, else the language the user writes in; `TZ` is
`posts.developer_tz` (ICT for a developer in Vietnam). `posts.txt` is the report the user reads:
plain text, only the chosen post of each platform (one per subreddit), copy-ready blocks, and a
schedule in the developer's time. The other variants stay in posts.json and posts.md.

Fix every error and run it again until it exits 0. Write `<run>/review_report.md` in the
rubric's format.

## Step 8: output

```
social/output/lv<level>_<YYYYMMDD-HHMM>/
  video/            raw.mp4  tiktok_9x16.mp4  landscape_16x9.mp4  linkedin_4x5.mp4  cover.jpg
                    [tiktok_9x16_peakfirst.mp4] [tiktok_9x16_hook.mp4]
  brief.md  posts.txt  posts.json  posts.md  review_report.md
  work/             takes/, qc.json, frames/, previews (safe to delete)
```

Optional: run `process_video.dart overlay --run <run> --text "<chosen on_screen_hook>"` to make
`tiktok_9x16_hook.mp4`. It burns the hook into the first 2 s in Be Vietnam Pro, in the upper
safe area, with emoji removed.

If `detect_project` reported `gitignore_ignores_output: false`, remind the user that the videos
can be committed by mistake (suggest the `.gitignore` line again).

End with a short summary for the user:
- `posts.txt` first: it is the report to read and copy from;
- the video paths;
- the chosen variant per platform (id, angle, the first line);
- warnings: QC, "trends not verified", subreddit rules second-hand, assumptions.

## Step 9: learn (optional)

When the user reports results (views, likes, comments, shares), append a row per post to
`social/performance_log.md`, with angle, hook and hashtags. Step 6 reads it next time.

## References

| File | Read at |
|---|---|
| `references/flutter_capture.md` | first run (reading the code, main_capture.dart, hooks), Step 2 (play modes, devices, recorders, timeouts, past failures) |
| `references/platform_specs.md` | when a limit matters; Step 5 to refresh numbers (with sources and dates) |
| `references/viral_playbook.md` | Steps 4–6: angles, hooks, emotions, voice per platform, hashtag layers, Reddit subs, posting times |
| `references/trend_words.md` | Steps 5–6: live words, formats, sounds, hashtags, calendar, stale list (update it) |
| `references/posts_format.md` | Step 6: posts.json fields |
| `references/review_rubric.md` | Step 7: knock-outs, weights, polish pass, report format, banned phrases |
| `assets/` | `main_capture.dart`, `capture_test.dart` + `integration_test_driver.dart`, `config.example.yaml`, `posts.example.json`, `performance_log.md`, `fonts/` (Be Vietnam Pro, OFL) |
