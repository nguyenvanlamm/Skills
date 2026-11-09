import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:game/ui/sfx.dart';

/// Records what would have been played.
class RecordingSound implements SoundSink {
  RecordingSound([List<String>? log]) : played = log ?? [];

  final List<String> played;

  @override
  void play(String id) => played.add(id);
}

/// Pumps [child] and returns a context below it.
Future<BuildContext> contextUnder(WidgetTester tester, Widget Function(Widget leaf) wrap) async {
  late BuildContext ctx;
  await tester.pumpWidget(
    wrap(
      Builder(
        builder: (c) {
          ctx = c;
          return const SizedBox();
        },
      ),
    ),
  );
  return ctx;
}

void main() {
  test('every sound has its file and volume, the generator makes exactly these, and the folder is bundled', () {
    final script = File('tool/gen_sfx.py').readAsStringSync();
    final made = RegExp(r"^    '(\w+)': \w+,$", multiLine: true).allMatches(script).map((m) => m.group(1)).toList();
    expect(made, Sfx.ids, reason: 'SOUNDS in tool/gen_sfx.py and Sfx.ids list the same sounds, in order');
    for (final id in Sfx.ids) {
      expect(File('assets/audio/$id.m4a').existsSync(), isTrue, reason: '$id: run python3 tool/gen_sfx.py');
      expect(Sfx.volumes[id], isNotNull, reason: id);
    }
    expect(Sfx.ids, contains('tap'), reason: 'withTapSound plays "tap"');
    expect(File('pubspec.yaml').readAsStringSync(), contains('    - assets/audio/\n'));
  });

  testWidgets('SoundScope plays only while Sound is on; without a scope nothing plays', (tester) async {
    final sound = RecordingSound();
    var on = true;
    var ctx = await contextUnder(tester, (leaf) => SoundScope(sink: sound, enabled: () => on, child: leaf));
    SoundScope.play(ctx, 'step');
    on = false;
    SoundScope.play(ctx, 'step');
    expect(sound.played, ['step']);

    ctx = await contextUnder(tester, (leaf) => leaf);
    SoundScope.play(ctx, 'step');
    expect(sound.played, ['step']);
  });

  testWidgets('withTapSound clicks before the action; a disabled control stays null and silent', (tester) async {
    final log = <String>[];
    final ctx = await contextUnder(
      tester,
      (leaf) => SoundScope(sink: RecordingSound(log), enabled: () => true, child: leaf),
    );
    expect(withTapSound(ctx, null), isNull);
    withTapSound(ctx, () => log.add('action'))!();
    expect(log, ['tap', 'action']);
  });
}
