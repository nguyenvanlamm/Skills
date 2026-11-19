---
name: sceneloom-sound
description: Make the sound of a sceneloom video, a narrator's voice for every scene line (with word timings for the subtitles) and one instrumental background track, then check that every line was spoken and fits its scene. Third of four sceneloom skills (script, visuals, sound, finish). Use whenever the user wants the voice-over or music of a sceneloom project made, changed or checked, even without naming the skill, "làm giọng đọc cho video", "thêm lời thuyết minh", "đổi giọng đọc sang giọng nam", "tạo nhạc nền", "đổi nhạc nền", "giọng đọc bị thiếu cảnh 4", "add narration and music to the sceneloom project". Don't use for writing the narration text (sceneloom-script), pictures or clips (sceneloom-visuals), mixing and exporting the video (sceneloom-finish), remixing songs (remix-chart-to-video, lofi-ballad-to-video) or French dialogue audio (vocab-to-video).
---

# sceneloom-sound

Input: a sceneloom project with a finished script. Output: `voice/scene_NNN.wav` and
`voice/scene_NNN.words.json` (when each word is spoken) for every scene that has narration, and
`voice/music.wav`, with the `audio` step done.

Sound does not depend on the pictures, so this skill can run before, after or alongside
`sceneloom-visuals`.

## Where things live

- `<sceneloom>`: `/home/lam/Documents/projects/sceneloom`. Run every command from that folder with
  `.venv/bin/python -m sceneloom ...` (written `sceneloom ...` below). The `.venv` matters here:
  it holds `edge-tts`.
- `<project>`: printed by `sceneloom status <id>`.
- Providers are chosen in `<sceneloom>/settings.json` (`"combo"` → `"voice"`, `"music"`):
  - voice: Microsoft Edge text-to-speech, free, online;
  - music: ACE-Step inside the StemForge checkout at
    `/home/lam/Documents/projects/Youtube/Youtube-music/StemForge`, on this machine's GPU.
- Code this skill owns: `step_audio`, `_make_voices`, `_make_music` in `sceneloom/pipeline.py`,
  `sceneloom/providers/edge.py`, `sceneloom/providers/stemforge.py`,
  `sceneloom/tools/stemforge_music.py`, and `music_prompt` in `sceneloom/prompts.py`. A new voice
  or music service is a new `Provider` subclass (contract: top of `sceneloom/providers/base.py`);
  a voice provider that also writes `<audio>.words.json` gets exactly timed subtitles for free.

## Steps

1. **Check the script is done**: `sceneloom status <id>` shows ✔ for `script`.
2. **Close StemForge if it is open.** The music step shares StemForge's GPU lock and will be
   skipped with "the GPU is locked" while the app runs. Ask the user rather than killing it.
3. **Run the step.** With the real providers it takes a few minutes (voices are made one line at
   a time, and the music model needs about a minute to load), so run it in the background and wait
   for it. A mock trial takes seconds. The real providers are the ones `<sceneloom>/settings.json`
   names under `"combo"`; with no settings.json every step falls back to the mock.

   ```bash
   sceneloom run <id> --only audio
   ```

   The last line reads `voice: 10/10 lines (… made now, voice …)   music: yes`. For a trial that
   costs nothing, add `--provider mock` (see "Dry run" below).
4. **Read `sceneloom status <id>`.** Its `Voice:` line counts the lines with a voice, names the
   voice and says whether there is music; the lines under it name scenes with no voice and scenes
   whose voice runs longer than the scene. `Made by:` says which provider made the voices and the
   music; "mock (placeholder)" means test tones, not speech.
   - **Missing voices**: Edge's free service often answers "no audio". The provider already
     retries each line 8 times; run the same command again, which only makes what is missing.
     After two more runs, stop and report which scenes are still silent (they will show
     subtitles only).
   - **Voice longer than the scene** (listed when it is more than 0.25 s over): the scene is
     stretched to the voice plus half a second, so the video still works. A few tenths of a second
     is fine. Lines listed as "more than 2 s over" make the pace drag: have them shortened with
     `sceneloom-script` and run the step again.
   - **Word timings**: each voice comes with `scene_NNN.words.json`, which times the subtitles to
     the speech. A voice provider that writes none still works; the subtitles are then timed by
     the length of each part of the sentence, which is close but less exact.
5. **Tell the user what to listen to.** You cannot hear. Give the paths of two or three voice
   files and of `voice/music.wav` and ask them to listen for a wrong reading of a name, an odd
   pause, or music that does not fit the mood. Then offer `sceneloom-finish`.

## Changing the voice

Where to set it, most specific first (the first one set wins):

- **One project** (what a user usually means by "this video"): `sceneloom voice <id> vi-VN-NamMinhNeural`;
  `sceneloom voice <id> default` clears it, `sceneloom voice <id>` shows where the current one comes from.
- **Every project of a genre**: `"voice"` in that genre's file.
- **Everything else**: `"edge_voice"` in `settings.json`; `"edge_rate"` (for example `"-5%"`) sets the speed.

Vietnamese voices: `vi-VN-HoaiMyNeural` (female, the default) and `vi-VN-NamMinhNeural` (male).
Other languages: `.venv/bin/edge-tts --list-voices`.

The audio step remembers which voice made each line and makes again every line whose voice
setting changed, so after any of the three just run `sceneloom run <id> --only audio`; its log says
how many lines it made. `sceneloom redo <id> --step voice` is only for remaking lines with the same
voice (after a mock trial, or a bad take). `edit` must run again for the video to use new voices.

## Changing the music

The mood comes from the genre's `music_mood` (style words such as "gentle, warm, a little
mysterious"); length and tempo from `"music_seconds"` (default 60, looped under the video) and
`"music_bpm"` (default 80) in `settings.json`. For a new track: `sceneloom redo <id> --step music`,
then run the step again (`--step audio` marks the voices and the music together). The current track
stays in use until a new one is made, and `sceneloom redo <id> --undo` takes a mark back. Loudness
under the voice is not set here: it is `"music_volume"`, applied by `sceneloom-finish` when it mixes.

## Dry run

`--provider mock` on the `run` command makes a test tone per line (as long as the line would take
to say, with evenly spaced word timings) and a two-tone "music" track, using no network and no
GPU. It ignores the voice name, so after a voice change it shows only that every line was made
again (the log count and the file times), not how the new voice sounds. It checks the plumbing:
every line gets a file, durations against scene lengths, the step completes. Skip closing
StemForge and asking the user to listen; say instead that nothing can be judged by ear yet. The
mock voices count as made, so before the real run mark them all: `sceneloom redo <id> --step audio`.

## Don't

- Don't report the sound as checked by ear. Say what you verified (files exist, durations, which
  lines are missing) and what the user still has to listen to.
- Don't stop a running StemForge app yourself.
- Don't switch to a paid voice or music service without the user's say-so.
