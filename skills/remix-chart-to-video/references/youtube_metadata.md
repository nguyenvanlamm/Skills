# Writing the YouTube package

The four repos produce no upload metadata except chapter times, so this part is yours. The
output is `RUN/youtube/youtube.json` (the package) and `RUN/youtube/evidence.json` (where the
keywords came from). `youtube_meta.py validate` checks both and, when nothing fails, writes
`RUN/youtube.md` for the human to paste from.

Contents: 1 Order of work · 2 Evidence · 3 youtube.json · 4 Titles · 5 Description · 6 Tags and
hashtags · 7 Form choices · 8 Pinned comment and playlist · 9 What each check means ·
10 Independent review

## 1. Order of work

1. `python3 <skill-dir>/scripts/youtube_meta.py facts --run RUN`. Everything factual you may
   write is in its output: songs, artists, chart ranks, the chart date, the chapter lines, the
   song count, whether "Top N" is allowed, and the limits with their verified flags.
2. Gather evidence (section 2) and write `evidence.json`.
3. Write `youtube.json` (sections 3–8).
4. `python3 <skill-dir>/scripts/youtube_meta.py validate --run RUN`. Fix every `FAIL` and run it
   again. A `SKIP` means a limit has no verified source: say so to the human, do not call it a pass.
5. Independent review (section 10), then validate once more.

## 2. Evidence

SEO advice passed around without a source is what this skill avoids. Keywords come from what
you can observe on the day of the run:

- the chart's name, the song titles and the artists (from `facts`);
- titles of videos that currently rank for a few seed queries. Use the session's web search
  tool with 3 to 5 queries such as `nhạc remix tiktok <tháng>/<năm>`, `top nhạc remix việt
  <năm>`, `nhạc remix vinahouse`, `nonstop nhạc remix`, plus one built from the strongest song
  title. Record what you saw, not what you assume.

From the observed titles, pick one primary keyword (the phrase most of them share and that
describes this video truthfully) and three to five secondary ones.

```json
{
  "collected_on": "2026-11-10",
  "live": true,
  "queries": [
    {"query": "nhạc remix tiktok tháng 11 2026",
     "results": [{"title": "…tiêu đề quan sát được…", "url": "https://…"}]}
  ],
  "notes": "what the titles have in common, in one or two sentences"
}
```

At least three queries, each with at least one result that has `title` and `url`. Never add a
search volume, a view count you did not read on the page, or a field named `volume`: the
validator fails the package for it. With no web tool, write
`{"live": false, "reason": "…"}` and take keywords from `keywords_vi.md`; the package then
carries a `WARN` and `youtube.md` says the run had no live data.

## 3. youtube.json

```json
{
  "language": "vi",
  "primary_keyword": "nhạc remix",
  "secondary_keywords": ["vinahouse remix", "nhạc trẻ remix"],
  "titles": [
    {"text": "…", "angle": "số bài + thể loại", "scores": {"keyword": 5, "clarity": 4, "honesty": 5, "appeal": 4}, "why": "…"},
    {"text": "…", "angle": "thời điểm", "scores": {"keyword": 4, "clarity": 5, "honesty": 5, "appeal": 3}, "why": "…"},
    {"text": "…", "angle": "cảm xúc", "scores": {"keyword": 4, "clarity": 4, "honesty": 5, "appeal": 4}, "why": "…"}
  ],
  "description": "…the whole description, chapter lines included…",
  "tags": ["nhạc remix", "…"],
  "hashtags": ["#nhacremix", "#vinahouse", "#m10music"],
  "form": {
    "category": {"value": "Âm nhạc (Music)", "why": "…"},
    "video_language": {"value": "Tiếng Việt", "why": "…"},
    "audience": {"value": "Không, video này không dành cho trẻ em", "why": "…"},
    "altered_content": {"value": "Có", "why": "…"},
    "license": {"value": "Giấy phép chuẩn của YouTube", "why": "…"},
    "embedding": {"value": "Cho phép nhúng", "why": "…"}
  },
  "pinned_comment": "…",
  "playlist": "…"
}
```

The first title is the chosen one. Order the three by total score.

## 4. Titles

Write three that differ in angle, not three rewordings: for example the count and genre, the
moment (month and year of the chart), and the mood. Score each from 1 to 5:

| Score | 5 means |
|---|---|
| `keyword` | the primary keyword sits in the first 40 characters, in the words people type |
| `clarity` | a stranger knows what the video is from the title alone |
| `honesty` | every claim is true of this video: the count, the chart, the month, "vinahouse" |
| `appeal` | a reason to click that the video keeps |

Rules the validator enforces: the primary keyword appears in the chosen title; no title is
longer than `title_max_chars`; no `<` or `>`; a number of songs equals the real count; "Top N"
only when `may_say_top_n` is true (the songs are exactly ranks 1 to N of the chart). When songs
were skipped or backfilled, say "12 bài remix hot" rather than "Top 12". Titles never say
"official", "chính thức" about the video or the chart, or anything about being copyright free.
The style is called vinahouse, never EDM: the validator fails "edm" anywhere in the package.

## 5. Description

Order, top to bottom:

1. **Two opening lines** with the primary keyword and a reason to listen. Only these show
   before "…more".
2. **Tracklist with chapters.** Paste `chapter_lines` from `facts` exactly, one per line, first
   line `00:00`. YouTube builds chapters from them; the validator compares them with the mix.
3. **Credits.** Each song's original title and every original artist. The validator looks for
   each name.
4. **What this is**, in plain words: a vinahouse remix made by M10 Music with AI tools. For
   example: `Bản phối vinahouse do M10 Music thực hiện, phần nhạc nền được tạo bằng công cụ AI.`
   When `visuals.dj_picture_is_ai` in `facts` is true, also: `Hình ảnh nhân vật DJ trong video
   được tạo bằng AI, không phải người thật.` Leave that sentence out when the cover uses the
   human's own picture or a plain gradient.
5. **Where the list comes from**, as a fact with its date: `Danh sách bài dựa theo BXH Top 50
   Nhạc Remix Việt của NhacCuaTui ngày 09/11/2026.` Never as if the video were NCT's chart.
6. A short call to subscribe, then three to five **hashtags**. The first three show above the
   title.

Limits: `description_max_chars` and `description_max_bytes` both apply. Vietnamese letters
with diacritics take 2 to 3 bytes, so 5,000 bytes is roughly 3,000 to 3,500 Vietnamese
characters; a 12-song description fits, a padded one does not. No comma-separated keyword
dump: YouTube's policy counts excessive tags in a description as spam
(`misleading_metadata_policy` in the limits file).

## 6. Tags and hashtags

- Tags go from specific to broad: the primary keyword, the secondary ones, the genre, song
  titles, the channel name. A spelling without diacritics (`nhac remix`) is a different tag
  from `nhạc remix` and may sit next to it when the evidence shows people type it.
- The total counts commas and two quote marks for every tag with a space, against
  `tags_max_chars`.
- No tag names an artist who is not in the mix. The validator compares tags with every artist
  on the chart who was not selected.
- Hashtags: no spaces, a `#` each, far below `hashtags_max_count`.

## 7. Form choices

Give a value and a one-line reason for each. The usual answers, with the limit entry that
backs them:

| Field | Usual value | Reason |
|---|---|---|
| `category` | Âm nhạc (Music) | the video is a music mix |
| `video_language` | Tiếng Việt | the songs are sung in Vietnamese |
| `audience` | Không dành cho trẻ em | required at upload (`made_for_kids`); club music for a general audience |
| `altered_content` | Có | the backing tracks are AI-generated and are the focus of the video (`altered_content_disclosure`) |
| `license` | Giấy phép chuẩn của YouTube | the originals are other people's works; Creative Commons would grant rights the channel does not hold |
| `embedding` | Cho phép nhúng | no reason to forbid it |

Pass `account_reminders` from `facts` on to the human in your final message: a video longer
than 15 minutes and a custom thumbnail each need a verified account. Whether the channel is
verified is not something the skill can see.

## 8. Pinned comment and playlist

- `pinned_comment`: one question that invites an answer about the songs ("Bạn thích bản phối
  nào nhất?"), optionally the tracklist again. No claims beyond the facts.
- `playlist`: a name that would hold every mix of this series, e.g. `Nhạc Remix Việt –
  Vinahouse Mix | M10 Music`.

## 9. What each check means

| Check | Fails when | Fix |
|---|---|---|
| `schema` | a field is missing, or there are not exactly three scored titles | fill it in |
| `title_length`, `description_length`, `tags_length` | over the limit | shorten; for the description mind the byte limit |
| `forbidden_chars` | `<` or `>` in a title or the description | remove them |
| `title_keyword`, `description_opening` | the primary keyword is not in the chosen title, or not in the first two lines | rewrite, or pick the keyword the text really uses |
| `count_claims` | a number of songs differs from the mix, or "Top N" without `may_say_top_n` | use the real count; "N bài remix hot" |
| `description_chapters` | the timestamp lines differ from `chapter_lines` | paste them again, unchanged |
| `chapter_rules` | first mark not 00:00, fewer marks than YouTube needs, a chapter under the minimum | a mix problem: report it, do not edit the times |
| `description_credits` | a song title or an original artist is not named | add the credit |
| `ai_disclosure` | the description never says AI | add the two sentences of section 5 |
| `tags_unique`, `tags_artists` | a repeated tag; a tag naming an artist outside the mix | remove it |
| `hashtags` | none, malformed, or over the limit | fix the list |
| `tag_stuffing` | a line of the description is a comma-separated keyword dump | delete the line |
| `banned_phrases` | "official", "no copyright", "không bản quyền", "BXH chính thức"… | remove the claim |
| `search_volume_claims` | a search volume anywhere, or a `volume` field | remove it; evidence holds observations, not numbers |
| `evidence` | no `evidence.json`, or fewer than three queries with results | gather it, or mark the run `live: false` |

## 10. Independent review

After `validate` passes, give the package to a subagent that has not seen your reasoning. It
reads `RUN/youtube/youtube.json`, `RUN/youtube/evidence.json` and the output of
`youtube_meta.py facts`, nothing else. Ask it for a verdict (`APPROVE` or `REVISE`) and, for
`REVISE`, exact replacement text, judged on:

1. **True.** Does anything promise what the video does not deliver, imply an official release
   or chart, or name someone who is not in it?
2. **Clear.** Would a Vietnamese listener know from the title and the first two lines what
   they will hear and for how long?
3. **On the keyword.** Is the primary keyword the phrase the evidence supports, and is it
   placed where it counts, without repetition that reads as stuffing?
4. **Natural Vietnamese.** Does it read like a person wrote it? No machine-translated phrases,
   no strings of emoji, no all-caps lines.
5. **Ranking of the three titles.** Would it choose a different one first, and why?

Apply the edits you agree with, validate again, and stop after two rounds. Tell the human
which of the reviewer's points you did not take and why.
