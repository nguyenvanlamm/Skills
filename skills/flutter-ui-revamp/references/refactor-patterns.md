# Refactor patterns

Read at Step 6 — the step that decides whether this was a UI revamp or an asset download. Downloading a font changes nothing until a `TextTheme` uses it, and downloading an illustration changes nothing until an empty state renders it.

**The boundary, restated because it is the rule most likely to be broken under momentum:** these patterns touch the *presentation layer only*. A `build()` method, a widget file, a theme file — yes. A repository, a bloc, a provider, a model, an API client, a `Future` that fetches — no. If a change alters what the app does rather than how it looks, it is out of scope, and out of scope means "raise it with the user", not "fix it while you're in there".

Work one screen at a time. After each screen: `flutter analyze`, then summarise what changed.

---

## 1. Default Material icons → a coherent icon set

**BEFORE**

```dart
AppBar(
  leading: IconButton(
    icon: const Icon(Icons.arrow_back),
    onPressed: () => Navigator.pop(context),
  ),
  actions: [
    IconButton(icon: const Icon(Icons.search), onPressed: _search),
    IconButton(icon: const Icon(Icons.more_vert), onPressed: _menu),
  ],
);
```

**AFTER**

```dart
import 'package:lucide_icons/lucide_icons.dart';

AppBar(
  leading: IconButton(
    icon: const Icon(LucideIcons.arrowLeft),
    tooltip: 'Back',
    onPressed: () => Navigator.pop(context),
  ),
  actions: [
    IconButton(
      icon: const Icon(LucideIcons.search),
      tooltip: 'Search',
      onPressed: _search,
    ),
    IconButton(
      icon: const Icon(LucideIcons.moreVertical),
      tooltip: 'More',
      onPressed: _menu,
    ),
  ],
);
```

`tooltip` is not decoration — on `IconButton` it also feeds the semantics tree, which is how the `NO_SEMANTICS` finding gets closed.

### The const hazard

`Icons.search` is a `const IconData`. So is `LucideIcons.search`, so the swap above is free. But `phosphor_flutter`'s ergonomic API is a **call**:

```dart
const Icon(PhosphorIcons.magnifyingGlass())  // ✗ does not compile
Icon(PhosphorIcons.magnifyingGlass())        // ✓
const Icon(PhosphorIconsRegular.magnifyingGlass) // ✓ const constant
```

Map to the **const constants** (`PhosphorIconsRegular.*`, `PhosphorIconsBold.*`) whenever the weight is fixed. `apply_icons.py` detects the hazard, names every site, and can strip the governing `const` with `--fix-const` — but a const-safe mapping is the better answer, because dropping `const` costs rebuild performance across the whole subtree.

### Mapping table

Verify each constant against the package version you actually installed. Icon sets rename glyphs between releases — Lucide renamed `home` to `house`, and packages lag upstream by varying amounts. A mapping that assumes a name is a mapping that produces 40 analyzer errors.

| Material | Lucide (`lucide_icons`) | Phosphor const (`phosphor_flutter`) |
|---|---|---|
| `Icons.home` | `LucideIcons.house` | `PhosphorIconsRegular.house` |
| `Icons.search` | `LucideIcons.search` | `PhosphorIconsRegular.magnifyingGlass` |
| `Icons.settings` | `LucideIcons.settings` | `PhosphorIconsRegular.gear` |
| `Icons.person` | `LucideIcons.user` | `PhosphorIconsRegular.user` |
| `Icons.add` | `LucideIcons.plus` | `PhosphorIconsRegular.plus` |
| `Icons.delete` | `LucideIcons.trash2` | `PhosphorIconsRegular.trash` |
| `Icons.edit` | `LucideIcons.pencil` | `PhosphorIconsRegular.pencilSimple` |
| `Icons.favorite` | `LucideIcons.heart` | `PhosphorIconsFill.heart` |
| `Icons.favorite_border` | `LucideIcons.heart` | `PhosphorIconsRegular.heart` |
| `Icons.share` | `LucideIcons.share2` | `PhosphorIconsRegular.shareNetwork` |
| `Icons.menu` | `LucideIcons.menu` | `PhosphorIconsRegular.list` |
| `Icons.close` | `LucideIcons.x` | `PhosphorIconsRegular.x` |
| `Icons.check` | `LucideIcons.check` | `PhosphorIconsRegular.check` |
| `Icons.arrow_back` | `LucideIcons.arrowLeft` | `PhosphorIconsRegular.arrowLeft` |
| `Icons.arrow_forward` | `LucideIcons.arrowRight` | `PhosphorIconsRegular.arrowRight` |
| `Icons.chevron_right` | `LucideIcons.chevronRight` | `PhosphorIconsRegular.caretRight` |
| `Icons.notifications` | `LucideIcons.bell` | `PhosphorIconsRegular.bell` |
| `Icons.shopping_cart` | `LucideIcons.shoppingCart` | `PhosphorIconsRegular.shoppingCart` |
| `Icons.more_vert` | `LucideIcons.moreVertical` | `PhosphorIconsRegular.dotsThreeVertical` |
| `Icons.star` | `LucideIcons.star` | `PhosphorIconsRegular.star` |
| `Icons.calendar_today` | `LucideIcons.calendar` | `PhosphorIconsRegular.calendarBlank` |
| `Icons.camera_alt` | `LucideIcons.camera` | `PhosphorIconsRegular.camera` |
| `Icons.download` | `LucideIcons.download` | `PhosphorIconsRegular.downloadSimple` |
| `Icons.filter_list` | `LucideIcons.filter` | `PhosphorIconsRegular.funnel` |
| `Icons.info_outline` | `LucideIcons.info` | `PhosphorIconsRegular.info` |
| `Icons.lock` | `LucideIcons.lock` | `PhosphorIconsRegular.lock` |
| `Icons.logout` | `LucideIcons.logOut` | `PhosphorIconsRegular.signOut` |
| `Icons.mail` / `Icons.email` | `LucideIcons.mail` | `PhosphorIconsRegular.envelope` |
| `Icons.refresh` | `LucideIcons.refreshCw` | `PhosphorIconsRegular.arrowsClockwise` |
| `Icons.visibility` | `LucideIcons.eye` | `PhosphorIconsRegular.eye` |
| `Icons.visibility_off` | `LucideIcons.eyeOff` | `PhosphorIconsRegular.eyeSlash` |
| `Icons.warning` | `LucideIcons.alertTriangle` | `PhosphorIconsRegular.warning` |
| `Icons.location_on` | `LucideIcons.mapPin` | `PhosphorIconsRegular.mapPin` |
| `Icons.play_arrow` | `LucideIcons.play` | `PhosphorIconsFill.play` |
| `Icons.pause` | `LucideIcons.pause` | `PhosphorIconsFill.pause` |
| `Icons.send` | `LucideIcons.send` | `PhosphorIconsRegular.paperPlaneTilt` |
| `Icons.bookmark` | `LucideIcons.bookmark` | `PhosphorIconsRegular.bookmarkSimple` |

Save the chosen mapping as JSON and feed it to `apply_icons.py`:

```json
{
  "import": "package:lucide_icons/lucide_icons.dart",
  "map": {
    "Icons.home": "LucideIcons.house",
    "Icons.search": "LucideIcons.search",
    "Icons.arrow_back": "LucideIcons.arrowLeft"
  }
}
```

Prefer generating the map from the audit rather than hand-typing it:

```bash
python3 <skill>/scripts/generate_icon_map.py --project . --audit .revamp/audit.json --set lucide --out icons.json
```

Icons with no good equivalent stay Material — the script lists them as UNMAPPED. One deliberate exception beats a forced glyph that means the wrong thing.

**Verify constants against the installed package version** before `--apply`. Lucide upstream renamed `home` → `house`; this table uses `house`. If `lucide_icons` on pub lags and still exposes `home` only, check the package API and adjust the map — do not guess.

---

## 2. Hardcoded colours → scheme tokens

**BEFORE**

```dart
Container(
  color: const Color(0xFFF5F5F5),
  child: Text('Total', style: TextStyle(color: Colors.black87)),
);
```

**AFTER**

```dart
final scheme = Theme.of(context).colorScheme;

Container(
  color: scheme.surfaceContainer,
  child: Text('Total', style: TextStyle(color: scheme.onSurface)),
);
```

Translation table — this is the mapping that matters, because picking the wrong slot is how you get text that vanishes in dark mode:

| Hardcoded | Token |
|---|---|
| page background | `scheme.surface` |
| card / raised panel | `scheme.surfaceContainer`, `surfaceContainerHigh` |
| primary text | `scheme.onSurface` |
| secondary / caption text | `scheme.onSurfaceVariant` |
| brand fill (button, chip) | `scheme.primary` + `scheme.onPrimary` |
| divider / border | `scheme.outlineVariant` |
| error text and fills | `scheme.error` / `scheme.onError` |
| success, warning | `Theme.of(context).extension<AppSemanticColors>()!` |

`Colors.white` and `Colors.black` are the two worst offenders because they look correct in whichever mode you developed in. The only legitimate uses are inside a colour *definition* and over an image scrim.

**Never** put a raw `scheme.primary` on a background as text. It is a fill colour; on a light scheme it commonly measures under 3:1. For coloured text use `scheme.primary` on a `primaryContainer` surface, or `onPrimaryContainer`.

---

## 3. Scattered `TextStyle` → `TextTheme`

**BEFORE**

```dart
Column(children: [
  Text('Orders', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
  Text('3 pending', style: TextStyle(fontSize: 13, color: Colors.grey)),
]);
```

**AFTER**

```dart
final text = Theme.of(context).textTheme;

Column(children: [
  Text('Orders', style: text.headlineMedium),
  Text('3 pending', style: text.bodyMedium),
]);
```

One-off deviation — override, never rebuild:

```dart
Text('12', style: text.headlineMedium?.copyWith(
  fontFeatures: const [FontFeature.tabularFigures()],
));
```

`copyWith` inherits the family, the colour and the line height. A fresh `TextStyle(fontSize: 28)` inherits nothing, which is how the new font fails to appear on the one screen everybody looks at.

---

## 4. Repeated `Container` + `BoxDecoration` → components

**BEFORE** — the same eleven lines in four files:

```dart
Container(
  padding: const EdgeInsets.all(16),
  decoration: BoxDecoration(
    color: Colors.white,
    borderRadius: BorderRadius.circular(12),
    boxShadow: const [
      BoxShadow(color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 2)),
    ],
  ),
  child: child,
);
```

**AFTER**

```dart
// lib/widgets/app_card.dart
import 'package:flutter/material.dart';
import '../theme/app_spacing.dart';

class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.md),
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final radius = BorderRadius.circular(AppRadius.lg);
    return Material(
      color: scheme.surfaceContainer,
      borderRadius: radius,
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(padding: padding, child: child),
      ),
    );
  }
}
```

`Material` + `InkWell` rather than `Container` + `GestureDetector`: the ripple is what makes the card feel like a control instead of a picture of one, and it comes free.

---

## 5. Magic numbers → spacing and radius tokens

**BEFORE**

```dart
padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
const SizedBox(height: 22),
borderRadius: BorderRadius.circular(9),
```

**AFTER**

```dart
// lib/theme/app_spacing.dart
/// A 4pt scale. Every gap in the app is one of these seven values.
class AppSpacing {
  AppSpacing._();
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;
}

class AppRadius {
  AppRadius._();
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 18;
  static const double pill = 999;
}
```

```dart
padding: const EdgeInsets.symmetric(
  horizontal: AppSpacing.md,
  vertical: AppSpacing.sm + AppSpacing.xs,
),
const SizedBox(height: AppSpacing.lg),
borderRadius: BorderRadius.circular(AppRadius.sm),
```

18, 11, 22, 9 are not a design — they are four different people's guesses. Snapping to a scale is the cheapest visible improvement in this whole document, because inconsistent rhythm is what the eye reads as "unpolished" without being able to name.

---

## 6. Blank screen → `EmptyState` with an illustration

**BEFORE**

```dart
if (items.isEmpty) {
  return const Center(child: Text('No items'));
}
```

**AFTER**

```dart
// lib/widgets/empty_state.dart
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../theme/app_spacing.dart';

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.illustration,
    required this.title,
    this.message,
    this.action,
  });

  final String illustration; // e.g. 'assets/illustrations/empty_box.svg'
  final String title;
  final String? message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SvgPicture.asset(
              illustration,
              width: 200,
              excludeFromSemantics: true, // decorative; the title carries meaning
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(title, style: text.titleMedium, textAlign: TextAlign.center),
            if (message != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(message!, style: text.bodyMedium, textAlign: TextAlign.center),
            ],
            if (action != null) ...[
              const SizedBox(height: AppSpacing.lg),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}
```

```dart
if (items.isEmpty) {
  return EmptyState(
    illustration: 'assets/illustrations/empty_box.svg',
    title: 'Nothing here yet',
    message: 'Items you add will show up on this screen.',
    action: FilledButton(onPressed: _add, child: const Text('Add the first one')),
  );
}
```

Same treatment for error and no-results states. Check the illustration on a dark surface before committing — an SVG with a baked white background shows a slab, which is the `licensing.md` dark-mode trap arriving in the UI.

---

## 7. `CircularProgressIndicator` → a branded loader

**BEFORE**

```dart
return const Center(child: CircularProgressIndicator());
```

**AFTER**

```dart
// lib/widgets/loading_view.dart
import 'package:flutter/material.dart';
import 'package:rive/rive.dart';

class LoadingView extends StatelessWidget {
  const LoadingView({super.key, this.label});

  final String? label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Semantics(
        label: label ?? 'Loading',
        liveRegion: true,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 96,
              height: 96,
              child: RiveAnimation.asset(
                'assets/animations/loader.riv',
                fit: BoxFit.contain,
              ),
            ),
            if (label != null) ...[
              const SizedBox(height: 12),
              Text(label!, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ],
        ),
      ),
    );
  }
}
```

Two caveats worth more than the animation. A spinner where a **skeleton** belongs is a downgrade — if the shape of the incoming content is known, render the shape (see §11). And a Rive loader that takes 400 ms to decode makes fast loads *feel slower*; keep a plain indicator for anything expected under ~300 ms.

---

## 8. Loose PNGs → WebP + buckets + typed references

**BEFORE**

```dart
Image.asset('assets/images/hero.png', width: 160);
```

**AFTER**

```
assets/images/hero.webp
assets/images/2.0x/hero.webp
assets/images/3.0x/hero.webp
```

```dart
import 'package:my_app/gen/assets.gen.dart';

Assets.images.hero.image(width: 160);
```

`optimize_flutter.py --assume 3x --apply --replace` produces the three files from one @3x source. Then `dart run build_runner build --delete-conflicting-outputs` regenerates `assets.gen.dart`. A path typo is now a compile error rather than a grey box that ships.

---

## 9. Dead buttons → ripple, haptics, press-scale

**BEFORE**

```dart
GestureDetector(
  onTap: _submit,
  child: Container(
    height: 44,
    color: Colors.blue,
    child: const Center(child: Text('Submit')),
  ),
);
```

**AFTER**

```dart
// lib/widgets/app_button.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppButton extends StatefulWidget {
  const AppButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;

  @override
  State<AppButton> createState() => _AppButtonState();
}

class _AppButtonState extends State<AppButton> {
  bool _down = false;

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onPressed != null;
    return AnimatedScale(
      scale: _down ? 0.97 : 1.0,
      duration: const Duration(milliseconds: 90),
      curve: Curves.easeOut,
      child: FilledButton.icon(
        onPressed: enabled
            ? () {
                HapticFeedback.lightImpact();
                widget.onPressed!();
              }
            : null,
        onLongPress: null,
        icon: widget.icon == null ? null : Icon(widget.icon, size: 20),
        label: Text(widget.label),
        style: FilledButton.styleFrom(
          // 48dp is the accessibility floor, not a style choice.
          minimumSize: const Size(64, 48),
        ),
      ),
    );
  }
}
```

Press-scale needs the pointer state, which `FilledButton` does not expose — wrap it in a `Listener` (`onPointerDown` / `onPointerUp` / `onPointerCancel` setting `_down`) when the effect is wanted. Handle `onPointerCancel`: without it, a drag off the button leaves it stuck at 0.97.

Haptics are for confirmations, not for every tap. `lightImpact` on a primary action, `selectionClick` on a picker, `heavyImpact` on an error. A phone that buzzes on every touch gets its haptics turned off system-wide.

---

## 10. Hard screen cuts → transitions and Hero

**BEFORE**

```dart
Navigator.push(context, MaterialPageRoute(builder: (_) => DetailScreen(item)));
```

**AFTER**

```dart
Navigator.push(context, _fadeThrough(DetailScreen(item)));

Route<T> _fadeThrough<T>(Widget page) {
  return PageRouteBuilder<T>(
    transitionDuration: const Duration(milliseconds: 280),
    reverseTransitionDuration: const Duration(milliseconds: 220),
    pageBuilder: (_, __, ___) => page,
    transitionsBuilder: (_, animation, __, child) {
      final curved =
          CurvedAnimation(parent: animation, curve: Curves.easeOutCubic);
      return FadeTransition(
        opacity: curved,
        child: SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0, 0.03),
            end: Offset.zero,
          ).animate(curved),
          child: child,
        ),
      );
    },
  );
}
```

Shared image, both ends, same tag:

```dart
// list
Hero(tag: 'product-${item.id}', child: Image.asset(item.image, height: 96));

// detail
Hero(tag: 'product-${item.id}', child: Image.asset(item.image, height: 320));
```

Tags must be unique per screen. A `Hero` inside a `ListView` where two items share a tag throws at runtime — use the entity id, never the list index.

---

## 11. Spinner-over-layout → skeleton

**BEFORE**

```dart
loading ? const CircularProgressIndicator() : ProductList(products);
```

**AFTER**

```dart
// lib/widgets/app_skeleton.dart
import 'package:flutter/material.dart';

class AppSkeleton extends StatefulWidget {
  const AppSkeleton({super.key, this.height = 16, this.width, this.radius = 8});

  final double height;
  final double? width;
  final double radius;

  @override
  State<AppSkeleton> createState() => _AppSkeletonState();
}

class _AppSkeletonState extends State<AppSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return FadeTransition(
      opacity: Tween<double>(begin: 0.45, end: 1.0)
          .animate(CurvedAnimation(parent: _c, curve: Curves.easeInOut)),
      child: Container(
        height: widget.height,
        width: widget.width,
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(widget.radius),
        ),
      ),
    );
  }
}
```

```dart
loading
    ? ListView.builder(
        itemCount: 6,
        itemBuilder: (_, __) => const Padding(
          padding: EdgeInsets.all(16),
          child: Row(children: [
            AppSkeleton(height: 64, width: 64, radius: 12),
            SizedBox(width: 12),
            Expanded(child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppSkeleton(height: 14, width: 160),
                SizedBox(height: 8),
                AppSkeleton(height: 12, width: 90),
              ],
            )),
          ]),
        ),
      )
    : ProductList(products);
```

Always `dispose()` the controller. A repeating `AnimationController` leaked from a list item is a real battery bug, not a style nit.

---

## 12. Games — loose sprites → atlas, drawn panels → 9-slice

**BEFORE**

```dart
add(SpriteComponent(sprite: await loadSprite('ui/btn_play.png')));
add(SpriteComponent(sprite: await loadSprite('ui/btn_pause.png')));
add(SpriteComponent(sprite: await loadSprite('ui/panel_bg.png')));
```

**AFTER**

```dart
@override
Future<void> onLoad() async {
  await images.loadAll(<String>['ui/atlas.png']);
  final atlas = await fromJSONString(
    await rootBundle.loadString('assets/images/ui/atlas.json'),
    images.fromCache('ui/atlas.png'),
  );
  add(SpriteComponent(sprite: atlas.getSprite('btn_play.png')));
  add(SpriteComponent(sprite: atlas.getSprite('btn_pause.png')));
}
```

Three loads and three draw-call batches become one of each.

Panels: replace the hand-drawn stretched PNG with the `NineSlicePanel` from `integration-flutter.md`, using the insets from the pack's spec. A Kenney panel at 64×64 with 16 px borders scales from a tooltip to a dialog with the corners intact.

SFX belong on the event, not on the frame:

```dart
void _onButtonPressed() {
  FlameAudio.play('sfx/click.ogg', volume: 0.6);
  HapticFeedback.selectionClick();
  overlays.add('pauseMenu');
}

void _onWin() => FlameAudio.play('sfx/win.ogg');
void _onLose() => FlameAudio.play('sfx/lose.ogg');
```

Preload every clip in `onLoad` (`FlameAudio.audioCache.loadAll`). A first-play decode mid-game is an audible stutter at the exact moment the player is watching.

---

## Order of operations within a screen

1. Icons — mechanical, `apply_icons.py`, dry run first.
2. Colours — to `scheme.*`. Now dark mode works.
3. Text — to `textTheme`. Now the font is visible.
4. Extract repeated decoration into components.
5. Snap remaining magic numbers to the spacing scale.
6. Replace empty / loading / error states with the new assets.
7. Micro-interactions last — ripple, haptics, transitions.

Then `flutter analyze`, then summarise, then the next screen. Reversing this order — starting with the fun animation work — means the animation gets rewritten when the theme lands underneath it.

## Do not

- Touch a repository, service, bloc, provider, model, or API call.
- Rename anything outside the presentation layer.
- Rewrite a whole project in one pass. One screen, verified, then the next.
- Introduce a second icon set, a third font, or an off-scale spacing value "just here".
- Delete an asset before confirming nothing references it — `scan_project.py`'s orphan list is the evidence, and it only reports static string references.
