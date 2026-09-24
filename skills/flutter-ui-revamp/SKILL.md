---
name: flutter-ui-revamp
description: Revamp the UI of an existing Flutter app or game with free assets — audit the codebase, lock a design direction, download licence-verified icons/fonts/illustrations/animations/game packs, optimize them, then refactor the real screens so the app actually looks different, builds, and ships with a credits file and a before/after report. Use when the user wants to refresh, replace or upgrade a Flutter interface — swap an icon set, change the font app-wide, replace illustrations, add a Rive/Lottie loader, drop in a game UI pack, wire sound effects, or rebuild the colour theme — or says things like "make my app look better", "my app looks ugly, revamp it", "swap in a new icon set", "add a loading animation", "make the game UI look nicer". Don't use for building a Flutter app from scratch (flutter-init), store listing art (flutter-store-metadata), or non-Flutter codebases.
capabilities: [ui-revamp]
license: MIT
metadata:
  version: 1.7.0
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
git switch -c ui-revamp/$(date +%Y-%m-%d-%H%M)
```

If that branch name already exists, append the short HEAD hash. Tell the user the base commit hash and the rollback command now, not at the end — `git reset --hard <sha>` is worth more before the work than after it. **Never modify code while the tree is dirty:** the diff is the only record of what this skill did, and mixed with the user's uncommitted work it stops being reviewable.

### Step 1 — Audit

```bash
python3 <skill>/scripts/scan_project.py --project .
```

Read `.revamp/audit.md`. Then read enough of `lib/` to know what you are looking at — the entry point, the main screens, whatever `audit.json → derived` flagged. Four questions decide the whole plan:

1. **Standard app or Flame game?** (`derived.app_type`) — it selects `sources-ui.md` or `sources-game.md`.
2. **Material, Cupertino or mixed?** (`derived.ui_framework`) — a Cupertino app does not get a Material 3 seed scheme bolted on; use the Cupertino path in `integration-flutter.md § Theme`.
3. **State management?** Not to change it — to know what not to touch.
4. **Is there already a design system?** Extending `lib/theme/` beats replacing it.

If `scope` is unset and `dart_files >= 12`, use the audit's **Suggested screen priority** table (from `lib.priority_screens`) and propose the top 3–5 screens to the user before Step 6. Do not silently revamp every file in a large app.

Summarise for the user in one block: what the app is, and the specific weaknesses with **numbers from the audit** — "17 hardcoded colours across 6 files, no dark theme, 1 pubspec asset pointing at a missing directory". Never "the UI looks dated"; that is an opinion, and the audit produced facts.

### Step 2 — Lock the design direction

Nothing gets downloaded until this is written down. Assets chosen before a direction are assets chosen by taste, and they will not agree with each other.

Read `references/style-recipes.md`. If `style` and `seed` were not given, propose **two or three** recipes that fit the audit — not a menu of everything. Each option is a full recipe (icons, fonts, radius, illustration, motion), so the user chooses a look rather than fills a form. Then write `.revamp/design-direction.md` from the chosen recipe:

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
             (exception: About/Credits screen when attribution-required assets are used)
Kept         (any `keep:` inputs)
```

Get explicit agreement. This file is what Step 6 is checked against — a change of mind at Step 6 costs the whole step.

### Step 3 — Select assets and verify licences

Read `references/sources-ui.md` (app) or `references/sources-game.md` (game), and `references/licensing.md`.

Pick from the locked direction, then present the list **before downloading**. For each asset, also note how it will be fetched. Each sources file has a **Direct download URLs** section, which gives verified file-URL patterns (Kenney, Game-icons, Google Fonts, Fontshare, GitHub font releases, Fluent/Noto emoji, Mixkit, ambientCG, Poly Haven, …). It also lists the sources that must be downloaded by hand and imported with `--local`, and `sources-ui.md` has a **Checked and rejected** list. Do not guess URLs: a landing page returns HTML, and the script refuses it. For an icon set, check the package's API shape too. `apply_icons.py` swaps only to const `IconData`, so `font_awesome_flutter` (`FaIconData`), `iconoir_flutter` (widgets) and `hugeicons` (path data) need a widget-level refactor.

| Asset | Source | Licence | Credit | Size | Why this one |
|---|---|---|---|---|---|
| Lucide icon set (`lucide_icons_flutter`) | lucide.dev | ISC | license-page | ~40 KB tree-shaken | const IconData; matches 1.5px stroke direction |
| Satoshi | fontshare.com | ITF free commercial | license-page | 3 × 45 KB | Body font in the locked pairing |
| unDraw empty box | undraw.co | unDraw licence | none | 12 KB SVG | Recoloured to seed; transparent |

Not negotiable at this step: read the licence **from the source page now**. Reference files go out of date, and a licence quoted from one is a guess. Reject anything CC BY-NC, GPL or unlicensed, and state the reason.

The **Credit** column uses the same three levels that `CREDITS.md` records (`licensing.md § The Credit column`). Every `on-screen` asset needs a decision about **where on screen** its credit appears. If the app has no About screen, building one is part of this work. Wait for approval before Step 4.

### Step 4 — Download and optimize

```bash
python3 <skill>/scripts/fetch_asset.py --url <url> --dest assets/<kind> \
    --name "<name>" --author "<author>" --license <SPDX-ish> --source <page> --apply
python3 <skill>/scripts/optimize_flutter.py --project . --dir assets --apply --replace
```

`fetch_asset.py` does six things:

- **Normalises filenames** to `lower_snake_case`, because Dart asset paths become Dart identifiers under `flutter_gen`. `Satoshi-Regular.ttf` becomes `satoshi_regular.ttf`, and `OFL.txt` becomes `ofl.txt`. **Write pubspec paths from the names the script printed**, not from the vendor's zip listing. A mismatched font path is the silent fall-back-to-Roboto failure.
- **Refuses HTML.** If a URL returns an HTML page (a JS download button or a login wall), the script writes nothing. Find the direct file URL instead.
- **Respects no-script sites.** unDraw, Storyset/Freepik and Flaticon forbid downloading through a tool, and the script refuses their URLs. Download those files by hand in a browser, then import each one with `--local <file> --source <page>`. The same normalisation and CREDITS row apply (`licensing.md` trap 9).
- **Prints every LICENSE/README** it finds inside a zip. **Read them.**
- **Names single files sensibly.** Some URLs end in a generic basename: Noto `…/<cp>/lottie.json`, Material Symbols `…/24px.svg`, DiceBear `…/svg?seed=x`. Pass `--filename rocket.json` for these, or each download overwrites the last; the script warns when it sees one. A URL with no extension gets one sniffed from the content.
- **Writes the `assets/CREDITS.md` row** at download time, the only moment the metadata is reliably known. Re-downloading an asset replaces its row instead of adding a duplicate.

`optimize_flutter.py` handles each asset type differently:

- **Widget images** get a 1.0x/2.0x/3.0x set derived from the @3x source, converted to WebP.
- **Sprites keep their pixels and filenames** and are only recompressed losslessly. This covers every image in a Flame project, anything in `sprites/`, `tiles/` or `atlas/`, and anything with atlas metadata beside it. Flame reads no density buckets, and atlases and 9-slice insets address source pixels.
- **Audio becomes `.m4a` (AAC)** when the project has `ios/` or `macos/`, because `AVPlayer` cannot play OGG Vorbis. Otherwise it becomes OGG.

With `--replace`, the script lists every renamed file (`.png` → `.webp`, `.wav` → `.m4a`). Update each reference to the old name. At Step 7, `scan_project.py`'s "referenced in code but absent from disk" list must be empty. The script reports before/after bytes. Pillow, svgo and ffmpeg are each optional; a missing one is a skipped job with a warning, never a crash.

Then update `pubspec.yaml`. The script prints the snippet. **Directory entries are not recursive**, so every subdirectory needs its own line. Then run `flutter pub add <packages> && flutter pub get`, and read the resolved versions in `pubspec.lock`. Rive 0.14 and 0.13 have incompatible APIs (`integration-flutter.md § Rive`), and the icon package must be `lucide_icons_flutter`, not the stale `lucide_icons`.

### Step 5 — Build the design system

Read `references/integration-flutter.md § Theme` (including **Cupertino and mixed apps**) and § Typography. Branch on `derived.ui_framework`:

| Framework | Create |
|---|---|
| `material` / `mixed` | `ColorScheme.fromSeed` + `ThemeData` below; mixed also sets `cupertinoOverrideTheme` / shared `AppColors` |
| `cupertino` | `CupertinoThemeData` light/dark, bundled fonts on `CupertinoTextThemeData` — **not** a Material-only `AppTheme` |

Material (and mixed root) files:

| File | Contains |
|---|---|
| `lib/theme/app_colors.dart` | `ColorScheme.fromSeed` light + dark, `ThemeExtension` for success/warning |
| `lib/theme/app_typography.dart` | `TextTheme` built from the new font |
| `lib/theme/app_spacing.dart` | `AppSpacing` + `AppRadius` tokens |
| `lib/theme/app_theme.dart` | Assembled light/dark `ThemeData` (appBar, navBar, inputDecoration too) |
| `lib/widgets/app_button.dart` | Ripple + haptics + 48dp minimum |
| `lib/widgets/app_card.dart` | `Material` + `InkWell`, themed surface |
| `lib/widgets/empty_state.dart` | Illustration + title + message + action |
| `lib/widgets/loading_view.dart` | Rive/Lottie loader with a reduce-motion fallback. For Rive, use `RiveWidgetBuilder` + `FileLoader` (0.14), plus `RiveNative.init()` in `main` |
| `lib/widgets/app_skeleton.dart` | When audit has list/grid loaders — shimmer placeholder (§11 patterns) |
| `lib/widgets/nine_slice_panel.dart` | Flame / game UI only — from integration § 9-slice |

Wire Material apps:

```dart
MaterialApp(
  theme: AppTheme.light,
  darkTheme: AppTheme.dark,
  themeMode: ThemeMode.system,
  home: const HomeScreen(),
);
```

Then **build once, here**, while the surface area is still small:

```bash
flutter analyze && flutter run -d <device> --debug   # or: flutter build apk --debug
```

A font that is not resolving, a package version conflict, a renamed `CardTheme` — every one of those is a one-file fix now and a cascade after thirty files are touched.

### Step 6 — Apply to the real code

The step everything else exists to serve. Read `references/refactor-patterns.md` and follow its per-screen order: icons → colours → text → components → spacing → states → micro-interactions.

Icons first, because they are mechanical. The icon package must already be resolved (`flutter pub get` from Step 4), because the map is checked against its source:

```bash
python3 <skill>/scripts/generate_icon_map.py --project . --audit .revamp/audit.json --set lucide --out icons.json
python3 <skill>/scripts/apply_icons.py --project . --map icons.json                 # dry run
python3 <skill>/scripts/apply_icons.py --project . --map icons.json --apply --yes   # after the user approved the diff
```

Use `--set phosphor` when the locked direction says Phosphor. `generate_icon_map.py` drops any target the installed package does not define and lists it as `DROPPED`. If it prints `targets NOT verified`, the package is not resolved yet: fix that before applying. **Show the user the diff from the dry run before applying.** `--apply` without `--yes` asks on stdin, and a non-interactive shell answers "no".

The apply script:

- skips matches inside comments and strings, while `${…}` interpolations are treated as code;
- reports every unmapped icon;
- lists every **COLLISION**, where two icons became one glyph. For example, `home` and `home_outlined` both become `house`, so a `NavigationBar` `selectedIcon` stops showing the selected state. Fix those sites by tinting the selected glyph with `colorScheme.primary`;
- flags the **const hazard**. A callable replacement like `PhosphorIcons.house()` cannot sit inside `const Icon(...)`, and it fails in every touched file at once. Prefer const constants in the mapping; `--fix-const` is the fallback.

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
| Text overflow | New font metrics differ from Roboto. Check the longest label on the narrowest screen; test at text scale **1.0, 1.3, and 2.0**. |
| Reduce motion | With animations disabled (OS setting or `MediaQuery.disableAnimations`), loaders/Rive must not be required for meaning — provide a static fallback where needed. |
| Contrast | Body text ≥ 4.5:1, large text ≥ 3:1. Derived-from-seed schemes usually pass; hand-edited slots usually do not. |
| Touch targets | ≥ 48×48 dp on every tappable. |
| Assets declared | Re-run `scan_project.py`. `ORPHAN_ASSETS`, `MISSING_ASSETS` and `BROKEN_ASSET_REFS` must all be clear. The last one catches code still pointing at a file that `--replace` renamed. Density folders (`2.0x/`, `3.0x/`) are **not** orphans when the 1.0x sibling is declared. |
| Bundle delta | `flutter build apk --release --analyze-size --target-platform android-arm64`, before vs after (size analysis refuses multi-ABI builds; use the same ABI both times). |

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

Go through the `Credit` column of `CREDITS.md`:

- Every `license-page` row gets its licence text registered with `LicenseRegistry`, so `showLicensePage` tells the truth (`integration-flutter.md § Typography`).
- Every `on-screen` row (CC BY, Freepik, anything custom) needs a visible credit line on the About / Credits screen, not just the file.
- `none` rows need nothing.

Write `.revamp/report.md`:

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

**Scope** — never modify business logic, state management, API calls, or models; presentation layer only. Do not restructure navigation **except** when licensing requires a visible About/Credits screen (or the user asked for motion/transitions on existing routes). Never refactor the whole project in one pass. Never bulk-replace without a dry run whose diff the user has seen.

**Licensing** — state every licence before proposing the asset, read from the source page. "Free" never implies commercially usable; prefer CC0 / MIT / OFL. Attribution-required assets need a place on screen, decided before download. No third-party logos, IP or copyrighted characters, whatever the stated licence. `fetch_asset.py` refuses GPL / CC-BY-NC / ARR unless `--force` (user must approve).

**Consistency** — one icon set, one illustration style, at most two font families. Pick a full recipe from `style-recipes.md`; do not mix recipes. Vector over raster, WebP over PNG, a cohesive pack over assembled loose files. Rive for interactive animation, Lottie for linear.

**Theming** — every colour and text style flows through `ThemeData` or `CupertinoThemeData`; a new widget with a hardcoded colour is a bug in the revamp itself. Check dark mode explicitly: an illustration with a baked white background shows a slab, so find a transparent version or recolour it.

**Budget and accessibility** — assets under 30 MB, else cut or defer. Text contrast ≥ 4.5:1 (large text ≥ 3:1). Touch targets ≥ 48×48 dp. Label icon-only controls via `semanticLabel` or `IconButton.tooltip`; `excludeFromSemantics` on decorative art. Verify text scale 2.0 and reduce-motion fallbacks at Step 7.

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
lib/widgets/       app_button · app_card · empty_state · loading_view · app_skeleton
.revamp/           audit.md · audit.json · design-direction.md · report.md
```

`CREDITS.md` is a table with the columns Asset | Type | Files | Author | License | Credit | Source | Downloaded. `Credit` takes one of three values: `on-screen`, `license-page` or `none`. It is inferred from the licence, can be overridden with `--credit`, and unknown licences default to `on-screen`. `fetch_asset.py` writes the rows, and re-running it for the same asset replaces the row.

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
        todo.done ? LucideIcons.circleCheck : LucideIcons.circle,
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
      FlameAudio.play('sfx/click.m4a', volume: 0.6);
      HapticFeedback.selectionClick();
      onTap();
    },
    child: SizedBox(
      width: 220,
      height: 60,
      // Kenney's button is 64x64 with 16px borders — from the pack spec.
      child: NineSlicePanel(
        asset: 'assets/sprites/ui/button_blue.png',
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
          placeholder: (context, url) => const AppSkeleton(height: 140, radius: 12),
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
| `references/style-recipes.md` | Step 2 — locked pairings per style (icons, fonts, radius, motion) |
| `references/sources-ui.md` | Step 3 — icons, illustrations, fonts, animation, colour tools for an app |
| `references/sources-game.md` | Step 3 — sprite packs, tilesets, audio, sprite hygiene for a Flame game |
| `references/licensing.md` | Step 3, before any download — licence table and the traps |
| `references/integration-flutter.md` | Steps 4–5 — pubspec, buckets, SVG, Rive, 9-slice, Material/Cupertino theme, Flame, bundle size |
| `references/refactor-patterns.md` | Step 6 — every BEFORE→AFTER transformation and the icon mapping table |

| Script | Run at |
|---|---|
| `scripts/scan_project.py` | Step 1 and again at Step 7 — writes `.revamp/audit.{json,md}` |
| `scripts/fetch_asset.py` | Step 4 — download, reject HTML, normalise filenames, write/replace the CREDITS row with a 3-level credit; denylists GPL/NC/ARR |
| `scripts/optimize_flutter.py` | Step 4 — density buckets + WebP for widget images, lossless in-place for sprites, svgo, m4a/OGG by platform, rename list, size report, pubspec snippet |
| `scripts/generate_icon_map.py` | Step 6 — audit.json → `icons.json` for Lucide or Phosphor, verified against the resolved package source; reports collisions |
| `scripts/apply_icons.py` | Step 6 — bulk icon swap; dry run by default, const-hazard and collision detection |

`fetch_asset`, `optimize_flutter`, and `apply_icons` default to a dry run and write only with `--apply`. `scan_project` and `generate_icon_map` always write their output files (read-only w.r.t. app source).

## Scope

Does: audit an existing Flutter codebase, lock a design direction, source licence-verified free assets, optimize them for the bundle, build a themed design system, refactor real screens to use it, add micro-interactions and motion, wire game UI packs and SFX for Flame, verify by analyzing and building, and hand off with credits and a before/after report.

Does not: create a Flutter project (see `flutter-init`); design custom original artwork; change business logic, state management, APIs, models or navigation structure; buy paid assets; produce store listing graphics (see `flutter-store-metadata`); sign or publish (see `flutter-signing`, `flutter-publish`); touch non-Flutter codebases.
