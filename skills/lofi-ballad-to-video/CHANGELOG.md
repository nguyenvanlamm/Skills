# Changelog

## v1.2.0 — 2026-11-14

- **No stop at the picture (S3)**: `cover.review` is `false` by default. The model's picture is
  taken as it is, recorded as approved and added to `art_history/`; the run stops there only
  when a check of the picture FAILs (`art_unique`). `cover.review: true` brings the stop back.

## v1.1.0 — 2026-11-14

- **Reads the ballad list's new shape**: `periods[].songs[]` with `title`, `artist`,
  `songwriter`, `year` (14 two-year periods of 20 songs, the last one `2026-present`). Names
  joined with "&" or "," in one string are split; "Nhiều nhạc sĩ" is no name. The first shape
  (`cac_giai_doan`) is still read.
- **Each song's release year** is in the manifest and in `youtube_meta.py facts`.
- **A used duet stays used** when the list changes the order of its singers.

## v1.0.0 — 2026-11-13

First version, forked from remix-chart-to-video 1.9.0 for the "M10 lofi chill" channel.

- **Songs from the human's ballad list**, not from a chart: one period at random (or
  `--period`), its songs in an order a kept seed fixes, songs of earlier videos last
  (`song_history.json`). The draw is stored with tiktok-nct-downloader's new `songs --file`
  command (no request) and searched on NCT by `originals` as before. A title NCT returns that is
  not the list's (`3107` / `3107-2`) is `title_mismatch`, not used. No "Top N" anywhere.
- **Lofi sound**: StemForge's `lofi_chill` preset (ACE-Step backing, 70–92 BPM, centre 80, the
  voice untouched); lofi handovers (2 bars around the singing, 6 s crossfades).
- **A new anime landscape for every video**: a scene of place, time, weather and detail never
  used before (`assets/lofi_scenes.json`, `art_history.json`), painted by m10-mixcover's `lofi`
  preset with no people (`image.subject: scenery`), and `art_unique` against every approved
  earlier picture; `--art ok` is refused while it fails.
- **One look**: the picture standing still, the song list in a column at its calm side, a bar
  spectrum at the bottom centre (m10-visualizer's `lofi` preset), nothing in the middle;
  checked by `bars_visible`, `center_clear` and `tracklist_readable`.
- **Metadata rules for lofi**: remix, vinahouse, nhạc sàn, EDM, DJ, BXH and "hot nhất" are banned;
  composers are in `facts`.
- Its own workspace, `mixes-lofi/`, and its own config variable `LOFI_CONFIG`.
- Removed from the fork: the chart sources (`--html`, `--nct-run-id`), the `cover` look and the
  rotating centre (`center.py`, `decide --center`).
