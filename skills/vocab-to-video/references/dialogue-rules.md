# Dialogue rules

## File format: `dialogue.json`

```json
{
  "level": "A2",
  "title": "Hugo va déménager",
  "vocab": [
    {"word": "déménager", "forms": ["déménager", "déménagé"]},
    {"word": "s'habituer à", "forms": ["t'habituer", "m'habitue", "habituée"]}
  ],
  "hook": {"speaker": "lea", "text": "Tu comprends ce dialogue en français ? Écoute bien !"},
  "short": {"from": 1, "to": 8},
  "lines": [
    {"speaker": "lea", "text": "Salut Hugo ! Ça va ?"},
    {"speaker": "hugo", "text": "Salut Léa ! Je vais déménager samedi."}
  ]
}
```

- `level`: `A2` or `B1`.
- `title`: short French title (at most about 40 characters); it is shown at the top of the video.
- `vocab`: one entry per input word. `word` is the word as the user gave it. `forms` lists every
  surface form you actually used in the text, without articles: conjugated verbs, plurals,
  feminine forms. For a reflexive verb, list the form with its pronoun when the pronoun is glued
  to the verb (`m'habitue`), otherwise only the verb (`habitue`, `habituée`). These forms are what
  gets highlighted in the captions, so a form you forget is a word that stays white.
- `hook`: one spoken line that opens every video before the dialogue (see "Hook" below).
- `short`: the line range (1-based, inclusive) cut into the 30-60 second vertical video for Shorts
  and TikTok (see "Short cut" below).
- `lines`: speakers `lea` and `hugo` only, strictly alternating. Either may start.

## Hook (first 3 seconds)

Viewers decide in the first seconds whether to stay, so the video starts with the hook, spoken and
shown as a large headline.

- At most 12 words, ends with `?` or `!`, addressed to the viewer with `tu`.
- A question or a challenge the viewer wants to answer: can you understand this, do you know this
  word, what would you do. Name the level or the situation, not the channel.
- Simple enough for the level: an A2 hook uses A2 words.
- Different for A2 and B1, and not the same sentence in every episode.
- True: don't promise something the video does not contain.

## Short cut (30-60 seconds)

- A run of consecutive lines that works alone: it starts where a newcomer can follow (usually the
  beginning) and ends on a complete exchange, ideally a small punchline or a question.
- It contains at least two of the new words, more if possible.
- Aim for 40-50 seconds: about 8 lines at A2, about 6 at B1. The pipeline measures the real
  duration and tells you to widen or narrow the range.
- The hook is added in front automatically.

## Length (each video must last 2-3 minutes)

| Level | Words in total | Turns | Words per turn (max) | Speech speed |
|---|---|---|---|---|
| A2 | 240-360 (aim for 300) | 22-34 | 22 | slowed 10% |
| B1 | 300-440 (aim for 400) | 18-30 | 28 | normal |

These totals give roughly 130 seconds. A short word list still needs a full-length dialogue:
reuse the new words in fresh contexts instead of adding harder words.

## Language level

**A2**
- Tenses: présent, passé composé, futur proche, impératif; a few fixed imparfait forms
  (`c'était`, `il y avait`).
- Short sentences, one idea each. Everyday words; nothing rarer than the new words themselves.
- Lots of questions and short reactions (`Ah bon ?`, `C'est super !`, `Tant mieux !`).

**B1**
- Add imparfait against passé composé, futur simple, conditionnel (présent, one passé at most),
  and one or two simple subjonctifs (`il faut que`, `bien que`).
- Connectors: `pourtant`, `en plus`, `finalement`, `à cause de`, `parce que`, `justement`.
- Opinions, reasons and a small disagreement or surprise; some sentences with two clauses.

## Using the new words

- Every word appears at least twice, in two different turns, ideally once per speaker.
- The first use must make the meaning guessable from context (a cause, an example, a contrast).
- Spread the words through the dialogue; never more than two new words in one turn.
- Keep the user's sense of the word. If a word has several meanings and the user gave no hint,
  use the most common one.

## Writing for speech and captions

- A real situation with a beginning and an end: greeting or hook, a small problem or plan, a
  closing line. The speakers use `tu`.
- Write numbers as words (`huit cents euros`, `neuf heures`): digits are read unpredictably and
  are harder for learners.
- French punctuation with a space before `? ! : ;`. Plain apostrophes or typographic ones are both
  fine. No emoji, no brackets, no stage directions, no speaker names inside `text`.
- No English words, no abbreviations (`M.`, `etc.`), no acronyms.
- Don't put one speaker's name in every line; once or twice in the whole dialogue is enough.
