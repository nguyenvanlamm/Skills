# Changelog

## v1.0.0 — 2026-09-13

### Added
- `SKILL.md` — 12-phase orchestrator (Environment → Analyse → Platform matrix → Architecture → Scaffold → Implement → Platform adapt → Test → Security → Quality → Build validation → Report) turning a natural-language idea into a Flutter project for Web + Android + iOS.
- Capability → sibling-skill table with an explicit inline fallback for every row; contract notes for `flutter-init` (no web in its `platforms` → add with `flutter create --platforms web .`), `flutter-build` (Android-only, needs signing) and the planning skills' Repo Sync trap.
- `scripts/check-env.sh` — per-platform `buildable` / `blocked: <reason>` verdicts (Flutter, Chrome, JDK, Android SDK, Xcode, CocoaPods), JSON on stdout, never installs.
- `scripts/build-all.sh` — `pub get → analyze → test → build web → apk → appbundle → ios --no-codesign`; statuses `ok | fail | skipped_env | skipped_user`; deletes stale artifacts before each build; `--only <step>` reruns one step and merges into the existing `build/flutter-all-platform/build-report.json`; iOS is `skipped_env` off macOS, never a pass or a fail.
- `references/architecture.md` — feature-first layout, default stack with reasons and "skip when" column, conditional-export platform abstraction pattern, Android/iOS/web pins, `--dart-define` env.
- `references/design-system.md` — tokens, component contracts (`AsyncValueView`, `AppScaffold` …), Material 3 window-class breakpoints, adaptive navigation, accessibility and per-screen state checklist.
- `references/platform-checklists.md` — verifiable Web / Android / iOS / Security checks and the environment-vs-project error triage table.
- `references/report-template.md` — final report skeleton filled only from `build-report.json` and the state file.

### Breaking Changes
- None (initial release).
