# The cartoon (Remotion)

`run.py` in `../pipeline` drives this project; nothing here is run by hand in normal use.

- `src/Toon.tsx`: one episode: the animated stage filling the frame, plus the title tag.
  Compositions `Toon16x9` (1920×1080) and `Toon9x16` (1080×1920), 60 fps.
- `src/Thumbnail.tsx`: the thumbnail (`Thumbnail16x9`) and the vertical cover (`Cover9x16`).
- `src/toon/`: the drawing code. Everything is a pure function of the frame number.
  - `Puppet.tsx`, `rig.ts`, `rig.json`: the character and its pose and emotion tables.
  - `actor.ts`: what a character does at a given moment (beats, idle, walk, lips).
  - `sets/`: the places. `shots.ts`: how each shot kind places its characters.
  - `Stage.tsx`: set + characters + lighting + camera. `fx.tsx`: labels and tags.
  - `Bubble.tsx`: the speech bubble with the karaoke text.
  - `Sheet.tsx`: composition `PuppetSheet`, every pose and emotion on one page.

Adding a set or a shot kind: write it, register it in `sets/index.ts` or `shots.ts`, and add its
name to `rig.json` (the dialogue validator reads the names from there).

```bash
npm install            # once
npm run lint           # eslint + tsc
npx remotion studio --props=<LEVEL>/episode.json --public-dir=<LEVEL>/public
npx remotion still PuppetSheet /tmp/sheet.png
```

Sources and licences: `CREDITS.md`.
