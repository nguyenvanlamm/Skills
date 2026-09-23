# Changelog

## v1.3.0 — 2026-09-23

The skill named ~50 asset sites but no fetchable URLs, so every run had to rediscover them. That is how an agent ends up fetching a Mixkit 35 KB preview instead of the sound, or guessing a Poly Haven filename that does not exist.

### Added
- **Direct download URLs** sections in `sources-ui.md` and `sources-game.md`. Every pattern was fetched live through `fetch_asset.py`: Google Fonts (`ofl/`, `apache/`, bracketed variable names URL-encoded), Fontshare API (with tested `--only` filters for static or variable TTF + `ffl.txt`), Fontsource, Lucide/Phosphor/Tabler/Iconify SVG, Open Peeps, Transparent Textures, Kenney, Game-icons, Mixkit `.wav`, ambientCG, Poly Haven (via its API) and OpenGameArt. Each section also lists which sources are **hand download only** and why (terms, JS button, login, bot-block, 7z), and which are generators rather than downloads.
- **`fetch_asset.py --strip N`** drops leading archive directories. Game-icons becomes `<author>/<name>.svg` instead of `icons/a_000000/transparent/a_1x1/<author>/…`.
- `SKILL.md` Step 3 points to these sections and says not to guess URLs.

### Fixed
- **Unsupported archives.** `fetch_asset.py` refuses `.7z` / `.rar` / `.tar.gz`, by extension before downloading and by magic bytes after. It used to save them as one opaque blob; Glitch's pack is a 185 MB `.7z`.
- **Mixkit previews.** `fetch_asset.py` refuses Mixkit `-preview.mp3` URLs and prints the full-quality `<id>.wav` URL.
- **False licence notices.** Licence/readme detection inside archives now also requires a text-like extension. An icon named `credits-currency.svg` was listed as a licence notice.

## v1.2.0 — 2026-09-23

The 1.1.0 audit's "no changes needed" was wrong. Three defects each produced an app that does not compile, or a report number that cannot be measured, even when the workflow was followed exactly. All three are the same failure: reference rot in the API docs, the thing the skill already guarded against for licences. Every Dart snippet below was compiled with `flutter analyze` (Flutter 3.47.4) against the package versions that `flutter pub add` resolves today.

### Fixed — compile / run blockers
- **Lucide package.** The map targeted `lucide_icons`, which is frozen at 0.257.0 (2023) and has no `house`, `circleAlert`, `circleHelp` or `circleUser`. `Icons.home` → `LucideIcons.house` therefore failed in every touched file. All docs and scripts now use `lucide_icons_flutter` (3.1.x), and every table target is confirmed present in it. `Icons.check_circle` now maps to the current name `circleCheck`.
- **Rive 0.14.** `flutter pub add rive` resolves 0.14, which removed `RiveAnimation`, `StateMachineController`, `SMIBool` and `onInit`. All Rive snippets (the loader, the like button, `LoadingView`) are rewritten for `RiveWidgetBuilder` / `FileLoader` / data binding, with the `RiveNative.init()` call in `main`, a prefixed import, and fail-soft states. `flutter_gen` is pinned to 5.15+, which emits `riveFileLoader`.
- **Bundle size.** `flutter build apk --analyze-size` refuses multi-ABI builds. The command now passes `--target-platform android-arm64`.

### Fixed — correctness
- **Font filenames.** The pubspec examples used vendor filenames (`Satoshi-Regular.ttf`, `OFL.txt`), but `fetch_asset.py` writes snake_case names. The examples now match, and the docs say to copy paths from the script output.
- **`fetch_asset.py` HTML check.** An HTML page (a JS download button or a login wall) is no longer saved as an asset with a CREDITS row.
- **Credit column.** `Credit required Y/N` marked MIT and OFL as "must appear on screen", contradicting `licensing.md`. It is now `on-screen | license-page | none`, inferred from the licence and overridable with `--credit`. Unknown licences default to `on-screen`.
- **CREDITS rows.** Re-running `fetch_asset.py` for the same asset replaces its row instead of adding a duplicate.
- **Denylist.** It now matches with word boundaries: a bare `ARR` substring used to reject any licence containing "WARRANTY". It also catches `NON-COMMERCIAL` and `PERSONAL USE`.
- **Interpolations.** `dart_lex` blanked `${…}` interpolations along with string bodies, so the audit under-counted and `apply_icons.py` silently skipped `'${Icons.home.codePoint}'`. Interpolations are now scanned as code, and nested strings inside them are recorded. String line numbers now come from a bisect over newline offsets, not an O(n) count per string.
- **`AppButton`.** The press-scale was dead code, because `_down` was never set. It is now wired through a `Listener`.
- **`LoadingView`.** It now falls back to a static indicator when `MediaQuery.disableAnimationsOf` is true.
- **Snippet imports.** The `LicenseRegistry` and `NineSlicePanel` snippets were missing `package:flutter/material.dart`.
- **SDK notes.** The docs claimed Flutter 3.22+, but `CardThemeData` needs 3.27. The SDK note is corrected, and the version table is refreshed against pub.dev.
- **Non-interactive apply.** `SKILL.md` Step 6 ran `apply_icons.py --apply` without `--yes`. In a non-interactive shell that prompt reads EOF and aborts. The command now passes `--yes`, used after the user has approved the dry-run diff.

### Fixed — games and renamed assets (second pass)
- **Sprites destroyed by `optimize_flutter.py`.** The Step 4 command runs over all of `assets/`, and it treated every raster as an @3x source. A 64×64 Kenney button became 21×21 at the path Flame loads, and a 1024² atlas became 341² (no longer power-of-two, with the JSON coordinates now wrong). With `--replace`, the atlas PNG that its JSON points to was deleted. Now sprites keep their pixels and filenames and are only recompressed losslessly in place. This covers images in a Flame project, under `sprites/`, `tiles/` or `atlas/`, and images with atlas metadata beside them. `--sprite-mode` overrides the detection.
- **OGG is silent on iOS/macOS.** `flame_audio` plays through `audioplayers`, which uses `AVPlayer`, and `AVPlayer` has no Vorbis decoder. The docs recommended OGG, and the script converted everything to it. Now the script outputs `.m4a` (AAC) whenever `ios/` or `macos/` exists, converts existing `.ogg` files, and exposes `--audio-format`. Music keeps its source channel count instead of being upmixed to stereo. SFX over 50 KB are flagged, matching the budget the docs already claimed was enforced.
- **Renames went unreported.** `--replace` renamed files without telling anyone. The script now prints every `old → new` rename. `scan_project.py` has a new high-severity `BROKEN_ASSET_REFS` finding. It covers Flame-relative paths (`'sfx/click.wav'`), and skips interpolated paths and `packages/…` paths, which were false positives before.
- **Wrong advice for Flame games.** `scan_project.py` no longer reports `NO_DENSITY_BUCKETS` or `NO_WEBP` for them.

### Fixed — invented API and stale sources (third pass)
- **Atlas snippets used an API that does not exist.** Both atlas snippets called `fromJSONString(...)` and `atlas.getSprite(...)`, which are not in Flame, so neither compiled. They are rewritten for `flame_texturepacker`: `atlasFromAssets('ui.atlas')`, libGDX format, `findSpriteByName` without the extension, with null handled. `flame_texturepacker` is added to the version table. The `flutter_gen` example YAML now pins `flutter_gen_runner: ^5.15.0`, matching the Rive note.
- **Every Dart snippet now compiles.** Every code block in `SKILL.md` and the references compiles with `flutter analyze` against the current packages. That includes Flame, atlas, `flutter_gen` output (generated for real, including `riveFileLoader`), SVG, `.vec`, Lottie, Cupertino theme, transitions, Hero, skeleton list, GameButton and the product tile. The `(_, __, ___)` builder parameters were renamed, so there are no lint infos either.
- **Licences re-checked against the live pages** (2026-09-23):
  - **Humaaans** is **CC0**, not CC BY 4.0.
  - **Lordicon free** is a modified **CC BY-ND 4.0**, which means no recolouring. The skill only said "free with attribution".
  - **unDraw** forbids automated downloading, and so do **Storyset / Freepik**. `fetch_asset.py` now refuses those hosts and has a `--local <file> --source <page>` import path for files downloaded by hand. This is new trap 9 in `licensing.md`.
  - **Popsy** illustrations are gone (the site redirects to a website builder), so they are removed from the `playful-rounded` recipe and replaced by Humaaans.
  - **Glitch**: glitchthegame.com now redirects to slack.com. The entry points to the CC0 OpenGameArt uploads instead.
  - **Rive Community** moved to `rive.app/community/files`. `fluttericon.com` only resolves with `www.`.
- **`Colors.transparent`** no longer counts as a hardcoded colour in the audit, because it has no theme token to migrate to.

### Added
- **Map verification.** `generate_icon_map.py` checks every target against the package source resolved in `.dart_tool/package_config.json`. Missing constants are dropped and listed as `DROPPED`. An unresolved package prints `targets NOT verified`. Use `--skip-verify` to opt out.
- **Collision warnings.** Both icon scripts print a `COLLISION` list when distinct icons collapse into one glyph (`home` + `home_outlined` → `house`), because a `NavigationBar` `selectedIcon` would stop showing state.
- **New audit checks.** `scan_project.py` reports `STALE_LUCIDE` when `lucide_icons` is a dependency, and now recognises `RiveWidget` and `lucide_icons_flutter`.

## v1.1.0 — audited 2026-09-13, no code changes needed

Audit of the 1.1.0 release (committed separately). This entry records what was verified and why nothing was changed.

### Verified in this audit
- `scan_project.py` on a synthetic project: detects `NO_DARK_MODE`, `HARDCODED_COLORS`, `INLINE_TEXTSTYLE`, `PLAIN_LOADER`, `MISSING_ASSETS` (pubspec entry pointing at a nonexistent dir), density/WebP/vector findings; `derived.ui_framework` and `state_management` correct.
- `generate_icon_map.py` → `apply_icons.py` dry run: swaps `Icons.home`/`Icons.settings`, adds the import once, **leaves `Icons.*` inside comments and string literals untouched** (the `dart_lex` tokenizer works).
- `optimize_flutter.py` dry run prints the pubspec snippet with only existing directories.
- `fetch_asset.py` refuses `GPL-3.0` without `--force`, as documented.
- All five scripts compile and answer `--help`; `dart_lex.py` self-test passes.

### Why no further changes
The skill already has what the other skills in this repo were missing: deterministic scripts for every mechanical step, dry-run-by-default writes, a safety step that refuses to run on a dirty tree, and a report whose numbers come from the audit rather than from memory. Its remaining risks (font not actually loading at runtime, contrast on hand-edited slots) are already called out in Step 7 with the honest "only a screenshot proves it". Nothing found justified a change.

### Added (1.1.0, from the installed copy)
- `references/style-recipes.md`, `scripts/generate_icon_map.py`, Cupertino/mixed theme path, priority-screen proposal for large apps, const-hazard detection in `apply_icons.py`.

## v1.0.0
- Initial release.
