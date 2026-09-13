# Design system & responsive reference

Read at Phase 3 (define tokens) and Phase 5 (build components). If `frontend-design` exists, use it to choose the visual direction — then encode the outcome here as tokens. Screens consume tokens and components only; a screen file never contains a raw `Color(0x…)`, a raw `EdgeInsets.all(13)` or a raw `TextStyle`.

## 1. Tokens (`lib/app/theme/tokens.dart`)

```dart
abstract final class AppColors {
  static const seed = Color(0xFF2E7D6B);          // one seed → ColorScheme.fromSeed
  static const success = Color(0xFF2E7D32);
  static const warning = Color(0xFFED6C02);
  static const danger  = Color(0xFFC62828);
}

abstract final class AppSpacing {                 // 4-pt grid
  static const xs = 4.0, sm = 8.0, md = 16.0, lg = 24.0, xl = 32.0, xxl = 48.0;
}

abstract final class AppRadius {
  static const sm = 8.0, md = 12.0, lg = 20.0, pill = 999.0;
}

abstract final class AppElevation {
  static const none = 0.0, low = 1.0, mid = 3.0, high = 6.0;
}

abstract final class Breakpoints {                // Material 3 window classes
  static const compact = 600.0;                   // < 600  phone
  static const medium  = 840.0;                   // 600–840 tablet portrait / small window
  static const expanded = 1200.0;                 // 840–1200 tablet landscape / laptop
}                                                 // ≥ 1200 desktop
```

Typography: `Theme.of(context).textTheme` from Material 3 defaults, optionally with one bundled OFL font via `google_fonts` **only if** offline use is not required (it fetches at runtime on web); otherwise bundle the `.ttf` under `assets/fonts/` and declare in `pubspec.yaml`.

Theme: `ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: AppColors.seed, brightness: …), useMaterial3: true)` for light and dark, plus component themes (`filledButtonTheme`, `inputDecorationTheme`, `cardTheme`) so every default widget already matches.

## 2. Components (`lib/core/widgets/`)

| Widget | Contract |
|--------|----------|
| `AppScaffold` | Adaptive navigation (§3), title, actions, FAB slot, body max-width on desktop |
| `AppButton` | `primary / secondary / text / danger`, `loading` flag disables + shows spinner, min 44×44 tap target |
| `AppTextField` | label, hint, validator, keyboard type, prefix/suffix, error text from validator |
| `AppCard` | padding `md`, radius `md`, elevation `low`, optional onTap with ink |
| `AppDialog.confirm / .info` | static helpers returning `Future<bool?>`; destructive action uses danger color |
| `LoadingView` | centered progress + optional message; use for full-screen loading |
| `ErrorView` | icon, message, `onRetry`; renders `AppException.userMessage` |
| `EmptyView` | icon, title, hint, optional primary action |
| `AsyncValueView<T>` | `AsyncValue<T>` → `LoadingView / ErrorView / builder(data)`; empty when `data.isEmpty` via `isEmpty` callback |
| `ResponsiveBuilder` | `builder(context, WindowClass)`; wraps `LayoutBuilder` |

`AsyncValueView` is what makes "every screen has loading/error/empty" cheap — screens must use it instead of hand-rolling `.when`.

## 3. Adaptive navigation (`AppScaffold`)

| Width | Navigation | Content |
|-------|------------|---------|
| < 600 | `NavigationBar` (bottom), max 5 destinations | full width |
| 600–1200 | `NavigationRail` (labels: selected) | full width, list/detail may split ≥ 840 |
| ≥ 1200 | `NavigationRail(extended: true)` or `NavigationDrawer` permanent | body constrained to 1100 px, centered |

Implementation: one `List<AppDestination>` (icon, label, route) shared by all three; `LayoutBuilder` picks the shell. `go_router` `StatefulShellRoute.indexedStack` keeps each tab's stack.

## 4. Responsive rules

- Widths come from `LayoutBuilder` constraints (nearest container), not `MediaQuery.size` (whole window) — except for keyboard insets/safe area.
- Grids: `SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent: 360)` rather than fixed `crossAxisCount`.
- Text never fixed-width: `Flexible`/`Expanded` + `overflow: TextOverflow.ellipsis`.
- Forms cap at 480 px on wide screens (`ConstrainedBox`), centered.
- Dialogs: `Dialog` on ≥ 600, `showModalBottomSheet` on compact — wrap in `AppDialog`.
- Hover/focus states on web and desktop: `InkWell`/`FilledButton` give these for free — do not replace with `GestureDetector` on tappable areas.
- Test `AppScaffold` and each list screen at 400, 800 and 1400 px in widget tests (`tester.view.physicalSize`).

## 5. Accessibility baseline

- Every icon-only button has `tooltip`.
- Tap targets ≥ 44×44 (Material buttons already do).
- Contrast: rely on `ColorScheme.fromSeed`; custom semantic colors checked ≥ 4.5:1 against their background.
- `Semantics(label:)` on custom painted widgets and charts.
- Respect `MediaQuery.textScalerOf` — no fixed-height rows containing text.

## 6. States checklist per screen

```
[ ] loading   (first load)          → LoadingView
[ ] refresh   (has data, reloading) → RefreshIndicator / linear progress, data stays visible
[ ] error     (no data)             → ErrorView + retry
[ ] error     (has data)            → SnackBar, data stays visible
[ ] empty                           → EmptyView + primary action
[ ] success                         → data
```
