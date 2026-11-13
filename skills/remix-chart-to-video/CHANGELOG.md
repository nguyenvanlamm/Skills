# Changelog

## v1.9.0 — 2026-11-13

### Added

- **The centre of the `visualizer` look differs per video.** Every video so far had the same
  lime ring, pink caps and particles. The M10 logo stays; the ring's colours, its shape and the
  particles now rotate through 210 combinations (10 palettes in 7 colour families, 7 ring
  shapes, 3 particle styles, `assets/center_styles.json`), the least recently used first: no
  combination comes back before all 210 were used, and no video shares its palette, colour
  family, ring shape or particle style with the ones just before it (`video.center_*_gap`). The
  logo's lime parts take the ring's colour. A palette close to the picture's own colour goes
  last. `center_history.json` beside the config remembers what each run used; the videos made
  before count as the classic centre.
- **The picture stop shows the centre**: its name and one frame on the video background
  (`art/provisional_center.png`), checked against the side column (`center_preview`).
  `decide --center redo` gives another one (another palette and shape; the picture stays).
- Config keys `video.center` (`rotate` | `fixed`: the old centre), `video.center_palette`,
  `center_shape`, `center_particles` (pin an axis), `center_tint_logo` and the four gaps.
- Selftest `center` (the rotation over a full cycle, the history, `set`) and `center_render`
  (every shape read by m10-visualizer without a warning and no wider than the default ring,
  the logo's colour, the stop, `redo`, `fixed`).

### Changed

- The `visualizer` look passes the run's own preset, logo and seed to m10-visualizer
  (`--preset`, `--logo`, `--seed`); `side_geometry` measures the ring of that preset.
- A run made with `--from-run` keeps the old run's centre.
- The art stage's signature includes the centre, so the human approves both at S3.

## v1.8.0 — 2026-11-11

An independent review after the first full 12-song run: the run's own products, the code, and
the documents against the code. The straight path worked; the failures were on the paths the
run never took (a job that stands still, an interrupt, `decide`, `--from-run`, a config change
in the middle of a run), which the selftest did not cover either.

### Fixed

- **A job that stood still ended the whole remix stage.** The pipeline cancelled it, slept
  3 s and retried, but StemForge cancels at the next stage boundary and refuses to retry a
  running job (409), so the error left the song loop: the other songs were not remixed and the
  stuck song never reached the failed-remix stop. Now the pipeline waits for a finished status
  (`remix.cancel_wait_s`, 120), restarts a server it started itself when the job hangs inside
  a stage, and otherwise reports the song as a failed remix (`stalled`).
- **`decide --remix-failed retry` re-downloaded the same file.** A remix that finished but
  failed the skill's checks is `completed` on the server, and retrying it reuses every stage.
  Such a song now gets a new job.
- **One failed request ended the stage with a traceback.** A read is tried three times; an
  error on one song's upload, download or measurement makes that song a failed remix (`api`)
  while the server is up, and ends the stage with one JSON error when the server is gone.
- **A server the skill started was left running** when the readiness check failed right after
  the start. It is stopped on every error now. A server counts as the skill's own only when
  its command line is StemForge's `run.py` on the recorded port, started in the StemForge
  repo: a reused PID is no longer signalled.
- **`decide` could change a finished run, answer a question nobody asked, or lose its answer**
  to a stage running at the same time. It takes the run's lock and exits 2 in all three cases.
- **Backfill broke the 60 s between two NCT downloads.** Each wider window is a new downloader
  command, and the downloader forgets its interval between commands. The pipeline now waits
  `nct.interval_s` after the previous command.
- **A crossfade ran over two voices** when the kept lead-in or tail was shorter than
  `mix.crossfade_s` (`lead_in_bars: 2` at 172 BPM is 2.8 s), and the report clamped the
  negative gap to "0.0 s". A fade is now held to the voiceless part kept at the join and
  becomes a straight join when nothing was kept; a negative gap is a `WARN` that says so.
- **A timed-out tool crashed with `TypeError`** (captured output is bytes after a timeout).
- **Ctrl-C during the mix was recorded as a failed stage** (exit 1). It is exit 130 for every
  stage, and resuming an interrupted remix no longer uses up one of its attempts.
- **`--from-run` pointed at the old run's picture.** The new run keeps its own copy, is marked
  as a run that sends nothing to NCT, and drops the old answers when `--count` changes.
- **A file replaced under the same name in `sources/` was never remixed again**, and a label or
  artist change left the old chapter lines in the mix report.
- **A changed check threshold or thumbnail setting cost a video render.** The video's
  fingerprint uses the content of the mix and the picture, not their file times.
- **`pipeline.py set` stored anything.** `set nct.interval_s 60s` left a config no command
  could load. Values are checked against the key's type and range; `cover.image` and
  `cover.dry_run`, which the error messages recommend, are now keys.
- **A run of one or two songs could never finish** (`chapter_rules` FAIL with nothing to fix).
  It is a `WARN`: YouTube makes no chapters below three timestamps.
- **YouTube checks that passed too easily.** "Top N" is checked in tags, hashtags and the whole
  description (the chart's own name is not a claim); the AI disclosure fails on a denial ("không
  dùng AI") and on `altered_content` other than "Có"; a credit is a line that names song and
  artists together; a tag that contains a stranger's name fails; a missing
  `metadata_rules.json` fails instead of passing empty; evidence without one YouTube result is
  a `WARN`.
- **The video length check compared the container's length**, so a picture stream that stopped
  early passed behind a complete sound track. Both streams are compared with the mix.
- **The report claimed things it had not measured**: "đã xoá sau khi chép" for any job folder
  it did not find, `mix.overlap_bars` as the key to change in a mix joined with `cut`, a
  stage with a `SKIP` shown as `PASS`.
- **The dot of "NHẠC" read as an accent on the line below** in the side title. A line with a
  mark under its letters gets more room beneath it.
- Preflight no longer fails a run whose remixes are done because StemForge is moved or
  mid-sync, and a run made with `--from-run` counts as such from its first stage: it asked
  for the disk space of twelve StemForge jobs (38 GB) and for free ports it never uses. A rank rejected after a failed remix can be supplied again with another file.
  Running again at an unanswered failed-remix stop asks again instead of retrying.

### Changed

- `source_tempo_range` lists the songs furthest from the preset's range first, with how far;
  `whole_bars` is a `WARN` only where a beat-matched overlap needs whole bars.
- The picture stop names a failed check of the picture and a video title that differs from
  the cover's.
- `selftest.py` exits 3 and says `INCOMPLETE` when tests were skipped; six new tests (`stall`,
  `decide`, `set`, `guards`, `from_run`, more bad metadata samples). The fake StemForge
  cancels after a delay and refuses a retry of a running job, like the real one.
- Rule 9 says what is true: YouTube limits and tunable thresholds are in files; fixed
  measuring tolerances are constants, listed in `references/design_notes.md`.
- Evals: `stops-for-failed-remix` and `declines-to-upload`; the YouTube case no longer accepts
  a claim about an AI picture the fixture does not have.

### Found while reviewing

- The finished run `…-remix-3` was a `--from-run` of a run that had since been deleted: its
  recorded picture path no longer existed, so one more `--from-run` would have failed.
- Its report printed "Không lời giữa hai bài: -0.0–4.2 giây" and named `mix.overlap_bars` for a
  mix joined with `cut`; its keyword evidence had no YouTube result (shopping, news and
  tool sites) and passed.
- Two of the three baseline selftest failures during the review were caused by the review's
  own first edit; the selftest caught it.

### Added

- **A thumbnail made to be read small** (`cover.thumb_style: poster`, the default). The cover
  scaled to 1280×720 carries ten song lines of 17 px, about 4 px at the 320 px width YouTube
  shows a thumbnail. The poster is the picture with the cover's title in large slanted letters
  (118–132 px on the 12-song run), the first `cover.poster_tracks` (3) songs and
  "+ N bài khác", drawn by the helper that draws the video's side column. It needs no chapter
  times, so the picture stop shows it and it is part of what the human approves.
  `thumb_style: tracklist` keeps m10-mixcover's thumbnail.
- **The mix is brought to the target loudness** (`mix.normalize`, default on): measured, then
  rendered once more with one gain to `mix.target_lufs`, never past the true-peak limit (no
  limiter). Before, the mix was only checked against a ±1.5 LU window.
- **The sound track inside the video is measured** after encoding (`video_loudness`): against
  the mix (`video.loudness_tolerance_lu`) and for a true peak over `video.true_peak_max_dbtp`;
  the check then names the two minutes with the highest peak. Measured on the finished
  12-song video: −13.9 LUFS like the mix, but a true peak of +1.8 dBTP where the mix has −1.1
  (m10-visualizer encodes AAC at 320k with no other processing), which no check had seen.

### Not changed

- m10-mixcover draws the cover title with the same tight line spacing (the dot of "NHẠC" over
  "HOT" on the thumbnail). The skill does not edit that repo.

## v1.7.0 — 2026-11-11

### Changed

- **Every song keeps its own tempo by default** (`remix.target_bpm: "source"`, was `128`). The
  voice is never sped up or slowed down. A job starts at `"auto"` so StemForge measures the
  source; once `/analysis` has the BPM the job is cancelled at the next stage boundary and
  retried with `target_bpm` = the source BPM, doubled or halved towards the new
  `remix.source_center_bpm` (128). StemForge reuses the analysis and the separation and
  stretches nothing (ratio 1.000). The measured tempo is kept in `source_tempo.json` and read
  back from a copied `remix_report.json`, so a redo or a `--from-run` creates the job at the
  right tempo directly.
- Two neighbours of different tempo hand over with a crossfade of `mix.crossfade_s`, reported
  as a planned `PASS` ("mỗi bài giữ tempo gốc") instead of the fallback `WARN`.
- New checks: `source_tempo` per song (`FAIL` when the voice was stretched anyway) and
  `source_tempo_range` (one `WARN` naming the songs whose backing lies outside the preset's
  124–140 BPM).
- `remix.target_bpm` set to a number keeps the old behaviour: one tempo, beat-matched overlaps,
  a stretched voice.
- New check `backing_tempo` per song: `FAIL` when StemForge's own measurement says the generated
  backing missed the requested tempo (`generation.chosen.validation.bpm_ok`), `WARN` when the
  tempo is right but the voice drifts against it. In `source` mode a miss re-queues the same job
  at the song's tempo one octave over (`tried_bpm` in `job.json`); both octaves missing is a
  failed remix. `VERIFY_VERSION` joins the remix stage hash, so an unfinished run re-checks its
  finished remixes and redoes only those that fail the new check.
- Preflight also looks for StemForge's `/analysis` route and for retry with option updates.
  The fake StemForge measures a "bpm<N>" source tempo, picks a mapping like StemForge's
  `plan_tempo`, refuses a cancel of a finished job and applies retry updates, and a "miss<N>"
  source gets a backing that misses any tempo above N; new selftests `source_tempo` and
  `backing_tempo`.

### Fixed

- `mix.transition: cut` joined the songs with a bare concat. On the 12-song run, 7 of 11 joins
  jumped by a sample step 3–17× the largest step in the 0.1 s around them: an audible click.
  The two songs now overlap `mix.cut_fade_ms` (20 ms), too short to hear as a fade.
- `mix.lead_in_bars: 0` and `mix.tail_bars: 0` (straight from one voice to the next) cut on the
  first and last bar at full vocal activity, so a pickup sung in the bar before and a last note
  ringing into the bar after were lost (5 songs each on the 12-song run). A neighbouring bar
  with `mix.edge_activity_min` (0.1) of voice is now always kept. A cut's few milliseconds of
  overlap no longer report a voiceless time of "-0.0 s".

### Added

- **`selection.manual_artist`** (`chart` | `tags`, default `chart`). A file the human puts in
  `RUN/sources/` is credited to the chart's artist by default; with `tags` it is credited to the
  artist written in the file's own tags (ID3, RIFF INFO or Vorbis `artist`, else
  `album_artist`), so the cover, the chapters and the description name the singer heard in the
  file. The title stays the chart's, since a tag can carry a typo. The key is part of the
  `originals` stage hash, so setting it on a run re-selects without a request to NCT.
- `ffmpeg.probe` returns the file's tags, lower-cased.
- At a `manual` answer the agent reads each supplied file's artist tag and names every mismatch
  with the chart before the long stages run.

### Found while building

- In the first real run, three of six hand-supplied originals carried a different singer in
  their tags than the chart listed for that rank, and the run would have credited the chart's
  artist with no way to follow the files.
- In the same run, 7 of 12 songs were stretched by more than 25% to reach 128 BPM: ballads
  measured at 164–179 BPM sang at 0.72–0.78× (song 1 lasted 6:22 instead of 4:45), a 98 BPM
  song at 1.31×. The human asked for the original speed. A trial of the first two songs at
  172 and 130 BPM came back at a ratio of 1.000029 and 1.000031, with no StemForge warning; the
  kick of the 172 BPM song measured at 172 BPM.
- The full 12-song run at the songs' own tempos: 11 backings came out at the requested tempo
  (98 to 172 BPM). "Như Một Người Dưng" (89.5 BPM, asked at 179) did not: six attempts, the best
  at 134 BPM, the voice drifting ±220 ms, reported only as a StemForge warning, so the skill
  passed it with a `WARN`. Resuming the run with the new check redid that song alone, at
  89.52 BPM: the backing measured 89.47 BPM, alignment spread 0 ms, the kick strongest at 90 BPM.

## v1.6.0 — 2026-11-11

### Changed

- **A new side column on the video background.** In the `visualizer` look the column at the
  side away from the DJ now holds a big title, `video.side_title` (default "remix nhạc hot
  tiktok"), above the song list. The title is a slanted poster block in Anton (upper case,
  each line scaled to fill the column, white and lime in turn, a solid pink copy behind); the
  font and its OFL licence ship in `assets/fonts/`. The list has one
  line per song in playing order, `01  Title`: no artist, no time, no subtitle, no song
  count. The cover, the thumbnail, the YouTube credits and the chapters keep artists and
  times.
- The list keeps its size (`video.side_track_max` 0.026 down to `side_track_min` 0.016 of the
  height) and the title grows into the room left (at least `side_title_min_size`, 0.037). A
  song title too long for the column is cut with "…" and the run warns. The background
  behind the column darkens until the list reaches 4.5:1 contrast.
- Drawn by a new helper, `scripts/mixcover_helpers/side_text.py`, run with m10-mixcover's
  Python (its Pillow, fonts and colours); m10-mixcover itself is unchanged and no longer
  draws this picture.
- Checks: `side_column` at S3 and `video_background` after the mix check the size, that every
  song is listed, and that everything fits the column at or above the minimum sizes; the
  `_warnings` checks name cut titles and low contrast. Preflight's `mixcover_preset` check
  now looks for the margin, the list's two font files, the colours and Pillow.
- `tracklist_readable` averages the strip at the column's edge down to 12×54 cells instead of
  96×432, because the saturated letters leave fringes after video coding (clean 23 → 8 at
  1080p, ring over the column 36–72). `video.max_side_diff` goes from 40 to 20.
- The S3 stop names the column's title, and changing it shows the picture again. The title,
  the column's limits and the helper's code are part of the `art` and `cover` stage hashes,
  so an unfinished run draws its background again.

## v1.5.0 — 2026-11-11

### Changed

- **Vinahouse only.** Every song is remixed with StemForge's `vinahouse` preset (until
  v1.4.0: `vietnamese_edm`). The preset is a constant, `GENRE` in `scripts/rcvlib/config.py`,
  no longer the config key `remix.genre`; a config that still sets that key to another preset
  is refused with a message saying to delete it. The arrangement (8-bar DJ intro and outro,
  section template), the 128 BPM target and the mastering are the same in both presets, so
  the join and its checks are unchanged.
- The genre is part of each remix's job key, so an unfinished run or an `init --from-run`
  redo whose songs were remixed with the old preset remixes them again; nothing old is mixed
  in by mistake.
- Every text says vinahouse: the cover subtitle (`Vinahouse Remix · Tháng {month}/{year}`),
  the remix stage in the steps pane (`Phối Vinahouse`), the trigger phrases, the YouTube
  guide, its examples and the baseline keywords.
- New `banned_phrases` rule: "edm" anywhere in the YouTube package fails validation.

## v1.4.0 — 2026-11-11

### Added

- **The tracklist stays in the video with the logo in the centre.** For the `visualizer` look
  m10-mixcover now draws a second picture, `video/background.png`: the same AI picture with
  the songs and their times in one narrow column at the far side, away from the DJ
  (`video.tracklist: side`, the default; `none` keeps the bare picture). The column's width
  (`video.side_column_width`, 0.24) is set so that the ring's farthest bar tip cannot reach it.
- Checks: `video_background` (size and chapter times), `side_column_clear` (the arithmetic on
  the two tools' presets), `tracklist_readable` (the finished video, at the column's inner
  edge), and a `WARN` whenever m10-mixcover had to cut a title with "…".
- The stop after S3 also shows the provisional video background.
- Preflight check `mixcover_preset`: the layout keys the side column overrides still exist in
  m10-mixcover's preset (that tool merges an unknown key silently), and the `--chapters` flag.

## v1.3.0 — 2026-11-10

### Changed

- **The background stands still in both looks** (`video.background_still`, default true): no
  shake and no beat zoom. The `visualizer` look is now the channel's look as in
  m10-visualizer's own output, with the picture held: the logo in the centre grows and shrinks
  on the beat, the ring and particles play around it. The `cover` look loses its slight zoom
  and is a still picture. The look question proposes `visualizer` first.

## v1.2.0 — 2026-11-10

### Added

- **A stop after the picture stage (S3).** Every run now waits there until the human has looked
  at the provisional cover: `decide --art ok`, `--art redo` (another seed), `--art image --path
  FILE` (their own picture, kept in the run folder), or new text through `pipeline.py set
  cover.title …`. A new picture or new text is shown again; nothing after S3 runs before `ok`.
  The approval is tied to the picture's hash and the two text lines, and carries over to a run
  made with `--from-run` as long as both are unchanged. `cover.review: false` turns it off.
- `selftest.py`: test `art_review`.

## v1.1.0 — 2026-11-10

From the human's first listen to the trial mix: the start and the handovers between songs were
too long.

### Changed

- **The mix is cut around the singing.** Each song keeps `mix.lead_in_bars` bars (4) before
  its first sung bar and `mix.tail_bars` bars (4) after its last, and hands over across
  `mix.overlap_bars` bars (4, was 8). The sung bars come from StemForge's per-bar vocal
  activity (`analysis.json`, downloaded with each remix and laid onto the remix's bars in
  `vocals.json`). On the trial the wait for the first sung line went from 32 s to 7.5 s and
  the stretch without a voice at each handover from 23–34 s to 7.5 s. `null` for the two new
  keys keeps whole songs as before.
- The `mix` checks and `REPORT.md` state both waits in seconds; a remix without vocal data is
  cut on its DJ intro and outro and flagged (`vocal_data`).

### Added

- `pipeline.py init --from-run OLD_RUN`: a new run folder that reuses a finished run's songs
  and remixes (hard links, no NCT request, no GPU), to redo the mix, cover and video with other
  settings.
- `selftest.py`: test `trim` (exact cuts, overlaps, chapter marks and waits).

### Fixed

- Preflight failed a run on a busy StemForge port even when every remix was already done (a
  site preview was listening on 8765). The port check is now skipped once the remix stage is
  done, and when it does fail it names `pipeline.py set remix.port N` as the way out.

## v1.0.0 — 2026-11-10

First version. Built from the brief in `Youtube-music/PROMPT-skill-remix-chart-to-video.md` and
exercised on a two-song trial (played A → B → A, 17:51) with no request to NCT.

### Added

- **Pipeline** (`scripts/pipeline.py`): ten stages (`preflight chart originals art remix mix
  cover video youtube report`) driven by `state.json`. A stage runs when it is not done or when
  the fingerprint of its inputs changed. Exit codes 10 (waiting for the human) and 20 (waiting
  for the agent).
- **Selection** from the downloader's `report --json`: eight reasons a song is unusable,
  files the human supplies in `RUN/sources/`, and a stop that asks before backfilling, skipping
  or waiting for a file.
- **Remix** through StemForge's Auto Remix API with the server started by the skill
  (`STEMFORGE_REMIX_RETENTION_DAYS=0`), one retry from checkpoints, per-song resume, and a
  measured check of every result.
- **Mix** on the beat: 8-bar overlaps at one tempo, each nudged by the measured beat offset,
  with a crossfade fallback; loudness, true peak, silence and length measured on the result;
  `transitions_preview.mp3` for the human's ear.
- **Cover** drawn after the mix, with durations fed so that m10-mixcover's times equal the
  skill's chapter marks; the AI picture is fetched before the remix stage.
- **Video** in two looks (`cover`, `visualizer`), with a readability check for the first.
- **YouTube package**: `youtube_meta.py facts` and `validate` (20 checks), limits in
  `references/youtube_limits.json` with official quotes, `youtube.md` for copy-paste.
- **Steps pane** (`scripts/steps_pane.py`), modelled on game-clone-pipeline's, with progress
  counts, a "Chờ bạn" line and a stall warning.
- **Offline tests** (`scripts/selftest.py`): nine tests with a fake StemForge server.

### Found while building

- An exact 8-bar overlap left the beats 24 ms apart; the measured nudge brings it to 0 ms.
- A fully transparent PNG as `--logo` removes m10-visualizer's centre logo (rendered and
  checked).
- StemForge's `auto_remix_setup.py --verify` reports every model missing after the repo is
  moved, because its manifest stores absolute paths; preflight maps the paths instead.
- YouTube's description limit is 5,000 characters in Help and 5,000 bytes in the Data API
  reference; both are enforced.
