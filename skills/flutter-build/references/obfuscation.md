# Obfuscation and debug symbols

## What `--obfuscate` does

It renames Dart classes, methods, and fields in the AOT snapshot, and writes the mapping to the directory given by `--split-debug-info`. The two flags are inseparable: `--obfuscate` without `--split-debug-info` is a build error, and the mapping is the only way back.

```bash
flutter build appbundle --release --obfuscate --split-debug-info=build/debug-info
```

Benefit: makes reverse-engineering harder and shrinks the binary slightly. It is **not** a security control — anything the app can decrypt at runtime, an attacker can too. Do not let it justify shipping secrets in the app.

## The retention rule

> **Delete the debug-info for a version still live on Play and every crash report from that version becomes permanently unreadable.**

There is no recovery: the mapping exists only in that directory, and rebuilding the same source does not reproduce it.

Therefore:

- Save it per version code — `build/release/debug-info-<versionCode>/` — not to one shared path that each build overwrites.
- Keep it for as long as *any* user might still be on that version. In practice: every version ever rolled out to a public track, indefinitely. These directories are small.
- `build/` is gitignored in a normal Flutter project, so this is **not backed up by default**. Say so explicitly, and treat it like the keystore backup: somewhere off the build machine.

## Reading an obfuscated crash

Given a stack trace from Play Console or Crashlytics:

```bash
flutter symbolize -i <stack_trace.txt> -d build/release/debug-info-8/app.android-arm64.symbols
```

The symbols file must be the **same architecture** as the crashing device and the **same version code** as the build. A mismatched file produces plausible-looking nonsense rather than an error, so check the version code first.

For Crashlytics, upload the symbols at release time instead — otherwise the console shows the obfuscated names and nobody notices until an incident:

```bash
firebase crashlytics:symbols:upload --app <app-id> build/release/debug-info-8
```

## What obfuscation breaks

Rare, but the failures are confusing because they only appear in release builds:

| Pattern | Why it breaks |
|---------|---------------|
| `runtimeType.toString()` used as a key or compared against a literal | The name becomes a short mangled string |
| Type name-based service location or DI registration | Same |
| `enum.toString()` persisted or sent to a server | The stored value stops matching after a rebuild |
| Reflection-ish plugin code keyed on class names | Same |

`json_serializable`, `freezed`, and other codegen packages are safe — they generate explicit code, not name lookups.

**Isolating it:** if a release build misbehaves and a debug build does not, rebuild with `--release` but no `--obfuscate`. If the bug disappears, it is one of the patterns above. Do not fix it by disabling obfuscation permanently without telling the user what the real cause was.

## When to skip obfuscation

- The first release of an app with no crash-reporting set up — obfuscated traces you cannot symbolize are worse than readable ones.
- Internal-testing builds, where debugging speed matters more.

Turn it on for anything reaching open testing or production, together with somewhere durable to keep the symbols.
