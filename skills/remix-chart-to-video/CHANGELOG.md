# Changelog

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
