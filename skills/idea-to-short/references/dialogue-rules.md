# Writing the skit

The picture and clip models see one scene at a time and remember nothing; the voice model reads
one line at a time. Most rules below follow from that. The checker (`sceneloom script import`)
enforces the measurable ones; the rest decide whether anyone watches to the end.

## Shape of `script.json`

```json
{
  "title": "in Vietnamese",
  "hook_text": "4-8 words, one complete sentence, shown big in the first 3 seconds",
  "summary": "3-5 sentences in Vietnamese",
  "entities": [
    {"id": "ba_tu", "kind": "character", "name": "Bà Tư", "en": "Ba Tu, an old market vendor",
     "look": "70 years old, thin, silver hair in a low bun, faded purple blouse, black trousers, jade bracelet",
     "voice": {"name": "vi-VN-HoaiMyNeural", "rate": "-10%", "pitch": "-18Hz"}},
    {"id": "khoa", "kind": "character", "name": "Khoa", "en": "Khoa, a delivery rider",
     "look": "24 years old, lean, short black hair, bright orange jacket, grey helmet under one arm",
     "voice": {"name": "vi-VN-NamMinhNeural", "rate": "+6%", "pitch": "+10Hz"}},
    {"id": "sap_rau", "kind": "place", "name": "Sạp rau", "en": "the vegetable stall",
     "look": "narrow wooden stall under a blue tarp, crates of greens, a hanging brass scale, wet concrete floor"}
  ],
  "chapters": [
    {"title": "in Vietnamese", "beats": "what happens, 1-2 sentences",
     "scenes": [
       {"type": "story",
        "location": "covered wet market",
        "visual": "35-70 English words",
        "camera": "over-the-shoulder medium shot from behind Khoa, eye level, 50mm lens",
        "lighting": "cool morning daylight from the left through the tarp, soft shadows",
        "colors": "muted greens and blue with one bright orange accent",
        "details": "water dripping from the tarp edge, a brass scale swinging slightly",
        "motion": "she pushes the bag back across the crates while the camera eases in",
        "refs": ["ba_tu", "khoa", "sap_rau"],
        "lines": [{"speaker": "khoa", "text": "Bà ơi, bà thối nhầm tiền rồi."},
                  {"speaker": "ba_tu", "text": "Không nhầm đâu con."}],
        "caption": ""}
     ]}
  ]
}
```

A scene says what is spoken in **one** of two ways: `lines` (dialogue) or `narration` (one sentence
by the narrator). Giving both is an error. `"speaker": "narrator"` inside `lines` is allowed. A
scene with `"type": "filler"` has neither: a silent reaction or a closing image.

## What the checker enforces

| Rule | Why |
|---|---|
| At most 2 lines in a scene | a 5-second clip cannot hold a longer exchange |
| The lines of a scene fit its seconds (under 10 characters per second in Vietnamese: about 48 characters for one line and 44 for two in a 5-second scene; the FAIL line gives the number) | a clip cannot be stretched; past its end the picture freezes |
| A speaker is a `character` id from `entities`, or `narrator` | the voice comes from the entity |
| Every speaking character has a `voice` with `name`, `rate` like `-8%`, `pitch` like `+15Hz` | |
| At most 3 characters speak | more voices than that are not told apart by ear |
| No two speaking characters share name, rate and pitch | they would sound like one person |
| Everything `sceneloom-script` already checks: English `visual` and `motion` of 35-70 words, concrete camera, lighting, colours and details, no written words in the picture, at most 3 scenes in a row in one place, no repeated picture or line | |

## Voices

Vietnamese has two voices: `vi-VN-HoaiMyNeural` (female) and `vi-VN-NamMinhNeural` (male). Two
characters of the same sex are separated by `rate` and `pitch`; keep them clearly apart, at least
15 Hz or 10 %. Starting points:

| Character | name | rate | pitch |
|---|---|---|---|
| young woman | HoaiMy | `+4%` | `+10Hz` |
| woman, plain | HoaiMy | `+0%` | `+0Hz` |
| old woman | HoaiMy | `-10%` | `-18Hz` |
| young man, boy | NamMinh | `+8%` | `+25Hz` |
| man, plain | NamMinh | `+0%` | `+0Hz` |
| heavy or old man | NamMinh | `-6%` | `-14Hz` |

Past about ±25 Hz the voice starts to sound processed. The narrator, if used, speaks in the
project's own voice at normal rate and pitch, so give no character that exact setting.

Write for the voice model: full sentences with normal punctuation, numbers as words, no emoji, no
stage directions in brackets (they would be read aloud). A name is spelled the same way every time.

## The opening

- Scene 1 is already inside the situation: an action under way, something wrong in the frame, a
  line that makes no sense yet. Never two people greeting each other, never an establishing shot of
  an empty place.
- `hook_text` states what is at stake in that moment. It is not the title.
- By scene 3 the viewer knows who wants what from whom.

## Lines that sound spoken

- **Know each speaker's game before writing.** What they want the other to do, what they cannot
  say outright, what they try first and what they switch to when it fails. Two people can argue
  about a bag of change while really fighting over something else.
- **Every line is a move.** The same fact can hurry someone, dodge blame, probe, threaten or
  protect; pick the move, then the words.
- **A blocked move forces a new one.** If one side wins every exchange the scene is a monologue.
- **The swap test.** Exchange two characters' lines; if nothing breaks, they are not yet two
  people. Separate them by what they notice, how they address others, how they dodge a question.
- **Never say what the picture shows.** If she pushes the bag across, she does not also say she is
  giving it back. Characters do not recite what both of them already know.
- **Short.** One breath per line. A speech is split across scenes at the point where the tactic
  changes, with a shot of the listener in between.

## Shots while someone speaks

The voice is laid over the clip, so lips do not match the words. Stage every speaking scene so
that nobody looks at the speaker's mouth:

- over the speaker's shoulder onto the listener;
- the listener's reaction in close-up while the line is heard;
- a wide or medium-wide shot where faces are small;
- hands and the thing being argued about;
- the speaker from behind or in profile, walking or working.

Change shot size and angle on every exchange, and give the hardest line to the listener's face.
In 9:16 keep the subject in the middle two thirds and avoid steep high or low angles, which bend
bodies. Say in `motion` only what can happen in five seconds: one movement, one camera move.

Each `visual` stands alone: who, by English name with the key look details again, doing what,
where. "She keeps arguing" means nothing to a model that never saw the scene before.

## The turn and the ending

- One reversal, about two thirds in: the thing the viewer assumed turns out otherwise, and it was
  possible to see it coming.
- The last scenes deliver what the opening promised: a result, a changed relationship, a truth or
  a laugh. Then one quiet closing image, usually a `filler` scene. Stop once the attitude is clear;
  do not explain the moral.
- Costs set up earlier still hold at the end. A prop that mattered is still where it was left.

## When a scene needs something in another state

A reference picture shows an entity one way. A scene that needs it otherwise (the box open, the
character soaked) says so plainly in `visual` and leaves that entity out of `refs`.
