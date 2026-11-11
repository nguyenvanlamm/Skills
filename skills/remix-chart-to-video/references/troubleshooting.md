# When a stage exits 1

`pipeline.py status --run RUN` shows the failed stage and its `error`; `RUN/logs/` holds the
tools' own output. Fix the cause, then run the same `pipeline.py run` command again: finished
stages and finished songs are kept.

| Stage | Symptom | Cause and fix |
|---|---|---|
| preflight | `stemforge_env` FAIL | StemForge was moved: run `uv sync --locked` in its folder. If `--locked` errors or wants to download large packages, stop and ask the human |
| preflight | `flags_*` FAIL | a repo changed a flag, route or preset key: read `repo_contracts.md`, open the named file, tell the human; do not patch the repo |
| preflight | `ports` FAIL | another program holds 8765 or 8001 (seen: a site preview on `python3 -m http.server 8765`). Give the skill a free port with `pipeline.py set remix.port N` (StemForge is started on that port), or ask the human to close the other program. A leftover ACE-Step from a crashed run: `pipeline.py stop --run RUN`. Never stop a process the skill did not start. The check is skipped once every remix of the run is done |
| preflight | `ports` WARN | a StemForge server is already running. The skill will use it and not stop it, and cannot turn off its 7-day job clean-up; ask the human to close it if old jobs matter |
| preflight | `gpu` WARN | less than about 10 GB of VRAM free: close GPU applications before the remix stage |
| preflight | `disk` FAIL | not enough room for the StemForge jobs: free space, or set `remix.cleanup_jobs` to `delete_after_copy` |
| init / originals | downloader exit 2 | NCT is off or unreachable. Off: offline mode (`--html`, `RUN/sources/`). Unreachable or "page changed": stop and tell the human; do not retry in a loop |
| originals | exit 10 | not a failure: songs are missing, the human decides (SKILL.md, Step 2) |
| art | provider error, quota or key | Cloudflare's free tier ran out (it resets at 00:00 UTC) or a key is wrong. Options for the human: wait, set `cover.image` to an existing picture, or `cover.dry_run` for a gradient cover |
| art | safety filter | another seed: `pipeline.py set cover.seed N` |
| remix | `Server StemForge thoát ngay` | read `RUN/logs/stemforge.log`. Usually the GPU lock (a StemForge CLI or server is running) or the venv |
| remix | `StemForge chưa sẵn sàng` | `missing` names absent model files: the human has to run StemForge's `scripts/auto_remix_setup.py` (it downloads) |
| remix | exit 10 with `cuda_oom`, `acestep_crashed`, `stalled` | the human chooses retry, skip or backfill. For `cuda_oom` free VRAM first |
| mix | `true_peak` FAIL | the trim did not bring the peak under the limit: report it with the numbers, do not ship the mix |
| mix | transitions `WARN` | a handover fell back to a crossfade (different tempo, no beat to measure). Not a failure; the human listens to `transitions_preview.mp3` |
| cover | `chapters_match` FAIL | mixcover's times differ from the mix. Do not edit either; report both lists |
| video | `cover_readable` FAIL | something is drawn over the text: check `logs/visualizer.log` for `Cảnh báo:` (a preset key was renamed), look at `video/frames/` |
| video | `video_length` FAIL | the render stopped early: read `logs/visualizer.log`, run the stage again |
| youtube | exit 20 | not a failure: write `youtube/youtube.json` (references/youtube_metadata.md) |
| any | the pane warns "Không có cập nhật" | the process may have died. `pipeline.py status`; if nothing is running, run the same command again |

After a crash that left a server behind, `pipeline.py stop --run RUN` stops the StemForge
server that run started. It never touches a server the skill did not start.
