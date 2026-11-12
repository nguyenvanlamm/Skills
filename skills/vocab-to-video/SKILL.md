---
name: vocab-to-video
description: Turn a list of new French words into A2 and B1 two-person dialogues and render each as a 2-3 minute podcast video (two speaker portraits, voice waveform in the middle, karaoke captions on top, new words highlighted) in 16:9 and 9:16 at 60 fps, plus SEO-ready upload fields for YouTube, YouTube Shorts and TikTok. Use when the user gives French vocabulary and wants a dialogue video, or says "làm video từ vựng", "tạo hội thoại từ các từ này", "vocab to video", "làm tập podcast tiếng Pháp". Don't use for uploading to YouTube, translating, or videos that are not French dialogues.
---

# vocab-to-video

Input: a list of French words or expressions. Output: for each level (A2 and B1 unless the user
names one) a dialogue, two full-length MP4 files (1920×1080 and 1080×1920, 60 fps, 2-3 minutes),
a 30-60 second vertical cut for Shorts and TikTok (`out/*_short_9x16.mp4`),
the upload fields for YouTube, YouTube Shorts and TikTok (`out/publish.md`, `out/publish.json`),
a YouTube thumbnail (`out/*_thumbnail.jpg`, 1280×720) and a vertical cover (`out/*_cover.jpg`, 1080×1920).

You write the dialogue and the upload texts; `scripts/pipeline/run.py` does everything else.

## Where things live

- `<skill>`: the folder holding this file. The code is in `<skill>/scripts/`: `pipeline/` (Python,
  run with `uv`), `video/` (Remotion project) and `assets/` (speaker portraits, fonts).
- `<episodes>`: where episodes are written. Default
  `/home/lam/Documents/projects/Youtube/Youtube-Podcast-Francais/episodes`; use another folder if
  the user names one. Always pass episode paths as absolute paths.
- First run on a machine: `npm install` in `<skill>/scripts/video` (`uv run` installs the Python
  side by itself). `ffmpeg` and `ffprobe` must be on the PATH.

## Steps

1. **Read the words.** Take them from the user's message (or a file they name). Fix obvious typos
   and say so. If the list has more than 12 words, split it into several episodes and tell the user.
2. **Create the episode folder** `<episodes>/<YYYY-MM-DD>_<slug>/` (slug: 1-3 ASCII words for the
   theme). Save the words, one per line, to `words.txt`. Create `A2/` and `B1/` inside.
   Then open the steps pane, so the human can see which step the work is at:

   ```bash
   python3 <skill>/scripts/pipeline/steps_pane.py open <episodes>/<name>
   ```

   It splits a pane to the right of the chat and keeps itself up to date from the files you write
   and from what `run.py` reports; you never update it by hand. Exit 69 means herdr is not
   available: print the output of `steps_pane.py once <episodes>/<name>` in the chat at each step
   change instead. Leave the pane open when the work ends; close it (`steps_pane.py close`) only
   when the human says so.
3. **Write `<LEVEL>/dialogue.json`** for each level. Read `references/dialogue-rules.md` first and
   follow it exactly: it holds the JSON schema, the level rules, the length targets, and the rules
   for the opening hook (first 3 seconds) and the short cut. The two
   levels are two different conversations on the same theme, not one text rewritten.
4. **Fetch search data**, once per episode, from `<skill>/scripts/pipeline/`, with 3-5 theme queries:

   ```bash
   uv run python keywords.py <episodes>/<name> "vocabulaire logement français" "louer un appartement français"
   ```

   It saves real YouTube search suggestions to `keywords.json`. If the network call fails, report
   it; don't invent keywords.
5. **Write `<LEVEL>/metadata.json`** for each level: titles, description intro, tags, hashtags,
   TikTok caption, cover and thumbnail text, and a short French definition of every new word.
   Read `references/publish-rules.md` first; it holds the format, the platform limits and the SEO
   rules, including how to use `keywords.json`. Chapters, the vocabulary list and the transcript are added by the script.
6. **Run the pipeline**, once per level, from `<skill>/scripts/pipeline/`:

   ```bash
   uv run python run.py <episodes>/<name>/<LEVEL>
   ```

   Steps inside: validate → tts → build → publish → thumbnail → render → check. Rendering takes a few minutes per video,
   so run the two levels in the background and wait for them.
7. **Fix and rerun when a step fails.** The script prints `FAIL` lines that say what to change:
   - validation errors (word missing, line too long, word count out of range): edit `dialogue.json`;
   - audio shorter than 120 s or longer than 180 s: add or remove turns, keeping every new word;
   - short cut outside 30-60 s: widen or narrow the `short` line range;
   - `[publish]` errors (title too long, level or keyword missing, tag budget, hashtag format):
     edit `metadata.json`.
   If you change the dialogue after writing `metadata.json`, reread the metadata: the intro and
   the vocabulary notes must still describe the final text.
   Rerunning is cheap: unchanged lines keep their audio and up-to-date videos are not rendered again.
   Use `--until thumbnail` to stop before rendering while you adjust the texts.
8. **Look at the images.** After `check`, open the thumbnail, the cover and the three JPEGs per
   video listed under `<LEVEL>/check/` with the Read tool. On the thumbnail the headline must not
   touch the portraits or run off the edge; if it does, shorten `thumbnail_text` and rerun. Confirm the caption fits, the speaking portrait is lit, and
   new words are yellow. If a caption overflows, shorten that line and rerun.
9. **Report** the six video paths (`<LEVEL>/out/*.mp4`), each one's duration, the dialogue titles,
   the thumbnail and cover paths, the path of each `out/publish.md` with its YouTube title, and any warning the script printed. Say plainly if something failed or was skipped.

## Rules

- Never upload or publish anything; this skill only produces files. The upload fields are drafts
  for the user to paste.
- Don't change `scripts/pipeline/config.json` (voices, speeds, length targets) unless the user asks.
- Speakers are fixed: `lea` (Léa, female voice, left) and `hugo` (Hugo, male voice, right).
  Portraits live in `scripts/assets/speakers/`; if they are missing, run `scripts/pipeline/portraits.py` with the
  interpreter named in that file's docstring.
- Speech comes from Edge TTS, an online service: a network error is retried by the script; if it
  keeps failing, report it instead of switching to another voice provider.

## Useful commands

```bash
# the steps pane: open it, print it once as plain text, close it
python3 steps_pane.py open|once|close <episodes>/<name>
# only check the text
uv run python validate_dialogue.py <episodes>/<name>/A2/dialogue.json
# only rebuild the upload fields (after build has run once)
uv run python publish.py <episodes>/<name>/A2
# one output only (16x9, 9x16 or short_9x16)
uv run python run.py <episodes>/<name>/A2 --format short_9x16
# preview in Remotion Studio (from <skill>/scripts/video/)
npx remotion studio --props=<episodes>/<name>/A2/episode.json --public-dir=<episodes>/<name>/A2/public
```
