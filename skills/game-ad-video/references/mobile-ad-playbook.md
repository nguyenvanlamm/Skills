# Mobile game video playbook: what studios, editors, stores and networks do

This file collects what specialist game-video studios and trailer editors do, and what the
stores and ad networks ask for. Where they agree, the skill follows them, and the skill feature
that carries each rule is named. Every rule cites its source (list at the end).

Pages were read on 2026-10-21. Fiverr and Upwork block direct reads, so those figures come from
search snapshots. Figures marked *vendor* come from a single tool vendor's own data; treat them
as hints, not benchmarks.

## 1. The brief comes first

| Ask for | Why | Source |
|---|---|---|
| Store link and the channels (Meta, TikTok, Google, AppLovin, Unity, App Store, Google Play, YouTube) | Channels decide ratios, lengths, file caps and text rules | Creatune, Sunstrike, Derek Lieu (location) |
| **Core message**: one sentence on what the viewer should feel or know after watching | Everything else serves it | Derek Lieu |
| **2–3 key pillars**, no more ("more dilutes their impact") | The trailer's sections | Derek Lieu |
| The player fantasy, and the mood and tone | The music and the pacing | Derek Lieu |
| Audience, defined by the games they already play | References and hook angles | Derek Lieu |
| **Don'ts**: spoilers, levels or features kept out of marketing | Takes to skip | Derek Lieu |
| 2–3 reference or competitor ads | Studios research competitors and pitch before editing | Quadral (client reviews), Sunstrike, vinhle3230 |
| End slate: CTA, platforms, date, rating | The end card | Derek Lieu |
| A clean capture: no tutorial pop-ups, debug access to stage moments | "A clean, tutorial-free capture is fastest"; debug access engineers the "wow" moments | Creatune, Kwalee (via search) |

Write the brief into `ad.json → brief` (free text). The direction boards answer it.

## 2. One video, one promise, shown fast

- "No feature list, one idea." The first 3 s show the idea, the middle proves it, and the end
  card names the game and says "play free". (Creatune)
- Hook angles come in three kinds, **promise**, **number** and **conflict**, which Creatune
  tests on the same game. Use them as the three directions, or as hook variants:

| Angle | Shape | Example caption (only if true) |
|---|---|---|
| Promise | What the player gets or becomes | "Fill *every* lamp." |
| Number | A concrete, true count or score | "*×3* in one shot" |
| Conflict | A dare, a fail, a near-miss | "Only one beam. *Can you?*" |

- Make the ad understandable "in like 3 seconds or less". "The more complex you are, the harder
  it is to get people to click." Watch it on a phone and ask whether it would stop your own
  scroll. (Voodoo's Jamora Crawford)
- Introduce the core message within the first 3 s and the hook within the first 6. (TikTok)

## 3. The first seconds

- "The first 3 seconds are critical." "Do not waste the first seconds on a logo or title card."
  "Get to gameplay immediately." Lead with the most exciting gameplay moment. (Meta)
- Successful app video ads have "2+ cut changes within the first 5 seconds". Grab attention
  within the first 2–3 s. (Google, via Replai)
- Brand early: Meta suggests within 3 s, and Google ABCD says "brand early, often". This doesn't
  contradict "no logo card", because a small corner bug names the game without spending the hook.
- Starting with non-gameplay footage "is always risky", especially on Steam. (Derek Lieu)

**In the skill:**
- `check` fails a UA cut that opens on a card or shows a card before 3 s.
- `storyboard` counts the cuts in the first 5 s.
- `brand_bug` puts the icon and name in a corner until the end card.

## 4. Real gameplay, real style

- "Show real gameplay, not pre-rendered cinematics." The ad must match the game's art style,
  mechanics and pace. (Meta)
- Use actual gameplay in all creatives. (ironSource, via Replai)
- Gameplay beats CGI because it feels authentic. Hard misleads are a poor choice: users leave
  once they see the real game. (Game Developer, hyper-casual review)
- Fail ads raise CTR but bring a noticeably higher 48-hour uninstall rate. (*vendor*, via
  search)
- The market sells "fake gameplay" ads (vinhle3230, Fiverr listings). This skill does not make
  them (rule 1).
- Dark visuals: colours that are "too dark" are a named reason ads fail. (Voodoo) For a unique
  mechanic, show the real gameplay with no effects or colour correction. (Game Developer)

**In the skill:** `look` (saturation, contrast, brightness) lifts a dark game a little for UA.
Store videos keep the true colours unless the storyboard grades them on purpose.

## 5. Show the touch

- Apple allows it even in App Previews: "If you need to demonstrate how interaction or
  navigation works within your app, you may add graphic elements, such as touch hotspots." Apple
  and Google Play both forbid filmed fingers or people holding the device.
- Interactive cues such as "crosshairs or a hand doing a 'come hither' motion" outperform more
  elaborate work. (Game Developer)
- For puzzle games, add a tutorial hand together with fail scenarios. (CrazyLabs, via search)

**In the skill:**
- `recorder.py` logs every tap and swipe of a take.
- `touches: true` draws them where and when they happened: a ripple ring, a fingertip dot that
  follows a drag, or a drawn hand (`touch_style: "hand"`).
- The indicators sit on the footage before the push-in, so they zoom with the screen.
- Store profiles always use the ring.

## 6. Sound off, text that reads

- "Most users browse with sound muted"; "design for sound-off viewing"; "large, legible text".
  (Meta)
- App previews autoplay muted. Text must be legible and "remain on the screen long enough for
  people to read". (Apple)
- Google Play also autoplays muted and asks for on-screen copy and captions. (Google Play)
- TikTok: captions or text overlays give context. "5–10 words per second" is its pacing figure
  for on-screen text. Sound is "critical": music, voice-over, a creator talking. (TikTok)
- At least half of users play with sound; odd sounds (chewing in Chain Cube) helped. (Game
  Developer) So design for muted viewing, and still mix the sound to be worth hearing.

**In the skill:**
- `storyboard` warns when a UA cut has no caption in its first 3 s.
- It also warns when a caption is on screen shorter than about 1 s per 15 characters.

## 7. Motion and finish

- Use "transitions, stickers, and graphics to hold attention and view time". Keep a native,
  not overly polished feel. (TikTok)
- Polish (better editing, a plot, silly text) wins in about 95 % of hyper-casual cases. (Game
  Developer)
- Motion graphics: gameplay callouts, UI overlays, typography, logo reveals. (Sunstrike)
- End cards: "all video ads must also include an end card". (Unity) Interactive end cards beat
  static ones where a network supports them. (ironSource; Trailmix case, via search)

**In the skill:**
- Captions pop, slide or appear word by word (`anim`), or sit on an accent sticker
  (`style: "sticker"`).
- Cards rise in.
- The end card animates: the icon pops, the lines rise, then the CTA pulses.
- `zoom.punch` gives quick bumps on hits and beats.
- The skill makes videos, not playables. For a playable or interactive end card, hand the best
  take to the network's tool.

## 8. Formats that work

| Format | How | Source |
|---|---|---|
| **Fail → solve** | The "player" fails at the last second, and the correct solution is clear from the start. Too hard, no hint, or too stupid, and viewers won't try. Expect 1–2 in 10 to work | Game Developer |
| **Noob vs pro / Level 1 vs Level N** | Side by side or one after the other. Suits constructive games with a static camera; weaker for fast shooters | Game Developer |
| **Direct challenge / unresolved ending** | End on the open question; the end card asks "Can you?" | Segwise (*vendor*: 84 % of one month's top ads) |
| **Satisfying** | One strong visual mechanic or colour scheme, nothing else | Voodoo |
| **Progression** | Escalate: show the basic mechanic, then add layers one at a time | Derek Lieu |

**In the skill:** `layout: "grid"` with 2 takes works in 9:16 too, side by side, with `labels`
and a `vs` badge. Directions are listed in `ad-structure.md`.

## 9. Lengths, ratios, files

| Placement | Ratio | Length | File | Source |
|---|---|---|---|---|
| Meta feed | 1:1, 4:5 | 15–30 s; "15-second videos consistently outperform 30-second" | ≥ 1080p, < 30 MB | Meta |
| Meta Stories / Reels | 9:16 | 15–30 s | — | Meta |
| TikTok | 9:16, ≥ 720p | 21–34 s | — | Replai, TikTok |
| Google App Campaigns | all ratios; ≥ 20 assets per campaign | — | — | Google, via Replai |
| Snapchat | 9:16 | ~6 s | — | Replai |
| ironSource | vertical and horizontal | 25–30 s | — | Replai |
| Unity Ads | 9:16 **and** 16:9 ("yields better optimization") | ≤ 60 s | H.264 MP4, 10 MB recommended, 100 MB max | Unity |
| App Store preview | per device (886×1920 for 6.9"/6.5") | 15–30 s; up to 3 per language | — | Apple |
| Google Play preview | portrait or landscape as the game plays, no black side bars | only the first 30 s autoplay | YouTube link, ads off, not age-restricted | Google Play |
| Steam / YouTube / press | 16:9, calmer, longer shots | 30–90 s | — | Creatune, `trailer-structure.md` |

- One hyper-casual studio found 30 s cuts perform best and makes 10–12, 15, 30 and 40–45 s
  cuts. (Game Developer)
- Meta favours 15 s.
- So ship two lengths.

**In the skill:**
- Profiles: `ua` (9:16), `ua-1x1`, `ua-4x5` and `ua-16x9` (6–60 s, ≤ 30 MB), `app-preview`,
  `play-promo`, `trailer` and `trailer-9x16`.
- `storyboard` prints which networks a UA cut's length suits.

## 10. Store video rules

**Apple App Store:**
- Only content from the app; "more gameplay than cutscenes".
- No prices.
- No seasonal or dated references.
- Plain transitions, "like dissolves and fades".
- Disclose IAP-only features, subscriptions or login if you show them; the disclaimer can go in
  the footage or the end frame.
- Pick a poster frame from the video.
- Each of up to 3 previews should show something new.

**Google Play:**
- At least 80 % of the video represents the real experience.
- Show the real game within the first 10 s.
- Limit title screens and logos.
- No CTA phrases and no ranking words ("Best", "#1").
- Localise it.
- The feature graphic is the video's cover.

**Data on store videos:** best performers are usually ≤ 20 s, and a 15 s preview won +16.9 %.
Repeating the screenshot captions in the video cost about 5 %. (SplitMetrics × Apptamin, 2018)

**In the skill:**
- `render` refuses, and `check` fails, selling words in `app-preview`, and CTA or ranking words
  in `play-promo`.
- Dated words and non-plain transitions get warnings.
- `check` saves a poster frame (`poster_at`).
- `play-promo` drops the end card's CTA.

## 11. Variations and refresh

- Studios ship a matrix: Creatune made 6 videos for one game (3 themes × 2 lengths).
- TikTok: 3–5 creatives per ad group, meaningfully different.
- Unity: A/B test at least 4 big concepts before refining.
- Google: 20+ assets per campaign.
- Meta: at least 50 optimisation events per variation, 3–5 days per test.
- Creatives burn out. A new one holding spend about two weeks is good (Game Developer).
  AppLovin suggests refreshing every 2–3 weeks.
- Iterate on a winner with outside changes (sound, intro, mirroring) or inside ones (a swapped
  item). (Game Developer)
- On-screen text set in code makes localisation safe. (Creatune)

**In the skill:** `ad.json → variants` (hook × length × language), `render --variant a,b`.

## 12. Music and the edit

- Plan the music first and fit the scenes to it. (Game trailer guides, via search) Cuts land on
  the beat. (Creatune)
- The **music stop** is "the most useful trick a trailer editor can ever learn": cut the music
  at a natural beat, often a downbeat, then come back with the hit. A hit followed by silence:
  "the silence is the effect". (Trailer-editing articles, via search)
- Fade every audio clip a little so nothing pops. Keep game audio clips crossfaded. Sync by
  feel, a frame or two off the waveform if it looks better. (Derek Lieu, editing tidbits)
- Use a single score through an App Preview; game SFX are fine. (Apple)

**In the skill:**
- `beats`, and `beats` timing on items.
- `music.stops` (`{"before": shot, "beats": 1}`).
- `music.end`: `fade`, `stop` (the music cuts when the end card lands), or `outro` (the track's
  own ending spliced in on a bar line so it ends with the video).

## 13. Trailers

These come from Derek Lieu, an editor whose trailers include Firewatch and Subnautica.
- Trailers are "video tutorials, in a way". List the game's verbs, show the principal unique
  feature as soon as possible, then expand on it. (PC Gamer interview, via search)
- Show the basic mechanic, then gradually add layers of complexity. Give a new mechanic enough
  time to be understood. The Sheepherds makeover opens on 10 s of the core loop.
- Show challenge: if every shot is perfect, the game looks easy.
- Title cards: test them on people outside the team. Personality beats generic copy ("A fluffy
  cheeky co-op game!" over "A Cozy Co-op Party Game!").
- Connect words to visuals as often as possible.

See `trailer-structure.md`.

## 14. Process and scope, for reference

| | Creatune | Sunstrike | Fiverr / Upwork market |
|---|---|---|---|
| Steps | store link → capture → edit + sound → delivery | discovery → script/storyboard/animatic → capture → edit/motion → sound → QA/exports | pitch → edit → revisions |
| Revisions | 2 rounds + a new hook if needed | — | 2–4 rounds; big changes cost extra |
| Time | 7–10 days | — | 2 days – 4 weeks |
| Price | — | $500–$5,000+ per ad | ~$20–$3,000; Quadral 30 s trailer $800–1,000 |

The skill's gates map onto this:

- the three direction boards are the pitch;
- `ad.json` is the storyboard;
- `check` is the QA;
- a revision is an `ad.json` edit and a re-render.

## Sources

Studios and editors:
- Creatune — game trailer service: https://www.creatuneagency.com/en/game-trailer/
- Sunstrike Studios — gaming ads: https://sunstrikestudios.com/en/services/Gaming-Ads-Video-Game-Advertising/
- vinhle3230 (Freelancer): https://www.freelancer.com/u/vinhle3230
- Anna K (Fiverr, via search): https://www.fiverr.com/anya_ring
- Louis R. / Quadral (Fiverr, via search): https://fiverr.com/adrn1216/30-seconds-mobile-game-trailer
- Upwork gameplay trailers (via search): https://www.upwork.com/services/game-trailers/get/gameplay
- Fiverr mobile game ad listings (via search): https://www.fiverr.com/search/gigs?query=mobile%20game%20ads
- Derek Lieu — creative brief: https://www.derek-lieu.com/blog/2024/9/2/how-to-make-a-creative-brief-for-a-game-trailer
- Derek Lieu — editing tidbits: https://www.derek-lieu.com/blog/2024/5/5/professional-video-editing-tidbits
- Derek Lieu — Sheepherds makeover: https://www.derek-lieu.com/blog/2026/8/4/game-trailer-makeover-sheepherds
- Derek Lieu — Carto launch trailer review: https://www.derek-lieu.com/blog/2026/1/3/carto-launch-trailer-review
- PC Gamer — the art of making effective game trailers (via search): https://www.pcgamer.com/the-art-of-making-effective-game-trailers
- Kwalee — how to make a great game trailer (via search): https://www.kwalee.com/blog/how-make-great-game-trailer

Stores and networks:
- Apple — App Previews: https://developer.apple.com/app-store/app-previews/
- Google Play — preview assets: https://support.google.com/googleplay/android-developer/answer/9866151
- Meta — click-to-play game ad creative: https://developers.facebook.com/documentation/games/acquire/click-to-play-ads/creative
- TikTok — creative best practices: https://ads.tiktok.com/resources/help/article/creative-best-practices
- Google — ABCDs of effective video ads: https://support.google.com/google-ads/answer/14783551
- Unity Ads — video specifications: https://docs.unity.com/en-us/user-acquisition/creatives/specifications/video
- Replai via Mobidictum — network best practices: https://mobidictum.com/best-practices-shared-by-ad-networks-on-creatives/

UA practice:
- Game Developer — mobile marketing creative review: https://www.gamedeveloper.com/game-platforms/big-mobile-marketing-creative-review-the-things-that-work
- Apptamin — Voodoo's Jamora Crawford: https://www.apptamin.com/blog/how-to-make-a-good-mobile-game-video-ad-with-jamora-crawford-voodoo-%e2%8e%ae-the-app-marketing-snack-12/
- Apptamin / SplitMetrics — app preview data (via search): https://www.splitmetrics.com/blog/create-app-preview-video-app-store-ios/
- Segwise — creative patterns (*vendor*, via search): https://segwise.ai/blog/mobile-ad-creative-trends
- CrazyLabs / Mobile Action — puzzle and fail creatives (via search): https://www.mobileaction.co/blog/top-3-ad-types-for-hyper-casual-games/
- Trailer music stops (via search): https://nofilmschool.com/how-to-edit-trailer-music
