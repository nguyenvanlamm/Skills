---
name: android-game-forge
description: Build a complete, buildable Kotlin + Jetpack Compose Android game from a short idea — locked design system (4 contrast-verified palettes), bundled OFL typography, canvas art direction, component library, fixed-timestep engine, then verify by compiling, measuring WCAG contrast, and grepping the design system. Use when the user wants an Android game generated from scratch. Don't use for Flutter (flutter-init), non-game Android apps, or Unity/Godot.
license: MIT
metadata:
  version: 3.0.0
---

# Android Game Forge

Generate a Kotlin + Jetpack Compose Android game from a one-line idea, then prove it works.

## Core principle

> **A game that does not compile is not a game, and a self-graded checklist is not a verification.** Every way these projects fail is mechanically detectable: unresolved imports fail a build, "the model ignored the design system" fails a grep, and "that colour is close enough" fails a contrast calculation. Run all three. Never report a score you did not measure — including a contrast claim.

The second rule: **build twice, not once.** Compile after the theme + components pass, while the surface area is ten small files. A toolchain or Gradle fault found there costs one fix; the same fault found after thirty files costs an afternoon of cascading errors.

The third rule: **beauty is a measurement, not an opinion.** Three things decide whether the output looks designed or generated — the palette being correct *and* readable, the real typeface being on disk, and the game canvas having an art direction. All three are gated in Step 6. A project that skips them still compiles; it just looks like every other generated Compose app.

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `idea` | ✅ | — | One line is enough: "endless runner where you dodge falling blocks" |
| `palette` | ❌ | auto by genre | `NEON`, `SPACE`, `PAPER`, `CANDY` |
| `package` | ❌ | ask | e.g. `com.yourname.blockdodge` — **never** `com.example.*` |
| `dir` | ❌ | `./<slug>` | Project directory |
| `lang` | ❌ | English | In-game text language (UI strings only; code stays English) |
| `build` | ❌ | auto | `false` skips compilation gates — code-only output |

## Workflow

### Step 0 — Toolchain preflight

Do this **before** writing a line of code. It decides whether the verification gates can run at all, and finding out after generating thirty files is worthless.

```bash
java -version 2>&1 | head -1
echo "${ANDROID_HOME:-${ANDROID_SDK_ROOT:-unset}}"
ls "${ANDROID_HOME:-$HOME/Android/Sdk}/platforms" 2>/dev/null | sort -V | tail -3
adb devices 2>/dev/null | tail -n +2
```

| Finding | Verdict |
|---------|---------|
| JDK 17+ present | OK. JDK 17 is the floor for AGP 8; 21 is fine. JDK 11 or lower → **BLOCK**, the build cannot run. |
| `ANDROID_HOME` unset and no SDK at `~/Android/Sdk` | Build gates unavailable → **degraded mode**: generate everything, run the grep gates, and say plainly in the report that compilation was never verified. Do not imply it was. |
| No `platforms/android-36` | Fine — Gradle downloads it on first build. Just expect a slow first build (3–6 min). |
| A device or emulator in `adb devices` | Enables Step 7's smoke test, the only check that proves the game actually runs. |

Announce which mode you are in before proceeding. A user who wanted a working game deserves to know upfront that nothing will be compiled.

### Step 1 — Game brief

Output this first, as a compact block, before any code:

**Title · Genre · Core loop (1 sentence) · Input (exactly ONE of: tap, hold, drag, swipe) · Win/lose · Session length (30–120s) · Difficulty ramp formula · Progression · Palette preset · 3 signature juice moments.**

Vague idea? Decide the details yourself and state the assumptions. **Ask at most 2 questions**, and only ones that change the build — package name if unset, or a genuinely ambiguous core mechanic. Never ask about colours, fonts, or spacing; those are locked.

One input verb only. Games generated with "tap or swipe or drag" end up with three half-tuned control schemes and no feel.

### Step 2 — Project skeleton and toolchain pin

Read `references/toolchain.md`. It has the Gradle files, the version-catalog layout, the manifest, and the adaptive icon.

Resolve versions instead of trusting a pin that rots:

```bash
SKILL=<this skill's directory>              # the scripts live beside SKILL.md, not in the project
mkdir -p gradle && bash "$SKILL/scripts/resolve-versions.sh" > gradle/libs.versions.toml
```

Non-negotiable from that file: **`compileSdk`/`targetSdk` 36, `minSdk` 26, JVM 17, portrait-locked, edge-to-edge.** From 31 Aug 2026 Google Play refuses new submissions targeting below API 36, so a game generated today with `targetSdk 35` is born unpublishable. `minSdk` is 26 rather than 24 because `FontVariation.Settings` needs it and the entire type scale rides on variable fonts.

### Step 3 — Design system and typography

Read `references/design-system.md` and write `ui/theme/{Tokens,Palette,Type,Theme}.kt`.

Your visual taste is not part of this job. The palettes, spacing scale, radii, motion durations, easing curves, glow levels, and type scale are fixed — assemble from them. Do not invent colours. Do not use Material 3 default theme colours; the giveaway of a generated Compose app is Material baseline purple.

Copy the hex values **character for character**, all seventeen tokens per preset. Every one was solved to clear 4.5:1 on the layer it belongs to, and `scripts/check-contrast.sh` recomputes them from the file you write. "Close enough" is caught, named, and failed.

Read **the layering law** at the top of that file before writing `Palette.kt`. `primary` and `accent` are fill colours and are never text; `textPrimary/Secondary/Tertiary` live on `surface`, not on the gradient; the semantic triple is per-palette. Most ugly generated screens are the right colour on the wrong layer.

Then fetch the real typefaces — they are mandatory, not optional:

```bash
bash "$SKILL/scripts/fetch-fonts.sh" <PRESET>      # from the project root
```

**Never fall back to `FontFamily.Default`.** Four palettes on Roboto is exactly the generated look this skill exists to avoid. If the download fails, that is a FAIL to report in Step 8, not a fallback to take quietly.

The palette reaches screens through a `CompositionLocal`. Screens read `palette.primary` — never a hex literal.

### Step 4 — Component library + build gate A

Write all twelve components in `ui/components/*` per `references/design-system.md`, plus a placeholder Home screen that uses three of them. All twelve, not the four the first screen happens to need — a component library written on demand ends up half-written, and Step 6 checks for each by name. Then:

```bash
./gradlew assembleDebug 2>&1 | tee /tmp/build-a.log | tail -20
```

**This gate is the reason the skill works.** Ten files with an unresolved import produce a readable error; thirty files produce a cascade. Do not proceed to Step 5 until this is green. On failure, triage with the table in `references/toolchain.md` rather than shotgunning edits.

### Step 5 — Engine and screens

Read `references/architecture.md`. The contract in short:

- Game state is a **plain Kotlin class** with `update(dt): List<GameEvent>`. Not Compose state.
- One frame loop (`withFrameNanos`), `dt` **clamped to 1/30 s**, incrementing a single `frame` counter.
- **One `Canvas`** reads `frame` and draws everything. No composable per entity, no allocation in `update`/`draw`.
- Virtual world coords 1000 × 1778 scaled uniformly, so physics is device-independent.
- `Feedback`: `tap()/score()/hit()/gameOver()/win()` fire SoundPool **and** Vibrator together, tap rate-limited to 40 ms.
- `SharedPreferences` only — highscore, level, soundOn, hapticsOn, **reduceMotion**, gamesPlayed.
- Navigation: `sealed interface Screen` + one `mutableStateOf`. No navigation-compose, Hilt, Room, or Lottie.

All 7 screens: **Splash → Home → HowToPlay → Game+HUD → Pause → Result → Settings.** Pause and Result are overlays above the live canvas, never separate screens. `BackHandler` during play opens Pause and never exits.

Juice rules are non-negotiable and each one is checked in Step 6:

1. Every tap gets visual scale **+** haptic **+** sound. All three — missing one makes the game feel dead.
2. No static screen, ever.
3. No number snaps. Everything counts up and pops.
4. Impact → screen shake. Reward *milestone* → particles. Constant confetti means nothing.
5. Things appear with Overshoot and leave ~40% faster with EaseOut.
6. Every screen transition animates.
7. All of 1–6 respect the `reduceMotion` pref. Mandatory screen shake with no opt-out is a vestibular problem, not a style choice.

Art defaults to **procedural** — Canvas shapes, gradients, glows, particles. It always renders, scales to any screen, recolours with the palette, and keeps the APK tiny.

But *procedural* is a technique, not an art direction. **Follow the "Canvas art direction" section of `references/design-system.md` and put its constants in `game/GameConfig.kt`:** one shape family for the whole game, the four stroke widths, the three depth planes, entity size bands, the particle budget, and the rule that the player is the highest-contrast object on screen. This is the screen the player looks at ninety percent of the time, and it is the one the token system does not otherwise reach.

Visual coherence beats asset fidelity: three mixed free sprite styles look cheaper than clean procedural shapes. If you do use assets, log every one in `ATTRIBUTION.md` with source and licence, and prefer CC0 (kenney.nl, game-icons.net, fonts.google.com OFL, mixkit.co/pixabay for SFX). **Never** third-party IP — no Mario, Pokémon, Flappy Bird, or brand logos, not even as a placeholder. Never reference an `R.raw`/`R.drawable` that does not exist; stub it to a no-op instead. `R.font` is the exception: those files are mandatory, so fetch them rather than stubbing them.

### Step 6 — Mechanical verification

```bash
bash "$SKILL/scripts/check.sh"          # run from the project root; add --no-build in degraded mode
```

The script greps what a self-report cannot be trusted on, computes what a grep cannot see, and compiles what neither can: hex literals outside the theme, raw `dp` and inline `fontSize`/`color` in screens, missing `R.*` targets, `safeDrawing`, the `dt` clamp, haptics + sound pairing, the seven screens, and a real `assembleDebug` whose APK is **newer than the build started** — a stale APK from an earlier run is a failure, not a pass.

Four of its gates are the design ones, and they are the reason v2's output could look generated and still score 31/31:

| Gate | What it measures |
|------|------------------|
| **C7** | every palette token matches the locked spec character for character — catches "I picked a nicer blue" |
| **C8** | all 14 required foreground/background pairs recomputed from your `Palette.kt`, ≥4.5:1 |
| **C9** | both typefaces are real files in `res/font/`, and `Type.kt` uses `FontVariation` rather than falling back to Roboto |
| **C10** | all twelve components exist — a four-component design system is four components |

C7 and C8 run `scripts/check-contrast.sh`, which you can also call directly while iterating on the theme.

Fix every FAIL and re-run until clean. If something genuinely cannot pass, say so with the reason. **A fabricated all-pass is worse than an honest fail**: it costs the user the debugging session they thought they were buying.

### Step 7 — Smoke test (device or emulator attached)

Nothing else in this skill proves the game *runs*.

```bash
./gradlew installDebug
adb logcat -c
adb shell am start -n "$PKG/.MainActivity"
sleep 4
adb exec-out screencap -p > /tmp/game-home.png
adb logcat -d -b crash | tail -30
```

Read `/tmp/game-home.png` with the Read tool and check it honestly against five things the gates cannot see:

1. Is the palette actually on screen, or is it Material baseline purple?
2. Is that the **real typeface**? Orbitron and Baloo 2 are unmistakable; if it looks like Roboto, C9 passed on a technicality and the fonts never loaded at runtime.
3. Is every piece of text on the layer it belongs to — body text inside a panel, not floating on the gradient?
4. Does the HUD clear the notch and the punch-hole camera?
5. Then tap through to gameplay (`adb shell input tap X Y`) and capture a second frame: one shape family, three readable depth planes, and the player unmistakably the highest-contrast object on screen.

Any `FATAL EXCEPTION` in the crash buffer is a FAIL regardless of what the build said.

### Step 8 — Report

```
ANDROID GAME FORGE — <OK | FAILED | CODE ONLY>

Game       <Title> · <genre> · <input> · palette <PRESET> · shape family <ROUND|EDGE|BLOCK>
Project    <dir>  (<n> files, <n> Kotlin)
Build      assembleDebug OK — app-debug.apk 4.2 MB · compileSdk 36 · minSdk 26
Toolchain  AGP <v> · Kotlin <v> · Compose BOM <v> · JDK <v>
Design     palette <n>/17 tokens exact · contrast <n>/14 pairs ≥4.5:1 · fonts <Display> + <UI> bundled
Checks     A _/_  B _/_  C _/_  D _/_  E _/_  F _/_  →  measured <n>/<n>, <n> FAIL
Judged     B6 320dp @200% ✓ · D9 3 juice moments ✓ (name them) · E6 feel + art direction ✓
Smoke      launched, no crash, palette + typeface confirmed on screen
Play       targetSdk 36 ✓ (required for new submissions from 31 Aug 2026)

Notes      <every FAIL, WARN, assumption, and stub — or "none">
Next       ./gradlew installDebug · then flutter-* skills do not apply; sign with a real keystore before publishing
```

Report every warning even on success, and label degraded mode as `CODE ONLY` — never `OK`.

**Every number on the `Checks` and `Design` lines comes from `scripts/check.sh`. Copy them from its output; do not type them from memory and do not fill in the blanks by hand.** The `MANUAL` items are yours to judge, and each needs a sentence of evidence — "D9 ✓" with nothing behind it is the fabricated all-pass in miniature.

If the fonts did not download, say so on the `Design` line and mark the run `CODE ONLY`. A game shipped in Roboto is a different product from the one the brief described.

## Reference files

| File | Read when |
|------|-----------|
| `references/design-system.md` | Step 3–4 — layering law, palettes, tokens, type scale, components, canvas art direction, accessibility |
| `references/architecture.md` | Step 5 — engine contract, frame loop, feedback, screen skeletons |
| `references/toolchain.md` | Step 2, and whenever a build fails |
| `references/oneshot-prompt.md` | The user wants the paste-anywhere prompt for a tool without skills |

| Script | Run at |
|--------|--------|
| `scripts/resolve-versions.sh` | Step 2 — writes `gradle/libs.versions.toml` |
| `scripts/fetch-fonts.sh <PRESET>` | Step 3 — the two OFL variable fonts into `res/font/` |
| `scripts/check-contrast.sh <Palette.kt> <PRESET>` | Step 3, while iterating on the theme |
| `scripts/check.sh [--no-build]` | Step 6 — everything, including the two above |

## Scope

Does: brief, scaffold, locked design system, contrast-verified palettes, bundled OFL typography, component library, canvas art direction, game engine, 7 screens, procedural art, build + design-system + accessibility verification, optional device smoke test.

Does not: sign a release or publish (needs a real keystore and a Play account); generate sprite art or music; multiplayer, ads, IAP, or analytics; Flutter, Unity, Godot, or iOS.
