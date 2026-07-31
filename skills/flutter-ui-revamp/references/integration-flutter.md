# Integrating assets into Flutter

Read at Step 4 and Step 5. Every snippet is null-safe and compiles against Flutter 3.22+ / Dart 3.4+.

**On versions:** the constraints below were current when this file was written and pub moves. Add packages with `flutter pub add rive` rather than pasting a pin, then check the resolved version against the API used here.

| Package | Constraint at time of writing | For |
|---|---|---|
| `flutter_svg` | `^2.0.10` | runtime SVG |
| `vector_graphics` / `vector_graphics_compiler` | `^1.1.11` | precompiled `.vec` |
| `rive` | `^0.13.0` | state-machine animation |
| `lottie` | `^3.1.0` | linear animation |
| `google_fonts` | `^6.2.1` | font resolution (bundled — see `licensing.md`) |
| `cached_network_image` | `^3.3.1` | remote images |
| `flutter_gen_runner` (dev) | `^5.4.0` | typed asset accessors |
| `flame` / `flame_audio` | `^1.18.0` / `^2.10.0` | 2D game engine + audio |
| `just_audio` | `^0.9.37` | app-side audio |

## Declaring assets

```yaml
flutter:
  uses-material-design: true
  assets:
    - assets/images/          # directory entry: immediate children only
    - assets/illustrations/
    - assets/icons/
    - assets/animations/
    - assets/audio/sfx/       # NOT covered by "assets/audio/"
    - assets/audio/music/
  fonts:
    - family: Satoshi
      fonts:
        - asset: assets/fonts/Satoshi-Regular.ttf
          weight: 400
        - asset: assets/fonts/Satoshi-Medium.ttf
          weight: 500
        - asset: assets/fonts/Satoshi-Bold.ttf
          weight: 700
```

**A directory entry is not recursive.** `assets/audio/` does not pick up `assets/audio/sfx/beep.ogg` — every subdirectory needs its own line. This is the single most common cause of "works in debug on my machine, `Unable to load asset` in release", and it is what `scan_project.py`'s `ORPHAN_ASSETS` finding detects.

Directory entry when the folder's contents change often (sprite packs, icon sets). Individual entries when the list is short and stable, or when you want an unused file to stay out of the bundle.

For a variable font, declare the file once and drive it with `FontVariation`:

```yaml
    - family: Inter
      fonts:
        - asset: assets/fonts/Inter-Variable.ttf
```

```dart
const heading = TextStyle(
  fontFamily: 'Inter',
  fontVariations: <FontVariation>[FontVariation('wght', 650)],
);
```

## Density buckets

```
assets/images/hero.webp          <- 1.0x, and the path you reference
assets/images/2.0x/hero.webp     <- same filename, exactly
assets/images/3.0x/hero.webp
```

You declare and reference **only** the 1.0x path. `AssetImage` reads `MediaQuery.devicePixelRatio` and picks the nearest bucket at or above it, falling back to the main asset. Buckets need no pubspec entries of their own — the directory entry covers them.

```dart
Image.asset('assets/images/hero.webp', width: 160); // resolves 3.0x on a Pixel 8
```

Sizes: if the design calls for 160 logical pixels, the 1.0x file is 160 px wide, 2.0x is 320, 3.0x is 480. `optimize_flutter.py --assume 3x` derives all three from the @3x source. Shipping only a 1.0x file means every modern phone upscales it, which is exactly the soft, slightly blurry look that reads as "cheap app".

Vectors (SVG, `.vec`, Rive) have no buckets and need none. Prefer them.

## SVG

```dart
import 'package:flutter_svg/flutter_svg.dart';

SvgPicture.asset(
  'assets/icons/rocket.svg',
  width: 24,
  height: 24,
  colorFilter: ColorFilter.mode(
    Theme.of(context).colorScheme.primary,
    BlendMode.srcIn,
  ),
  semanticsLabel: 'Launch',
);
```

`colorFilter` with `BlendMode.srcIn` is how an SVG picks up the theme — a hardcoded fill inside the file will not follow dark mode.

### Precompile to `.vec`

Parsing SVG XML at runtime costs real milliseconds per first paint. Compile once instead:

```bash
dart run vector_graphics_compiler --input-dir assets/icons --out-dir assets/icons
```

```dart
import 'package:vector_graphics/vector_graphics.dart';

const VectorGraphic(
  loader: AssetBytesLoader('assets/icons/rocket.svg.vec'),
  width: 24,
  height: 24,
);
```

Declare the `.vec` files in pubspec (the directory entry covers them) and you may drop the `.svg` sources from the bundle.

### SVG or an icon font?

| Situation | Use |
|---|---|
| Monochrome glyph, tinted by theme, many sizes | **icon font** — one file, no per-icon decode, `IconData` is const |
| Multi-colour, gradients, or an illustration | **SVG / `.vec`** |
| Under ~40 glyphs from mixed sources | **custom icon font** (below) |
| A published set with a maintained package | the **package** (`lucide_icons`, `phosphor_flutter`) |

## Custom icon font from SVGs

1. Collect the SVGs — single path, no strokes (convert strokes to fills), square viewBox.
2. Upload to **fluttericon.com**, select the glyphs, name the font, download.
3. Put `MyIcons.ttf` in `assets/fonts/` and declare it.

```yaml
    - family: MyIcons
      fonts:
        - asset: assets/fonts/MyIcons.ttf
```

```dart
// lib/theme/app_icons.dart
import 'package:flutter/widgets.dart';

/// Glyphs generated by fluttericon.com. Codepoints must match the download.
class AppIcons {
  AppIcons._();

  static const _family = 'MyIcons';
  static const IconData home = IconData(0xe800, fontFamily: _family);
  static const IconData search = IconData(0xe801, fontFamily: _family);
  static const IconData settings = IconData(0xe802, fontFamily: _family);
}
```

These are `const`, so `const Icon(AppIcons.home)` compiles — which makes them safe targets for `apply_icons.py`.

If you ever build with `--no-tree-shake-icons`, a full icon package costs ~1 MB. Prefer a custom font over disabling tree-shaking.

## Rive

```dart
import 'package:rive/rive.dart';

RiveAnimation.asset(
  'assets/animations/loader.riv',
  fit: BoxFit.contain,
  animations: const ['idle'],
);
```

### State machine — an interactive button

```dart
import 'package:flutter/material.dart';
import 'package:rive/rive.dart';

class RiveLikeButton extends StatefulWidget {
  const RiveLikeButton({super.key, required this.onTap});

  final VoidCallback onTap;

  @override
  State<RiveLikeButton> createState() => _RiveLikeButtonState();
}

class _RiveLikeButtonState extends State<RiveLikeButton> {
  SMIBool? _pressed;

  void _onInit(Artboard artboard) {
    final controller =
        StateMachineController.fromArtboard(artboard, 'ButtonMachine');
    if (controller == null) return; // machine renamed in the .riv — fail soft
    artboard.addController(controller);
    _pressed = controller.findSMI<SMIBool>('pressed');
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Like',
      child: GestureDetector(
        onTap: () {
          _pressed?.value = !(_pressed?.value ?? false);
          widget.onTap();
        },
        child: SizedBox(
          width: 64,
          height: 64,
          child: RiveAnimation.asset(
            'assets/animations/like_button.riv',
            onInit: _onInit,
            fit: BoxFit.contain,
          ),
        ),
      ),
    );
  }
}
```

Two things that go wrong: the state-machine name is set by the artist and is case-sensitive, and `findSMI` returns null for a renamed input. Both fail silently to a static drawing. Handle null rather than `!`.

Rive is not a `TickerProvider` animation — it runs its own renderer, and a `.riv` left mounted off-screen keeps ticking. Dispose or unmount it.

## Lottie

```dart
import 'package:lottie/lottie.dart';

Lottie.asset(
  'assets/animations/empty_box.json',
  width: 220,
  repeat: true,
  frameRate: FrameRate.max,
);
```

Lottie JSON with embedded raster images is a trap — it is a zip of PNGs wearing a vector costume, and it is enormous. Check the file size; a real vector Lottie is 10–80 KB.

## Remote images

```dart
import 'package:cached_network_image/cached_network_image.dart';

CachedNetworkImage(
  imageUrl: url,
  fadeInDuration: const Duration(milliseconds: 200),
  placeholder: (context, _) => const AppSkeleton(height: 180),
  errorWidget: (context, _, __) => Icon(
    Icons.broken_image_outlined,
    color: Theme.of(context).colorScheme.outline,
  ),
);
```

Warm a local hero image before the route that shows it, so it does not pop in:

```dart
@override
void didChangeDependencies() {
  super.didChangeDependencies();
  precacheImage(const AssetImage('assets/images/hero.webp'), context);
}
```

WebP over PNG: typically 25–35% smaller at visually identical quality, decoded by Flutter on every platform, alpha supported. Use lossless WebP for flat UI art and sprites, lossy (q85) for photography.

## 9-slice panels

```dart
/// A game panel that scales without smearing its corners.
///
/// [border] is given in the SOURCE image's pixel coordinates, and the widget
/// must end up LARGER than the source in both axes — Flutter asserts
/// otherwise in debug. Get the insets from the pack's spec sheet.
class NineSlicePanel extends StatelessWidget {
  const NineSlicePanel({
    super.key,
    required this.child,
    required this.sourceSize,
    this.asset = 'assets/sprites/ui/panel_beige.webp',
    this.border = const EdgeInsets.all(16),
    this.padding = const EdgeInsets.all(20),
  });

  final Widget child;
  final String asset;

  /// Pixel dimensions of the source image, needed to place the centre rect.
  final Size sourceSize;

  /// Border insets of the source image, in source pixels.
  final EdgeInsets border;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(
          child: Image.asset(
            asset,
            fit: BoxFit.fill,
            centerSlice: Rect.fromLTRB(
              border.left,
              border.top,
              sourceSize.width - border.right,
              sourceSize.height - border.bottom,
            ),
            filterQuality: FilterQuality.none, // keep pixel art crisp
          ),
        ),
        Padding(padding: padding, child: child),
      ],
    );
  }
}
```

`centerSlice` takes the *stretchable centre rectangle* in source pixels, not the insets themselves — for a 64×64 panel with 16 px borders that is `Rect.fromLTRB(16, 16, 48, 48)`, which is what the arithmetic above produces. Read the pack's spec; guessing produces a panel whose corners look almost right, which is worse than obviously wrong.

## Theme

Everything visual flows through `ThemeData`. A colour or a `TextStyle` written inside a screen is a bug, not a shortcut — it will not follow dark mode, and it will not follow the next revamp.

```dart
// lib/theme/app_colors.dart
import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  static const seed = Color(0xFF4F46E5);

  static final ColorScheme light = ColorScheme.fromSeed(
    seedColor: seed,
    brightness: Brightness.light,
  );

  static final ColorScheme dark = ColorScheme.fromSeed(
    seedColor: seed,
    brightness: Brightness.dark,
  );
}

/// Colours Material 3 has no slot for. Extensions keep them themed and
/// lerp-able instead of hardcoded at the call site.
@immutable
class AppSemanticColors extends ThemeExtension<AppSemanticColors> {
  const AppSemanticColors({required this.success, required this.warning});

  final Color success;
  final Color warning;

  @override
  AppSemanticColors copyWith({Color? success, Color? warning}) =>
      AppSemanticColors(
        success: success ?? this.success,
        warning: warning ?? this.warning,
      );

  @override
  AppSemanticColors lerp(ThemeExtension<AppSemanticColors>? other, double t) {
    if (other is! AppSemanticColors) return this;
    return AppSemanticColors(
      success: Color.lerp(success, other.success, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
    );
  }

  static const lightColors =
      AppSemanticColors(success: Color(0xFF166534), warning: Color(0xFF92400E));
  static const darkColors =
      AppSemanticColors(success: Color(0xFF4ADE80), warning: Color(0xFFFBBF24));
}
```

```dart
// lib/theme/app_theme.dart
import 'package:flutter/material.dart';
import 'app_colors.dart';
import 'app_typography.dart';

class AppTheme {
  AppTheme._();

  static ThemeData _base(ColorScheme scheme, AppSemanticColors semantic) {
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: scheme.surface,
      textTheme: AppTypography.textTheme(scheme),
      extensions: <ThemeExtension<dynamic>>[semantic],
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(64, 48), // 48dp: the accessibility floor
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: scheme.surfaceContainer,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
    );
  }

  static ThemeData get light =>
      _base(AppColors.light, AppSemanticColors.lightColors);
  static ThemeData get dark =>
      _base(AppColors.dark, AppSemanticColors.darkColors);
}
```

`CardTheme` was renamed to `CardThemeData` in Flutter 3.22+. On an older SDK the analyzer will tell you; use whichever the project's SDK exposes.

```dart
MaterialApp(
  theme: AppTheme.light,
  darkTheme: AppTheme.dark,
  themeMode: ThemeMode.system,
  home: const HomeScreen(),
);
```

Reading an extension:

```dart
final semantic = Theme.of(context).extension<AppSemanticColors>()!;
Text('Saved', style: TextStyle(color: semantic.success));
```

`ColorScheme.fromSeed` is not decoration — it derives tonal palettes whose on-colour pairs already meet contrast. Overriding individual slots by hand is how the 3:1 body text gets in. If a slot is wrong, change the seed, or supply a full scheme from the Material Theme Builder.

## Typography

```dart
// lib/theme/app_typography.dart
import 'package:flutter/material.dart';

class AppTypography {
  AppTypography._();

  static const display = 'ClashDisplay';
  static const body = 'Satoshi';

  static TextTheme textTheme(ColorScheme scheme) {
    final onSurface = scheme.onSurface;
    return TextTheme(
      displaySmall: TextStyle(
        fontFamily: display, fontSize: 36, height: 1.15,
        fontWeight: FontWeight.w600, letterSpacing: -0.5, color: onSurface,
      ),
      headlineMedium: TextStyle(
        fontFamily: display, fontSize: 28, height: 1.2,
        fontWeight: FontWeight.w600, color: onSurface,
      ),
      titleMedium: TextStyle(
        fontFamily: body, fontSize: 17, height: 1.3,
        fontWeight: FontWeight.w600, color: onSurface,
      ),
      bodyLarge: TextStyle(
        fontFamily: body, fontSize: 16, height: 1.5, color: onSurface,
      ),
      bodyMedium: TextStyle(
        fontFamily: body, fontSize: 14, height: 1.45,
        color: scheme.onSurfaceVariant,
      ),
      labelLarge: TextStyle(
        fontFamily: body, fontSize: 14, height: 1.2,
        fontWeight: FontWeight.w600, letterSpacing: 0.1, color: onSurface,
      ),
    );
  }
}
```

Register the font licence so `showLicensePage` tells the truth:

```dart
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  LicenseRegistry.addLicense(() async* {
    final license = await rootBundle.loadString('assets/fonts/OFL.txt');
    yield LicenseEntryWithLineBreaks(const <String>['Satoshi'], license);
  });
  runApp(const MyApp());
}
```

## Flame

```dart
import 'package:flame/game.dart';
import 'package:flame/components.dart';
import 'package:flame/sprite.dart';
import 'package:flame_audio/flame_audio.dart';

class MyGame extends FlameGame {
  @override
  Future<void> onLoad() async {
    // Preload everything here. A first-use load mid-gameplay is a frame drop
    // exactly when the player is paying attention.
    await images.loadAll(<String>[
      'ui/panel.png',
      'ui/button.png',
      'sprites/player.png',
    ]);
    await FlameAudio.audioCache.loadAll(<String>[
      'sfx/click.ogg',
      'sfx/win.ogg',
    ]);

    final sheet = SpriteSheet(
      image: images.fromCache('sprites/player.png'),
      srcSize: Vector2.all(32),
    );

    add(
      SpriteAnimationComponent(
        animation: sheet.createAnimation(row: 0, stepTime: 0.08, to: 6),
        size: Vector2.all(64),
        position: size / 2,
        anchor: Anchor.center,
      ),
    );
  }
}
```

Flame reads from `assets/images/` and `assets/audio/` by default, so `images.load('ui/panel.png')` resolves `assets/images/ui/panel.png`. Both directories still need pubspec entries — including every subdirectory.

TexturePacker atlas:

```dart
import 'package:flame/sprite.dart';
import 'package:flutter/services.dart' show rootBundle;

final atlas = await fromJSONString(
  await rootBundle.loadString('assets/images/ui.json'),
  images.fromCache('ui.png'),
);
final button = atlas.getSprite('button_blue.png');
```

One atlas per screen keeps the draw calls batched; a directory of loose sprites does not.

SFX, once, at the event:

```dart
FlameAudio.play('sfx/click.ogg', volume: 0.6);
```

Looping music belongs on `FlameAudio.bgm` (which handles lifecycle pause/resume), not on a second `play` call.

## flutter_gen

```yaml
dev_dependencies:
  build_runner: ^2.4.9
  flutter_gen_runner: ^5.4.0

flutter_gen:
  output: lib/gen/
  integrations:
    flutter_svg: true
    rive: true
    lottie: true
```

```bash
dart run build_runner build --delete-conflicting-outputs
```

```dart
import 'package:my_app/gen/assets.gen.dart';

Assets.images.hero.image(width: 160);
Assets.illustrations.emptyBox.svg(width: 220);
```

A typo becomes a compile error instead of a grey box in production. Re-run the generator whenever assets change, and commit the generated file so CI does not need the step.

## Bundle size

```bash
flutter build apk --release --split-per-abi     # ~⅓ the size per ABI
flutter build appbundle --release               # Play splits this for you
flutter build apk --release --analyze-size      # where the bytes actually went
```

`--analyze-size` writes a JSON you can open in DevTools' app-size tool. Run it before and after the revamp; the delta is a required line in the Step 8 report, and it is the number that catches a 12 MB illustration set nobody noticed.

Budget: assets under **30 MB**. Above that, either cut, or defer:

```yaml
# pubspec.yaml — Android deferred components
flutter:
  deferred-components:
    - name: premiumAssets
      assets:
        - assets/illustrations/premium/
```

```dart
import 'premium_gallery.dart' deferred as premium;

await premium.loadLibrary();
```

Cheaper wins first, in this order: WebP instead of PNG, `.vec` instead of SVG, one atlas instead of loose sprites, mono OGG instead of stereo WAV, and deleting the pack files you downloaded but never used — `scan_project.py`'s orphan list is exactly that.
