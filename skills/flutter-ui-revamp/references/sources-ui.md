# Asset sources — app UI

Read at Step 3, after the design direction is locked. Reading it earlier leads to picking assets you like rather than assets that match a decision.

**The selection rule: one pack per category.** A screen assembled from Lucide arrows, Phosphor tabs and one stray Material icon looks exactly like what it is. Pick the pack whose *whole set* fits, then live with its weaker icons — internal consistency beats per-icon perfection every time.

Licence column is the licence as published at the time of writing. **Re-read it on the page before downloading** — projects relicense, and a stale line in this file is not a defence.

## Icons

| Set | URL | Licence | Formats | Flutter package | API |
|---|---|---|---|---|---|
| **Lucide** | lucide.dev | ISC | SVG, font, PNG | `lucide_icons` (const `IconData`; preferred for bulk swap) | yes (unpkg / jsDelivr per-icon SVG) |
| **Phosphor** | phosphoricons.com | MIT | SVG, font | `phosphor_flutter` | via GitHub raw |
| **Tabler** | tabler.io/icons | MIT | SVG, font, PNG | none official — build a font | via GitHub raw |
| **Material Symbols** | fonts.google.com/icons | Apache-2.0 | SVG, variable font | built in (`Icons.*`) | Google Fonts API |
| **Ionicons** | ionic.io/ionicons | MIT | SVG, font | `ionicons` | via GitHub raw |
| **HugeIcons** | hugeicons.com | free tier MIT-ish, **check tier** | SVG | `hugeicons` | partial |
| **Iconify** | icon-sets.iconify.design | aggregator — **per-set licences vary** | SVG, JSON | none | yes, `api.iconify.design` |

Notes that decide the choice:

- **Lucide** — 1.5px stroke, geometric, 1400+ icons. The safe default for a minimal/modern direction. Prefer the **`lucide_icons`** package for revamps: it exposes const `IconData`, so `const Icon(LucideIcons.house)` stays const (see const hazard in `refactor-patterns.md`). Upstream Lucide renamed `home` → `house` — map `Icons.home` to `LucideIcons.house` and verify against the resolved package version after `flutter pub add`. (`lucide_flutter` exists on pub with a different API surface; do not mix both packages in one app.)
- **Phosphor** — six weights (thin → fill) from one family, which is why it wins for playful and for apps that need a filled/outlined tab-bar pair. In `phosphor_flutter` v2 the ergonomic API is a call — `PhosphorIcons.house()` — which is **not const**. Use the const constants (`PhosphorIconsRegular.house`) in bulk replacements.
- **Iconify** is not an icon set, it is 200 000 icons across ~150 sets with ~15 different licences. Excellent for finding one missing glyph, dangerous as a primary source: you inherit whichever licence that specific set carries.
- **Material Symbols** ships with Flutter. If the design direction is "clean Material 3", the honest answer is often *keep the icons* and spend the effort on colour, type and motion.

**When to build a custom icon font instead of adding a package:** you need fewer than ~40 icons, or you are mixing two sets deliberately (a brand glyph plus a standard set), or the package's tree-shaking is not trimming the unused thousands. Upload the SVGs to **fluttericon.com**, download the `.ttf` + generated Dart, and follow `integration-flutter.md § Custom icon font`. A 40-icon font is ~8 KB; a full icon package with tree-shaking disabled can be 200 KB+.

## Illustrations

| Source | URL | Licence | Formats | Notes |
|---|---|---|---|---|
| **unDraw** | undraw.co/illustrations | unDraw open licence (free commercial, no attribution) | SVG, PNG | **Recolour to your seed colour on the site before downloading.** Flat, transparent background — safe in dark mode. |
| **Storyset** | storyset.com | Freepik free — **attribution required** | SVG, PNG, animated SVG | Editable colour + optional built-in animation. Attribution is not optional; it belongs in CREDITS.md and on the About screen. |
| **Humaaans** | humaaans.com | CC BY 4.0 | SVG, Sketch, PNG | Mix-and-match human figures. Attribution required. |
| **Open Peeps** | openpeeps.com | CC0 | SVG, PNG, PSD | Hand-drawn people, no attribution. Best CC0 human illustration set. |
| **Popsy** | popsy.co/illustrations | free commercial, no attribution | SVG, PNG | Hand-drawn, playful, transparent. |
| **Blush** | blush.design | **per-collection**, many require a paid plan | SVG, PNG | Check the individual collection; several are not free. |
| **DrawKit** | drawkit.com | free packs: no attribution; check per pack | SVG, PNG | |

The dark-mode trap: an illustration exported with a baked white rectangle behind it shows a hard white slab on a dark surface. Every source above can export transparent — verify the exported file, do not assume it. `undraw` and `openpeeps` are transparent by default.

## Fonts

| Source | URL | Licence | Formats | API |
|---|---|---|---|---|
| **Google Fonts** | fonts.google.com | almost all OFL, a few Apache-2.0 | TTF, variable TTF, WOFF2 | yes — `fonts.gstatic.com`, and the `google_fonts` package |
| **Fontshare** | fontshare.com | free for commercial use, ITF licence | TTF, OTF, WOFF2, variable | no |
| **Fontsource** | fontsource.org | mirrors OFL/Apache fonts | TTF, WOFF2 | yes — npm/jsDelivr |
| **Uncut.wtf** | uncut.wtf | per-font, mostly OFL | TTF, OTF, variable | no |
| **Velvetyne** | velvetyne.fr | OFL | TTF, OTF | no |

**Fontshare** is the reason a Flutter app can stop looking like every other Flutter app — Satoshi, General Sans, Clash Display and Switzer are contemporary, well-hinted and free for commercial use, and none of them is Roboto. Download the TTF and bundle it. See `licensing.md § google_fonts` for why *bundling* beats the runtime-fetch package.

Pairing, and the hard limit of two families: one display family for headings, one text family for body and UI. A third family is a bug. If in doubt, one variable family across two weights beats two families badly paired.

## Animation

| Source | URL | Licence | Format | Flutter |
|---|---|---|---|---|
| **Rive Community** | rive.app/community | **per-file** — most CC BY, some all-rights-reserved | `.riv` | `rive` package |
| **LottieFiles Free** | lottiefiles.com/featured-free-animations | per-file; free tier often needs attribution | `.json`, `.lottie` | `lottie` package |
| **Lordicon free** | lordicon.com/icons?price=free | free with attribution | Lottie JSON, GIF | `lottie` |
| **useAnimations** | useanimations.com | free, attribution appreciated | Lottie JSON | `lottie` |

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
| **Coolors** | coolors.co | palette exploration | free |
| **Realtime Colors** | realtimecolors.com | palette previewed on a real layout | free |
| **Material Theme Builder** | material-foundation.github.io/material-theme-builder | full M3 `ColorScheme` from a seed, exportable as Dart | Apache-2.0 |

**Material Theme Builder is the one to actually use.** It emits a complete light + dark `ColorScheme` from a seed colour, tonally correct, with the contrast pairs already solved. Paste its Dart output into `lib/theme/app_colors.dart` rather than hand-picking hexes — hand-picked schemes are where the 3.1:1 body text comes from.

## Verification before proposing anything

For each candidate, be able to answer all five, and put the answers in front of the user:

1. Exact licence, from the page — not from this file, and not from memory.
2. Attribution required? If yes, it must reach `assets/CREDITS.md` **and** the About screen.
3. Transparent background, or a baked one that will break dark mode?
4. Format that Flutter can use directly — SVG, TTF, `.riv`, WebP. A `.ai`, `.psd` or `.fig` download is not an asset.
5. Does it match the locked direction, or is it just good? Good-and-off-direction is the more expensive mistake.
