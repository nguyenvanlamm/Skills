# Automated upload via the Play Developer API

## Hard limits — read before offering this

- **The API cannot create an app, and cannot upload its first binary.** At least one AAB must be uploaded manually through Console first. This is a Google security rule, not a configuration gap.
- The API cannot fill in Content rating, Data safety, or the legal consents, and cannot flip an app between published and unpublished. Those stay in Console.
- So: automation is for *updates*. First release always goes through `console-guide.md`.

## Service account setup (one-time)

Do not attempt this on the user's behalf silently — it touches their Google Cloud and Play Console permissions. Walk them through it and confirm each step.

1. **Play Console → Setup → API access.** Link a Google Cloud project (create one if needed).
2. **Google Cloud Console → APIs & Services.** Enable **Google Play Android Developer API** on that project.
3. **IAM & Admin → Service Accounts → Create service account.** No GCP roles are needed — Play permissions are granted separately in step 5.
4. **Keys → Add key → Create new key → JSON.** Save as `service-account.json` in the project root.
5. **Play Console → Users and permissions → Invite new user.** Paste the service account email. Grant **Release manager**, or narrower: *Release apps to testing tracks* and *Manage production releases*, scoped to this app only.
6. Permissions can take up to 24 hours to propagate. A `403` right after granting usually means "not yet", not "wrong".

Then, immediately:

```bash
echo "service-account.json" >> .gitignore
```

**The JSON key is a credential with release authority over the app.** Never commit it, never paste its contents into a report, and never echo it in a shell transcript. For CI, put it in a secret store, not the repo.

Verify before use:

```bash
fastlane run validate_play_store_json_key json_key:service-account.json
```

## Upload with fastlane supply (preferred)

```bash
fastlane supply \
  --aab build/release/app-release.aab \
  --package_name com.example.myapp \
  --json_key service-account.json \
  --track internal \
  --release_status draft \
  --skip_upload_metadata --skip_upload_images --skip_upload_screenshots
```

| Flag | Why |
|------|-----|
| `--release_status draft` | Uploads without rolling out. **Default this on any track above `internal`** — it gives the user a review step in Console before anything reaches users. Use `completed` only when they explicitly ask. |
| `--rollout 0.1` | Staged rollout fraction; requires `--release_status inProgress`. Production only. |
| `--skip_upload_*` | Without these, supply overwrites the store listing from local `fastlane/metadata/` — which this pipeline does not populate, so it would wipe listing text. Always pass them unless deliberately syncing metadata. |
| `--version_name` | Defaults to the AAB's version name; leave it. |

Release notes: supply reads `fastlane/metadata/android/<locale>/changelogs/<versionCode>.txt`. Copy them there first:

```bash
mkdir -p fastlane/metadata/android/en-US/changelogs
cp store-metadata/whats-new/en-US.txt fastlane/metadata/android/en-US/changelogs/<versionCode>.txt
```

and then drop `--skip_upload_metadata` — or accept that no release notes are attached.

## Upload with the raw API

If fastlane is unavailable (`pip install google-api-python-client google-auth`):

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

PACKAGE, AAB, TRACK = "com.example.myapp", "build/release/app-release.aab", "internal"

creds = service_account.Credentials.from_service_account_file(
    "service-account.json", scopes=["https://www.googleapis.com/auth/androidpublisher"])
svc = build("androidpublisher", "v3", credentials=creds).edits()

edit = svc.insert(packageName=PACKAGE, body={}).execute()["id"]
bundle = svc.bundles().upload(packageName=PACKAGE, editId=edit,
                              media_body=AAB, media_mime_type="application/octet-stream").execute()
svc.tracks().update(packageName=PACKAGE, editId=edit, track=TRACK, body={
    "releases": [{
        "versionCodes": [bundle["versionCode"]],
        "status": "draft",                      # "completed" rolls out immediately
        "releaseNotes": [{"language": "en-US", "text": open("store-metadata/whats-new/en-US.txt").read()}],
    }]}).execute()
svc.commit(packageName=PACKAGE, editId=edit).execute()
print("uploaded versionCode", bundle["versionCode"])
```

Everything between `insert` and `commit` is one transaction: nothing takes effect until `commit`, and an abandoned edit changes nothing. If a step fails, do not retry from the middle — start a new edit.

## Before any API call

Confirm with the user, out loud, the three values that decide blast radius: **package name, track, and status/rollout.** An upload with `status: completed` on `production` is live worldwide the moment `commit` returns, and the only way back is a higher version code.

Record the result in `store-metadata/publish-state.json` with `"method": "api"`.
