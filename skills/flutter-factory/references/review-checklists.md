# Review checklists

One checklist per reviewed stage. The orchestrator pastes the relevant block
verbatim into the reviewer prompt (`reviewer-prompt.md`). A reviewer answers
every line with **pass / fail / n.a.** and turns every *fail* into a numbered
finding.

Lines marked **[E]** are evidence-required: a `pass` must quote the
file:line, command output or `verify.json` step that proves it — otherwise
the line counts as `fail`. These are the lines a reviewer is most likely to
tick by habit (security, "tests exist", "matches architecture").

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
- [ ] `## Assumptions` lists every gap the author filled.
- [ ] Nothing in the idea contradicts `constitution.md`.

## planning

- [ ] Every MVP feature in `idea.md` maps to ≥ 1 requirement in `prd.md`; no requirement lacks a source feature.
- [ ] Each requirement has an acceptance criterion someone could test by hand.
- [ ] Non-functional requirements present: offline behaviour, performance budget, min OS versions, accessibility baseline.
- [ ] **[E]** `tasks.json` validates against `tasks-schema.md` (ids unique, `depends_on` acyclic, every task has `verify`).
- [ ] Task 1 is the scaffold; no task edits code before it.
- [ ] Each task is ≤ ~1 day of work and touches a bounded `files` set.
- [ ] Tasks marked `parallel_safe: true` have pairwise-disjoint `files`.
- [ ] Task order respects data flow: models → repositories → state → screens.
- [ ] Out-of-scope section exists and matches idea's Extended/Future.

## design

- [ ] `ux.md`: one flow per MVP feature from app open to visible result; every flow ends in a success state.
- [ ] `states.md`: every list/detail/form screen has **loading, error, empty** defined (text + action).
- [ ] `design-system.md`: colour tokens, type scale, spacing, radius, elevation — no raw hex in `ui.md`.
- [ ] Light + dark palettes; body-text contrast ≥ 4.5:1 stated or computed.
- [ ] Touch targets ≥ 48 dp; text scales with system font size.
- [ ] Navigation pattern is named and matches screen count (bottom bar ≤ 5 destinations).
- [ ] Copy is in the product's language and consistent (same verb for the same action everywhere).
- [ ] Nothing requires a component the architecture stage could not build in Flutter without a paid package.
- [ ] Don't-Make-Me-Think pass: no screen needs explanation to be used.

## architecture

- [ ] Each `DECISION-*` names alternatives considered and why they lost.
- [ ] **[E]** `org` decision present, reverse-domain, not `com.example` / placeholder.
- [ ] Dependency table: package · why · what breaks without it. Every `pubspec` package has a row.
- [ ] State management, routing and persistence each decided once — no "either/or".
- [ ] `folder-structure.md` is feature-first and matches `tasks.json` `files` paths.
- [ ] Platform-specific code has a named home (`lib/core/platform/`) or is declared absent.
- [ ] **[E]** Secrets/config path: `--dart-define` or env file, never Dart literals; `.gitignore` entries listed.
- [ ] minSdk / targetSdk / Dart SDK constraints stated and compatible with `env.md`.
- [ ] `coding-rules.md` is enforceable by `analysis_options.yaml` where possible (lints named).
- [ ] No layer (domain/use-case/DI) the PRD cannot justify.

## test

- [ ] **[E]** `verify.json` in `artifacts/test/` shows `analyze: ok` and `test: ok` from **this** run.
- [ ] **[E]** Unit tests exist for every model, validator and repository.
- [ ] Widget tests cover each design-system component and each form (valid + invalid input).
- [ ] Loading / error / empty states each have a widget test.
- [ ] **[E]** One integration test drives the primary flow from `ux.md`.
- [ ] Edge cases: empty input, max length, offline/failed repository, rapid double-tap.
- [ ] No test asserts on implementation details (private method names, exact widget tree depth).
- [ ] `report.md` lists counts (unit/widget/integration), skipped tests with reasons, and any flaky test.

## qa

Read the project source, `artifacts/test/report.md`, `artifacts/test/verify.json`.

- [ ] **[E] Bugs** — null-safety escapes (`!`) without a guard; unawaited futures; `setState` after dispose; list index math; timezone/locale assumptions.
- [ ] **[E] Security** — secrets grep clean; tokens only in `flutter_secure_storage`; input validated at form *and* repository; no `http://` outside debug; no `print` of user data.
- [ ] **Performance** — no heavy work in `build()`; lists use builders; images sized; providers not rebuilt per frame.
- [ ] **[E] Clean code** — no dead files/unused deps; no feature imports another feature's `presentation/`; platform imports confined to `core/platform/`; `flutter analyze` clean incl. infos.
- [ ] **Design fidelity** — screens use tokens from `design-system.md`, not raw values; every screen renders its three states.
- [ ] **[E] Architecture fidelity** — folder layout and packages match `architecture.md`; every deviation has a `DECISION-*`.
- [ ] **Store policy** (only when `store_bound: true`) — run or reference `flutter-store-compliance` output; permissions trace to features.

Findings **must** be numbered `F-01 …` with `file:line`, severity, and a
one-line fix hint — the bugfix loop maps each one to a change.
