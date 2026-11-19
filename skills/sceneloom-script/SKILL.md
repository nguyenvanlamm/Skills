---
name: sceneloom-script
description: Write the scene-by-scene script of an AI video in sceneloom, from an idea, a plot or a title to a checked script (title, opening hook, chapters, fixed cast, and for every scene the picture, camera, motion and narration), or revise an existing one. First of four sceneloom skills (script, visuals, sound, finish). Use whenever the user wants a video script for an AI-made story, cooking or narrated video, even without naming the skill, "viết kịch bản video", "lên kịch bản cho video AI", "tạo project sceneloom mới", "sửa lời kể cảnh 5", "làm video truyện kể về ...", "thêm thể loại mới", "write the script for a sceneloom video". Don't use for drawing pictures or clips (sceneloom-visuals), voice or music (sceneloom-sound), editing or YouTube texts (sceneloom-finish), French vocabulary dialogues (vocab-to-video) or music mixes (lofi-ballad-to-video, remix-chart-to-video).
---

# sceneloom-script

Input: an idea, a plot, or just a title, plus a genre. Output: a sceneloom project whose `script`
step is done: `project.json` holds the bible (title, hook, chapters, cast) and every scene, and
`script.txt` and `visual_bible.txt` hold the same in a form a person can read.

You write the script. The code checks it: it cannot tell a good story from a dull one, but it
catches everything that makes an image or video model fail (non-English picture text, vague shots,
written words in the picture, narration too long to say, repeated lines, repeated pictures, too
long in one place). Fixing those here is far cheaper than after the pictures are drawn.

## Where things live

- `<sceneloom>`: `/home/lam/Documents/projects/sceneloom`. Run every command from that folder with
  `.venv/bin/python -m sceneloom ...` (written `sceneloom ...` below).
- `<project>`: `<sceneloom>/output/<slug>-<id>/`, where the slug comes from the `--title` given to
  `new` (`video-<id>` when there was none). The id is what every command takes;
  `sceneloom status <id>` prints the folder, and `sceneloom list` shows every project with its id
  (the newest last), which is how to find "the latest project".
- Genres: `<sceneloom>/genres/*.json`. `sceneloom genres` lists them.
- Code this skill owns, when the user asks to improve script writing itself:
  `sceneloom/checks.py` (the rules), `sceneloom/planning.py` (scene and cast counts),
  `sceneloom/prompts.py` (text prompts for the automatic writer), `import_script`, `export_script`
  and `step_script` in `sceneloom/pipeline.py`, and the genre files. After a code change run
  `python3 -m unittest discover -s tests` in `<sceneloom>`.

## Steps for a new video

1. **Pick the genre.** Run `sceneloom genres`, choose the one that fits, and read its JSON file:
   `script_brief`, `chapter_pattern`, `scene_rules`, `cast_hint` and `visual_style` are your brief.
   If nothing fits, see "A new genre" below.
2. **Create the project.** Pass only what the user decided; the genre supplies the rest.

   ```bash
   sceneloom new --genre truyen-ke --notes "ý tưởng của người dùng" --minutes 1
   ```

   Options: `--title`, `--minutes`, `--aspect 16:9|9:16|1:1`, `--seconds-per-scene`, `--chapters`,
   `--lang`, `--no-narration`. It prints the id, the folder, and how many scenes and chapters the
   length needs. Write to those numbers. Of the two "Next" lines it prints, yours is
   `script import`; the other one hands the writing to the pipeline (see the end of this file).
3. **Write `<project>/script.json`.** Read `references/script-rules.md` first and follow it: it
   holds the JSON shape, the rules for the opening, the cast and every scene field, and the
   mistakes the checker will reject.
4. **Import it.**

   ```bash
   sceneloom script import <id> <project>/script.json
   ```

   Every `FAIL scene N: ...` line says what to change. Edit `script.json` and import again until
   it prints `OK`. Fix the scene, not the symptom: if a scene is flagged as almost identical to
   another, give it a different moment, not a few swapped words.
5. **Read `<project>/script.txt` as a viewer would.** The checker passed the form; now judge the
   story yourself. Does the first scene open on the most gripping moment? Does each scene move the
   story on? Does the ending pay off? Would the narration sound natural read aloud by a native
   speaker? Rewrite what is weak and import again.
6. **Show the user** the title, the hook line, the summary, the chapter list with scene counts
   and the cast, and ask whether to go on to the pictures. This is the cheap moment to change
   direction: pictures cost quota, words do not. Go on to `sceneloom-visuals` only after a yes.

## Revising an existing script

```bash
sceneloom script export <id> <project>/script.json     # the current script, same shape
# edit the file
sceneloom script import <id> <project>/script.json
```

The rules in `references/script-rules.md` apply to every edit; for a narration change the one that
usually matters is the length limit (about 16 characters per second of scene in Vietnamese).

An import keeps what it can, and `sceneloom status <id>` then shows exactly what has to be made
again:

| You changed | Goes back to pending | Made again on the next run |
|---|---|---|
| a narration line | `audio`, `edit`, `seo` | that scene's voice |
| a scene's picture fields or `refs` | `images`, `clips`, `edit`, `seo` | that scene's picture and clip |
| only a scene's `motion` | `clips`, `edit`, `seo` | that scene's clip |
| an entity's `look`, `en` or `kind` | `entities`, `images`, `clips`, `edit`, `seo` | that reference picture and every scene it appears in |
| title, hook, summary, chapter titles | `edit`, `seo` | nothing but the assembly and the texts |

Steps that stay ✔ are not redrawn, and running a pending step only makes what is missing, so a
narration fix costs one voice and a re-assembly. A changed `look` is the expensive one (every
scene with that entity is redrawn to keep the cast consistent); change it only when the user wants
the character to look different, and say what it will cost. Tell the user which steps must run
again: a new narration line is spoken by `sceneloom-sound` (its next audio run makes only the
changed lines), then `sceneloom-finish` assembles the video again.

The aspect ratio (16:9, 9:16, 1:1) is fixed when the project is created. To change it, create a
new project with `--aspect` and import the same `script.json` into it.

`sceneloom script check <id>` re-runs the checks on the stored script without changing anything.

## A new genre

Copy the closest file in `<sceneloom>/genres/`, give it a new `id` (same as the file name), and
rewrite every field for the new format. `script_brief` (what every video of this genre shows and
its emotional arc), `scene_rules` (how one shot is written) and `visual_style` (image style words)
matter most; `defaults` sets aspect, minutes, seconds per scene, chapters and whether there is
narration. Check it loads with `sceneloom genres`, then write one short script in it as a trial.

## Letting the pipeline write instead

`sceneloom run <id> --only script` has the configured text provider write and self-correct the
script without you. Use it only when the user asks for a hands-off run; you writing it gives
better stories and costs no extra calls.

## Don't

- Don't mark a script as finished while `script import` still prints `FAIL`.
- Don't put real people, clubs or brands in picture text; give them new names and looks (the rules
  file explains why).
- Don't start drawing pictures from this skill.
