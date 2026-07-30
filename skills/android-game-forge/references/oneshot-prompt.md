# One-shot prompt (paste-anywhere version)

For models or tools without skill support. Paste everything inside the fence, then add the idea on the last line.

Written in English deliberately — instruction-following degrades measurably on weaker models when the operative instructions are not in English. Ask for in-game text in any language you like; that is a separate line at the bottom.

Note what this version cannot do: nothing compiles the project, fetches the fonts, greps the design system, or computes a contrast ratio. The self-check is self-graded, so treat its score as a claim rather than a measurement — particularly the contrast and typography lines, which are the two easiest to assert and the two that most change how the result looks. Use the skill itself when a real build gate is available.

---

```
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

THE LAYERING LAW — read before writing Palette.kt. There are exactly 3 places text can sit:
  background (the bgTop→bgBottom gradient) → ONLY onBg, onBgMuted
  surface    (GlassPanel, HudChip, overlay) → textPrimary/Secondary/Tertiary, primaryInk,
                                              accentInk, success, warning, danger
  fill       (inside a primary/accent shape) → ONLY onPrimary, onAccent
primary and accent are FILL colours and are NEVER text — for coloured text use primaryInk/accentInk.
textPrimary/Secondary/Tertiary belong on surface, never on the gradient.
Putting the right colour on the wrong layer is what makes generated screens unreadable.

NEON  · dark · glow STRONG · Orbitron + Inter
  bgTop #0B0F2B  bgBottom #1A0B2E  surface #1C2145  stroke white@12%
  primary #00E5FF  accent #FF3DA6  onPrimary #00606B  onAccent #56002F
  primaryInk #00E5FF  accentInk #FF3DA6
  textPrimary #F2F5FF  textSecondary #B9C0E0  textTertiary #838BAE
  onBg #F2F5FF  onBgMuted #B9C0E0
  success #3DD68C  warning #FFB020  danger #FF5C5C
SPACE · dark · glow STRONG · Space Grotesk + Inter
  bgTop #040A1F  bgBottom #0E1B3D  surface #15234A  stroke white@12%
  primary #6C8CFF  accent #FFC978  onPrimary #001C80  onAccent #824E00
  primaryInk #6C8CFF  accentInk #FFC978
  textPrimary #EAF0FF  textSecondary #A9B6DC  textTertiary #828DB1
  onBg #EAF0FF  onBgMuted #A9B6DC
  success #3DD68C  warning #FFB020  danger #FF5C5C
PAPER · light · glow OFF · Fraunces + Nunito
  bgTop #FBF3E4  bgBottom #F3E6D0  surface #FFFBF2  stroke black@8%
  primary #E9714B  accent #2E9E8F  onPrimary #4F1A0A  onAccent #0D2B27
  primaryInk #CE4519  accentInk #257E72
  textPrimary #2B2118  textSecondary #6B5B4B  textTertiary #82715D
  onBg #2B2118  onBgMuted #6B5B4B
  success #1C8251  warning #A06700  danger #E60000
CANDY · deep-violet bg, white surface · glow SOFT · Baloo 2 + Nunito
  bgTop #3A24B8  bgBottom #7C29C6  surface #FFFFFF  stroke white@14%
  primary #FF6B9D  accent #FFD166  onPrimary #700026  onAccent #7A5600
  primaryInk #EB004F  accentInk #996B00
  textPrimary #2A1B4A  textSecondary #6E5F91  textTertiary #7D6BA5
  onBg #FFFFFF  onBgMuted #D9C9FF
  success #1C8653  warning #A56A00  danger #EB0000
(in Kotlin these become Color(0xFF + the six digits), e.g. #FF3DA6 → Color(0xFFFF3DA6))
Every value above was solved for >=4.5:1 on the layer it belongs to. Copy them character for
character — a "nicer" nearby colour silently breaks readability.

SPACING  xs4 sm8 md12 lg16 xl24 xxl32 xxxl48 · screen gutter 20 · min touch 48
RADIUS   sm10 md18 lg28 pill999
MOTION   fast120 base220 slow400 ambient6000ms
EASING   EaseOut cubic(0.16,1,0.3,1) · Overshoot cubic(0.34,1.56,0.64,1) for anything appearing
GLOW     radius sm12 md24 lg48 · alpha STRONG .55 / SOFT .28 / OFF 0
         NO Material shadowElevation — over a gradient it renders as a grey smear. Depth = stroke + glow.
TYPE     size/lineHeight, ALWAYS both:
         hero 44/52 w700 display · title 28/34 w700 display · score 34/38 w700 display ·
         section 20/26 w600 ui · body 16/24 w400 ui · button 17/20 w600 ui ·
         label 13/16 w600 ui +0.8 tracking UPPERCASE · caption 13/18 w400 ui
         Max 2 font families. Nothing under 13sp. Scores ALWAYS use the display font.

Put these in ui/theme/Tokens.kt + Palette.kt + Type.kt + Theme.kt.
Expose the palette via a CompositionLocal. Screens read `palette.primary`, never a hex literal.

FONTS ARE MANDATORY. Download the two variable fonts from the google/fonts repo into res/font/
(lowercase names only: orbitron.ttf, inter.ttf, space_grotesk.ttf, fraunces.ttf, nunito.ttf, baloo2.ttf)
and drive weights with FontVariation.Settings(FontVariation.weight(400|700)) — which is why minSdk is 26.
DO NOT fall back to FontFamily.Default. Four palettes on Roboto is exactly the "looks generated"
outcome this whole design system exists to prevent. If you cannot fetch them, say so explicitly.

═══ STEP 3 · COMPONENT LIBRARY (write these first, in ui/components/) ═══
ScreenScaffold(topBar,content,buttons) – Box(bgGradient) > AnimatedGameBackground > Column(safeDrawing
                                       + 20dp gutter) > 48dp top bar > content > bottom button stack
                                       (12dp gaps, 24dp bottom pad). EVERY screen uses this.
GameButton(Primary|Secondary|Ghost)  – pill, gradient primary→accent for Primary, 56dp min height,
                                       press-scale to 0.94 over 120ms, haptic + sfx on tap
IconTapButton(icon, label)           – 48dp square, radius md, translucent surface + 1dp stroke.
                                       `label` is REQUIRED and becomes the contentDescription.
GlassPanel                           – surface 88% alpha, radius lg, 1dp stroke, padding xl, preset glow.
                                       This is the standard host for body text over the gradient.
HudChip(label, value)                – pill, surface fill, UPPERCASE label + display-font value
AnimatedCounter(value)               – tweens 220ms AND pops to 1.18x scale on change
AnimatedGameBackground               – 5 drifting radial-gradient blobs in primary/accent at 14-20% alpha,
                                       infinite transition. Static frame when reduceMotion is on, and
                                       FROZEN while a run is live (it competes with the frame loop).
GameOverlay                          – 62% black scrim + GlassPanel scaling 0.85→1 with Overshoot
ProgressPill                         – animated gradient fill
ParticleSystem                       – burst(x,y,colors,count) + gravity + fade-out, pooled
rememberShake(trigger)               – decaying sine offset, 260ms. Offset.Zero when reduceMotion is on.
GameText(text, style, color)         – Text bound to the type scale + palette
Write ALL TWELVE before any screen, not just the ones the first screen needs.
Screens compose ONLY from these. No raw Button, no colour literal, no numeric .dp,
no inline fontSize= or color=Color(...) in any screen file.
Size containers with heightIn(min=…), never a fixed height() — at 200% font scale a fixed
height clips the text instead of growing.

═══ STEP 4 · ARCHITECTURE ═══
· Game state = plain Kotlin class with update(dt): List<GameEvent>. NOT Compose state.
  GameState.kt imports nothing from androidx.compose.
· Frame loop: LaunchedEffect + withFrameNanos, dt CLAMPED to max 1/30s, increments one `frame` counter.
· ONE Canvas reads `frame` and draws everything. No composable per entity. No allocation in update/draw.
· Virtual world coords (1000 x 1778) scaled uniformly to canvas, so physics is device-independent.
· Feedback object: tap()/score()/hit()/gameOver()/win() → SoundPool + Vibrator together. Rate-limit tap to 40ms.
  No sound files? Stub every method to a no-op and say so.
· SharedPreferences only: highscore, level, soundOn, hapticsOn, reduceMotion, gamesPlayed. Load at startup.
· Navigation: sealed interface Screen + one mutableStateOf. NO navigation-compose, NO Hilt, NO Room, NO Lottie.
· Pause and Result are OVERLAYS above the live canvas, not separate screens.
· BackHandler: during play → open Pause, never exit. FLAG_KEEP_SCREEN_ON while playing.
· ON_PAUSE: stop the loop, SoundPool.autoPause(), reset the frame timestamp to 0.

═══ STEP 5 · MANDATORY SCREENS (all 7) ═══
Splash → Home → HowToPlay → Game+HUD → Pause → Result → Settings
Overlay content order, always: title → big AnimatedCounter stat → stats row → primary CTA → secondary → ghost.
HUD layout is fixed: score HudChip top-centre, secondary stat top-left, pause IconTapButton top-right,
all three inside safeDrawing — a score under the punch-hole camera is the classic generated-game bug.
Result must visibly distinguish a new highscore (different copy + particles).
HowToPlay: under 25 words + a visual. Layout survives 320dp width AT 200% font scale.
Settings exposes sound, haptics AND reduceMotion.

═══ STEP 6 · JUICE RULES (non-negotiable) ═══
1. Every tap: visual scale + haptic + sound. All three. Missing one makes the game feel dead.
2. No static screen, ever.
3. No number snaps — everything counts up and pops.
4. Impact → screen shake. Reward milestone → particles (NOT on every point; constant confetti means nothing).
5. Things appear with Overshoot; they disappear ~40% faster with EaseOut.
6. Every screen transition animates.
7. ALL of 1-6 respect the reduceMotion pref: static background, no shake, half the particles,
   120ms fade transitions. Gameplay motion is untouched — it is a comfort setting, not an easy mode.
   Mandatory screen shake with no opt-out is a vestibular problem, not a style choice.

═══ STEP 7 · ART DIRECTION ═══
Default to PROCEDURAL art: Compose Canvas circles, paths, gradients, glows, particles. It always renders,
scales to any screen, recolours with the palette, and keeps the APK tiny.
But procedural is a TECHNIQUE, not an art direction. Put these in game/GameConfig.kt and obey them.
All numbers are virtual units (vu) in the 1000x1778 space:
  SHAPE     ONE family for the whole game: ROUND (circles/capsules) | EDGE (triangles/diamonds) |
            BLOCK (rounded rects, radius = 12% of the shorter side). Mixing families looks accidental.
  STROKE    hairline 2 · normal 4 · bold 8 · heavy 14 vu. Nothing else.
  SIZE      player 64-96 · obstacle 80-140 · pickup 40-56 · particle 6-14 vu. Nothing hittable under 56.
  DEPTH     3 planes back-to-front: far = ambient blobs, accent @10-16% alpha, parallax 0.15x ·
            mid = terrain, surface fill + 4vu stroke, parallax 1.0x · near = player/pickups/threats/
            particles, full chroma + glow. Nothing on `far` may look like a collider.
  CONTRAST  The player is the highest-contrast object on screen at all times, >=4.5:1 against BOTH
            bgTop and bgBottom. Threats = danger, rewards = success/accent, scenery = onBgMuted.
            A player that reads like an obstacle is a bug, not a difficulty setting.
  GLOW      near plane only, radius 0.6x entity radius. PAPER (glow OFF): 4vu offset shadow @12% instead.
  PARTICLES 12-20 per burst, never >24 · life 380-620ms · size 6-14vu shrinking to 0 · gravity 1400 vu/s^2
            · colours only from {primary, accent, success}. One burst per milestone, never continuous.
  TRAIL     moving player leaves a 6-frame trail @30% alpha, same fill, no stroke.
  The Canvas never paints its own background — it draws over AnimatedGameBackground so the gradient
  stays continuous across all 7 screens. That continuity is most of why the app feels like one product.
If you need real assets: kenney.nl (CC0), game-icons.net (CC-BY), fonts.google.com (OFL),
mixkit.co / pixabay sound-effects. Log every one in ATTRIBUTION.md with source + licence.
NEVER third-party IP (Mario, Pokémon, Flappy Bird, brand logos) — not even as a placeholder.
NEVER reference an R.raw/R.drawable that does not exist — stub it to a no-op instead.
(R.font is the exception: the fonts are mandatory, so fetch them rather than stubbing them.)
Always ship a real adaptive launcher icon (vector glyph + palette background). The default robot icon
makes the whole build look unfinished.

═══ STEP 8 · DELIVER ═══
Full file tree with complete file contents:
settings.gradle.kts · build.gradle.kts · gradle/libs.versions.toml · gradle.properties ·
app/build.gradle.kts · AndroidManifest.xml · res/{font,drawable,mipmap-anydpi-v26,raw,values} ·
MainActivity.kt · ui/theme/{Tokens,Palette,Type,Theme}.kt ·
ui/components/* · ui/screens/* · game/{GameConfig,GameState,Entities,Engine}.kt ·
platform/{SoundBank,Haptics,Prefs,Feedback}.kt · README.md · ATTRIBUTION.md
Baseline: compileSdk/targetSdk 36 · minSdk 26 (FontVariation needs it) · JVM 17 · Kotlin 2.4.x · Compose BOM 2026.06.01 ·
newest stable AGP 8.x (NOT 9.x — it drops kotlinOptions and variant APIs)
targetSdk 36 is not optional: from 31 Aug 2026 Google Play refuses new submissions below it.
Plugins: com.android.application, org.jetbrains.kotlin.android, org.jetbrains.kotlin.plugin.compose
(the Compose plugin version must equal the Kotlin version). Version catalog, no versions on Compose artifacts.
applicationId must be real — never com.example.*, com.myapp.*, com.test.*.
namespace = applicationId = the source directory path = every file's package line.
Portrait-locked. Edge-to-edge. All strings in strings.xml.
Write EVERY import explicitly — unresolved references are the #1 failure mode in generated Compose projects.

═══ STEP 9 · SELF-CHECK (output this table, filled honestly) ═══
A Build: imports resolve · no missing R.* · versions consistent · package matches everywhere ·
         no reachable TODO · minSdk 26
B Layout: safeDrawing on every screen · 20dp gutter everywhere · touch targets >=48dp via heightIn(min=) ·
         every icon-only control has a contentDescription · survives 320dp width at 200% font scale
C System: zero hex outside Palette.kt · zero raw dp in screens · zero raw Button · one preset ·
         all 17 palette tokens copied exactly · all 14 required contrast pairs >=4.5:1 ·
         both fonts real files in res/font/ driven by FontVariation (NOT FontFamily.Default) ·
         all 12 components written · explicit lineHeight on all 8 type roles · no shadowElevation
D Juice: press-scale everywhere · haptic+sfx on every tap · animated bg on every screen · AnimatedCounter on
         every number · animated transitions · shake on impact · particles on reward ·
         reduceMotion honoured by background, shake and particles · all 3 brief moments built
E Feel:  playable in 3s · smooth ramp · one-tap restart · deaths are readable · dt clamped ·
         art direction constants in GameConfig · player is the highest-contrast object on screen
F Done:  all 7 screens reachable · back opens Pause · highscore persists · sound/haptics/reduceMotion
         persist and are reachable in Settings · highscore run looks different · README + ATTRIBUTION present
Report as: A x/6  B x/5  C x/10  D x/9  E x/7  F x/6  TOTAL x/43, plus honest notes on any FAIL.
Fix every fail before you finish. A fabricated all-pass is worse than an honest fail.

═══ MY IDEA ═══
<your idea in one line>
In-game text language: <English | Vietnamese | both>
```

## Usage notes

- **If the model's output limit truncates the project**, run it in two passes: pass 1 = "Steps 1–3 only: brief + theme + components", pass 2 = "now Steps 4–9 using exactly the files you just wrote". Weak models handle two focused passes far better than one giant one. This mirrors the skill's two build gates.
- **If the model ignores the design system**, the fix is almost never a longer prompt. It is to run pass 1 alone, verify `Palette.kt` matches the preset character-for-character, and only then continue.
- **Keep the palette hex values exact.** Every one was solved for a contrast ratio on a specific layer. "Close enough" colours are exactly how generated games end up looking generated — and on the light presets they are how text ends up genuinely unreadable, not merely worse.
- **Verify the claimed self-check.** Even without the skill you can run its two design gates on the output:
  `bash check-contrast.sh app/src/main/java/**/ui/theme/Palette.kt <PRESET>` and `ls app/src/main/res/font/`.
  Three greps catch most of the rest: `grep -rn '0x[0-9A-Fa-f]\{8\}' ui/screens`, `grep -rn 'coerceAtMost' game/`, and `grep -rn 'FontFamily.Default' ui/theme/`.
- **The two things weak models drop first are the fonts and the art direction**, because both are easy to claim and invisible in a code listing. Check `res/font/` has two real files and `GameConfig.kt` names one shape family before believing any self-reported score.
