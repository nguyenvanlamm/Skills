# Changelog

## v1.4.0 — 2026-10-21

A second research round: trailer editors (Derek Lieu), Apple's and Google Play's video rules,
TikTok, Google ABCD, the networks' published practices (via Replai), a hyper-casual creative
review (Game Developer) and Voodoo. All of it is folded into `references/mobile-ad-playbook.md`.
What the sources agreed on is now a feature.

### Added
- **Touch indicators.**
  - `recorder.py` logs every tap and swipe of a take (`marks.json → inputs`, fractions of the
    screen, real drag durations).
  - `"touches": true` draws them where and when they happened: a ripple ring, a fingertip dot
    that follows a drag or holds, or a drawn hand (`touch_style: "hand"`, UA only).
  - They sit on the raw take, so a push-in zooms them with the screen.
  - Older takes can list touches by hand.
  - Apple allows "touch hotspots" in App Previews; gesture cues outperform in UA.
  - Verified against a test page that marks every touch: the ring lands on the mark, the dot
    on the drag's head.
- **Animated text, drawn frame by frame by Chrome from CSS.**
  - Captions: `anim` `pop` (default) / `slide` / `words` / `fade`, and `style: "sticker"`.
  - Cards: `anim` `rise` (default) / `pop` / `words` / `settle`.
  - End card: the icon pops, the lines rise one after another, then the CTA pulses
    (`anim: "none"` for the still card).
- **Level 1 vs N / noob vs pro.** A grid of 2 takes now works in portrait and square frames too,
  with `labels` above the panels and a `vs` badge between them.
- **Brand bug.** `brand_bug` puts the icon + name in a corner until the end card, so the game is
  named early (Meta, Google ABCD) without a logo card in the hook.
- **Music edits for trailers.**
  - `music.stops` (`{"before": shot, "beats": 1}`) silences the music for the beat before a
    title.
  - `music.end` is `fade` (default), `stop` (the music cuts when the end card lands) or `outro`
    (the track's own ending spliced in on a bar line, so its last hit and tail land as the video
    ends).
  - `beats.py` reports where the track's sound really ends and suggests `outro_at`.
- **`play-promo` profile** for the Google Play preview video (1080×1920, 15–30 s). It refuses
  CTA and ranking words ("best", "#1"), drops the end card's CTA, and uses `caption_play_promo`,
  then `caption_app_preview`.
- **Store text rules** in `render` and `check`: selling words for the App Store, CTA and ranking
  words for Google Play. Dated words (years, seasons) and non-plain App Preview transitions get
  warnings. `check` saves the poster frame at `poster_at`.
- **Storyboard guidance:**
  - a `pacing` line (cuts in the first 5 s; which networks the length suits: Meta, TikTok,
    ironSource, Snapchat, Unity);
  - captions too short to read (~15 characters a second);
  - touches with no logged inputs;
  - the brand bug crowding top captions.
- `zoom.punch`: quick 8 % bumps that settle back, on hits and beats.
- `look`: a light grade (saturation, contrast, brightness) for UA; store videos keep their true
  colours.
- `build_ad.py thumb`: a YouTube (1280×720) or vertical thumbnail from a take frame, big text and
  the game's icon + name.
- `transition_<profile>` overrides, so a store video can fade where the UA cut slides.
  `PICK_FALLBACK` lets `caption_ua` cover every UA ratio.

### Changed
- UA profiles allow 6–60 s, the range across networks; `storyboard` says which networks fit.
- Captions pop in by default and cards rise in. Set `anim: "fade"` / `"settle"` for the v1.3
  look.
- Docs: the brief template (core message, 2–3 pillars, don'ts, end slate), new directions (Fail
  → solve, Noob vs pro, unresolved Challenge), touch, motion, brand bug and look sections, both
  stores' rules, Derek Lieu's trailer principles, the music stop, and thumbnails.

### Fixed
- A looped still with no `-t` (the brand bug) kept `join` running for ever: overlay lasts as
  long as either input. Every looped input is now bounded.

## v1.3.0 — 2026-10-21

What game-video studios and ad networks do, applied to the skill. Sources: Creatune, Sunstrike
Studios, Quadral, Anna K, vinhle3230, the Fiverr/Upwork market, Meta's click-to-play creative
guide and Unity's video specs.

### Added
- `references/mobile-ad-playbook.md` covers:
  - the brief;
  - one promise per video;
  - hook angles (promise / number / conflict);
  - the first 3 s;
  - real gameplay only (no "fake gameplay" ads);
  - sound-off design;
  - ratios, lengths and file caps per placement;
  - the variant matrix;
  - QA and file naming.

  Each rule names its source.
- **UA ratios.** New profiles `ua-1x1` (1080×1080, Meta feed), `ua-4x5` (1080×1350) and `ua-16x9`
  (1920×1080, Unity / AppLovin landscape, Meta desktop), all 15–30 s. Shots without `profiles`
  go into every ratio, and `"ua"` in a `profiles` list means the whole `ua*` family.
- **Variants.** `ad.json → variants.<name>` patches shots by index: a new hook take or caption,
  `{"drop": true}` for a 15 s cut, translated captions. It also merges `end_card` / `audio` /
  `music`. `storyboard` / `render` / `check --variant a,b` apply variants in order. Output and
  check frames are named after the variant (`ad-ua-9x16-hook-number-short.mp4`).
- **Hook rule.** For `ua*`, `check` fails a cut that opens on a card or shows any card before
  3 s; logos go on the end card (Meta, Creatune). `storyboard` also flags it, and warns when no
  caption shows in the first 3 s (most viewers watch muted).
- **UA file cap.** 30 MB for `ua*` (Meta's click-to-play guidance; Unity recommends 10 MB, max
  100 MB).
- `ad.json → brief` (free text: store link, channels, promise, references). Steps 1, 4, 5, 6, 7
  and 9 of SKILL.md now cover the brief, clean capture, hook angles, the variant matrix and
  per-channel ratios.
- `templates/ad.example.json` gains a brief and hook / language variants.

### Changed
- `panel` and `grid` now also fall back to `fit` in square profiles, not only in portrait ones.

## v1.2.0 — 2026-10-21

### Added
- **Trailer mode.** A 16:9 gameplay trailer, cut on the music's beat, in the style of a showcase
  trailer such as *Constance – Official Gameplay Trailer*. New profiles:
  - `trailer`: 1920x1080, 45–120 s, music-led mix (full-range BGM at 0.9, 2 s fade-out), AAC
    320k, `trailer-16x9.mp4`;
  - `trailer-9x16`: 1080x1920, 30–60 s cut-down from the same storyboard, `trailer-9x16.mp4`.
- `scripts/beats.py` and `build_ad.py beats MUSIC [--drop-at S] [--length L]`. They find BPM,
  first downbeat, energy sections, rises and the drop with numpy only, and suggest the
  `music.start` that lands the drop on cue. Tested on click tracks at 97/120 BPM (beat0 within
  3 ms) and on huashu `bgm-ad` (126 BPM).
- **Beat-cut timing.** An item with `beats` ends on the grid set by
  `music: {bpm, beat0, start}`. `storyboard` shows a `lands` column (bar:beat) and flags cuts off
  the beat. `check` fails a hard cut more than a frame off the beat (`music.sync: false` turns it
  off).
- **Cards.** A `{"card": {"text", "style": "title|feature|logo", "sub", "bg_take", "bg_at"}}` item
  in `shots` renders a full-frame card. `game.logo` (a wordmark PNG) is used on logo cards and
  end cards.
- **`layout` for portrait footage in 16:9.** `fit` (default, as before), `fill` (cut a band
  around `fill_y`), `panel` (take on a rounded card on one `side`, caption as big text beside
  it), `grid` (2–3 `takes` side by side). In portrait profiles, `panel` and `grid` fall back to
  `fit`.
- The end card gains `date` and `platforms` (text chips).
- A top-level `"profiles"` sets the default profiles for a storyboard's shots.
- `pick()` generalises `caption_<profile>` to `layout_<profile>`, `zoom_<profile>`,
  `music_<profile>` and `fade_in_<profile>`. `fade_in` opens the video from black, and `check`
  then passes `--allow-black-open` to verify-video.sh.
- `board --wide` renders a 16:9 hook frame for trailer directions.
- `references/trailer-structure.md` (acts, cut-down, directions, editing rules, cards, layouts,
  audio, specs) and `templates/trailer.example.json`.

### Fixed
- Cards and the end card came out a sixth short. A looped still read at 25 fps through zoompan
  gave 25 frames per second of slot, so the video stream ended before the audio. Beamfork's
  current UA ad has 539 video frames for an 18.4 s (552-frame) timeline. Stills now loop at
  30 fps.
- Cuts slipped by a frame per xfade and the game sound drifted late. Timestamps are now rebuilt
  from frame and sample counts in `join`, segments are frame-exact (`-frames:v`, timeline in
  whole frames), and intermediate audio stays PCM (`.mov`) until the final AAC encode. Rendered
  videos now match the storyboard to the frame. On the 16:9 test trailer, every detectable cut
  lands at 0 ms from its planned beat.
- `check` reports a check frame past the end of the video instead of crashing.

### Changed
- Caption and end-card sizes follow the frame's short side, so 16:9 matches 9:16. Portrait
  output is unchanged.
- In landscape, `bottom` captions sit at 10 % from the bottom edge.
- Multi-line text wraps balanced.
- Check-frame numbers can move by one frame against v1.1.0, because shot times are now rounded
  to whole frames rather than truncated.

## v1.1.0 — 2026-10-21

### Changed
- Videos never go to GitHub. `recorder.py serve` and `build_ad.py render` write or extend a `.gitignore` in the output folder (`*.mp4 *.mov *.m4v *.webm *.mkv`, `takes/`, `shots/`, `sheets/`, `.build-*/`), so the rendered ads are ignored along with the takes. `build_ad.py check` fails a video that git would track or push. SKILL.md gains rule 5 and a `Git` line in the report.

## v1.0.0 — 2026-10-21

### Added
- `scripts/recorder.py` — long-lived game session the agent drives between thinking steps: `serve` (Playwright + Chrome, or `--android` via adb), `shot` / `tap` / `swipe` / `key` / `wait`, `rec start|stop`, `mark`, scripted `play`, `status`, `stop`. Web takes come from CDP `Page.startScreencast` (works headless and on Wayland), resampled to constant 30 fps at device resolution (`--force-device-scale-factor`). Optional `--audio` records the PulseAudio/PipeWire monitor alongside.
- `scripts/build_ad.py` — `storyboard`, `board` (direction board PNG), `render` (`ua` 1080x1920, `app-preview` 886x1920; 15–30 s enforced; smoothstep push-ins on a named anchor; blurred fill; HTML captions with a readability plate; end card; xfade transitions), `check` (size, fps, duration, codec, AAC stereo, 500 MB cap, huashu-design `verify-video.sh`, check frames extracted).
- Audio follows huashu-design's two-layer mix (BGM lowpass 4 kHz at 0.45, SFX highpass 800 Hz, `amix normalize=0`, loudnorm −14 LUFS), using its `bgm-*.mp3` and `sfx/**` when installed.
- Three-direction human gate and storyboard card adopted from huashu-design.
- `references/ad-structure.md`, `templates/ad.example.json`, `templates/take.example.json`.
