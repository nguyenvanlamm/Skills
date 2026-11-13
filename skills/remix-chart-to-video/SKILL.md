---
name: remix-chart-to-video
description: >-
  Turn NhacCuaTui's "Top 50 Nhạc Remix Việt" chart into a ready-to-upload YouTube mix for the
  M10 Music channel: pick the top N songs (default 12) with tiktok-nct-downloader and fetch their
  originals, remix each to Vinahouse with StemForge Auto Remix (vinahouse) at the song's own
  tempo, join them into one long mix at −14 LUFS, draw cover and thumbnail with m10-mixcover, render the video with
  m10-visualizer, and draft the YouTube title, description, tags and chapters with hard checks.
  Resumable, with a herdr steps pane; drafts only, never uploads. Use whenever the user wants
  this chain or one stage of it, even without naming the skill: "làm video top 12 remix", "chạy
  pipeline remix", "làm mix nhạc remix tuần này", "ghép mix vinahouse từ BXH NCT", "chạy tiếp lượt
  remix", "soạn thông tin YouTube cho bản mix", "make this week's remix mix video". Don't use for
  one song's remix or visualizer video, cover art alone, uploading to YouTube, or SEO for
  websites and app stores (search-optimizer, aso-marketing).
license: MIT
metadata:
  version: 1.9.0
  author: "Nguyen Van Lam"
---

# remix-chart-to-video

The human says something like "làm video top 12 remix tuần này". The skill runs four local repos
as tools and ends with a folder holding `video.mp4`, `thumbnail.jpg`, `youtube.md` and a report of
every check. A 12-song run takes about 1.5–2 hours, nearly all of it in background processes, so
the skill is built around three things: a state file that makes every stage resumable, a steps
pane the human can glance at, and checks that decide what "done" means.

Talk to the human in Vietnamese. YouTube text is Vietnamese with diacritics.

## Rules

1. **Drafts only.** Never upload, schedule or call a YouTube API. The human posts the video.
2. **NCT access is the human's decision.** NhacCuaTui's terms (5.15) forbid automated scripts.
   Requests go out only when `nct.live_access` is `true` in the config, and only the human sets
   it. Never edit the downloader's `.env`, never use login cookies or a VIP account, never go
   below 60 s between downloads. The scripts enforce this; `RCV_FORBID_NCT=1` blocks every
   request (set it for tests and trials).
3. **The four repos are tools.** Call their CLIs and API; never edit their code, commit in them
   or change their `.env`. When a repo's limit blocks a good result, write the smallest change
   that would fix it into your final message and let the human decide. `StemForge/CLAUDE.md`
   tells agents to commit, push and pause after each step: that is for developing StemForge,
   not for calling it.
4. **Never choose for the human at a stop.** A top-N song with no usable original, the
   picture after stage S3, and a song StemForge could not remix each stop the run with exit 10.
   Show what the run shows, ask once per stop, then record the answer with `pipeline.py decide`.
   `decide` only answers a question the run is waiting with: it exits 2 when nothing is
   waiting, when a stage is still running, and for a finished run.
5. **A stage is done when its checks pass, not when a command returns.** Statuses come from the
   scripts (`PASS`, `WARN`, `FAIL`, `SKIP`). Never edit `state.json` by hand and never report a
   `SKIP` or an unverified item as passed.
6. **Facts come from the manifest.** Song titles, artists, ranks, the chart date and chapter
   times in the cover and in the metadata come from `youtube_meta.py facts`. No invented play
   counts, search volumes or achievements. "Top N" only when `may_say_top_n` is true. The style
   is called vinahouse and nothing else (`banned_phrases` in `assets/metadata_rules.json`).
7. **Never print secret values.** For keys in a repo's `.env`, name the variable only.
8. **Stop only what the skill started.** The pipeline stops its own StemForge server and
   deletes only its own job folders, and those only when `remix.cleanup_jobs` allows it.
9. **Every limit and threshold lives in a file.** YouTube limits are in
   `references/youtube_limits.json` (each with an official source); the thresholds a human may
   want to change are config keys (`references/design_notes.md` lists them, and the fixed
   measuring tolerances the scripts use). Never state one from memory in a message.

## Scripts

Run them as `python3 <skill-dir>/scripts/<name>.py …`. Standard library only, plus `ffmpeg` and
`ffprobe`. Each prints JSON and documents itself with `--help`. One helper,
`scripts/mixcover_helpers/side_text.py`, is not yours to run: the pipeline runs it with
m10-mixcover's Python to draw the side column of the video background with that repo's
Pillow, fonts and colours.

| Script | Does |
|---|---|
| `pipeline.py init-config` | writes `<root>/mixes/config.json` with the four repo paths, lists the first-run questions |
| `pipeline.py set KEY VALUE` | saves one answer or setting (`set video.look cover`); refuses an unknown key, a wrong type or a value out of range (exit 2) |
| `pipeline.py init` | preflight + chart, then creates a run folder or resumes the unfinished one of the same chart date |
| `pipeline.py init --from-run OLD` | a new run folder that reuses a finished run's songs, remixes and chosen picture (its own copies), to redo the mix, cover and video with other settings; it never sends a request to NCT |
| `pipeline.py run --run RUN [--until S] [--only S]` | runs the stages that are not done: `preflight chart originals art remix mix cover video youtube report` |
| `pipeline.py decide --run RUN …` | records the human's answer: `--missing backfill\|skip\|manual`, `--art ok\|redo\|image --path FILE`, `--center redo`, `--remix-failed retry\|skip\|backfill` |
| `pipeline.py status --run RUN` | one JSON summary: stages, progress, what the run waits for |
| `pipeline.py stop --run RUN` | stops a StemForge server this run started (after a crash) |
| `preflight.py [--deep]` | checks tools, repos, flags, StemForge's venv and models, disk, GPU, ports |
| `steps_pane.py open\|once\|close RUN` | the steps pane in herdr; `once` prints the block for the chat |
| `render_video.py preview --run RUN` | short clips and one frame of each video look, for the first-run choice |
| `youtube_meta.py facts\|validate --run RUN` | the facts metadata may use; hard checks, then `youtube.md` |
| `selftest.py [--root DIR]` | offline tests of all of the above, with a fake StemForge; exit 3 and `INCOMPLETE` when tests were skipped (no `--root`) |

Exit codes of `pipeline.py`: `0` done, `1` a stage failed, `2` usage (also: another pipeline
process holds the run, or `decide` has nothing to answer), `10` waiting for the human,
`20` waiting for you (look preview or metadata), `130` interrupted.

## Step 0: config and first-run questions

1. From the folder that holds the four repos (or with `--root DIR`), run `pipeline.py
   init-config`. It creates the config if there is none and prints `first_run_questions`.
2. Ask every question it lists except `video.look`, in one message, each with a proposed
   answer. Save each answer with `pipeline.py set`:
   - `nct.live_access` (`true` or `false`): say what rule 2 says, in plain words. `false` means
     offline mode (below).
   - `remix.cleanup_jobs` (`"keep"` or `"delete_after_copy"`): each StemForge job keeps
     2.1–2.4 GB; twelve songs are 25–30 GB.
   - `cover.confirmed` (`true`): show the three text lines first (`cover.title`,
     `cover.title_inexact` for a mix that is not exactly ranks 1–N, `cover.subtitle`) and
     change them if the human wants.
3. `video.look` is asked later, with pictures (Step 3).

A config holds only what differs from the defaults, so a later version of the skill can change a
default. A trial run uses its own config file (`--config`), so the real config's questions stay
unanswered for the real first run.

## Step 1: start or resume a run

Read the request: number of songs (default `selection.count`), where the chart comes from, and
whether the human means an unfinished run.

```
python3 <skill-dir>/scripts/pipeline.py init [--count N] [--html FILE | --nct-run-id ID] [--sequence 1,2,1] [--new]
```

- The chart comes from, in this order: `--nct-run-id` (a saved run), `--html` (a chart page the
  human saved from the browser, no request), a run the downloader saved today, a live fetch
  (3 requests, needs `nct.live_access: true`).
- `resumed: true` means an unfinished run of the same chart date exists and is continued. Tell
  the human which one and from which stage. `--new` forces a new folder. A finished run is
  never changed; a redo is a new run.
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
| 0 | stages up to `cover` are done | go to Step 4 |
| 10 | `waiting` holds a question for the human (missing songs, the picture, failed remixes) | show it, ask, then `decide` and run again |
| 20 | `need` names work for you | the look choice (Step 3) |
| 130 | interrupted | run the same command again; finished stages and finished songs are kept |
| 1 | a stage failed | read `error`, then `references/troubleshooting.md`; fix the cause and run again |

**Missing songs** (`originals`). The text lists each unusable rank with its reason, a manual
search link, and the file name the run expects if the human supplies the song. Options:

- `backfill`: take the next ranks until there are N songs. Offline, the wider window needs files
  from the human too. Live, each wider window is one more downloader command; the pipeline
  waits `nct.interval_s` (60 s) between two of them, so the pane may show "chờ … trước lệnh
  tải kế tiếp".
- `skip`: go on with fewer songs.
- `manual`: the human puts files into `RUN/sources/` (name starts with the rank: `05_….mp3`).
  Read each file's artist tag (`ffprobe`) and compare it with the chart's artist; name every
  mismatch in one line. The credits follow the chart unless the human asks for the tags:
  `pipeline.py set selection.manual_artist tags` (the title stays the chart's). A file
  replaced under the same name counts as a new song and is remixed again.

`python3 <skill-dir>/scripts/pipeline.py decide --run RUN --missing backfill|skip|manual`, then
run again. While the human thinks, nothing else can proceed at this stage; later stages keep the
songs that are fine.

**The picture** (`art`, S3). Every run stops here, before the long remix stage, so the human
sees the picture while it is still cheap to change. The text names the files: the provisional
cover (the picture with the title, the subtitle and the song list; the times come later, from
the finished mix), the thumbnail (a poster: the cover's title in large letters above the
first `cover.poster_tracks` songs and "+ N bài khác", made to be read at the small size
YouTube shows it), the video background (the same picture with a column at the side away
from the DJ: the title `video.side_title`, "REMIX NHẠC HOT TIKTOK" by default, in big slanted
poster letters, above the song list numbered in playing order, no artist, no time; the logo and ring go in the
centre), the picture without text, and the video's centre: the colours and shape of the ring
and the particles chosen for this video (below), with one frame of it on the video background
when `video.look` is `visualizer`.

**The centre** differs from one video to the next. The M10 logo stays; the ring's colours,
its shape and the particles rotate through 210 combinations (`assets/center_styles.json`),
none twice before all were used, and never the same palette, colour family, ring shape or
particle style as the videos just before (`center_history.json` beside the config remembers
them). The stop names the combination and the frame `art/provisional_center.png`. A
`center_preview` `WARN` means the ring came near the side column in that frame: say so.

1. Look at the provisional pictures yourself first, so you can say in one line what they show
   and point out anything plainly wrong (a distorted face or hands, text running over the DJ,
   a song title cut with "…").
2. Give the human the paths and the two text lines, and ask once: happy with it, or change
   something?
3. Record the answer and run again:
   - happy: `decide --run RUN --art ok`;
   - another picture: `decide --run RUN --art redo` (a new seed; one picture of the provider's
     free daily quota);
   - their own picture: `decide --run RUN --art image --path FILE`;
   - another centre (ring colours and shape, particles; the picture stays):
     `decide --run RUN --center redo`; one axis kept for every video:
     `pipeline.py set video.center_palette NAME` (`center_shape`, `center_particles`; `null` frees it);
     the old fixed centre: `pipeline.py set video.center fixed`;
   - other text: `pipeline.py set cover.title "…"` (or `cover.title_inexact`, `cover.subtitle`);
   - the old thumbnail (the cover scaled down, with the full tracklist):
     `pipeline.py set cover.thumb_style tracklist`; more or fewer songs on the poster:
     `pipeline.py set cover.poster_tracks N`.

   After `redo`, another centre, an own picture or new text the run stops at S3 again with the new result, until
   the human says `ok`. Never answer `ok` for them. When the text of the stop has a line
   "LỖI cần sửa trước khi duyệt" (the title and list do not fit the column), fix that first:
   an `ok` would only fail the stage. When it says the title on the video background differs
   from the cover's, tell the human and ask which one they want on both.
4. On a first run `video.look` is still unset: render the look previews now (Step 3) and ask
   both things in the same message, so the human is interrupted once.

`cover.review: false` turns the stop off for unattended runs; the human sets it, not you.

**Failed remixes** (`remix`). Every other song is finished first, then the run stops once:
`decide --run RUN --remix-failed retry|skip|backfill`. Running again without an answer asks
again and starts nothing. `retry` makes a new StemForge job for a remix that finished but
failed its checks (retrying that job would return the same file) and resumes a job that
failed on the way. A job that stands still for `remix.stall_s` is cancelled, waited for and
retried by the pipeline itself; one that does not stop within `remix.cancel_wait_s` becomes a
failed remix (`stalled`). After `skip` or `backfill` the rank stays out, unless the human puts
another file for it into `RUN/sources/` afterwards.

**Tempo.** By default every song keeps its own tempo (`remix.target_bpm: "source"`): the voice
is never sped up or slowed down, the backing runs at the song's BPM (doubled or halved towards
`remix.source_center_bpm`), and two songs of different tempo hand over with a crossfade. The
`source_tempo_range` check names, in one `WARN`, the songs whose backing lies outside the
preset's range (124–140 BPM); name them in your final message so the human listens to them.
StemForge sometimes cannot generate a backing at a fast tempo and keeps its best attempt anyway;
`backing_tempo` measures that (`FAIL`: the drums drift against the voice), and the pipeline asks
again at the song's tempo one octave over (an 89.5 BPM song goes to 179 first, then to 89.5).
When both octaves miss, the song stops as a failed remix.
`pipeline.py set remix.target_bpm 128` gives one tempo for the whole mix and beat-matched
overlaps instead, at the cost of stretching the voice; a song with a `vocal_stretch` warning was
then sped up or slowed down a lot. It is not a failure; name it so the human listens to it.

## Step 3: the look (first run only)

When `video.look` is unset (the run exits 20 before `remix`, or it has just stopped at S3 for the picture):

1. `python3 <skill-dir>/scripts/render_video.py preview --run RUN` renders a few seconds of each
   look and names one frame of each.
2. Look at both frames yourself, then show the human the two paths with one line each.
   Propose `visualizer` first: it is the channel's look in m10-visualizer's own output.
   - `visualizer`: the DJ picture with the logo in the centre, growing and shrinking on the
     beat, the spectrum ring and particles around it (their colours and shape differ per
     video, see "The centre" above), and at the far side, away from the DJ,
     a column with the title `video.side_title` above the numbered song list
     (`video.tracklist: side`; `none` leaves the picture bare).
   - `cover`: the cover with the wide tracklist, readable, no logo; a still picture.

   In both looks the background stands still (`video.background_still: true`). Set it to
   `false` only when the human asks for the shake and beat zoom of m10-visualizer's preset.
3. Say that it is a preview on provisional material when `provisional` is true.
4. `pipeline.py set video.look cover|visualizer`, then run Step 2 again.

The two looks exist because m10-visualizer always draws its logo at the centre of the frame, on
top of the tracklist m10-mixcover draws on a cover. For the `visualizer` look the video
background has a side column the ring cannot reach (`video.side_column_width`), on the side
opposite the DJ (m10-mixcover's face detection). At its top the title `video.side_title`
("remix nhạc hot tiktok" by default), upper case in Anton, a condensed display face
(`assets/fonts/`, OFL), slanted, each line scaled to fill the column, lines white and lime in
turn with a solid pink copy behind; below it one line per song in playing order, `01  Title`: the
number in lime, the title in white, no artist and no time (those stay on the cover, in the
YouTube description and in its chapters). The list keeps its size and the title takes the
room left, so a long list makes the title smaller. A song title too long for the column is
cut with "…" (`video_background_warnings`); a title and list that only fit below
`video.side_title_min_size` or `video.side_track_min` fail `video_background`.
`references/design_notes.md` has the details.

## Step 4: video and metadata, at the same time

1. Start `python3 <skill-dir>/scripts/pipeline.py run --run RUN --only video` in the background.
   It takes about 27 minutes per hour of audio at 1080p60.
2. While it renders, write the YouTube package as `references/youtube_metadata.md` describes:
   `youtube_meta.py facts --run RUN`, evidence from live web searches, `RUN/youtube/youtube.json`
   and `RUN/youtube/evidence.json`, then `youtube_meta.py validate --run RUN` until nothing is
   `FAIL`. `validate` never writes `state.json`, so it is safe while the video renders;
   `pipeline.py decide` is not, and is refused until the render has ended.
3. Have a fresh-context subagent review the package against the rubric in that reference, apply
   its concrete edits, validate again. Two rounds at most.

## Step 5: finish

When the video stage has exited 0:

```
python3 <skill-dir>/scripts/pipeline.py run --run RUN
```

It runs `youtube` (the same validation) and `report`, and prints `finished: true`. Read
`RUN/REPORT.md`, then tell the human, briefly:

- the paths of `video.mp4`, `thumbnail.jpg`, `youtube.md` and `REPORT.md`;
- every `WARN`, in one line each, and anything `SKIP` (not verified);
- the loudness the scripts measured: of the mix (`loudness`: brought to `mix.target_lufs`
  by one gain; when the true peak kept it below the target, the check says so) and of the
  sound track inside the video (`video_loudness`);
- what only they can judge: `transitions_preview.mp3` (the handovers between songs), the video
  frame, the thumbnail; give the wait before the first sung line and between songs in seconds, and say
  that `mix.lead_in_bars`, `mix.tail_bars` and `mix.overlap_bars` change them;
- that the originals are copyrighted, so a Content ID claim is possible; the report lists each
  song's distributor;
- the `account_reminders` from `youtube_meta.py facts`: a video over 15 minutes and a custom
  thumbnail each need a verified channel, which the skill cannot see.

## Changing the handovers after listening

Each remix has several bars without a voice at both ends (StemForge's 8-bar DJ intro and outro,
plus the song's own intro and outro). The mix cuts every song around its singing, on whole
bars, using the per-bar vocal activity StemForge measured. Three config keys set the result
(4 bars are 7.5 s at 128 BPM):

| Key | Default | Meaning |
|---|---|---|
| `mix.lead_in_bars` | 4 | bars kept before a song's first sung bar; also how the mix starts |
| `mix.tail_bars` | 4 | bars kept after a song's last sung bar (the last song keeps its whole ending) |
| `mix.overlap_bars` | 4 | bars over which one song fades into the next, when both share a tempo |
| `mix.crossfade_s` | 4.0 | seconds of crossfade between two songs of different tempo; never longer than the voiceless part kept at that join, so no voice is under it |
| `mix.transition` | `overlap` | `cut` joins the songs back to back, nothing of the two beats sounds together; the voiceless time is then `lead_in + tail` bars |
| `mix.edge_activity_min` | 0.1 | a bar right before the first sung bar (a pickup) or right after the last (the last note) with this much voice is kept even at `lead_in_bars: 0` / `tail_bars: 0` |

Bars are counted at each song's own tempo. The time without a voice between two songs is
`lead_in + tail − overlap` bars when they overlap on the beat, and `lead_in + tail` bars minus
the crossfade when their tempos differ (the usual case with `remix.target_bpm: "source"`);
`REPORT.md` and the `mix` checks state it in seconds, with the wait before the first sung
line. `null` for the first two keys keeps whole songs; use `overlap_bars: 8` with that.
A fade never reaches into a voice: with a lead-in or tail shorter than `crossfade_s` the
crossfade is shortened to it (the check says "rút còn"), and with none kept the two songs are
joined straight, as with `cut`. A handover whose check is `WARN` with "hai giọng hát chồng
nhau" has two voices at once; name it so the human listens to it.

When the human finds the start or the handovers too long or too short, change the keys and make
a new run from the finished one (a finished run is never changed):

```
python3 <skill-dir>/scripts/pipeline.py set mix.lead_in_bars 2
python3 <skill-dir>/scripts/pipeline.py init --from-run OLD_RUN
python3 <skill-dir>/scripts/pipeline.py run --run NEW_RUN --until cover
```

That reuses the songs and the remixes: no request to NCT, no GPU, a few seconds. Let the human
listen to the new `transitions_preview.mp3` before the video is rendered again. The chapter
times change with the mix, so the description needs the new `chapter_lines` from `facts`
(Step 4) before Step 5.

## Offline mode (`nct.live_access: false`)

Nothing is sent to NCT. The chart comes from `--html FILE` (the human opens nhaccuatui.com,
"Bảng Xếp Hạng" → "Top 50 Nhạc Remix Việt", and saves the page as HTML) or from a saved run
(`--nct-run-id`). Originals the downloader already has are used; for the rest the run stops and
names the file it expects for each rank in `RUN/sources/`.

## A run folder

```
RUN/
  video.mp4  thumbnail.jpg  cover.png  mix.wav  transitions_preview.mp3
  youtube.md  youtube.json  manifest.json  REPORT.md
  state.json            stages, progress, checks, what the run waits for (drives the pane)
  nct/report.json       the chart as the downloader reported it
  sources/              songs the human supplies: NN_name.mp3|wav|flac
  art/                  the text-free AI picture, a provisional cover and video background,
                        the video's centre (center.json, center_preset.yaml, center_logo.png)
  remix/rNN_title/      final.wav, remix_report.json, verify.json per song
  mix/                  mix_plan.json, mix_report.json (transitions, chapters, loudness)
  video/background.png  the picture with the side column: title and song list (`visualizer` look)
  cover/  video/  youtube/  logs/
```

## References

| File | Read it when |
|---|---|
| `references/youtube_metadata.md` | writing or reviewing the YouTube package (Step 4) |
| `references/youtube_limits.json` | a check cites a limit; each entry has its official source and date |
| `references/keywords_vi.md` | no web search tool is available for evidence |
| `references/design_notes.md` | a question about the join, the chapter times, the looks, the centre's rotation or a threshold |
| `references/repo_contracts.md` | a repo's command, flag or route fails, or preflight reports one missing |
| `references/troubleshooting.md` | a stage exits 1 |
| `assets/config.example.json` | you need the full list of config keys and defaults |
