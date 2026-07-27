---
name: flutter-publish
description: "Upload a Flutter Android App Bundle (AAB) to Google Play Console and guide the user through submission. Use when user says 'publish', 'upload', 'submit', 'đăng lên chplay', 'publish app', 'push to play store', or asks whether a build is ready to upload. Run LAST after all other flutter-* skills pass."
license: MIT
metadata:
  version: 2.1.0
---

# Flutter Publish

Final step of the Flutter → Google Play pipeline: verify the release is uploadable, get the AAB into Play Console, and drive the app to a live release.

## Core principle

> **Fail locally, not at upload.** Every rule Play enforces at upload time can be checked here first. A rejected upload costs a rebuild and a burned version code; a rejected *review* costs days.

Never claim an app is "published" or "submitted". This skill's output ends at *uploaded and ready for the user to submit* — final submission requires human action in Play Console, and review is Google's call.

## Workflow

Run in order. Each step names the file to read — read it when you reach that step, not before.

**Step 1 — Determine release mode and account type.** Ask, or infer from `store-metadata/publish-state.json`:

| Mode | Condition | Consequence |
|------|-----------|-------------|
| **First release** | App does not exist in Play Console yet | Manual upload only. The Play Developer API cannot create an app or upload its first binary — this is a hard Google limitation, not a setup gap. |
| **Update** | App exists, ≥1 binary previously uploaded | API upload available if a service account is configured. |

**Missing state is not proof of a first release.** A fresh clone, a new machine, or a deleted file all produce the same empty result, and treating an update as a first release means Gate 5 has no baseline to check the version code against. If the state file is absent, ask whether the app already exists on Play; if it does, read the current version code from Console (or `edits.tracks.get`) and reconstruct the file before continuing.

Then establish two things that decide whether the requested track is even reachable:

| Question | Why it matters now |
|----------|--------------------|
| Personal or organization account? | Personal accounts created after 13 Nov 2023 **cannot** release to production until closed testing is complete (Step 6). |
| Has closed testing finished? | If not, `track: production` is not a choice the user has yet. |

If the user asked for `production` and either answer blocks it, say so **before** running the gates — otherwise the whole preflight runs for a track Play will not accept.

**Step 2 — Run the gates.** Read `references/preflight.md`. It defines every blocking and warning check with the real command to run: compliance verdict, applicationId, target API level, 16 KB page alignment, version code, signing, debuggable flag, size, committed credentials. Do not skip a check because a sibling skill "should have" caught it — verify the AAB against `build/release/build-info.json` (Gate 0) instead of assuming the file in `build/` came from the last verified build.

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

**Step 4 — Upload.** First, check whether this version code already shipped:

```bash
python3 -c "
import json; s=json.load(open('store-metadata/publish-state.json'))
print(s['last_uploaded'])" 2>/dev/null
```

If it matches the AAB's version code, this is a re-run. Do not upload again — the API rejects it and a second manual attempt just confuses the Console. Report what already shipped and move to Step 5.

Then route by Step 1:

- **Manual** (first release, or no service account): read `references/console-guide.md` and walk the user through it. Substitute real values from `store-metadata/store-listing.json` into the guide — never hand the user a template with `$APP_NAME` still in it.
- **API** (update + service account present): read `references/api-upload.md`. Upload as a **draft** unless the user explicitly asks to roll out; confirm package name, track, and status with them before the call. An API upload to `production` with `status: completed` is live worldwide the moment `commit` returns, and the only way back is a higher version code.

Check for a service account before assuming manual:

```bash
ls service-account.json 2>/dev/null   # plus wherever the user keeps theirs
```

**Step 5 — Declarations.** Read `references/console-guide.md` § 2 *App content declarations*. These are required before Play will let the user submit, and they are the most common cause of a submission being stuck. If `test_credentials` was provided, it goes in **App access** — an app behind a login with no test credentials gets rejected without review.

**Step 6 — Testing track requirements.** Read `references/testing-track.md`. Personal accounts created after 13 Nov 2023 cannot reach production without closed testing: **12 testers opted in for 14 consecutive days**. Organization accounts are exempt. Step 1 should already have surfaced this; here, give the user the concrete setup and the recruiting advice, and record where they are in the 14 days.

**Step 7 — Record and report.** Write `store-metadata/upload-checklist.md` — the gate table plus the manual steps still outstanding — so the user has the state in a file rather than only in this conversation.

Then update `store-metadata/publish-state.json`:

```json
{
  "app_id": "com.example.myapp",
  "last_uploaded": { "version_name": "1.0.0", "version_code": 1, "track": "internal", "at": "2026-07-27T10:00:00Z", "method": "manual" },
  "play_console_app_created": true,
  "closed_testing": { "started": null, "testers_opted_in": 0 }
}
```

**Only record an upload that actually happened.**

| Route | When to write `last_uploaded` |
|-------|------------------------------|
| API | After `commit` returns successfully — the response confirms the version code |
| Manual | Only after the user confirms the upload succeeded in Console |

For the manual route the upload is the user's action, not this skill's, so writing the field on the strength of having produced a guide is a lie the next run will act on: Gate 5 would block a version code that was never used. Until the user confirms, leave `last_uploaded` unchanged and record the intent separately:

```json
"pending_upload": { "version_code": 2, "track": "internal", "prepared_at": "2026-07-27T10:00:00Z" }
```

Then report using the Output section below.

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `track` | ❌ | `internal` | `internal`, `closed`, `open`, `production` |
| `aab_path` | ❌ | auto-detect | Path to the AAB |
| `whats_new` | ❌ | from git log | Release notes, ≤500 chars per locale |
| `test_credentials` | ❌ | — | Login for reviewers; **required if the app is login-gated** |
| `rollout_percentage` | ❌ | `20` | Staged rollout fraction; production only |

Default to `internal` when the user does not say. Going straight to `production` on a first release is almost always a mistake — say so once, then follow their call.

Production rollout defaults to staged, not 100%. A staged rollout can be halted when the crash rate moves; a completed 100% rollout can only be replaced by a higher version code, which means a rebuild and another review. Ask before deviating in either direction.

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
Track          internal · draft (not rolled out)
Release notes  store-metadata/whats-new/en-US.txt (312 chars)

Remaining manual steps:
  1. <specific, ordered, with the Play Console path to click>
  2. ...

Blocking issues (if any):
  ✗ <check> — <what to change, in which file>
```

State what is actually done versus what the user still must do, and keep the two apart in the status line: `UPLOADED` means a binary reached Play, `READY FOR MANUAL UPLOAD` means a guide was produced and nothing has been sent. If the AAB was uploaded via API but declarations are incomplete, the app is *not* ready to submit — say that plainly.

When the run ends with `pending_upload` in the state file, tell the user that confirming the upload is what lets the next run track version codes correctly.

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
