# Changelog

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
