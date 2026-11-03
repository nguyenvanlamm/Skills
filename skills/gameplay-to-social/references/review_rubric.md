# Review rubric

Read at Step 7. Every variant goes through three passes:

1. The knock-out round. A variant that fails any check here is out.
2. Scoring.
3. One polish pass, done in the persona of someone scrolling that platform.

`validate_posts.dart` enforces everything in the `g2s-rules` block mechanically. The rest is
your judgement, and you write it down in `review_report.md`.

## 1. Knock-out round

A variant is out if any of these is true:

- **A platform limit or a subreddit rule is broken.** This covers character counts, hashtag
  counts, link placement, flair, posting day and AI disclosure.
- **It gets a hard fact about the game wrong.** Hard facts are features, numbers (downloads,
  ratings, the share of players who clear a level), awards, prices, discounts, giveaways and
  dev-story facts (how long it took, team size). Each one must match the project and
  `config.yaml → facts`. If you want a number as a hook, ask the developer for the real one.
  Wrong hard facts get posts removed, get called out by the community, or break ad and
  consumer-protection rules. The validator flags any phrase that looks like a hard fact and
  has no confirmed claim behind it.
- **A trend hashtag from outside the game has no bridge.** The text must contain the sentence
  that connects the game to that trend. Example: "Level 10 còn khó hơn đề thi 😭" makes an
  exam-season tag fair. Stuffing trending tags is spam: X's Authenticity policy names "using
  trending or popular hashtags with an intent to subvert or manipulate a conversation", and it
  also sends the video to the wrong viewers.
- **It rides a sensitive trend.** That means disasters, accidents, deaths, politics, elections,
  religion, layoffs, or real people's scandals. Check the news on the posting day: central
  Vietnam's flood season and similar events change week to week.
- **It reads like stock ad copy or AI copy.** See `banned` below. Natural exclamations, slang and
  emoji are welcome. Templated marketing phrases are not.
- **It promises a moment the clip doesn't have.** "Xem đến cuối để thấy boss" with no boss in the
  clip makes viewers swipe away, and completion rate is the signal that matters most.

## 2. Scoring

Score each criterion from 1 to 5, multiply by its weight, and add them up. The maximum is 60.

| Criterion | Weight | 5 means |
|---|---|---|
| `hook` | ×3 | a stranger who has never heard of the game stops scrolling in the first second (on-screen text + first line + first frame) |
| `emotion` | ×2 | the words carry clear energy: hype, salt, suspense, surprise, laughter, "đã mắt" |
| `trend` | ×2 | the words, format, meme or sound are current (seen in trend_words.md within its freshness window, or checked today) |
| `engagement` | ×2 | it gives people a reason to comment, share, save or tag a friend (a dare, a question with an easy answer, a "tag the friend who…") |
| `platform_fit` | ×2 | it matches the platform's culture and how much hype that platform tolerates (viral_playbook.md § Voice) |
| `hashtags` | ×1 | the tags reach people who play this kind of game, are still live, and are searched |

Pick the highest-scoring variant on each platform. To pick a lower one, write `chosen_reason`.

## 3. Polish pass

Re-read the chosen variant as someone thumbing fast through that feed:

- **TikTok / X**: "Would I stop, like, comment?" If the answer is "maybe", sharpen the hook. Ways to
  do that: make the line shorter, put the conflict first, use a number the clip actually shows,
  or turn it into a dare.
- **LinkedIn**: "Does the first line make me press …see more, and is there a real lesson?"
- **Reddit**: read it as a redditor who hates ads. Anything that sounds like marketing (hype
  words, exclamation marks, "check out", a link in the title) goes. A real person telling a
  story with some self-deprecation survives.

Make one rewrite. Run the validator again, then score the rewrite.

## review_report.md

Use exactly these sections:

```
# Review — <game> level <N> — <date>
## Chosen
<platform>: <id> — <angle> — <score>/60 — why it wins (one line)
## Scores
<table: platform, id, angle, hook, emotion, trend, engagement, fit, hashtags, total, out? (why)>
## Knocked out
<variant: reason>
## Warnings
<validator warnings kept on purpose, with why; video QC warnings (upscaled, silent, continued into next level)>
## Not verified
<trends not checked online, subreddit rules from summaries only, facts still unconfirmed>
## Assumptions
<from run.assumptions>
```

## Machine block

```g2s-rules
weights.hook: 3
weights.emotion: 2
weights.trend: 2
weights.engagement: 2
weights.platform_fit: 2
weights.hashtags: 1

# Hashtag counts. The developer asked for 4–6 on TikTok; TikTok has capped posts at 5 in the app
# since 2025-08 (reported, not confirmed), so 4–5 works under both.
tiktok.hashtags.min: 4
tiktok.hashtags.max: 5
tiktok.generic_hashtags.max: 1
x.hashtags.min: 1
x.hashtags.max: 2
linkedin.hashtags.min: 1
linkedin.hashtags.max: 3
tiktok.on_screen_hook.max_words: 8
tiktok.on_screen_hook.max_words.vi: 10
tiktok.cover_text.max_words: 8

generic_hashtag: #fyp
generic_hashtag: #foryou
generic_hashtag: #foryoupage
generic_hashtag: #fy
generic_hashtag: #xuhuong
generic_hashtag: #xuhuongtiktok
generic_hashtag: #trending
generic_hashtag: #trend
generic_hashtag: #viral
generic_hashtag: #viralvideo
generic_hashtag: #tiktok
generic_hashtag: #explore

# Only on tech / behind-the-scenes angles.
dev_hashtag: #flutter
dev_hashtag: #flutterdev
dev_hashtag: #flutterdeveloper
dev_hashtag: #dart
dev_hashtag: #dartlang
dev_hashtag: #flame
dev_hashtag: #flameengine
dev_hashtag: #madewithflutter
dev_hashtag: #indiedev
dev_hashtag: #indiegamedev
dev_hashtag: #gamedev
dev_hashtag: #solodev
dev_hashtag: #devlog
dev_hashtag: #buildinpublic

# Stock ad / AI phrases (case-insensitive substring match).
banned: trải nghiệm đỉnh cao
banned: đừng bỏ lỡ
banned: không thể bỏ qua
banned: không thể bỏ lỡ
banned: hãy cùng khám phá
banned: khám phá ngay
banned: siêu phẩm
banned: tuyệt tác
banned: hành trình đầy thú vị
banned: thế giới đầy màu sắc
banned: mang đến trải nghiệm
banned: trải nghiệm tuyệt vời
banned: trải nghiệm chơi game
banned: hứa hẹn mang lại
banned: vô cùng hấp dẫn
banned: đầy thử thách và thú vị
banned: nâng tầm
banned: đắm chìm
banned: game-changer
banned: game changer
banned: dive into
banned: dive in
banned: delve
banned: immersive experience
banned: unleash
banned: embark on
banned: elevate your
banned: a journey like no other
banned: like never before
banned: don't miss out
banned: don’t miss out
banned: must-play
banned: look no further
banned: whether you're a
banned: whether you’re a
banned: it's not just a game
banned: it’s not just a game
banned: take your gaming to the next level
banned: experience the thrill
banned: perfect blend
banned: testament to
banned: seamless
banned: unparalleled
banned: captivating
banned: tapestry
banned: realm of
banned: harness the power
banned: buckle up
banned: check out my game
banned: check out our game

# Sensitive topics (warning: make sure the post does not ride them).
sensitive: động đất
sensitive: bão lũ
sensitive: lũ lụt
sensitive: sạt lở
sensitive: tai nạn
sensitive: thảm họa
sensitive: thảm hoạ
sensitive: chiến tranh
sensitive: bầu cử
sensitive: tôn giáo
sensitive: đám tang
sensitive: qua đời
sensitive: tử vong
sensitive: earthquake
sensitive: hurricane
sensitive: flood
sensitive: wildfire
sensitive: shooting
sensitive: war
sensitive: election
sensitive: midterms
sensitive: politics
sensitive: religion
sensitive: funeral
sensitive: layoffs

# Payoff promises (warning: the clip must deliver them).
promise: xem đến cuối
promise: xem tới cuối
promise: đợi đến cuối
promise: chờ đến cuối
promise: cuối video
promise: wait till the end
promise: wait until the end
promise: watch till the end
promise: watch until the end
promise: wait for it
promise: end of the video

# Hard facts (regex, case-insensitive): each match needs a claim backed by a confirmed fact.
hardfact.downloads: \d[\d.,]*\s*(k|m|tr|triệu|nghìn|ngàn)?\+?\s*(lượt tải|lượt cài|lượt chơi|downloads?|installs?|players?|người chơi)
hardfact.rating: (\d([.,]\d)?\s*(★|⭐|sao(?!\p{L})|stars?\b))|(rated\s+\d)
hardfact.rank: (top\s*\d+\b)|(#\s?1\b)|(số\s*1\b)|(number one)|(no\.\s*1\b)|(hạng\s*\d+)
hardfact.award: (giải thưởng|đoạt giải|giành giải|award|winner of|nominated|đề cử)
hardfact.promo: (miễn phí|free to play|free-to-play|free download|for free|giảm giá|khuyến mãi|\bsale\b|giveaway|tặng code|quà tặng|promo code|mã quà|\d+\s*%\s*off)
hardfact.player_share: \d+([.,]\d+)?\s*%\s*(người chơi|players?|of players|người|qua|pass|clear|win|thắng|bỏ cuộc|quit)
hardfact.devtime: (\d+\s*(ngày|tuần|tháng|năm|days?|weeks?|months?|years?)\s*(làm|phát triển|code|dev\b|of (work|dev|development)|building|to (make|build)))|((made|built|developed|coded)\s+(it\s+)?in\s+\d+\s*(days?|weeks?|months?|years?))
hardfact.team: (solo dev|one-person|một mình làm|1 người làm|team of \d+|\d+\s*(devs?|developers?)\b)
hardfact.content_count: \d+\s*(levels?|màn chơi|màn|stages?|worlds?|chapters?|chương|puzzles?|câu đố)(?!\p{L})
```
