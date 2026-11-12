# Upload fields: `metadata.json`

You write `<LEVEL>/metadata.json`; `scripts/pipeline/publish.py` checks it against the platform limits and
assembles the final fields in `<LEVEL>/out/publish.md` and `publish.json`. The script adds the
chapters (first use of each new word), the vocabulary list, the full transcript, the footer and
the hashtags to the YouTube description itself, so do not write those into `intro`.

## Start from real search data

Before writing, run `uv run python keywords.py <episodes>/<name> "<theme query>" ...` from
`<skill>/scripts/pipeline/` and read `<episode>/keywords.json`. It holds what people actually type into YouTube
search (autocomplete suggestions) for the channel's core phrases at both levels, plus the theme
queries you pass. Pass 3-5 theme queries for the episode (`"vocabulaire logement français"`,
`"louer un appartement français"`).

- Build the YouTube title on a suggestion of three or more words, placed first
  (`Dialogue en français niveau A2 : ...`).
- At least 5 tags must be suggestions copied exactly (the script checks this; accents and case
  don't matter). Prefer the ones that name the level.
- Suggestions that are another channel's or person's name are not keywords; never use them.
- There is no equivalent open data for TikTok. TikTok hashtags follow the fixed guidance below.

Write everything in the language set in `scripts/pipeline/config.json` → `publish.language` (French by
default: learners search in French, and the video itself is all French). A few English search
phrases in tags and hashtags are welcome.

## Format

```json
{
  "youtube": {
    "title": "Dialogue en français A2 : déménager, le loyer, un colocataire",
    "intro": "Dialogue en français facile (niveau A2) pour apprendre ...",
    "tags": ["dialogue en français", "français A2", "learn french"],
    "hashtags": ["#français", "#apprendrelefrançais", "#learnfrench", "#DELFA2"]
  },
  "shorts": {
    "title": "Tu comprends ce dialogue en français A2 ? Hugo déménage",
    "description": "Dialogue en français niveau A2 avec sous-titres : ...",
    "hashtags": ["#français", "#apprendrelefrançais", "#learnfrench", "#Shorts"]
  },
  "tiktok": {
    "caption": "Dialogue en français A2 : Hugo va déménager 📦 ...",
    "hashtags": ["#français", "#apprendrelefrançais", "#learnfrench", "#frenchlesson", "#vocabulaire"],
    "cover_text": "Dialogue A2 : déménager"
  },
  "thumbnail_text": "DÉMÉNAGER · Le logement",
  "vocab_notes": [
    {"word": "déménager", "note": "changer de logement, partir habiter ailleurs"}
  ]
}
```

## Field rules (the script fails on the hard limits)

| Field | Hard limit | SEO rule |
|---|---|---|
| `youtube.title` | 100 characters; contains the level and `français` | Aim for 50-70. A real search suggestion first (`Dialogue en français niveau A2`), then a reason to click: a question or the story's tension (`pourquoi Hugo déménage ?`). It must be true of the video. No all caps. |
| `youtube.intro` | level + `français` in the first 150 characters | 250-600 characters. Sentence one repeats the main phrase and lists the new words; then what happens in the dialogue and who it is for (level, exam, grammar practised). Natural sentences, no keyword lists. |
| `youtube.tags` | 8-25 tags, 500 characters in total, no duplicates, at least 5 from `keywords.json` | Mix: 3-4 broad (`apprendre le français`), 3-4 level-specific (`français A2`, `DELF A2`), the new words themselves, the theme, 3-4 English phrases. |
| `youtube.hashtags` | 3-5, one word each | The first three appear above the title: put the most searched first. |
| `shorts.title` | 100 characters; contains the level and `français` | A hook, different from the long video's title: a question or a challenge. |
| `shorts.description` | — | One or two sentences with the main phrase and 2-3 new words that are in the short cut. |
| `shorts.hashtags` | 3-5 | Include `#Shorts`. |
| `tiktok.caption` | 2200 characters with hashtags; level + `français` in the first 100 | 100-200 characters: main phrase, a one-line hook about the story, a call to act (listen, repeat, comment). One emoji at most two. |
| `tiktok.hashtags` | 3-5, no `#fyp`-style tags | TikTok may cap captions at 5 hashtags. Two broad (`#learnfrench`, `#apprendrelefrancais`), one or two niche (`#frenchlesson`, `#fle`), one for the level (`#DELFA2`). Write TikTok hashtags without accents: that is how these tags are mostly used. |
| `tiktok.cover_text` | 40 characters | Level + theme; it is typed onto the cover in the TikTok app. |
| `thumbnail_text` | 32 characters; must not contain the level | Text drawn on the thumbnail and cover images (the level badge is added automatically). A headline of 1-2 words in capitals (the key word or theme, longest word 12 letters at most), then optionally ` · ` and a short subtitle: `DÉMÉNAGER · Le logement`. |
| `vocab_notes` | one per vocabulary word, same `word` as in `dialogue.json` | A short definition in simple French, at the level of the episode (A2 notes use A2 words). No translation. |

## General rules

- The Shorts and TikTok texts describe the short cut (the `short` line range), not the whole
  dialogue: only mention words and events that are in it.
- Accuracy first: every claim must be true of this video (level, words, grammar, speed). Don't
  promise translations, exercises, a PDF or a publishing schedule that do not exist.
- A2 and B1 of the same episode need different titles, intros and hooks, not one text with the
  level swapped.
- Hashtags: letters, digits and underscore only, so `#DELFA2`, not `#DELF-A2`.
- Never use `<` or `>` anywhere; the platforms reject them.
- Don't name other channels, brands or people.
