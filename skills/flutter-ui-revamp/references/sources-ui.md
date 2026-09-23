# Asset sources — app UI

Read at Step 3, after the design direction is locked. Reading it earlier leads to picking assets you like rather than assets that match a decision.

**The selection rule: one pack per category.** A screen assembled from Lucide arrows, Phosphor tabs and one stray Material icon looks exactly like what it is. Pick the pack whose *whole set* fits, then live with its weaker icons — internal consistency beats per-icon perfection every time.

Licence column is the licence as published at the time of writing. **Re-read it on the page before downloading** — projects relicense, and a stale line in this file is not a defence.

## Icons

| Set | URL | Licence | Formats | Flutter package | API |
|---|---|---|---|---|---|
| **Lucide** | lucide.dev | ISC | SVG, font, PNG | `lucide_icons_flutter` (const `IconData`; preferred for bulk swap) | yes (unpkg / jsDelivr per-icon SVG) |
| **Phosphor** | phosphoricons.com | MIT | SVG, font | `phosphor_flutter` | via GitHub raw |
| **Tabler** | tabler.io/icons | MIT | SVG, font, PNG | none official — build a font | via GitHub raw |
| **Material Symbols** | fonts.google.com/icons | Apache-2.0 | SVG, variable font | built in (`Icons.*`) | Google Fonts API |
| **Ionicons** | ionic.io/ionicons | MIT | SVG, font | `ionicons` | via GitHub raw |
| **HugeIcons** | hugeicons.com | free tier MIT-ish, **check tier** | SVG | `hugeicons` | partial |
| **Iconify** | icon-sets.iconify.design | aggregator — **per-set licences vary** | SVG, JSON | none | yes, `api.iconify.design` |
| **Fluent UI System Icons** | github.com/microsoft/fluentui-system-icons | MIT | SVG, font | `fluentui_system_icons` (const `IconData`, e.g. `FluentIcons.home_24_regular`) | via GitHub raw |
| **Heroicons** | heroicons.com | MIT | SVG | `heroicons_flutter` (const `IconData`) | unpkg |
| **Bootstrap Icons** | icons.getbootstrap.com | MIT | SVG, font | `bootstrap_icons` (const `IconData`) | unpkg |
| **Iconoir** | iconoir.com | MIT | SVG | `iconoir_flutter` — **widgets, not `IconData`** | via GitHub raw |
| **Eva Icons** | akveo.github.io/eva-icons | MIT | SVG, font | `eva_icons_flutter` (const `IconData`) | — (upstream unmaintained since 2023) |
| **Remix Icon** | remixicon.com | **Remix Icon License v1.0** (custom, since 2026) | SVG, font | `remixicon` (const `IconData`) | unpkg |
| **MingCute** | mingcute.com | Apache-2.0 | SVG | none — build a font | via GitHub raw |
| **Material Symbols (variable)** | fonts.google.com/icons | Apache-2.0 | variable font | `material_symbols_icons` (`Symbols.home`, with `fill`/`weight`/`grade`) | Google Fonts |
| **Font Awesome Free** | fontawesome.com | icons **CC BY 4.0** as SVG, **OFL** as font | SVG, font | `font_awesome_flutter` — **`FaIconData`, not `IconData`** | unpkg |
| **Pictogrammers MDI** | pictogrammers.com | Pictogrammers Free License (Apache-2.0 for most icons) | SVG, font | `material_design_icons_flutter` (last release 2023) | unpkg (`@mdi/svg`) |
| **Carbon** | carbondesignsystem.com/elements/icons | Apache-2.0 | SVG | none | unpkg (`@carbon/icons`) |
| **Octicons** | primer.style/octicons | MIT | SVG | none maintained (`octicons` is from 2016) | unpkg (`@primer/octicons`) |
| **Boxicons** | boxicons.com | MIT | SVG, font | `boxicons` (2021, stale) | unpkg |
| **Pixelarticons** | pixelarticons.com | MIT (free set) | SVG | none — build a font | via GitHub raw |

Notes that decide the choice:

- **Lucide** — 1.5px stroke, geometric, 1400+ icons. The safe default for a minimal/modern direction. Use the **`lucide_icons_flutter`** package for revamps. It is actively maintained, tracks upstream names (`house`, `circleAlert`, and so on, with the old names kept as aliases), and exposes const `IconData`, so `const Icon(LucideIcons.house)` stays const (see the const hazard in `refactor-patterns.md`). Import it with `package:lucide_icons_flutter/lucide_icons.dart`. **Do not use `lucide_icons`.** It is frozen at 0.257.0 (2023), and `LucideIcons.house` does not exist in it. If the project already depends on `lucide_icons`, migrate it: both packages declare a class named `LucideIcons`, so they cannot coexist in one app. (`lucide_flutter` is a third, unrelated package with a different API surface.)
- **Phosphor** — six weights (thin → fill) from one family, which is why it wins for playful and for apps that need a filled/outlined tab-bar pair. In `phosphor_flutter` v2 the ergonomic API is a call — `PhosphorIcons.house()` — which is **not const**. Use the const constants (`PhosphorIconsRegular.house`) in bulk replacements.
- **Iconify** is not an icon set, it is 200 000 icons across ~150 sets with ~15 different licences. Excellent for finding one missing glyph, dangerous as a primary source: you inherit whichever licence that specific set carries.
- **Material Symbols** ships with Flutter. If the design direction is "clean Material 3", the honest answer is often *keep the icons* and spend the effort on colour, type and motion. When the direction needs a heavier or filled weight, `material_symbols_icons` exposes the variable axes (`Icon(Symbols.home, fill: 1, weight: 600)`) without changing the set.
- **Fluent UI System Icons** — Microsoft's set, regular + filled at 16/20/24/28/48 px, MIT. The strongest choice for a Windows-flavoured or productivity app, and the tab-bar outline/filled pair comes for free (`home_24_regular` / `home_24_filled`).
- **Heroicons** — Tailwind's set: outline 24, solid 24, mini 20, micro 16. Fewer than 350 icons, so check coverage against the audit's icon list before choosing it.
- **API shape decides whether `apply_icons.py` can do the swap.** It rewrites `Icons.x` to another const `IconData`. That works for Lucide, Phosphor (`PhosphorIconsRegular.*`), Fluent, Heroicons, Bootstrap, Eva, Remix and `material_symbols_icons`. It does **not** work for:
  - **`font_awesome_flutter` 11+**, whose constants are `FaIconData`. `Icon(FontAwesomeIcons.house)` does not compile; every call site must become `FaIcon(...)`.
  - **`iconoir_flutter`**, where each icon is its own widget (`HomeSimple()`).
  - **`hugeicons`**, where each icon is `List<List<dynamic>>` path data drawn by a `HugeIcon` widget.

  These need a widget-level refactor, not a constant swap. Budget for it, or pick a set with const `IconData`.
- **Font Awesome Free** licenses its icons differently by format: the SVG/JS files are **CC BY 4.0** (on-screen credit), and the font files are **OFL** (licence page). `font_awesome_flutter` ships the font, so `--license OFL-1.1` is correct for the package, while hand-copied SVGs need CC BY credit. This is trap 10 in `licensing.md`.
- **Remix Icon** moved from Apache-2.0 to its own **Remix Icon License v1.0** in January 2026. Using it in an app is allowed, with attribution optional. Two clauses matter: you **may not use an icon as a logo, brand mark or app icon** (§3.3), and you may not redistribute the set as an icon pack. Keep Remix glyphs out of `flutter_launcher_icons` and the splash logo.
- **Pixelarticons** is the one UI set that fits a pixel-art game's menus. Its 24px grid matches Kenney's pixel packs.

**When to build a custom icon font instead of adding a package:** you need fewer than ~40 icons, or you are mixing two sets deliberately (a brand glyph plus a standard set), or the package's tree-shaking is not trimming the unused thousands. Upload the SVGs to **www.fluttericon.com** (the bare domain does not resolve), download the `.ttf` + generated Dart, and follow `integration-flutter.md § Custom icon font`. A 40-icon font is ~8 KB; a full icon package with tree-shaking disabled can be 200 KB+.

## Illustrations

| Source | URL | Licence | Formats | Notes |
|---|---|---|---|---|
| **unDraw** | undraw.co/illustrations | unDraw licence: free commercial use, no attribution. **No packs, no AI training, no automated downloading** | SVG, PNG | **Download by hand in the browser**, after recolouring to your seed colour on the site. The licence forbids "automated … ways to … download", so do not point `fetch_asset.py` at it. Use a handful as UI illustrations; a product built around unDraw art is outside the licence. Flat, transparent background — safe in dark mode. |
| **Storyset** | storyset.com | Freepik free — **attribution required**; **no downloads via robots, programs or tools** | SVG, PNG, animated SVG | Editable colour + optional built-in animation. **Download by hand.** Attribution is not optional; it belongs in CREDITS.md and on the About screen. |
| **Humaaans** | humaaans.com | **CC0** | SVG, Sketch, PNG | Mix-and-match human figures by Pablo Stanley. No attribution required. |
| **Open Peeps** | openpeeps.com | CC0 | SVG, PNG, PSD | Hand-drawn people, no attribution. Best CC0 human illustration set. |
| **Blush** | blush.design | **per-collection**, many require a paid plan | SVG, PNG | Check the individual collection; several are not free. |
| **DrawKit** | drawkit.com | free packs: no attribution; check per pack | SVG, PNG | |
| **Open Doodles** | opendoodles.com | **CC0** | SVG, PNG, GIF | Pablo Stanley's sketchy people. Direct S3 links (below). Pairs with Open Peeps and Humaaans, which come from the same author. |
| **3dicons** | 3dicons.co | **CC0** | PNG, Blender, Figma | 1400+ 3D renders by Vijay Verma, in clay/colour/gradient styles. They make good empty-state and onboarding hero art. Take the full pack from the "Download V1" link (Gumroad, hand download). The per-icon thumbnails on the site are 400px WebP served from an undocumented storage bucket, so do not script against them. |
| **Microsoft Fluent Emoji** | github.com/microsoft/fluentui-emoji | **MIT** | 3D PNG, colour/flat/high-contrast SVG | 1500+ glyphs in four styles. The 3D PNGs (256×256) work well as friendly empty-state and achievement art. MIT, so `license-page` credit. |

The dark-mode trap: an illustration exported with a baked white rectangle behind it shows a hard white slab on a dark surface. Every source above can export transparent — verify the exported file, do not assume it. `undraw` and `openpeeps` are transparent by default.

## Emoji and avatars

| Source | URL | Licence | Formats | Notes |
|---|---|---|---|---|
| **Fluent Emoji** | github.com/microsoft/fluentui-emoji | MIT | 3D PNG, SVG | See Illustrations above. The safest emoji set for a closed-source app. |
| **Noto Emoji** | github.com/googlefonts/noto-emoji | images **Apache-2.0**, font **OFL** | PNG 32/128/512, SVG | The repo now splits into `2D/` and `3D/` folders; older `png/…` and `svg/…` URLs return 404. |
| **Noto Animated Emoji** | googlefonts.github.io/noto-emoji-animation | **CC BY 4.0** | Lottie JSON, WebP, GIF | Direct Lottie per code point (below). This is the cheapest good celebratory animation for the `lottie` package. It needs an on-screen credit. `animated_emoji` on pub bundles the same files. |
| **Twemoji** | github.com/jdecked/twemoji (community fork; `twitter/twemoji` is no longer updated) | graphics **CC BY 4.0**, code MIT | SVG, PNG 72 | Needs an on-screen credit. |
| **OpenMoji** | openmoji.org | **CC BY-SA 4.0** | SVG, PNG | **Share-alike.** Recolouring or editing makes the derivative BY-SA too (`licensing.md` trap 8). Use as-is, or pick Fluent/Noto. |
| **DiceBear** | dicebear.com | **per style**: 42 CC0, 14 CC BY 4.0, 1 MIT, 4 "artist's own terms" | SVG, PNG via HTTP API | Deterministic avatars from a seed, good for placeholder profile pictures. Check the style on dicebear.com/licenses. Notionists, Lorelei, Open Peeps, Thumbs and Shapes are CC0; Adventurer, Micah, Big Smile and Personas need credit; Avataaars/Bottts use the artist's own terms. Every SVG also embeds its licence in `<metadata>`. **Fetch at build time and bundle.** Calling `api.dicebear.com` at runtime sends every user's seed to a third party, the same privacy problem as `google_fonts` (trap 7). |
| **Boring Avatars** | boringavatars.com | MIT | SVG (generated) | Abstract geometric avatars. It is a React library with no Flutter port, so export the SVGs you need from the site and bundle them. |

## Fonts

| Source | URL | Licence | Formats | API |
|---|---|---|---|---|
| **Google Fonts** | fonts.google.com | almost all OFL, a few Apache-2.0 | TTF, variable TTF, WOFF2 | yes — `fonts.gstatic.com`, and the `google_fonts` package |
| **Fontshare** | fontshare.com | free for commercial use, ITF licence | TTF, OTF, WOFF2, variable | no |
| **Fontsource** | fontsource.org | mirrors OFL/Apache fonts | TTF, WOFF2 | yes — npm/jsDelivr |
| **Uncut.wtf** | uncut.wtf | per-font, mostly OFL | TTF, OTF, variable | no |
| **Velvetyne** | velvetyne.fr | OFL | TTF, OTF | no |
| **GitHub releases (OFL foundries)** | Geist (`vercel/geist-font`), Inter (`rsms/inter`), IBM Plex (`IBM/plex`), JetBrains Mono, Monaspace (`githubnext/monaspace`), The League of Moveable Type (`theleagueof/*`) | OFL-1.1 (all checked) | zip of TTF/OTF/variable | yes: `api.github.com/repos/<o>/<r>/releases/latest` |

GitHub releases are the upstream source, and they are often newer than the Google Fonts copy. Inter 4.x and Geist, for example, ship there first. Resolve the asset name from the API instead of guessing the tag.

**Fontshare** is the reason a Flutter app can stop looking like every other Flutter app — Satoshi, General Sans, Clash Display and Switzer are contemporary, well-hinted and free for commercial use, and none of them is Roboto. Download the TTF and bundle it. See `licensing.md § google_fonts` for why *bundling* beats the runtime-fetch package.

Pairing, and the hard limit of two families: one display family for headings, one text family for body and UI. A third family is a bug. If in doubt, one variable family across two weights beats two families badly paired.

## Animation

| Source | URL | Licence | Format | Flutter |
|---|---|---|---|---|
| **Rive Community** | rive.app/community/files | **per-file** — most CC BY, some all-rights-reserved | `.riv` | `rive` package |
| **LottieFiles Free** | lottiefiles.com/featured-free-animations | per-file; free tier often needs attribution | `.json`, `.lottie` | `lottie` package |
| **Lordicon free** | lordicon.com/icons?price=free | modified **CC BY-ND 4.0**: commercial OK, attribution required, **no derivatives** | Lottie JSON, GIF | `lottie`. ND means you may not recolour or edit the animation to fit the theme. Use it as-is, or pay for the Pro licence. |
| **useAnimations** | useanimations.com | free, attribution appreciated | Lottie JSON | `lottie` |
| **Noto Animated Emoji** | googlefonts.github.io/noto-emoji-animation | **CC BY 4.0** | Lottie JSON | `lottie`, or `animated_emoji`. The only source here with a stable direct Lottie URL (below). |

Rive is the first choice in Flutter and it is not close: the runtime is a vector renderer with a state machine, so one 12 KB `.riv` covers idle → hover → pressed → success without four separate files or a single `AnimationController`. Lottie is the right tool for a linear, fire-and-forget animation (a splash, a confetti burst, an empty-state loop).

Rive Community licences are **per artboard, set by the author**. The "Community" label means shared, not licensed for reuse. Open the file's page and read the licence field; if there is none, treat it as all-rights-reserved and pick another.

## Layout reference (Figma — for reading, not for downloading)

| Kit | URL | Use |
|---|---|---|
| **Material 3 Design Kit** | figma.com/community/file/1035203688168086460 | Canonical M3 component sizing, states, elevation |
| **iOS 18 UI Kit (Apple)** | developer.apple.com/design/resources | Cupertino metrics, when the app is genuinely iOS-first |
| **Untitled UI Free** | untitledui.com/figma | 900+ components; good for spacing and hierarchy conventions |

These inform decisions about density, spacing and state; they are not assets to ship.

## Background, pattern, colour

| Tool | URL | Output | Licence |
|---|---|---|---|
| **Haikei** | haikei.app | blobs, waves, meshes as SVG/PNG | free, no attribution |
| **Hero Patterns** | heropatterns.com | tileable SVG patterns | CC BY 4.0 |
| **Transparent Textures** | transparenttextures.com | tileable PNG textures | free, attribution appreciated |
| **fffuel** | fffuel.co | noise, blob, gradient, wave, pattern generators as SVG | fffuel licence: personal and commercial use, no attribution; **no standalone redistribution** of the images. Embedding in an app is fine; publishing them as a background pack is not |
| **Coolors** | coolors.co | palette exploration | free |
| **Realtime Colors** | realtimecolors.com | palette previewed on a real layout | free |
| **Material Theme Builder** | material-foundation.github.io/material-theme-builder | full M3 `ColorScheme` from a seed, exportable as Dart | Apache-2.0 |

**Material Theme Builder is the one to actually use.** It emits a complete light + dark `ColorScheme` from a seed colour, tonally correct, with the contrast pairs already solved. Paste its Dart output into `lib/theme/app_colors.dart` rather than hand-picking hexes — hand-picked schemes are where the 3.1:1 body text comes from.

## Direct download URLs

`fetch_asset.py --url` needs a URL that returns **the file itself**. A landing page returns HTML, and the script refuses it. The patterns below were all fetched successfully on **2026-09-23**. Placeholders are in `<angle brackets>`. Always read the licence on the landing page first, and pass that page as `--source`.

| Source | URL pattern | Returns | Notes |
|---|---|---|---|
| **Google Fonts** | `https://github.com/google/fonts/raw/main/ofl/<family-lowercase>/<File>.ttf` | TTF | Variable files carry their axes in brackets, which must be URL-encoded: `Nunito[wght].ttf` becomes `Nunito%5Bwght%5D.ttf`, and `Roboto[wdth,wght].ttf` becomes `Roboto%5Bwdth%2Cwght%5D.ttf`. Fetch `…/ofl/<family>/OFL.txt` as well; it becomes `ofl.txt` for `LicenseRegistry`. About 40 older families (e.g. Chewy) live under `apache/<family>/` and ship `LICENSE.txt` instead. If `ofl/` returns 404, list the folder with `https://api.github.com/repos/google/fonts/contents/<dir>/<family>`, where `<dir>` is `ofl`, `apache` or `ufl`. |
| **Fontshare** | `https://api.fontshare.com/v2/fonts/download/<slug>` (e.g. `satoshi`, `clash-display`, `general-sans`) | zip, ~60 files (OTF, TTF, WOFF, CSS) | Take only what you ship; see the `--only` filters below the table. The licence is `License/FFL.txt`, which becomes `ffl.txt`. |
| **Fontsource** | `https://cdn.jsdelivr.net/fontsource/fonts/<id>@latest/latin-<weight>-normal.ttf` | TTF (one weight, latin subset) | Subset files are small. Pick another subset (`vietnamese`, `latin-ext`, …) if the app's copy needs it. |
| **Lucide** (single SVG) | `https://unpkg.com/lucide-static@latest/icons/<name>.svg` | SVG | Only for a custom icon font. Normally use the `lucide_icons_flutter` package. |
| **Phosphor** (single SVG) | `https://raw.githubusercontent.com/phosphor-icons/core/main/assets/<weight>/<name>.svg` | SVG | `<weight>` is `regular`, `bold`, `fill`, …; non-regular files carry a suffix (`house-fill.svg`). |
| **Tabler** (single SVG) | `https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/<style>/<name>.svg` | SVG | `<style>` is `outline` or `filled`. No official Flutter package; build a font (above). |
| **Iconify** | `https://api.iconify.design/<set>/<icon>.svg` | SVG | Each set has **its own licence**. Look it up on icon-sets.iconify.design before using a glyph. |
| **Open Peeps** | the `cdn.prod.website-files.com/…/<id>_peep-<n>.svg` links in the "Grab and go" grid on openpeeps.com | SVG / PNG | Copy the link from the page; the IDs are not guessable. |
| **Transparent Textures** | `https://www.transparenttextures.com/patterns/<name>.png` | tileable PNG | "Attribution appreciated". Record it anyway. |
| **Fluent UI System Icons** | `https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/<Name>/SVG/ic_fluent_<name>_<size>_<regular\|filled>.svg` | SVG | `<Name>` is the Title Case folder (`Home`), and `<name>` is snake_case (`home`). |
| **Heroicons** | `https://unpkg.com/heroicons@2/<24/outline\|24/solid\|20/solid\|16/solid>/<name>.svg` | SVG | |
| **Bootstrap Icons** | `https://unpkg.com/bootstrap-icons@latest/icons/<name>.svg` | SVG | |
| **Iconoir** | `https://raw.githubusercontent.com/iconoir-icons/iconoir/main/icons/<regular\|solid>/<name>.svg` | SVG | |
| **Remix Icon** | `https://unpkg.com/remixicon@latest/icons/<Category>/<name>-<line\|fill>.svg` | SVG | `<Category>` is Title Case (`Buildings`, `System`). Not for app icons or logos (§3.3). |
| **MingCute** | `https://raw.githubusercontent.com/Richard9394/MingCute/main/packages/svg/<core-regular\|core-filled>/<name>.svg` | SVG | The old `svg/<category>/…` layout is gone (404). |
| **Material Symbols** (single SVG) | `https://fonts.gstatic.com/s/i/short-term/release/materialsymbols<outlined\|rounded\|sharp>/<name>/default/24px.svg` | SVG | Every file is named `24px.svg`. **Pass `--filename <name>.svg`**, or the second download overwrites the first. |
| **Font Awesome Free** (SVG) | `https://unpkg.com/@fortawesome/fontawesome-free@latest/svgs/<solid\|regular\|brands>/<name>.svg` | SVG | SVGs are **CC BY 4.0**, so they need on-screen credit. `brands/` is third-party trademarks (trap 6). |
| **Pictogrammers MDI** | `https://unpkg.com/@mdi/svg@latest/svg/<name>.svg` | SVG | |
| **Carbon** | `https://unpkg.com/@carbon/icons@latest/svg/32/<name>.svg` | SVG | |
| **Octicons** | `https://unpkg.com/@primer/octicons@latest/build/svg/<name>-<16\|24>.svg` | SVG | |
| **Boxicons** | `https://unpkg.com/boxicons@latest/svg/<regular\|solid\|logos>/bx<-\|s-\|l->-<name>.svg` | SVG | `logos/` is third-party trademarks (trap 6). |
| **Pixelarticons** | `https://raw.githubusercontent.com/halfmage/pixelarticons/master/svg/<name>.svg` | SVG | |
| **Fluent Emoji** | `https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/<Name>/<3D\|Color\|Flat\|High Contrast>/<name>_<3d\|color\|flat\|high_contrast>.<png\|svg>` | PNG (3D) / SVG | `<Name>` is the folder name (`Rocket`, `Party popper`). URL-encode spaces as `%20`. Skin-tone emoji have one more folder level (`Default/`, `Light/`, …). |
| **Noto Emoji** | `https://raw.githubusercontent.com/googlefonts/noto-emoji/main/<2D\|3D>/png/<32\|128\|512>/emoji_u<codepoint>.png`, or `…/2D/svg/emoji_u<codepoint>.svg` | PNG / SVG | Lower-case hex code point, with sequences joined by `_` (`emoji_u1f468_200d_1f4bb`). |
| **Noto Animated Emoji** | `https://fonts.gstatic.com/s/e/notoemoji/latest/<codepoint>/lottie.json` (also `512.webp`, `512.gif`) | Lottie JSON | **Pass `--filename <name>.json`**, since every file is `lottie.json`. CC BY 4.0, so it needs on-screen credit. `latest` is a rolling endpoint, so bundle the file; do not point `Lottie.network` at it. |
| **Twemoji** | `https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/<svg\|72x72>/<codepoint>.<svg\|png>` | SVG / PNG | CC BY 4.0. |
| **OpenMoji** | `https://openmoji.org/data/color/svg/<CODEPOINT>.svg` | SVG | Upper-case code point. CC BY-SA 4.0, so do not edit. |
| **DiceBear** | `https://api.dicebear.com/10.x/<style>/<svg\|png>?seed=<seed>` | SVG / PNG | **Pass `--filename <seed>.svg`**. The URL path ends in `svg`, which would otherwise become the filename. Check the style's licence first (see Emoji and avatars). |
| **Open Doodles** | `https://opendoodles.s3-us-west-1.amazonaws.com/<name>.<svg\|png\|gif>` | SVG / PNG | Names are on the page's SVG/PNG links (`coffee`, `reading-side`, `meditating`, …). CC0. |
| **GitHub font releases** | `https://github.com/<owner>/<repo>/releases/download/<tag>/<asset>.zip`, e.g. `vercel/geist-font` `v1.7.2` `geist-font-v1.7.2.zip` | zip | Get `<tag>` and `<asset>` from `api.github.com/repos/<o>/<r>/releases/latest`. Filter with `--only 'ttf/.*Geist-(Regular\|Medium\|SemiBold)\.ttf$\|OFL\.txt$' --flatten`. |

A Fontshare zip holds every format and weight. Filter it down to what you ship:

```bash
# Static weights → satoshi_regular.ttf, satoshi_medium.ttf, satoshi_bold.ttf, ffl.txt
python3 <skill>/scripts/fetch_asset.py --url https://api.fontshare.com/v2/fonts/download/satoshi \
    --only 'WEB/fonts/Satoshi-(Regular|Medium|Bold)\.ttf$|License/' --flatten \
    --dest assets/fonts --name Satoshi --author "Indian Type Foundry" \
    --license "ITF Free Font License" --source https://www.fontshare.com/fonts/satoshi --apply

# One variable file instead → satoshi_variable.ttf (+ italic), ffl.txt
    --only 'Fonts/TTF/|License/' --flatten
```

**Hand download only.** For these sources, download in a browser and import with `--local <file> --source <page>`:

| Source | Why |
|---|---|
| unDraw, Storyset (Freepik), Flaticon | The terms forbid scripted downloads, and `fetch_asset.py` refuses these hosts (`licensing.md` trap 9) |
| Humaaans | Distributed through Gumroad, so the link is an HTML checkout page |
| Rive Community, LottieFiles, Lordicon | Download sits behind a JS button and usually a login |
| Blush, DrawKit, HugeIcons (web) | Per-item download flow in the browser (HugeIcons is also available as the `hugeicons` pub package) |
| 3dicons | Full pack via Gumroad. Site thumbnails come from an undocumented bucket and top out at 400px |
| SVG Repo | Behind a Vercel bot checkpoint. The licence is also **per icon** (CC0, MIT, CC BY, and some GPL), so read each one |

## Checked and rejected

These show up in "free asset" lists. Each was checked on **2026-09-23** and fails for the stated reason. Do not propose them without new evidence.

| Source | Why not |
|---|---|
| **ManyPixels gallery** | The licence page itself warns that if the illustrations are central to what you do, "e.g. … add them in an app", you "probably should not proceed". It also forbids "automated and non-automated ways to link, embed". The permission for app use is too ambiguous to rely on. |
| **Solar icons** (`solar_icons`) | The upstream repo (`480-Design/Solar-Icon-Set`) publishes no licence file. The pub package's BSD-3 covers the Dart code, not the glyphs, so the glyph licence cannot be established. |
| **Iconsax** (`iconsax`, `iconsax_flutter`) | Same problem: the upstream repo (`lusaxweb/iconsax`) has no licence. The package's BSD-3 covers only the wrapper. |
| **Simple Icons** | The SVG files are CC0, but every icon is a third-party brand mark (trap 6). Use one only where that brand's own guidelines allow it, such as a "Sign in with …" button, and follow those guidelines rather than the CC0. |
| **Feather** | MIT, but it has 287 icons and no longer grows; the last release, 4.29.2 in 2024, was maintenance only. Lucide is its maintained fork, with the same visual style and 1400+ icons. |

**Tools, not downloads.** Haikei, Hero Patterns, Coolors, Realtime Colors and Material Theme Builder are generators: you configure the result on the site and export it. The Figma kits are layout reference only.

## Verification before proposing anything

For each candidate, be able to answer all five, and put the answers in front of the user:

1. Exact licence, from the page — not from this file, and not from memory.
2. Attribution required? If yes, it must reach `assets/CREDITS.md` **and** the About screen.
3. Transparent background, or a baked one that will break dark mode?
4. Format that Flutter can use directly — SVG, TTF, `.riv`, WebP. A `.ai`, `.psd` or `.fig` download is not an asset.
5. Does it match the locked direction, or is it just good? Good-and-off-direction is the more expensive mistake.
