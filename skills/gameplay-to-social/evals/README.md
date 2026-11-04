# Evals

Five cases: four from the brief, one from a real run (2026-11-04). Each one needs a real Flutter game project as its working folder,
so the cases can't run from `files/` alone. Prepare it like this:

- **first-run-unsetup-project**: a copy of a game repo with no `social/` and no `lib/main_capture.dart`.
- **record-level10-all-platforms**: the same copy plus `lib/main_capture.dart` (built from
  `assets/main_capture.dart`) and a `social/config.yaml` whose `capture.device` is usable on
  the machine (Chrome on a desktop without a phone).
- **no-device-connected**: the set-up copy with `web/` removed, `game.platforms: [android, ios]`,
  a phone in `capture.device`, and no phone or emulator connected.
- **existing-video-reddit-linkedin**: the set-up copy plus a 20 s gameplay MP4. Point the
  prompt's path at it. Videos are not committed.
- **record-level-lose-endcard**: a set-up copy whose capture entry can lose on purpose (Bus Loop
  Rush's `lib/main_capture.dart` reads `CAPTURE_OUTCOME=lose`), with Chrome as the device. It
  checks the end card in the last 2 s, the viewport check and the chosen-only `posts.txt`.

The game used on 2026-11-03 was a 60-level portrait puzzle game with a demo bot. The run
results are in the skill-creator workspace, not here.
