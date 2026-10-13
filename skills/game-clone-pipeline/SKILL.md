---
name: game-clone-pipeline
description: >-
  Clone a successful mobile casual/puzzle game into a differentiated, English-only Flutter game
  and take it to the App Store with a landing page, in 10 gated
  stages: pick the target → APK facts with REA + human gameplay recording → evidence-backed
  SPEC → differentiation and economy design → Flutter core with tests, bot and simulator →
  3 UI directions (huashu-design) → flutter-ui-revamp + icon → IAP and playtest →
  codebase-modernizer → plan-to-issues → fixes → privacy/support pages → iOS kit built and
  uploaded on a Mac → appstore-assets, aso-marketing, appstore-review-checker, asc validate →
  ship → submit → search-optimizer and design-optimizer on the landing repo. Pauses at human
  gates, commits after every stage with the commit skill, resumes from `.clone/status.md`.
  Use when asked to "clone a game", "make a game like X", "làm game giống X", "clone game",
  "quy trình clone game", "chạy quy trình clone", "game clone pipeline". Don't use for original
  game ideas with no reference game (flutter-factory, android-game-forge), non-Flutter stacks,
  web apps, or a single step on its own (call that skill directly).
license: MIT
effort: high
capabilities:
  - orchestration
  - workflow
  - human-gates
  - flutter
  - app-store
metadata:
  version: 1.1.0
  author: "Nguyen Van Lam"
permissions:
  filesystem: { read: true, write: true }
  shell: { enabled: true }
  network: { enabled: true }   # store pages, gh, asc, pub get
  secrets: { required: false } # Apple keys stay with the human; never written to the repo
---

# game-clone-pipeline: reference game → differentiated Flutter game → App Store

The agent orchestrates; sibling skills do the specialised work. The human plays the original,
approves five gates, and builds/uploads on a Mac. `PROCESS.md` (Vietnamese) is the one-page
version for people; this file is the operating manual.

## Hard rules

1. **Facts and mechanics only.** REA and recordings feed `SPEC.md` with rules and numbers. No
   asset, frame, sound, font, string, level file or code from the original (APK, ads, store
   page) ever enters the game repo's tracked files. `.clone/` is git-ignored.
2. **Differ before you draw.** Theme, palette, naming and an own mechanic are decided at S2 and
   checked against `references/differentiation-gate.md`. The core is built on placeholder art;
   the real look arrives at S4.
3. **Economy with the core loop.** Fail state, boosters, IAP and anti-farm rules are designed
   at S2 (`references/economy-and-monetization.md`), not bolted on later.
4. **English only.** All in-game text, store listing (en-US, no localization), IAP names,
   landing page, privacy and support pages. Internal docs (SPEC, DESIGN, status) may be
   Vietnamese.
5. **main + tags.** Work on `main`; releases are tags `vX.Y.Z`. No long-lived `ios` branch.
   Short feature branches merged back are fine.
6. **Gates advance on evidence.** A command that ran in this session and exited 0, or a human
   answer recorded in `.clone/status.md`. Never on a claim.
7. **Commit after every stage** with the `commit` skill (English conventional commit, secret
   scan, push, never `--no-verify` or force). Tags and releases are `/ship`'s job.
8. **App Store only.** No Google Play release in this pipeline; Android files in the Flutter
   project are left as generated.
9. **Human-only decisions stay human:** gates G0, G0b, G1, G2 (UI direction), G3 (prices), G4
   (submit), every App Store submission, every secret value, every paid action.

## Roles

| Who | Does |
|---|---|
| Human | Plays the original and records it, answers ❓, approves gates, provides Apple account access, builds and uploads on a Mac |
| Agent | Runs every other step: REA analysis, contact sheets, SPEC, DESIGN, code, tests, sibling skills, `asc` from Ubuntu, commits |

## Workspace (inside the game repo)

```
SPEC.md                 # S1: evidence-backed research (references/spec-template.md)
DESIGN.md               # S2: differentiation table, economy, difficulty targets, name
.clone/status.md        # stage checklist + gate log (from templates/status.md) — read first
.clone/reference/       # recordings, store screenshots, contact sheets  (git-ignored)
.clone/apk/             # the original's APK and REA notes                 (git-ignored)
tool/simulate.dart      # S3: plays many seeded games with a bot and a careless player
scripts/build-ios.sh    # S8: from templates/, archive/export/upload on a Mac
docs/IOS-BUILD-ON-MAC.md
```

Add `.clone/reference/` and `.clone/apk/` to `.gitignore` at S1, before anything is copied in.

## Start or resume

1. If `.clone/status.md` exists, read it and continue at the first unchecked stage. Re-run the
   last stage's verification before trusting a checked box from an older session.
2. Otherwise ask for the target (store URL or name) and the repo location, copy
   `templates/status.md` to `.clone/status.md`, fill the header, start at S0.
3. **Sibling skills**: invoke them by name with the Skill tool. If one is missing, do its step
   inline with the same output, and log it under "Fallbacks" in status.md. A missing skill
   lowers quality; it never stops the run.

## Stages

### S0 — Pick the game → gate G0

- `idea-validator` on "a differentiated clone of <original>": demand, competition, feasibility.
- Fit check (write the answers in status.md): 2D and rule-based (Flutter + CustomPainter or
  Flame can do it), a twist is possible, the category is not flooded with near-identical clones
  (Guideline 4.3), the original's monetization is understood from its store page.
- **G0**: human approves the target and the twist hypothesis. Commit (`docs: start clone of …`).

### S1 — Evidence: APK + recording → SPEC → gate G0b

0. **APK via REA** (`reverse-engineer-anything`). Get the APK from the human, or with a phone
   attached `pull_adb_package` (REA). Use REA's Android tools (manifest, resources via Apktool,
   JADX classes) to record: engine (Unity IL2CPP/Mono, Flutter, native), SDKs (ads, mediation,
   analytics, IAP), product IDs, permissions, readable config numbers. Logic inside
   `libil2cpp.so` or values from remote config → write "not recoverable from the APK" and rely
   on observation. Record facts with the file path as evidence in SPEC §2. Copy nothing else.
   REA's own terms limit it to lawful research and authorized analysis; stay within them.
1. **Human records gameplay**: 30–60 min across several levels or difficulty tiers, including
   one deliberate loss and the booster/shop screens. Phone screen recorder, or with a cable the
   agent runs `adb shell screenrecord` / REA `capture_adb_screen`. Files go to `.clone/reference/`.
2. **Agent**: `scripts/contact-sheet.sh <video> .clone/reference/sheets [--at t1,t2]` (1 fps
   sheets with burned-in timestamps, 4 fps strips around key moments); read the sheets with
   vision; fetch the store pages and screenshots; write `SPEC.md` from
   `references/spec-template.md`. Every rule cites a timestamp or path; guesses are ❓.
   Observation beats the APK when they disagree.
3. End SPEC with the ❓ list as concrete requests ("record filling the board completely").
- **G0b**: human answers or records more; agent updates SPEC (at most 2 rounds); what remains
  becomes an explicit assumption in DESIGN.md. Commit (`docs(spec): …`).

### S2 — Differentiation and economy → gate G1

- Fill `DESIGN.md`: the table from `references/differentiation-gate.md` (every **must** row
  "different", one own mechanic), economy per `references/economy-and-monetization.md` (fail
  state, session unit, boosters with anti-farm rules, IAP list with product IDs, ads yes/no,
  analytics yes/no), difficulty targets for the simulator, English name.
- `brand-name-checker` on the name; act on Proceed/Modify/Abandon.
- **G1**: human approves DESIGN.md. Commit.

### S3 — Core in Flutter (placeholder art)

- New project: `flutter-init` (org from the user's other apps, e.g. `com.nguyenvanlam`).
- Rules in pure Dart (no Flutter imports) so tests and the simulator run on the VM; seeded,
  platform-identical RNG (xorshift-style) for deals/levels; UI replays rule "steps".
- Tests for every rule in SPEC §4 that we keep; a heuristic bot; `tool/simulate.dart` printing
  win rates of bot and careless player per difficulty band against DESIGN.md targets.
  `test-coverage` if branches are thin.
- Verify: `flutter analyze` and `flutter test` exit 0; simulator numbers recorded in DESIGN.md.
  Commit after each green milestone.

### S4 — UI direction and look → gate G2

1. `huashu-design` (default; `lam-design` if the user prefers): three real HTML directions for
   the game screen + home, using our DESIGN.md theme, not the original's. The skill stops for
   the choice: **G2**. Run the differentiation check (fresh-eyes comparison) on the chosen one.
2. `flutter-ui-revamp`: give it the chosen direction so Step 2 only records it in
   `.revamp/design-direction.md`; it sources licence-verified assets, builds the design system,
   applies it to the real screens and verifies.
3. `logo-designer` for the app icon; generate platform icons (no alpha for iOS).
- Verify: analyze + test exit 0, screenshots of home and game captured. Commit.

### S5 — IAP, boosters, telemetry, playtest → gate G3

- Implement DESIGN.md's economy: `in_app_purchase` (+ storekit), Restore purchases, every
  purchase path, store-unavailable message without naming platforms, anti-farm tests, no debug
  unlock in release. Analytics/crash SDK only if DESIGN.md says so (then update privacy page).
- Human playtest (3–5 people or the user): note where they get stuck or bored; re-tune with
  the simulator.
- **G3**: human approves the product list and price tiers. Commit.

### S6 — Codebase hardening

- `codebase-modernizer` (the "codebase optimiser" step): read-only audit → `MODERNIZATION_PLAN.md`.
- `plan-to-issues`: plan → labelled GitHub issues under one epic.
- Fix them: `issue-work-loop` per issue when herdr + gh are available, else fix directly on
  short branches merged to main. `code-review` optional for risky changes.
- Verify: analyze + test exit 0 on main. Commit/merge.

### S7 — Landing repo, minimal (before any submission)

- New repo `<game>-site`: `landing-page-generator` for copy, a simple English page,
  `privacy.html` and `support.html` from `templates/` filled from DESIGN.md (must match what the
  app really collects), `.github/workflows/pages.yml` from `templates/pages.yml`, Pages enabled.
- Verify: both URLs return 200 (`curl -sI`). Commit with `commit` in that repo.

### S8 — iOS: prepare on Ubuntu, build and upload on a Mac → gate G4

Follow `references/ios-release-runbook.md`. In short:
1. `flutter-ios-release` (prep-report exit 0); copy `templates/build-ios.sh` →
   `scripts/build-ios.sh`, `templates/ExportOptions.plist` → `ios/ExportOptions.plist`; write
   `docs/IOS-BUILD-ON-MAC.md`; `asc bundle-ids create`; app record created by the human in the
   web UI; `asc iap setup/create` for DESIGN.md's products. Commit.
2. Human on a Mac: `TEAM_ID=… scripts/build-ios.sh upload`. Agent: `asc builds wait`.
3. TestFlight with a Sandbox account: buy, cancel, reinstall, restore; IAP review screenshot.
4. `appstore-assets` (en-US; iPad set only if iPad is targeted), `aso-marketing` (en-US), then
   `asc metadata` / `screenshots` / `age-rating` / `categories` / `review` to push them.
5. `appstore-review-checker`, then `asc validate --app APP_ID --version X.Y.Z --check-urls`.
   **G4**: human reads both reports and approves.
6. `/ship --no-auto` (version bump, changelog, tag, push; asks per step) → human uploads the
   release build from the Mac → `asc release stage …` → submit (web "Add for Review" with the
   first IAP, or `asc publish appstore --ipa … --submit --confirm`). Record in status.md, commit.

### S9 — Landing polish and follow-up

- In the site repo: `search-optimizer`, then `design-optimizer`; store badges and links once
  the app is live. Commit; Pages redeploys on push.
- After launch: `asc reviews`, `asc analytics` / `insights`; feed findings back as issues.

## Final report (end of each session)

Stage reached, gates passed with dates, commands run and their exit codes, fallbacks, open
assumptions, what the human must do next (record, approve, build on the Mac). Tick boxes in
`.clone/status.md` and commit it.

## Files in this skill

| Path | Use |
|---|---|
| `PROCESS.md` | Vietnamese one-page process for people |
| `references/spec-template.md` | SPEC skeleton and evidence rules (S1) |
| `references/differentiation-gate.md` | similarity checklist, hard "no" list (S2, S4, S8) |
| `references/economy-and-monetization.md` | fail state, boosters, IAP, ads, analytics (S2, S5) |
| `references/ios-release-runbook.md` | Ubuntu prep + Mac build/upload + `asc` commands (S8) |
| `scripts/contact-sheet.sh` | recording → timestamped contact sheets and strips (S1) |
| `templates/status.md` | `.clone/status.md` starter |
| `templates/build-ios.sh`, `templates/ExportOptions.plist` | Mac archive/export/upload kit (S8) |
| `templates/privacy.html`, `templates/support.html` | App Store privacy and support pages (S7) |
| `templates/pages.yml` | GitHub Pages deploy for the landing repo (S7) |
