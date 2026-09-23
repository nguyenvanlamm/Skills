# Review checklists

One checklist per review point. The orchestrator pastes the relevant block
verbatim into the reviewer prompt (`reviewer-prompt.md`). A reviewer answers
every line as `- [pass] …` / `- [fail] …` / `- [n.a.] …` under
`## Checklist results` and turns every `[fail]` into a numbered finding —
`review-verdict.sh` rejects a report with more `[fail]` lines than findings.

## Markers

| Marker | Meaning |
|--------|---------|
| **[E]** | Evidence-required: a `pass` must quote the file:line, command output or `verify.json` step that proves it — otherwise the line counts as `fail`. These are the lines a reviewer is most likely to tick by habit. |
| **[lens]** | Panel ownership (`panel_stages`). A panel member answers its own lens lines in full; lines of another lens may be `n.a.` unless something is obviously wrong. Untagged lines belong to every member. Lenses: `sec` `cor` (qa) · `feas` `fit` (architecture) · `use` `cons` (design). |
| **(self)** | Self-checklist: no reviewer — the orchestrator answers it and records the result in the stage artifact. |
| `→ file` | Where the evidence for an **[E]** line normally lives in `artifacts/<stage>/evidence/` (built by `scripts/evidence-pack.sh` and by sibling skills the orchestrator ran). The reviewer cites it, then confirms the `file:line` in the source itself — evidence files are inputs, never verdicts. Missing file → answer the line by reading the code, and say so. |

Scope: approved upstream artifacts are context, not subject. A defect found
there → ESCALATE naming the upstream artifact, never a REVISE of this stage.

## Severity scale (shared)

| Severity | Meaning | Effect on verdict |
|----------|---------|-------------------|
| `critical` | Violates the constitution or a `DECISION-*`, ships a security hole, or makes the stage unusable downstream | **BLOCK** if unfixable in this stage, else REVISE |
| `major` | The stage does not fully do its job — a later stage would have to guess | REVISE |
| `minor` | Quality issue that does not mislead later stages | may still APPROVE (list under "Nits") |

Verdict rule: any `critical` → BLOCK or REVISE (reviewer decides whether a
revision can fix it); any `major` → REVISE; only `minor` → APPROVE with
nits. ESCALATE only when the artifact is fine but the reviewer cannot decide
without the user (conflicting constitution vs PRD, missing business input).

---

## idea

- [ ] Problem statement names **who** has the problem and **when** it occurs.
- [ ] Target user is one segment, not "everyone".
- [ ] MVP feature list has **3–6** items; each is a user-visible outcome.
- [ ] Extended / Future features are separated from MVP.
- [ ] At least one alternative or competitor is named with what this idea does differently.
- [ ] Feasibility for a solo Flutter build is stated (offline-first? backend required? third-party APIs with keys?).
- [ ] One measurable success signal for the MVP (e.g. "user logs 5 expenses in week 1").
- [ ] Data sensitivity named: does it touch health, finance, location, children, contacts? (drives privacy, store policy, `store_bound`).
- [ ] No feature depends on content the project has no right to use (brand names, copyrighted media, scraped data).
- [ ] `## Assumptions` lists every gap the author filled — including "UI language: English (default); additional locales: …".
- [ ] Nothing in the idea contradicts `constitution.md`.

## planning

- [ ] Every MVP feature in `idea.md` maps to ≥ 1 requirement in `prd.md`; no requirement lacks a source feature.
- [ ] Each requirement has an acceptance criterion someone could test by hand.
- [ ] Non-functional requirements present: offline behaviour, performance budget, min OS versions, accessibility baseline, locale/language — English is the default locale; any other locale is listed as additional, with a task that adds its ARB.
- [ ] Data model sketch: entities, key fields, relationships — enough for architecture to pick persistence.
- [ ] External dependencies listed with their cost: APIs needing keys, backend, accounts, paid services — and what happens when each is unavailable.
- [ ] Risks section: top 3 with mitigation or explicit acceptance.
- [ ] Test strategy stated: what is unit / widget / flow tested (primary flow as a headless widget flow test in `test/flows/`; device `integration_test/` optional); coverage target as a number (it becomes `--min-coverage`).
- [ ] **[E]** `tasks.json` validates against `tasks-schema.md` (ids unique, `depends_on` acyclic, every task has `verify`).
- [ ] Task 1 is the scaffold; no task edits code before it.
- [ ] UI polish (`skill: flutter-ui-revamp`) depends on every screen task; nothing runs after it except the iOS kit task. Its `files` include the app shell, router, `lib/l10n/**`, `assets/**`, `pubspec.{yaml,lock}` and `test/**`; its `verify` matches `release_build` and `env.md` (`tasks-schema.md` rule 9).
- [ ] `ios_release: true` → T01 creates `ios/`, and the last task is the iOS kit (`skill: flutter-ios-release`, `files` = `ios/**`, `ios-release/**`, `.gitignore`, depends on UI polish) (`tasks-schema.md` rule 10).
- [ ] Each task is ≤ ~1 day of work and touches a bounded `files` set.
- [ ] Tasks marked `parallel_safe: true` have pairwise-disjoint `files`.
- [ ] Task order respects data flow: models → repositories → state → screens.
- [ ] Out-of-scope section exists and matches idea's Extended/Future.

## design

Lenses: `use` = usability & flows · `cons` = consistency, tokens, a11y.
Methodology (read if present, apply as an extension of the `[use]` lines):
`dont-make-me-think/references/krug-principles.md`; evidence, if the
orchestrator ran the skill on `ux.md`/`ui.md`: `evidence/dmmt-report.md`.

- [ ] **[use]** `ux.md`: one flow per MVP feature from app open to visible result; every flow ends in a success state.
- [ ] **[use]** `states.md`: every list/detail/form screen has **loading, error, empty** defined (text + action).
- [ ] **[use]** Navigation pattern is named and matches screen count (bottom bar ≤ 5 destinations); back behaviour defined for every screen.
- [ ] **[use]** Destructive actions (delete, sign out) have confirmation or undo.
- [ ] **[use]** Don't-Make-Me-Think pass: no screen needs explanation to be used; primary action is visually first.
- [ ] **[use]** Responsive: breakpoints stated (compact < 600 dp, medium 600–1200, expanded ≥ 1200) and each screen says what changes — or the app is declared phone-only in a `DECISION-*`.
- [ ] **[cons]** `design-system.md`: colour tokens, type scale, spacing, radius, elevation — no raw hex in `ui.md`.
- [ ] **[cons]** `design-system.md` opens with `style: <minimal-modern | playful-rounded | neo-brutalism | casual-game | dark-premium>` and `seed: #RRGGBB`; tokens below are consistent with that recipe (these two lines drive `flutter-ui-revamp` at the last implementation task).
- [ ] **[cons]** Light + dark palettes; body-text contrast ≥ 4.5:1 stated or computed.
- [ ] **[cons]** Touch targets ≥ 48 dp; text scales with system font size; icon-only buttons have a semantics label.
- [ ] **[cons]** All copy in `ui.md`/`states.md` is written in English (the default locale) and consistent (same verb for the same action everywhere); translations, if any, are a separate section keyed by the English string.
- [ ] **[cons]** Assets: icon set / fonts / illustrations named with their **upstream** licence (not the pub package's); none require attribution the app does not give; the icon set's Flutter package exposes const `IconData` (or the design says a widget refactor is budgeted); the app icon source is not under a no-logo licence (Remix Icon).
- [ ] Nothing requires a component the architecture stage could not build in Flutter without a paid package.

## architecture

Lenses: `feas` = buildability & dependencies · `fit` = constitution/PRD fit & simplicity.

- [ ] **[fit]** Each `DECISION-*` names alternatives considered and why they lost.
- [ ] **[fit] [E]** `org` decision present, reverse-domain, not `com.example` / placeholder.
- [ ] **[fit]** State management, routing and persistence each decided once — no "either/or".
- [ ] **[fit]** No layer (domain/use-case/DI) the PRD cannot justify.
- [ ] **[fit]** `folder-structure.md` is feature-first and matches `tasks.json` `files` paths.
- [ ] **[fit]** Every PRD non-functional requirement (offline, perf, locale) has a named mechanism.
- [ ] **[fit]** Localisation: `flutter gen-l10n` with `lib/l10n/app_en.arb` as template, `en` first in `supportedLocales`; additional ARBs only for locales the PRD lists; no user-facing string literals outside ARB.
- [ ] **[feas]** Dependency table: package · why · what breaks without it. Every `pubspec` package has a row; each is null-safe, maintained, and licence-compatible.
- [ ] **[feas]** minSdk / targetSdk / Dart SDK constraints stated and compatible with `env.md`.
- [ ] **[fit] [E]** `ios_release: true` → an iOS `DECISION-*` fixes bundle id (not `com.example`), team id or "provided at build time", device family (iPhone-only unless the PRD needs iPad), deployment target, and the encryption-exemption answer.
- [ ] **[feas]** Platform-specific code has a named home (`lib/core/platform/`) or is declared absent.
- [ ] **[feas] [E]** Secrets/config path: `--dart-define` or env file, never Dart literals; `.gitignore` entries listed.
- [ ] **[feas]** Error handling strategy: how failures surface from repository → state → UI; what is logged, what is never logged (user data).
- [ ] **[feas]** Offline / sync strategy matches the PRD (local-first? queue? none) and local DB has a migration plan.
- [ ] **[feas]** Test seams: every repository/service is an interface with a fake; time and randomness are injectable.
- [ ] **[feas]** `coding-rules.md` is enforceable by `analysis_options.yaml` where possible (lints named); CI runs analyze + test.

## test

- [ ] **[E]** `verify.json` in `artifacts/test/` shows `analyze: ok` and `test: ok`, `dirty: false`, and `tests.failed: 0`; quote `tests` and `git_sha`.
- [ ] **[E]** Unit tests exist for every model, validator and repository.
- [ ] Widget tests cover each design-system component and each form (valid + invalid input).
- [ ] Loading / error / empty states each have a widget test.
- [ ] **[E]** A flow test in `test/flows/` drives the primary flow from `ux.md` end to end with fakes (headless — the gate runs it). `integration_test/` is optional; its `skipped_env` row is not a fail.
- [ ] Edge cases: empty input, max length, offline/failed repository, rapid double-tap.
- [ ] Unit tests hit no real network, file system or clock — fakes/injected `Clock` only.
- [ ] No flaky patterns: `pumpAndSettle` on screens with infinite animations, real `Future.delayed`, order-dependent tests.
- [ ] No test asserts on implementation details (private method names, exact widget tree depth).
- [ ] **[E]** Coverage meets the PRD target (or a `DECISION-*` lowers it with a reason): quote `coverage.percent` (and `coverage.min` if the gate enforced it) from `verify.json`.
- [ ] `report.md` lists counts (unit/widget/flow, matching `verify.json` `tests`), skipped tests with reasons, and any flaky test.

## qa

Read the project source, `artifacts/test/report.md`, `artifacts/test/verify.json`,
and everything in `artifacts/qa/evidence/` (`index.json` lists what was produced).
Lenses: `sec` = security & data · `cor` = correctness, performance, fidelity.

Methodology (read if present): `code-review/references/review-mode.md`,
`code-review/references/code-smells.md`. Evidence from skills the
orchestrator ran: `evidence/code-review-report.md` (findings to confirm,
not to copy), `evidence/compliance-report.json` (`flutter-store-compliance`,
only when `store_bound`).

### Correctness `[cor]`
- [ ] **[cor] [E]** No `BuildContext` used after an `await` without a `mounted` check; no `setState` after dispose. `→ patterns.txt` §context-after-await, `code-review-report.md`
- [ ] **[cor] [E]** No unawaited futures (`unawaited()` or awaited); no `!` null-assert without a preceding guard. `→ patterns.txt` §null-assert, §unawaited; `analyze.txt` (`unawaited_futures` lint)
- [ ] **[cor]** Providers/controllers/streams/`TextEditingController`s are disposed; `autoDispose` where appropriate.
- [ ] **[cor]** List index math, empty-list paths and pagination boundaries handled.
- [ ] **[cor]** Dates use explicit time zones/locale; money is not a `double`. `→ patterns.txt` §double-for-money
- [ ] **[cor] [E]** Every list/detail/form screen renders loading, error, empty via the shared components. `→ patterns.txt` §CircularProgressIndicator
- [ ] **[cor]** Forms validate at the form **and** the repository; error messages are localised strings (from ARB, English default), not exceptions.
- [ ] **[cor]** No hardcoded user-facing text in `lib/` outside `l10n/`; `app_en.arb` is complete (every key used) and `en` is the first supported locale.

### Performance `[cor]`
- [ ] **[cor]** No heavy work in `build()`; lists use `.builder`; images sized/cached; `const` constructors where possible.
- [ ] **[cor]** Parsing/crypto/large JSON > ~16 ms runs in an isolate (`compute`).
- [ ] **[cor]** Providers are scoped so a keystroke does not rebuild the whole screen.

### Security & data `[sec]`
- [ ] **[sec] [E]** Secrets grep clean. `→ secrets.txt` (must be empty), `verify.json` step `secrets`
- [ ] **[sec] [E]** Tokens/credentials only in `flutter_secure_storage`; nothing sensitive in `shared_preferences` or logs. `→ patterns.txt` §SharedPreferences, §print; `deps.txt` (is `flutter_secure_storage` even present?)
- [ ] **[sec]** No `http://` outside debug; certificates not disabled (`badCertificateCallback`). `→ patterns.txt` §http, §badCertificateCallback
- [ ] **[sec]** No `print`/`debugPrint`/`log` of user data or tokens in release paths. `→ patterns.txt` §print
- [ ] **[sec] [E]** `AndroidManifest.xml`: every permission traces to an MVP feature; `android:exported` set explicitly on every component; `usesCleartextTraffic` not `true`; no `android:debuggable`. `→ manifest.txt`, `compliance-report.json`
- [ ] **[sec]** Release build has R8/minify enabled or a `DECISION-*` says why not. `→ gradle.txt`
- [ ] **[sec] [E]** `flutter pub outdated` shows no dependency with a known advisory; discontinued packages flagged. `→ outdated.json`
- [ ] **[sec]** Deep links / intent filters validate their input. `→ manifest.txt` §intent-filter data
- [ ] **[sec] [E]** Asset licences: every file under `assets/` (fonts, icons, illustrations, animations, audio) has a row in `assets/CREDITS.md` with source + licence; none is GPL / CC-BY-NC / all-rights-reserved / no-licence / third-party IP; the licence recorded is the **upstream** art's, not the pub wrapper's; CC BY-SA assets are unmodified; no Remix Icon glyph in the launcher icon, splash or store icon; every attribution-required asset has a visible credit (`showLicensePage` or an About screen) and bundled fonts are registered in `LicenseRegistry`. `→ assets/CREDITS.md`, `evidence/revamp-report.md`
- [ ] **[sec]** Store policy (only when `store_bound: true`) — `flutter-store-compliance` output referenced; its BLOCK rows are `critical` here.

### iOS `[sec]` (only when `ios_release: true`)
- [ ] **[sec] [E]** `ios_prep_check.py` overall is not `BLOCK`; every `WARN` is either fixed or named in `report.md`/notes. `→ evidence/ios-prep.json`
- [ ] **[sec] [E]** Every `NS*UsageDescription` traces to an MVP feature and says why in English; no permission key without a feature behind it. `→ ios.txt` §Info.plist, `ios-prep.json` `usage_strings*`
- [ ] **[sec]** `PrivacyInfo.xcprivacy` data declarations match what the app actually collects (accounts, analytics, crash reports, location) — nothing collected but undeclared. `→ ios.txt` §privacy manifest
- [ ] **[sec]** `appstore-review-checker` FAIL rows (e.g. 4.8 Sign in with Apple with third-party login, 5.1.1(v) in-app account deletion when accounts exist, 2.1 completeness) confirmed in the code become `critical`/`major` findings. `→ evidence/appstore-review.md`

### Fidelity & clean code
- [ ] **[E]** Architecture fidelity: folder layout and packages match `architecture.md`; every deviation has a `DECISION-*`.
- [ ] Design fidelity: screens use tokens from `design-system.md`, not raw values.
- [ ] **[E]** `flutter analyze` clean incl. infos; no `// ignore:` without a reason comment. `→ analyze.txt`, `patterns.txt` §ignore, `verify.json` step `analyze`
- [ ] No dead files, unused dependencies, or duplicated business logic across features. `→ deps.txt` vs imports; `code-review-report.md`; `code-smells.md` as method
- [ ] No feature imports another feature's `presentation/`; platform imports confined to `core/platform/`.
- [ ] `README` says how to run, test and build with the required `--dart-define`s.

Findings **must** be numbered `F-01 …` with `file:line`, severity, and a
one-line fix hint — the bugfix loop maps each one to a change.

---

## implementation — per task (self)

Answered by the orchestrator after every task, recorded as a line in
`artifacts/implementation/tasks-log.md` (`T04 · ok · <commit>`).

- [ ] `verify-gate --no-test` for this stage is `ok` (analyze clean).
- [ ] `task.verify` command exited 0.
- [ ] Changed files (`git diff --name-only`) fall inside the task's `files` globs; anything outside is either moved to the right task or recorded as a nit.
- [ ] No new `pubspec` dependency without a row in the architecture dependency table (add the row + `DECISION-*` if it is new).
- [ ] No secret literal introduced (grep the diff).
- [ ] New user-facing strings went into `app_en.arb` (English), not into widget code; identifiers and comments are English.
- [ ] Commit message `feat(<feature>): <title> [<id>]`, written in English; `pipeline-state.sh set task.<id> done`.
- [ ] T01 only: `pipeline-state.sh init --project <dir>` re-run (`project_dir` set, `.pipeline/` excluded); no nested git repo when the workspace is already a repo.
- [ ] Parallel mode: task ran in its own worktree `../wt-<id>` on `task/<id>`; merged in id order, gate re-run after the merge, worktree removed and branch deleted.
- [ ] UI-polish task (`flutter-ui-revamp`): every package it added has a dependency-table row + `DECISION-*`; `unmapped`/`DROPPED`/`COLLISION` lines from its icon scripts resolved; widget tests using old icon finders updated; `ui-revamp/*` merged as `feat(infra): <title> [<id>]` with `.revamp/` untracked; revamp report + audit copied to `artifacts/implementation/evidence/`.
- [ ] Last task: `verify-gate --no-test --stage implementation` re-run on the final committed tree (`dirty: false`, `git_sha` = HEAD).

## bugfix cycle (self)

Answered before re-running the QA review; recorded at the top of
`bugfix/fix-NNN.md`.

- [ ] Every `F-nn` from the QA Findings table has a row: finding → change → file(s) → how verified. None skipped silently; "won't fix" needs a `DECISION-*` and is reported as such.
- [ ] Fixes stay inside the finding's scope — no unrelated refactors mixed in.
- [ ] No new dependency without a dependency-table row.
- [ ] A regression test was added for every `critical`/`major` bug fix.
- [ ] Fix commit message in English — `fix(<feature>): <summary> [F-nn, …]`.
- [ ] Fixes committed first, then `verify-gate --stage test --coverage` is `ok` on that commit (`dirty: false`); `verify.json` path recorded.
- [ ] `bugfix_cycles` bumped; the next QA prompt receives this cycle's Findings table as `previous_findings`.

## release (self)

Answered before tagging; recorded in `artifacts/release/notes.md` §2.

- [ ] `pubspec.yaml` version bumped (semver + build number) and committed as `chore(release): v<version>` (English) **before** the gate; tag `v<version>` does not already exist.
- [ ] `verify-gate --build <release_build> --release` is `ok` on that commit — analyze, test, build, `app_id`, `secrets` all `ok` (or `skipped_env` with a reason the user accepted); `dirty: false`, `git_sha` = HEAD.
- [ ] Every earlier stage was left via `advance` (events.log shows `advance <stage>→…` for each; any `OVERRIDE` line is listed in §6); latest `qa-vN.md` is APPROVE.
- [ ] On the intended branch; `git log` shows no non-English commit from this run.
- [ ] `notes.md` filled from `verify.json`, `state.yaml`, `events.log`, `reviews/`, `tasks.json` only (a project `CHANGELOG.md`, if any, went into the release commit from `tasks.json` + `reviews/`).
- [ ] `notes.md` §6 lists every blocked task, unresolved finding and `OVERRIDE` — nothing dropped.
- [ ] Human gate asked with notes path + version, answered `approved`, **then** `git tag v<version>`, then `pipeline-state.sh advance`.
- [ ] `ios_release: true` → the release gate ran with `--check ios_kit=…` and it is `ok`; `ios-release/` is in the tagged commit; notes §2 says "iOS: ready to build on a Mac", never "IPA built", and §7 lists `bash ios-release/build-ios.sh` + the one-time Apple setup from `ios-release/README.md`.
- [ ] `notes.md` §7 hands off to `flutter-signing → flutter-build → flutter-store-metadata → flutter-store-compliance → flutter-publish`.
- [ ] Push only if the user asked; otherwise the report says "not pushed".
