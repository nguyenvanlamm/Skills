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
   write is in its output: songs, singers, composers, the period of the draw, the scene of the
   picture, the chapter lines, the song count, and the limits with their verified flags. Each
   track has the list's release `year` (or null): a period or decade named in a title or the
   description must hold for every track's year.
   `may_say_top_n` is always false: the songs are a random draw, not a ranking.
2. Gather evidence (section 2) and write `evidence.json`.
3. Write `youtube.json` (sections 3–8).
4. `python3 <skill-dir>/scripts/youtube_meta.py validate --run RUN`. Fix every `FAIL` and run it
   again. A `SKIP` means a limit has no verified source: say so to the human, do not call it a pass.
5. Independent review (section 10), then validate once more.

## 2. Evidence

SEO advice passed around without a source is what this skill avoids. Keywords come from what
you can observe on the day of the run:

- the period, the song titles and the singers (from `facts`);
- titles of videos that currently rank for a few seed queries. Use the session's web search
  tool with 3 to 5 queries such as `ballad lofi việt`, `nhạc lofi chill buồn`, `ballad lofi
  <giai đoạn, ví dụ 2010>`, `lofi chill học bài ngủ`, plus one built from the best-known song
  title. Add `site:youtube.com` (or `youtube`) to the queries: the titles that count are
  those of videos, and a package whose evidence holds no `youtube.com` or `youtu.be` result
  at all gets a `WARN`. Record what you saw, not what you assume.

From the observed titles, pick one primary keyword (the phrase most of them share and that
describes this video truthfully) and three to five secondary ones.

```json
{
  "collected_on": "2026-11-10",
  "live": true,
  "queries": [
    {"query": "ballad lofi việt chill",
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
  "primary_keyword": "ballad lofi",
  "secondary_keywords": ["lofi chill", "nhạc lofi buồn"],
  "titles": [
    {"text": "…", "angle": "số bài + thể loại", "scores": {"keyword": 5, "clarity": 4, "honesty": 5, "appeal": 4}, "why": "…"},
    {"text": "…", "angle": "giai đoạn", "scores": {"keyword": 4, "clarity": 5, "honesty": 5, "appeal": 3}, "why": "…"},
    {"text": "…", "angle": "cảm xúc", "scores": {"keyword": 4, "clarity": 4, "honesty": 5, "appeal": 4}, "why": "…"}
  ],
  "description": "…the whole description, chapter lines included…",
  "tags": ["ballad lofi", "…"],
  "hashtags": ["#balladlofi", "#lofichill", "#m10lofichill"],
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
period of the songs ("ballad 2010–2014"), and the mood or the moment to listen (học bài, đêm
mưa, trước khi ngủ). Score each from 1 to 5:

| Score | 5 means |
|---|---|
| `keyword` | the primary keyword sits in the first 40 characters, in the words people type |
| `clarity` | a stranger knows what the video is from the title alone |
| `honesty` | every claim is true of this video: the count, the period, "lofi chill", the voices being the original singers' |
| `appeal` | a reason to click that the video keeps |

Rules the validator enforces: the primary keyword appears in the chosen title; no title is
longer than `title_max_chars`; no `<` or `>`; a number of songs equals the real count; never
"Top N": the songs are a random draw from the channel's list, so "12 bản ballad lofi" is true
and "Top 12" is not. No "BXH", "bảng xếp hạng", "xếp hạng" or "hot nhất" either. Titles never say
"official" or "chính thức", or anything about being copyright free. The style is called lofi
chill: the validator fails remix, vinahouse, nhạc sàn, EDM and DJ anywhere in the package
(remix is the name of the channel's vinahouse series).

## 5. Description

Order, top to bottom:

1. **Two opening lines** with the primary keyword and a reason to listen. Only these show
   before "…more".
2. **Tracklist with chapters.** Paste `chapter_lines` from `facts` exactly, one per line, first
   line `00:00`. YouTube builds chapters from them; the validator compares them with the mix.
3. **Credits.** Each song's original title and every original artist. The validator looks for
   each name.
3b. **Composers**, when `facts` has them: one line per song or a short "Sáng tác: …" after
   each credit line. They are the people the song belongs to; naming them costs nothing.
4. **What this is**, in plain words: a lofi chill version made by M10 lofi chill with AI tools,
   the voices those of the original recordings. For example: `Bản lofi chill do M10 lofi chill
   thực hiện: nhạc nền lofi được tạo bằng công cụ AI, giọng hát giữ nguyên từ bản gốc.` When
   `visuals.picture_is_ai` in `facts` is true, also: `Tranh phong cảnh trong video được vẽ bằng
   AI.` Leave that sentence out when the cover uses the human's own picture or a plain gradient.
5. **Where the songs come from**, as a fact: `Các bài trong video được chọn ngẫu nhiên từ danh
   sách ballad Việt giai đoạn 2010–2014 của kênh.` Never as a ranking.
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
- No tag names an artist who is not in the mix. The validator compares tags with every singer
  of the draw who was not selected.
- Hashtags: no spaces, a `#` each, far below `hashtags_max_count`.

## 7. Form choices

Give a value and a one-line reason for each. The usual answers, with the limit entry that
backs them:

| Field | Usual value | Reason |
|---|---|---|
| `category` | Âm nhạc (Music) | the video is a music mix |
| `video_language` | Tiếng Việt | the songs are sung in Vietnamese |
| `audience` | Không dành cho trẻ em | required at upload (`made_for_kids`); ballads for a general audience |
| `altered_content` | Có | the lofi backing tracks and the picture are AI-generated and are the focus of the video (`altered_content_disclosure`) |
| `license` | Giấy phép chuẩn của YouTube | the originals are other people's works; Creative Commons would grant rights the channel does not hold |
| `embedding` | Cho phép nhúng | no reason to forbid it |

Pass `account_reminders` from `facts` on to the human in your final message: a video longer
than 15 minutes and a custom thumbnail each need a verified account. Whether the channel is
verified is not something the skill can see.

## 8. Pinned comment and playlist

- `pinned_comment`: one question that invites an answer about the songs ("Bài nào làm bạn nhớ
  nhất giai đoạn này?"), optionally the tracklist again. No claims beyond the facts.
- `playlist`: a name that would hold every mix of this series, e.g. `Ballad Việt Lofi – M10
  lofi chill`.

## 9. What each check means

| Check | Fails when | Fix |
|---|---|---|
| `schema` | a field is missing, or there are not exactly three scored titles | fill it in |
| `title_length`, `description_length`, `tags_length` | over the limit | shorten; for the description mind the byte limit |
| `forbidden_chars` | `<` or `>` in a title or the description | remove them |
| `title_keyword`, `description_opening` | the primary keyword is not in the chosen title, or not in the first two lines | rewrite, or pick the keyword the text really uses |
| `count_claims` | a number of songs differs from the mix, or any "Top N" | use the real count; "N bản ballad lofi" |
| `description_chapters` | the timestamp lines differ from `chapter_lines` | paste them again, unchanged |
| `chapter_rules` | first mark not 00:00, a chapter under the minimum (`FAIL`); fewer marks than YouTube needs for chapters (`WARN`: a mix of one or two songs) | a mix problem: report it, do not edit the times |
| `description_credits` | a song title or an original artist is not named | add the credit |
| `ai_disclosure` | the description never says AI | add the two sentences of section 5 |
| `tags_unique`, `tags_artists` | a repeated tag; a tag naming an artist outside the mix | remove it |
| `hashtags` | none, malformed, or over the limit | fix the list |
| `tag_stuffing` | a line of the description is a comma-separated keyword dump | delete the line |
| `banned_phrases` | "official", "no copyright", "không bản quyền", remix, vinahouse, EDM, DJ, BXH, "hot nhất"… | remove the claim |
| `search_volume_claims` | a search volume anywhere, or a `volume` field | remove it; evidence holds observations, not numbers |
| `evidence` | no `evidence.json`, or fewer than three queries with results | gather it, or mark the run `live: false` |

## 10. Independent review

After `validate` passes, give the package to a subagent that has not seen your reasoning. It
reads `RUN/youtube/youtube.json`, `RUN/youtube/evidence.json` and the output of
`youtube_meta.py facts`, nothing else. Ask it for a verdict (`APPROVE` or `REVISE`) and, for
`REVISE`, exact replacement text, judged on:

1. **True.** Does anything promise what the video does not deliver, imply an official release,
   a ranking or a remix, or name someone who is not in it?
2. **Clear.** Would a Vietnamese listener know from the title and the first two lines what
   they will hear and for how long?
3. **On the keyword.** Is the primary keyword the phrase the evidence supports, and is it
   placed where it counts, without repetition that reads as stuffing?
4. **Natural Vietnamese.** Does it read like a person wrote it? No machine-translated phrases,
   no strings of emoji, no all-caps lines.
5. **Ranking of the three titles.** Would it choose a different one first, and why?

Apply the edits you agree with, validate again, and stop after two rounds. Tell the human
which of the reviewer's points you did not take and why.
