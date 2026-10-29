# Clone status: {{GAME_NAME}} (clone of {{REFERENCE_GAMES}})

Written by the game-clone-pipeline skill. Resume from the first unchecked stage.
Reference: {{STORE_URLS}} · Repo: {{REPO_URL}} · Landing: {{SITE_REPO_URL}}
Evidence: {{SOURCES}}  <!-- what the human has: APK, data files, video, description -->
Remote: Telegram {{off|on}}  <!-- on when ~/.config/game-clone-pipeline/telegram.env exists; here/away lives in .clone/telegram/mode -->

<!-- For an idea with no original: REFERENCE_GAMES = "idea; refs <closest hits>", confirmed at G0. -->

Now: S0 · idea-validator
Waiting on: —
<!-- Waiting on: only while the run stops for the human (rule 10); deferred steps go under Deferred (human). -->
<!-- Parked with only the Apple steps left: "Now: S8 · 6 waiting for the Apple steps" + "Waiting on: S8-apple: build VALID + Apple ID". -->

## Stages

- [ ] S0 Pick the game (or idea) and its reference games: idea-validator report, Flutter-2D fit, twist hypothesis → **G0**
- [ ] S1 Evidence from what the human has (APK via REA, data files, video, store pages, description) → `SPEC.md` → **G0b**
- [ ] S2 Differentiation + economy in `DESIGN.md`, name cleared by brand-name-checker → **G1**
- [ ] S3 Core in Flutter: pure-Dart rules, tests, bot, `tool/simulate.dart`, pre-commit gate (`tool/check.sh`); analyze + test exit 0
- [ ] S4 UI: 3 directions (huashu-design) → chosen → built in Flutter (mockup-to-flutter) → icon (logo-designer) → **G2**
- [ ] S5 IAP + Restore from `templates/store/`, booster rules, analytics decision, human playtest, re-tune → **G3**
- [ ] S6 codebase-modernizer → plan-to-issues → issues fixed, PRs merged, branches deleted; analyze + test exit 0
- [ ] S7 Landing repo with privacy + support pages live on Pages
- [ ] S8 iOS: only `main` left → flutter-ios-release + docs/APP-STORE-CONNECT.md → human web setup + Mac build/upload → TestFlight → store assets/ASO → review-checker → **G4** → ship + submit (no `asc`, rule 12)
- [ ] S9 Landing polish: search-optimizer, design-optimizer on this site (store badge and post-launch checks wait under Deferred)

## Gate log

| Gate | Date | Decision | Notes |
|---|---|---|---|
<!-- Notes: where the human decided, `tại máy` or `via Telegram` -->

## Deferred (human)

<!-- Human steps postponed by rule 13 (App Store Connect web setup, Mac build, TestFlight) and post-launch items.
They never fill `Waiting on:`; the run goes on with everything else. -->

## Fallbacks and deviations

| Stage | Skill missing or skipped | What was done instead |
|---|---|---|

## Assumptions (open ❓ carried from SPEC)

-
