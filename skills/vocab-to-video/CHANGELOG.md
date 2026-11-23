# Changelog

## v2.2.0 — 2026-11-24

A storyboard model that runs on this machine. Off by default: the storyboard is still written
by hand, and nothing changes until `config.json` → `storyboard.provider` is set.

Pipeline
- `storyboard.py`: asks a local model (Ollama) for `scenes`, with the answer held to a JSON
  schema built from the rig, so poses, sets and characters are always valid names. The answer
  goes through the same validator as a hand-written storyboard; its errors and warnings go back
  to the model for up to three more tries, stopping early when the model repeats itself. When
  the tries run out on wrong cue words, those beats are dropped and those labels moved to the
  scene that says the word, instead of losing the whole storyboard. No model, no server or no
  valid answer: a `WARN` and the plain generated storyboard, as before.
- `run.py` calls it before `validate` when `dialogue.json` has no `scenes`, saves the result in
  the file, and never replaces a storyboard already there. `--storyboard-only` stops after it.

Training (`scripts/train/`, its own `uv` project)
- `make_dataset.py`: checked dialogues to chat examples, with a fixed evaluation set and repair
  lessons (a storyboard with typical mistakes, the checker's words, the right answer).
- `finetune.py`: a QLoRA adapter on `Qwen/Qwen3.5-9B` in 4-bit; fits a 12 GB card.
- `export.py`: merges the adapter into the base, converts to GGUF, quantizes, registers in Ollama.
- `eval_storyboard.py`: valid, first try, salvaged, tries, time and the shape of the storyboards
  next to the plain one and the hand-written one.
- `dataset-brief.md`: the brief for writing training dialogues in parallel batches.
- Measured on 12 held-out dialogues, the best run (about 700 training dialogues) gives a valid
  storyboard for all 12 in about 90 s each, with fewer gestures than hand-written ones.
- `references/local-model.md`: install, train, export, measure, train again.

## v2.1.0 — 2026-11-22

Fixes from an independent review: a first-time run of the skill, a review of the pipeline and a
review of the drawing code.

Picture
- Walk scenes stay in the frame: in 9:16 the camera follows the walkers; the paths start and
  end inside the picture; the legs step with the distance covered, so feet no longer slide.
- The 9:16 frame shows the characters 12% larger and less empty sky and floor.
- Bubble text: no word changes size any more (words used to touch: "prendl'appartement");
  words not yet spoken are a readable grey, and the yellow marker of a new word is solid from
  the start; larger type in 16:9.
- A bubble never follows the picture into the next shot, fades with a whip pan, and follows a
  speaker who is walking in or out instead of pointing at an empty spot.
- Labels are placed on the frame, not in the set: the push-in no longer moves them into the
  title. Wide shots: over the listener, gliding across when the speaker changes. Closeups:
  behind the character. A bubble with no speaker in a closeup goes to the bottom, off the face.
- The place tag leaves after four seconds; in 9:16 it sits under the title, not on the legs.
- The whip pan stays inside the drawn set; night light pools follow a moving character; the
  `worried` face keeps its mouth shut, so a listener no longer seems to talk.
- Thumbnail and cover: the opening set, dimmed, behind the text; the headline word is not
  repeated as a chip; any number of speakers.
- Lip movement is judged per line, so the quieter voice opens its mouth as wide as the other.

Pipeline
- `upload.py plan/push` refuse a video that is older than its dialogue or the video design, or
  that was rendered again and not checked.
- Cues: a word inside another word no longer matches (`loyer` in `employer`); elision works for
  short words (`un an` in `d'un an`); accents may be left out; a beat with `who` lands on that
  character's own line; in the short cut a cue of a line that was cut is dropped instead of
  moving to a similar word. `+seconds` must be a plain number and is kept inside the shot.
- The validator answers malformed input with `FAIL` lines instead of a traceback, and checks
  `zoom`, `x`, `y`, `s`, `face`, `skin`, duplicate characters. New warnings: a cue said twice, a
  beat on a speaker who is not in the picture, the hook speaker walking in, `tiphat` without a
  hat, two labels in a scene, a shot under 1.2 s, digits, brackets, a long title, more than two
  new words in a turn. A vocabulary use matched by two forms counts once.
- `metadata.json` is checked during `validate`, before any speech is made. `--until build` and
  `--until publish` stop where they say.
- `check` writes one frame per shot and tiles them into contact sheets, instead of three frames
  per video. A chapter that could not be placed is named.
- Speech is reused by content, so adding turns costs only their own calls; a failed call can no
  longer leave half a file that passes for finished audio. `state.json` and every JSON file are
  written atomically. Errors end as a `FAIL` line the steps pane can show.
- Two runs on one machine take turns at the renderer (they used to crash each other's bundler
  cache). Videos are also rendered again when the fonts, `package-lock.json` or
  `remotion.config.ts` change.
- Tests: 52 (were 24).

Not changed: the shop sign is still cropped in 9:16 street shots, a label can sit over a set
prop (clock, sun), outfits and hair are still if-chains in `Puppet.tsx`.

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
