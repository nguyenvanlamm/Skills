# Screenshots

## Play's requirements

| Property | Rule |
|----------|------|
| Count | 2 minimum, 8 maximum per device type; 4+ recommended |
| Format | JPEG or 24-bit PNG, **no alpha channel** |
| Dimensions | 320–3840 px per side |
| Aspect ratio | Max 2:1 (so 1080×1920 and 1080×2340 are both fine) |
| Content | Must show the real in-app experience |

Tablet screenshots are optional but decide whether the app surfaces well on tablets and Chromebooks — 4+ at 1080×1920 (7") or 1200×1920 (10") if the app supports large screens.

The "≤ 30% text overlay" rule sometimes cited for Play does not exist — that is a Meta Ads rule. Text overlays are allowed; they just must not misrepresent the app.

## 1. Capture from a running app (preferred)

```bash
adb devices                    # confirm exactly one target
adb shell wm size              # note the resolution
mkdir -p store-metadata/screenshots/phone
adb exec-out screencap -p > store-metadata/screenshots/phone/01-home.png
```

Drive the app to each screen worth showing, capturing between steps. On an emulator, start it first:

```bash
flutter emulators                       # list
flutter emulators --launch <id>
flutter run --release                   # release build — debug banners must not appear
```

Then verify each file:

```bash
for f in store-metadata/screenshots/phone/*.png; do
  identify -format '%f %wx%h %[channels]\n' "$f"
done
```

Strip alpha if present (`magick` on ImageMagick 7, `convert` on 6):

```bash
magick "$f" -background white -alpha remove -alpha off "$f"
```

**Check for debug artifacts before accepting a capture**: the DEBUG banner, placeholder/lorem text, an empty state with no data, a visible keyboard, a notification shade. Seed realistic data first — a screenshot of an empty list sells nothing and reads as an unfinished app.

## 2. Automate with integration_test

Worth setting up when screenshots must be regenerated per release or per locale.

```yaml
dev_dependencies:
  integration_test:
    sdk: flutter
```

```dart
// integration_test/screenshots_test.dart
IntegrationTestWidgetsFlutterBinding.ensureInitialized()
    as IntegrationTestWidgetsFlutterBinding
  ..takeScreenshot('01-home');
```

Run with a driver that writes the files out:

```bash
flutter drive --driver=test_driver/integration_test.dart \
  --target=integration_test/screenshots_test.dart --profile
```

This also gives locale coverage cheaply: run the suite once per locale with a different `--dart-define`.

## 3. Placeholders — last resort

Only when no device or emulator is available. A placeholder is **not an asset**; it is a tracked debt.

Rules:

1. It must be visibly a placeholder — the words "PLACEHOLDER — NOT THE REAL APP" on the image itself. A polished gradient card is worse than an obvious stub, because it looks submittable.
2. Record it in `store-listing.json` with `"source": "placeholder", "placeholder": true`, and add an entry to `unresolved`.
3. Say so in the report, in the blocking section, not as a footnote.

`flutter-store-compliance` reads `unresolved` and fails on it. That link is the point: it is what stops fake assets from reaching Play.

## Why this matters

Play's Deceptive Behavior policy requires all metadata — listing text, title, and screenshots — to reflect the app's actual functionality. Generic marketing art substituted for the real UI is a documented rejection reason, and rejections for misleading metadata are among the most common.

A rejection here costs a review cycle. Shipping a real screenshot of a plain screen costs nothing.
