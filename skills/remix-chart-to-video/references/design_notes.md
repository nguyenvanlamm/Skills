# Design notes: the join, the chapters, the looks, the thresholds

Read this when the human asks why the mix or the video is built the way it is, or when a
check's threshold needs changing. Numbers marked "measured" come from the trial run of
2026-11-10 on this machine (two songs, played A → B → A). That trial ran before the skill
switched to `vinahouse` (v1.5.0, see CHANGELOG), on a preset with the same arrangement, the
same 128 BPM target and the same mastering, so the numbers hold for the join. A vinahouse run
has not been measured yet.

## The join

StemForge's `vinahouse` preset (the only one the skill uses, `GENRE` in
`scripts/rcvlib/config.py`) writes every remix as an 8-bar DJ intro, the song, and an 8-bar
DJ outro, and the song itself often has instrumental bars before its first sung line and
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
  than the kept lead-in or tail, so no voice is under a fade. The time without a voice is
  `lead_in + tail − overlap` bars: 4 bars, 7.5 s at 128 BPM, with the defaults. Measured on the
  trial after the change: 7.5 s to the first sung line and 7.5 s at both handovers.
- **No vocal data.** A remix without `analysis.json` (an instrumental, or a job folder that is
  gone) is cut on its DJ intro and outro instead, and the `vocal_data` check is `WARN`.
- **One tempo.** Overlaps only line up when both songs have the same BPM, so every job gets
  `target_bpm: 128` (the preset's target) instead of `"auto"`, which would put each song
  somewhere in the preset's range (124–140). Measured: both remixes came out at exactly
  128.0 BPM and a whole number of bars long (204 and 179).
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
that uses it is drawn, because the image provider is the one outside service in the chain. The
run stops there for the human: they see the picture with the title, subtitle and song list (no
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

## The two looks

m10-visualizer draws its logo at the centre of the frame unconditionally and a spectrum ring
around it; no preset key hides or moves the logo. The cover from m10-mixcover has the DJ on one
side and the tracklist on the other, so the default overlays cover text.

| Look | Background | Overlays | Result |
|---|---|---|---|
| `visualizer` | the AI picture with a column at the far side: the title `video.side_title` above the numbered song list (`video/background.png`), or the bare picture with `video.tracklist: none` | as the preset defines: logo with its beat pulse, spectrum ring, particles; dim and vignette off when the picture carries text | the channel's look, as in m10-visualizer's own output, with the title and songs readable beside the ring |
| `cover` | `cover.png` with the tracklist | ring, particles, vignette and dim off; logo replaced by a fully transparent PNG | the text stays readable; a still picture |

In both looks the background is held still (`video.background_still`, default true: shake and
beat zoom off). The human asked for this after the first trial: the logo in the centre should
grow and shrink, the picture behind it should not move. Putting the logo and ring on the cover
with the wide tracklist was tried and rejected: they hide the time column and part of the title.

**The side column.** The human wanted the songs kept in the video. The first versions had
m10-mixcover draw them as a narrow column at the far side, with the cover's title, subtitle and
song count above them. On 2026-11-11 the human asked, in turn, for each line to be the
play-order number and the song title (no artist, no minutes), then for the words "remix nhạc
hot tiktok" in a beautiful, prominent font, and then for those words as the title above the
song list. A glowing white-to-lime title in Be Vietnam Pro Black was found ugly; four styles
were then drawn on the trial picture (a clean lockup, neon tubes, a slanted condensed poster,
a TikTok-style colour split) and the human chose the poster. The result: the poster title,
then the numbered list; no subtitle, no count.

- **Who draws it.** mixcover cannot style a title this way and the visualizer draws no text,
  so `scripts/mixcover_helpers/side_text.py` draws the whole column with m10-mixcover's Pillow,
  the preset's list fonts (`fonts.track`, `fonts.number`) and colours, and the skill's own
  title font, `assets/fonts/Anton-Regular.ttf` (SIL OFL 1.1, licence beside it; it has every
  Vietnamese letter, checked with mixcover's `missing_glyphs`; Bebas Neue lacks 64 of them).
  The helper sits in a folder of its own because Python puts a script's folder first on the
  import path, and `rcvlib` has modules (`config`, `video`, …) that could shadow ones Pillow or
  mixcover import.
- **The title.** Upper case in Anton, left-aligned, slanted by 0.18 (about 10°). Each line is
  scaled until it and its shadow fill the column's width; lines go white, lime, white, …; a
  solid pink `accent` copy sits 0.06 of the size down and right of each line; 0.12 of a size
  separates the ink of two lines, so the dot under "Ạ" stays with its own line. The words are
  broken into at most four lines, choosing the break whose smallest line is largest while the
  block fits the room above the list (fewer lines on a tie); no line may exceed 1.4 times the
  smallest, so a short word does not tower over the rest.
- **The list.** One line per song in playing order (a song played twice appears twice): the
  number `01` in lime at 0.86 of the size, the song title in white, a soft dark shadow; rows
  1.75 sizes apart. A title wider than the column is cut with "…" and counted.
- **Sizes.** The list takes the largest row size from `video.side_track_max` (0.026 of the
  height, 28 px at 1080p) down to `side_track_min` (0.016, 17 px) that leaves the title room
  with no line below `side_title_min_size` (0.037, 40 px); the title then takes the largest
  sizes that fit that room, no line above 0.20 of the height, 0.45 of it in total. The block is centred
  on the height. Measured at 1080p on the trial picture: 3 songs, REMIX / NHẠC HOT / TIKTOK at
  169, 121 and 169 px; 12 songs, REMIX NHẠC / HOT TIKTOK at 97 and 108 px, list at 28 px, one
  song title cut ("Ngày Mai Người Ta Lấy Ch…"). The helper takes under a second; a 12-word
  title, about two.
- **Contrast.** A dark gradient (opacity 0.70, fading over 0.16 of the width towards the DJ)
  sits behind the column. The helper measures the lime numbers against the 95th-percentile
  brightest background in the list's box and darkens the gradient up to 0.90 until that is at
  least 4.5:1 (WCAG AA). Measured: 9–11:1 at 0.70 on the trial picture. Below 4.5:1 at 0.90 the
  run warns.
- **Where.** On the side away from the DJ, read from m10-mixcover's face detection in the
  cover run ("cô gái ở bên trái" puts the column on the right); right when nothing is detected.
- **Clear of the ring.** The column is `video.side_column_width` of the frame inside the
  preset's margin. The ring's farthest bar tip is
  `radius × (1 + ring_pulse) + gap + min_length + max_length × (1 + peak_cap)` of the height
  from the centre (0.405 with the `m10` preset, 438 px at 1080p, so x = 1398), and a column
  0.24 wide starts at x = 1400. The `side_column_clear` check does this arithmetic on the two
  presets at every run. The title's glow may reach a few pixels past the column; letters do not.

The `tracklist_readable` check looks at the finished video: the mean luma difference between a
frame and the background in the strip at the column's inner edge, both averaged down to 12×54
cells. With mixcover's white list (averaged to 96×432) it measured 9–15 of 255 clean and 54–83
with the ring blown up over it. The new column's saturated lime and pink letters leave fringes
after video coding that raised the clean value to 23 at 96×432 (1080p), too close to the old
threshold; at 12×54 the fringes average out: measured at 1080p, 8–9 clean and 36–72 with the
ring over the column (13 and 33 in the 360p selftest). `video.max_side_diff` is 20. SSIM was
tried for this and did not separate the two cases (0.78 against 0.71–0.75).

The `cover_readable` check compares a frame of the video with `cover.png` at 640×360 (SSIM).
Measured: 0.88–0.94 with the `cover` look, 0.42 with the default overlays on the real cover and
0.70 on a plain gradient cover. `video.min_cover_ssim` is 0.80.

A smaller change in m10-visualizer would give both a readable cover tracklist and a spectrum: a
preset key to hide the logo and to move the ring's centre (one function,
`Renderer.render` in `visualizer/render.py`). The skill does not make that change.

## Thresholds (config keys)

| Key | Default | Meaning |
|---|---|---|
| `selection.min_duration_s` | 90 | a shorter original is a snippet, not a song |
| `selection.max_duration_s` | 600 | StemForge refuses longer input |
| `remix.target_bpm` | 128 | one tempo for every song |
| `remix.max_attempts` | 2 | the first try plus retries from checkpoints |
| `remix.warn_tempo_stretch` | 1.25 | a song sped up or slowed down by more than this factor to reach the tempo is `WARN` (measured: 0.744× on a ballad detected at 172 BPM) |
| `remix.stall_s` | 600 | a job whose stage and progress stand still this long is cancelled and retried |
| `remix.job_timeout_s` | 2400 | the same, for a job that keeps moving but never ends |
| `mix.lead_in_bars` | 4 | bars kept before a song's first sung bar, and before the first sung bar of the mix; `null` keeps all |
| `mix.tail_bars` | 4 | bars kept after a song's last sung bar; `null` keeps all |
| `mix.overlap_bars` | 4 | bars over which one song fades into the next (8 when whole songs are kept) |
| `mix.vocal_activity_min` | 0.5 | a bar counts as sung from this vocal activity on |
| `mix.max_beat_offset_ms` | 60 | a first offset beyond this is flagged `WARN` even when the nudge fixed it |
| `mix.min_beat_correlation` | 0.25 | below this there is no beat to measure: crossfade instead |
| `mix.target_lufs`, `mix.lufs_tolerance` | −14, 1.5 | integrated loudness of the mix; outside is `WARN` |
| `mix.true_peak_max_dbtp` | −1.0 | above it the mix gets one gain trim, then must pass |
| `mix.silence_db`, `mix.silence_min_s` | −50, 1.5 | a quieter stretch this long inside the mix is `WARN` |
| `video.min_cover_ssim` | 0.80 | `cover` look: a frame must still look like `cover.png` |
| `video.side_column_width` | 0.24 | `visualizer` look: width of the side column; wider and the ring can reach it |
| `video.side_title_min_size` | 0.037 | smallest size of the column's title, as a fraction of the height (40 px at 1080p) |
| `video.side_track_max` | 0.026 | largest size of a song line (28 px at 1080p) |
| `video.side_track_min` | 0.016 | smallest size of a song line (17 px); below it, or the title below its minimum, `video_background` fails |
| `video.max_side_diff` | 20 | mean luma difference allowed at the side column's inner edge (12×54 cells) |
| `video.duration_tolerance_s` | 0.1 | video length against audio length |
| `panel.stall_warn_s` | 300 | the pane warns when a running stage has not reported for this long |

## Time and disk for 12 songs (estimate from measured rates)

- Originals: 12–15 minutes (60 s between downloads). Remix: about 4.7 minutes a song. Mix:
  under a minute. Cover: seconds. Video: 7 minutes for an 18-minute mix at 1080p60 (measured),
  so about 25 minutes for an hour.
- Disk: 2.1–2.4 GB per StemForge job until cleaned, about 1 GB for `mix.wav` per hour, about
  4 GB per hour of video.

## State and resume

`state.json` holds each stage's status, progress, checks and a fingerprint of its inputs. A
stage runs when it is not done or when its fingerprint changed, which also re-runs the stages
that depend on its output. The video's fingerprint holds only what changes the picture (look, preset, fps, size,
zoom), so changing a check threshold never costs a render. A finished run is never touched again;
`pipeline.py run` on it does nothing. Remixes are kept per song (`remix/rNN_title/job.json`), so one
failed or interrupted song never repeats the others. An interrupted StemForge job is retried
from its checkpoints (measured: the retry reused the analysis step). The pane and
`REPORT.md` read the same file.
