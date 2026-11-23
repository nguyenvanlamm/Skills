# Storyboard rules: `cast` and `scenes`

The video is a 2D cartoon. You don't draw anything: you add a storyboard to `dialogue.json`, and
the video code draws the sets, moves the characters and cuts the shots on the audio. Idle
bobbing, blinks, lip movement, the slow camera push-in and the whip pan between places are
automatic. So is the text: each line appears in a speech bubble that points at its speaker, the
words turn solid as they are spoken, and new words carry a yellow marker.

## Format

```json
"cast": {"hugo": {"hat": "cap"}},
"scenes": [
  {"kind": "wide", "lines": [1, 2], "set": "street", "time": "day", "shop": "BOULANGERIE",
   "tag": "PARIS · LE MATIN",
   "chars": [{"id": "lea"}, {"id": "hugo", "enter": "right", "emotion": "tired"}],
   "beats": [{"at": "Salut", "who": "lea", "pose": "wave", "emotion": "smile"},
             {"at": "bruyant", "pose": "stressed", "emotion": "angry"}],
   "labels": [{"at": "voisin", "text": "le voisin"}]},
  {"kind": "closeup", "lines": [3, 3], "set": "street", "time": "day",
   "chars": [{"id": "lea", "emotion": "thinking"}],
   "beats": [{"at": "voisin", "emotion": "worried"}]}
]
```

### Scene fields

| Field | Meaning |
|---|---|
| `kind` | `wide` (everyone full length; `dialogue` is the same thing), `closeup` (one character, head and shoulders, soft background), `walk` (the characters walk across the set, see below). |
| `lines` | `[from, to]`, 1-based and inclusive. Scenes cover every line exactly once, in order. The hook plays over the first scene. |
| `set` | `home`, `office`, `street`, `void` (plain paper). Default: `home`, or `street` for a walk. |
| `time` | `day`, `dusk`, `night`. Night and dusk are lit by the lamps and windows of the set. Default `day`. |
| `shop` | Street only: the sign over the shop, in capitals (`BOULANGERIE`). |
| `wall` | Home and office: `green`, `blue`, `plum`, `teal`, `sand`, `grey`, `cream`, `brick`. |
| `tag` | A place and time tag (`PARIS · LE MATIN`) that slides in when the scene starts and leaves after four seconds. Use it the first time a place appears. |
| `chars` | Who is in the picture, left to right. A closeup has exactly one. |
| `beats` | Changes of pose, emotion or head direction on a cue (below). |
| `labels` | A hand-lettered word that pops in over the scene on a cue: `{"at": "loyer", "text": "le loyer"}`. Optional `color`: `lime`, `cream`, `gold`, `sky`, `pink`, `red`, `white`. |
| `side` | Closeup only: `left` or `right`, the side the character stands on. Default: their usual side. |
| `zoom` | `[from, to]`, to replace the slow push-in (default `[1, 1.07]`; `1` shows the whole set). Rarely needed. |

### Character fields (`chars`)

- `id`: a speaker (`lea`, `hugo`) or a name from `cast`.
- `pose`, `emotion`: how they start the scene (lists below).
- `enter`, `exit`: `"left"` or `"right"`: they walk in at the start, or out during the last second.
- `x`, `y`, `s`, `face`: only to override the automatic placement. The set is 1920 wide and 1080
  high; `x` and `y` are where the feet are, `s` is the size (1 = normal), `face` is -1 to 1, the
  way the head is turned. A portrait frame only shows the middle 800 of the 1920: keep `x`
  between 660 and 1260 or the character is cut off in the 9:16 video.
- `walk`: `[from_x, to_x]`, to replace the automatic path of a `walk` scene.

### Walk scenes

The characters cross the set from left to right for the whole scene, the first one in `chars`
in front, the next ones a step behind. Poses, emotions and beats work as in any scene. In 9:16
the camera follows them. A walk needs time to read: use it for scenes of two lines or more.

### Cues (`at`)

- A word or a few words said in this scene's lines: the change lands on that word. This is the
  normal form, and it is what makes the picture follow the voice.
- How a cue is matched: the words as written, an elided article ignored (`école` finds
  `l'école`, `un an` finds `d'un an`); failing that, without accents (`ecole`); failing that,
  another form of a word of seven letters or more (`déménager` finds `déménagé`). A word inside
  another word never matches (`loyer` does not find `employer`).
- When the words are said more than once in the scene, the cue lands on the first time, and the
  script warns. A beat with `who` looks at that character's own lines first, so a reaction
  "on the other one's number" needs `who` to be the one who says it, or more words in `at`.
- `"+1.5"`: seconds after the scene starts. A number from 0 to 1: that fraction of the scene.
- `who` is optional on a beat: without it, the beat goes to the character who says the word. If
  that character is not in the picture (a closeup of the listener), write `who`.

### Poses

`idle`, `explain`, `present`, `present_left`, `point`, `think`, `shrug`, `hips`, `pockets`,
`arms_crossed`, `hold`, `wave`, `celebrate`, `push`, `facepalm`, `stressed`, `tiphat`.

`present` and `point` reach to the right of the picture, `present_left` to the left: use the one
that points at the other character. `tiphat` needs a character with a `hat` in `cast`.

### Emotions

`neutral`, `calm`, `smile`, `happy`, `excited`, `confident`, `smug`, `thinking`, `worried`,
`nervous`, `shocked`, `sad`, `tired`, `angry`, `embarrassed`, `greedy`.

### Cast

Every speaker has a default look in `scripts/pipeline/config.json`. `cast` in `dialogue.json` only
overrides keys for this episode (a hat, another colour) or adds an extra, non-speaking character.
Keys: `skin` (`light`, `fair`, `tan`, `olive`, `brown`, `dark`), `outfit` (`suit`, `hoodie`,
`tshirt`, `dress`, `sweater`), `color`, `hair` (`slick`, `short`, `bun`, `long`, `curly`, `bald`,
`none`), `hair_col`, `glasses`, `beard`, `moustache`, `hat` (`fedora`, `cap`, `none`), `hat_col`,
`tie`, `bowtie`. Keep each character's look the same through an episode.

## What you get without directing

- A character with no `pose`, no `emotion` and no beat in a scene is animated for you: a small
  talking gesture when their line starts, back to rest when the other speaks.
- As soon as you give a character a `pose`, an `emotion` or a beat in a scene, that character is
  yours for the whole scene: nothing is added, and the last pose stays. A character left
  pointing while the other one answers looks frozen: end with a beat back to `idle` on the
  first word of the answer (`{"at": "<that word>", "who": "lea", "pose": "idle"}`).
- A dialogue with no `scenes` at all still renders, as wide shots and close-ups in one room. Use
  that only for a quick test: a written storyboard is what makes the episode worth watching.
  When a storyboard model is set up (`local-model.md`), `run.py` asks it for `scenes` first and
  falls back on those plain shots only if its answer never passes these rules.

## Pacing

- One scene per 1-3 lines. The script warns above 3 lines, when a shot lasts over 17 seconds, and
  when one lasts under 1.2 seconds.
- Never three scenes of the same kind in a row. A good rhythm: wide, wide or closeup, closeup, wide.
- Cut to a closeup of the listener or the speaker on a surprise, a number or a strong feeling.
- Two or three beats per scene. Put them on the word that carries the feeling, not at the start.
- Put the place where the story is: a new place for a new part of the conversation, two or three
  places in an episode. Changing `set` or `time` between scenes gives a whip pan.
- Label each new word once, on its first use, with the form to learn (`le loyer`, `s'habituer à`).
  One label per scene (the script warns on more). The label is placed for you where the bubble
  is not: over the listener in a wide shot (it glides across when the other one starts to
  speak), behind the character in a closeup, under the title in 9:16.
- A speaker who is not in the picture gets a bubble with no tail, at the top of a wide shot and
  at the bottom of a closeup. Use that on purpose (a close-up of the listener's reaction), not
  by forgetting a character in `chars`.
- Emotions must match the words: read each line and ask what the face should say.
- The first scene opens under the hook: start with both characters visible. If one walks in, it
  must not be the one who says the hook, or the first bubble points at nobody (the script warns).
  The same holds for the first scene of the short cut and whoever speaks first in it.
- The short cut plays the scenes of its line range, so those scenes must work as an opening.
