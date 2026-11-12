# Changelog

## v1.1.0 — 2026-11-12

- Steps pane (`scripts/pipeline/steps_pane.py`): a herdr pane to the right of the chat that shows
  which step the episode is at, for both levels, with the running step's clock and the last FAIL
  line. Without herdr, `steps_pane.py once` prints the same block for the chat.
- `run.py` writes `progress` to `state.json` (current step, steps done in this run, error).

## v1.0.0 — 2026-11-12

First version.

- French word list → A2 and B1 two-person dialogues (Léa and Hugo), each 2-3 minutes.
- Edge TTS voices with word timings; karaoke captions with the new words highlighted.
- Remotion render at 60 fps: 1920×1080, 1080×1920 and a 30-60 second vertical cut, each opening
  with a spoken hook.
- Thumbnail (1280×720) and vertical cover (1080×1920).
- Upload fields for YouTube, YouTube Shorts and TikTok, checked against platform limits and
  built on real YouTube search suggestions (`keywords.py`).
- Output checks: size, frame rate, duration, loudness (−14 LUFS), black frames.
