# Changelog

## v2.1.0 — 2026-09-13

### Fixed
- **`check-prereqs.sh` still required a `firebase login:ci` token** and failed without one, contradicting SKILL.md ("not needed — removed"). Now checks ambient `firebase login` / `gcloud auth` only.
- **`--google-client-id` / `--google-client-secret` were documented on `setup.sh` but rejected as "Unknown arg"** — Google sign-in could never be enabled through the orchestrator script. Now passed through to `enable-auth.sh`; also read from `GOOGLE_OAUTH_CLIENT_ID/SECRET`.
- `create-web-app.sh` fallback used the (unneeded) CI token; now uses `gcloud auth print-access-token`. An empty `apiKey` is now a hard failure instead of an empty config file.
- `firebase-web-config.json` built with `jq -n` (no unescaped interpolation).

### Added
- `--project-id <existing>`: reuse a project instead of creating one (the project quota is ~10–12 and takes 30 days to free). Adds Firebase to a plain GCP project automatically. `created: true|false` recorded in the output.
- `identityPlatform:initializeAuth` is called before enabling providers, with retries while the API propagates — replaces the manual "Console → Authentication → Get started" step the old version required.
- `setup.sh` now does the credential hygiene itself: `chmod 600` on the key, and `.gitignore` entries for the key and output JSON in the enclosing git repo.
- `--help` on `setup.sh`; argument validation (id and secret must come together).

### Changed
- Service account roles: `roles/firebaseauth.admin` + `roles/iam.serviceAccountTokenCreator` instead of `roles/firebase.admin`. This skill configures Authentication only; the old grant gave the key full Firestore/Storage/Hosting authority. IAM grant failures are now reported instead of swallowed.
- `--region` is documented as informational (`firebase projects:create` has no region argument).

### Breaking Changes
- Backends that relied on the service account having Firestore/Storage permissions via `roles/firebase.admin` must add the specific role (e.g. `roles/datastore.user`). Token verification and user management are unaffected.

## v2.0.0
- `auth_providers` reflects what was actually enabled; Google requires an OAuth client.
