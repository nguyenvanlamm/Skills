# Changelog

## v2.0.0 — 2026-11-22

The video is now a 2D cartoon instead of two portraits and a waveform.

- Characters are vector puppets drawn in code (17 poses, 16 emotions, hair, hats, outfits): idle
  bob and sway, blinks, squash on cuts, pose changes with overshoot, walking in and out, lip
  movement from the loudness of the voice.
- Four sets (`home`, `office`, `street`, `void`) at day, dusk or night with lamp and window
  lighting; three shot kinds (`wide`, `closeup`, `walk`); slow push-in on every shot, whip pan
  when the place changes; pop-in word labels and place tags.
- Storyboard in `dialogue.json` (`cast`, `scenes`), described in `references/scene-rules.md` and
  checked by `validate_dialogue.py`. Cues are words of the text, so the picture lands on the
  voice. Characters left undirected gesture by themselves; a dialogue with no `scenes` gets a
  plain generated storyboard, so old episodes still render.
- `episode.json` gains `cast`, `shots` (timed) and `mouth` (one shape per frame);
  `scripts/pipeline/scenes.py` builds them.
- The picture fills the frame. Each line is shown in a speech bubble that pops out of its speaker:
  words turn solid as they are spoken, new words carry a yellow marker. The caption block and
  the progress bar at the bottom are gone.
- Thumbnail and cover show the cartoon characters. Removed: the generated portraits and
  `portraits.py`, the compositions `Dialogue16x9`/`Dialogue9x16` (now `Toon16x9`/`Toon9x16`).
- A change in any file under `scripts/video/src/` now makes stills and videos render again.
- The puppet, the motion formulas and the sets are a rewrite in SVG for Remotion of the Python
  engine of the "2d-long-form" skill (see `scripts/video/CREDITS.md`). Not carried over: bloom,
  music and sound effects, charts, maps, props.

## v1.2.0 — 2026-11-21

- YouTube upload (`scripts/pipeline/upload.py`, `youtube.py`), run only when the user asks: the
  16:9 video with its thumbnail, then the Short with a link to it. Always private with a scheduled
  release (`--publish-at`). `plan` is a dry run; `push` records its work in `out/uploaded.json`,
  continues an interrupted upload and never sends a finished video twice.
- One-time Google sign-in: `upload.py auth`, described in `references/upload-setup.md`.
- The steps pane shows an upload row for a level once `upload.py` has touched it.
- `publish.json`: `youtube.visibility` is now the API value `private`.

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
