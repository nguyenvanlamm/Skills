// Reads the machine-readable blocks of the reference files.
//
// A block is a fenced code block whose info string is `g2s-<name>`:
//
//     ```g2s-specs
//     x.post.max_weighted: 280
//     banned: đừng bỏ lỡ
//     banned: game-changer
//     ```
//
// One `key: value` per line; `#` starts a comment line. A key may repeat: every value is kept, in
// order, so lists need no separator. Scalar getters take the last value.
library;

import 'dart:io';

import 'common.dart';

class Spec {
  Spec(this.values, this.sources);

  final Map<String, List<String>> values;

  /// Which file each key came from, for error messages.
  final Map<String, String> sources;

  bool has(String key) => values.containsKey(key);

  String? str(String key) => values[key]?.last;

  List<String> list(String key) => values[key] ?? const [];

  int integer(String key, [int? fallback]) {
    final v = int.tryParse(str(key) ?? '');
    if (v != null) return v;
    if (fallback != null) return fallback;
    throw StateError('spec key "$key" missing or not an integer (references/*.md g2s blocks)');
  }

  double number(String key, [double? fallback]) {
    final v = double.tryParse(str(key) ?? '');
    if (v != null) return v;
    if (fallback != null) return fallback;
    throw StateError('spec key "$key" missing or not a number (references/*.md g2s blocks)');
  }

  /// Comma-separated value, or repeated keys, as one list.
  List<String> csv(String key) => [
        for (final v in list(key))
          for (final part in v.split(','))
            if (part.trim().isNotEmpty) part.trim(),
      ];

  /// Every key that starts with [prefix], without the prefix.
  Map<String, List<String>> section(String prefix) => {
        for (final e in values.entries)
          if (e.key.startsWith(prefix)) e.key.substring(prefix.length): e.value,
      };
}

final RegExp _fence = RegExp(r'^```g2s-([a-z0-9_-]+)\s*$');

/// Parses every `g2s-*` block of [files] (paths relative to `references/` unless absolute).
Spec loadSpec(List<String> files) {
  final values = <String, List<String>>{};
  final sources = <String, String>{};
  for (final name in files) {
    final path = name.startsWith('/') ? name : '$referencesDir/$name';
    final f = File(path);
    if (!f.existsSync()) {
      fail('reference file not found: $path');
    }
    var inBlock = false;
    for (final raw in f.readAsLinesSync()) {
      final line = raw.trimRight();
      if (!inBlock) {
        if (_fence.hasMatch(line.trim())) inBlock = true;
        continue;
      }
      if (line.trim() == '```') {
        inBlock = false;
        continue;
      }
      final t = line.trim();
      if (t.isEmpty || t.startsWith('#')) continue;
      final colon = t.indexOf(':');
      if (colon <= 0) continue;
      final key = t.substring(0, colon).trim();
      final value = t.substring(colon + 1).trim();
      values.putIfAbsent(key, () => []).add(value);
      sources[key] = name;
    }
  }
  return Spec(values, sources);
}

/// The "Updated:" date line of a reference file, if it has one (`Updated: 2026-11-03`).
String? updatedDate(String file) {
  final f = File('$referencesDir/$file');
  if (!f.existsSync()) return null;
  final m = RegExp(r'^(?:\*\*)?Updated(?:\*\*)?:\s*(?:\*\*)?\s*(\d{4}-\d{2}-\d{2})', multiLine: true)
      .firstMatch(f.readAsStringSync());
  return m?.group(1);
}
