# Project scaffold

## What to generate

```
lib/
  main.dart              entry point only
  app.dart               MaterialApp: theme, routing
  config/
    theme.dart
    routes.dart
  core/
    constants/
    utils/
    widgets/
  features/              one directory per feature, added as features are built
test/
  widget_test.dart
```

Keep it this small. A scaffold's job is to make the first real file's location obvious, not to anticipate the architecture. Do not add state management, dependency injection, networking, or a `.env` loader — those are the app author's decisions, and an unused pattern is harder to remove than to add.

Empty directories are not tracked by git. Either leave `features/` out until there is a feature, or add a `.gitkeep`; do not generate an `example/` feature that the user then has to delete.

## Files

Substitute real values when writing these. A shell variable inside a Dart string literal (`title: '$PROJECT_NAME'`) ships as the literal text `$PROJECT_NAME` — it is not interpolated by anything.

**`lib/main.dart`**

```dart
import 'package:flutter/material.dart';
import 'app.dart';

void main() {
  runApp(const App());
}
```

`WidgetsFlutterBinding.ensureInitialized()` belongs here only once something before `runApp` needs it (plugins, Firebase, preferences). Adding it pre-emptively is cargo cult.

**`lib/app.dart`**

```dart
import 'package:flutter/material.dart';
import 'config/routes.dart';
import 'config/theme.dart';

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Task Flow',            // the human-readable app name
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      initialRoute: AppRoutes.home,
      onGenerateRoute: AppRoutes.onGenerateRoute,
    );
  }
}
```

`title` is what Android shows in the task switcher. It should match the listing name — `flutter-store-compliance` flags a mismatch between the store listing and `android:label` as misleading metadata.

**`lib/config/theme.dart`**

```dart
import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData get light => ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.indigo,
        brightness: Brightness.light,
      );

  static ThemeData get dark => ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.indigo,
        brightness: Brightness.dark,
      );
}
```

**`lib/config/routes.dart`**

```dart
import 'package:flutter/material.dart';

class AppRoutes {
  static const String home = '/';

  static Route<dynamic> onGenerateRoute(RouteSettings settings) {
    switch (settings.name) {
      case home:
        return MaterialPageRoute(builder: (_) => const HomeScreen());
      default:
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            body: Center(child: Text('No route defined for ${settings.name}')),
          ),
        );
    }
  }
}
```

The home route must point at a real widget, not `Placeholder()`. `flutter run` on a fresh scaffold should show something intentional — the first thing the user sees should not look broken. A minimal `HomeScreen` with the app name and an empty state is enough.

**`test/widget_test.dart`** — replace the generated counter test, which references the template's widgets and fails after they are removed:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:task_flow/app.dart';

void main() {
  testWidgets('app builds', (tester) async {
    await tester.pumpWidget(const App());
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
```

The import path uses the pubspec `name`, which is `project_name` — not the directory, if they differ.

## After writing

```bash
flutter analyze     # must be clean
flutter test        # must pass
```

A scaffold that does not analyse clean is worse than no scaffold: it teaches the user that analyzer output is noise. Fix it before reporting.
