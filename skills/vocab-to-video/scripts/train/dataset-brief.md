# Brief: write validated French dialogues with storyboards

Give this brief to each helper that writes training examples, with three things filled in:
`<skill>` (the skill folder), `<output>` (the dataset folder), `<scratch>` and a batch number,
and the themes of the batch (slug and one line on what it is about). Seven themes per batch
(14 files) is a good size.

For EACH of your themes, write two files: `<output>/<slug>/A2/dialogue.json` and
`<output>/<slug>/B1/dialogue.json` (slug: 1-3 lowercase ASCII words joined by `-`, taken from the
theme). The two levels are two different conversations on the theme, not one text rewritten.

Before writing anything, read in full:
- `<skill>/references/dialogue-rules.md` (JSON schema, level rules, length targets, hook, short cut)
- `<skill>/references/scene-rules.md` (the storyboard: `scenes`)
Follow both exactly. Pick 8 useful new words or expressions for the theme yourself (different
words for A2 and B1 where natural). Do not write metadata.json; do not run run.py; no audio.

Each file must contain the storyboard (`scenes`). These storyboards are reference examples of
good direction, so make them good, not merely valid:
- one scene per 1-3 lines; vary wide / closeup / walk, never three of a kind in a row;
- 2-3 places per episode chosen for the story (sets: home, office, street, void; times: day,
  dusk, night), each kept for several scenes; a `tag` the first time a place appears; a `shop`
  sign on street scenes when it fits;
- 2-3 beats per scene on the word that carries the feeling, each with `who`; emotions that fit
  the words; a directed character goes back to `idle` on the first word of the other's answer;
- a closeup of the speaker or of the reacting listener on a surprise, number or strong feeling;
- each new word labelled once, in the scene of its first use, at most one label per scene;
- both characters visible in the first scene, the hook speaker never `enter`ing; the same for
  the first scene of the short cut;
- across your episodes use every set and time of day, some `walk` scenes, some `enter`/`exit`,
  and a wide range of poses and emotions. Do not use the pose `tiphat`, and do not add `cast`.

Check every file, from `<skill>/scripts/pipeline/`:
  uv run python validate_dialogue.py <output>/<slug>/<LEVEL>/dialogue.json
and edit until it prints `RESULT: PASS` with NO `WARN` line at all (warnings count as failures
here: fix the cause, e.g. use more words in a cue that is said twice, split a long scene, reuse
a word that is used once). Never edit anything inside the skill folder.

Report: one line per file (path, words, turns, scenes), and any file you could not get to a
clean PASS with the reason. Nothing else.

## Rules when several batches run at once
- Never write into a `<slug>` folder that already exists in the output folder: pick another slug
  (add `-2`). Check the existing slugs before choosing themes for a new round.
- Any helper file you create goes in a folder of your own, `<scratch>/batch-<your batch number>/`;
  never touch another batch's files.
- Vary the shape between your episodes: who speaks first, where it starts (not always at home
  by day), how many scenes, where the closeups and the walk fall.
- A batch stopped by a usage limit keeps what it wrote: resume it, don't start it again.
