---
name: flutter-publish
description: "Upload a Flutter Android App Bundle (AAB) to Google Play Console and guide the user through submission. Use when user says 'publish', 'upload', 'submit', 'đăng lên chplay', 'publish app', 'push to play store', or asks whether a build is ready to upload. Run LAST after all other flutter-* skills pass."
license: MIT
metadata:
  version: 2.0.0
---

# Flutter Publish

Final step of the Flutter → Google Play pipeline: verify the release is uploadable, get the AAB into Play Console, and drive the app to a live release.

## Core principle

> **Fail locally, not at upload.** Every rule Play enforces at upload time can be checked here first. A rejected upload costs a rebuild and a burned version code; a rejected *review* costs days.

Never claim an app is "published" or "submitted". This skill's output ends at *uploaded and ready for the user to submit* — final submission requires human action in Play Console, and review is Google's call.

## Workflow

Run in order. Each step names the file to read — read it when you reach that step, not before.

**Step 1 — Determine release mode.** Ask, or infer from `store-metadata/publish-state.json`:

| Mode | Condition | Consequence |
|------|-----------|-------------|
| **First release** | App does not exist in Play Console yet | Manual upload only. The Play Developer API cannot create an app or upload its first binary — this is a hard Google limitation, not a setup gap. |
| **Update** | App exists, ≥1 binary previously uploaded | API upload available if a service account is configured. |

**Step 2 — Run the gates.** Read `references/preflight.md`. It defines every blocking and warning check with the real command to run: compliance verdict, applicationId, target API level, 16 KB page alignment, version code, signing, debuggable flag, size. Do not skip a check because a sibling skill "should have" caught it — verify the AAB against `build/release/build-info.json` (Gate 0) instead of assuming the file in `build/` came from the last verified build.

Report all gate results in one table before doing anything else. **Any BLOCK ⇒ stop and fix.** Do not offer to "proceed anyway" past a BLOCK — Play will reject it, so proceeding only wastes a version code.

**Step 3 — Generate release notes.** Skip if `whats_new` was provided.

```bash
LAST_TAG=$(git tag --sort=-creatordate | head -1)
if [ -n "$LAST_TAG" ]; then
  git log "$LAST_TAG"..HEAD --oneline --no-merges --format="• %s"
else
  git log --oneline --no-merges -10 --format="• %s"
fi
```

Rewrite the raw commits into user-facing language — *"• Fixed a crash when opening saved items"*, not *"• fix(list): null deref in ItemRepo"*. Drop refactors, CI, and dependency bumps entirely; a release note is for users, not the changelog.

Write `store-metadata/whats-new/en-US.txt` (one file per locale, matching the locales in `store-listing.json`). **Max 500 characters per locale — verify with `wc -m`, not by eye.**

**Step 4 — Upload.** Route by Step 1:

- **Manual** (first release, or no service account): read `references/console-guide.md` and walk the user through it. Substitute real values from `store-metadata/store-listing.json` into the guide — never hand the user a template with `$APP_NAME` still in it.
- **API** (update + service account present): read `references/api-upload.md`. Confirm the track and rollout percentage with the user before the call — an API upload to `production` at 100% is immediately live and cannot be undone, only rolled forward.

Check for a service account before assuming manual:

```bash
ls service-account.json ~/.config/gplay/service-account.json 2>/dev/null
```

**Step 5 — Declarations.** Read `references/console-guide.md` § 2 *App content declarations*. These are required before Play will let the user submit, and they are the most common cause of a submission being stuck. If `test_credentials` was provided, it goes in **App access** — an app behind a login with no test credentials gets rejected without review.

**Step 6 — Testing track requirements.** Read `references/testing-track.md`. Personal accounts created after 13 Nov 2023 cannot reach production without closed testing: **12 testers opted in for 14 consecutive days**. Tell the user this *before* they build a production release plan around a date. Organization accounts are exempt.

**Step 7 — Record and report.** Write `store-metadata/publish-state.json` so the next run knows what already shipped:

```json
{
  "app_id": "com.example.myapp",
  "last_uploaded": { "version_name": "1.0.0", "version_code": 1, "track": "internal", "at": "2026-07-27T10:00:00Z", "method": "manual" },
  "play_console_app_created": true,
  "closed_testing": { "started": null, "testers_opted_in": 0 }
}
```

Then report using the Output section below.

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `track` | ❌ | `internal` | `internal`, `closed`, `open`, `production` |
| `aab_path` | ❌ | auto-detect | Path to the AAB |
| `whats_new` | ❌ | from git log | Release notes, ≤500 chars per locale |
| `test_credentials` | ❌ | — | Login for reviewers; **required if the app is login-gated** |
| `rollout_percentage` | ❌ | `100` | Staged rollout fraction; production only |

Default to `internal` when the user does not say. Going straight to `production` on a first release is almost always a mistake — say so once, then follow their call.

## Output

| Path | Content |
|------|---------|
| `store-metadata/whats-new/<locale>.txt` | Release notes per locale |
| `store-metadata/publish-state.json` | What shipped, for the next run |
| `store-metadata/upload-checklist.md` | The gate table + remaining manual steps |

Final report format:

```
FLUTTER PUBLISH — <UPLOADED | READY FOR MANUAL UPLOAD | BLOCKED>

Gates          <n> passed, <n> warnings, <n> blocking
AAB            build/release/app-release.aab (24 MB, v1.0.0+1, signed)
Track          internal
Release notes  store-metadata/whats-new/en-US.txt (312 chars)

Remaining manual steps:
  1. <specific, ordered, with the Play Console path to click>
  2. ...

Blocking issues (if any):
  ✗ <check> — <what to change, in which file>
```

State what is actually done versus what the user still must do. If the AAB was uploaded via API but declarations are incomplete, the app is *not* ready to submit — say that plainly.

## Reference files

| File | Read when |
|------|-----------|
| `references/preflight.md` | Step 2 — every gate, with commands |
| `references/console-guide.md` | Step 4/5 — manual upload, store listing, App content declarations |
| `references/testing-track.md` | Step 6 — 12-tester rule, production access application |
| `references/api-upload.md` | Step 4 — fastlane/API upload, service account setup |
| `references/troubleshooting.md` | An upload error or a rejection notice |

## Scope

Does: gate the release, verify the AAB, produce release notes, upload via API where possible, and guide the Console work that cannot be automated.

Does not: complete the Content Rating questionnaire, Data safety, or legal consents (API cannot touch these — Console UI only); submit for review on the user's behalf; appeal rejections; publish to iOS (separate App Store process, requires macOS).
