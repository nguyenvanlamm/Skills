# Style recipes

Read at **Step 2** when locking design direction. Each recipe is a complete,
internally consistent pack: icon set, fonts, radius character, illustration
voice, motion, and spacing. Pick **one** recipe (or the user's `style` input),
paste its fields into `.revamp/design-direction.md`, then stop inventing pairings.

Licence column is a hint only — re-read on the source page before Step 4
(`licensing.md`).

## Recipes

### `minimal-modern`

| Slot | Choice |
|---|---|
| Seed default | `#4F46E5` (indigo) |
| Icons | **Lucide** (ISC) — 1.5px stroke, const `IconData` via `lucide_icons` |
| Fonts | **Clash Display** 600 (headings) + **Satoshi** 400/500/700 (body) — Fontshare |
| Illustration | unDraw, flat, recolour to seed, transparent |
| Animation | Rive loader + empty-state; skeletons for lists |
| Spacing | 4 / 8 / 16 / 24 / 32 / 48 |
| Radius | 8 / 12 / 18 / pill |
| Surfaces | Low elevation, tonal `surfaceContainer*`, hairline `outlineVariant` |
| Motion | 180–280 ms easeOutCubic; fade-through routes; light haptics on primary only |
| Dark mode | Required — `ColorScheme.fromSeed` both brightnesses |

Best for: productivity, SaaS, finance, settings-heavy apps that currently look like a Flutter demo.

### `playful-rounded`

| Slot | Choice |
|---|---|
| Seed default | `#7C3AED` or a warm coral `#F97316` |
| Icons | **Phosphor** (MIT) — regular + fill pair for tabs; use **const** `PhosphorIconsRegular.*` / `Fill.*` |
| Fonts | **Nunito** or **Plus Jakarta Sans** (OFL, Google Fonts — **bundle** TTF) |
| Illustration | Open Peeps (CC0) or Popsy; soft, human, transparent |
| Animation | Lottie empty/success bursts; playful press-scale 0.96 |
| Spacing | 4 / 8 / 16 / 24 / 32 / 48 |
| Radius | 12 / 16 / 24 / pill (softer than minimal) |
| Surfaces | Soft fills, optional pastel `primaryContainer` chips |
| Motion | Springier curves (`easeOutBack` sparingly); selectionClick haptics |
| Dark mode | Required |

Best for: consumer social, kids-adjacent (non-Families policy), onboarding-heavy apps.

### `neo-brutalism`

| Slot | Choice |
|---|---|
| Seed default | `#111111` + one hard accent `#FFE600` or `#FF5C8A` |
| Icons | **Tabler** or **Lucide** — geometric, never soft duotone |
| Fonts | **Space Grotesk** (headings) + **Inter** (body) — OFL, bundled |
| Illustration | Flat geometric / Haikei blobs with hard strokes; high contrast |
| Animation | Minimal — hard cuts OK; short 100 ms colour flashes over floaty motion |
| Spacing | 4 / 8 / 16 / 24 / 32 |
| Radius | **0 / 4 / 8** only — no pills on primary cards |
| Surfaces | Hard borders (`outline` 2–3 px), offset box shadows, raw paper/ink |
| Motion | Snappy, no Hero morphs that soften edges |
| Dark mode | Inverted ink/paper; keep accent saturated |

Best for: marketing tools, indie brands, portfolios. Clashes with Material defaults — expect more component overrides.

### `casual-game`

| Slot | Choice |
|---|---|
| Seed default | Warm UI accent matching the pack (often Kenney blue/green) |
| Icons | **Game-icons.net** (CC BY → Credits screen) for abilities; pack glyphs for chrome |
| Fonts | **Baloo 2** or **Fredoka** (OFL) for HUD; one family only |
| UI pack | **Kenney UI Pack** (CC0) — panels/buttons with documented 9-slice insets |
| Audio | Kenney Interface Sounds (CC0); SFX mono OGG |
| Animation | Button press scale + SFX; win/lose stingers; no full-screen Lottie menus |
| Spacing | Follow pack metrics; HUD padding 8 / 12 / 16 |
| Radius | From pack (often chunky 8–12 px pixel-ish) |
| Surfaces | 9-slice panels only — never `BoxFit.fill` on decorative frames |
| Dark mode | Optional; many packs are authored light — test readability |

Best for: Flame / casual 2D. See `sources-game.md`. Stay inside one pack family.

### `dark-premium`

| Slot | Choice |
|---|---|
| Seed default | `#0F172A` surface world + accent `#38BDF8` or gold `#D4AF37` |
| Icons | **Lucide** or **Phosphor thin/light** — airy strokes on dark |
| Fonts | **Syne** or **Clash Display** (headings) + **Satoshi** / **General Sans** (body) |
| Illustration | unDraw recolored to accent on transparent; avoid baked white |
| Animation | Rive subtle idle; slow fade-through; restrained haptics |
| Spacing | 4 / 8 / 16 / 24 / 32 / 48 |
| Radius | 12 / 16 / 20 / pill |
| Surfaces | `surface` / `surfaceContainerHigh` hierarchy; hairline borders; no heavy Material shadows |
| Motion | 220–320 ms; opacity + 4–8 dp slide; premium feels *quiet* |
| Dark mode | **Primary** — design dark first, light second |

Best for: fintech, creator tools, pro media. Pair with high contrast checks (body ≥ 4.5:1).

---

## How to use at Step 2

1. If the user passed `style`, load that recipe.
2. If not, propose **two or three** recipes (not all five) that fit the audit (game → `casual-game`; already-dark UI → `dark-premium`; generic Material demo → `minimal-modern` vs `playful-rounded`).
3. Each proposal is the recipe table filled with the seed (user's or default) — user picks a **look**, not a form.
4. Write `.revamp/design-direction.md` from the chosen recipe fields only.
5. Do **not** mix recipes (Lucide + Phosphor tabs, Kenney panel + CraftPix button, three fonts).

## `keep` overrides

When the user says `keep: font` or `keep: colours`, take every other slot from the recipe and leave the kept slots as the project already has them (from audit). Document the keep in design-direction under `Out of scope` / `Kept`.
