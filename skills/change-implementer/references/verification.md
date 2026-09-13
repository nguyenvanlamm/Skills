# Verification Lookup

Pick the narrowest check that covers the change, then widen if it passes. Always check project rules files (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `Makefile`, CI config) first — they override this table.

## Detect the stack

| Signal | Stack |
|---|---|
| `package.json` | Node / TS / React / Vue |
| `pyproject.toml`, `requirements.txt`, `setup.py` | Python |
| `pubspec.yaml` | Flutter / Dart |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `build.gradle(.kts)`, `settings.gradle` | Android / JVM |
| `*.csproj`, `*.sln` | .NET |
| `Gemfile` | Ruby |
| `composer.json` | PHP |

## Commands by stack

Run scoped first (single file / package), then the full suite if the scoped run passes and the change touches shared code.

### Node / TypeScript
```
npm test -- <path>              # or: pnpm test / yarn test / npx vitest run <path> / npx jest <path>
npx tsc --noEmit                # type check
npm run lint                    # if script exists; else: npx eslint <path>
npm run build                   # if bundler present
```
Check `package.json` → `scripts` for the real names (`typecheck`, `check`, `test:unit`, etc.).

### Python
```
pytest <path>                   # or: python -m pytest
mypy <package>  /  pyright      # if configured
ruff check <path>  /  flake8    # lint
ruff format --check <path>      # formatting
```

### Flutter / Dart
```
flutter analyze
flutter test <path>
flutter build apk --debug       # only when change touches native/platform code
```

### Go
```
go build ./...
go vet ./...
go test ./<pkg>/...
```

### Rust
```
cargo check
cargo clippy -- -D warnings
cargo test <filter>
```

### Android / JVM (Gradle)
```
./gradlew :<module>:compileDebugKotlin
./gradlew :<module>:testDebugUnitTest
./gradlew :<module>:lint
```

### .NET
```
dotnet build
dotnet test <project>
```

## Runtime checks (no test suite)

| Change type | Check |
|---|---|
| CLI | Run the command with the new/changed args; check exit code and output |
| HTTP API | Start server, `curl` the endpoint, assert status + body |
| Script | Execute with representative input |
| UI (web) | Start dev server, load the affected route, exercise the changed control; check console for errors |
| UI (mobile) | `flutter run` / emulator only if analyze + widget tests are insufficient |
| Config / infra | Dry-run or validate command (`terraform validate`, `docker compose config`, `yamllint`) |

## Failure loop

```
verify fails
  → read the full error, not just the last line
  → locate the cause in the change (diff), not in unrelated code
  → fix
  → re-run the SAME command
  → then run the wider suite
```

Stop and report if the failure is pre-existing and unrelated to the change — say so explicitly in Notes, do not "fix" it silently.

## No verification possible

State it in Result → Notes:
- what was attempted (`no test suite`, `build requires credentials`, …)
- what manual step the user should run
