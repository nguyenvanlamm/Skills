import 'package:flutter_test/flutter_test.dart';
import 'package:game/store/save_store.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_platform_interface.dart';

const key = 'game.save.v1';

/// [key] and its backup as the device stores them (SharedPreferences adds its prefix).
const deviceKey = 'flutter.$key';
const deviceBackupKey = 'flutter.$key.backup';

/// Device storage that can refuse writes, as a full disk does, or fail to read; either can recover later.
class FakeDevice extends InMemorySharedPreferencesStore {
  FakeDevice(super.data) : super.withData();

  bool refuseWrites = false;
  bool readable = true;

  /// Writes the device accepted.
  int writes = 0;

  @override
  Future<bool> setValue(String valueType, String key, Object value) async {
    if (refuseWrites) return false;
    writes++;
    return super.setValue(valueType, key, value);
  }

  @override
  Future<Map<String, Object>> getAll() async {
    if (!readable) throw StateError('device storage unavailable');
    return super.getAll();
  }

  /// What the device holds, whether or not it is [readable].
  Future<Map<String, Object>> held() => super.getAll();
}

/// The game's saved data in miniature.
class SaveData {
  SaveData(this.coins);

  factory SaveData.fromJson(Map<String, dynamic> j) => SaveData(j['coins'] as int);

  int coins;

  Map<String, dynamic> toJson() => {'coins': coins};
}

/// Starts the app on [device], as a fresh launch does.
FakeDevice launchOn(FakeDevice device) {
  SharedPreferencesStorePlatform.instance = device;
  // getInstance caches the first store; reset it so this one is used.
  SharedPreferences.resetStatic();
  return device;
}

Future<Saved<SaveData>> load([SaveStore? store]) => Saved.open(
  store ?? PrefsSaveStore(key),
  fromJson: SaveData.fromJson,
  fresh: () => SaveData(0),
  toJson: (p) => p.toJson(),
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('a write the device refuses throws, so the shop never completes an unsaved purchase', () async {
    final device = launchOn(FakeDevice({}))..refuseWrites = true;
    await expectLater(PrefsSaveStore(key).write('{}'), throwsStateError);
    await expectLater(PrefsSaveStore(key).keepAside('{}'), throwsStateError);
    expect(device.writes, 0);
  });

  test('unreadable text is kept aside and play starts fresh', () async {
    for (final bad in ['{not json', '[1, 2]', '{"coins": "many"}']) {
      final device = launchOn(FakeDevice({deviceKey: bad}));
      final saved = await load();
      expect((saved.data.coins, saved.storageFailed), (0, false), reason: bad);
      expect(await device.held(), {deviceKey: bad, deviceBackupKey: bad}, reason: bad);
      saved.data.coins = 4;
      await saved.persist();
      expect(await device.held(), {deviceKey: '{"coins":4}', deviceBackupKey: bad}, reason: 'backup kept; $bad');
    }
  });

  test('a readable save loads with no backup written, and loads back after the next save', () async {
    final device = launchOn(FakeDevice({deviceKey: '{"coins": 7}'}));
    final saved = await load();
    expect((saved.data.coins, saved.storageFailed), (7, false));
    expect(device.writes, 0);
    saved.data.coins = 9;
    await saved.persist();
    launchOn(device);
    expect((await load()).data.coins, 9);
    expect(await device.held(), {deviceKey: '{"coins":9}'});
  });

  test('a refused backup means memory mode, and the device save is never touched', () async {
    final device = launchOn(FakeDevice({deviceKey: '{not json'}))..refuseWrites = true;
    final saved = await load();
    expect((saved.data.coins, saved.storageFailed), (0, true));
    device.refuseWrites = false; // storage recovers
    saved.data.coins = 50;
    await saved.save();
    await expectLater(saved.persist(), throwsStateError);
    expect(device.writes, 0);
    expect(await device.held(), {deviceKey: '{not json'});
  });

  test('a failed read means memory mode: persist throws, save swallows, nothing is written after recovery', () async {
    final device = launchOn(FakeDevice({deviceKey: '{"coins": 7}'}))..readable = false;
    final saved = await load();
    expect((saved.data.coins, saved.storageFailed), (0, true), reason: 'play goes on from memory');
    device.readable = true;
    saved.data.coins = 3;
    await saved.save();
    await expectLater(saved.persist(), throwsStateError);
    expect(device.writes, 0);
    expect(await device.held(), {deviceKey: '{"coins": 7}'});
  });

  test('a gameplay save swallows a refused write; the shop save throws', () async {
    final device = launchOn(FakeDevice({}));
    final saved = await load();
    device.refuseWrites = true;
    saved.data.coins = 2;
    await saved.save();
    await expectLater(saved.persist(), throwsStateError);
    device.refuseWrites = false;
    await saved.save();
    expect(await device.held(), {deviceKey: '{"coins":2}'});
  });

  test('the memory store keeps the save and the text set aside, for tests and screenshots', () async {
    final store = MemorySaveStore('{not json');
    final saved = await load(store);
    expect((saved.data.coins, saved.storageFailed), (0, false));
    expect(store.backup, '{not json');
    saved.data.coins = 1;
    await saved.persist();
    expect(store.text, '{"coins":1}');
  });
}
