# The posts

`sceneloom seo facts <id>` prints the title, summary, length and audience. Write
`<project>/seo.json`; `sceneloom seo import` checks it and `sceneloom publish --dry-run` shows what
each platform would receive.

## Shape of `seo.json`

```json
{
  "titles": ["3-6 candidate titles, each at most 100 characters"],
  "description": "at least 80 characters; the long-form description, kept for the record",
  "tags": ["5 to 30 tags", "within 500 characters in total"],
  "hashtags": ["#one", "#to", "#five"],
  "pinned_comment": "a question to the viewers",
  "thumbnail_texts": ["at most 5 words each"],
  "shorts": {
    "title": "at most 100 characters, no < or >",
    "description": "two or three sentences",
    "hashtags": ["#three", "#to", "#five"]
  },
  "tiktok": {
    "caption": "the text only, no hashtags inside it",
    "hashtags": ["#three", "#to", "#five"]
  }
}
```

The numbers the checker uses are in `<sceneloom>/sceneloom/limits.json`, each with its source and
the date it was read. When a limit looks out of date, say so; do not change the file from here.

## What the checker enforces

| Block | Rule |
|---|---|
| `shorts` | title present, at most 100 characters; description at least 40 characters; description plus hashtags within 5000 bytes; no `<` or `>` |
| `tiktok` | caption at least 20 characters with no `#` in it; caption plus hashtags within 2200 UTF-16 units |
| both | 3-5 hashtags, each `#` plus letters, digits or `_`, none repeated, none of `#fyp #foryou #foryoupage #viral #xuhuong #trending #fy` |

## What the checker cannot judge

- **The first words carry the post.** Both feeds cut the text after a line. Open with the
  situation ("Bà bán rau thối dư tiền cho shipper, ba ngày liền"), not with the channel or a
  greeting.
- **Promise only what the video delivers.** No "kết không ai ngờ" unless the ending is one; no
  claim about views, trends or search volume you have not measured.
- **Say it was made with AI.** One plain sentence in the Shorts description and in the TikTok
  caption, for example "Video được tạo bằng AI." The upload also carries the platforms' own AI
  label; the sentence is for the viewer.
- **Hashtags describe the video**: its form (`#tieupham`, `#phimngan`), its subject, its feeling.
  A tag that fits every video helps none.
- **Write the two platforms separately.** Shorts takes a title and a description; TikTok takes
  one caption and is read faster. Do not paste one into the other.
- **Vietnamese with full diacritics.** No emoji walls, no all-caps.

## What posting does

| Platform | What `sceneloom publish` does | What stays with the human |
|---|---|---|
| YouTube | uploads the file with the Shorts title, description, tags, the AI label and "not made for kids"; visibility is `private` unless `--privacy unlisted` or `public` is given | changing visibility later, the thumbnail, the pinned comment |
| TikTok | sends the file to the account's TikTok inbox through TikTok Hub | in the TikTok app: paste the caption, choose who can see it, add sound if wanted, post |

TikTok's inbox route takes no caption, which is why the caption is handed over as text. A project
gets a default of 100 YouTube uploads a day; TikTok keeps at most 5 unposted inbox videos per
account in 24 hours.

A video counts as a Short when it is at most 3 minutes long and upright. `--dry-run` adds a note
when the video would be listed as a normal video instead.
