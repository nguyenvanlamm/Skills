# Changelog

## 1.1.1 — 2026-10-13

- S3 runs `flutter-init` in place inside the existing game repo: `--project-name` in snake_case
  (a `<game>-clone` folder name makes `flutter create .` exit 1), no second `git init`, and our
  `.gitignore` moved aside and appended back, because `flutter create` keeps an existing one and
  would leave `build/` and `.dart_tool/` unignored.
- Hard rule 1 names the ignored folders (`.clone/reference/`, `.clone/apk/`); `.clone/status.md`
  is tracked so a run can resume. It used to say all of `.clone/` was ignored, contradicting the
  "commit status.md" steps.
- Six gates, not five; PROCESS.md title shows the current version.

## 1.1.0 — 2026-10-13

- Drop the Google Play stage: the pipeline releases to the App Store only.
- Stages renumbered S0–S9 (landing polish is now S9).

## 1.0.0 — 2026-10-13

- First version. Eleven stages at 1.0.0 (S0–S10) with human gates G0, G0b, G1, G2, G3, G4 and a
  resumable `.clone/status.md`.
- S1 combines APK facts from REA with a human gameplay recording; `scripts/contact-sheet.sh`
  turns recordings into timestamped contact sheets for the evidence-backed SPEC.
- Differentiation gate and economy guide decided before any art (lessons from Coin Cubby).
- English-only games; commit after every stage with the `commit` skill; main + tags only.
- iOS is prepared on Ubuntu and built/uploaded on a Mac (`templates/build-ios.sh`,
  `ExportOptions.plist`, runbook with `asc` commands); no CI build.
- Landing repo templates: privacy, support, GitHub Pages workflow.
