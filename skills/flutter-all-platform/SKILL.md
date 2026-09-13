---
name: flutter-all-platform
description: "Orchestrator: turn a natural-language app idea into a real, buildable Flutter project for Web + Android + iOS. Analyzes the idea, plans architecture and responsive UI, discovers and delegates to existing skills (flutter-init, frontend-design, firebase-auth-setup, test-coverage, code-review, flutter-build, ...) and does the work itself when a skill is missing, then verifies with analyze/test/build per platform and reports honestly what was and was not built. Use when the user says 'build a Flutter app for web and mobile', 'tạo app Flutter đa nền tảng', 'flutter all platform', 'app chạy web + android + ios'. Don't use for Android-only Play Store pipelines (idea-to-play-store), scaffolding alone (flutter-init), UI refresh of an existing app (flutter-ui-revamp), or non-Flutter stacks."
license: MIT
effort: max
metadata:
  version: 1.0.0
  author: "Nguyen Van Lam"
---

# Flutter All-Platform App Builder

Orchestrator that takes **an idea in plain language** and leaves behind **a Flutter project that compiles and builds for Web, Android and iOS** — with tests, a design system, isolated platform code, and a platform compatibility report.

## Core principle

> **Delegate what a sibling skill already does; do the rest yourself; never stop because a skill is missing.** This skill owns the pipeline, the decisions, and the final report. Sibling skills own the work they specialise in. When no sibling exists for a capability, this skill implements it inline — a missing skill lowers the ceiling, it never blocks the run.

Three consequences:

- **Analyse before coding.** No `flutter create` until the idea has a feature list, user flows, a platform matrix and a tech decision table.
- **≥ 90 % shared Dart.** Platform-specific code lives behind an interface in one folder. Nothing else imports `dart:html`, `dart:io` conditionally, or a platform channel.
- **Report only what was verified.** ✅ means the command ran and exited 0 in this session. A platform the environment cannot build (iOS without Xcode) is ⚠️ *configured, not built* — never ✅, never "should work".

## Input

Anything. One sentence is enough:

> "Tôi muốn làm một ứng dụng quản lý chi tiêu cá nhân: thêm khoản chi, phân loại, xem thống kê, xuất báo cáo."

Do **not** ask the user to complete a brief before starting. Fill gaps with reasonable assumptions and write every assumption to `docs/ASSUMPTIONS.md`. The only question worth asking up front is the reverse-domain `org` (see Phase 4) — it is the single decision that becomes permanent.

## How sibling skills are used

Discover, don't assume. Before each phase, check for the capability with the skill tool (`search` with keywords, or attempt the invocation). Never probe filesystem paths to decide whether a skill exists. `/name` below describes intent, not a CLI — invoke through the host's skill mechanism and pass the values in the prompt.

| Capability | Prefer (if present) | If absent, do inline |
|------------|--------------------|----------------------|
| Idea validation, PRD, TAD, tasks | `idea-validator`, `prd-generator`, `tad-generator`, `tasks-generator` | Phase 1 analysis written to `docs/` |
| Project scaffold + toolchain | `flutter-init` | `flutter create --platforms web,android,ios`, pin SDK levels (`references/architecture.md`) |
| Brand / logo | `logo-designer` | Material icon + generated launcher icons |
| UI/UX design | `frontend-design` | Design system in `references/design-system.md` |
| Auth | `firebase-auth-setup` | Local auth abstraction with a fake + secure_storage token |
| Backend + DB | `deploy-render` (FastAPI) | Local-first: drift/sqflite + `shared_preferences`; repository interface ready for a remote impl |
| Security hardening | `security-setup` | Phase 8 checklist in `references/platform-checklists.md` |
| Tests | `test-coverage` | Unit + widget + one integration test (Phase 7) |
| Code review | `code-review` | Self-review against Phase 9 checklist |
| Android release build / signing | `flutter-build`, `flutter-signing` | `scripts/build-all.sh` (debug-signed apk/aab) |
| CI | `devops-pipeline` | `.github/workflows/flutter.yml` running analyze/test/build web |
| Docs | `doc-manager` | `README.md` + `docs/` written by hand |
| Store follow-ups (not run here) | `flutter-store-metadata`, `flutter-store-compliance`, `flutter-publish`, `appstore-review-checker` | Listed under "Next steps" only |

Contract notes learned from the installed siblings:

- `flutter-init` accepts `platforms` as `android`, `ios` or both — **web is not in its contract**. After it finishes, run `flutter create --platforms web .` inside the project to add the `web/` folder, then re-run `flutter analyze`.
- `flutter-build` is **Android-only** and expects `android/key.properties` from `flutter-signing`. For this skill's verification pass use `scripts/build-all.sh` (unsigned/debug-signed artifacts are enough to prove buildability); hand off to `flutter-signing → flutter-build` when the user wants a Play upload.
- Planning skills (`idea-validator`, `prd-generator`, `tad-generator`, `tasks-generator`) run a mandatory `git pull --rebase` and stop if `origin` is missing. Always add to their prompt: *"local git repo with no remote — skip Repo Sync, commit locally, do not push."*

## State

`$PROJECT_DIR/.flutter-all-platform-state.json`, written after every phase:

```json
{
  "app_name": "Spendly", "slug": "spendly", "org": "com.acme", "application_id": "com.acme.spendly",
  "phase": 6, "skills_used": ["flutter-init", "frontend-design"], "skills_missing": ["test-coverage"],
  "platforms": { "web": "pending", "android": "pending", "ios": "pending" },
  "assumptions": 7, "updated_at": "2026-09-13T10:00:00Z"
}
```

On start, if the file exists offer **resume from `phase`** or start over in a new directory. Never delete an existing project directory without a fresh, explicit yes.

## Pipeline

```
Phase 0  Environment        scripts/check-env.sh → which platforms this machine can build
Phase 1  Analyse            product · features (MVP/extended/future) · user stories · user flows
Phase 2  Platform matrix    every feature → Shared / Web / Android / iOS
Phase 3  Architecture+Tech  folder layout · dependency table with reasons · design system
Phase 4  Scaffold           flutter-init (or inline) · add web · pin IDs · env config · gitignore secrets
Phase 5  Implement          entry → router → theme → design system → models → repos → state → screens
Phase 6  Platform adapt     web routing/refresh/CORS · AndroidManifest/permissions · Info.plist/pods
Phase 7  Test               unit · widget · integration → flutter test
Phase 8  Security           no secrets in source · secure storage · input validation · HTTPS
Phase 9  Quality audit      analyze clean · no dead code · no unused deps · states (loading/error/empty)
Phase 10 Build validation   scripts/build-all.sh → fix → rebuild (max 3 rounds per step)
Phase 11 Report             references/report-template.md, filled from build-report.json only
```

---

## Phase 0 — Environment

```bash
bash <skill-dir>/scripts/check-env.sh            # table + verdicts + JSON on stdout
```

Reports Flutter/Dart, Chrome (web), Android SDK/JDK, and on macOS Xcode + CocoaPods. Emits one verdict per platform: `buildable` or `blocked: <reason>`. Copy those lines into the state file — they decide, up front, which ✅ are even possible in Phase 10. If Flutter is missing, that is `flutter-init`'s job (Phase 4); do not install it here.

## Phase 1 — Analyse the idea

Write `docs/ANALYSIS.md` before touching Flutter:

1. **Product** — name (propose one; note it as an assumption), purpose, target user, problem, core value.
2. **Features** in three buckets: **MVP** (ships in this run), **Extended** (interface stubbed, not built), **Future** (listed only). Keep MVP to what a first user needs — 3–6 features.
3. **User stories** — `As a <user>, I want <action>, so that <value>` for each MVP feature.
4. **User flows** — one arrow chain per primary story, from app open to the visible result.
5. **Assumptions** — every gap you filled, in `docs/ASSUMPTIONS.md`.

If `prd-generator`/`tad-generator` exist and the user wants a formal PRD, run them here; otherwise this file is the PRD.

## Phase 2 — Platform matrix

Add a table to `docs/ANALYSIS.md`:

| Feature | Shared | Web | Android | iOS | Note |
|---------|--------|-----|---------|-----|------|
| Add expense | ✅ | | | | pure Dart |
| Export CSV | ✅ API | download blob | share sheet | share sheet | one interface, 3 impls |
| Push notifications | | ⚠️ | ✅ | ✅ | Extended — stub only |

Rules: default every feature to Shared; a row only leaves Shared when a platform API forces it. Each non-shared row names the abstraction (`lib/core/platform/<name>.dart`) that hides it.

## Phase 3 — Architecture, tech, design system

Read `references/architecture.md` for the layout and the default stack, then write `docs/ARCHITECTURE.md` containing:

- the folder tree actually used (feature-first; drop layers the app does not need — a 4-screen app does not need `domain/` in every feature);
- a **dependency table**: package · why · what breaks without it. No package enters `pubspec.yaml` without a row. Defaults: `flutter_riverpod`, `go_router`, `freezed`/`json_serializable` only if there is JSON, `drift` or `shared_preferences` by data shape, `flutter_secure_storage` only if there is a token, `intl`;
- the **design system** tokens (colors, type scale, spacing, radius, elevation) and component list (button, input, card, dialog, loading, error, empty). Read `references/design-system.md`; use `frontend-design` if present to pick the visual direction, then still encode the result as tokens in `lib/app/theme/`.

Responsive rules are non-negotiable: breakpoints in one file, `LayoutBuilder`/`MediaQuery` at the layout level, `NavigationBar` < 600 dp, `NavigationRail` 600–1200, extended rail/sidebar ≥ 1200. No hard-coded pixel widths in screens.

## Phase 4 — Scaffold

1. **Ask for `org`** (reverse-domain the user controls). No default: it becomes `applicationId` and iOS bundle identifier, permanent after first publish. Explain once, don't pick for them.
2. `flutter-init` with `project_name=<slug>`, `org`, `platforms=android,ios` (both, even on Linux — the iOS folder must exist for the configuration to be complete). If unavailable: `flutter create --org $ORG --platforms android,ios,web $SLUG` and pin `compileSdk/targetSdk 36`, `minSdk 23`, NDK r28+ per `references/architecture.md`.
3. `cd $SLUG && flutter create --platforms web .` — adds `web/` without touching existing files.
4. Confirm the IDs that were actually written:
   ```bash
   grep -E "applicationId|namespace" android/app/build.gradle*
   grep -A1 PRODUCT_BUNDLE_IDENTIFIER ios/Runner.xcodeproj/project.pbxproj | head -4
   ```
5. Environment config: `lib/core/config/env.dart` reading `--dart-define` values (`API_BASE_URL`, etc.), `.env.example` documenting them, `.env*` in `.gitignore`. **No key, token or secret is ever a Dart literal.**
6. `.gitignore` gets `*.jks`, `*.keystore`, `android/key.properties`, `service-account.json`, `.env*`, `ios/Runner/GoogleService-Info.plist`, `android/app/google-services.json` (the last two only if Firebase is in play).
7. `git init -b main` if not done, first commit `chore: scaffold web+android+ios`.

## Phase 5 — Implement

Order matters — each step must `flutter analyze` clean before the next:

1. `main.dart` → `app/app.dart` (MaterialApp.router, theme, locale)
2. `app/router.dart` — go_router, URL-addressable routes (web refresh must land on the same screen), a `NotFoundScreen`
3. `app/theme/` — tokens from Phase 3, light + dark
4. `core/widgets/` — the design-system components; `AppScaffold` doing the adaptive navigation
5. `core/platform/` — one abstract class per non-shared row from Phase 2, with `*_io.dart` / `*_web.dart` behind a conditional export, plus a `*_stub.dart`
6. Per feature: model → repository (interface + local impl) → Riverpod providers → screens → widgets → forms with validation
7. Every list/detail screen renders **loading, error, empty** states via the shared components — no bare `CircularProgressIndicator` in a screen file

Keep SOLID/DRY, but the smallest structure that works wins. Do not add a `domain/` layer, use cases, or DI containers the app cannot justify. Commit after each feature.

## Phase 6 — Platform adaptation

Work through `references/platform-checklists.md` — web (routing strategy, refresh, CORS note, storage, file download, `index.html` title/manifest/icons), Android (manifest permissions matching the platform matrix, app label, adaptive icon, `INTERNET` if there is an API), iOS (`Info.plist` usage-description strings for every permission, `CFBundleDisplayName`, deployment target ≥ 13.0, Podfile platform line). Every permission added must trace back to a Phase 2 row; delete any the template added that the app does not use.

## Phase 7 — Test

If `test-coverage` exists, invoke it after writing the first tests yourself — it fills gaps, it does not decide structure. Minimum set:

- **unit** — models, validators, repositories (with in-memory fakes), any pure business logic (totals, grouping, formatting)
- **widget** — each design-system component, each form (valid/invalid), `AppScaffold` at 400 / 800 / 1400 px widths, loading/error/empty rendering
- **integration** (`integration_test/app_test.dart`) — the primary user flow from Phase 1, end to end

```bash
flutter test
```

Red → read the failure, fix the cause (not the assertion), re-run. Up to 3 rounds per failing test before recording a blocker.

## Phase 8 — Security

```bash
grep -rniE "(api[_-]?key|secret|password|token|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}" lib/ web/ android/app/src ios/Runner 2>/dev/null
```

Must return nothing. Then: tokens only in `flutter_secure_storage` (web falls back to encrypted `localStorage` — say so in the report); all inputs validated at the form and again at the repository; HTTP client refuses `http://` outside debug; no `print` of user data; if `security-setup` exists, run it for hooks and dependency scanning.

## Phase 9 — Quality audit

`flutter analyze` clean (zero infos too — use `analysis_options.yaml` to enable `flutter_lints`). Then `dart run dart_code_metrics`-style checks by hand: no unused files, no unused dependencies (`flutter pub deps --style=compact` vs imports), no duplicated business logic across features, no screen imports another feature's `presentation/`, all platform imports confined to `core/platform/`. Run `code-review` if present, on the diff since the scaffold commit.

## Phase 10 — Build validation

```bash
bash <skill-dir>/scripts/build-all.sh --project "$PROJECT_DIR"
```

Runs, in order, `pub get → analyze → test → build web → build apk → build appbundle → build ios --no-codesign`, records each as `ok` / `fail` / `skipped_env` with a log path, and writes `build/flutter-all-platform/build-report.json`. iOS is attempted only on macOS with Xcode; elsewhere it is `skipped_env` with the reason — never a failure, never a pass.

On any `fail`:

```
read the log → classify: project · dependency · platform config · environment
project/dependency/platform  → fix → bash scripts/build-all.sh --only <step>
environment                  → record, continue with the remaining steps
```

Three fix-and-rerun rounds per step, then it is a recorded blocker. Never mark a step green from an artifact left by an earlier run — the script deletes stale outputs before each build.

## Phase 11 — Report

Fill `references/report-template.md` **from `build-report.json` and the state file**, not from memory, and save it as `docs/PLATFORM-REPORT.md`. It must contain: overview, implemented features (MVP) vs stubbed (Extended), architecture summary, dependency table, skills used **and skills that were missing and done inline**, per-platform status with the exact command and exit code, remaining blockers, next steps (signing → `flutter-build` → store skills; macOS for iOS build; backend if local-first was chosen). Write it in the user's language.

## Rules

1. Analyse first; no code in the first response to an idea.
2. Search for a skill before implementing a large capability; use it if it exists; do it yourself if not; **never halt on a missing skill**.
3. Design for Web + Android + iOS from the first commit; platform code isolated under `core/platform/`.
4. `org` is asked, never defaulted; secrets never in source.
5. ✅ only for a command that ran and passed now. Environment limits are reported as such, separately from project errors.
6. Build failure → analyse → fix → rebuild; max 3 rounds per step; blocked steps do not stop independent ones.
7. No over-engineering: smallest architecture that stays testable.
8. The deliverable is a project someone can keep developing — with docs, tests, config and an honest report.

## Definition of done

```
<slug>/
├── lib/                    shared Dart ≥ 90 %, platform code in core/platform/
├── web/  android/  ios/    all present and configured
├── test/  integration_test/
├── docs/                   ANALYSIS · ASSUMPTIONS · ARCHITECTURE · PLATFORM-REPORT
├── .env.example            no real values anywhere in the repo
└── build/flutter-all-platform/build-report.json
    web ✅ built · android ✅ apk + aab · ios ✅ built (macOS) or ⚠️ configured, not built
```

## Reference files

| File | Read when |
|------|-----------|
| `references/architecture.md` | Phase 3–4 — layout, default stack with reasons, SDK pins, platform abstraction pattern |
| `references/design-system.md` | Phase 3, 5 — tokens, components, adaptive navigation, breakpoints |
| `references/platform-checklists.md` | Phase 6, 8 — web / Android / iOS / security checklists |
| `references/report-template.md` | Phase 11 — final report skeleton |

| Script | Run at |
|--------|--------|
| `scripts/check-env.sh` | Phase 0 — per-platform buildability verdicts, JSON on stdout, never installs |
| `scripts/build-all.sh` | Phase 10 — analyze/test/build per platform, `--only <step>` to rerun one, writes build-report.json |

## Scope

Does: analyse, plan, scaffold, implement, test, adapt per platform, build-verify, report.

Does not: sign or upload to stores (`flutter-signing`, `flutter-build`, `flutter-publish`, `appstore-review-checker`); deploy a backend unless `deploy-render` is present and the user asks; install Xcode; claim an iOS build on non-macOS.
