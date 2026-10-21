# Ad structure for casual / puzzle game videos

For a 16:9 trailer and its 9:16 cut-down, read `trailer-structure.md`. The camera, caption and
audio rules below still apply there.

This file is a summary. The camera and audio rules are condensed from huashu-design
(`references/storyboard-basics.md`, `camera-language.md`, `ui-demo-animation.md`,
`audio-design-rules.md`); read those when a shot needs more than what is here.

## Beats (15–30 s)

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
| **Satisfying / ASMR** | none, or one word | Games with juicy feedback (pops, merges, sorting) | Long uninterrupted clips, minimal text, game SFX loud |
| **Challenge** | "Can you clear *all 35*?" / "Only 2% pass level 9" | Puzzles with a visible goal | Dare → attempt → near-miss → success |
| **Progression** | "Level 1 vs level 50" | Games with visible growth (board, city, collection) | Before/after, speed-ramped middle |
| **Fail-bait** | "Wait for it…" | Games with a dramatic fail state | A near-miss or a fail at the end of the hook, then the right move |
| **Relax / calm** | "Your 5-minute break" | Low-pressure games | Slow pacing, soft BGM (`bgm: educational`) |

Claims in captions must be true of the game ("Only 2% pass" needs a number from somewhere, or
use "Can you pass level 9?"). App Preview captions never sell: no price, "free", "download".

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
  - `slideup` / `slideleft` for "next level / next board".
  - `fade` into the end card.

  Any ffmpeg `xfade` transition name works, but keep to these. Trailers add `fadeblack`
  (between acts) and `fadewhite` (0.1 s, into the title on the drop); see
  `trailer-structure.md`.
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

## App Store App Preview rules

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

  Text overlays and music are allowed. The first frames are the poster frame, so the hook shot
  should open on a clean, legible frame.
- **No end card.** `render` drops it for this profile unless `end_card.profiles` names
  `app-preview` explicitly. Even then, keep it to name + icon with no CTA.

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
             "at": 0.1, "dur": 0.6},                       // push starts at 0.1 s into the shot
    "caption": {"text": "Combo *x20*", "pos": "bottom", "size": 0.074, "plate": true},
    "caption_app_preview": null,                           // override (or drop) for one profile
    "transition": "fade", "transition_s": 0.3,             // into this shot
    "profiles": ["ua", "app-preview"],                     // default: both
    "mute": false,                                         // drop this take's game audio
    "framing": "close 1.5x", "why": "push onto the combo", // storyboard columns, not rendered
    "action": "rows burst", "composition": "board 80%, caption bottom",
    "check_at": [1.5]                                      // seconds into the shot
  }],
  "end_card": {"seconds": 2.8, "headline": "Tile Pop", "subline": "One more board?", "cta": "Play free",
               "icon": null, "transition": "fade", "transition_s": 0.3, "check_at": [1.5]},
  "audio": {"bgm": "ad", "bgm_volume": 0.45, "game_volume": 1.0},
  "cues": [
    {"shot": 1, "at": 0.1, "sfx": "transition/whoosh-fast.mp3", "db": -14},   // shot index in "shots"
    {"end_card": true, "at": 0.1, "sfx": "impact/brand-stamp.mp3", "db": -10},
    {"t": 7.5, "sfx": "feedback/achievement.mp3", "db": -12}                   // absolute time
  ]
}
```

Shot timing is computed:

- duration = `(out − in) / speed`;
- a transition overlaps the previous shot by `transition_s`;
- cues anchored to a shot or to the end card follow it in both profiles, while absolute `t` cues
  don't.
