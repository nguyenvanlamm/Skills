# Changelog

## v1.5.0 — 2026-09-23

A much wider source net, checked the same way as 1.4.0: every licence was read from the live page or the upstream repo, and every new URL pattern was fetched live. The date stamp on the Direct download sections stays 2026-09-23 because the new patterns were verified today.

### Added — sources-ui.md
- **Icons**: Akar, Teenyicons, Jam, Radix, Flowbite (`flowbite_icons`), CoreUI free set, IconPark (Apache-2.0, archived repo noted), Health Icons (CC0), Unicons (IconScout Simple License), Codicons (CC BY 4.0), Majesticons free set, PrimeIcons, CSS.gg, Weather Icons, Fork Awesome, Line Awesome, Flag Icons, Devicon. Each row states the Flutter package (or "build a font") and a fetchable URL.
- **Licence findings that change choices**: **PrimeIcons** relicensed at v8 to the custom PrimeUI License — pin `primeicons@7` / `prime_icons` (still MIT). **CSS.gg** relicensed at 2.1.2 — attribution is now mandatory; ≤2.1.1 stays MIT. **Majesticons** MIT covers only the 760-icon npm package, not the site's 11 000-icon set. **Unicons** uses the IconScout Simple License (commercial OK, no republishing as a pack, no competing service).
- **Illustrations**: illlustrations (MIT), IRA Design (MIT), LukaszAdam (CC0), Charco (free commercial, no resell), Mixkit Art (Mixkit licence), SVG Silh, Absurd Design, Ouch!/Icons8 (link-back), Vecteezy (attribution), Doodle Ipsum (URL API, fetchable).
- **Emoji and avatars**: Personas by Draftbit (MIT), plus a note that avatar-as-a-service endpoints have the same third-party-request problem as DiceBear/runtime fonts.
- **Fonts**: Collletttivo (OFL), Font Squirrel, Font Library, Use & Modify, Free Faces, Fontesk (default personal-use — per-font readme required), Fontfabric; the GitHub OFL releases row now names Cascadia Code, Intel One Mono, Commit Mono and Maple Mono too.
- **Animation**: IconScout Lottie (IconScout Simple License), Creattie (custom licence with reproduction/budget caps).
- **Backgrounds**: SVG Backgrounds (free tier needs attribution), Pattern Monster (MIT generator), Subtle Patterns (CC BY-SA 3.0 — flagged).
- **New "Photos" section**: Pexels, Unsplash, Pixabay, StockSnap, Kaboompics, Nappy, Openverse, Wikimedia Commons — with the bundle-don't-hotlink and depicted-IP rules.
- **Direct download URLs**: verified patterns for Majesticons, Teenyicons, Jam, Akar, Radix, Flowbite, IconPark, Codicons, Health Icons (whole-set `icons.zip`, with `--strip` hint), Unicons, PrimeIcons@7, CoreUI, Weather Icons, Line Awesome, Flag Icons, Devicon, DotGothic16/Press Start 2P, Doodle Ipsum, Wikimedia Commons, Openverse API.
- **Checked and rejected**: DaFont/1001Fonts-style aggregators (default "personal use"), Noun Project free tier (per-icon CC BY format), Gridicons (GPL), Typicons/Entypo (BY-SA), Designstripe (sunset), IcoMoon free pack.

### Added — sources-game.md
- **Sprites**: Open Duelyst (CC0 — a shipped CCG's full art drop: 600+ animated units, VFX, UI, music, SFX), Superpowers asset packs (CC0, GitHub-fetchable), pixel-boy Ninja Adventure (CC0), GameArt2D freebies (CC0), Lost Garden (CC BY 3.0, with the no-clones clause), Ansimuz (custom free / some CC0).
- **New "Pixel fonts" section**: Press Start 2P, DotGothic16, Fusion Pixel, Cubic 11 (all OFL), itch.io per-author fonts.
- **Low-poly 3D**: market.pmnd.rs (CC0), Smithsonian 3D (CC0 filter), Polytope Studio (store EULA), Mixamo (royalty-free, no raw redistribution, no ML training), TurboSquid/CGTrader/Free3D free sections, BlendSwap.
- **PBR**: CG Bookcase (CC0), 3Dassets.one (licence-filterable search engine over the CC0 sites), ShareTextures, Textures.com free (restrictive — last resort).
- **Audio**: gamesounds.xyz (CC0 packs, fetchable directory index), ZapSplat (attribution), SoundImage/Eric Matyas (credit inside the game), 99Sounds, Sample Focus, Free Music Archive (per-track CC), Musopen (PD filter), ende.app (CC BY, attribution voluntary), Audionautix (CC BY), Fesliyan (credit), DOVA-SYNDROME.
- **Direct download URLs**: Open Duelyst and Superpowers (GitHub raw + contents API), gamesounds.xyz directory files, Fusion Pixel releases, Cubic 11 raw TTF, SoundImage file links, Openverse API, Wikimedia Commons.
- **New "Checked and rejected" section**: Spriters/Textures/Models/Sounds Resource (ripped assets), RPG Maker RTP (engine-locked), ThreeDScans (no licence published), OS system fonts as pixel fonts, Orange Free Sounds (CC BY-NC), YouTube/TikTok SFX packs (no provenance), LPC art (BY-SA/GPL).

## v1.4.0 — 2026-09-23

More sources, each checked the same way as in 1.3.0. The licence was read from the live page or the upstream repo, every URL pattern was fetched, and pub packages were checked by downloading their archives. Testing the new URLs exposed two `fetch_asset.py` bugs.

### Added — sources
- **Icons** (`sources-ui.md`): Fluent UI System Icons, Heroicons, Bootstrap Icons, Iconoir, Eva, Remix Icon, MingCute, Material Symbols variable (`material_symbols_icons`), Font Awesome Free, Pictogrammers MDI, Carbon, Octicons, Boxicons, Pixelarticons. Each entry has its licence, Flutter package and direct SVG URL, and says whether the package exposes const `IconData`, which is what `apply_icons.py` can swap to.
- **Emoji and avatars** (new section): Fluent Emoji (MIT), Noto Emoji (new `2D/`/`3D/` layout), Noto Animated Emoji (CC BY 4.0, direct Lottie JSON), Twemoji (jdecked fork), OpenMoji (flagged BY-SA), DiceBear (licence varies by style, bundle rather than fetch at runtime), Boring Avatars.
- **Illustrations**: Open Doodles (CC0, direct S3 links) and 3dicons (CC0, hand download).
- **Fonts**: OFL font releases on GitHub (Geist, Inter, IBM Plex, JetBrains Mono, Monaspace, League of Moveable Type), with a tested `--only` filter.
- **Backgrounds**: fffuel, including its no-redistribution clause.
- **Games** (`sources-game.md`): Pixel Frog *Pixel Adventure*, 0x72 *DungeonTileset II*, Screaming Brain Studios (all CC0), the itch.io CC0 tag, Juhani Junkala 512 SFX (CC0, direct zip), incompetech (CC BY 4.0), jsfxr, and Sonniss GDC bundles. BBC Sound Effects is explicitly rejected (RemArc licence is non-commercial only).
- **Checked and rejected** list: ManyPixels, Solar icons, Iconsax, Simple Icons, Feather, each with the reason.
- `licensing.md` traps **11** (a pub package's licence is not the art's licence) and **12** (Remix Icon License forbids use as a logo or app icon). Trap 10 gains the Font Awesome SVG-vs-font case.

### Fixed — `fetch_asset.py`
- **Generic filenames collided.** A single-file download was named from the URL basename, so every Noto Animated Emoji became `lottie.json` and each download overwrote the last. A DiceBear avatar became `svg`, with no extension. Added `--filename`. Also added a warning for known generic basenames and a content sniff that adds `.svg`/`.png`/`.webp`/`.json` when the URL has no extension.
- **`OFL.txt` was not seen as a licence.** A Geist zip containing `OFL.txt` printed "no LICENSE/README inside the archive". Notice detection now also matches `ofl`, `ffl` and `notice`.
- `manypixels.co` added to the no-scripted-download hosts.

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
