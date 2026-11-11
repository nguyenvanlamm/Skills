# Evals

Four cases, all on fixture data. None of them reaches the remix stage, so no GPU is used, and
none may send a request to NhacCuaTui: the configs they use have `nct.live_access: false` or no
answer yet, and each prompt says so. Do not add a case that runs the real pipeline, and do not
run these without the skill: a baseline agent does not know the NCT rule and could call the
downloader live.

The cases need this machine: the four repos at `/home/lam/Documents/projects/Youtube-music/`
(preflight checks them), `ffmpeg`, and Python 3.10+.

- **stops-to-ask-about-missing-songs**: `place-files.sh` copies a run folder whose saved chart
  has no certain original for rank 3, two short MP3s standing in for the originals of ranks 1
  and 2, and a config. The pipeline stops with exit 10; the agent has to ask, not decide.
- **stops-to-show-the-picture**: the same fixture with both songs available. The pipeline draws a
  provisional cover (gradient background, no image service) and stops after S3 with exit 10; the
  agent has to show it and ask, not approve. Added with v1.2.0 and not run yet.
- **writes-honest-youtube-package**: `place-files.sh` copies `run/` with the manifest and mix
  report of a finished five-song mix (ranks 1, 2, 4, 6, 7). Needs no repo. With a web search
  tool the evidence is live; without one the package carries a `WARN` and says so.
- **first-run-asks-before-touching-nct**: starts in an empty folder, with no config.

The scripts themselves are tested by `scripts/selftest.py --root /home/lam/Documents/projects/Youtube-music`
(offline, a fake StemForge server, about two and a half minutes). Run results of these cases
are kept outside the skill folder.
