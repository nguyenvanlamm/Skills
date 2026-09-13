# Changelog

## v3.0.0 — 2026-09-13

### Fixed — API calls that could never work
- **Twitter/X**: `POST /2/users/:id/profile_image`, `/profile_banner`, `PUT /2/users/:id` do not exist, and the v1.1 media upload was sent with an unsigned `Authorization: OAuth …` header (no signature → always 401). Replaced with the real v1.1 `account/update_profile_image|_banner|` endpoints, signed OAuth 1.0a via `scripts/twitter_oauth1.py` (stdlib HMAC-SHA1). Bearer token dropped — it cannot write a profile.
- **LinkedIn**: the script uploaded an asset and reported `updated`; nothing was ever attached to the organization. Now `PARTIAL_UPDATE /v2/organizations/{id}` sets `logoV2` / `coverPhotoV2`, and `updated` is written only on a 2xx from that call. Name change marked `manual` (no API).
- **YouTube**: banner bytes were POSTed to `/upload/youtube/v3/channels` (not an upload endpoint). Now `channelBanners.insert` → `channels.update brandingSettings.image.bannerExternalUrl`. Name update fetches the current `brandingSettings.channel` first so `channels.update` does not wipe description/keywords/country.
- **Dry-run returned early**: `can_write … || return 0` at the top of LinkedIn/Twitter/YouTube/GitHub (and inside the first Facebook block) meant a dry run listed at most one planned change. Every item is now evaluated and recorded as `planned`.
- `report.json` was never initialised, so `update_report` silently did nothing unless another process had created it. The script now creates the file and the platform row.

### Added
- `scripts/analyze-website.py` — deterministic brand extraction (name, logo, cover, colour) with per-field provenance and `missing[]`; replaces an LLM-executed agent checklist.
- `scripts/process-images.sh` — download, normalise, per-platform resize, generated covers, `identify` validation → `images-manifest.json`; ImageMagick 6 and 7.
- `scripts/sync.sh` — one-command orchestrator; per-platform failures do not stop the others; final per-line report.
- Per-platform credential check → `skipped (missing env: …)`; one retry on 429/5xx; `--action` respected for every platform; `not-requested` status.
- Explicit capability table in SKILL.md: what each platform truly allows via API.

### Changed
- SKILL.md 490 → ~170 lines; fabricated/duplicated curl snippets removed. `agents/*.md` are now logic references for the scripts.
- Facebook profile picture produced at 360×360 (was 180 — Facebook rejects/blurs small uploads).
- Logs go to stderr so helper functions can return values on stdout.

### Breaking Changes
- **Twitter env vars**: `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` (all four). `TWITTER_BEARER_TOKEN` and `TWITTER_USER_ID` are no longer used.
- **LinkedIn scope**: `rw_organization_admin` is required (was `w_organization_social`, which cannot change a Page's branding).
- `report.json` gains `mode`, statuses `planned` and `not-requested`; `error` concatenates per-field messages.
- Entry point is `scripts/sync.sh`; calling `update-platform.sh` directly still works.

### Migration
1. Re-issue the X access token from an app with Read and write permission; export the four variables.
2. Re-authorise LinkedIn with `rw_organization_admin` as a Page admin.
3. Run `sync.sh` without `--apply`, read `report.json`, then `--apply`.

## v2.0.0
- Dry-run by default, backups, partial-failure reporting.
