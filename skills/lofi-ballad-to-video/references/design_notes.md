# Design notes: the draw, the scene, the join, the chapters, the look, the thresholds

Read this when the human asks why the mix or the video is built the way it is, or when a
check's threshold needs changing. This skill is a fork of remix-chart-to-video 1.9.0: the join,
the chapters, the remix stage and their measurements come from that skill (its runs used the
`vinahouse` preset at 128 BPM). Numbers measured for this skill are marked "lofi": the
listening test of 2026-11-13 (two songs of the 2026-11-09 run remixed with `lofi_chill`) and
the selftest. A full 12-song lofi run has not been measured yet.

## The draw

The songs come from the human's ballad list, not from a chart. `pipeline.py init` reads it
(`songlist.path`), takes one period at random (or `--period`), drops a song listed twice in that
period, puts songs an earlier video of this workspace used at the end (`song_history.json`;
a run folder the human deleted gives its songs back), shuffles both groups with a seed it keeps
in `songlist/pick.json` and hands up to `songlist.pool` (50) songs to the downloader as a plain
list (`songs --file`, no request). Positions 1..`count` are the video's songs; the rest are what
"backfill" takes. Draw and search are separate on purpose: the draw is made once and kept, so an
unfinished run is continued with the same songs, and a search that fails is answered by the
human, never by a silent second draw.

The list (`periods[].songs[]`) has two-year periods of 20 songs, each song with `title`, `artist`,
`songwriter` and `year`. `artist` and `songwriter` are one string each: names joined with "&" or
"," are split, "Nhiều nhạc sĩ" is no name. A period "2026-present" is `2026-nay` (label
"2026–nay"). The year goes to the manifest and to `facts`. A song counts as used when an earlier
video's key matches any of its singers, so a duet whose singers changed order is not drawn as
new. A period holds 20 songs, so a draw of 12 leaves 8 for backfill: when NCT has too few of
them the run stops for missing songs as usual (`skip` or `manual`), it never takes songs of
another period.

Because the order is random, no "Top N" is ever true: `exact_top` is always false, `count_claims`
fails any "top N", and the metadata rules ban "BXH", "xếp hạng" and "hot nhất".

The downloader matches each song by title (≥ 90/100) and first singer and keeps only the
original version. A sequel can pass that ("3107-2" for "3107"), so the skill compares the title
NCT returned with the list's, without accents, case, punctuation or a bracketed guest
(`nct.same_title`): a different title is `title_mismatch` and the song is not used. The video
credits the list's title and singers, and its composers.

## The scene

The picture is an anime landscape with no people, painted by m10-mixcover with its `lofi`
preset (`image.subject: scenery`: the prompt's mandatory rules forbid people, faces and
characters instead of describing a woman). Every video gets another one, three ways:

- **Another description.** A scene is one place, one time, one weather and one detail from
  `assets/lofi_scenes.json` (20 × 5 × 6 × 8 = 4800 combinations). A combination any run of the
  workspace chose is never chosen again; the place differs from the last
  `cover.scene_place_gap` (6) videos; the focus of the picture goes left or right at random, so
  the column moves too. A `redo` excludes the scene shown and moves the seed.
- **Another seed.** From the run's name, so two runs never ask the provider the same thing;
  m10-mixcover's cache key holds the prompt and the seed.
- **A measured difference.** `art_unique` compares the new picture with a small copy of every
  approved earlier picture (`art_history/RUN.jpg`): the same file hash, or an SSIM at
  320×180 at or above `cover.max_art_similarity` (0.75), FAILs, and `--art ok` is refused while
  it does. Measured (selftest): the same picture 1.00, the same picture with a hue shift 0.97,
  two unrelated pictures well below 0.75. A picture joins the comparison set only when the human
  approves it, so an abandoned run takes no scene from later ones.

The scene reaches m10-mixcover through flags it already has: `--preset` with the run's own
`art/mixcover_preset.yaml` (`extends: lofi`, `image.scene`, `layout.default_side`). `--from-run`
keeps the old run's scene and seed, so the cache returns the same picture and `art_unique`
leaves that one pair out.

## The join

StemForge's presets write every remix as an intro, the song, and an outro (8 bars each in
`vinahouse`, where this section was measured; 4 bars in `lofi_chill`, the only preset this skill
uses, `GENRE` in `scripts/rcvlib/config.py`), and the song itself often has instrumental bars before its first sung line and
after its last. Joined whole, with the DJ outro of one song laid over the DJ intro of the next,
the first version of this skill gave a mix that waited 32 s for the first sung line and had
23–34 s without a voice at each handover (measured on the trial). The human found that too long.

- **Cut around the singing.** StemForge's analysis holds the vocal activity of every source
  bar, and the remix keeps the bars of the body one to one between its DJ intro and outro, so
  the activity maps onto the remix bar by bar (`remix/rNN_title/vocals.json`). A bar counts as
  sung when its activity reaches `mix.vocal_activity_min` (0.5); a faint pickup just before
  falls inside the lead-in and is kept. Of each song the mix keeps `mix.lead_in_bars` bars
  before the first sung bar and `mix.tail_bars` bars after the last; the mix starts
  `lead_in_bars` before the first song's first sung bar, with a `mix.start_fade_s` fade-in, and
  the last song keeps its own ending. All cuts are on whole bars.
- **Overlap.** One song hands over to the next across `mix.overlap_bars` bars, never more
  than the kept lead-in or tail, so no sung bar is under a fade (a faint pickup bar may start
  under the end of one). A crossfade (two tempos, or the fallback below) is held to the
  voiceless part kept at that join, pickup and last note included: shorter than
  `mix.crossfade_s` when less was kept, and a straight join (`mix.cut_fade_ms`) when nothing
  was. Before v1.8.0 a 4 s crossfade ran over both voices at `lead_in_bars: 2` (2.8 s at
  172 BPM) and the report said "0.0 s". The time without a voice is
  `lead_in + tail − overlap` bars: 4 bars, 7.5 s at 128 BPM, with the defaults. Measured on the
  trial after the change: 7.5 s to the first sung line and 7.5 s at both handovers.
- **No vocal data.** A remix without `analysis.json` (an instrumental, or a job folder that is
  gone) is cut on its DJ intro and outro instead, and the `vocal_data` check is `WARN`.
- **Each song at its own tempo (default, `remix.target_bpm: "source"`).** One common tempo
  stretched the voice of most songs: on the 2026-11-09 chart 7 of 12 originals moved by more
  than 25% to reach 128 BPM (ballads measured at 164–179 BPM sang at 0.72–0.78×; a 98 BPM song
  at 1.31×). So the default keeps every song at its own tempo. A job starts at `"auto"` only so
  StemForge can measure the source; as soon as `/analysis` has the BPM the job is cancelled
  (StemForge stops at the next stage boundary and keeps the finished stages) and retried with
  `target_bpm` = the source BPM, doubled or halved, whichever lies nearest
  `remix.source_center_bpm` (128). StemForge then maps the groove x1, x2 or x0.5 with a stretch
  of 1.000×; the measurement and the separation are reused, so the extra cost is one stage
  boundary. A tempo measured once is kept in `source_tempo.json` (and read from the
  `remix_report.json` a `--from-run` copies), so a redo creates the job at the right tempo
  directly. Measured on the trial: song 1 at 172.0 BPM (ratio 1.000029, 4:45 instead of 6:22),
  song 2 at 130.0 BPM. Cost: the backing runs at the song's tempo, often outside the preset's
  124–140 BPM (the kick of the 172 BPM trial song measured at 172 BPM, less regular than at
  128), and neighbours with different tempos cannot overlap on the beat, so they hand over with
  a crossfade of `mix.crossfade_s` (a planned `PASS`, not the `WARN` fallback below).
  `source_tempo_range` names, in one `WARN`, the songs whose backing lies outside the preset's range.
- **A backing that misses its tempo.** At a fast tempo ACE-Step may not produce the requested
  beat. StemForge measures every attempt and, when none passes, keeps the best one with a
  warning. A "cover" backing is then only shifted into place, never conformed to the tempo, so
  the drums drift against the voice. Measured on the first full run at the songs' own tempos:
  11 of 12 backings came out at the requested tempo (98 to 172 BPM), but an 89.5 BPM song asked
  at 179 BPM got six attempts, the best measured 134 BPM with the voice drifting ±220 ms, and the
  kick showed no 179 BPM period. `backing_tempo` reads StemForge's measurement
  (`generation.chosen.validation.bpm_ok`): `FAIL` when it missed, `WARN` when the tempo is right
  but the alignment drifts, `PASS` for a "text2music" backing (StemForge stretches that one to
  the tempo). In `source` mode a miss re-queues the same job at the song's tempo one octave over
  (`tried_bpm` in `job.json`); analysis and separation are reused. When every octave missed the
  song stops as a failed remix; a `retry` starts the octaves over. `VERIFY_VERSION` in
  `scripts/rcvlib/stemforge.py` is part of the remix stage's inputs, so an unfinished run checks
  its finished remixes again after a check is added, and redoes only those that fail it.
- **One tempo (`remix.target_bpm`: a number).** Overlaps only line up when both songs have the
  same BPM, so every job gets the same `target_bpm`, e.g. 128 (the preset's target), instead of
  `"auto"`, which would put each song somewhere in the preset's range (124–140). Measured: both
  remixes came out at exactly 128.0 BPM and a whole number of bars long (204 and 179). The voice
  is stretched to that tempo; `remix.warn_tempo_stretch` flags the songs moved furthest.
- **Whole bars are not enough.** Bar-aligned overlaps still left the beats of the two songs
  24–25 ms apart (measured, both handovers), which is audible as a flam. So every overlap is
  measured: the onset envelopes of the low band of the outgoing tail and the incoming head are
  cross-correlated over a quarter beat either side, and the incoming song is moved by the lag
  found. Measured after the move: 0 ms, correlation 0.63.
- **Fallback.** When the two songs differ in tempo, when the correlation is below
  `mix.min_beat_correlation` (no beat to measure), or when a nudge does not bring the offset
  under 3 ms, the handover becomes a plain crossfade of `mix.crossfade_s` seconds and the
  check is `WARN`.
- **No clipping.** The fade curves are linear (`mix.curve: tri`), so the two gains sum to 1
  and an overlap cannot exceed the louder song's peak. Measured on the mix: −13.9 LUFS,
  true peak −1.10 dBTP, with no gain correction.
- The human's ear is the last check. `transitions_preview.mp3` holds every handover with
  `mix.preview_pad_s` seconds either side; `REPORT.md` lists where each one starts.

## The stop after the picture

The picture is fetched right after the songs are chosen (stage S3), an hour before the cover
that uses it is drawn, because the image provider is the one outside service in the chain. Since
1.2.0 the run goes on without asking (`cover.review: false`): the human said they take the
model's picture as it is. The picture is recorded as approved and joins `art_history/` right
away, and the run still stops when a check of it FAILs (`art_unique`). With `cover.review: true`
the run stops there for the human: they see the picture with the title, subtitle and song list (no
times yet) and either approve it, ask for another one, hand in their own, or change the text.
Asking here costs a minute; asking after the remix and the render would cost the whole run.
What they approve is recorded as a hash of the picture and the two text lines
(`decisions.art_approved` in `state.json`), so any change is shown again and an unchanged
picture is not asked about twice.

## Chapter times

A chapter starts in the middle of the overlap, where the incoming song takes over, rounded
half up to a whole second. Positions come from sample counts of the joined file, not from NCT
durations (those are the originals') and not from estimates.

m10-mixcover draws start times and the total on the picture and writes `chapters.txt`, both
from cumulative durations. The skill feeds it a CSV whose durations are the gaps between its
own whole-second marks, with `--crossfade 0`, so mixcover's sums reproduce the marks exactly.
The `chapters_match` check compares `chapters.txt` with the marks; the picture uses the same
numbers but cannot be read back, so the human looks at it.

## The look

One look, built from what m10-visualizer already draws and one effect added for this channel:

- **The picture stands still** (`video.background_still`): no shake, no beat zoom, no dim, no
  vignette. The landscape is the point of a lofi video.
- **The song list** sits in a column at the calm side of the picture (`video.tracklist: side`,
  `video/background.png`): the title `video.side_title` above the numbered titles, drawn by
  `scripts/mixcover_helpers/side_text.py` in the mixcover preset's colours.
- **One horizontal bar spectrum at the bottom centre** (`effects.bar_spectrum` in the
  visualizer's `lofi` preset): 0.42 of the frame width, 0.07 of the height above the bottom,
  the bass in the middle, drawn last. `side_column_clear` checks by arithmetic that the bars
  stay clear of the column.
- **Nothing in the middle.** The visualizer always draws a logo there; the skill passes a fully
  transparent one (`video.logo`).

Three checks compare a frame with the picture it was drawn on (mean luma difference over 12×54
cells): `bars_visible` (the bars' strip, at least `video.min_bars_diff`), `center_clear` (the
middle fifth of the frame, at most `video.max_center_diff`) and `tracklist_readable` (the
column's inner edge, at most `video.max_side_diff`). Measured (lofi, selftest at 640×360):
bars 85 against 0.7 with the bars off; centre 1.0 against 45 with the M10 logo; column 9
against 93 with bars stretched over it.

## Thresholds (config keys)

| Key | Default | Meaning |
|---|---|---|
| `selection.min_duration_s` | 90 | a shorter original is a snippet, not a song |
| `selection.max_duration_s` | 600 | StemForge refuses longer input |
| `songlist.path` | `Assets/danh_sach_nhac_ballad_viet_nam.json` | the ballad list, relative to the folder of the four repos |
| `songlist.pool` | 50 | songs of the drawn period handed to the downloader: the video's and those backfill may take (at most 50) |
| `selection.manual_artist` | `list` | who a file the human put in `RUN/sources/` is credited to: the list's singers, or (`tags`) the artist in the file's own tags; the title stays the list's |
| `remix.target_bpm` | `source` | `source`: every song keeps its own tempo, the voice is never stretched, handovers are crossfades; a number: one tempo for every song, handovers overlap on the beat, the voice is stretched |
| `remix.source_center_bpm` | 80 | with `source`: a song's BPM, doubled or halved, whichever lies nearest this, is its backing tempo (lofi: a 172 BPM song plays at 86, an 89.5 BPM song at 89.5) |
| `remix.max_attempts` | 2 | the first try plus retries from checkpoints |
| `remix.warn_tempo_stretch` | 1.25 | with a number as `target_bpm`: a song sped up or slowed down by more than this factor to reach the tempo is `WARN` (measured: 0.744× on a ballad detected at 172 BPM) |
| `remix.stall_s` | 600 | a job whose stage and progress stand still this long is cancelled and retried |
| `remix.cancel_wait_s` | 120 | how long a cancelled job may take to stop (StemForge stops at the next stage boundary and refuses to retry a running job); after that a server the skill started is restarted, and the song otherwise becomes a failed remix |
| `remix.job_timeout_s` | 2400 | the same, for a job that keeps moving but never ends |
| `mix.lead_in_bars` | 2 | bars kept before a song's first sung bar, and before the first sung bar of the mix; `null` keeps all |
| `mix.tail_bars` | 2 | bars kept after a song's last sung bar; `null` keeps all |
| `mix.crossfade_s` | 6.0 | crossfade between two songs of different tempo (the usual case), never longer than the voiceless part kept at that join |
| `mix.overlap_bars` | 4 | bars over which one song fades into the next (8 when whole songs are kept) |
| `mix.cut_fade_ms` | 20 | with `mix.transition: cut`, the two songs overlap this long: a bare concat clicked at 7 of 11 joins (a sample step 3–17× the largest step around it) |
| `mix.vocal_activity_min` | 0.5 | a bar counts as sung from this vocal activity on |
| `mix.edge_activity_min` | 0.1 | a bar next to the singing with this much voice is never cut: on the 12-song run 5 songs had 0.11–0.45 in the bar before the first sung bar (a pickup) and 5 had 0.10–0.43 in the bar after the last (the last note), so `lead_in_bars: 0` alone would have cut syllables |
| `mix.max_beat_offset_ms` | 60 | a first offset beyond this is flagged `WARN` even when the nudge fixed it |
| `mix.min_beat_correlation` | 0.25 | below this there is no beat to measure: crossfade instead |
| `mix.target_lufs`, `mix.lufs_tolerance` | −14, 1.5 | integrated loudness of the mix; outside is `WARN` |
| `mix.normalize`, `mix.normalize_min_db` | true, 0.1 | the mix is measured, then rendered once more with one gain that brings it to `target_lufs`; a correction below 0.1 dB is skipped. The gain never lifts the true peak past its limit (there is no limiter: a gain changes the level and nothing else), so a mix with high peaks stays below the target and the `loudness` check says so |
| `mix.true_peak_max_dbtp` | −1.0 | above it the mix gets one gain trim, then must pass |
| `video.loudness_tolerance_lu` | 0.5 | the sound track inside the video, measured after encoding, against the mix; further apart is `WARN` (`video_loudness`) |
| `video.true_peak_max_dbtp` | 0.0 | AAC coding overshoots the mix's peak at single loud moments (measured on the 12-song run: +1.8 dBTP from a mix at −1.1, loudness unchanged); above this the check is `WARN` and names the two minutes with the highest peak |
| `cover.thumb_style` | `poster` | `poster`: the thumbnail is the picture with the cover's title in large letters, the first `cover.poster_tracks` (3) songs and "+ N bài khác". `tracklist`: m10-mixcover's cover scaled to 1280×720, where ten song lines are 17 px high, about 4 px at the 320 px width YouTube shows a thumbnail |
| `cover.poster_column_width` | 0.44 | `poster`: width of the text column |
| `cover.poster_title_min_size` | 0.10 | `poster`: smallest title size (72 px of 720); below it `thumbnail_poster` fails |
| `cover.poster_track_max`, `cover.poster_track_min` | 0.054, 0.044 | `poster`: size of a song line (39 to 32 px of 720) |
| `mix.silence_db`, `mix.silence_min_s` | −50, 1.5 | a quieter stretch this long inside the mix is `WARN` |
| `cover.max_art_similarity` | 0.75 | SSIM against every approved earlier picture; at or above it `art_unique` fails |
| `cover.scene_place_gap` | 6 | the scene's place differs from those of this many videos before |
| `video.side_column_width` | 0.24 | width of the side column |
| `video.side_title_min_size` | 0.037 | smallest size of the column's title, as a fraction of the height (40 px at 1080p) |
| `video.side_track_max` | 0.026 | largest size of a song line (28 px at 1080p) |
| `video.side_track_min` | 0.016 | smallest size of a song line (17 px); below it, or the title below its minimum, `video_background` fails |
| `video.max_side_diff` | 20 | mean luma difference allowed at the side column's inner edge (12×54 cells) |
| `video.min_bars_diff` | 3.0 | mean luma difference the bars' strip must reach |
| `video.max_center_diff` | 4.0 | mean luma difference allowed in the middle of the frame |
| `video.duration_tolerance_s` | 0.1 | length of the picture stream and of the sound stream, each against the mix (a file is as long as its longest stream) |
| `panel.stall_warn_s` | 300 | the pane warns when a running stage has not reported for this long |

Fixed measuring tolerances are constants in the scripts, not config keys: nobody tunes them,
and a change means the check itself changed. They are: export length ±0.05 s, source length
±1.0 s, requested tempo ±0.01 BPM, tempo ratio ±0.001 and whole bars ±0.01 bar
(`stemforge.py`); residual beat lag 3 ms, mix length ±0.02 s and the last 2 s left out of the
silence search (`mix.py`); three evidence queries and twelve commas for a stuffed line
(`youtube.py`); contrast 4.5:1 (`cover.py`, `side_text.py`); about 10 GB of VRAM and
2.5 GB of disk a song plus 8 GB (`preflight.py`). The YouTube numbers the mix needs (ten
seconds a chapter, fifteen minutes for an unverified account) are in
`references/youtube_limits.json`.

## Time and disk for 12 songs (estimate from measured rates)

- Originals: 12–15 minutes (60 s between downloads). Remix: about 4.7 minutes a song. Mix:
  under a minute. Cover: seconds. Video: 7 minutes for an 18-minute mix at 1080p60 (measured),
  so about 25 minutes for an hour.
- Disk: 2.1–2.4 GB per StemForge job until cleaned, about 1 GB for `mix.wav` per hour, about
  4 GB per hour of video.

## State and resume

`state.json` holds each stage's status, progress, checks and a fingerprint of its inputs. A
stage runs when it is not done or when its fingerprint changed, which also re-runs the stages
that depend on its output. The video's fingerprint holds what changes the picture or the sound
(look, preset, logo, fps, size, background, tracklist) and the content (SHA-256) of the mix
and of the picture the look shows, not their file times: a stage that ran again and wrote the
same bytes (a check threshold, a thumbnail setting) does not cost a render. The originals'
fingerprint holds name, size and time of every file in `sources/`, so a file replaced under
the same name is selected and remixed again; the mix's holds the labels, since the chapters
carry them. A finished run is never touched again: `pipeline.py run` on it does nothing and
`pipeline.py decide` refuses it. Remixes are kept per song (`remix/rNN_title/job.json`), so one
failed or interrupted song never repeats the others. An interrupted StemForge job is retried
from its checkpoints (measured: the retry reused the analysis step). The pane and
`REPORT.md` read the same file.
