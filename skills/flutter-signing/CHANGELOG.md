# Changelog

## v2.1.0 — 2026-09-13

### Fixed
- **Keystore generation could not succeed as written.** Step 4 piped `store\nkey\n` into `keytool -genkeypair`, but keytool prompts *store, re-enter store, key, re-enter key* — the second line answered the wrong prompt and keytool aborted with "passwords don't match". Replaced by `-storepass:env` / `-keypass:env`, which also keeps passwords out of `argv` and stdin transcripts.

### Added
- `scripts/generate-keystore.sh`: password generation, PKCS12 keystore, `key.properties` (`umask 077`, `chmod 600`), `.gitignore` patterns + `git check-ignore`, leak check against git history, verification, SHA-1/SHA-256 output, and the exact list of what to store in a password manager. Refuses to overwrite an existing keystore without `--force`; with it, moves the old files to `*.bak.<ts>`.
- Input validation: keysize ≥ 2048, validity ≥ 3000 days (Play requires validity past 2033-10-22).

### Changed
- Store type PKCS12 instead of the deprecated JKS; one password for store and key.
- Step 9 verification uses `-storepass:env` reading from `key.properties`.

### Breaking Changes
- None. Projects signed with an existing JKS keystore are untouched (the script refuses to replace them).

## v2.0.0
- Fail-loud Gradle config, key-custody guidance distinguishing upload vs app-signing keys.
