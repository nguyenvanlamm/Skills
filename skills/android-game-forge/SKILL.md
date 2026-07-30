---
name: android-game-forge
description: Build a complete, buildable Kotlin + Jetpack Compose Android game from a short idea — locked design system (4 palettes), component library, fixed-timestep engine, then verify by actually compiling and grepping the design system. Use when the user wants an Android game generated from scratch. Don't use for Flutter (flutter-init), non-game Android apps, or Unity/Godot.
license: MIT
metadata:
  version: 2.0.0
---

# Android Game Forge

Generate a Kotlin + Jetpack Compose Android game from a one-line idea, then prove it works.

## Core principle

> **A game that does not compile is not a game, and a self-graded checklist is not a verification.** Both ways these projects fail are mechanically detectable: unresolved imports and missing `R.*` references fail a build, and "the model ignored the design system" fails a grep. Run both. Never report a score you did not measure.

The second rule: **build twice, not once.** Compile after the theme + components pass, while the surface area is ten small files. A toolchain or Gradle fault found there costs one fix; the same fault found after thirty files costs an afternoon of cascading errors.

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

Non-negotiable from that file: **`compileSdk`/`targetSdk` 36, `minSdk` 24, JVM 17, portrait-locked, edge-to-edge.** From 31 Aug 2026 Google Play refuses new submissions targeting below API 36, so a game generated today with `targetSdk 35` is born unpublishable.

### Step 3 — Design system

Read `references/design-system.md` and write `ui/theme/{Tokens,Palette,Type,Theme}.kt`.

Your visual taste is not part of this job. The palettes, spacing scale, radii, motion durations, easing curves, and type scale are fixed — assemble from them. Do not invent colours. Do not use Material 3 default theme colours; the giveaway of a generated Compose app is Material baseline purple.

Copy the hex values **character for character**. They are chosen for ≥4.5:1 contrast against their backgrounds; "close enough" is exactly how generated games end up looking generated.

The palette reaches screens through a `CompositionLocal`. Screens read `palette.primary` — never a hex literal.

### Step 4 — Component library + build gate A

Write `ui/components/*` per `references/design-system.md`, plus a placeholder Home screen that uses three of them. Then:

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
- `SharedPreferences` only — highscore, level, soundOn, hapticsOn, gamesPlayed.
- Navigation: `sealed interface Screen` + one `mutableStateOf`. No navigation-compose, Hilt, Room, or Lottie.

All 7 screens: **Splash → Home → HowToPlay → Game+HUD → Pause → Result → Settings.** Pause and Result are overlays above the live canvas, never separate screens. `BackHandler` during play opens Pause and never exits.

Juice rules are non-negotiable and each one is checked in Step 6:

1. Every tap gets visual scale **+** haptic **+** sound. All three — missing one makes the game feel dead.
2. No static screen, ever.
3. No number snaps. Everything counts up and pops.
4. Impact → screen shake. Reward *milestone* → particles. Constant confetti means nothing.
5. Things appear with Overshoot and leave ~40% faster with EaseOut.
6. Every screen transition animates.

Art defaults to **procedural** — Canvas shapes, gradients, glows, particles. It always renders, scales to any screen, recolours with the palette, and keeps the APK tiny. Visual coherence beats asset fidelity: three mixed free sprite styles look cheaper than clean procedural shapes. If you do use assets, log every one in `ATTRIBUTION.md` with source and licence, and prefer CC0 (kenney.nl, game-icons.net, fonts.google.com OFL, mixkit.co/pixabay for SFX). **Never** third-party IP — no Mario, Pokémon, Flappy Bird, or brand logos, not even as a placeholder. Never reference an `R.raw`/`R.font`/`R.drawable` that does not exist; stub it to a no-op instead.

### Step 6 — Mechanical verification

```bash
bash "$SKILL/scripts/check.sh"          # run from the project root; add --no-build in degraded mode
```

The script greps what a self-report cannot be trusted on and compiles what a grep cannot see: hex literals outside the theme, raw `dp` and inline `fontSize`/`color` in screens, missing `R.*` targets, `safeDrawing`, the `dt` clamp, haptics + sound pairing, the seven screens, and a real `assembleDebug` whose APK is **newer than the build started** — a stale APK from an earlier run is a failure, not a pass.

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

Read `/tmp/game-home.png` with the Read tool and check it honestly: is the palette actually on screen, or is it Material baseline purple? Is text readable? Then tap through to gameplay (`adb shell input tap X Y`) and capture a second frame. Any `FATAL EXCEPTION` in the crash buffer is a FAIL regardless of what the build said.

### Step 8 — Report

```
ANDROID GAME FORGE — <OK | FAILED | CODE ONLY>

Game       <Title> · <genre> · <input> · palette <PRESET>
Project    <dir>  (<n> files, <n> Kotlin)
Build      assembleDebug OK — app-debug.apk 4.2 MB · compileSdk 36 · minSdk 24
Toolchain  AGP <v> · Kotlin <v> · Compose BOM <v> · JDK <v>
Checks     A 4/4  B 3/3  C 7/7  D 7/7  E 4/4  F 6/6  →  measured 31/31, 0 FAIL
Judged     B4 320dp ✓ · D8 3 juice moments ✓ (name them) · E5 feel ✓  — 4 manual items
Smoke      launched, no crash, palette confirmed on screen
Play       targetSdk 36 ✓ (required for new submissions from 31 Aug 2026)

Notes      <every FAIL, WARN, assumption, and stub — or "none">
Next       ./gradlew installDebug · then flutter-* skills do not apply; sign with a real keystore before publishing
```

Report every warning even on success, and label degraded mode as `CODE ONLY` — never `OK`. The 31 measured scores come from `scripts/check.sh`; do not hand-write them. The 4 `MANUAL` items are yours to judge, and each needs a sentence of evidence — "D8 ✓" with nothing behind it is the fabricated all-pass in miniature.

## Reference files

| File | Read when |
|------|-----------|
| `references/design-system.md` | Step 3–4 — palettes, tokens, type scale, component specs |
| `references/architecture.md` | Step 5 — engine contract, frame loop, feedback, screen skeletons |
| `references/toolchain.md` | Step 2, and whenever a build fails |
| `references/oneshot-prompt.md` | The user wants the paste-anywhere prompt for a tool without skills |

## Scope

Does: brief, scaffold, locked design system, component library, game engine, 7 screens, procedural art, build + design-system verification, optional device smoke test.

Does not: sign a release or publish (needs a real keystore and a Play account); generate sprite art or music; multiplayer, ads, IAP, or analytics; Flutter, Unity, Godot, or iOS.
