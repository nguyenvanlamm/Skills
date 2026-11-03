// integration_test/capture_test.dart — scripted play for the gameplay-to-social recorder
// (play mode `script`). Template: copy, then write the taps for each level you record.
//
// Needs `integration_test` (sdk: flutter) in dev_dependencies — ask the developer first — and
// test_driver/integration_test.dart (assets/integration_test_driver.dart). The recorder runs:
//
//   flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/capture_test.dart -d <device> --profile \
//     --dart-define=CAPTURE_MODE=true --dart-define=CAPTURE_LEVEL=10 --dart-define=CAPTURE_PLAY_MODE=script
//
// fullyLive keeps the game running in real time between taps, as on a phone.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:my_game/main_capture.dart'
    as capture; // GAME: your package name

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  testWidgets('capture level ${capture.captureLevel}', (tester) async {
    await capture.main();
    // The hold screen (CAPTURE_HOLD_MS) runs first; wait until the level is on screen.
    await tester.pump(Duration(milliseconds: capture.captureHoldMs + 600));

    // GAME: the moves for this level, paced like a good player (150–600 ms apart).
    final size = tester.view.physicalSize / tester.view.devicePixelRatio;
    Future<void> tapAt(double fx, double fy, {int afterMs = 450}) async {
      await tester.tapAt(Offset(size.width * fx, size.height * fy));
      await tester.pump(Duration(milliseconds: afterMs));
    }

    switch (capture.captureLevel) {
      case 10:
        await tapAt(0.30, 0.62);
        await tapAt(0.55, 0.58);
        await tapAt(0.72, 0.64, afterMs: 900);
      default:
        // No script for this level: let it idle so the recorder still gets its clip.
        break;
    }
    // Keep the app alive until the recorder has its clip.
    await tester.pump(const Duration(seconds: 30));
  }, timeout: const Timeout(Duration(minutes: 3)));
}
