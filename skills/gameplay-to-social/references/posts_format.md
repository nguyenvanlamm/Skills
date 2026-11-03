# posts.json and posts.md

Read at Step 6, before writing posts.json. `validate_posts.dart` checks the file against this
page (the `g2s-fields` block), `platform_specs.md` (limits) and `review_rubric.md` (rules), then
renders `posts.md` from it with `--render`. Never write posts.md by hand. That way posts.md
always matches the data the validator passed.

## Shape

```jsonc
{
  "schema": "gameplay-to-social/posts@1",
  "created": "2026-11-03T17:20:00+07:00",
  "game": {
    "name": "Pebble Hop",                      // display name, as in config.yaml
    "own_hashtag": "#PebbleHop",               // config.yaml → hashtags.own (same in every post)
    "core_hashtags": ["#puzzlegame", "#cozygame"],
    "links": {"app_store": "https://apps.apple.com/app/id000", "play_store": null, "website": null}
  },
  "run": {
    "level": 10,
    "requested": "chạy game level 10, quay 20s, làm bài 4 nền tảng",
    "assumptions": ["duration 20 s (default)", "clip continues into level 11 at 8.3 s: the bot clears 10 in 6.8 s"],
    "platforms": ["tiktok", "reddit", "linkedin", "x"],
    "trend_check": {"verified": true, "checked_at": "2026-11-03", "sources": ["https://…"]}
  },
  "accounts": {"tiktok": "personal", "x_premium": false},
  "facts": [                                   // confirmed facts only (config.yaml → facts)
    {"id": "levels_total", "text": "60 levels", "source": "lib/game/progress.dart:46, confirmed 2026-11-03", "confirmed": true}
  ],
  "tiktok":   { "language": "vi", "chosen": "tt-2", "chosen_reason": "", "variants": [ … ] },
  "reddit":   { "language": "en", "subreddits": [ { "subreddit": "r/…", …, "chosen": "rd-1b", "variants": [ … ] } ] },
  "linkedin": { "language": "en", "chosen": "li-1", "variants": [ … ] },
  "x":        { "language": "en", "chosen": "x-3",  "variants": [ … ] }
}
```

Only the platforms in `run.platforms` need a block. Every variant carries:

- `id`: unique within the platform, e.g. `tt-1`, `rd-2a`.
- `angle`: the content angle in a few words. Each variant needs a different one.
- `angle_type`: one of the `angle_types` below. It decides whether dev hashtags are allowed.
- `video`: path relative to the run folder, e.g. `video/tiktok_9x16.mp4`. The file must exist.
- `claims`: every hard fact the text uses, as `{"text": "60 levels", "fact_id": "levels_total"}`.
  `fact_id` must point at a confirmed entry in `facts`.
- `scores`: `hook`, `emotion`, `trend`, `engagement`, `platform_fit`, `hashtags`, each 1–5
  (review_rubric.md). The validator computes the weighted total, so don't add it yourself.
- `notes`: optional, one line on why this variant works.

## Fields per platform

**TikTok**

| field | what goes in |
|---|---|
| `on_screen_hook` | text on the video for the first 2 s; about 8 words (10 Vietnamese syllables) |
| `title` | short title if the upload screen offers one (photo posts only today), else `""` |
| `caption` | first line is the hook with a searched or trending keyword; ends on a question or a natural call; no hashtags here |
| `hashtags` | 4–5 tags: the game's own tag, a genre or gaming-community tag, 1–2 trending tags, at most one generic (#fyp…) |
| `trend_hashtags` | `[{"tag": "#…", "bridge": "the sentence in the caption that links the post to that trend"}]` for every trend outside the game |
| `sound` | `{"choice": "original" \| "trending", "name": "…", "note": "…", "commercial_library": true}`; a business account may only use the Commercial Music Library |
| `cover_timestamp` | seconds into `video/tiktok_9x16.mp4` (qc.json → cover_at, or your pick) |
| `cover_text` | a few words for the cover |
| `pinned_comment` | the first comment you pin: a question, a dare, or the link if the account can't use bio links |
| `post_time` | local day and time with the timezone, e.g. `2026-11-05 19:30 ICT (Thu)` |

**Reddit**: write a separate post for each of 2–3 subreddits. The subreddit block has:

| field | what goes in |
|---|---|
| `subreddit` | `r/Name` |
| `why` | why this sub fits the game and the angle |
| `rules` | the rules that apply to this post: self-promo limits, flair, day, link placement, AI disclosure |
| `rules_checked` | date and how, starting with the date: `2026-11-03, sidebar via web search`, or `2026-11-03, second-hand (search summaries; reddit.com not reachable)` |
| `link_in_comment` | true when the sub wants links in a comment; the validator then rejects a link in the body |
| `post_time` | different for every sub |
| `chosen`, `variants` | as above |

Each Reddit variant has these fields (flair: the sub's flair if known; `""` if it has none; if it has flair you couldn't read, your best guess plus a note in `rules`):
- `title`: ≤ 300 characters, a real person's voice, no hashtags, no emoji.
- `flair`: may be `""` if the sub has none.
- `oc` and `spoiler`: booleans.
- `body` or `first_comment`: who you are, what the game is, what stage it's at, what feedback you want. The link goes in the comment when the sub asks.

**LinkedIn**

| field | what goes in |
|---|---|
| `hook` | the 2–3 lines before "…see more" (~210 chars) |
| `body` | the work story or lesson, in short paragraphs |
| `cta` | one open question for the community |
| `hashtags` | 1–3: game/industry tags for a game angle, Flutter tags only for a tech angle |
| `first_comment` | holds the link |
| `video_version` | `4:5` (`video/linkedin_4x5.mp4`) unless you say why not |
| `post_time` | as above |

**X**

| field | what goes in |
|---|---|
| `post` | the full text with its hashtags inline; ≤ 280 weighted (twitter-text v3) unless Premium |
| `thread` | optional list of 2–4 follow-up posts (behind the scenes) |
| `hashtags` | the 1–2 tags used in `post`, listed again |
| `trend_hashtags` | as for TikTok |
| `alt_text` | what the video shows, for screen readers (≤ 1,000) |
| `reply_with_link` | the first reply, with the link |
| `community` | `null`. X shut down Communities in 2026; set it only if they are back |
| `post_time` | as above |

## Machine block

```g2s-fields
variants.min: 3
angle_types: relatable, pov, challenge, humor, satisfying, rage, comparison, trend_bridge, story, tech, behind_the_scenes, other
dev_angle_types: tech, behind_the_scenes
tiktok.required: id, angle, angle_type, video, on_screen_hook, title, caption, hashtags, sound, cover_timestamp, cover_text, pinned_comment, post_time, scores
tiktok.may_be_empty: title
reddit.subreddits.min: 2
reddit.subreddits.max: 3
reddit.sub.required: subreddit, why, rules, rules_checked, post_time, chosen, variants
reddit.required: id, angle, angle_type, video, title, flair, body|first_comment, scores
reddit.may_be_empty: flair
linkedin.required: id, angle, angle_type, video, video_version, hook, body, cta, hashtags, first_comment, post_time, scores
x.required: id, angle, angle_type, video, post, hashtags, alt_text, reply_with_link, post_time, scores
x.thread.max_posts: 4
```

`assets/posts.example.json` is a complete file that passes the validator. Copy its structure,
not its facts: every dev-story line in it has a claim behind it.

**No links yet** (every `game.links` value null): no URL anywhere. `first_comment` and
`reply_with_link` then carry context, a question or "coming soon", and
`link_in_comment` stays false.
