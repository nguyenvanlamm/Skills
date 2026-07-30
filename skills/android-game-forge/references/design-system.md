# Locked design system

Nothing here is a suggestion. Pick one palette, then assemble. Inventing a fifth palette, a third font, or a 14dp spacing step is the failure mode this file exists to prevent.

## Palette selection

| Genre | Preset |
|-------|--------|
| Action, arcade, reflex | **NEON** |
| Sci-fi, space, tech | **SPACE** |
| Puzzle, word, cozy, calm | **PAPER** |
| Match-3, kids, idle, casual | **CANDY** |

```
NEON   bgTop #0B0F2B  bgBottom #1A0B2E  surface #1C2145  primary #00E5FF  accent #FF3DA6
       text #F2F5FF / #B9C0E0 / #7A82A8   dark · glow ON     · Orbitron + Inter
SPACE  bgTop #040A1F  bgBottom #0E1B3D  surface #15234A  primary #6C8CFF  accent #FFC978
       text #EAF0FF / #A9B6DC / #6C79A3   dark · glow ON     · Space Grotesk + Inter
PAPER  bgTop #FBF3E4  bgBottom #F3E6D0  surface #FFFBF2  primary #E9714B  accent #2E9E8F
       text #2B2118 / #6B5B4B / #A1907C   light · glow OFF   · Fraunces + Nunito
CANDY  bgTop #6A5AE0  bgBottom #A96BE0  surface #FFFFFF  primary #FF6B9D  accent #FFD166
       text #2A1B4A / #6E5F91 / #A79BC2   light · glow soft  · Baloo 2 + Nunito
```

Every preset also carries: `success #3DD68C`, `warning #FFB020`, `danger #FF5C5C`, and `stroke` = 12% white on dark presets / 8% black on light ones.

Text triple is `textPrimary / textSecondary / textTertiary`. In Kotlin, `#FF3DA6` → `Color(0xFFFF3DA6)` — prefix `0xFF`, then the six digits unchanged.

**Copy the hex values character for character.** They are picked for ≥4.5:1 contrast against their own background. A "nicer" nearby colour silently breaks accessibility and is how generated games end up looking generated.

## Tokens

```
SPACING  xs 4 · sm 8 · md 12 · lg 16 · xl 24 · xxl 32 · xxxl 48
         screen gutter 20 · minimum touch target 48
RADIUS   sm 10 · md 18 · lg 28 · pill 999
MOTION   fast 120 · base 220 · slow 400 · ambient 6000 (ms)
EASING   EaseOut    cubic(0.16, 1.00, 0.30, 1.00)
         Overshoot  cubic(0.34, 1.56, 0.64, 1.00)   ← anything that appears
```

Overshoot on entry, EaseOut on exit, and exits run ~40% faster than entries. A UI where things leave as slowly as they arrive feels sluggish even when every duration is "correct".

## Type scale

| Role | Size / line | Weight | Family |
|------|-------------|--------|--------|
| hero | 44 / 48 | bold | display |
| title | 28 | bold | display |
| score | 34 | bold | display |
| section | 20 | semibold | ui |
| body | 16 | regular | ui |
| button | 17 | semibold | ui |
| label | 13 | semibold | ui | UPPERCASE, +0.8 tracking |
| caption | 13 | regular | ui |

Two font families maximum. Nothing below 13sp. **Scores always use the display font** — a score in the UI font reads as a form field, not an achievement.

Fonts come from Google Fonts (OFL). Either bundle the `.ttf` files in `res/font/` and reference them, or fall back to `FontFamily.Default` for both roles — **never** reference an `R.font.*` that is not on disk. A missing font resource is a compile error, and it is one of the two most common failures in generated Compose projects.

## Structure

```kotlin
ui/theme/Tokens.kt    // Spacing, Radius, Motion, Easing objects — all dp/ms values live here
ui/theme/Palette.kt   // data class GamePalette + the 4 presets + LocalPalette CompositionLocal
ui/theme/Type.kt      // AppType: TextStyle per role above
ui/theme/Theme.kt     // GameTheme { CompositionLocalProvider(LocalPalette provides preset) }
```

`Palette.kt` is the **only** file in the project allowed to contain a colour literal. Screens read `LocalPalette.current.primary`. This is grep-enforced in `scripts/check.sh`, and it is what makes a palette swap a one-line change instead of a refactor.

## Component library

Write these into `ui/components/` **before** any screen. Screens compose only from this list.

| Component | Spec |
|-----------|------|
| `ScreenScaffold(topBar, content, buttons)` | Box(bg gradient) → `AnimatedGameBackground` → Column with `WindowInsets.safeDrawing` + 20dp gutter → 48dp top bar → content → bottom button stack (12dp gaps, 24dp bottom pad). **Every screen uses this**, so insets and gutter are correct in one place instead of seven. |
| `GameButton(Primary\|Secondary\|Ghost)` | Pill. Primary gets a primary→accent gradient. 56dp min height. Press-scales to 0.94 over 120ms. Haptic + SFX on tap. |
| `IconTapButton` | 48dp square, radius md, translucent surface, 1dp stroke. |
| `GlassPanel` | Surface at 88% alpha, radius lg, 1dp stroke, padding xl, soft glow when the preset has glow on. |
| `HudChip(label, value)` | Pill with UPPERCASE label + display-font value. |
| `AnimatedCounter(value)` | Tweens over 220ms **and** pops to 1.18× on change. Every user-visible number uses this. |
| `AnimatedGameBackground` | 5 drifting radial-gradient blobs in primary/accent at 14–20% alpha, infinite transition. On screen always. |
| `GameOverlay` | 62% black scrim + GlassPanel scaling 0.85→1 with Overshoot. |
| `ProgressPill` | Animated gradient fill. |
| `ParticleSystem` | `burst(x, y, colors, count)` + gravity + fade-out. Pooled — no allocation per frame. |
| `rememberShake(trigger)` | Decaying sine offset over 260ms, returned as an offset modifier. |
| `GameText(text, style, color)` | Thin wrapper over `Text` bound to `AppType` + palette. Exists so screens never hand-set `fontSize` or `color`. |

Screen files must contain **no** raw `Button`/`OutlinedButton`/`TextButton`, no colour literal, no numeric `.dp`, and no inline `fontSize =` or `color = Color(...)`. Plain `Text` with an `AppType` style is acceptable; `Text` with inline sizing is not — that is where a design system quietly dies.

## Screen layout rules

Overlay content order, always: **title → big `AnimatedCounter` stat → stats row → primary CTA → secondary → ghost.** Consistent ordering is why players can hit "again" without reading.

- `Result` must visibly distinguish a new highscore — different copy *and* particles. Same screen for a record and a mediocre run wastes the best moment in the game.
- `HowToPlay` is under 25 words plus a visual. If it needs more, the input scheme is too complex.
- Layout survives a 320dp-wide screen. Test with a narrow preview or an emulator at 320dp.
