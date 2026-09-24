# Changelog

## v1.8.0 — 2026-09-24

For account-gated sources, the user logs in once, creates a key, and every later download is scripted through the site's **official** API.

### Added — `scripts/fetch_api.py`
- **Providers**: Freesound (API key for HQ previews; OAuth2 for original files, via `fetch_api.py auth freesound`: open the URL, log in, paste the code once, then the token refreshes automatically), Sketchfab (API token; GLB/glTF/USDZ), Pixabay and Pexels (images and video), Poly Pizza (GLB) and Smithsonian Open Access (CC0 images).
- **The licence comes from the API response**, not from the agent. It is normalised to an SPDX-style id (`CC0`, `CC-BY-4.0`, `CC-BY-NC-3.0`…) and then goes through `fetch_asset.py`'s denylist, so CC-BY-NC Freesound sounds and Sketchfab "Editorial" models are refused. The landing page, not a temporary S3 link, is recorded as the CREDITS source.
- **Credentials**: read from env vars, then `~/.config/flutter-ui-revamp/credentials`. That file is written with mode 600 (directory 700), and the script refuses to read it if group or others can read it. Values are never printed, logged, or passed on the command line. `fetch_api.py check` reports only set/missing.
- `fetch_api.py self-test` runs offline checks of licence mapping, denylist and credit inference.
- **Verified**: Smithsonian end to end with `DEMO_KEY` (real CC0 JPEG written, CREDITS row correct). Every other provider was run with an invalid key and returned a clean 401/400 with nothing written; the Sketchfab response ("Invalid API token") confirms the Token scheme is accepted. Response parsing for Sketchfab, Pixabay, Pexels, Poly Pizza and Freesound was tested against the documented response shapes. **Verified later with real keys**: Freesound (HQ preview; CC-BY-4.0 read from the API, credit level `on-screen`), Pixabay (1280 px JPEG) and Pexels (JPEG). A CC-BY-NC-4.0 Freesound sound was refused with nothing written. Sketchfab, Poly Pizza and Freesound originals (OAuth2) are still unverified with real credentials.
- **Not covered, by design**: sites with no API (Mixamo, ZapSplat, IconScout, LottieFiles, Rive, Lordicon, Textures.com…) stay hand download + `--local`, because scripting a logged-in browser breaks several sites' terms. Unsplash also stays manual: its API guidelines require hotlinking, which contradicts bundling.

### Changed — `fetch_asset.py`
- `main(argv, auth)` and `download(url, auth)` can be called from `fetch_api.py`. Auth headers are never logged, and urllib does not forward them on a cross-host redirect.
- `snake()` transliterates accents: "Le Blessé" becomes `le_blesse`, not `le_bless`, and "Đường Phố" becomes `duong_pho`.
- `Pixabay Content License`, `Pexels License` and `Unsplash License` now infer credit level `none` (none of them requires attribution) instead of the unknown-licence default `on-screen`.

## v1.7.0 — 2026-09-24

This release fills the categories that had the fewest options: animation (7 → 11), VFX (2 → 6), tilesets (3 → 8), 3D (10 → 14), PBR (6 → 9), backgrounds (10 → 15), photos (9 → 16) and emoji/avatars (9 → 15). The skill now lists ~245 recommended sources (sources-ui ~154, sources-game ~91) and ~29 checked-and-rejected ones. Licences were read from upstream repos and live pages, as before. Sample downloads went end to end through `fetch_asset.py --apply`: Fluent animated APNG, a Met CC0 image, Notion Avatar, Blobmoji, the Kenney 1-Bit zip with `--only`, and a Khronos GLB.

### Link audit (2026-09-24)
- **All 242 source pages were requested; 210 returned 200.** Another 22 returned 401/403/429/202, which is bot protection: the sites work in a browser but block scripts, and they are already listed as hand download. Two sites are really down and are now flagged ⚠️: **market.pmnd.rs** (404) and **gamesounds.xyz** (522). Six landing URLs had moved and were corrected: Carbon, Zendesk Garden, Streamline, facesjs, Absurd Design, and Duoicons (HTTPS dead, so point to the repo). Font Squirrel (502), Fontfabric (timeout) and Uncut (Cloudflare 455) failed from the test machine. Archive.org shows the first two alive in September 2026, so this is likely blocking, not shutdown.
- **99 sample direct-download URLs were fetched with `fetch_asset.py`'s own User-Agent; 97 returned the real file** (SVG/PNG/ZIP/TTF/GLB/WAV/JSON, magic bytes checked). The two failures: gamesounds.xyz (down), and `openmoji.org/data/…`, which now serves an HTML bot check to scripts, so the OpenMoji pattern switched to the official jsDelivr npm copy. The Fusion Pixel note now says to pick the `-otf-`/`-ttf-` asset by name.

### Fixed — `fetch_asset.py`
- **Git LFS pointers were saved as assets.** For an LFS-tracked file (e.g. `microsoft/fluentui-emoji-animated`), `raw.githubusercontent.com` returns a ~130-byte text pointer, and the script would have written it out as a `.png`. The script now refuses LFS pointers and prints the `media.githubusercontent.com` URL that returns the real file.

### Added — sources-ui.md
- **Animation**: Fluent Emoji Animated (MIT, APNG). A Flutter test decode confirmed APNG plays (72 frames), and ffmpeg → animated WebP was 6× smaller. Also Flutter's built-in `AnimatedIcons`, `flutter_animate` (BSD-3), and Glaxnimate (GPL tool, output is yours).
- **Emoji and avatars**: Fluent Emoji Animated, Blobmoji (Apache-2.0), Tossface (custom Korean licence, bundle the notice), Notion Avatar (CC0 assets), facesjs (Apache-2.0), Multiavatar (custom).
- **Backgrounds**: Kenney Pattern Packs (CC0), uiGradients (MIT, 382 gradients as JSON), WebGradients (MIT, 174 with angles/stops), BGJar (free tier CC BY 4.0). Get Waves and Blobmaker are noted as merged into Haikei.
- **Photos**: Negative Space and Skitterphoto (CC0). The Met Open Access (CC0, direct `primaryImage` via API), Art Institute of Chicago (CC0; its IIIF server blocks scripts), Rijksmuseum (per object), Smithsonian Open Access (CC0 items, API key), and the NASA image library (with the insignia, endorsement and identifiable-person limits).
- **Direct download URLs**: Fluent Emoji Animated (LFS media URL), Blobmoji, Notion Avatar parts, uiGradients/WebGradients JSON, The Met API.
- **Checked and rejected**: Lottielab free tier (Lottie export is Pro-only), unofficial animated-Fluent re-uploads, Big Heads/Avvvatars (React-only, no asset files).

### Added — sources-game.md
- **Sprites/tilesets**: Foozle (CC0 series: Void, Spire, Lucifer, Critters, Scallywag), Kenney 1-Bit Pack and the Tiny series (CC0), Hyptosis (CC BY 3.0), Sharm *Tiny 16* (CC BY 4.0/3.0).
- **VFX**: Kenney Smoke Particles, Splat Pack and Light Masks (CC0), Foozle effects (CC0), pimen free items (custom, no redistribution).
- **3D**: Kenney 3D kits (CC0), Khronos glTF Sample Assets (per-model licence in `metadata.json` — the Duck is SCEA, not CC), NASA 3D Resources (logo/endorsement limits), TextureCan models (CC0).
- **PBR**: TextureCan (CC0, 650+), 3DTextures.me (CC0, stylised materials), Kenney Prototype Textures (CC0).
- **Direct download URLs**: Kenney 1-Bit, Smoke Particles and Prototype Textures zips, Khronos GLB + `metadata.json`, NASA GLB.
- **Checked and rejected**: Mystic Woods free version (non-commercial).

## v1.6.0 — 2026-09-24

More sources, checked the same way as 1.5.0. Licences were read from the upstream repo (`gh api repos/<o>/<r>`, LICENSE/README) or the live licence page. Every new URL pattern was fetched live, and a sample of them (Myna UI, TDesign, Mage, Maki, Fluent Color, Kenney Fonts) went end to end through `fetch_asset.py --apply` into a scratch project, with correct CREDITS rows. New Direct-download rows are stamped *(2026-09-24)*.

### Added — sources-ui.md
- **Icons**: Myna UI (MIT, 2 600+), TDesign (MIT; const `TDIcons.*` inside `tdesign_flutter`), Gravity UI, ProIcons, Humbleicons, Qlementine, Duoicons (MIT), Mage (Apache-2.0, stroke + bulk), Lineicons free set (MIT), Zendesk Garden (Apache-2.0), System UIcons (Unlicense), Fluent UI System **Color** (MIT), Flat Color Icons (MIT), Maki + Temaki (CC0 map glyphs), and the CC BY 4.0 group: Pepicons, Streamline free, coolicons, HackerNoon Pixel Icon Library.
- **Licence findings**: the Pixel Icon Library repo is tagged MIT, but its icons are CC BY 4.0 (trap 11 inside one repo). Streamline's credit must link to streamlinehq.com. The pub package `line_icons` is Line Awesome, not Lineicons.
- **Illustrations**: Scale by Flexiple (free commercial, no attribution), Pixeltrue free (no redistribution in templates).
- **Emoji**: Firefox OS Emoji (art CC BY 4.0).
- **Fonts**: Omnibus-Type (OFL, GitHub-fetchable), Tunera (OFL), Atkinson Hyperlegible Next (OFL).
- **Photos**: Burst by Shopify.
- **Direct download URLs** for all new icon sets, Firefox OS Emoji and Omnibus-Type.
- **Checked and rejected**: Reshot (retired January 2026), Fresh Folk (CC BY-NC-ND), IconaMoon (no licence file), animated-SVG sets `line-md`/`svg-spinners` (MIT, but `flutter_svg` does not run SMIL/CSS animation), LottieFlow (no published licence).

### Added — sources-game.md
- **Sprites**: Brackeys' Platformer Bundle (CC0). Pixel Frog *Tiny Swords* Free Pack (custom, no redistribution; the old version is CC0). Pipoya RPG tilesets and Cainos Top Down Basic (custom: commercial OK, no redistribution).
- **Pixel fonts**: Kenney Fonts (CC0), with a verified direct zip and `--only` filter.
- **Audio**: Abstraction/Tallbeard Music Loop Bundle (CC0, 200+ loops), Scott Buckley (CC BY 4.0), ChipTone (output CC0), Bfxr (MIT tool).
- **Checked and rejected**: Sprout Lands free tier (non-commercial), FreePD (closed 2025).

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
