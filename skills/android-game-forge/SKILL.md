---
name: android-game-forge
description: Build complete Kotlin + Jetpack Compose Android games from a short idea, with locked design system (4 palettes), component library, juice rules, and self-check. Use when the user wants to generate an Android game project from scratch.
---

# One-shot prompt (paste-anywhere version)

For models or tools that do not support skills. Paste everything inside the fence, then add your idea on the last line. Written in English deliberately — instruction-following degrades measurably on weaker models when the operative instructions are not in English. Ask for in-game text in whatever language you want; that is a separate line at the bottom.

---

You are a senior Android game developer and mobile UI designer. Build a COMPLETE, BUILDABLE
Kotlin + Jetpack Compose Android game from the idea at the bottom of this message.

Your visual taste is NOT part of this job. The design system below is fixed. Assemble from it.
Do not invent colours, fonts, spacing or easing. Do not use Material 3 default theme colours.

═══ STEP 1 · GAME BRIEF (output this first, then build) ═══
Title / Genre / Core loop (1 sentence) / Input (ONE of: tap, hold, drag, swipe) /
Win-lose / Session length (30-120s) / Difficulty ramp formula / Progression /
Palette preset / 3 signature juice moments.
If my idea is vague, decide the details yourself and state your assumptions. Ask at most 2 questions.

═══ STEP 2 · LOCKED DESIGN SYSTEM ═══
Pick ONE palette. Action/arcade → NEON. Sci-fi → SPACE. Puzzle/word/cozy → PAPER. Match3/kids/idle → CANDY.

NEON  : bgTop #0B0F2B bgBottom #1A0B2E surface #1C2145 primary #00E5FF accent #FF3DA6
        text #F2F5FF / #B9C0E0 / #7A82A8 · dark · glow ON · fonts Orbitron + Inter
SPACE : bgTop #040A1F bgBottom #0E1B3D surface #15234A primary #6C8CFF accent #FFC978
        text #EAF0FF / #A9B6DC / #6C79A3 · dark · glow ON · fonts Space Grotesk + Inter
PAPER : bgTop #FBF3E4 bgBottom #F3E6D0 surface #FFFBF2 primary #E9714B accent #2E9E8F
        text #2B2118 / #6B5B4B / #A1907C · light · glow OFF · fonts Fraunces + Nunito
CANDY : bgTop #6A5AE0 bgBottom #A96BE0 surface #FFFFFF primary #FF6B9D accent #FFD166
        text #2A1B4A / #6E5F91 / #A79BC2 · light · glow soft · fonts Baloo 2 + Nunito
(all presets also: success #3DD68C  warning #FFB020  danger #FF5C5C  stroke = 12% white on dark / 8% black on light)
(in Kotlin these become Color(0xFF + the six digits), e.g. #FF3DA6 → Color(0xFFFF3DA6))

SPACING  xs4 sm8 md12 lg16 xl24 xxl32 xxxl48 · screen gutter 20 · min touch 48
RADIUS   sm10 md18 lg28 pill999
MOTION   fast120 base220 slow400 ambient6000ms
EASING   EaseOut cubic(0.16,1,0.3,1) · Overshoot cubic(0.34,1.56,0.64,1) for anything appearing
TYPE     hero 44/48 bold display · title 28 bold display · score 34 bold display ·
         section 20 semibold ui · body 16 ui · button 17 semibold ui ·
         label 13 semibold ui +0.8 tracking UPPERCASE · caption 13 ui
         Max 2 font families. Nothing under 13sp. Scores ALWAYS use the display font.

Put these in ui/theme/Tokens.kt + Palette.kt + Type.kt + Theme.kt.
Expose the palette via a CompositionLocal. Screens read `palette.primary`, never a hex literal.

═══ STEP 3 · COMPONENT LIBRARY (write these first, in ui/components/) ═══
GameButton(Primary|Secondary|Ghost)  – pill, gradient primary→accent for Primary, 56dp min height,
                                       press-scale to 0.94 over 120ms, haptic + sfx on tap
IconTapButton                        – 48dp square, radius md, translucent surface + 1dp stroke
GlassPanel                           – surface 88% alpha, radius lg, 1dp stroke, padding xl, soft glow
HudChip(label, value)                – pill, UPPERCASE label + display-font value
AnimatedCounter(value)               – tweens 220ms AND pops to 1.18x scale on change
AnimatedGameBackground               – 5 drifting radial-gradient blobs in primary/accent at 14-20% alpha,
                                       infinite transition, ALWAYS on screen
GameOverlay                          – 62% black scrim + GlassPanel scaling 0.85→1 with Overshoot
ProgressPill                         – animated gradient fill
ParticleSystem                       – burst(x,y,colors,count) + gravity + fade-out
rememberShake(trigger)               – decaying sine offset, 260ms
Screens use ONLY these. No raw Button/Text/Color in any screen file.

═══ STEP 4 · ARCHITECTURE ═══
· Game state = plain Kotlin class with update(dt): List<GameEvent>. NOT Compose state.
· Frame loop: LaunchedEffect + withFrameNanos, dt CLAMPED to max 1/30s, increments one `frame` counter.
· ONE Canvas reads `frame` and draws everything. No composable per entity. No allocation in update/draw.
· Virtual world coords (1000 x 1778) scaled uniformly to canvas, so physics is device-independent.
· Feedback object: tap()/score()/hit()/gameOver()/win() → SoundPool + Vibrator together. Rate-limit tap to 40ms.
· SharedPreferences only: highscore, level, soundOn, hapticsOn, gamesPlayed. Load settings at startup.
· Navigation: sealed interface Screen + one mutableStateOf. NO navigation-compose, NO Hilt, NO Room, NO Lottie.
· Pause and Result are OVERLAYS above the live canvas, not separate screens.
· BackHandler: during play → open Pause, never exit.

═══ STEP 5 · MANDATORY SCREENS (all 7) ═══
Splash → Home → HowToPlay → Game+HUD → Pause → Result → Settings
Screen skeleton: Box(bgGradient) > AnimatedGameBackground > Column(safeDrawing insets + 20dp gutter)
                 > top bar 48dp > content > bottom button stack (12dp gaps, 24dp bottom pad)
Overlay content order, always: title → big AnimatedCounter stat → stats row → primary CTA → secondary → ghost.
Result must visibly distinguish a new highscore (different copy + particles).
HowToPlay: under 25 words + a visual.

═══ STEP 6 · JUICE RULES (non-negotiable) ═══
1. Every tap: visual scale + haptic + sound. All three. Missing one makes the game feel dead.
2. No static screen, ever.
3. No number snaps — everything counts up and pops.
4. Impact → screen shake. Reward milestone → particles (NOT on every point; constant confetti means nothing).
5. Things appear with Overshoot; they disappear ~40% faster with EaseOut.
6. Every screen transition animates.

═══ STEP 7 · ART ═══
Default to PROCEDURAL art: Compose Canvas circles, paths, gradients, glows, particles. It always renders,
scales to any screen, recolours with the palette, and keeps the APK tiny. Visual coherence beats asset
fidelity — mixing three free sprite styles looks cheaper than clean procedural shapes.
If you need real assets: kenney.nl (CC0), game-icons.net (CC-BY), fonts.google.com (OFL),
mixkit.co / pixabay sound-effects. Log every one in ATTRIBUTION.md with source + licence.
NEVER third-party IP (Mario, Pokémon, Flappy Bird, brand logos) — not even as a placeholder.
NEVER reference an R.raw/R.font/R.drawable that does not exist — stub it to a no-op instead.
Always ship a real adaptive launcher icon (vector glyph + palette background). The default robot icon
makes the whole build look unfinished.

═══ STEP 8 · DELIVER ═══
Full file tree with complete file contents:
settings.gradle.kts · build.gradle.kts · gradle.properties · app/build.gradle.kts ·
AndroidManifest.xml · res/{font,drawable,mipmap-anydpi-v26,raw,values} ·
MainActivity.kt · ui/theme/{Tokens,Palette,Type,Theme}.kt ·
ui/components/* · ui/screens/* · game/{GameConfig,GameState,Entities,Engine}.kt ·
platform/{SoundBank,Haptics,Prefs}.kt · README.md · ATTRIBUTION.md
Baseline: AGP 8.7.2 · Kotlin 2.0.21 · Compose BOM 2024.10.01 · compileSdk/targetSdk 35 · minSdk 24 · JVM 17
Plugins: com.android.application, org.jetbrains.kotlin.android, org.jetbrains.kotlin.plugin.compose
Portrait-locked. Edge-to-edge. FLAG_KEEP_SCREEN_ON during play. All strings in strings.xml.
Write EVERY import explicitly — unresolved references are the #1 failure mode in generated Compose projects.

═══ STEP 9 · SELF-CHECK (output this table, filled honestly) ═══
A Build: imports resolve · no missing R.* · versions consistent · package matches everywhere · no reachable TODO
B Layout: safeDrawing on every screen · 20dp gutter everywhere · touch targets ≥48dp · survives 320dp width
C System: zero hex outside Palette.kt · zero raw dp in screens · zero raw Button · one preset · two fonts · ≥4.5:1 contrast
D Juice: press-scale everywhere · haptic+sfx on every tap · animated bg on every screen · AnimatedCounter on
         every number · animated transitions · shake on impact · particles on reward · all 3 brief moments built
E Feel:  playable in 3s · smooth ramp · one-tap restart · deaths are readable · dt clamped
F Done:  all 7 screens reachable · back opens Pause · highscore persists · toggles work and persist ·
         highscore run looks different · README + ATTRIBUTION present
Report as: A x/5  B x/4  C x/6  D x/8  E x/5  F x/6  TOTAL x/34, plus honest notes on any FAIL.
Fix every fail before you finish. A fabricated all-pass is worse than an honest fail.

═══ MY IDEA ═══
$ARGUMENTS
In-game text language: <English | Vietnamese | both>

## Usage notes

- **If the model's output limit truncates the project**, run it in two passes: pass 1 = "Steps 1–3 only: brief + theme + components", pass 2 = "now Steps 4–9 using exactly the files you just wrote". Weak models handle two focused passes far better than one giant one.
- **If the model ignores the design system**, the fix is almost never a longer prompt. It is to run pass 1 alone, verify `Palette.kt` matches the preset character-for-character, and only then continue.
- **Keep the palette hex values exact.** They are chosen for contrast ratios. "Close enough" colours are exactly how generated games end up looking generated.
