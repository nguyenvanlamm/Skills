# Script rules

Everything the picture and clip models will see comes from this file's fields, one scene at a
time, with no memory of the other scenes. That single fact explains most of the rules below.

## Shape of `script.json`

```json
{
  "title": "final title, in the video language",
  "hook_text": "4-8 words, one complete sentence shown big in the first seconds",
  "summary": "4-6 sentences, in the video language",
  "entities": [
    {"id": "mai", "kind": "character", "name": "Mai", "en": "Mai, a fishing village girl",
     "look": "8 years old, round face, two short black braids with red ribbons, bright yellow blouse, dark blue trousers, barefoot"}
  ],
  "chapters": [
    {"title": "chapter title, in the video language",
     "beats": "what happens in this chapter, 2-3 sentences",
     "scenes": [
       {"type": "story",
        "location": "fishing village wooden pier",
        "visual": "35-70 English words",
        "camera": "wide shot, low angle, 24mm lens",
        "lighting": "thick night fog lit by one warm lantern from above",
        "colors": "deep blue greys with one glowing red accent",
        "details": "wet planks, coiled rope, faint ripples",
        "motion": "she raises the lantern higher while the camera slowly pushes in",
        "refs": ["mai", "den_long"],
        "narration": "one spoken sentence in the video language",
        "caption": ""}
     ]}
  ]
}
```

Scenes are numbered in order across chapters; you do not write the number.

## How many

`sceneloom new` prints the scene and chapter counts for the chosen length. Stay within about
20 % of the scene count or the import fails; put at least 3 scenes in a chapter.

Cast size grows with length: about 2 characters, 2 places and 1 prop for one minute, up to about
8, 10 and 5 for a quarter of an hour. If the genre fixes a small cast on purpose (only a pair of
hands, one family), keep it and add places and props instead.

Entities are only what the viewer sees more than once and must recognise: a place the story
returns to, a prop that matters. A place seen once (a bridge the boat passes under) needs no
entity; naming it in that scene's `location` and `visual` is enough.

## The opening and the ending

- The first scenes start in the middle of the most gripping moment of the story: danger, a
  discovery, the thing at stake. Give the hook about a tenth of the scenes: 1-2 scenes in a
  one-minute video, up to 3 in a long one. Then a bridge scene ("Mới chiều hôm ấy…", "It had all
  started…") and the story is told from the beginning. Viewers decide in the first seconds
  whether to stay.
- `hook_text` states what is at stake in that opening. It is not the title, and it is a complete
  sentence, never cut off.
- The last chapter resolves the story and ends on a calm closing shot.
- For genres without a story (a recipe, a build), scene 1 shows the finished result first.

## Entities: what must look the same in every scene

- `id`: short snake_case, unique. `kind`: `character`, `place` or `prop`.
- `name`: display name in the video language. `en`: short English name, 2-5 words; this is how
  scenes refer to the entity.
- `look`: 15-30 English words. People: age, face, hair, build, the one outfit they wear, colors.
  Places and props: shape or architecture, materials, colors, layout.
- Make every character clearly different from the others (age, hair, outfit color), or the image
  model will blend them.

## Scene fields

| Field | Rule |
|---|---|
| `type` | `story`, or `filler` for a calm in-between shot with no narration |
| `location` | 2-5 English words; the same words every time the story returns there |
| `visual` | 35-70 English words: who (by English name, with the key look details again), one clear action, where, the mood |
| `camera` | shot size + angle + lens or focus |
| `lighting` | source, direction, quality, time of day |
| `colors` | palette and textures |
| `details` | 2-4 small things in the foreground or background that make it real |
| `motion` | 10-25 English words: one simple movement and one camera move |
| `refs` | ids of the listed entities visible in the scene, most important first: only the first 3 have their reference pictures attached, and the picture model copies their look exactly (see below) |
| `narration` | one sentence in the video language that matches the picture; empty for filler scenes and for genres without narration |
| `caption` | usually empty; a short on-screen label of at most 6 words when the genre uses step labels |

## Rules the checker enforces

- `visual` and `motion` are 100 % English, names included: use the entity's `en`.
- `visual` has at least 25 words (aim for 35-70) and at most about 95.
- `camera`, `lighting`, `colors`, `details` each say something concrete; `motion` has at least
  4 words; `location` is not empty.
- Nothing asks for written words, captions, signs, a split screen or a flashback in the picture.
  The words that trip the check are: text, caption, subtitle, "sign that reads", "words on",
  letters, split screen, flashback, "before and after".
  Image models draw garbled letters, and one frame cannot show two times.
- Narration fits the scene: about 16 characters per second for Vietnamese, 17 for English (a
  6-second scene holds roughly 95 Vietnamese characters). That is the most a line can hold, not a
  target: a natural voice says 70-85 Vietnamese characters in 5-6 seconds, and longer lines stretch
  the scene. Every story scene has a line when the video is narrated.
- No narration line repeats or closely paraphrases an earlier one.
- No picture is almost the same as an earlier one.
- At most 3 scenes in a row in one location.
- `refs` only names ids that exist.

## Rules the checker cannot enforce, and why they matter

- **Each `visual` stands alone.** Repeat who, what and where every time. "She keeps walking"
  means nothing to a model that never saw the previous scene.
- **One drawable moment.** Real objects and a real action, no metaphor, nothing appearing by
  magic unless the story says so, an action that fits in a few seconds.
- **Continuity.** Same place, weather, time of day and outfits as the neighbouring scenes unless
  the story changes them; say the time of day in `lighting`.
- **Variety.** Change shot size and angle from scene to scene (wide, medium, close-up, detail,
  aerial); give side characters screen time; bring places to life with background people and
  things.
- **Safe to generate.** No gore, no weapons aimed at people, no nudity. Show fear through mood
  (shadows, fog, a flickering light). Services refuse the rest, and the scene falls back to a
  still picture.
- **No real people, clubs or brands** in any picture text. Image services refuse real and
  look-alike faces. Turn them into original characters with new names and looks.
- **Narration is for the ear.** Natural spoken language of a native storyteller, not a
  description of the picture. Read it aloud in your head.

## When a scene needs an entity in another state

A reference picture shows an entity one way (a lantern lit, a door closed, a character smiling).
The picture model copies the references attached to a scene, so a scene that needs the entity
otherwise (the lantern dark, the door open, the character crying) comes out wrong. For such a
scene, say the state plainly in `visual` ("one dark, unlit red paper lantern, no flame") and leave
that entity out of `refs`.

## Typical FAIL lines and the fix

| Message | Fix |
|---|---|
| `visual/motion contain non-English words` | replace the name or word with the entity's `en` |
| `visual is too short or vague` | add who with look details, the action, the setting, the mood |
| `asks for written text, a split screen or a flashback` | describe the object without its writing; show one moment |
| `narration is too long` | cut to one short sentence, or move part of it to the next scene |
| `narration repeats scene N` | write a line that moves the story on |
| `picture is almost identical to scene N` | change the moment, the angle or the place, not a few words |
| `N scenes in a row at "..."` | move this beat to another place that fits the story |
| `refs name unknown entity ids` | use an id from `entities`, or add the entity |
| `N scenes written but about M are needed` | add or merge scenes, keeping the chapter balance |
