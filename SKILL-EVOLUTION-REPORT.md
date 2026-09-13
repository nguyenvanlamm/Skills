# Skill Evolution Report — 2026-09-13

Deep audit of the 18 skills in `skills/`: read → reverse-engineer → score → redesign → implement → test → release. Nothing was "upgraded" by fetching a newer version; every change came from reading what the skill does and where it breaks.

Method for scores: 12 criteria (functionality, reliability, accuracy, performance, maintainability, extensibility, error handling, UX, tool usage, instruction quality, security, edge cases) collapsed to one 0–10 overall per skill. A bug that makes a documented path impossible (e.g. keytool prompt order, non-existent API endpoints) caps the *before* score at 5 regardless of how good the prose is.

| Skill | Before → After | Version | What changed most |
|-------|---------------:|---------|-------------------|
| travel-planner | 8.0 → 8.7 | 2.0.0 → 2.1.0 | Feasibility pre-check, lookup budget (15–25 calls, not 60), multi-destination, arithmetic self-check |
| trend-ideas | 6.0 → 8.4 | 2.1.0 → 2.2.0 | Fallback contradiction removed; **URLs 404'd** (`/topic/` missing); growth semantics verified live (`99` = "+99X+" cap); `idea.md`+`validate.md` contract; retries, offline `--from-file` |
| idea-discovery | 6.5 → 8.2 | 2.0.0 → 2.1.0 | Agents' "general knowledge" fallback (contradicting the core principle) removed; `research-log.md`; minimum bar → honest "no viable opportunity"; parallel/inline modes |
| idea-to-product | 5.5 → 7.9 | 2.0.0 → 2.1.0 | **Sibling contracts fixed** (`prd-generator` needs `idea.md`+`validate.md`, not a string; `tad.md`; `doc-manager` not `docs-generator`); repo creation moved behind the gate; `DATABASE_URL`/`ALLOWED_ORIGINS` from env; CORS step after Netlify |
| idea-to-play-store | 4.5 → 7.8 | 2.0.0 → 2.1.0 | 1160 → 417 lines, templates moved to `references/`; non-existent `/agent feature-gen-crud` and `--db postgres` removed; Android-only `--platforms`; **Abort no longer `rm -rf`**; state file specified; Google sign-in gated on `auth_providers`; `flutterfire configure` step |
| deploy-netlify | 6.5 → 8.3 | 2.0.0 → 2.1.0 | `--public` never reached the script; `npm ci` on fresh checkout; keep user's `netlify.toml`; publish dir from toml; HTML-body verify with retry; `--skip-github` |
| deploy-render | 4.5 → 8.2 | 2.0.0 → 2.1.0 | `grep DATABASE_URL` false-positive left SQLite in prod; **`pg_isready` never installed** (60 s dead wait every boot); `--region/--health-path` dropped by `deploy.sh`; commit-before-create; branch written to blueprint; `postgresMajorVersion`; 2 workers |
| firebase-auth-setup | 5.0 → 8.4 | 2.0.0 → 2.1.0 | prereq check **still demanded the CI token** SKILL.md said was gone; Google client flags rejected by `setup.sh`; `--project-id` reuse (quota); `initializeAuth` replaces the manual "Get started"; chmod/gitignore done by script; least-privilege roles |
| social-brand-sync | 3.0 → 7.6 | 2.0.0 → **3.0.0** | Twitter v2 endpoints **do not exist** → v1.1 + OAuth 1.0a signer; LinkedIn reported `updated` without applying; YouTube wrong upload endpoint; dry-run returned early; `report.json` never initialised; deterministic `analyze-website.py` / `process-images.sh` / `sync.sh` |
| flutter-init | 8.0 → 8.6 | 2.0.0 → 2.1.0 | `inspect-toolchain.sh`, `pin-android-config.sh` (Groovy **and** Kotlin DSL — tested); `HomeScreen` was referenced but never defined |
| flutter-signing | 6.0 → 8.8 | 2.0.0 → 2.1.0 | **keytool stdin sequence was wrong** (store/re-enter/key/re-enter) → `-storepass:env`, PKCS12; `generate-keystore.sh` refuses to overwrite without `--force` |
| flutter-build | 8.0 → 8.7 | 2.0.0 → 2.1.0 | `verify-artifact.sh` → `verify.json` (`OK/WARN/BLOCK/UNVERIFIED`), macOS-portable, accepts ≥16 KB alignments; shared with publish |
| flutter-store-metadata | 8.0 → 8.6 | 2.0.0 → 2.1.0 | `derive-facts.sh` (dev-deps excluded — old `sed` range included them; flavor manifests; unknown SDKs; evidence lines) shared with compliance |
| flutter-store-compliance | 8.0 → 8.7 | 2.0.0 → 2.1.0 | `check-assets.sh`: all measurable checks as report rows + code↔listing diff; per-locale description paths; jq `//`-with-false bug |
| flutter-publish | 7.5 → 8.6 | 2.1.0 → 2.2.0 | `preflight.sh` (10 gates, one JSON); told users to import a `data-safety.csv` the sibling deliberately never writes; `find … | head -1` contradiction; per-locale paths |
| flutter-ui-revamp | 8.5 → 8.5 | 1.1.0 (unchanged) | Scripts exercised on a synthetic project: audit codes, icon map, comment/string-safe icon swap, GPL denylist all correct. **Kept as is, deliberately** |
| android-game-forge | 8.0 → 8.5 | 3.0.0 → 3.1.0 | `STALE=1` set in a subshell → warning could never fire; bash-4/`stat`/`sort -V` portability; contrast gate re-verified on all 4 palettes (14/14 each) |

Mean: **6.5 → 8.3**. Twelve of eighteen skills had at least one path that could not work as written; those are all closed.

---

## Themes across the repo

**1. Contracts between skills were assumed, not read.** Orchestrators called `prd-generator --idea "<string>"` (it reads two files), `docs-generator` (does not exist), `/agent feature-gen-crud` (does not exist), `deploy-render --db postgres` (no such flag), and told users to import `data-safety.csv` (deliberately never produced). Both orchestrators now carry a contract table copied from each sibling's SKILL.md, and `trend-ideas` writes the exact `idea.md`+`validate.md` pair downstream consumes.

**2. Scripts drifted from their SKILL.md.** `firebase-auth-setup` said "no CI token" while its prereq script failed without one; `deploy-render`/`deploy-netlify` documented flags their entry script rejected. Every documented flag now exists and is exercised.

**3. Instructions asked the model to do what a script does better.** Deriving facts from `pubspec.yaml`, measuring PNG dimensions, computing 16 KB alignment, signing checks, website scraping, image resizing, keystore generation. Eleven new scripts (bash/Python, stdlib only) now do these deterministically and emit JSON the agent copies from — one vocabulary (`OK/WARN/BLOCK/UNVERIFIED` or `PASS/WARN/FAIL/SKIP`), and "tool missing" is never a pass.

**4. Fabricated success.** LinkedIn `updated` after an upload that changed nothing; a stale APK/AAB reported as built; "validated" scores the skill produced itself; "low confidence" market data from memory. Each path now either verifies the applying call or says it did not.

**5. Destructive or outward-facing actions without a gate.** `rm -rf $PRODUCT_DIR` on abort; GitHub repos created at setup before any approval. Removed / moved behind gates.

---

## Testing

| Area | Method | Result |
|------|--------|--------|
| Syntax | `bash -n` on 27 shell scripts; `py_compile` on 11 Python files | all pass |
| trend-ideas | `--from-file` fixture (ratio/int/garbage growth, `--min-volume`, `--limit 0`), then a **live fetch** and a topic-page fetch to verify growth semantics and URL shape | pass; two real bugs found and fixed |
| flutter-init | `pin-android-config.sh` on Groovy and Kotlin DSL fixtures; `inspect-toolchain.sh` on this machine | correct literals in both; JDK 17 / SDK 36 / NDK r28 detected |
| flutter-build / publish | fake AAB with a 4 KB-aligned `.so`, unsigned, no bundletool | `alignment16k BLOCK` names the file, `signing BLOCK`, `manifest UNVERIFIED`, `preflight` overall `BLOCK`, exit 1 |
| store-metadata / compliance | fixture with `google_mobile_ads` in **dev** deps, `READ_SMS`, unknown SDK, placeholder screenshot, `UNRESOLVED` marker, `has_login` listed false | `has_ads=false` (dev dep ignored), restricted permission FAIL, unknown SDK WARN, cross-check FAIL on `has_login`, deletion-route FAIL |
| deploy-render | `prepare-server.sh` on env-aware and hardcoded `database.py`, `uvicorn[standard]>=0.29` in requirements | keeps the first, rewrites the second preserving `DeclarativeBase`; no duplicate `uvicorn` (regex bug found and fixed in test); `render.yaml` carries region/healthCheckPath |
| deploy-netlify / deploy-render / firebase / signing / sync | argument validation and `--help` | every invalid input stops before step 1 with a specific message |
| social-brand-sync | `analyze-website.py` on github.com; `update-platform.sh` dry-run with and without env; TikTok manual path; report accumulation | correct provenance; `skipped (missing env)` / `planned` / `manual` / `not-requested` as designed; stale-error carry-over found and fixed |
| android-game-forge | `check-contrast.sh` on all 4 palettes + a drifted one; `resolve-versions.sh` with `curl` stubbed to fail | 14/14 pairs each; drift named; STALE warning now prints |
| flutter-ui-revamp | all 5 scripts on a synthetic Flutter project | see its CHANGELOG — no changes needed |

Not tested here: anything needing real credentials (Render, Netlify, Firebase, social APIs, Play), ImageMagick-dependent image generation (not installed on this machine — scripts detect and say so), an actual Flutter/Gradle build.

Regression: no v1 capability was removed. Behaviour changes that were intended are listed under *Breaking Changes* in each skill's `CHANGELOG.md` (abort no longer deletes; agents no longer emit "low confidence" fabricated data; Twitter/LinkedIn credential requirements; least-privilege Firebase roles; `tad.md` filename).

---

## Not in scope

`change-implementer` was added to the repo by a separate commit during this session and was not audited.
