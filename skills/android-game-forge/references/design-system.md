# Locked design system

Nothing here is a suggestion. Pick one palette, then assemble. Inventing a fifth palette, a third font, or a 14dp spacing step is the failure mode this file exists to prevent.

Every contrast number below was computed, not estimated, and `scripts/check-contrast.sh` re-computes them from the `Palette.kt` you actually generate. If you change a hex, that script will catch you.

## Palette selection

| Genre | Preset |
|-------|--------|
| Action, arcade, reflex | **NEON** |
| Sci-fi, space, tech | **SPACE** |
| Puzzle, word, cozy, calm | **PAPER** |
| Match-3, kids, idle, casual | **CANDY** |

## The layering law

Read this before the hex table. Almost every ugly generated screen comes from putting the right colour on the wrong layer.

There are exactly **three** places text can sit, and each has its own foreground tokens:

| Layer | What it is | Text tokens allowed |
|-------|-----------|---------------------|
| **background** | the `bgTop → bgBottom` gradient, behind everything | `onBg`, `onBgMuted` |
| **surface** | `GlassPanel`, `HudChip`, `GameOverlay`, any filled card | `textPrimary`, `textSecondary`, `textTertiary`, `primaryInk`, `accentInk`, `success`, `warning`, `danger` |
| **fill** | inside a `primary` or `accent` filled shape (buttons, chips) | `onPrimary`, `onAccent` |

Three rules follow, and they are non-negotiable:

1. **`primary` and `accent` are fill colours. They are never text.** On light presets a raw `primary` on the background measures 2.5:1 — legible to the person who picked it, invisible to everyone else. When you need coloured *text*, use `primaryInk` / `accentInk`, which are the same hue solved to clear 4.5:1 on `surface`.
2. **`textPrimary/Secondary/Tertiary` belong on `surface`, never on the background.** On CANDY, `textSecondary` on the raw gradient measures **1.1:1**. If a screen needs body text over the gradient, either wrap it in a `GlassPanel` or use `onBg`/`onBgMuted`.
3. **The semantic triple lives on `surface`.** It is per-palette, not global: the bright `#3DD68C` green that reads beautifully on NEON's navy measures 1.8:1 on PAPER's cream, so the light presets carry darkened variants.

## Palettes

Seventeen tokens each. Copy them **character for character** — `#FF3DA6` becomes `Color(0xFFFF3DA6)`: prefix `0xFF`, then the six digits unchanged.

```
NEON  · dark · glow STRONG · Orbitron + Inter
  bgTop #0B0F2B   bgBottom #1A0B2E   surface #1C2145   stroke white@12%
  primary #00E5FF   accent #FF3DA6    onPrimary #00606B   onAccent #56002F
  primaryInk #00E5FF   accentInk #FF3DA6
  textPrimary #F2F5FF   textSecondary #B9C0E0   textTertiary #838BAE
  onBg #F2F5FF   onBgMuted #B9C0E0
  success #3DD68C   warning #FFB020   danger #FF5C5C

SPACE · dark · glow STRONG · Space Grotesk + Inter
  bgTop #040A1F   bgBottom #0E1B3D   surface #15234A   stroke white@12%
  primary #6C8CFF   accent #FFC978    onPrimary #001C80   onAccent #824E00
  primaryInk #6C8CFF   accentInk #FFC978
  textPrimary #EAF0FF   textSecondary #A9B6DC   textTertiary #828DB1
  onBg #EAF0FF   onBgMuted #A9B6DC
  success #3DD68C   warning #FFB020   danger #FF5C5C

PAPER · light · glow OFF · Fraunces + Nunito
  bgTop #FBF3E4   bgBottom #F3E6D0   surface #FFFBF2   stroke black@8%
  primary #E9714B   accent #2E9E8F    onPrimary #4F1A0A   onAccent #0D2B27
  primaryInk #CE4519   accentInk #257E72
  textPrimary #2B2118   textSecondary #6B5B4B   textTertiary #82715D
  onBg #2B2118   onBgMuted #6B5B4B
  success #1C8251   warning #A06700   danger #E60000

CANDY · dark bg, light surface · glow SOFT · Baloo 2 + Nunito
  bgTop #3A24B8   bgBottom #7C29C6   surface #FFFFFF   stroke white@14%
  primary #FF6B9D   accent #FFD166    onPrimary #700026   onAccent #7A5600
  primaryInk #EB004F   accentInk #996B00
  textPrimary #2A1B4A   textSecondary #6E5F91   textTertiary #7D6BA5
  onBg #FFFFFF   onBgMuted #D9C9FF
  success #1C8653   warning #A56A00   danger #EB0000
```

CANDY's gradient is a deep violet, not a pastel one. That is deliberate: on the old mid-purple, hot pink `#FF6B9D` measured 1.9:1 and simply dissolved. Deep violet is what makes candy pink and gold *pop* — the palette got both more accessible and more vivid at the same time.

`GamePalette` therefore looks like:

```kotlin
data class GamePalette(
    val bgTop: Color, val bgBottom: Color, val surface: Color, val stroke: Color,
    val primary: Color, val accent: Color, val onPrimary: Color, val onAccent: Color,
    val primaryInk: Color, val accentInk: Color,
    val textPrimary: Color, val textSecondary: Color, val textTertiary: Color,
    val onBg: Color, val onBgMuted: Color,
    val success: Color, val warning: Color, val danger: Color,
    val glow: GlowLevel,
)
```

`Palette.kt` is the **only** file in the project allowed to contain a colour literal. Screens read `LocalPalette.current.primary`. This is grep-enforced in `scripts/check.sh`, and it is what makes a palette swap a one-line change instead of a refactor.

## Tokens

```
SPACING  xs 4 · sm 8 · md 12 · lg 16 · xl 24 · xxl 32 · xxxl 48
         screen gutter 20 · minimum touch target 48
RADIUS   sm 10 · md 18 · lg 28 · pill 999
MOTION   fast 120 · base 220 · slow 400 · ambient 6000 (ms)
EASING   EaseOut    cubic(0.16, 1.00, 0.30, 1.00)
         Overshoot  cubic(0.34, 1.56, 0.64, 1.00)   <- anything that appears
GLOW     radius sm 12 · md 24 · lg 48 (dp)
         alpha  STRONG 0.55 · SOFT 0.28 · OFF 0.0    <- per preset, above
```

Overshoot on entry, EaseOut on exit, and exits run ~40% faster than entries. A UI where things leave as slowly as they arrive feels sluggish even when every duration is "correct".

**There is no elevation token and no Material `shadowElevation`.** Depth is expressed as `stroke` + `glow` only. A Material drop shadow over a gradient background renders as a grey smear and is an instant tell that the theme was not designed.

## Type scale

| Role | Size / line height | Weight | Family | Notes |
|------|--------------------|--------|--------|-------|
| hero | 44 / 52 | 700 | display | |
| title | 28 / 34 | 700 | display | |
| score | 34 / 38 | 700 | display | tabular figures |
| section | 20 / 26 | 600 | ui | |
| body | 16 / 24 | 400 | ui | |
| button | 17 / 20 | 600 | ui | |
| label | 13 / 16 | 600 | ui | UPPERCASE, +0.8 tracking |
| caption | 13 / 18 | 400 | ui | |

Every role carries an explicit `lineHeight`. Leaving it to the Compose default gives eight different vertical rhythms in one app, which reads as sloppy long before anyone can name why.

Two font families maximum. Nothing below 13sp. **Scores always use the display font** — a score in the UI font reads as a form field, not an achievement.

### Fonts are mandatory, not optional

```bash
bash "$SKILL/scripts/fetch-fonts.sh" <PRESET>     # from the project root
```

This downloads the two OFL variable fonts into `res/font/` and prints attribution lines for `ATTRIBUTION.md`.

**There is no `FontFamily.Default` fallback.** The four palettes get their entire personality from Orbitron / Space Grotesk / Fraunces / Baloo 2; strip the typography and what remains is four colour schemes on Roboto — precisely the "looks generated" outcome this whole file exists to prevent. If the download fails, that is a **FAIL to report**, not a fallback to take silently.

These are variable fonts, so one file carries the whole weight axis:

```kotlin
private val display = FontFamily(
    Font(R.font.orbitron, FontWeight.Normal,
         variationSettings = FontVariation.Settings(FontVariation.weight(400))),
    Font(R.font.orbitron, FontWeight.Bold,
         variationSettings = FontVariation.Settings(FontVariation.weight(700))),
)
```

`FontVariation` needs **API 26**, which is why `minSdk` is 26 and not 24. On API 24–25 Android ignores the `wght` axis and every "bold" score silently renders at regular weight. The two lost API levels are worth well under half a percent of devices; the typography is the product.

## Structure

```kotlin
ui/theme/Tokens.kt    // Spacing, Radius, Motion, Easing, Glow objects — all dp/ms values here
ui/theme/Palette.kt   // data class GamePalette + the 4 presets + LocalPalette CompositionLocal
ui/theme/Type.kt      // AppType: TextStyle per role above
ui/theme/Theme.kt     // GameTheme { CompositionLocalProvider(LocalPalette provides preset) }
```

## Component library

Write these into `ui/components/` **before** any screen. Screens compose only from this list. All twelve must exist — `scripts/check.sh` checks for each file by name, because a "design system" with four of its twelve components written is just four components.

| Component | Spec |
|-----------|------|
| `ScreenScaffold(topBar, content, buttons)` | Box(bg gradient) → `AnimatedGameBackground` → Column with `WindowInsets.safeDrawing` + 20dp gutter → 48dp top bar → content → bottom button stack (12dp gaps, 24dp bottom pad). **Every screen uses this**, so insets and gutter are correct in one place instead of seven. |
| `GameButton(Primary\|Secondary\|Ghost)` | Pill, `heightIn(min = 56.dp)`. Primary: primary→accent gradient fill, label in `onPrimary`. Secondary: surface fill + 1dp stroke, label `textPrimary`. Ghost: no fill, label `onBg`. Press-scales to 0.94 over 120ms. Haptic + SFX on tap. |
| `IconTapButton(icon, label)` | 48dp square, radius md, translucent surface, 1dp stroke. **`label` is required** and becomes the `contentDescription`. |
| `GlassPanel` | Surface at 88% alpha, radius lg, 1dp stroke, padding xl, glow at the preset's level. This is the standard host for body text over the gradient. |
| `HudChip(label, value)` | Pill, surface fill (so the text triple applies), UPPERCASE `label` + display-font `value`. |
| `AnimatedCounter(value)` | Tweens over 220ms **and** pops to 1.18× on change. Every user-visible number uses this. |
| `AnimatedGameBackground` | 5 drifting radial-gradient blobs in primary/accent at 14–20% alpha, infinite transition. Renders one static frame when `reduceMotion` is on, and **stops animating while a run is live** — see below. |
| `GameOverlay` | 62% black scrim + GlassPanel scaling 0.85→1 with Overshoot. |
| `ProgressPill` | Animated gradient fill. |
| `ParticleSystem` | `burst(x, y, colors, count)` + gravity + fade-out. Pooled — no allocation per frame. |
| `rememberShake(trigger)` | Decaying sine offset over 260ms, returned as an offset modifier. Returns `Offset.Zero` when `reduceMotion` is on. |
| `GameText(text, style, color)` | Thin wrapper over `Text` bound to `AppType` + palette. Exists so screens never hand-set `fontSize` or `color`. |

Screen files must contain **no** raw `Button`/`OutlinedButton`/`TextButton`, no colour literal, no numeric `.dp`, and no inline `fontSize =` or `color = Color(...)`. Plain `Text` with an `AppType` style is acceptable; `Text` with inline sizing is not — that is where a design system quietly dies.

## Canvas art direction

The design system above governs the menus. This section governs the **game screen**, which is where the player spends ninety percent of their time. "Procedural" is a technique, not an art direction; without the rules below, two runs of this skill produce two games that look nothing alike in the one place it matters.

All numbers are **virtual units (vu)** in the 1000 × 1778 space, so they scale with the device instead of against it.

```
SHAPE      Pick ONE family at brief time and use it for every entity:
             ROUND  circles, capsules, arcs
             EDGE   triangles, diamonds, chevrons
             BLOCK  rounded rects, corner radius = 12% of the shorter side
           Mixing families is the fastest way to make procedural art look accidental.

STROKE     hairline 2 · normal 4 · bold 8 · heavy 14 vu. Nothing else. Strokes are
           virtual units, so they never hairline out on a dense screen.

SIZE       player 64-96 · obstacle 80-140 · pickup 40-56 · particle 6-14 vu.
           Nothing the player must hit or dodge is under 56 vu.

DEPTH      Exactly three planes, drawn back to front:
             far   ambient blobs, starfield  — accent @ 10-16% alpha, no stroke, parallax 0.15x
             mid   terrain, scenery          — surface fill + 4vu stroke, parallax 1.0x
             near  player, pickups, threats, particles — full-chroma fill + glow, parallax 1.0x
           Nothing on `far` may be mistaken for a collider: keep it under 20% alpha and
           never give it full-chroma `primary`.

CONTRAST   The player entity is the highest-contrast object on screen at all times —
           >= 4.5:1 against BOTH bgTop and bgBottom. Threats read `danger`, rewards read
           `success` or `accent`, inert scenery reads `onBgMuted`. A player that reads the
           same as an obstacle is a bug, not a difficulty setting.

GLOW       Near plane only. Radius = 0.6x the entity radius, alpha from the preset's glow
           level. On PAPER (glow OFF) substitute a 4vu offset shadow at 12% instead.

PARTICLES  12-20 per burst, never above 24 · lifetime 380-620ms · size 6-14vu shrinking to
           0 · gravity 1400 vu/s^2 · colours drawn only from {primary, accent, success}.
           One burst per milestone. Continuous emission is banned except as a player trail.

TRAIL      A moving player leaves a 6-frame position trail at 30% alpha, same fill, no stroke.

BACKGROUND The Canvas never paints its own background colour. It draws over
           AnimatedGameBackground so the palette gradient stays continuous across all
           seven screens — that continuity is most of why the app feels like one product.
```

## Accessibility

These are as locked as the hex values. Each is checked in `scripts/check.sh`.

- **Every icon-only control carries a label.** `IconTapButton` takes a mandatory `label: String` and sets `Modifier.semantics { contentDescription = label }`. A game whose pause button is an unlabelled glyph is unusable with TalkBack.
- **`Prefs` carries `reduceMotion`, and Settings exposes it beside sound and haptics.** When on: `AnimatedGameBackground` renders one static frame, `rememberShake` returns `Offset.Zero`, particle counts halve, and screen transitions become a 120ms fade. Gameplay motion is untouched — this is a comfort setting, not an easy mode. Mandating constant screen shake with no opt-out is a real vestibular problem, not a style choice.
- **Containers use `heightIn(min = …)`, never fixed `height(…)`,** and all type is `sp`. At 200% font scale the row grows instead of clipping the text.
- **Never encode state in colour alone.** A `danger` entity also takes the heavy stroke weight; a new highscore gets different copy *and* particles, not just a different colour.

## Screen layout rules

Overlay content order, always: **title → big `AnimatedCounter` stat → stats row → primary CTA → secondary → ghost.** Consistent ordering is why players can hit "again" without reading.

- **HUD layout is fixed**: score `HudChip` top-centre, secondary stat (lives, level, timer) top-left, pause `IconTapButton` top-right. All three sit inside `safeDrawing` — a score under the punch-hole camera is the single most common generated-game layout bug.
- `Result` must visibly distinguish a new highscore — different copy *and* particles. Same screen for a record and a mediocre run wastes the best moment in the game.
- `HowToPlay` is under 25 words plus a visual. If it needs more, the input scheme is too complex.
- Layout survives a 320dp-wide screen **at 200% font scale**. Test with a narrow preview or an emulator.
