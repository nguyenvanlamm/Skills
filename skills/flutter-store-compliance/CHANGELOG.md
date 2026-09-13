# Changelog

## v2.1.0 — 2026-09-13

### Added
- `scripts/check-assets.sh` — every measurable check as report rows (`{id, group, verdict, summary, evidence, fix}`): icon/feature-graphic dimensions and alpha, screenshot count/size/aspect/alpha, placeholders and `unresolved`, name/description character counts per locale, privacy URL reachability, `UNRESOLVED` markers, target API vs today's date, `build-info.json` presence.
- Cross-checks in the script: `store-listing.json → derived` vs a fresh run of `derive-facts.sh` (shared with `flutter-store-metadata`), `app_name` vs `android:label`, restricted permissions, unknown SDKs, ad SDK vs `has_ads`, account-deletion route when an auth SDK is present.
- Step 1/2/3 split into *mechanical (script)* vs *judgement (read)* so the agent stops re-measuring what a script measures better.

### Fixed
- `checks.md` group 4 read descriptions from `store-metadata/description/en-US/…` while the metadata skill writes one directory per locale — now iterates `store-listing.json → locales`.
- Verdict logic: a `false` derived fact was treated as "missing" in the cross-check (`jq //`); fixed with an explicit null test.

### Breaking Changes
- None. `compliance-report.json` shape unchanged; the script's rows slot straight in.

## v2.0.0
- PASS/WARN/FAIL vocabulary, evidence-first audit, no CSV emission.
