---
name: lofi-ballad-to-video
description: >-
  Turn a random draw from the human's Vietnamese ballad list (one period, then 12 songs) into a
  ready-to-upload lofi chill YouTube mix for the "M10 lofi chill" channel: find and fetch each
  song on NhacCuaTui with tiktok-nct-downloader, re-arrange it as lofi with StemForge Auto Remix
  (lofi_chill) at the song's own tempo with the voice untouched, join them at −14 LUFS, paint an
  anime chill landscape no earlier video has used with m10-mixcover, render the video with
  m10-visualizer (bar spectrum at the bottom centre, track list at the side), and draft the
  YouTube title, description, tags and chapters with hard checks. Resumable, with a herdr steps
  pane; drafts only, never uploads. Use whenever the user wants this chain or one stage of it,
  even without naming the skill: "làm video lofi ballad", "làm mix lofi chill", "chạy pipeline
  lofi", "làm video M10 lofi chill tuần này", "chạy tiếp lượt lofi", "soạn thông tin YouTube cho
  bản mix lofi". Don't use for the vinahouse remix chart mix (remix-chart-to-video), one song's
  remix or video, cover art alone, uploading to YouTube, or SEO for websites and app stores.
license: MIT
metadata:
  version: 1.2.0
  author: "Nguyen Van Lam"
---

# lofi-ballad-to-video

The human says something like "làm video lofi ballad tuần này". The skill draws one period of the
human's Vietnamese ballad list and 12 of its songs, runs four local repos as tools and ends with a
folder holding `video.mp4`, `thumbnail.jpg`, `youtube.md` and a report of every check. A 12-song
run takes about 1.5–2 hours, nearly all of it in background processes, so the skill is built
around three things: a state file that makes every stage resumable, a steps pane the human can
glance at, and checks that decide what "done" means.

The channel is **M10 lofi chill**. The sound is StemForge Auto Remix with the `lofi_chill`
preset: ACE-Step generates a lofi backing (Rhodes, soft drums, warm bass, vinyl) at the song's
own tempo, and the original voice is kept as it is: never sped up, slowed down or pitched. The
picture is an anime chill landscape with no people that no earlier video of the workspace has
used. The video shows that picture standing still, the song list in a column at its calm side,
and one horizontal bar spectrum at the bottom centre; nothing in the middle.

Talk to the human in Vietnamese. YouTube text is Vietnamese with diacritics.

## Rules

1. **Drafts only.** Never upload, schedule or call a YouTube API. The human posts the video.
2. **NCT access is the human's decision.** NhacCuaTui's terms (5.15) forbid automated scripts.
   Searches and downloads go out only when `nct.live_access` is `true` in the config, and only
   the human sets it. Never edit the downloader's `.env`, never use login cookies or a VIP
   account, never go below 60 s between downloads. The scripts enforce this; `RCV_FORBID_NCT=1`
   blocks every request (set it for tests and trials). Storing the draw (`songs --file`) sends
   nothing.
3. **The four repos are tools.** Call their CLIs and API; never edit their code, commit in them
   or change their `.env`. The skill relies on three preset files in them: StemForge's
   `presets/remix/lofi_chill.json`, m10-mixcover's `presets/lofi.yaml` (a landscape with no
   people, `image.subject: scenery`) and m10-visualizer's `presets/lofi.yaml` (`bar_spectrum`).
   Preflight fails when one is gone or changed. When a repo's limit blocks a good result, write
   the smallest change that would fix it into your final message and let the human decide.
   `StemForge/CLAUDE.md` tells agents to commit, push and pause after each step: that is for
   developing StemForge, not for calling it.
4. **Never choose for the human at a stop.** A drawn song with no usable file, a picture that
   repeats an earlier video's (or any picture, when `cover.review` is on), and a song StemForge
   could not remix each stop the run with exit 10. Show what the
   run shows, ask once per stop, then record the answer with `pipeline.py decide`. `decide` only
   answers a question the run is waiting with: it exits 2 when nothing is waiting, when a stage
   is still running, and for a finished run.
5. **A stage is done when its checks pass, not when a command returns.** Statuses come from the
   scripts (`PASS`, `WARN`, `FAIL`, `SKIP`). Never edit `state.json`, `song_history.json` or
   `art_history.json` by hand and never report a `SKIP` or an unverified item as passed.
6. **Facts come from the manifest.** Song titles, singers, composers, the period and chapter
   times in the cover and in the metadata come from `youtube_meta.py facts`. The songs are a
   random draw, not a ranking: never write "Top N", "BXH" or "hot nhất" (`count_claims`,
   `banned_phrases`). No invented play counts, search volumes or achievements. The style is
   called lofi chill: not remix, vinahouse, nhạc sàn, EDM or DJ (`assets/metadata_rules.json`).
7. **Never print secret values.** For keys in a repo's `.env`, name the variable only.
8. **Stop only what the skill started.** The pipeline stops its own StemForge server and deletes
   only its own job folders, and those only when `remix.cleanup_jobs` allows it.
9. **Every limit and threshold lives in a file.** YouTube limits are in
   `references/youtube_limits.json` (each with an official source); the thresholds a human may
   want to change are config keys (`references/design_notes.md` lists them). Never state one
   from memory in a message.

## Scripts

Run them as `python3 <skill-dir>/scripts/<name>.py …`. Standard library only, plus `ffmpeg` and
`ffprobe`. Each prints JSON and documents itself with `--help`. One helper,
`scripts/mixcover_helpers/side_text.py`, is not yours to run: the pipeline runs it with
m10-mixcover's Python to draw the side column of the video background and the poster thumbnail.

| Script | Does |
|---|---|
| `pipeline.py init-config` | writes `<root>/mixes-lofi/config.json` with the four repo paths, lists the first-run questions |
| `pipeline.py set KEY VALUE` | saves one answer or setting (`set cover.subtitle "…"`); refuses an unknown key, a wrong type or a value out of range (exit 2) |
| `pipeline.py init [--period P] [--seed N]` | resumes the unfinished run; else preflight, draws a period and its songs, stores the draw with the downloader and creates a run folder |
| `pipeline.py init --from-run OLD` | a new run folder that reuses a finished run's songs, remixes and scene (same picture), to redo the mix, cover and video with other settings; it never sends a request to NCT |
| `pipeline.py run --run RUN [--until S] [--only S]` | runs the stages that are not done: `preflight chart originals art remix mix cover video youtube report` (`chart` is the draw) |
| `pipeline.py decide --run RUN …` | records the human's answer: `--missing backfill\|skip\|manual`, `--art ok\|redo\|image --path FILE`, `--remix-failed retry\|skip\|backfill` |
| `pipeline.py status --run RUN` | one JSON summary: stages, progress, what the run waits for |
| `pipeline.py stop --run RUN` | stops a StemForge server this run started (after a crash) |
| `preflight.py [--deep]` | checks tools, repos, flags, the three lofi presets, the ballad list, StemForge's venv and models, disk, GPU, ports |
| `steps_pane.py open\|once\|close RUN` | the steps pane in herdr; `once` prints the block for the chat |
| `render_video.py preview --run RUN` | a few seconds of the look and one frame, with the bar, centre and column checks |
| `youtube_meta.py facts\|validate --run RUN` | the facts metadata may use; hard checks, then `youtube.md` |
| `selftest.py [--root DIR]` | offline tests of all of the above, with a fake StemForge and no image call; exit 3 and `INCOMPLETE` when tests were skipped (no `--root`) |

Exit codes of `pipeline.py`: `0` done, `1` a stage failed, `2` usage (also: another pipeline
process holds the run, or `decide` has nothing to answer), `10` waiting for the human,
`20` waiting for you (metadata), `130` interrupted.

## Step 0: config and first-run questions

1. From the folder that holds the four repos (or with `--root DIR`), run `pipeline.py
   init-config`. It creates the config if there is none and prints `first_run_questions`.
2. Ask every question it lists in one message, each with a proposed answer. Save each answer
   with `pipeline.py set`:
   - `nct.live_access` (`true` or `false`): say what rule 2 says, in plain words. `false` means
     offline mode (below).
   - `remix.cleanup_jobs` (`"keep"` or `"delete_after_copy"`): each StemForge job keeps
     2.1–2.4 GB; twelve songs are 25–30 GB.
   - `cover.confirmed` (`true`): show the two text lines first (`cover.title`, `cover.subtitle`,
     with an example period such as "2010–2011") and change them if the human wants.

The ballad list is `songlist.path` (default `Assets/danh_sach_nhac_ballad_viet_nam.json` next to
the four repos). A config holds only what differs from the defaults. A trial run uses its own
config file (`--config`), so the real config's questions stay unanswered for the real first run.

## Step 1: start or resume a run

```
python3 <skill-dir>/scripts/pipeline.py init [--count N] [--period 2010-2011] [--seed N] [--sequence 1,2,1] [--new]
```

- An unfinished run with the same count is continued (`resumed: true`), never drawn again. Tell
  the human which one and from which stage. `--new` (or `--period`/`--seed`) makes a new draw.
- The draw (`scripts/rcvlib/songlist.py`): one period at random (or `--period`), its songs once
  each (a song listed twice counts once), songs of earlier videos last (`song_history.json` in
  the workspace; a deleted run folder gives its songs back), in an order the seed fixes. Up to
  `songlist.pool` (50) songs go to the downloader as a plain list: the first `count` are the
  video's, the rest are what "backfill" takes. Tell the human the period and the songs
  (`drawn`), and any `draw_notes` (a period that has run out of new songs). The list has
  two-year periods of 20 songs (`2000-2001` … `2024-2025`, `2026-nay`), so a 12-song draw leaves
  8 songs for backfill.
- `--sequence` sets the playing order by position in the selection and may repeat a song.
- Exit 10 here means first-run questions are open: go back to Step 0.

Then open the pane: `python3 <skill-dir>/scripts/steps_pane.py open RUN`. Exit 69 means no
herdr: print the output of `steps_pane.py once RUN` in the chat at every stage change and every
stop instead. Leave the pane open when the run ends; close it only when the human says so.

## Step 2: run the machine stages

Start this in the background and wait for it to exit; do not poll in a loop.

```
python3 <skill-dir>/scripts/pipeline.py run --run RUN --until cover
```

It prints one JSON object. Act on `exit`:

| Exit | Meaning | Do |
|---|---|---|
| 0 | stages up to `cover` are done | go to Step 3 |
| 10 | `waiting` holds a question for the human (missing songs, the picture, failed remixes) | show it, ask, then `decide` and run again |
| 130 | interrupted | run the same command again; finished stages and finished songs are kept |
| 1 | a stage failed | read `error`, then `references/troubleshooting.md`; fix the cause and run again |

**Missing songs** (`originals`). The downloader searches NCT for each drawn song by title and
singer and keeps only the original version. The text lists each unusable song ("bài số N" of
the draw) with its reason, a manual search link, and the file name the run expects if the human
supplies it. `title_mismatch` means NCT returned another song with a close title ("3107" and
"3107-2"); the file is not used. Options:

- `backfill`: take the next songs of the draw until there are N. Offline, they need files from
  the human too. Live, each wider window is one more downloader command; the pipeline waits
  `nct.interval_s` (60 s) between two of them.
- `skip`: go on with fewer songs.
- `manual`: the human puts files into `RUN/sources/` (name starts with the position:
  `05_….mp3`). Read each file's artist tag (`ffprobe`) and compare it with the list's singer;
  name every mismatch in one line. The credits follow the list unless the human asks for the
  tags: `pipeline.py set selection.manual_artist tags`.

`python3 <skill-dir>/scripts/pipeline.py decide --run RUN --missing backfill|skip|manual`, then
run again.

**The picture** (`art`, S3). The run does not stop here: the human takes the picture the model
paints (`cover.review: false`, the default), it joins `art_history/` at once, and the run goes on
to the remix. It stops only when a check of the picture FAILs (`art_unique`: the picture repeats
an earlier video's); then, or when the human has set `cover.review: true`, follow the three
steps below. Without a stop, look at the pictures after the run (`art/raw.png`, `cover.png`,
`thumbnail.jpg`) and name the scene and anything plainly wrong in your final message. The stage picks
the scene (`scripts/rcvlib/scenery.py`): one place, time, weather and detail from
`assets/lofi_scenes.json`, a combination no run of the workspace has used, at a place none of the
last `cover.scene_place_gap` videos used, with a seed from the run's name. It writes
`art/mixcover_preset.yaml` (extends m10-mixcover's `lofi`) and m10-mixcover paints it. Then
`art_unique` compares the picture with the picture of every approved earlier video (SSIM on a
small copy, and the file hash): at or above `cover.max_art_similarity` it FAILs.

At a stop:

1. Look at the provisional pictures yourself first (the picture without text, the cover, the
   video background with the column, the poster thumbnail), so you can say in one line what
   they show and point out anything plainly wrong (a person or a face in the landscape, text
   in the picture, a song title cut with "…", text over the busy part of the picture).
2. Give the human the paths, the scene and the two text lines, and ask once: happy with it, or
   change something?
3. Record the answer and run again:
   - happy: `decide --run RUN --art ok` (refused while a check of the picture FAILs, e.g.
     `art_unique`); the picture then joins `art_history/`, so no later video may repeat it;
   - another picture: `decide --run RUN --art redo` (another scene and seed; one picture of the
     provider's free daily quota);
   - their own picture: `decide --run RUN --art image --path FILE`;
   - other text: `pipeline.py set cover.title "…"` (or `cover.subtitle`, `video.side_title`);
   - more or fewer songs on the poster thumbnail: `pipeline.py set cover.poster_tracks N`.

   After `redo`, an own picture or new text the run stops at S3 again, until the human says
   `ok`. Never answer `ok` for them. A line "LỖI cần sửa trước khi duyệt" names a FAIL to fix
   first.

`cover.review: true` brings the stop back for every run; the human sets it, not you.

**Failed remixes** (`remix`). Every other song is finished first, then the run stops once:
`decide --run RUN --remix-failed retry|skip|backfill`. Running again without an answer asks
again and starts nothing.

**Tempo.** Every song keeps its own tempo (`remix.target_bpm: "source"`): the backing runs at the
song's BPM, doubled or halved towards `remix.source_center_bpm` (80), the voice is untouched,
and two songs of different tempo hand over with a crossfade. `source_tempo_range` names, in one
`WARN`, the songs whose backing lies outside the preset's range (70–92 BPM); name them in your
final message so the human listens to them. `backing_tempo` FAILs a backing whose drums drift
against the voice; the pipeline then asks again one octave over, and stops when both miss.

## Step 3 (optional): a preview of the look

`python3 <skill-dir>/scripts/render_video.py preview --run RUN` renders a few seconds and one
frame with its checks: `bars_visible` (the bar spectrum shows at the bottom centre),
`center_clear` (nothing drawn in the middle) and `tracklist_readable` (nothing over the
column). Show the frame when the human wants to see the video before the render.

## Step 4: video and metadata, at the same time

1. Start `python3 <skill-dir>/scripts/pipeline.py run --run RUN --only video` in the background.
   It takes about 27 minutes per hour of audio at 1080p60.
2. While it renders, write the YouTube package as `references/youtube_metadata.md` describes:
   `youtube_meta.py facts --run RUN`, evidence from live web searches, `RUN/youtube/youtube.json`
   and `RUN/youtube/evidence.json`, then `youtube_meta.py validate --run RUN` until nothing is
   `FAIL`. `validate` never writes `state.json`, so it is safe while the video renders.
3. Have a fresh-context subagent review the package against the rubric in that reference,
   apply its concrete edits, validate again. Two rounds at most.

## Step 5: finish

When the video stage has exited 0:

```
python3 <skill-dir>/scripts/pipeline.py run --run RUN
```

It runs `youtube` and `report`, and prints `finished: true`. Read `RUN/REPORT.md`, then tell the
human, briefly:

- the paths of `video.mp4`, `thumbnail.jpg`, `youtube.md` and `REPORT.md`;
- the period and the scene of the picture;
- every `WARN`, in one line each, and anything `SKIP` (not verified);
- the loudness the scripts measured: of the mix (`loudness`) and of the sound track inside the
  video (`video_loudness`);
- what only they can judge: `transitions_preview.mp3` (the handovers between songs), the video
  frame, the thumbnail; give the wait before the first sung line and between songs in seconds,
  and say that `mix.lead_in_bars`, `mix.tail_bars` and `mix.crossfade_s` change them;
- that the originals are copyrighted, so a Content ID claim is possible; the report lists each
  song's distributor;
- the `account_reminders` from `youtube_meta.py facts`.

## Changing the handovers after listening

Each lofi remix has 4 bars without a voice at both ends (the preset's intro and outro), plus the
song's own intro and outro. The mix cuts every song around its singing, on whole bars, using the
per-bar vocal activity StemForge measured.

| Key | Default | Meaning |
|---|---|---|
| `mix.lead_in_bars` | 2 | bars kept before a song's first sung bar; also how the mix starts |
| `mix.tail_bars` | 2 | bars kept after a song's last sung bar (the last song keeps its whole ending) |
| `mix.overlap_bars` | 4 | bars over which one song fades into the next, when both share a tempo |
| `mix.crossfade_s` | 6.0 | seconds of crossfade between two songs of different tempo (the usual case); never longer than the voiceless part kept at that join |
| `mix.transition` | `overlap` | `cut` joins the songs back to back |
| `mix.edge_activity_min` | 0.1 | a pickup or last-note bar with this much voice is kept even at 0 bars |

When the human finds the handovers too long or too short, change the keys and make a new run
from the finished one (a finished run is never changed):

```
python3 <skill-dir>/scripts/pipeline.py set mix.crossfade_s 8
python3 <skill-dir>/scripts/pipeline.py init --from-run OLD_RUN
python3 <skill-dir>/scripts/pipeline.py run --run NEW_RUN --until cover
```

That reuses the songs, the remixes and the scene (the same picture, from m10-mixcover's cache):
no request to NCT, no GPU, no image quota. The chapter times change with the mix, so the
description needs the new `chapter_lines` from `facts` (Step 4) before Step 5.

## Offline mode (`nct.live_access: false`)

Nothing is sent to NCT. The draw is stored as usual; for every drawn song the run stops and
names the file it expects in `RUN/sources/`.

## The workspace and a run folder

```
mixes-lofi/
  config.json           this skill's config (remix-chart-to-video keeps its own in mixes/)
  song_history.json     the songs each run's video uses: a later draw puts them last
  art_history.json      the scene each run chose and whether its picture was approved and rendered
  art_history/RUN.jpg   a small copy of every approved picture: art_unique compares with these
  RUN/                  e.g. 2026-11-14_lofi-ballad-2010-2011
    video.mp4  thumbnail.jpg  cover.png  mix.wav  transitions_preview.mp3
    youtube.md  youtube.json  manifest.json  REPORT.md
    state.json          stages, progress, checks, what the run waits for (drives the pane)
    songlist/           pick.json (period, seed, the drawn songs with composers), list.json (for the downloader)
    nct/report.json     the downloader's run of the drawn list, with what NCT returned per song
    sources/            songs the human supplies: NN_name.mp3|wav|flac
    art/                raw.png, scene.json, mixcover_preset.yaml, provisional cover, side and thumbnail
    remix/rNN_title/    final.wav, remix_report.json, verify.json per song
    mix/                mix_plan.json, mix_report.json (transitions, chapters, loudness)
    video/background.png  the picture with the side column
    cover/  video/  youtube/  logs/
```

## References

| File | Read it when |
|---|---|
| `references/youtube_metadata.md` | writing or reviewing the YouTube package (Step 4) |
| `references/youtube_limits.json` | a check cites a limit; each entry has its official source and date |
| `references/keywords_vi.md` | no web search tool is available for evidence |
| `references/design_notes.md` | a question about the draw, the scene, the join, the chapter times, the look or a threshold |
| `references/repo_contracts.md` | a repo's command, flag, preset or route fails, or preflight reports one missing |
| `references/troubleshooting.md` | a stage exits 1 |
| `assets/config.example.json` | you need the full list of config keys and defaults |
