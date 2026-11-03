# Viral playbook

Read at Steps 4–6. This file covers the craft: angles, hooks, voice, hashtags and platform
habits. What is trending this week lives in `trend_words.md`. Numbers and limits live in
`platform_specs.md`.

## 1. What wins

- **The first second decides.** Feeds measure whether people stop, watch to the end and
  rewatch. The on-screen hook, the first caption line and the first frame do that job together.
  Put the conflict, the payoff or the question up front, never a logo.
- **Talk like a player, not an ad.** Write like you're texting a friend about a level that just
  wrecked you. Exclamations, slang, emoji and "trời ơi" are fine. "Trải nghiệm đỉnh cao" is not.
- **Be specific.** "Level 10 lừa mình 3 lần" beats "game khó". "8 bước, par 8, không thừa một
  bước" beats "chơi hay". Use numbers the clip shows (steps, timer, score) or that the
  developer has confirmed.
- **Make it easy to comment.** Ask a question anyone can answer in one word, set a dare, or
  give a "tag the friend who…".
- **Don't promise what isn't there.** Go beyond the clip with situations, POVs and comparisons.
  But never promise a scene the clip doesn't have, because completion rate drops when viewers
  feel tricked.

## 2. Angles

Pick three different angles per platform, matched to the clip (brief.md) and the platform's
voice. `angle_type` in posts.json uses these names.

| angle_type | Idea | TikTok / X example | Fits |
|---|---|---|---|
| `relatable` | the situation every player knows | "Ai đã từng nói 'màn cuối rồi ngủ' lúc 1h sáng… điểm danh 🙋" | TikTok, X |
| `pov` | the viewer is inside the moment | "POV: bạn tưởng level 10 dễ 🙂" | TikTok |
| `challenge` | dare the viewer | "Chan đê: qua màn này dưới 10 bước. Mình làm được 8 😤" | TikTok, X |
| `rage` | salt, rage-quit energy, made funny | "Màn này được thiết kế bởi kẻ thù của tôi" | TikTok, X |
| `satisfying` | eye candy, ASMR, the perfect move | "Cái cảm giác bước đúng ô cuối cùng 🤤" | TikTok |
| `comparison` | level 1 vs 10, noob vs pro, expectation vs reality, "X but…" | "Level 1: dễ thương. Level 10: 💀" | TikTok, X, Reddit |
| `humor` | self-deprecating dev or player | "Mình làm game này. Mình vẫn thua màn 10." | all |
| `trend_bridge` | ride a live trend with a real bridge | "Everyone's playing GTA VI. Someone's gotta hold it down." | TikTok, X |
| `story` | the making-of journey, a decision, a lesson | "Mình xoá 40 level vì một lý do…" | LinkedIn, Reddit |
| `tech` | how it's built (Flutter, Flame, a solver, 60fps) | "One CustomPainter, a solver that proves every level is beatable" | LinkedIn, X, r/FlutterDev |
| `behind_the_scenes` | bugs, cut features, first prototype vs now | "First prototype vs today 👀" | all |
| `other` | anything else, explained in `notes` | | |

The "made with Flutter/Flame" angle is just one angle. It fits LinkedIn, X and r/FlutterDev
best. It is not the default.

## 3. Hooks

**On screen, first 2 s**: about 8 words, high contrast, no emoji (the burned-in text can't show
them). Formulas:

- Conflict: "Level 10 lừa mình 3 lần" · "This level is a scam"
- Wrong assumption: "Tưởng dễ… cho đến khi…" · "Looks easy. It isn't."
- Dare: "Qua được không? Chan đê" · "Bet you can't do it in 8"
- Number from the clip: "8 bước. Không thừa một bước." · "8 steps. Zero mistakes."
- POV: "POV: 1h sáng, màn cuối rồi ngủ"

**First caption line**: the hook again, plus one keyword people search ("game giải đố", "game
mobile", "puzzle game", the genre) or a live trend word.

**Last line**: a question or a natural call. Examples: "Bạn qua màn này mấy lần?", "Tag đứa hay
rage quit", "Describe this level in one word."

## 4. Emotions

Choose one main emotion per variant and let the words carry it:

| Emotion | Vietnamese | English |
|---|---|---|
| hype | "trời ơi đẹp gì đâu", "bá khí quá" | "the way it just CLICKS" |
| salt | "cay", "tức á", "lừa nhau à" | "I'm not mad. I'm fine. (I'm mad)" |
| suspense | "1 bước nữa thôi…" | "one step from disaster" |
| surprise | "khoan… cái gì vậy" | "wait— what" |
| humour | "dạ gỗ xà cừ ạ" | "skill issue (mine)" |
| eye candy | "đã mắt", "nhìn mà chill" | "so satisfying" |

## 5. Voice by platform

| Platform | Hype | Write like | Avoid |
|---|---|---|---|
| TikTok | highest | a hyped friend; trends, slang, emoji, POV, dares | stale slang; generic tag stuffing; payoff promises |
| X | high, short | meme captions, one punchline, maybe a thread | more than 2 hashtags; links in the main post |
| LinkedIn | medium | a maker telling what they learned; emotion tied to the work; little slang | hype words, emoji walls, links in the body (put them in the first comment) |
| Reddit | low | a real person, honest, self-deprecating, asking for feedback | marketing tone, hashtags, emoji in titles, "check out my game", links in titles |

## 6. Hashtags

Mix these layers, and pick each tag for this post:

1. **The game's own tag** (config `hashtags.own`), the same in every post so it builds up.
2. **Genre and platform**, e.g. #puzzlegame #cozygame #mobilegame #gamemobile #androidgames.
3. **Gaming community**, e.g. #gaming #gamer #game.
4. **A famous game in the same genre**, only when the caption compares to it or mentions it.
5. **The emotion or situation of the post**, e.g. #ragequit #satisfying.
6. **A live trend** (trend_words.md, checked today). If it's outside the game (an event, a season,
   a meme), the caption must hold the sentence that bridges to it. List it in `trend_hashtags`.
7. **Dev tags** (#flutter #flutterdev #indiedev #gamedev): only on `tech` / `behind_the_scenes` angles.

Counts are in `review_rubric.md`: TikTok 4–5, X 1–2, LinkedIn 1–3, Reddit 0. Allow at most one
generic reach tag (#fyp/#xuhuong), since those are too diluted to help. Match the tag's language to
the post's market. Vietnamese and English tags may sit together.

A bridge example for exam season (TikTok vi):
caption "Level 10 còn khó hơn đề thi học kỳ 😭 …" with tags `#PebbleHop #gamemobile #puzzlegame #muathi`,
and `trend_hashtags: [{"tag": "#muathi", "bridge": "Level 10 còn khó hơn đề thi học kỳ 😭"}]`.

## 7. Platform habits

### TikTok
- **Caption**: hook line, then one or two short lines (what happens, the emotion), then the
  question. Hashtags go in the `hashtags` field.
- **Sound**:
  - Original game audio suits satisfying and ASMR clips.
  - A trending sound suits POV and meme formats, as long as the account may use it.
  - A business account may use only the Commercial Music Library.
  - A silent recording (iOS simulator, a game without sound) needs a sound picked in the app.
- **Cover**: the clip's sharpest action frame (`qc.json → cover_at`), plus 2–5 words of cover text.
- **Pinned comment**: a dare, a poll-like question, or the link when the bio can't hold it.
- **Post time for a Vietnamese audience**: weekdays 11:30–13:00 or 19:00–22:30 ICT. Weekends run later.
  TikTok Studio can schedule up to 30 days ahead.

### Reddit
- **Pick 2–3 subs that fit the genre.** Before writing, check each sub's rules today. Rules
  change, and most subs remove posts that break them. Candidates (rules as of 2026-11,
  second-hand, so verify):

  | Sub | Developer posts | Notes |
  |---|---|---|
  | r/indiegames | allowed with gameplay media and flair (Promotion/Video/Upcoming) | no store/social links in the post; no "would you play this?" titles |
  | r/IndieGaming | one submission every 2 weeks | disclose generative-AI use; no store-page-only posts |
  | r/IndieDev | relaxed | images/GIFs do better than links |
  | r/AndroidGaming | title must start with "[DEV]" | follow the self-promo guidelines |
  | r/iosgaming | only in the Developer Saturday megathread | anything else is removed |
  | r/MobileGaming | no stated rule | ask the mods first |
  | r/playmygame | game must be free to play now; one post a month | paid games only on Trailer Tuesday |
  | r/puzzlevideogames | self-promo reportedly allowed | small but on-topic for puzzles |
  | r/WebGames | browser-playable only | a Flutter web build can qualify |
  | r/FlutterDev | tech angle only | app ads get removed; show code or a lesson |
  | r/gamedev | not for showing off | post-mortems with numbers, feedback threads |
  | r/DestroyMyGame | harsh feedback on a clip | flair by stage |

- **Title**: what people see, in a person's voice. Examples: "I made a puzzle game where a frog
  hops on pebbles that sink — level 10 took my friends 9 tries", "Six months of evenings on this
  little puzzle game. Is level 10 too mean?"
- **Body or first comment**: who you are (solo dev, day job?), what the game is, what stage it's
  at, and the specific feedback you want. The link goes in the comment when the sub asks.
- **Timing**: one sub at a time, hours or days apart, at a US morning (13:00–16:00 UTC is
  20:00–23:00 ICT). Reply to every comment in the first hour.

### LinkedIn
- **Hook**: 2–3 short lines that make people press "…see more". Lead with a tension or a lesson:
  "Our hardest level is the one we almost deleted."
- **Body**: the story (what you tried), the turn (what broke or surprised you), the lesson. Keep
  paragraphs short. Add one confirmed number if you have it.
- **CTA**: an open question, e.g. "How do you decide a level is too hard?"
- **Links and hashtags**: the link goes in the first comment. Use at most 3 hashtags matched to
  the angle.
- **Video**: 4:5.
- **Timing**: Tuesday–Thursday, 08:00–10:00 in the audience's timezone.

### X
- **Format**: one punchline. A meme format or a visual joke works. Keep the clip's best second first.
- **Hashtags**: 1–2 inline. Put the link in the first reply.
- **Threads**: 2–4 posts for behind-the-scenes material, e.g. how the solver works or why a level got cut.
- **Alt text**: describe what the clip shows.
- **Communities**: X shut them down in 2026. Leave `community` null.
- **Timing**: weekdays at the audience's morning or lunch.

## 8. Using the brief

The brief is a source of ideas, not a script. Take its main emotion and its best second (the
timestamp), then go wider:
- everyday situations every player knows;
- POVs;
- comparisons with famous games;
- the dev's own fails;
- calendar bridges.

The clip and the post need to feel like the same moment. They don't need to describe the same thing.

## 9. Hard facts

Hard facts are:
- features;
- numbers: downloads, ratings, how many players clear a level, how many levels;
- awards;
- prices, discounts and giveaways;
- dev-story facts: how long it took, team size.

Each one must come from the project or be confirmed by the developer in `config.yaml → facts`.
Each one also needs a `claims` entry in posts.json. If you want a number as a hook ("only 12 % clear level
10"), ask for the real number (analytics) first. Hyperbole that is clearly a joke ("khó hơn đề
thi") is not a hard fact.

## 10. Learning from results

When `social/performance_log.md` has rows, read it before writing (Step 6). Rank angles, hook
types and hashtags by engagement rate per platform ((likes + comments + shares) / views). Lean
on what worked for this game, and drop what flopped twice. Say in review_report.md what you
reused and why.
