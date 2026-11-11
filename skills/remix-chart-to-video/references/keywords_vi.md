# Baseline keywords (fallback only)

Use this list only when the session has no web search tool, and then write
`{"live": false, "reason": "…"}` in `evidence.json`. These are phrases Vietnamese remix mixes
are commonly titled with. They carry no search numbers and were not measured; do not present
them as evidence.

Seed queries to try when a web tool is available:

- `nhạc remix tiktok <tháng> <năm>`
- `top nhạc remix việt <năm>`
- `nhạc remix vinahouse <năm>`
- `nonstop vinahouse <năm>`
- `nhạc remix hot nhất hiện nay`
- `<tên bài mạnh nhất trong mix> remix`

Broad phrases: `nhạc remix`, `nhạc remix việt`, `nhạc trẻ remix`, `nhạc vinahouse`,
`vinahouse remix`, `nhạc remix tiktok`, `nonstop`, `nhạc sàn`, `mix nhạc remix`.

Modifiers that are true of this video and may be combined with them: the month and year of
the chart, the song count, `vinahouse`, `mix liền mạch`, `m10 music`.

Phrases to avoid because they claim something the video is not, or name its style wrongly:
`official`, `chính thức`, `không bản quyền`, `no copyright`, `edm` (the channel calls its style
vinahouse; the validator fails it), another style such as `deep house` or `big room`, an
artist who is not in the mix.
