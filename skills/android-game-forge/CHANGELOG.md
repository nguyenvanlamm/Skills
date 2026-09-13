# Changelog

## v3.1.0 — 2026-09-13

### Fixed
- `resolve-versions.sh`: `STALE=1` was set inside `$(...)` and lost with the subshell, so the "offline fallback used" warning could never appear even when every version came from the pins. Now tracked through a marker file and the warning names which coordinates fell back.
- `check.sh` on macOS: `declare -A` needs bash 4 (macOS ships 3.2) and `stat -c %Y` is GNU-only — the script died with a syntax error, or treated every APK as STALE. Now checks the bash version with a clear message and uses a GNU/BSD `stat` fallback; `--no-build` is accepted in any argument position.
- `resolve-versions.sh`: `sort -V` (GNU) replaced with a numeric field sort that also works on BSD `sort`.

### Verified
- `check-contrast.sh` against all four locked palettes: 17/17 tokens, 14/14 pairs ≥ 4.5:1 each; a one-digit drift in `primary` is detected and named.
- Offline simulation of `resolve-versions.sh` produces the pinned TOML **and** the warning.

### Breaking Changes
- None.

## v3.0.0
- Measured contrast gate, mandatory bundled fonts, canvas art direction, build-twice rule.
