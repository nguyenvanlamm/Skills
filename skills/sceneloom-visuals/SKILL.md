---
name: sceneloom-visuals
description: Draw the pictures and clips of a sceneloom video from its finished script, reference pictures of the fixed cast, one picture per scene, one clip per scene, then look at every picture and redraw the ones that do not match the script. Second of four sceneloom skills (script, visuals, sound, finish). Use whenever the user wants the images or clips of a sceneloom project made, checked or redone, even without naming the skill, "vẽ ảnh cho video", "tạo ảnh các cảnh", "làm clip cho project", "vẽ lại cảnh 6", "nhân vật bị sai, vẽ lại", "kiểm tra ảnh các cảnh", "draw the scenes of the sceneloom project". Don't use for writing or changing the script (sceneloom-script), voice or music (sceneloom-sound), assembling the video or YouTube texts (sceneloom-finish), cover art for music mixes (lofi-ballad-to-video) or store screenshots (appstore-assets).
---

# sceneloom-visuals

Input: a sceneloom project whose `script` step is done. Output: `entities/*.png` (reference
pictures of the cast), `images/scene_NNN.png` and `clips/scene_NNN.mp4`, with the `entities`,
`images` and `clips` steps done, and every picture looked at by you.

The pipeline draws; you are the eyes. Image models make mistakes no code check finds: two
lanterns instead of one, the wrong person, garbled letters, a sixth finger. Catching them here
is the main reason this skill exists.

## Where things live

- `<sceneloom>`: `/home/lam/Documents/projects/sceneloom`. Run every command from that folder with
  `.venv/bin/python -m sceneloom ...` (written `sceneloom ...` below).
- `<project>`: printed by `sceneloom status <id>`; `sceneloom list` shows all projects.
- The providers are chosen in `<sceneloom>/settings.json` (`"combo"` → `"image"`, `"video"`).
  The image provider today is FLUX.2 klein on Cloudflare Workers AI; its keys are in
  `<sceneloom>/.env`. `"video": "still"` means each clip is a slow zoom on the picture.
- Code this skill owns: `step_entities`, `step_images`, `step_clips` and `mark_redo*` in
  `sceneloom/pipeline.py`, the media prompts at the bottom of `sceneloom/prompts.py`,
  `sceneloom/providers/cloudflare.py`, `sceneloom/review.py` (contact sheets) and
  `media.still_clip`. A new image or video service is a new `Provider` subclass; the contract is
  at the top of `sceneloom/providers/base.py`. Run `python3 -m unittest discover -s tests` after
  a code change.

## Before you start

1. `sceneloom status <id>`: the `script` step must show ✔. If not, that is `sceneloom-script`.
2. **Count the cost.** Pictures needed = entities + scenes still missing. On Cloudflare one
   1280×720 picture uses about 160 of the 10,000 free neurons per day, so roughly 60 pictures a
   day. If the project needs more than that, tell the user and ask whether to split it over days
   or switch provider. For a dry run that costs nothing, see "Dry run" below.

## Steps

1. **Draw the cast.**

   ```bash
   sceneloom run <id> --only entities
   sceneloom sheet <id> --what entities
   ```

   It writes numbered sheets to `<project>/review/entities_N.jpg` and prints their paths. Open
   each one with the Read tool and compare every picture with that entity's `look` in
   `<project>/visual_bible.txt`: right age, hair, outfit colors (or fur and markings for an
   animal); one character per sheet; places without people. A wrong reference spoils every scene
   that uses it, so fix these first:

   ```bash
   sceneloom redo <id> --entities mai,ong_tu
   sceneloom run <id> --only entities
   ```

2. **Draw the scenes.**

   ```bash
   sceneloom run <id> --only images
   sceneloom sheet <id> --what images
   ```

   Open every sheet and check each numbered picture against its scene in `<project>/script.txt`:
   - the right people, recognisably the same as their reference picture;
   - the action and the place the scene describes;
   - the right number of things (one lantern, two people);
   - no letters or signs, no extra limbs or melted faces;
   - day or night as the story needs.

   When a small picture on the sheet is unclear, open `<project>/images/scene_NNN.png` itself.

3. **Redraw what is wrong**, at most two rounds per scene:

   ```bash
   sceneloom redo <id> --scenes 6,9
   sceneloom run <id> --only images
   ```

   A redraw rolls the dice again with the same words. If the same mistake comes back, the words
   are the cause: say so and have the scene's `visual` rewritten with `sceneloom-script`
   (for example "holding one red paper lantern in her right hand" instead of "the lanterns").
   After two rounds, stop and list what is still imperfect; don't loop on quota.

   A mark deletes nothing: the old picture and clip stay in use until a new one has been drawn
   and checked, and a failed redraw keeps the old one. Marked scenes show as "N redo" on the
   sheet and are listed by `sceneloom status <id>`. Marking also sends `edit` and `seo` back to
   pending, because the finished `final.mp4` no longer matches; the old file stays on disk until
   the next assembly.

   When the user only wants the pictures checked, or today's allowance is used up, stop after
   `redo`: the next `run --only images` draws exactly the marked scenes. List each scene you
   marked and what is wrong in it, plus the borderline ones you did not mark, so the user can
   decide; `sceneloom redo <id> --undo --scenes 3` takes a mark back (`--undo` alone takes back all).

   **When a picture contradicts its scene because of a reference.** The scene prompt tells the
   model to keep the look of every attached reference, so the reference wins over the scene text:
   a lantern drawn lit in its reference comes back lit in a scene where its candle has just gone
   out. Before redrawing such a scene, have the script changed with `sceneloom-script`: state the
   different state plainly in `visual`, and take that entity out of the scene's `refs`.

4. **Make the clips.**

   ```bash
   sceneloom run <id> --only clips
   ```

   The last log line, and the `Clips:` line of `sceneloom status <id>`, say how many clips really
   move and how many are slow zooms on the picture: `zoom` means the video provider has no video
   model (today's setting, `"video": "still"`), `fallback` means the model refused or failed for
   that scene (`status` prints the reason). To retry one fallback:
   `sceneloom redo <id> --scenes 4 --what clip`, then run again.

5. **Report**: how many pictures were drawn, which scenes you had redrawn and why, anything still
   imperfect, how many clips are real motion and how many are zooms (say plainly when none
   move), and where the sheets are (`<project>/review/`). Then offer `sceneloom-sound`.

## Dry run

`--provider mock` on every `run` costs nothing and draws nothing real: each picture is a colored
card with the start of its prompt printed on it (and "[N reference image(s)]" when references
were attached), and each clip is a slow zoom on that card. A dry run can check the plumbing
only: one picture per entity and per scene, the right references attached to each scene, the
prompts naming the right people and place. It cannot check a drawing against the script; say so
instead of reporting the pictures as correct.

The dry run marks `entities`, `images` and `clips` done. Before drawing for real, forget it all,
then run with the real provider:

```bash
sceneloom redo <id> --step entities     # every reference picture, scene picture and clip
sceneloom run <id> --only entities      # then go on with steps 1-4 above
```

## When a run stops

Every run can be repeated; finished pictures are kept. Read the message:

- `today's free allowance is used up`: Cloudflare's daily quota; it resets at 00:00 UTC
  (07:00 in Vietnam). Report it and stop; do not switch provider on your own.
- `refused` / `blocked by the safety filter`: the pipeline already tried a softer rewrite. Have
  the scene rewritten more gently with `sceneloom-script`.
- `rejected the token`: the keys in `<sceneloom>/.env` are wrong or expired; ask the user.

## Don't

- Don't call the pictures done without opening the sheets.
- Don't edit `project.json` by hand to change a scene; go through `sceneloom script export` and
  `import`, which keep the checks and the unchanged pictures.
- Don't print or copy the keys in `.env`.
