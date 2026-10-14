# Changelog

## 1.6.0 — 2026-10-14

- Hard rule 13: the Apple-account steps of S8 (App Store Connect web setup, Mac build and upload,
  TestFlight test) are deferred by default and listed under `## Deferred (human)` in status.md;
  the run continues with store assets, ASO, the review check and S9 site work, and only ship,
  release upload and submission wait for them. G4 can pass as partial without a build.

## 1.5.0 — 2026-10-14

- Hard rule 12: `asc` is deferred. The agent runs no `asc` command; S8 writes
  `docs/APP-STORE-CONNECT.md` (bundle id, IAP ids and prices, URLs, review notes, checklist) and
  `store/` for the human to enter in the App Store Connect web UI. S9 review/analytics follow-up
  is read by the human. The runbook keeps its `asc` commands behind a deferral banner.

## 1.4.0 — 2026-10-14

- Hard rule 11: no GitHub Actions anywhere. No `.github/workflows/` in the game or site repo, no
  CI job; checks run on the dev machine (analyze, test, simulator, pre-commit hooks).
- S6 passes the rule to `codebase-modernizer`, so a missing CI is no longer a finding and the plan
  never schedules a workflow task (this run had added `ci.yml`, which the account could not run).
- S7 enables GitHub Pages from the `main` branch with `gh api` instead of a workflow;
  `templates/pages.yml` is removed. The site repo is public so Pages stays free.

## 1.3.0 — 2026-10-13

- S1 takes whatever the human has, one source being enough: APK (REA), game data files in the
  new git-ignored `.clone/data/`, a gameplay video of any length (short clips replace the 30–60
  min session), store pages the agent fetches, or a written description. A precedence rule
  settles conflicts (video > data > APK > description) and ❓ requests ask for the cheapest
  missing piece.
- Ideas with no original are in scope: S0 picks the 1–3 closest successful games as references,
  confirmed at G0, and SPEC and the differentiation gate compare against them. The skill
  description no longer sends such ideas to flutter-factory.
- `.gitignore` entries for `.clone/` are added at S0, since the human may hand files over at the
  start; status.md template carries the reference games and evidence sources.
- Skill description cut to 1,019 characters (it was 1,118, over the 1,024 limit).

## 1.2.0 — 2026-10-13

- Steps pane: `scripts/steps_pane.py open <repo>` splits the agent's herdr pane and shows S0–S9
  on the right (done ✓, current ▶, gate passed ✓, waiting on the human ⏸), redrawn whenever
  `.clone/status.md` changes; it reuses an open pane, and `close` removes it. Without herdr,
  `once` prints the same block for the chat.
- `status.md` gains `Now:` and `Waiting on:` lines; hard rule 10 has the agent keep them current.

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
