---
name: idea-to-play-store
description: "End-to-end Flutter app builder: from idea to Google Play. Automates trend research, idea validation, PRD/tasks, brand identity, Flutter code generation (full auto for standard apps), Firebase Auth, backend API, testing, signing, AAB build, store metadata, policy compliance, and publish guide. Use when asked to build a full mobile app from scratch, turn an idea into a published app, or create a Flutter MVP with Google Play submission. Don't use for single-phase work or non-mobile projects."
license: MIT
effort: max
metadata:
  version: 2.1.0
  author: "Nguyen Van Lam"
---

# Idea to Play Store

5-phase orchestrator that takes an idea and produces a Flutter app uploaded to Google Play, ready for the user to submit.

**Stack:** Flutter (Dart, Riverpod, go_router) + Firebase Auth (optional) + FastAPI backend (optional, deployed to Render with PostgreSQL).

## Core principle

> **The orchestrator owns the gates and the state; the sibling skills own the work.** This file never re-implements a check a sibling already performs (compliance, preflight, signing verification). It decides *when* each runs, feeds it the right inputs, reads its machine-readable output, and stops when a gate says stop. A phase report is a copy of what the siblings produced — not a summary written from memory.

Two things follow:

- **Irreversible decisions get a gate.** `applicationId` (permanent after first publish), the upload keystore, the Play track, anything pushed to GitHub or Render. Approval for one is not approval for the next.
- **Nothing is deleted without a fresh, explicit yes.** An "Abort" at a gate stops the run and leaves `$PRODUCT_DIR` on disk with its state file, so the user can resume or delete it themselves. The old behaviour (`rm -rf $PRODUCT_DIR` on abort) threw away an hour of research and any Firebase project id with it.

## How sibling skills are invoked

Commands written as `/skill --flag value` describe **intent**, not a CLI. Invoke each skill through the host's mechanism (skill tool, `/name`, …) and pass the values in the prompt. Contracts below are read from each skill's own SKILL.md — planning files must keep their default names and live in one directory:

| Skill | Reads | Writes |
|-------|-------|--------|
| `trend-ideas` (2.2+) | `output`, `output_dir` | `trend-report.md`, `ideas/…`, **`idea.md` + `validate.md`** of the winner at `output_dir` |
| `idea-validator` | the idea as text. **No output-dir argument** — creates `$IDEAS_ROOT/YYYY_MM_DD_<name>/` and echoes the path | `idea.md` + `validate.md` in that folder |
| `brand-name-checker` | a name (`$ARGUMENTS`) | `RISK:` + `RECOMMEND: Proceed/Modify/Abandon` block |
| `prd-generator` | **folder path** containing `idea.md` + `validate.md` | `prd.md` in that folder |
| `tad-generator` | folder path containing `prd.md` | `tad.md` |
| `tasks-generator` | **file path** to `prd.md`; finds `tad.md` beside it | `tasks.md` beside `prd.md` |
| `flutter-init` | `project_name`, `org`, `platforms` | project dir, `applicationId` |
| `firebase-auth-setup` | `--slug`, optional `--project-id` | `firebase-output.json` with **`auth_providers`** |
| `flutter-build` | project | `build/release/app-release.aab`, `build/release/build-info.json` |
| `flutter-store-metadata` | project + `app_name`, `features`, `category`, `contact_email` | `store-metadata/store-listing.json` (with `unresolved[]`) |
| `flutter-store-compliance` | project + `store-metadata/` | `store-metadata/compliance-report.json → overall` |
| `flutter-publish` | AAB, `track`, `whats_new` | `publish-state.json`, `upload-checklist.md` |

Check availability per phase by attempting the invocation — never by probing a filesystem path. If a phase's skill is missing, stop **before** the phase starts and name it.

**Repo Sync trap.** `idea-validator`, `prd-generator`, `tad-generator` and `tasks-generator` each run a mandatory `git fetch origin && git pull --rebase` before writing, and **stop to ask the user when `origin` is missing**. `$PRODUCT_DIR` has no remote until the user chooses to push. Every planning invocation therefore says in its prompt: *"`$PRODUCT_DIR` is a local git repo with no remote — skip Repo Sync, commit locally, do not push."*

## Prerequisites

| Skill | Phase |
|-------|-------|
| `trend-ideas`, `idea-validator`, `brand-name-checker`, `prd-generator`, `tad-generator`, `tasks-generator` | 1 |
| `logo-designer`, `frontend-design` | 2 |
| `flutter-init`, `firebase-auth-setup` (opt), `deploy-render` (opt), `devops-pipeline` | 3 |
| `code-review`, `test-coverage` | 4 |
| `flutter-signing`, `flutter-build`, `flutter-store-metadata`, `flutter-store-compliance`, `flutter-publish`, `release-manager`, `aso-marketing` (opt) | 5 |

Runtime: Flutter SDK 3.22+ and Android SDK (installed by `flutter-init` if missing), JDK 17, Git configured; Python 3.10+ only if a backend is generated; `gcloud` + `firebase-tools` only if Firebase Auth is used. Linux or macOS. This pipeline targets **Android only** — iOS needs macOS + Xcode and a separate App Store flow, so `flutter-init` is called with `--platforms android`.

## State

`$PRODUCT_DIR/.idea-play-store-state.json` is written after every step and read at start:

```json
{
  "slug": "task_flow", "app_name": "Task Flow", "org": "com.acme", "application_id": "com.acme.task_flow",
  "needs_auth": true, "needs_backend": false, "auth_providers": ["email"],
  "phase": 3, "step": "3b", "gates": { "1": "approved", "2": "approved" },
  "updated_at": "2026-09-13T10:00:00Z"
}
```

On start: if the file exists, offer **resume from `step`** or start over (start over does not delete anything — it uses a new dated directory). Every phase report reads its numbers from this file and the siblings' outputs.

## Setup

1. **Resolve root**: `$PRODUCT_DIR` env → `~/.config/idea-to-play-store-dir.txt` → ask once and save → default `~/workspace/products`.
2. **Create project folder**:
   ```bash
   DATE=$(date +%Y_%m_%d)
   # ${DATE}_${SLUG}, not $DATE_$SLUG — '_' is a valid identifier char, so "$DATE_$SLUG" reads the empty variable "$DATE_".
   mkdir -p "$PRODUCT_DIR/${DATE}_${SLUG}"/{plan,assets,store-metadata}
   export PRODUCT_DIR="$PRODUCT_DIR/${DATE}_${SLUG}"
   ```
   `app/` is created by `flutter-init`; `backend/` only if needed.
3. **Ask for `org`** (reverse-domain the user controls, e.g. `com.acme`). There is no default: it becomes `applicationId = <org>.<slug>`, permanent after first publish, and `flutter-build`/`flutter-publish` block `com.example.*`. Explain the permanence once.
4. `git init -b main` in `$PRODUCT_DIR`. First commit after Phase 1 produces files.
5. Write the state file.

## Workflow

```
Phase 1 — Idea & Plan      trend-ideas (or idea-validator on the user's idea)
                           → brand-name-checker → prd-generator → tad-generator → tasks-generator
                           GATE ⛔ plan
Phase 2 — Brand & Design   logo-designer → frontend-design (mobile mockups)
                           GATE ⛔ brand
Phase 3 — Setup & Backend  flutter-init → [firebase-auth-setup] → [backend + deploy-render] → devops-pipeline
Phase 4 — Build            feature generation → flutter analyze → flutter test → code-review → test-coverage
                           GATE ⛔ running app
                           GATE ⛔ entering Phase 5 (outward-facing)
Phase 5 — Store & Publish  flutter-signing → flutter-build → flutter-store-metadata
                           → flutter-store-compliance (FAIL blocks) → flutter-publish → [aso-marketing] → release-manager
```

---

## Phase 1: Idea & Plan (Gate ⛔)

All files in `$PRODUCT_DIR/plan/`. Pass that directory to each skill; do not pass file contents.

**1a — Idea.** If the user already has an idea: set `IDEAS_ROOT="$PRODUCT_DIR/plan"`, invoke `idea-validator` with the idea as `$ARGUMENTS`; it creates `plan/YYYY_MM_DD_<name>/{idea.md,validate.md}` and echoes the path — copy both files up to `plan/`. Otherwise:

```
/trend-ideas --output "$PRODUCT_DIR/plan/trend-report.md" --output-dir "$PRODUCT_DIR/plan"
```

which leaves `plan/idea.md` + `plan/validate.md` for the winner. **Do not run `idea-validator` again** — trend-ideas already did, and a second run produces a second, possibly different, score.

Extract `APP_NAME`, one-line description, features, audience into the state file.

**1b — Brand name.** `/brand-name-checker --name "$APP_NAME"` → `plan/brand-check.md`. `Abandon` → propose 3 alternatives, re-check the user's pick before continuing. `Modify` → surface the reason at the gate.

**1c — PRD.** `/prd-generator "$PRODUCT_DIR/plan"` (folder path) → `plan/prd.md`. Add this orchestrator's constraints to the prompt: Flutter Android app, Riverpod + go_router, Firebase Auth if login, FastAPI on Render if a server is needed.

**1d — TAD.** `/tad-generator "$PRODUCT_DIR/plan"` → `plan/tad.md` (keep the name; `tasks-generator` looks for it).

**1e — Tasks.** `/tasks-generator "$PRODUCT_DIR/plan/prd.md"` (**file** path) → `plan/tasks.md`.

**1f — Derive flags** from `prd.md`, and record them in the state file:

| Flag | Set when the PRD |
|------|------------------|
| `needs_auth` | has register / login / account / user profile features |
| `needs_backend` | needs data shared between users or devices, server-side logic, or sync. Local-only apps (SQLite/shared_preferences) do **not** |

Read the PRD's feature list for this; do not `grep -qi "api\|sync"` — "sync" appears in "asynchronous" and "api" in "capital".

### Gate 1

```
◆ Phase 1 — Idea & Plan
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
  Idea:            $APP_NAME — $SCORE/100 ($VERDICT)          ← from validate.md
  Brand check:     $RISK · $RECOMMENDATION                     ← from brand-check.md
  PRD / TAD:       $N features · stack $STACK
  Tasks:           $N tasks
  Flags:           needs_auth=$B  needs_backend=$B
  App ID (planned) $ORG.$SLUG  ← permanent once published

  ⛔ Approve / Revise / Abort
```

Revise → ask what to change, regenerate only the affected doc(s) and everything downstream of it. Abort → stop, keep the directory, say where the state file is.

---

## Phase 2: Brand & Design (Gate ⛔)

**2a** `/logo-designer --name "$APP_NAME"` → `assets/logo/` (7 SVG variants + showcase). `flutter-store-metadata` later turns the primary mark into the 512 px icon, adaptive layers and feature graphic — do not resize anything here.

**2b** `/frontend-design --prd plan/prd.md --platform mobile` → `assets/ui-mockups/`. Mockups are the visual reference for Phase 4; they are not shipped.

### Gate 2

```
◆ Phase 2 — Brand & Design
  Logo:       $N variants at assets/logo/
  UI design:  $N screens at assets/ui-mockups/
  ⛔ Approve / Revise
```

---

## Phase 3: Setup & Backend

**3a — Flutter project.**

```
/flutter-init --project_name "$SLUG" --org "$ORG" --platforms android --dir "$PRODUCT_DIR/app"
```

Read back the `applicationId` it reports (flutter create sanitises names) and store it as `application_id`. `flutter-init` v2 pins compileSdk/targetSdk 36 and NDK r28+, adds credentials to `.gitignore`, and makes the first commit.

**3b — Firebase Auth** (only if `needs_auth`).

```
/firebase-auth-setup --slug "$SLUG" --output "$PRODUCT_DIR/firebase-config"   [--project-id <existing>]
```

Then read `firebase-config/firebase-output.json`:

- `auth_providers` → store in state. **Generate Google sign-in UI only if it contains `"google"`.** By default the skill enables `email` only — Google needs an OAuth client the API cannot mint. A Google button on a provider that is not enabled fails on the first tap.
- Android app registration (`google-services.json`, `firebase_options.dart`) is **not** produced by `firebase-auth-setup` (it creates a Web app). Run `flutterfire configure --project=<project_id> --platforms=android` inside `app/` — it needs `firebase-tools` logged in, which the setup skill already verified. The Android app's SHA-1 for Google sign-in comes from `flutter-signing` in Phase 5; add it in Firebase Console then, not now.
- `firebase-config/` goes in `.gitignore` (service account key).

**3c — Backend** (only if `needs_backend`). Read `references/backend-template.md` and generate `$PRODUCT_DIR/backend/`. Verify locally: `uvicorn main:app --port 8000` → `GET /api/health` 200. Then, if the user wants it live now:

```
/deploy-render --server-dir "$PRODUCT_DIR/backend" --slug "$SLUG" --health-path /api/health
```

(`--no-db` if the backend is stateless.) Use `deploy-output.json → url` **only when `verified: true`**; store it as `api_base_url`. Warn once: Render's free PostgreSQL is deleted 30 days after creation.

**3d — DevOps.** `/devops-pipeline --dir "$PRODUCT_DIR/app"` (pre-commit + lean CI). Also on `backend/` if it exists.

```
◆ Phase 3 — Setup & Backend
  Flutter project:   $APPLICATION_ID at app/  (compileSdk 36 · NDK r28)
  Firebase Auth:     providers=$AUTH_PROVIDERS  |  N/A
  Backend:           $API_BASE_URL (verified)  |  local only  |  N/A
  DevOps:            pre-commit + CI on app/ [+ backend/]
```

No gate.

---

## Phase 4: Build (Gate ⛔)

**4a — Parse `tasks.md` into features.** Classify each task by what it *does*, reading the task text (not by keyword grep):

| Task is about… | Type | Files (see `references/feature-templates.md`) |
|----------------|------|------|
| creating / listing / editing a domain object | `crud` | model · provider · service · list/detail/form screens · card |
| login / register / sign-in | `auth` | provider · login · register (only if `needs_auth`) |
| search / filter | `search` | screen |
| profile / account | `profile` | provider · screen |
| settings / preferences | `settings` | screen |
| onboarding, map, camera, charts, webview, notifications | that type | screen + whatever plugin it needs, added to pubspec explicitly |

For `crud`, extract the fields (name, type, required, enum values) from the task description into a small JSON block per feature. Ambiguous → look at `tad.md`'s schema, then ask; do not invent fields.

**4b — Generate features.** One feature at a time, from the templates in `references/feature-templates.md`; `flutter analyze` after each. Where the host has a subagent tool, features are independent and can be generated in parallel — but analyze **once per feature** either way. There is no `feature-gen-*` agent shipped with this skill; the templates are the spec.

Rules the templates encode: Riverpod for state, `go_router` for navigation, `dio` + Firebase ID-token interceptor only when `needs_backend`, `firebase_auth` only when `needs_auth`, Google sign-in only when `auth_providers` has `google`. Every generated screen gets an empty state and an error state; `// ...` placeholders from the template must not survive into committed code.

**4c — App shell.** `lib/config/routes.dart` (go_router, one route per screen generated), `lib/app.dart`, `lib/main.dart` (with `Firebase.initializeApp` when `needs_auth`), `lib/core/network/api_client.dart` when `needs_backend`. Update `pubspec.yaml` with exactly the packages the code imports; `flutter pub get`.

**4d — Verify.**

```bash
cd "$PRODUCT_DIR/app"
[ -d lib/generated ] || ! grep -rq "part '.*\.g\.dart'" lib || dart run build_runner build --delete-conflicting-outputs
flutter analyze
flutter test
```

Errors → fix and re-run, up to 3 rounds. Still failing → stop and show the analyzer output; do not proceed to review on a red tree.

**4e — Review and tests.**

```
/code-review "$PRODUCT_DIR/app"                      → plan/code-review.md   (apply critical fixes)
/test-coverage "$PRODUCT_DIR/app" --framework flutter_test → plan/test-coverage.md
```

**4f — Run it.** `flutter run` on a device/emulator if one is attached; otherwise `flutter build apk --debug` proves it links. The gate needs something the user can see — a screenshot via `adb exec-out screencap -p` when a device exists.

### Gate 4

```
◆ Phase 4 — Build
  Features:          $N ($TYPES)
  Routes:            $N
  flutter analyze:   0 errors · $N infos
  flutter test:      $N passed
  Code review:       $N findings, $N fixed
  Tests added:       $N (coverage $P%)
  Runs on:           <device/emulator + screenshot path>  |  debug APK built, no device

  ⛔ Approve / Retry / Manual fix
```

### Gate 5-entry ⛔ — before anything outward-facing

Tell the user, in this order, and wait:

- `applicationId` = `$APPLICATION_ID` — **permanent after the first publish**
- A keystore will be generated at `app/android/app/upload-keystore.jks`; backing it up is theirs to do (`flutter-signing` says what to store where)
- The build goes to track **`internal`** unless they say otherwise; `production` on a first release is almost always wrong
- Personal Play accounts created after 13 Nov 2023 need a 12-tester × 14-day closed test before production

Approval for `internal` is not approval for `production`.

---

## Phase 5: Store & Publish

Each step reads the previous step's machine output. Do not summarise them from memory.

**5a — Signing.** `/flutter-signing --dir "$PRODUCT_DIR/app"`. Record the SHA-1/SHA-256 it reports; if `auth_providers` has `google`, the SHA-1 must be added to the Firebase Android app before Google sign-in works on a release build — say so.

**5b — Build.**

```
/flutter-build --dir "$PRODUCT_DIR/app" --build_type appbundle --bump none --obfuscate true
```

First release → no bump. Keep `app/build/release/debug-info-<versionCode>/` — the only way to read crash reports from an obfuscated release. Output: `build/release/app-release.aab` + `build-info.json`.

**5c — Store assets.**

```
/flutter-store-metadata --app_name "$APP_NAME" --features "$FEATURES" --category "$CATEGORY" --contact_email "$CONTACT_EMAIL"
```

Do **not** pass `has_login` / `collects_data` / `has_ads` — the skill derives them from `pubspec.yaml` and the manifest; a wrong flag produces a listing that contradicts the app, which is a policy violation. Screenshots must come from a running build; with no device the skill emits placeholders and lists them in `store-listing.json → unresolved`, and compliance then fails **by design**. Resolve before 5d.

**5d — Compliance.** `/flutter-store-compliance --dir "$PRODUCT_DIR/app"` then read `store-metadata/compliance-report.json → overall`:

| overall | Do |
|---------|----|
| `FAIL` | List every FAIL check with its `fix`; resolve; re-run. **Publish is blocked.** |
| `WARN` | Show the items; the user decides |
| `PASS` | Continue |

**5e — Publish.**

```
/flutter-publish --aab_path "$PRODUCT_DIR/app/build/release/app-release.aab" --track "$TRACK" \
                 --whats_new "$PRODUCT_DIR/app/store-metadata/whats-new/en-US.txt"
```

A first release is always a **manual Console upload** — the Play API cannot create an app. The skill produces `upload-checklist.md` with real values substituted and writes `pending_upload` to `publish-state.json`; `last_uploaded` is written only after the user confirms the upload landed.

**5f — ASO (optional).** `/aso-marketing` on the listing text → `store-metadata/aso-report.md`. Its keyword plan is gated by its own approval step.

**5g — Release.** Commit everything in `$PRODUCT_DIR` (state file, plan, app, store-metadata — never `firebase-config/` or the keystore), then `/release-manager --version 1.0.0` on `app/`. Tagging is outward-facing only if a remote exists; if none does, say the tag is local.

**5h — Announcement copy.** There is no `social-poster` skill; posting is manual. Draft:

```
<APP_NAME> is on Google Play.
<SHORT_DESC>
https://play.google.com/store/apps/details?id=<APPLICATION_ID>
```

`social-brand-sync` syncs avatars and covers; it does **not** post. And the store link 404s until Google approves the release — say that next to the draft.

```
◆ Phase 5 — Store & Publish
  Signing:      upload-keystore.jks · SHA-1 $SHA1 · backup: NOT done for you
  Build:        app-release.aab $SIZE · v$VERSION+$CODE · targetSdk $T · 16 KB ✓   ← build-info.json
  Listing:      icon ✓ · feature graphic ✓ · $N screenshots ($SOURCE) · unresolved: $N
  Compliance:   $OVERALL ($PASS pass / $WARN warn / $FAIL fail)            ← compliance-report.json
  Publish:      READY FOR MANUAL UPLOAD · track $TRACK · upload-checklist.md
  ASO:          aso-report.md | skipped
```

---

## Final report

```
═══════════════════════════════════════════════════
  IDEA TO PLAY STORE — $APP_NAME
═══════════════════════════════════════════════════
  Phase 1  Idea & Plan        ✓  $SCORE/100 · brand $RISK
  Phase 2  Brand & Design     ✓  approved
  Phase 3  Setup & Backend    ✓  $APPLICATION_ID · auth=$AUTH_PROVIDERS · backend=$API_BASE_URL|none
  Phase 4  Build              ✓  $N features · analyze clean · $N tests
  Phase 5  Store & Publish    $STATUS  (compliance $OVERALL · track $TRACK)

  Project:        $PRODUCT_DIR
  AAB:            app/build/release/app-release.aab (v1.0.0+1)
  Debug symbols:  app/build/release/debug-info-1/   ← keep
  Store assets:   app/store-metadata/
  State:          .idea-play-store-state.json

  You still have to:
  1. Back up the keystore + key.properties to a password manager
  2. Upload the AAB in Play Console — app/store-metadata/upload-checklist.md
  3. Host privacy-policy.html at a public HTTPS URL and paste it in App content
  4. Fill Data safety from store-metadata/data-safety.md; complete Content rating
  5. [if Google sign-in] add SHA-1 $SHA1 to the Firebase Android app
  6. [if personal account] run the 12-tester closed test before applying for production
  7. [if Render DB] upgrade or export before the free PostgreSQL expires (30 days)
```

`$STATUS` is `READY FOR MANUAL UPLOAD` unless `flutter-publish` reported `UPLOADED`. Never write "published" — submission and review are the user's and Google's.

## Edge cases

| Situation | Handling |
|-----------|----------|
| No trend ideas / fetch fails | Ask for an idea directly → 1a "user already has an idea" branch |
| Brand name `Abandon` | 3 alternatives, re-check the user's choice |
| Gate: Revise | Regenerate only the affected doc and its downstream |
| Gate: Abort | Stop. Keep the directory and state file. Tell the user the path. |
| Resume | State file present → offer resume from `step` |
| `flutter-init` toolchain install fails | Surface its report; do not hand-roll an SDK install here |
| Firebase project quota exhausted | Ask for an existing project → `--project-id` |
| `flutterfire configure` missing | `dart pub global activate flutterfire_cli`; if it still fails, stop — a wrong `firebase_options.dart` fails at runtime, not at build |
| Backend deploy `verified: false` | Continue with the app pointing at localhost for now; record backend as unverified in the report; do not write the URL into the app |
| `flutter analyze` errors after 3 rounds | Stop at 4d with the output. Do not review or build a red tree |
| Compliance `FAIL` | Blocked. Fix, re-run 5d |
| Screenshots are placeholders | Compliance FAILs by design; capture from a device or emulator, re-run 5c |
| User wants `production` on first release | Say why `internal` first; if they insist, `flutter-publish` still applies its own gates |

## Acceptance criteria

- [ ] `plan/` has `idea.md`, `validate.md`, `brand-check.md`, `prd.md`, `tad.md`, `tasks.md`
- [ ] State file present, `application_id` recorded and not `com.example.*`
- [ ] Every task in `tasks.md` maps to generated feature code; `flutter analyze` clean; `flutter test` green
- [ ] Firebase Auth integrated iff `needs_auth`; Google UI iff `auth_providers` has `google`
- [ ] Backend generated iff `needs_backend`; its URL used only when `verified: true`
- [ ] `build-info.json` exists; `store-listing.json → unresolved` is empty
- [ ] `compliance-report.json → overall` is `PASS` or `WARN`
- [ ] `upload-checklist.md` produced; `publish-state.json` has `pending_upload` (or `last_uploaded` after user confirmation)
- [ ] Final report lists every remaining manual step; nothing is described as "published"

## Reference files

| File | Read when |
|------|-----------|
| `references/feature-templates.md` | Phase 4b–4c — per-type Dart templates, routing, app shell, api client, pubspec |
| `references/backend-template.md` | Phase 3c — FastAPI layout and `main.py` with Firebase token verification |
