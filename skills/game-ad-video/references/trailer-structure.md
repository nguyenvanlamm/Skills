# Trailer structure: 16:9 gameplay trailer + 9:16 cut-down

The model is a showcase gameplay trailer such as *Constance – Official Gameplay Trailer*
(Guerrilla Collective 2024). It runs 1–2 minutes and is cut to the music. Full-frame cards name
what the footage shows, and it ends on logo, platforms and date.

We borrow its **editing**: pacing, act structure, cards, logo beats. We do not borrow its art.
Every gameplay frame is still a take from `recorder.py` (SKILL.md rule 1). For a casual or puzzle
game, 45–75 s is plenty: a trailer that outlasts the game's variety loses people.

## Acts (16:9, 45–90 s)

| Act | Time | Job | Cut rate | Material |
|---|---|---|---|---|
| Cold open | 0–8 s | Mood. One clear image of the game, music still low | 8 beats a shot | `fit`, a slow push (1.0→1.15 over 3–4 s); maybe one `title` card ("One *beam*.") |
| Title | on the first hit / drop | The name lands with the music | 4 beats | `logo` card, `fadewhite` 0.1 s into it, cue `impact/logo-reveal.mp3` |
| Mechanics | ~10–35 s | How to play, one verb at a time, three verbs (a triad) | 8 beats a verb | `panel` shots: the take on one side, the verb big on the other; alternate `side` |
| Escalation | ~35–60 s | Variety and speed: more rooms, harder boards | 4 → 2 → 1 beat | `grid` (2–3 rooms at once), then `fill` and `fit` cuts on every beat or two |
| Payoff | before the end | The best moment, held | 12–16 beats | `fit` with a push onto the payoff; `fadeblack` + a `feature` card before it marks the act break |
| End card | last 3–5 s | Logo, line, date, platforms, CTA | 6–8 beats | `end_card` with `date` / `platforms` |

Budget the music first. Run `build_ad.py beats MUSIC --drop-at 9.5 --length 60` and choose
`music.start` so that the drop lands on the title card. If the drop leaves too little track for
the trailer, the script picks another rise. Lay out the acts in beats, then fill each act with
shots.

## 9:16 cut-down (30–60 s)

Same `trailer.json` and the same shot list, filtered by `profiles`.

- **Hook first, no cold open.** Give the cut-down its own first shot
  (`"profiles": ["trailer-9x16"]`) and mark the cold-open shots `"profiles": ["trailer"]`.
- **Start the music at the drop.** Set `music_trailer_9x16` with a later `start`, and
  `"fade_in_trailer_9x16": 0`. The feed punishes a slow open.
- **Layouts fall back on their own.** `panel` and `grid` become `fit` in portrait, because a
  portrait take already fills the frame. A panel's caption becomes an overlay caption. Use
  `caption_trailer_9x16` / `layout_trailer_9x16` / `zoom_trailer_9x16` to tune one shot for the
  vertical cut.

## Directions (three-direction gate, SKILL.md rule 2)

| Direction | Opening | Shape | Best for |
|---|---|---|---|
| **Cinematic mood** | Slow, quiet, one image held | Cold open → title on the drop → triad → montage → payoff | Games with atmosphere (light, music, art); closest to Constance |
| **Feature triad** | Title in the first 3 s | Three verb cards, each followed by 2–3 shots, then montage | Games with three clear mechanics |
| **Escalation montage** | Easiest room | Level 1 → level N, cuts getting faster every 8 bars, hold the hardest | Games with visible growth or difficulty |
| **Level 1 vs Level N** | Split before/after (`grid` of 2) | Before/after pairs, then the payoff | Puzzles whose late boards look nothing like the first |

Render each board with `build_ad.py board --wide …` from a real frame.

## Editing rules

- **Cut on the beat.** Give items `beats` rather than `out` / `seconds`, so each one ends on the
  grid. `storyboard` shows where each cut lands (`bar:beat`). `check` fails a hard cut more than
  a frame off the beat. Use `music.sync: false` only for a deliberately free edit.
- **Transitions:**
  - `cut` inside an act;
  - `fadeblack` (0.3 s) between acts;
  - `fadewhite` (0.1 s) into the title on the drop;
  - `fade` (0.3 s) into the end card.

  A fade lands when it completes: the incoming shot is fully on screen on the beat.
- **Camera:** the ad rules apply (`ad-structure.md` § Camera). Pushes end on a named anchor, the
  zoom ladder tops out at 2×, and framing changes from one shot to the next. Only the cold open
  may push slowly.
- **Holds:**
  - the payoff gets 12–16 beats;
  - the logo gets 4 beats;
  - the end card gets 6–8 beats.

  A trailer that never holds reads as noise.

## Cards

| `style` | Use | Size |
|---|---|---|
| `title` | Cold-open line, 1–3 words | 0.12 of the short side |
| `feature` | A verb or a promise, ≤ 4 words ("Light every *lamp*.") | 0.09 |
| `logo` | `game.logo` (a wordmark PNG) if set, else icon + name in the game's font | — |

- `sub` adds a smaller line under the card or panel text.
- `bg_take` + `bg_at` put a blurred, darkened still from a take behind the card. Without them
  the card uses the game's gradient.
- Claims must be true of the game. "Three chapters" needs three chapters in the build; "100+
  levels" needs 100 levels.

## Portrait footage in a 16:9 frame (`layout`)

| Layout | What it does | Use |
|---|---|---|
| `fit` | Scales the take into the frame over a blurred copy of itself | Landscape takes; cold open; payoff with a push |
| `fill` | Cuts a frame-shaped band out of the take around `fill_y` (0 top … 1 bottom) and scales it up | Fast montage cuts. A 974-px-wide take goes up ~2× in 16:9: fine for 1–4 beats, soft if held. `storyboard` warns past 2× |
| `panel` | Puts the take on a rounded card at ~88 % height on one `side`, with the caption as big text on the other half | The mechanics triad |
| `grid` | Puts 2–3 takes side by side (`takes: [{take, in}, …]`); a caption overlays as usual | Variety, before/after |

If the game lays out in landscape on the web, record native 16:9 takes instead:
`recorder.py serve --url … --width 960 --height 540 --dpr 2` gives 1920×1080, and `fit` fills
the frame.

## Audio

- **Music.** The music leads. Trailer profiles play the BGM full-range (no 4 kHz low-pass) at
  0.9, trimmed from `music.start`, with a 2 s fade-out. Game sound sits under it
  (`audio.game_volume` 0.6–0.8).
- **Cues.** One per structural beat:
  - `impact/logo-reveal.mp3` on the title;
  - `transition/whoosh.mp3` into the triad;
  - `feedback/achievement.mp3` on the payoff;
  - `impact/brand-stamp.mp3` on the end card.
- **Loudness.** The mix is loudnormed to −14 LUFS, as YouTube expects.

## Output specs

| Profile | Size | Length | Where |
|---|---|---|---|
| `trailer` | 1920×1080, 30 fps, H.264 High yuv420p, AAC 320k | 45–120 s | YouTube, Steam, landing page, press kit |
| `trailer-9x16` | 1080×1920, same codecs | 30–60 s | Shorts, Reels, TikTok |

The App Store takes App Previews (`app-preview`, 15–30 s), not trailers. Don't upload a trailer
as a preview.
