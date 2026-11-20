---
name: idea-to-short
description: >-
  Turn one short idea into a finished one-minute vertical video with characters who speak in their
  own voices, and post it to YouTube Shorts and TikTok: write the skit (cast, dialogue, every
  shot), have it reviewed, draw the pictures, make the clips (a paid video model when one is
  configured, a slow zoom when not), voice each character, mix music, assemble with coloured
  subtitles, write the Shorts and TikTok texts, then stop once to show the result and post only
  after a yes. Runs on sceneloom from start to end without other stops. Use whenever the user
  gives an idea and wants a short made or posted, even without naming the skill: "làm video short
  từ ý tưởng này", "làm tiểu phẩm ngắn về ...", "tạo short có thoại rồi đăng lên TikTok và
  YouTube", "chạy idea to short", "make a short from this idea and post it". Don't use for one
  stage on an existing project (sceneloom-script, sceneloom-visuals, sceneloom-sound,
  sceneloom-finish), long narrated story videos (sceneloom-script), French vocabulary dialogues
  (vocab-to-video), music mixes (lofi-ballad-to-video, remix-chart-to-video), or posts about a
  game's gameplay (gameplay-to-social).
license: MIT
metadata:
  version: 1.0.0
  author: Nguyen Van Lam
---

# idea-to-short

Input: one idea, a sentence or a paragraph. Output: `final.mp4` (9:16, about a minute), the texts
for YouTube Shorts and TikTok, and, after the human says yes, the video uploaded to YouTube and
sent to TikTok.

The human asked for one command and one question. So decide everything yourself up to the finished
video, and ask exactly once: before anything is posted. Posting is the only step that cannot be
taken back, which is why it is the only stop.

Talk to the human in Vietnamese.

## Where things live

- `<sceneloom>`: `/home/lam/Documents/projects/sceneloom`. Run every command from that folder with
  `.venv/bin/python -m sceneloom ...` (written `sceneloom ...` below).
- `<project>`: `<sceneloom>/output/<slug>-<id>/`. `sceneloom new` prints the id and the folder;
  every later command takes the id.
- `references/dialogue-rules.md`: the script shape and how to write a skit that works. Read it
  before writing.
- `references/publish-rules.md`: the Shorts and TikTok texts and what the platforms allow.
- `references/setup.md`: the one-time connections (video model key, YouTube, TikTok). Read it only
  when `sceneloom doctor` shows something missing and the human wants it fixed.

## Rules

1. **Never post without a yes given in this conversation, after the human has seen the result.**
   An earlier "post it when done" in the request is the reason to prepare the posts, not the yes:
   the human has not seen this video yet. `sceneloom run` cannot post; only `sceneloom publish`
   can, and you run it only after the stop in step 8.
2. **Say what the video really is.** If no video model is configured the clips are slow zooms on
   still pictures; if a scene fell back to a zoom, or a line got no voice, say so at the stop with
   the scene numbers. You cannot hear the sound, so never say it sounds right; give the file path.
3. **Money is spent only by the clips step**, and only when `doctor` shows a paid video service.
   `max_paid_clips_per_run` in `settings.json` caps one run. If the step stops on that cap, report
   it and wait; do not raise the cap yourself.
4. **Do not switch providers, start or stop other apps, or edit `.env`, `settings.json` or
   `project.json` by hand.** When a provider is down or out of quota, report and stop.
5. **Original characters only.** No real people, clubs or brands in the script or the pictures;
   give them new names and looks. Image and video services refuse look-alikes, and posting one is
   a problem of its own.

## Steps

### 1. Check what is ready

```bash
sceneloom doctor
```

`FAIL` on ffmpeg, text, image or voice stops the run: report the line and what it needs. `WARN`
lines do not stop it, they change what you promise:

- `WARN video`: clips will be slow zooms. Say so in one line now and carry on.
- `WARN music`: the video is made without music.
- `WARN publish youtube` / `tiktok`: that platform cannot be posted to; the video is still made,
  and the stop in step 8 offers the file and the texts instead.

Music is made by a local app that cannot run while its own window is open; if the audio step
reports that, the video is assembled without music and you say so.

### 2. Create the project

```bash
sceneloom new --genre tieu-pham --notes "<the idea, in the human's words>"
```

The genre sets 9:16, one minute, 5 seconds per scene. Pass `--minutes` only if the human gave a
length. Read `<sceneloom>/genres/tieu-pham.json`: its brief and scene rules are your brief. The
command prints how many scenes and chapters to write.

### 3. Write the skit

Read `references/dialogue-rules.md`, then write `<project>/script.json`: the cast with a voice for
each speaking character, and every scene with its picture fields and its `lines`.

```bash
sceneloom script import <id> <project>/script.json
```

Fix every `FAIL` line and import again until it prints `OK`. A line that is too long is cut or
split across two scenes, never squeezed: the clip cannot be stretched to fit it.

### 4. Have it reviewed

Nobody else reads this script before pictures are drawn, so get one read that is not yours. Start
a fresh subagent with only `<project>/script.txt`, the idea, and this brief: "You are the viewer,
thumb on the screen. Answer APPROVE or REVISE. Would you stop scrolling in the first three seconds,
and why? Is there a line a character would not say out loud? Could two characters swap lines
without anyone noticing? Does the ending pay off the opening? List the scenes to change and what
is wrong with each." Apply what it lists, import again, and ask once more if it said REVISE. Two
rounds at most; then go on with the best version.

### 5. Draw

```bash
sceneloom run <id> --only entities,images
sceneloom sheet <id> --what entities
sceneloom sheet <id> --what images
```

Open every sheet with Read and compare each picture with its scene: the right people, the look
from the cast, no written words, no extra limbs. Mark what is wrong and run again:

```bash
sceneloom redo <id> --scenes 6,9        # or --entities <id> when a reference picture is wrong
sceneloom run <id> --only entities,images
```

Two redraw rounds at most. A picture still wrong after that is named at the stop in step 8.

### 6. Clips, voices, music, assembly

```bash
sceneloom run <id> --only clips,audio,edit
sceneloom status <id>
sceneloom sheet <id> --what final
```

`status` tells what really happened: how many clips have motion and how many are zooms, which
scenes have no voice, which voices run longer than their scene. A voice more than 2 s over its
scene means that line is too long: shorten it in `script.json`, import, and run the same command
again (only the changed line is spoken again, nothing is redrawn). Open the final sheet and check
the hook text in the first frame, subtitles of at most two lines, and no black or wrong scene.

If the step stopped, read the message, fix the cause if it is yours (a script line), and run the
same command again: finished work is kept, and a paid clip that was already ordered is collected,
not ordered twice.

### 7. Write the posts

```bash
sceneloom seo facts <id>
```

Read `references/publish-rules.md`, write `<project>/seo.json` with the usual fields plus the
`shorts` and `tiktok` blocks, then:

```bash
sceneloom seo import <id> <project>/seo.json
sceneloom publish <id> --to youtube,tiktok --dry-run
```

Fix every `FAIL` and import again until `OK`. The dry run prints exactly what would be sent and
sends nothing; skip a platform that `doctor` showed as not connected.

### 8. The one stop

Show, in this order:

- the path of `final.mp4`, its length, and the path of the final contact sheet;
- what the clips are (motion, zoom, fallback zoom, with scene numbers for the last two), any scene
  without a voice, any picture still wrong, and whether there is music;
- the paid clips used, if any (`paid_clips` in `project.json`);
- the Shorts title and description, and the TikTok caption, each with its hashtags;
- for each platform, what posting will do: YouTube uploads as **private** unless the human picks
  unlisted or public; TikTok goes to the account's **TikTok inbox**, where the human pastes the
  caption, picks who can see it and posts in the app.

Then ask one question: post to which platforms, and with which YouTube visibility. Sending to
TikTok also needs the account owner's agreement to TikTok's Music Usage Confirmation; name it in
the question, because `--tiktok-consent` states that agreement on their behalf.

### 9. Post

Only what the human said yes to:

```bash
sceneloom publish <id> --to youtube --privacy private
sceneloom publish <id> --to tiktok --tiktok-consent
```

Report the YouTube link and its visibility, and the TikTok status with the caption ready to
paste. If a platform failed, give its message as printed; the other one stays posted. Running
`publish` again never posts twice: it continues an unfinished upload or reports what was sent.

## Changing things afterwards

The four stage skills still own every repair: a line or a shot (`sceneloom-script`), a picture or
a clip (`sceneloom-visuals`), a voice or the music (`sceneloom-sound`), the assembly and the texts
(`sceneloom-finish`). A video that was already posted is not replaced by posting again: tell the
human it needs a new upload.

## Don't

- Don't post, schedule, or open a platform in a browser on your own.
- Don't call the video finished while `sceneloom status` shows a step that is not `✔`.
- Don't describe a zoom as animation, or sound you have not heard as good.
- Don't put the idea's real names into the script; see rule 5.
