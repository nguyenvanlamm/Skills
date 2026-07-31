---
name: flutter-ui-revamp
description: Revamp the UI of an existing Flutter app or game with free assets — audit the codebase, lock a design direction, download licence-verified icons/fonts/illustrations/animations/game packs, optimize them, then refactor the real screens so the app actually looks different, builds, and ships with a credits file and a before/after report. Use when the user wants to refresh, replace or upgrade a Flutter interface — swap an icon set, change the font app-wide, replace illustrations, add a Rive/Lottie loader, drop in a game UI pack, wire sound effects, or rebuild the colour theme — or says things like "make my app look better", "my app looks ugly, revamp it", "swap in a new icon set", "add a loading animation", "make the game UI look nicer". Don't use for building a Flutter app from scratch (flutter-init), store listing art (flutter-store-metadata), or non-Flutter codebases.
license: MIT
metadata:
  version: 1.0.0
---

# Flutter UI Revamp

Take an existing Flutter app that works but looks generic, and change how it actually looks — in the code, on the screen, with the build passing.

## Core principle

> **Downloading assets is not a revamp.** A font in `assets/fonts/` that no `TextTheme` references, an icon pack that no screen imports, and a Rive loader sitting beside an untouched `CircularProgressIndicator` are three files and zero visible change. The deliverable is modified screens, a passing `flutter analyze`, and a build — not a folder.

Three rules follow, and each exists because it is a way this task fails.

**Presentation layer only.** A UI revamp is safe to run on a working app precisely because it never touches a repository, a bloc, a model or an API call. The moment it does, "make it prettier" becomes a debugging session in code the user did not ask you to open. Widgets, themes, assets. Nothing else.

**One screen at a time, verified.** A 40-file sweep ending in 200 analyzer errors is worse than no revamp: now nothing works and nobody knows which change did it. Refactor a screen, analyze, summarise, move on.

**State the licence before proposing the asset.** "Free" on an asset site means free to download. Whether it is free to ship in this app is a different question with a different answer, and it has to be answered first — see `references/licensing.md`.

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `project` | ❌ | `.` | Flutter project root (the directory with `pubspec.yaml`) |
| `style` | ❌ | ask at Step 2 | `minimal-modern`, `playful-rounded`, `neo-brutalism`, `casual-game`, `dark-premium` |
| `seed` | ❌ | ask at Step 2 | Seed colour, e.g. `#4F46E5` |
| `scope` | ❌ | all screens | Limit to specific screens: "just the home and profile screens" |
| `keep` | ❌ | — | Things not to change: "keep the current font", "don't touch the colours" |

## Workflow

Eight steps, in order. Step 6 is the one that matters; Steps 0–5 exist so that Step 6 is safe and coherent, and skipping ahead to it is how a revamp becomes a mess of half-applied styles.

### Step 0 — Safety

Before anything else:

```bash
cd <project> && git status --porcelain && git rev-parse --short HEAD
```

| Finding | Action |
|---|---|
| Working tree dirty | **STOP.** Ask the user to commit or stash. Do not offer to commit their in-progress work for them. |
| Not a git repo | **STOP.** Offer `git init` + an initial commit. There is no rollback without one, and this skill rewrites dozens of files. |
| Clean | Record the base commit, then branch. |

```bash
git switch -c ui-revamp/$(date +%Y-%m-%d)
```

Tell the user the base commit hash and the rollback command now, not at the end — `git reset --hard <sha>` is worth more before the work than after it. **Never modify code while the tree is dirty:** the diff is the only record of what this skill did, and mixed with the user's uncommitted work it stops being reviewable.

### Step 1 — Audit

```bash
python3 <skill>/scripts/scan_project.py --project .
```

Read `.claude/revamp/audit.md`. Then read enough of `lib/` to know what you are looking at — the entry point, the main screens, whatever `audit.json → derived` flagged. Four questions decide the whole plan:

1. **Standard app or Flame game?** (`derived.app_type`) — it selects `sources-ui.md` or `sources-game.md`.
2. **Material, Cupertino or mixed?** A Cupertino app does not get a Material 3 seed scheme bolted on.
3. **State management?** Not to change it — to know what not to touch.
4. **Is there already a design system?** Extending `lib/theme/` beats replacing it.

Summarise for the user in one block: what the app is, and the specific weaknesses with **numbers from the audit** — "17 hardcoded colours across 6 files, no dark theme, 1 pubspec asset pointing at a missing directory". Never "the UI looks dated"; that is an opinion, and the audit produced facts.

### Step 2 — Lock the design direction

Nothing gets downloaded until this is written down. Assets chosen before a direction are assets chosen by taste, and they will not agree with each other.

If `style` and `seed` were not given, propose **two or three** concrete options — not a menu of everything. Each option names its icon set, font pairing, illustration style and radius character, so the user chooses a look rather than fills a form. Then write `.claude/revamp/design-direction.md`:

```markdown
# Design direction — locked <date>

Style        minimal-modern
Seed         #4F46E5
Icons        Lucide (ISC) — const IconData, stroke 1.5
Fonts        Clash Display 600 (headings) + Satoshi 400/500/700 (body) — Fontshare
Illustration unDraw, flat, recoloured to seed, transparent
Animation    Rive (loader, empty-state)
Spacing      4 / 8 / 16 / 24 / 32 / 48
Radius       8 / 12 / 18 / pill
Dark mode    required, ColorScheme.fromSeed both brightnesses
Out of scope business logic, state management, API, models, navigation structure
```

Get explicit agreement. This file is what Step 6 is checked against — a change of mind at Step 6 costs the whole step.

### Step 3 — Select assets and verify licences

Read `references/sources-ui.md` (app) or `references/sources-game.md` (game), and `references/licensing.md`.

Pick from the locked direction, then present the list **before downloading**:

| Asset | Source | Licence | Attribution | Size | Why this one |
|---|---|---|---|---|---|
| Lucide icon set | lucide.dev | ISC | no | ~40 KB tree-shaken | const IconData; matches 1.5px stroke direction |
| Satoshi | fontshare.com | ITF free commercial | no | 3 × 45 KB | Body font in the locked pairing |
| unDraw empty box | undraw.co | unDraw licence | no | 12 KB SVG | Recoloured to seed; transparent |

Not negotiable at this step: the licence is read **from the source page now** — reference files rot, and a licence quoted from one is a guess. Anything CC BY-NC, GPL or unlicensed is rejected, with the reason stated. Anything requiring attribution needs a decision about **where on screen** the credit appears; if the app has no About screen, building one is part of this work. Wait for approval before Step 4.

### Step 4 — Download and optimize

```bash
python3 <skill>/scripts/fetch_asset.py --url <url> --dest assets/<kind> \
    --name "<name>" --author "<author>" --license <SPDX-ish> --source <page> --apply
python3 <skill>/scripts/optimize_flutter.py --project . --dir assets --apply --replace
```

`fetch_asset.py` normalises filenames to `lower_snake_case` (Dart asset paths become Dart identifiers under `flutter_gen`), prints every LICENSE/README found inside a zip — **read them** — and writes the `assets/CREDITS.md` row at download time, which is the only moment the metadata is reliably known.

`optimize_flutter.py` derives the 1.0x/2.0x/3.0x set from @3x sources, converts to WebP, and reports before/after bytes. Pillow, svgo and ffmpeg are each optional; a missing one is a skipped job with a warning, never a crash. Then update `pubspec.yaml` (the script prints the snippet — **directory entries are not recursive**, so every subdirectory needs its own line) and run `flutter pub add <packages> && flutter pub get`.

### Step 5 — Build the design system

Read `references/integration-flutter.md § Theme` and § Typography. Create:

| File | Contains |
|---|---|
| `lib/theme/app_colors.dart` | `ColorScheme.fromSeed` light + dark, `ThemeExtension` for success/warning |
| `lib/theme/app_typography.dart` | `TextTheme` built from the new font |
| `lib/theme/app_spacing.dart` | `AppSpacing` + `AppRadius` tokens |
| `lib/theme/app_theme.dart` | Assembled light/dark `ThemeData` |
| `lib/widgets/app_button.dart` | Ripple + haptics + 48dp minimum |
| `lib/widgets/app_card.dart` | `Material` + `InkWell`, themed surface |
| `lib/widgets/empty_state.dart` | Illustration + title + message + action |
| `lib/widgets/loading_view.dart` | Rive/Lottie loader |

Wire it in:

```dart
MaterialApp(
  theme: AppTheme.light,
  darkTheme: AppTheme.dark,
  themeMode: ThemeMode.system,
  home: const HomeScreen(),
);
```

Then **build once, here**, while the surface area is eight small files:

```bash
flutter analyze && flutter run -d <device> --debug   # or: flutter build apk --debug
```

A font that is not resolving, a package version conflict, a renamed `CardTheme` — every one of those is a one-file fix now and a cascade after thirty files are touched.

### Step 6 — Apply to the real code

The step everything else exists to serve. Read `references/refactor-patterns.md` and follow its per-screen order: icons → colours → text → components → spacing → states → micro-interactions.

Icons first, because they are mechanical:

```bash
python3 <skill>/scripts/apply_icons.py --project . --map icons.json          # dry run
python3 <skill>/scripts/apply_icons.py --project . --map icons.json --apply
```

**Show the user the diff from the dry run before applying.** The script skips matches inside comments and strings, reports every unmapped icon, and flags the const hazard — a callable replacement like `PhosphorIcons.house()` cannot sit inside `const Icon(...)`, and it will fail across every touched file at once. Prefer const constants in the mapping; `--fix-const` is the fallback.

Then, **one screen at a time**:

- Hardcoded colours → `Theme.of(context).colorScheme.*`
- Inline `TextStyle` → `textTheme.*`, deviations via `copyWith`
- Repeated `Container` + `BoxDecoration` → `AppCard` / `AppButton`
- Magic padding/radius → `AppSpacing` / `AppRadius`
- Empty, error and onboarding states → `EmptyState` with the new illustrations
- `CircularProgressIndicator` → `LoadingView`, or a skeleton where the content shape is known
- Ripple, haptics, press-scale, `PageRouteBuilder` transitions, `Hero` on shared images
- Flame games: old UI sprites → the new pack, panels → 9-slice, SFX hooked to press / win / lose

After each screen: `flutter analyze`, then a one-line summary of what changed. Do not batch four screens and analyze once.

### Step 7 — Verify

```bash
flutter analyze
flutter test          # if a test/ directory exists
flutter build apk --debug     # or: flutter build web
```

Fix every **new** error and warning. Pre-existing lint in files you did not touch is not this task's to clean up — say it is there, leave it alone.

Then the checks a build cannot make. Each needs evidence, not a tick:

| Check | How |
|---|---|
| Dark mode | Run in both brightnesses. Look for illustrations with baked white backgrounds, invisible text, and `Colors.white` survivors. |
| Text overflow | New font metrics differ from Roboto. Check the longest label on the narrowest screen; test at 200% text scale. |
| Contrast | Body text ≥ 4.5:1, large text ≥ 3:1. Derived-from-seed schemes usually pass; hand-edited slots usually do not. |
| Touch targets | ≥ 48×48 dp on every tappable. |
| Assets declared | Re-run `scan_project.py` — `ORPHAN_ASSETS` and `MISSING_ASSETS` must both be clear. |
| Bundle delta | `flutter build apk --release --analyze-size`, before vs after. |

If a device or emulator is attached, run the app and read a screenshot of two screens. It is the only check that proves the font actually loaded rather than silently falling back to Roboto — which is the failure that passes every mechanical gate and defeats the entire point of the work.

### Step 8 — Handoff

Complete `assets/CREDITS.md`, and put the required attributions **on screen**:

```dart
showLicensePage(
  context: context,
  applicationName: 'My App',
  applicationLegalese: '© 2026 …',
);
```

Register bundled font licences with `LicenseRegistry` so that page tells the truth (`integration-flutter.md § Typography`). Any CC BY asset needs a visible credit line, not just the file.

Write `.claude/revamp/report.md`:

```markdown
# UI revamp — <app> — <date>

| Category | Before | After |
|---|---|---|
| Icon set | Material default, 23 distinct | Lucide, 23 mapped, 0 unmapped |
| Font | platform default | Clash Display + Satoshi (bundled) |
| Colours | 17 hardcoded across 6 files | ColorScheme.fromSeed #4F46E5, light + dark |
| Loading | CircularProgressIndicator ×4 | Rive loader + 2 skeletons |
| Assets | 2.1 MB, 12 PNG | 1.4 MB, WebP + 3 buckets |
| Release APK | 18.2 MB | 19.1 MB (+0.9) |

## Files changed · Manual follow-ups · Rollback
git reset --hard <base-sha>     # or: git switch main && git branch -D ui-revamp/<date>
```

Every number in that table comes from `audit.md` and the `--analyze-size` runs. Do not fill it from memory.

Commit in grouped changes, not one blob:

```bash
git commit -m "chore(assets): add Lucide, Satoshi, unDraw illustrations + credits"
git commit -m "feat(theme): M3 seed scheme, typography and spacing tokens"
git commit -m "refactor(ui): swap icon set across lib/"
git commit -m "refactor(home): theme tokens, empty state, Rive loader"
```

## Hard rules

**Scope** — never modify business logic, state management, API calls, models or navigation structure; presentation layer only. Never refactor the whole project in one pass. Never bulk-replace without a dry run whose diff the user has seen.

**Licensing** — state every licence before proposing the asset, read from the source page. "Free" never implies commercially usable; prefer CC0 / MIT / OFL. Attribution-required assets need a place on screen, decided before download. No third-party logos, IP or copyrighted characters, whatever the stated licence.

**Consistency** — one icon set, one illustration style, at most two font families. Warn loudly when mixing would occur: Lucide beside Heroicons, flat illustrations beside 3D renders, a Kenney panel beside a CraftPix button. Vector over raster, WebP over PNG, a cohesive pack over assembled loose files. Rive for interactive animation, Lottie for linear.

**Theming** — every colour and text style flows through `ThemeData`; a new widget with a hardcoded colour is a bug in the revamp itself. Check dark mode explicitly: an illustration with a baked white background shows a slab, so find a transparent version or recolour it.

**Budget and accessibility** — assets under 30 MB, else cut or defer. Text contrast ≥ 4.5:1 (large text ≥ 3:1). Touch targets ≥ 48×48 dp. `semanticLabel` on meaningful icons, `excludeFromSemantics` on decorative ones.

**Games** — power-of-two atlases with 1–2 px transparent padding against texture bleeding. Every panel needs a measured 9-slice inset spec, not a guessed one. Preload sprites and audio in `onLoad`, never mid-gameplay.

## Output structure

```
assets/
  images/          2.0x/  3.0x/
  icons/
  illustrations/
  sprites/
  fonts/
  animations/
  audio/sfx/  audio/music/
  CREDITS.md
lib/theme/         app_colors · app_typography · app_spacing · app_theme
lib/widgets/       app_button · app_card · empty_state · loading_view
.claude/revamp/    audit.md · audit.json · design-direction.md · report.md
```

`CREDITS.md` is a table: Asset | Type | Files | Author | License | Credit required (Y/N) | Source | Downloaded. `fetch_asset.py` writes the rows.

## Examples

### 1. Todo app — default everything → minimal modern

**Request:** "My todo app looks like a Flutter demo. Make it look designed."

**Audit:** standard Material app, 8 screens, provider. 23 distinct `Icons.*`, 17 hardcoded colours across 6 files, 31 inline `TextStyle`, no `darkTheme`, no bundled font, 4 × `CircularProgressIndicator`, `Center(child: Text('No todos'))` as the empty state, no assets directory at all.

**Direction:** minimal-modern, seed `#4F46E5`, Lucide (ISC), Clash Display + Satoshi (Fontshare), unDraw recoloured to seed, one Rive loader.

**BEFORE** — `TodoTile.build`

```dart
return Container(
  margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
  padding: const EdgeInsets.all(14),
  decoration: BoxDecoration(
    color: Colors.white,
    borderRadius: BorderRadius.circular(10),
    border: Border.all(color: Colors.grey.shade300),
  ),
  child: Row(children: [
    IconButton(
      icon: Icon(
        todo.done ? Icons.check_circle : Icons.radio_button_unchecked,
        color: todo.done ? Colors.green : Colors.grey,
      ),
      onPressed: onToggle,
    ),
    Expanded(
      child: Text(todo.title, style: TextStyle(
        fontSize: 16,
        color: todo.done ? Colors.grey : Colors.black87,
        decoration: todo.done ? TextDecoration.lineThrough : null,
      )),
    ),
  ]),
);
```

**AFTER**

```dart
final scheme = Theme.of(context).colorScheme;
final semantic = Theme.of(context).extension<AppSemanticColors>()!;
final text = Theme.of(context).textTheme;

return Padding(
  padding: const EdgeInsets.symmetric(
    horizontal: AppSpacing.md,
    vertical: AppSpacing.xs + 2,
  ),
  child: AppCard(
    onTap: () {
      HapticFeedback.selectionClick();
      onToggle();
    },
    child: Row(children: [
      Icon(
        todo.done ? LucideIcons.checkCircle2 : LucideIcons.circle,
        color: todo.done ? semantic.success : scheme.outline,
        semanticLabel: todo.done ? 'Completed' : 'Not completed',
      ),
      const SizedBox(width: AppSpacing.md),
      Expanded(
        child: AnimatedDefaultTextStyle(
          duration: const Duration(milliseconds: 180),
          style: (text.bodyLarge ?? const TextStyle()).copyWith(
            color: todo.done ? scheme.onSurfaceVariant : scheme.onSurface,
            decoration: todo.done ? TextDecoration.lineThrough : null,
          ),
          child: Text(todo.title),
        ),
      ),
    ]),
  ),
);
```

Empty state became `EmptyState(illustration: 'assets/illustrations/empty_checklist.svg', …)`; the four spinners became `LoadingView`. The `Todo` model and the provider were not opened.

### 2. Flame casual game — hand-drawn UI → Kenney pack

**Request:** "The game plays fine but the menus look terrible."

**Audit:** `FlameGame`, 6 loose UI PNGs stretched with `BoxFit.fill` (visibly smeared corners), no atlas, no audio, HUD text in default Roboto, buttons are bare `GestureDetector`s.

**Direction:** casual-game. Kenney UI Pack (**CC0**), Kenney Interface Sounds (**CC0**), Game-icons.net for the ability glyphs (**CC BY → Credits screen required**), Baloo 2 (OFL).

**BEFORE**

```dart
GestureDetector(
  onTap: _resume,
  child: Container(
    width: 220,
    height: 60,
    decoration: const BoxDecoration(
      image: DecorationImage(
        image: AssetImage('assets/images/ui/button.png'),
        fit: BoxFit.fill, // corners smear at every size
      ),
    ),
    child: const Center(
      child: Text('RESUME', style: TextStyle(fontSize: 18, color: Colors.white)),
    ),
  ),
);
```

**AFTER** — `GameButton.build`

```dart
return Semantics(
  button: true,
  label: label,
  child: GestureDetector(
    onTap: () {
      FlameAudio.play('sfx/click.ogg', volume: 0.6);
      HapticFeedback.selectionClick();
      onTap();
    },
    child: SizedBox(
      width: 220,
      height: 60,
      // Kenney's button is 64x64 with 16px borders — from the pack spec.
      child: NineSlicePanel(
        asset: 'assets/sprites/ui/button_blue.webp',
        sourceSize: const Size(64, 64),
        border: const EdgeInsets.all(16),
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Center(
          child: Text(label, style: Theme.of(context).textTheme.labelLarge),
        ),
      ),
    ),
  ),
);
```

Plus: six loose PNGs packed into one atlas, `FlameAudio.audioCache.loadAll` in `onLoad`, win/lose SFX on the existing game-over callbacks, and a Credits screen for the CC BY icons. The game loop, physics and scoring were not opened.

### 3. E-commerce app — competent but lifeless

**Request:** "The design is okay, it just feels dead."

**Audit:** already has `lib/theme/`, M3, dark mode, a bundled font. Weaknesses are all motion and state: no `Hero`, no haptics, spinner over the whole product grid, `Center(child: Text('Your cart is empty'))`, hard route cuts.

**Direction:** keep the existing theme (`keep: colours, font`). Add only motion, states and feedback.

**BEFORE**

```dart
GestureDetector(
  onTap: () => Navigator.push(
      context, MaterialPageRoute(builder: (_) => ProductScreen(product))),
  child: Column(children: [
    CachedNetworkImage(imageUrl: product.image, height: 140),
    Text(product.name),
  ]),
);
```

**AFTER**

```dart
InkWell(
  borderRadius: BorderRadius.circular(AppRadius.lg),
  onTap: () {
    HapticFeedback.selectionClick();
    Navigator.push(context, fadeThrough(ProductScreen(product)));
  },
  child: Column(children: [
    Hero(
      tag: 'product-${product.id}',
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: CachedNetworkImage(
          imageUrl: product.image,
          height: 140,
          fadeInDuration: const Duration(milliseconds: 200),
          placeholder: (_, __) => const AppSkeleton(height: 140, radius: 12),
        ),
      ),
    ),
    const SizedBox(height: AppSpacing.sm),
    Text(product.name, style: Theme.of(context).textTheme.titleMedium),
  ]),
);
```

Plus: grid spinner → six skeleton cards, empty cart → `EmptyState` with an unDraw illustration and a "Browse products" action, `HapticFeedback.mediumImpact()` on add-to-cart. No asset downloads beyond one illustration; the whole win was motion and state.

## Reference files

| File | Read when |
|---|---|
| `references/sources-ui.md` | Step 3 — icons, illustrations, fonts, animation, colour tools for an app |
| `references/sources-game.md` | Step 3 — sprite packs, tilesets, audio, sprite hygiene for a Flame game |
| `references/licensing.md` | Step 3, before any download — licence table and the seven traps |
| `references/integration-flutter.md` | Steps 4–5, and whenever a build fails — pubspec, buckets, SVG, Rive, 9-slice, theme, Flame, bundle size |
| `references/refactor-patterns.md` | Step 6 — every BEFORE→AFTER transformation and the icon mapping table |

| Script | Run at |
|---|---|
| `scripts/scan_project.py` | Step 1 and again at Step 7 — writes `.claude/revamp/audit.{json,md}` |
| `scripts/fetch_asset.py` | Step 4 — download, normalise filenames, write the CREDITS row |
| `scripts/optimize_flutter.py` | Step 4 — density buckets, WebP, svgo, OGG, size report, pubspec snippet |
| `scripts/apply_icons.py` | Step 6 — bulk icon swap; dry run by default, const-hazard detection |

Every script defaults to a dry run and writes only with `--apply`.

## Scope

Does: audit an existing Flutter codebase, lock a design direction, source licence-verified free assets, optimize them for the bundle, build a themed design system, refactor real screens to use it, add micro-interactions and motion, wire game UI packs and SFX for Flame, verify by analyzing and building, and hand off with credits and a before/after report.

Does not: create a Flutter project (see `flutter-init`); design custom original artwork; change business logic, state management, APIs, models or navigation structure; buy paid assets; produce store listing graphics (see `flutter-store-metadata`); sign or publish (see `flutter-signing`, `flutter-publish`); touch non-Flutter codebases.
