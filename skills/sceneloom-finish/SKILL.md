---
name: sceneloom-finish
description: Finish a sceneloom video, assemble the clips, voice, subtitles, opening hook text and music into final.mp4, look at frames of the result, then write the publishing package (titles, description, tags, hashtags, pinned comment, chapter marks, thumbnails) and check it against platform limits. Last of four sceneloom skills (script, visuals, sound, finish). Use whenever the user wants a sceneloom project put together, re-exported or prepared for upload, even without naming the skill, "ghép video", "dựng video hoàn chỉnh", "xuất final", "nhạc to quá, ghép lại", "soạn tiêu đề mô tả YouTube cho video này", "làm thumbnail", "viết SEO cho video", "assemble the sceneloom video". Don't use for uploading to YouTube or TikTok (it never uploads), writing the script (sceneloom-script), pictures or clips (sceneloom-visuals), making voice or music (sceneloom-sound), or SEO for websites and app stores (search-optimizer, aso-marketing).
---

# sceneloom-finish

Input: a sceneloom project whose clips exist (voice and music if the video has them).
Output: `<project>/final.mp4`, `<project>/seo.txt`, `<project>/thumbs/thumb_N.jpg`, with the
`edit` and `seo` steps done. Nothing is uploaded.

## Where things live

- `<sceneloom>`: `/home/lam/Documents/projects/sceneloom`. Run every command from that folder with
  `.venv/bin/python -m sceneloom ...` (written `sceneloom ...` below).
- `<project>`: printed by `sceneloom status <id>`.
- Settings that shape the result, in `<sceneloom>/settings.json`: `"height"` (720 or 1080),
  `"fps"`, `"music_volume"` (default 0.15), `"music"` (false = no music), `"encoder"`
  (`cpu` is the fastest on this machine; measured against NVENC).
- Code this skill owns: `sceneloom/editor.py` (scene normalising, subtitles, hook text, mixing,
  thumbnails), `step_edit`, `finish_seo`, `seo_problems`, `chapter_timestamps` in
  `sceneloom/pipeline.py`, and `sceneloom/review.py`. Run
  `python3 -m unittest discover -s tests` after a code change.

## Part 1: assemble

1. **Check what is there**: `sceneloom status <id>`. `clips` must show ✔. If `audio` is not done,
   say so and ask whether to finish without sound or run `sceneloom-sound` first; a narrated
   video without voice has subtitles only.
2. **Assemble.**

   ```bash
   sceneloom run <id> --only edit
   ```

   Each scene lasts as long as its voice (plus half a second), or the scene length when there is
   no voice. Subtitles follow the voice's word timings. The hook line shows for the first three
   seconds. Music is levelled, looped and mixed under the voice, and the whole track is brought
   to −14 LUFS.
3. **Look at the result.**

   ```bash
   sceneloom sheet <id> --what final
   ```

   Open the sheets with the Read tool. The first frame is taken at 0:01 to show the hook text;
   the others are the middle of each scene. Check that:
   - the hook text is fully inside the frame and readable;
   - subtitles are inside the frame, at most two lines, with all accents drawn;
   - no scene is black or shows the wrong picture.

   A long narration line is shown as several subtitle pages of up to two lines, one after the
   other, so a frame from the middle of a scene may show only part of a sentence; that is not an
   overflow. An overflow is text running past the edge of the frame, or more than two lines on
   screen at once: have that line shortened with `sceneloom-script`, remake its voice with
   `sceneloom-sound`, and assemble again.
4. **State the facts** from `sceneloom status <id>`: `Final video:` gives the length, `Clips:` how
   many clips really move and how many are slow zooms, `Voice:` which scenes have no voice and
   whether there is music, and `Made by:` which provider made the pictures, clips, voices and
   music. Anything marked "(placeholder)" was made by the mock: say plainly that the video cannot
   be published as it is, and which skill remakes those parts (`sceneloom-visuals`,
   `sceneloom-sound`). "unknown" means the project was made before sceneloom recorded this. You cannot hear the mix; ask the user to listen to the first 20
   seconds for voice against music. Too loud or too quiet: change `"music_volume"` and run
   step 2 again (it takes seconds; nothing else is remade).

## Part 2: the publishing package

5. **Get the facts.**

   ```bash
   sceneloom seo facts <id>
   ```

   It prints the title, summary, language, length, the chapter marks computed from the real scene
   lengths, whether they will go into the description (`chapters_in_description`, with the reason
   in `chapters_note` when not: YouTube only shows chapters when there are at least three, each
   10 seconds or longer), and the genre's audience note.
6. **Write `<project>/seo.json`.** Read `references/publish-rules.md` first; it has the shape,
   the limits and the honesty rules. Do not put chapter marks in the description yourself: the
   import adds the computed ones when YouTube can use them, and leaves them out otherwise.
7. **Import it.**

   ```bash
   sceneloom seo import <id> <project>/seo.json
   ```

   Fix every `FAIL` line in the file and import again until it prints `OK`. The import writes
   `seo.txt` and one thumbnail per thumbnail text.
8. **Look at the thumbnails** (`<project>/thumbs/`) with the Read tool. To choose the scene
   picture behind each thumbnail text, add `"thumbnail_scenes": [4, 7, 9]` to seo.json (one scene
   number per text; by default they are spread over the video) and import again. The text must be fully
   inside the picture and must not cover the main face. If it does not fit, shorten that
   thumbnail text and import again. A thumbnail is drawn on a scene picture spread across the
   video; if the picture is a poor choice, say which scene would be better.

## Report

Give the paths of `final.mp4`, `seo.txt` and the thumbnails, the length, and plainly what is not
perfect (zoom clips, silent scenes, a picture you flagged). Uploading is the user's job.

## Don't

- Don't upload or schedule anything.
- Don't claim the mix sounds right; you checked pictures and numbers, not sound.
- Don't write claims the video does not deliver (see the rules file).
