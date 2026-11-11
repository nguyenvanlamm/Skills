# What the skill calls in the four repos

Read from source on 2026-11-10 and exercised by the trial run of that day. The repos keep
changing: `preflight.py` re-checks every flag, route and preset key listed here at the start
of each run and fails when one is gone. When that happens, open the file named below, trust
the source over this page, and tell the human what changed.

## tiktok-nct-downloader (NhacCuaTui only, despite the name)

Entry: `<repo>/.venv/bin/python <repo>/run.py [--home DIR] <command>`; argparse in `app/cli.py`.

| Call | Purpose | Requests |
|---|---|---|
| `remix --top 50 --no-download [--chart TAG]` | save the chart as a run | 3 (live) |
| `remix --top 50 --no-download --html FILE` | the same from a page saved in a browser | 0 |
| `originals --run-id ID --limit K --interval 60` | find and download the originals of ranks 1..K | 1–2 searches per rank, plus a page and a file when matched |
| `report --run-id ID --json` | the run as JSON on stdout (logs go to stderr) | 0 |

- Live access needs `NCT_LIVE_ACCESS=true` in the environment of that one command. Without it
  `remix` (no `--html`) exits 2 and `originals` records `not_searched`.
- `report --json`: `run{id,status,chart_tag,chart_title,chart_date,chart_url,started_at}`,
  `songs[]{position,title,artist,duration_seconds,nct_url,release_information,
  original{decision,title,artist,duration_seconds,nct_url,manual_search_url,status,
  local_file_path,base_title}}`. `decision`: `matched | uncertain | not_found | skipped |
  not_searched`. With no run it prints `{}` and exits 3.
- `originals` skips a rank only when its original is already downloaded; every unmatched rank
  is searched again on each call. Widen the window in as few calls as possible.
- Exit codes: 0 ok, 1 error, 2 NCT off or unreachable (argparse errors are 2 as well), 3 no
  data. A song that fails still leaves exit 0: read the report.
- Originals land in `<home>/downloads/ban_goc/` (default home `~/Music/NhacCuaTuiRemix`). The
  rank in a file name is not reliable; order by `position`.
- Progress of a running `originals`: lines in `<home>/logs/app.jsonl` with
  `"message": "Kết quả tìm bản gốc"` and a `position`. Two CLI commands must not run at once
  on the same home.

## StemForge (Auto Remix)

Server: `cd <repo> && STEMFORGE_REMIX_RETENTION_DAYS=0 .venv/bin/python run.py --offline --host
127.0.0.1 --port 8765 --acestep-port 8001` (the documented `uv run python run.py --offline` is
the same thing; the skill calls the venv's Python so nothing re-syncs at run time). Routes in
`backend/api/auto_remix.py`:

| Route | Use |
|---|---|
| `GET /api/health` | `{"status":"ok"}` |
| `GET /api/auto-remix/status` | `ready` must be true; `gpu.free_vram_mb` |
| `POST /api/auto-remix/upload` | multipart field `file` (mp3, wav, flac; 20–600 s; ≤ 200 MB) → `upload_id` |
| `POST /api/auto-remix` | `{upload_id, genre, target_bpm, target_key, preserve_vocal, quality, output_format}` → `job_id` |
| `GET /api/auto-remix/{id}` | `status`, `stage`, `progress` (0–1), `error_type`, `error` |
| `GET /api/auto-remix/{id}/download?format=wav\|report\|analysis` | `final.wav` (48 kHz, 24-bit, stereo), `remix_report.json`, `analysis.json` |
| `POST /api/auto-remix/{id}/retry` | re-queue; finished stages are reused |
| `POST /api/auto-remix/{id}/cancel`, `DELETE /api/auto-remix/{id}` | cancel; delete the job folder |

- `genre` is the id of a file in `presets/remix/`. The skill always sends `vinahouse`
  explicitly (`GENRE` in `scripts/rcvlib/config.py`, not a config key), so a change of the
  server's default does not change the mix; preflight fails when `presets/remix/vinahouse.json`
  is gone. `target_bpm` is `"auto"` or 60–200.
- States: `queued → analyzing → separating → syncing → generating → arranging → mixing →
  mastering → exporting → completed`, or `failed` / `cancelled`. After a server restart a job
  that was running is `failed` and can be retried.
- One job at a time. Measured here: about 290 s for a 5-minute song, VRAM peak about 10 GB,
  2.1–2.4 GB of disk per job under `~/.local/share/stemforge/output/remix/local/<job_id>/`.
- **Retention.** `backend/main.py` deletes finished jobs older than
  `STEMFORGE_REMIX_RETENTION_DAYS` (default 7) one hour after the server starts and hourly after
  that. `0` turns it off. The skill always starts the server with `0`.
- Do not send an `x-auth-user` header: jobs would go to another user's folder.
- `remix_report.json` fields the skill reads: `source.duration`, `tempo.{source_bpm,
  target_bpm,tempo_ratio,within_vocal_limit}`, `target_key`, `exports.wav.{ok,duration}`,
  `mastering.{target_reached,true_peak_ok,after.integrated_lufs,after.true_peak_dbtp}`,
  `warnings`, `timings_s.total`, `arrangement.sections[]{type,bars,source}` (`source` is `dj_intro`, `body` or
  `dj_outro`), `body.{start_bar,end_bar}`. From `analysis.json`: `vocals.{has_vocals,bar_activity}` (one value
  from 0 to 1 per source bar). The remix keeps the body's bars one to one, so remix bar `dj_intro + i` is source
  bar `body.start_bar + i`.
- **After the repo is moved** its `.venv` still points at the old path (editable installs and
  script shebangs). `uv sync --locked` in the repo repairs it without changing the lock.
  StemForge's own `scripts/auto_remix_setup.py --verify` then still reports every model
  missing, because `~/.cache/stemforge/auto_remix_manifest.json` records absolute paths from
  the day of the download; preflight's `stemforge_models` check maps those paths onto the
  current checkout instead.
- `StemForge/CLAUDE.md` (commit, push, pause after each step) is for developing StemForge.

## m10-mixcover

`<repo>/.venv/bin/python <repo>/main.py SOURCE [options]`, run with the repo as working
directory; argparse in `mixcover/cli.py`.

- `SOURCE`: `.csv` (`artist,title[,duration]`), `.txt`, or a folder of audio. No JSON.
  `duration` is each song's length in seconds, not a start time.
- `--all -o X/cover.png` writes `X/cover.png` (1920×1080), `X/cover_thumb.jpg` (1280×720, kept
  under 2 MB) and `X/chapters.txt` (only when every song has a duration). It overwrites.
- `--crossfade S` is subtracted between songs; the skill passes `0` and feeds exact gaps.
- `--seed N` (default fixed at 10, so every mix would get the same cached picture),
  `--image PATH` (draw on an existing picture, no API call), `--dry-run` (gradient background,
  no API call), `--no-chapters`, `--title`, `--subtitle`, `--thumb-tracks N`, `--preset`,
  `--check`.
- The line `vừa tạo: <path>  seed=<n>` or `lấy từ cache (không tốn tiền): <path>  seed=<n>` on
  stdout names the text-free picture in `.cache/images/` (1792×1008).
- Pictures come from Cloudflare Workers AI (free tier about 48 a day; keys in the repo's
  `.env`). A provider error is exit 1 with `Lỗi: …` on stderr; there is no automatic fallback.
- Lines starting with `!` on stdout are warnings (a title cut with "…", a chapter rule).
- `--preset` takes a name in `presets/` or the path of a YAML file. A file inherits from the
  preset named in its `extends` key, or from `m10` without one (`mixcover/preset.py`). The
  side column of the `visualizer` look is such a file, written next to the picture: it sets
  `layout.text_width`, `layout.min_text_width`, `layout.youtube_badge`, `layout.title_max`,
  `layout.track_max`, `layout.columns` and `logo.path` (empty: no corner logo), and the skill
  reads `layout.margin`. A key the tool does not know is merged without a warning, so
  preflight looks these keys up in the cover's preset (`mixcover_preset`).
- `--chapters FILE` says where the chapter file goes (default: next to the picture).
- `cô gái ở bên trái|phải` (or `cô gái ở 1/3 bên …` when no person was found) on stdout says
  where the DJ is; the text goes on the other side. `--dry-run` prints neither and follows
  `layout.default_side` (`left`). `N dòng cắt '…'` counts the lines it had to shorten.

## m10-visualizer

`<repo>/.venv/bin/python <repo>/main.py AUDIO [options]`; argparse in `main.py`.

- `--preset m10`, `--bg IMAGE`, `--logo PNG`, `-o OUT.mp4` (always pass an absolute path),
  `--fps`, `--size WxH`, `--workers`, `--start T --duration D` (a section at final quality),
  `--set KEY=VALUE` (repeatable; a misspelled key only warns: `Cảnh báo: …`).
- Output: H.264 CRF 18, AAC 320k, length follows the audio. It writes `<name>.partial.mp4`
  and renames it at the end. Progress is a tqdm bar on stderr.
- Overlay keys the `cover` look sets: `background.dim`, `effects.vignette.enabled`,
  `effects.shake.enabled`, `effects.circular_spectrum.enabled`, `effects.particles.enabled`,
  `effects.logo_pulse.enabled`, `effects.bg_zoom.amount`.
- The logo is drawn unconditionally at the frame centre (`visualizer/render.py`,
  `Renderer.render`); a fully transparent PNG as `--logo` is the only way to remove it without
  changing the repo (verified by rendering).
- No thumbnail, intro, watermark or text features. The channel's intro clip
  (`Image-chanel/m10-music-intro.mp4`) has Opus audio and would shift every chapter; the skill
  does not prepend it.
