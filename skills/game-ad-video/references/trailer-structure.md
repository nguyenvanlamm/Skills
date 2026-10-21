# Trailer structure: 16:9 gameplay trailer + 9:16 cut-down

The model is a showcase gameplay trailer such as *Constance – Official Gameplay Trailer*
(Guerrilla Collective 2024). It runs 1–2 minutes and is cut to the music. Full-frame cards name
what the footage shows, and it ends on logo, platforms and date.

We borrow its **editing**: pacing, act structure, cards, logo beats. We do not borrow its art.
Every gameplay frame is still a take from `recorder.py` (SKILL.md rule 1). For a casual or puzzle
game, 45–75 s is plenty: a trailer that outlasts the game's variety loses people.

## How editors think about it (Derek Lieu)

Derek Lieu's trailers include Firewatch, Shadow of Mordor and Subnautica.

- **A trailer is a tutorial, in a way.** List the game's verbs first (aim, bank, split…). Show
  the principal unique feature as soon as possible, then expand on it.
- **Layers, not a list.** "Show the basic mechanic and then gradually add on layers of
  complexity", giving each new mechanic "enough time to fully understand". The Sheepherds
  makeover opens on 10 s of the core loop. Cosmetics and modes can wait for the end.
- **Show challenge.** If every shot is a perfect run, the game "looks not at all challenging". A
  near-miss teases the audience.
- **Brief first.** Write a core message (one sentence), 2–3 pillars (no more), the player
  fantasy, the mood, the don'ts and the end slate. Write it into `trailer.json → brief`.
- **Title cards with personality,** tested on someone outside the team: "A fluffy cheeky co-op
  game!" over "A Cozy Co-op Party Game!". Tie words to visuals as often as you can.
- **Non-gameplay openings are risky,** especially on Steam. Get to gameplay within seconds.

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

**Edit the music, not just the picture.**

- **The music stop.** Silence the music for a beat right before the title lands on the drop:
  `"stops": [{"before": <index of the title card>, "beats": 1}]` in `music`. Trailer editors
  call the music stop the most useful trick they know. Game sound and SFX keep playing; put
  `impact/logo-reveal.mp3` on the title so the hit comes out of the silence.
- **End on the track's own ending.** `beats` prints `outro_at`, a downbeat a few bars before the
  track's sound ends. Then:
  - `"end": "outro", "outro_at": …` jumps there on a bar line, so the track's last hit and tail
    land as the video ends;
  - `"end": "stop"` cuts the music dead when the end card lands, and the brand-stamp hit sits in
    the silence;
  - `"end": "fade"` (the default) fades the music out over 2 s.

## 9:16 cut-down (30–60 s)

Same `trailer.json` and the same shot list, filtered by `profiles`.

- **Hook first, no cold open.** Give the cut-down its own first shot
  (`"profiles": ["trailer-9x16"]`) and mark the cold-open shots `"profiles": ["trailer"]`.
- **Start the music at the drop.** Set `music_trailer_9x16` with a later `start`, and
  `"fade_in_trailer_9x16": 0`. The feed punishes a slow open.
- **Layouts fall back on their own.** `panel` and a grid of 3 become `fit` in portrait, because
  a portrait take already fills the frame; a grid of 2 stays side by side. A panel's caption
  becomes an overlay caption. Use `caption_trailer_9x16` / `layout_trailer_9x16` /
  `zoom_trailer_9x16` to tune one shot for the vertical cut, and check fallback captions against
  the game's HUD.
- **End the cut-down cleanly.** `music_trailer_9x16` with `"end": "stop"` cuts the music when the
  end card lands.

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

- `anim`:
  - `rise` (default): the line rises in, `sub` after it, the icon or logo pops;
  - `pop`: for a title on a hit;
  - `words`: word by word, for a three-word line on three beats;
  - `settle`: the still card.

  Every card also settles from 1.06× to 1×.
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
| `grid` | Puts 2–3 takes side by side (`takes: [{take, in}, …]`); a caption overlays as usual. `labels` go above the panels, and `vs: true` puts a badge between two | Variety, before/after, "Level 1 vs Level 20" |

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

## Thumbnail

YouTube shows the thumbnail before anyone presses play, so make one per trailer:

```bash
build_ad.py thumb --ad trailer.json --take takes/l20-a.mp4 --at 17.6 \
  --text "One beam. *Every lamp.*" --sub "A light-splitting puzzle" --out thumb.png
```

- The default size is 1280×720: the frame blurred behind, the frame on a tilted card, big text
  with the icon and name.
- `--size 1080x1920` gives a vertical cover with the text above the card.
- One promise, ≤ 5 words, true to the game. Test two thumbnails the way you test two hooks.

## Output specs

| Profile | Size | Length | Where |
|---|---|---|---|
| `trailer` | 1920×1080, 30 fps, H.264 High yuv420p, AAC 320k | 45–120 s | YouTube, Steam, landing page, press kit |
| `trailer-9x16` | 1080×1920, same codecs | 30–60 s | Shorts, Reels, TikTok |

The App Store takes App Previews (`app-preview`, 15–30 s), not trailers. Don't upload a trailer
as a preview.
