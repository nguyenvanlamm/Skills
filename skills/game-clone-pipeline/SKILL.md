---
name: game-clone-pipeline
description: >-
  Turn a successful mobile casual/puzzle game, or a game idea set against the closest hits, into
  a differentiated, English-only Flutter game on the App Store with a landing page, in 10 gated
  stages: pick target and reference games → evidence from whatever the human has (APK via REA,
  game data, a short video, a description) → SPEC → differentiation and economy design →
  Flutter core with tests, bot and simulator → 3 UI directions (huashu-design) →
  flutter-ui-revamp + icon → IAP and playtest → codebase-modernizer, plan-to-issues, fixes →
  privacy/support pages → iOS built on a Mac → appstore-assets, aso-marketing,
  appstore-review-checker → ship and submit → search-optimizer, design-optimizer.
  Pauses at human gates, commits each stage, resumes from `.clone/status.md`. Use when
  asked to "clone a game", "make a game like X", "làm game giống X", "làm game từ ý tưởng này",
  "chạy quy trình clone". Don't use for non-game apps (flutter-factory), Kotlin games
  (android-game-forge), web apps, or a single step on its own.
license: MIT
effort: high
capabilities:
  - orchestration
  - workflow
  - human-gates
  - flutter
  - app-store
metadata:
  version: 1.7.0
  author: "Nguyen Van Lam"
permissions:
  filesystem: { read: true, write: true }
  shell: { enabled: true }
  network: { enabled: true }   # store pages, gh, pub get
  secrets: { required: false } # Apple keys stay with the human; never written to the repo
---

# game-clone-pipeline: reference game or idea → differentiated Flutter game → App Store

The agent orchestrates; sibling skills do the specialised work. The human brings what they have
about the game (an APK, data files, a video, a description), approves six gates, and
builds/uploads on a Mac. "The original" below means the reference game(s) chosen at S0. `PROCESS.md` (Vietnamese) is the one-page
version for people; this file is the operating manual.

## Hard rules

1. **Facts and mechanics only.** APK, data files, recordings and descriptions feed `SPEC.md`
   with rules and numbers. No asset, frame, sound, font, string, level file or code from the
   original (APK, data files, ads, store page) ever enters the game repo's tracked files.
   `.clone/reference/`, `.clone/apk/` and `.clone/data/` are git-ignored; `.clone/status.md` is
   tracked so any session can resume.
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
10. **Keep the steps pane current.** `.clone/status.md` drives the steps pane: rewrite its
    `Now:` line when a stage or a numbered step starts (`Now: S1 · 2 contact sheets`), and its
    `Waiting on:` line with the human's next action whenever the run stops for them
    (`Waiting on: G0b: trả lời ❓ trong SPEC.md`), back to `—` once they answered. The pane
    redraws by itself.
11. **No GitHub Actions.** No file under `.github/workflows/` in the game repo or the site repo,
    no CI job, no build on Actions. Checks run on the dev machine: `flutter analyze`,
    `flutter test`, the simulator, and pre-commit hooks once installed. Every delegate inherits
    this: a "no CI" finding is not a finding, and no task may add a workflow. GitHub Pages
    deploys from a branch, not from a workflow.
12. **`asc` is deferred.** The agent runs no `asc` command (no auth, bundle ids, IAP, metadata,
    screenshots, validate, release or reviews) until the human lifts this rule. Everything
    `asc` would push is written as files instead: `docs/APP-STORE-CONNECT.md` (bundle id, product
    ids, prices, review notes, URLs, a checklist) plus `store/` (screenshots, en-US texts), and
    the human enters it in the App Store Connect web UI. Status changes there advance on the
    human's answer, recorded in status.md.
13. **Apple account steps are deferred.** The human's App Store Connect web setup, the Mac
    build and upload, and the TestFlight test (S8 steps 2–3) are postponed by default: list them
    under `## Deferred (human)` in status.md, do not stop for them, and continue with the steps
    that need no Apple account (S8 steps 4–5, then S9's site work). Only `/ship`, the release
    upload and the submission (S8 step 6) wait until the human resumes the deferred steps.

## Roles

| Who | Does |
|---|---|
| Human | Brings what they have (APK, data files, a gameplay clip, a description), answers ❓, approves gates, provides Apple account access, builds and uploads on a Mac |
| Agent | Runs every other step: REA analysis, contact sheets, SPEC, DESIGN, code, tests, sibling skills, commits; prepares App Store Connect inputs as files (hard rule 12) |

## Workspace (inside the game repo)

```
SPEC.md                 # S1: evidence-backed research (references/spec-template.md)
DESIGN.md               # S2: differentiation table, economy, difficulty targets, name
.clone/status.md        # stage checklist, Now / Waiting on, gate log (from templates/) — read first
.clone/reference/       # recordings, store screenshots, contact sheets  (git-ignored)
.clone/apk/             # the original's APK and REA notes                 (git-ignored)
.clone/data/            # game data the human gave: config, levels, saves  (git-ignored)
tool/simulate.dart      # S3: plays many seeded games with a bot and a careless player
scripts/build-ios.sh    # S8: from templates/, archive/export/upload on a Mac
docs/IOS-BUILD-ON-MAC.md
```

Add `.clone/reference/`, `.clone/apk/` and `.clone/data/` to `.gitignore` at S0, before
anything is copied in.

**Names.** The game repo (folder and GitHub repo) carries the game's name in kebab-case,
`<game>` (Nightwall → `nightwall`); the landing repo is `<game>-site`. Never a `-clone` suffix,
in either. Until G1 fixes the name, the repo uses a working slug of the idea or target (also
without `-clone`) and is renamed right after G1 (see S2).

## Start or resume

1. If `.clone/status.md` exists, read it and continue at the first unchecked stage. Re-run the
   last stage's verification before trusting a checked box from an older session.
2. Otherwise ask for the target (a store URL or name, or a description of the game idea), what
   the human already has about it (S1's sources), and the parent folder; create the repo there
   under a working slug (see Names), private on GitHub; copy
   `templates/status.md` to `.clone/status.md`, fill the header, start at S0.
3. **Steps pane**: `python3 <skill-dir>/scripts/steps_pane.py open <repo>` splits the agent's
   herdr pane and shows S0–S9 on the right with the current stage marked, reusing one already
   open. Exit 69 means no herdr: then show the output of `steps_pane.py once <repo>` in the chat
   at every stage change and gate stop instead.
4. **Sibling skills**: invoke them by name with the Skill tool. If one is missing, do its step
   inline with the same output, and log it under "Fallbacks" in status.md. A missing skill
   lowers quality; it never stops the run.

## Stages

### S0 — Pick the game and its references → gate G0

- Reference games: the named original. For an idea with no original, the 1–3 closest
  successful games from `idea-validator`'s competitor list, confirmed by the human at G0.
- `idea-validator` on "a differentiated clone of <original>", or on the idea itself: demand,
  competition, feasibility.
- Fit check (write the answers in status.md): 2D and rule-based (Flutter + CustomPainter or
  Flame can do it), a twist is possible, the category is not flooded with near-identical clones
  (Guideline 4.3), the reference games' monetization is understood from their store pages.
- **G0**: human approves the target, the reference games and the twist hypothesis. Commit
  (`docs: start clone of …`).

### S1 — Evidence from what the human has → SPEC → gate G0b

One source is enough to start; each extra one turns ❓ into facts. Use what the human named at
the start, ask once for anything else they may have, and never wait for a source they lack.

| Source | Put in | Read with | Best for |
|---|---|---|---|
| APK / XAPK / AAB | `.clone/apk/` | REA (step 1) | engine, SDKs, IAP product IDs, permissions, shipped config |
| Game data: config JSON/CSV, level files, remote-config or save dumps, asset bundles | `.clone/data/` | Python or `jq`; binary bundles with REA `inspect_artifact` (step 3) | exact numbers: board sizes, spawn tables, prices, timers, difficulty curve |
| Gameplay video of any length; a few minutes of the core loop is enough to start | `.clone/reference/` | `scripts/contact-sheet.sh` (step 2) | rules, flow, timings, feedback, fail state |
| Store pages, screenshots, public gameplay videos | `.clone/reference/` | fetched by the agent for every named reference game | store facts, monetization, the look to avoid |
| Written description of the game or the idea | quoted in SPEC §4 | as given (step 4) | rules as the human knows or wants them |

1. **APK via REA** (`reverse-engineer-anything`). From the human, or with a phone attached
   `pull_adb_package` (REA). Use REA's Android tools (manifest, resources via Apktool, JADX
   classes) to record: engine (Unity IL2CPP/Mono, Flutter, native), SDKs (ads, mediation,
   analytics, IAP), product IDs, permissions, readable config numbers. Logic inside
   `libil2cpp.so` or values from remote config → write "not recoverable from the APK". Record
   facts with the file path as evidence in SPEC §2. Copy nothing else. REA's own terms limit it
   to lawful research and authorized analysis; stay within them.
2. **Video**: `scripts/contact-sheet.sh <video> .clone/reference/sheets [--at t1,t2]` (1 fps
   sheets with burned-in timestamps, 4 fps strips around key moments); read the sheets with
   vision. With a cable the agent can record itself (`adb shell screenrecord` / REA
   `capture_adb_screen`). A loss and the shop/booster screens settle most economy ❓: ask for
   them as short clips, not a long session.
3. **Game data**: take numbers and distributions (colours per level band, capacity, timers,
   prices), never the level layouts themselves. Cite file and key
   (`.clone/data/levels.json → levels[12].capacity`) in SPEC §2.
4. **Description**: quote it rule by rule in SPEC §4 with "description" as the evidence;
   whatever it leaves open is ❓. For an idea, SPEC §1, §3 and §5 cover the reference games
   from their store pages and public videos.
5. Write `SPEC.md` from `references/spec-template.md`; every rule cites its source, guesses are
   ❓. When sources disagree, the video beats data files and the APK (remote config may override
   shipped values), data files beat numbers estimated from a video, a description loses to any
   of them; note both values.
6. End SPEC with the ❓ list as the cheapest concrete requests ("a 1-minute clip filling the
   board completely", "the shop screen", "the file behind …").
- **G0b**: human answers, sends more, or accepts the gaps; agent updates SPEC (at most 2
  rounds); what remains becomes an explicit assumption in DESIGN.md. Commit (`docs(spec): …`).

### S2 — Differentiation and economy → gate G1

- Fill `DESIGN.md`: the table from `references/differentiation-gate.md` (every **must** row
  "different", one own mechanic), economy per `references/economy-and-monetization.md` (fail
  state, session unit, boosters with anti-farm rules, IAP list with product IDs, ads yes/no,
  analytics yes/no), difficulty targets for the simulator, English name.
- `brand-name-checker` on the name; act on Proceed/Modify/Abandon.
- **G1**: human approves DESIGN.md. Commit.
- Rename the repo to the approved name (see Names), unless it already has it:
  `gh repo rename <game>`, move the folder to `<parent>/<game>`, then
  `git remote set-url origin git@github.com:<owner>/<game>.git` and update the repo URL in the
  status.md header. Reopen the steps pane on the new path.

### S3 — Core in Flutter (placeholder art)

- New project: `flutter-init` inside the game repo (org from the user's other apps, e.g.
  `com.nguyenvanlam`). The folder already holds `.git`, `.gitignore`, `.clone/`, `SPEC.md` and
  `DESIGN.md` from S0–S2, so:
  - when it asks about the existing directory, answer **use in place**: run its create command
    with `--project-name <snake_case> .` (a kebab-case folder name such as `<game>` with a
    hyphen is not a valid Dart package name, and `flutter create .` exits 1 on it);
  - `flutter create` keeps an existing `.gitignore`, so move ours aside first and append it back
    afterwards; otherwise `build/` and `.dart_tool/` are not ignored:
    `mv .gitignore .gitignore.clone` → create → `cat .gitignore.clone >> .gitignore && rm .gitignore.clone`;
  - skip its `git init` (the repo and its remote exist since S0), keep the credential lines it
    appends to `.gitignore`;
  - before committing, `git status --short` shows nothing from `.clone/reference/`,
    `.clone/apk/`, `.clone/data/`, `build/` or `.dart_tool/`.
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
  Pass it hard rule 11 in its arguments: the `CI` dimension covers local pre-commit hooks only,
  "no CI" is out of scope, and the plan must not contain a workflow task (`devops-pipeline`
  runs pre-commit only).
- `plan-to-issues`: plan → labelled GitHub issues under one epic.
- Fix them: `issue-work-loop` per issue when herdr + gh are available, else fix directly on
  short branches merged to main. `code-review` optional for risky changes.
- Verify: analyze + test exit 0 on main. Commit/merge.

### S7 — Landing repo, minimal (before any submission)

- New repo `<game>-site`: `landing-page-generator` for copy, a simple English page,
  `privacy.html` and `support.html` from `templates/` filled from DESIGN.md (must match what the
  app really collects). The site repo is public (free Pages). Enable Pages from the branch, no
  workflow (hard rule 11):
  `gh api -X POST repos/<owner>/<game>-site/pages -f 'source[branch]=main' -f 'source[path]=/'`.
  Every push to `main` republishes the site.
- Verify: both URLs return 200 (`curl -sI`). Commit with `commit` in that repo.

### S8 — iOS: prepare on Ubuntu, build and upload on a Mac → gate G4

Follow `references/ios-release-runbook.md`, skipping every `asc` step (hard rule 12). In short:
1. `flutter-ios-release` (prep-report exit 0); copy `templates/build-ios.sh` →
   `scripts/build-ios.sh`, `templates/ExportOptions.plist` → `ios/ExportOptions.plist`; write
   `docs/IOS-BUILD-ON-MAC.md` and `docs/APP-STORE-CONNECT.md` (bundle id, IAP product ids and
   prices from DESIGN.md, Support/Privacy URLs from S7, review notes, web-UI checklist). Commit.
2. *(Deferred, hard rule 13.)* Human in the App Store Connect web UI: register the bundle id,
   create the app record and the IAPs from `docs/APP-STORE-CONNECT.md`. On a Mac:
   `TEAM_ID=… scripts/build-ios.sh upload`. Human reports when the build shows VALID in TestFlight.
3. *(Deferred, hard rule 13.)* TestFlight with a Sandbox account: buy, cancel, reinstall,
   restore; IAP review screenshot.
4. `appstore-assets` (en-US; iPad set only if iPad is targeted) and `aso-marketing` (en-US)
   write `store/` (screenshots, name, subtitle, keywords, description); the human pastes them
   into the web UI, plus age rating and category from the checklist.
5. `appstore-review-checker` on the source, the iOS project and `store/` (the build too, once
   steps 2–3 are done). **G4**: human reads the report and approves the package; with steps 2–3
   still deferred, G4 approves everything except the build and is noted as partial.
6. Waits for the deferred steps 2–3. `/ship --no-auto` (version bump, changelog, tag, push; asks per step) → human uploads the
   release build from the Mac and submits in the web UI ("Add for Review" with the first IAP).
   Record in status.md, commit.

### S9 — Landing polish and follow-up

- In the site repo: `search-optimizer`, then `design-optimizer`; store badges and links once
  the app is live. Commit; Pages redeploys on push.
- After launch: the human reads reviews and analytics in App Store Connect (no `asc`, hard rule
  12) and passes findings back; file them as issues.

## Final report (end of each session)

Stage reached, gates passed with dates, commands run and their exit codes, fallbacks, open
assumptions, what the human must do next (record, approve, build on the Mac). Tick boxes in
`.clone/status.md` and commit it. Once S9 is done, `steps_pane.py close <repo>`; before that
leave the pane open.

## Files in this skill

| Path | Use |
|---|---|
| `PROCESS.md` | Vietnamese one-page process for people |
| `references/spec-template.md` | SPEC skeleton and evidence rules (S1) |
| `references/differentiation-gate.md` | similarity checklist, hard "no" list (S2, S4, S8) |
| `references/economy-and-monetization.md` | fail state, boosters, IAP, ads, analytics (S2, S5) |
| `references/ios-release-runbook.md` | Ubuntu prep + Mac build/upload (S8); its `asc` commands are deferred by hard rule 12 |
| `scripts/contact-sheet.sh` | recording → timestamped contact sheets and strips (S1) |
| `scripts/steps_pane.py` | steps pane in herdr, redrawn from status.md: `open`, `close`, `once` (all stages) |
| `templates/status.md` | `.clone/status.md` starter |
| `templates/build-ios.sh`, `templates/ExportOptions.plist` | Mac archive/export/upload kit (S8) |
| `templates/privacy.html`, `templates/support.html` | App Store privacy and support pages (S7) |
