# Changelog

## v1.0.0 — 2026-10-21

### Added
- `scripts/recorder.py` — long-lived game session the agent drives between thinking steps: `serve` (Playwright + Chrome, or `--android` via adb), `shot` / `tap` / `swipe` / `key` / `wait`, `rec start|stop`, `mark`, scripted `play`, `status`, `stop`. Web takes come from CDP `Page.startScreencast` (works headless and on Wayland), resampled to constant 30 fps at device resolution (`--force-device-scale-factor`). Optional `--audio` records the PulseAudio/PipeWire monitor alongside.
- `scripts/build_ad.py` — `storyboard`, `board` (direction board PNG), `render` (`ua` 1080x1920, `app-preview` 886x1920; 15–30 s enforced; smoothstep push-ins on a named anchor; blurred fill; HTML captions with a readability plate; end card; xfade transitions), `check` (size, fps, duration, codec, AAC stereo, 500 MB cap, huashu-design `verify-video.sh`, check frames extracted).
- Audio follows huashu-design's two-layer mix (BGM lowpass 4 kHz at 0.45, SFX highpass 800 Hz, `amix normalize=0`, loudnorm −14 LUFS), using its `bgm-*.mp3` and `sfx/**` when installed.
- Three-direction human gate and storyboard card adopted from huashu-design.
- `references/ad-structure.md`, `templates/ad.example.json`, `templates/take.example.json`.
