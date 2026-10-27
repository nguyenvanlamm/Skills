import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// Where the save's text lives between launches: device storage in the app, memory in tests and screenshots.
abstract class SaveStore {
  /// The saved text, or null on a first launch. Throws when device storage is unavailable.
  Future<String?> read();

  /// Throws when the device refuses the write, so a purchase is never completed before its grant is kept.
  Future<void> write(String text);

  /// Keeps unreadable text under a backup key, so a fresh start cannot destroy it. Throws when refused.
  Future<void> keepAside(String text);
}

/// The save in SharedPreferences under [key]; unreadable text is kept under [backupKey].
class PrefsSaveStore implements SaveStore {
  PrefsSaveStore(this.key) : backupKey = '$key.backup';

  /// Versioned and unique to the game, e.g. 'mygame.wallet.v1'; permanent once shipped.
  final String key;
  final String backupKey;

  @override
  Future<String?> read() async => (await SharedPreferences.getInstance()).getString(key);

  @override
  Future<void> write(String text) => _set(key, text);

  @override
  Future<void> keepAside(String text) => _set(backupKey, text);

  Future<void> _set(String to, String text) async {
    final prefs = await SharedPreferences.getInstance();
    if (!await prefs.setString(to, text)) throw StateError('Device storage refused to save $to.');
  }
}

/// Keeps the text in memory; for tests and screenshots, where nothing may outlive the run.
class MemorySaveStore implements SaveStore {
  MemorySaveStore([this.text]);

  /// The saved text; null until the first write.
  String? text;

  /// What [keepAside] kept.
  String? backup;

  @override
  Future<String?> read() async => text;

  @override
  Future<void> write(String text) async => this.text = text;

  @override
  Future<void> keepAside(String text) async => backup = text;
}

/// The game's saved [data] and the way it reaches the device.
///
/// When device storage fails at launch, play runs from memory ([storageFailed]) and nothing is written to the store
/// again, even if storage recovers: a fresh start must never overwrite a save the device may still hold.
class Saved<T> {
  Saved._(this.data, this._toJson, this._store);

  /// Loads the save from [store]; never throws. Unreadable text (bad JSON, or [fromJson] throws) is kept aside, then
  /// play starts [fresh]. When keeping it aside is refused, or the read throws, play runs from memory.
  static Future<Saved<T>> open<T>(
    SaveStore store, {
    required T Function(Map<String, dynamic>) fromJson,
    required T Function() fresh,
    required Map<String, dynamic> Function(T) toJson,
  }) async {
    final String? text;
    try {
      text = await store.read();
    } on Object {
      return Saved._(fresh(), toJson, null);
    }
    if (text == null) return Saved._(fresh(), toJson, store);
    try {
      return Saved._(fromJson(jsonDecode(text) as Map<String, dynamic>), toJson, store);
    } on Object {
      // Unreadable, or not the shape fromJson expects: kept aside below before play starts fresh.
    }
    try {
      await store.keepAside(text);
    } on Object {
      return Saved._(fresh(), toJson, null);
    }
    return Saved._(fresh(), toJson, store);
  }

  /// The loaded data; the game changes it in place, then calls [save] (gameplay) or the shop calls [persist].
  final T data;
  final Map<String, dynamic> Function(T) _toJson;

  /// Null when play runs from memory, so nothing can write to the device.
  final SaveStore? _store;

  /// True when device storage failed at launch: progress lives in memory only, [persist] always throws, and the shop
  /// screen pauses the consumable packs.
  bool get storageFailed => _store == null;

  /// Saves after a gameplay change. A failure keeps the change in memory; the next save writes everything again.
  Future<void> save() async {
    try {
      await persist();
    } on Object {
      // Kept in memory.
    }
  }

  /// Saves and throws when the data did not reach the device: the write was refused, or storage failed at launch.
  /// The shop awaits this before it completes a purchase, so a grant that is not kept stays uncompleted and the store
  /// delivers it again.
  Future<void> persist() async {
    final store = _store;
    if (store == null) throw StateError('Device storage is unavailable; the save lives in memory only.');
    await store.write(jsonEncode(_toJson(data)));
  }
}
