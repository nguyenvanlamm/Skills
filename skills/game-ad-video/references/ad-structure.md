# Ad structure for casual / puzzle game videos

For a 16:9 trailer and its 9:16 cut-down, read `trailer-structure.md`. The camera, caption and
audio rules below still apply there.

This file is a summary. The camera and audio rules are condensed from huashu-design
(`references/storyboard-basics.md`, `camera-language.md`, `ui-demo-animation.md`,
`audio-design-rules.md`); read those when a shot needs more than what is here.

## Beats (15–30 s; make a 15 s and a 30 s cut)

| Beat | Time | Job | Footage |
|---|---|---|---|
| Hook | 0–3 s | Stop the thumb. A question, a dare, or an instantly satisfying motion | The most legible, most "I want to try that" moment. Never a logo, never a menu |
| Loop | 3–10 s | Show how to play in one look | 1–2 clips of the core action, readable at phone size |
| Payoff | 10–(end−3) s | The reward: combo, clear, win, level-up, near-miss saved | A push-in on the payoff, then hold it |
| End card | last 2.5–3 s | Name + icon + CTA (UA only) | Rendered from `end_card` |

**Energy budget** (storyboard-basics §4): plan the holds before the motion. After a payoff,
hold ≥0.5 s; the viewer needs time to register it. Cut on action, not on stillness.

## Directions (pick 3 that fit the game)

| Direction | Hook caption | Best for | Shape |
|---|---|---|---|
| **Satisfying / ASMR** | none, or one word | Games with juicy feedback (pops, merges, sorting) | Long uninterrupted clips, minimal text, game SFX loud. One strong visual element, nothing else (Voodoo) |
| **Challenge** | "Can you clear *all 35*?" / "Only 2% pass level 9" | Puzzles with a visible goal | Dare → attempt → near-miss → success. Or stop on the open question and let the end card ask "Can you?" (unresolved ending) |
| **Progression / Level 1 vs N** | "Level 1 vs *level 50*" | Games with visible growth (board, city, collection), static camera | `layout: "grid"` with 2 takes, `labels` and `vs`, in any ratio; then the late board on its own |
| **Fail → solve** | "Wait for it…" / "Don't do this" | Puzzles with a visible mistake | The attempt fails at the last second; the right move must be clear from the start, then show it solved. Too hard, no hint or too silly, and viewers won't try. It raises CTR but also early uninstalls, so keep it honest |
| **Noob vs pro** | "Noob vs *pro*" | Constructive games where skill shows on one board | Grid of 2 takes of the same level, one clumsy, one clean (both real takes) |
| **Relax / calm** | "Your 5-minute break" | Low-pressure games | Slow pacing, soft BGM (`bgm: educational`) |

Claims in captions must be true of the game ("Only 2% pass" needs a number from somewhere, or
use "Can you pass level 9?"). App Preview captions never sell: no price, "free", "download".

**One promise per video.** Studios test three hook angles for the same game: **promise** (what the
player gets), **number** (a true count or score) and **conflict** (a dare, a fail, a near-miss).
Either use one angle per direction board, or keep the chosen direction and ship the other two
angles as hook variants. Sources and specs: `mobile-ad-playbook.md`.

**The first 3 s are gameplay.** No logo, studio name or title card before 3 s: they go on the end
card. `check` fails a UA cut that opens on a card or shows one before 3 s. Most people watch
muted, so the hook should carry a caption unless the motion explains itself; `storyboard` warns
otherwise.

## Camera (from huashu-design)

- **Real UI plus restrained camera beats effects** (ui-demo-animation §0). Only use push-ins,
  holds and cuts. No spins, glitch transitions or fake particles.
- **Every push-in ends on a concrete anchor** (storyboard-basics, law 2): the combo counter, the
  cleared row, the last tile. `zoom.anchor` is that point as `[x, y]` fractions of the take frame.
  Name it in `anchor_label`.
- **Zoom ladder** (camera-language §4): 1.0 wide, 1.2–1.4 medium, 1.5–1.8 close, never above 2.0.
  The footage is only ~1075 px wide, so past 2× it goes soft. Push fast (0.4–0.8 s, smoothstep),
  then hold.
- **No same framing twice in a row**: alternate wide ↔ close. A run of 1× shots reads as one
  long clip.
- **One action per shot.** If you need two, it's two shots.
- **Transitions by relationship** (storyboard-basics §7):
  - `cut` for the same scene continuing (default, hidden).
  - `fade` (0.2–0.3 s) for a time jump.
  - `slideup` / `slideleft` for "next level / next board" (UA only: Apple asks for plain
    transitions, "like dissolves and fades", so give that shot `"transition_app_preview": "fade"`).
  - `fade` into the end card.

  Any ffmpeg `xfade` transition name works, but keep to these. Trailers add `fadeblack`
  (between acts) and `fadewhite` (0.1 s, into the title on the drop); see
  `trailer-structure.md`.
- **Punch** (`zoom.punch: [1.2, 2.0]`, seconds into the shot): an 8 % bump that settles back in
  ~0.15 s, on a hit, a clear or a beat. One or two per shot; a punch on every beat is noise. A
  punch works with or without a push (`{"punch": [1.2]}` alone keeps 1×).
- **Check frames**: 1–2 per shot, at the moment the shot must prove something (caption fully in,
  push-in landed, payoff visible).

## Captions

- ≤ 6 words per caption, at most one caption on screen. Mark the key word `*like this*`; it takes
  the accent colour.
- **Safe zones for UA (TikTok/Reels).** The bottom ~20% and the right ~12% are covered by app UI.
  Keep captions to `pos: top`, a number between 0.03 and 0.15, or `center`. Use `bottom` (22%
  from the bottom edge) only for short labels.
- **Don't cover the game's HUD or the action.** Look at the check frame. If the top is taken by
  the score, use `pos: 0.035` (above the HUD) or move the caption. `plate` (on by default) keeps
  text readable over busy footage.
- App Preview: fewer captions, no selling, no CTA. Text overlays are allowed.
- **Long enough to read.** A caption needs about 1 s per 15 characters, and at least 1 s (Apple:
  "long enough for people to read"). `storyboard` warns below that.
- **Motion** (`caption.anim`, or `caption_anim` for the whole storyboard):
  - `pop` (default) scales in with a small overshoot;
  - `slide` rises in;
  - `words` brings in one word after another, for a hook line or a 3-beat claim;
  - `fade` is the plain fade.

  The frames are drawn by Chrome from CSS, so what you see in the check frame is exact.
- **Style.** `plate` (default) puts dark rounded glass behind the text. `"plate": false` gives
  outlined text. `"style": "sticker"` sets dark text on an accent pill, tilted 2.5°, like a
  TikTok sticker; use it for one punchy word or number, not for every caption.

## Touch indicators

Show how to play the way the stores allow it. Apple permits "graphic elements, such as touch
hotspots", while Apple and Google Play both forbid filmed fingers. UA studios add a tutorial
hand or a cue because it makes the mechanic obvious.

- `recorder.py` logs every tap and swipe of a take in `NAME.marks.json → inputs` (`t`, `kind`,
  `at`, `to`, `ms`, as fractions of the screen; a swipe that doesn't move is a hold). On web the
  timing is exact. On Android it is estimated from adb, about ±0.1 s.
- `"touches": true` on a shot draws the inputs that fall inside it:
  - a ring that ripples out where a finger lands;
  - a fingertip dot that follows a drag or stays for a hold.

  The indicators sit on the raw take before the push-in, so they zoom with the screen.
- `"touch_style": "hand"`, per shot or for the whole storyboard, draws a pointing hand instead
  of the dot. UA only: store profiles always use the ring.
- Takes recorded before inputs were logged can list touches by hand:
  `"touches": [{"t": 4.2, "at": [0.45, 0.62]}, {"t": 5.0, "at": [0.3, 0.7], "to": [0.7, 0.7], "ms": 400}]`.
  `t` is take seconds; `at` and `to` are fractions of the take frame.
- Use them in the hook and the loop beat, where the mechanic is being taught. Drop them in the
  payoff, where they clutter the moment.

## Brand bug and look

- `"brand_bug": {"pos": "top-right"}` puts a small icon + name pill in a corner from the first
  frame until the end card lands. This names the game early (Meta: within 3 s; Google: "brand
  early, often") without spending the hook on a logo card.
  - `pos` is `top-left`, `top-right`, `bottom-left`, `bottom-right`, or `[x, y]` fractions.
  - Check it against the game's HUD and against TikTok's bottom 20 %.
  - `brand_bug_app_preview: null` keeps it off the store video.
- `"look": {"saturation": 1.12, "contrast": 1.06, "brightness": 0.03}` grades the footage a
  little. Dark games read badly in a feed (Voodoo: "too dark" is a named reason ads fail).
  - Store profiles keep the true colours unless the storyboard sets `look_app_preview` /
    `look_play_promo` itself.
  - Don't grade a game whose look is the selling point.

## Audio (two layers, from huashu-design audio-design-rules)

| Layer | Source | Treatment |
|---|---|---|
| Bed | `audio.bgm`: `ad` (huashu `bgm-ad.mp3`), another huashu mood (`tech`, `educational`, `tutorial`), or a path | lowpass 4 kHz, volume 0.45, fade in 0.3 s / out 1.5 s |
| Beats | `cues[]`: huashu `assets/sfx/<category>/<name>.mp3` or a path | highpass 800 Hz, `db` −16 (whoosh) … −10 (impact) |
| Game | the take's own audio (needs `serve --audio`) | `audio.game_volume`, untouched |

Everything goes through `amix normalize=0`, then `loudnorm` to −14 LUFS. Cue density: about one
per structural beat. That means a whoosh into the push-in, an `feedback/achievement` on the
payoff and an `impact/brand-stamp` on the end card. Don't add one per tap; the game's own sound
does that.

## Ratios and variants (UA)

| Profile | Size | For |
|---|---|---|
| `ua` | 1080×1920 | TikTok, Reels, Stories, Shorts, Google App Campaigns, AppLovin, Unity portrait |
| `ua-1x1` | 1080×1080 | Meta feed |
| `ua-4x5` | 1080×1350 | Meta / Instagram feed |
| `ua-16x9` | 1920×1080 | Unity and AppLovin landscape, Meta desktop feed |

- All allow 6–60 s and ≤ 30 MB. `storyboard` prints which networks the length suits: Meta 15–30,
  TikTok 21–34, ironSource 25–30, Snapchat ~6, Unity ≤ 60. Meta finds 15 s beats 30 s; a
  hyper-casual studio finds 30 s best. Make both.
- Shots without `profiles` go into every ratio, and `"ua"` in a `profiles` list means all four.
  `caption_ua` (and other `_ua` overrides) apply to all four unless a ratio has its own.
- Portrait takes in `ua-16x9` look small with `fit`. Give its shots `layout_ua_16x9: "panel"` or
  `"fill"` (see `trailer-structure.md` § Layouts). In 1:1 and 4:5, `panel` and a grid of 3 fall
  back to `fit`; a grid of 2 works everywhere.

**Variants** turn one storyboard into a test matrix (hook × length × language):

```jsonc
"variants": {
  "hook-number":   {"shots": {"0": {"caption": {"text": "*×3* in one shot", "pos": 0.03}}}},
  "hook-conflict": {"shots": {"0": {"take": "takes/take-07.mp4", "in": 4.0, "out": 6.6,
                                    "caption": {"text": "One beam. *Can you?*"}}}},
  "short":         {"shots": {"3": {"drop": true}}},           // the 15 s cut
  "vi":            {"shots": {"0": {"caption": {"text": "Tách *ba* chỉ một lần bắn"}}},
                    "end_card": {"cta": "Chơi ngay"}}
}
```

- Keys under `shots` are 0-based indices into `shots`. A patch merges into that shot, so you
  can replace its take, in, out, caption or zoom. `{"drop": true}` removes the shot from every
  profile, and cues pointing at it are skipped. `end_card`, `audio` and `music` merge as well.
- `--variant hook-number,short` applies the variants in order. The output is
  `ad-ua-9x16-hook-number-short.mp4`, and its check frames are
  `sheets/check-ua-hook-number-short-f….jpg`.
- Check each variant with the same `--variant`, so `check` uses that cut's timeline.
- Two or three hooks × two lengths is plenty. Meta wants at least 50 optimisation events per
  variation and 3–5 days per test.

## Store videos: App Store preview and Google Play

### App Store App Preview (`app-preview`)

- **Specs**:
  - 886×1920 portrait for the 6.9"/6.5" iPhone slots;
  - 15–30 s, ≤ 30 fps;
  - H.264 High, yuv420p;
  - stereo AAC 256 kbps, 48 kHz;
  - ≤ 500 MB.

  `check --profile app-preview` tests all of these.
- **Content**:
  - footage captured from the app itself;
  - no people or hands, no device frames;
  - no other platforms' UI;
  - no prices or "free" claims, since prices vary by region.

  Text overlays, touch hotspots (`touches`) and music are allowed.
- **More rules** (Apple):
  - show "more gameplay than cutscenes";
  - no seasonal or dated references (`storyboard` warns on years and seasons);
  - plain transitions, like dissolves and fades (warned);
  - one score throughout;
  - disclose IAP-only features, subscriptions or login if the footage shows them; put the
    disclaimer in a caption or the end frame;
  - up to 3 previews per language, each showing something new.
- **Poster frame.** It shows when autoplay is off, and it is picked from the video. `check`
  saves `sheets/poster-app-preview.jpg` at `poster_at` (seconds, default 0.5); set the same time
  in App Store Connect. Open the hook on a clean, legible frame.
- **No end card.** `render` drops it for this profile unless `end_card.profiles` names
  `app-preview` explicitly. Even then, keep it to name + icon with no CTA.

### Google Play preview video (`play-promo`)

- It's a YouTube link: public or unlisted, ads (monetisation) off, not age-restricted. Only the
  first 30 s autoplay, muted. The feature graphic is its cover image.
- Choose the orientation the game plays in, and leave no black bars beside a portrait video.
  `play-promo` is 1080×1920 for portrait games.
- At least 80 % of it should be the real experience, and the game should show within the first
  10 s. Limit title screens and logos.
- No CTA phrases and no ranking words ("Best", "#1"). `render` refuses them, and the end card
  drops its CTA. Captions fall back from `caption_play_promo` to `caption_app_preview` to
  `caption`.
- Localise it: the UI, the taglines and the audio (variants).

## ad.json

```jsonc
{
  "game": {
    "name": "Tile Pop",
    "icon": "../../assets/icon/icon.png",       // paths are relative to ad.json
    "font": "../../assets/fonts/Display.ttf",   // optional; captions and end card use it
    "colors": {"bg": "#1b1530", "bg2": "#3a2a6b", "fg": "#ffffff", "accent": "#ffcc33", "stroke": "#000000"}
  },
  "direction": "B · challenge",
  "shots": [{
    "take": "takes/take-03.mp4", "in": 3.0, "out": 5.6,   // seconds in the take
    "speed": 1.0,                                          // 0.5–2 reads natural; atempo follows
    "zoom": {"from": 1.0, "to": 1.5, "anchor": [0.5, 0.45], "anchor_label": "the clearing row",
             "at": 0.1, "dur": 0.6, "punch": [1.4]},       // push starts at 0.1 s; punch at 1.4 s
    "caption": {"text": "Combo *x20*", "pos": "bottom", "size": 0.074, "plate": true,
                "anim": "pop", "style": null},             // anim: pop|slide|words|fade · style: sticker
    "caption_app_preview": null,                           // override (or drop) for one profile
    "touches": true,                                       // draw the take's logged taps/swipes
    "touch_style": "ring",                                 // ring (default) | hand (UA only)
    "transition": "fade", "transition_s": 0.3,             // into this shot
    "profiles": ["ua", "app-preview"],                     // default: both
    "mute": false,                                         // drop this take's game audio
    "framing": "close 1.5x", "why": "push onto the combo", // storyboard columns, not rendered
    "action": "rows burst", "composition": "board 80%, caption bottom",
    "check_at": [1.5]                                      // seconds into the shot
  }],
  "end_card": {"seconds": 2.8, "headline": "Tile Pop", "subline": "One more board?", "cta": "Play free",
               "icon": null, "transition": "fade", "transition_s": 0.3, "check_at": [1.5],
               "anim": "rise"},                            // rise (icon pops, lines rise, CTA pulses) | none
  "brand_bug": {"pos": "top-right"},                       // icon + name until the end card
  "look": {"saturation": 1.1, "contrast": 1.05},           // a light grade for UA (not store videos)
  "poster_at": 0.5,                                        // App Store poster frame (check saves it)
  "audio": {"bgm": "ad", "bgm_volume": 0.45, "game_volume": 1.0},
  "cues": [
    {"shot": 1, "at": 0.1, "sfx": "transition/whoosh-fast.mp3", "db": -14},   // shot index in "shots"
    {"end_card": true, "at": 0.1, "sfx": "impact/brand-stamp.mp3", "db": -10},
    {"t": 7.5, "sfx": "feedback/achievement.mp3", "db": -12}                   // absolute time
  ]
}
```

A grid shot (2–3 takes side by side; 2 also in portrait) replaces `take`/`in`/`out` with:

```jsonc
{"layout": "grid", "seconds": 3.6,
 "takes": [{"take": "takes/l01.mp4", "in": 1.1}, {"take": "takes/l20.mp4", "in": 22.5}],
 "labels": ["Level 1", "Level *20*"], "vs": true,
 "caption": {"text": "Level 1 vs *Level 20*", "pos": 0.06, "anim": "slide"}}
```

Shot timing is computed:

- duration = `(out − in) / speed`;
- a transition overlaps the previous shot by `transition_s`;
- cues anchored to a shot or to the end card follow it in both profiles, while absolute `t` cues
  don't.
