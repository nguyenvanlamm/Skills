# Release notes / run report template

Save as `.pipeline/artifacts/release/notes.md`. Fill **only** from
`verify.json` files, `state.yaml`, `events.log`, `reviews/` and `tasks.json`
— never from memory. Write in the user's language. `✅` = the command ran and
exited 0 in this run; `⚠️` = `skipped_env`; `❌` = failed and left as a
blocker.

```markdown
# <App name> v<version> — release report

Run: <started_at> → <finished_at> · pipeline flutter-factory v<metadata.version from SKILL.md>
Project: `<project_dir>` · applicationId `<org>.<slug>` · tag `v<version>` on `<git_sha from verify.json, short>`

## 1. What was built
<2–4 sentences: the product, who it is for, what the MVP does>

### MVP features (from idea.md)
| Feature | Tasks | Status |
|---------|-------|--------|
| Add expense | T04, T07 | ✅ done |
| Export CSV | T09 | ❌ blocked — see §6 |

### Deferred (Extended / Future)
- <feature> — <why deferred>

## 2. Verification (from artifacts/release/verify.json)
| Step | Status | Exit | Duration | Artifact / log |
|------|--------|------|----------|----------------|
| pub_get | ✅ ok | 0 | 4s | — |
| analyze | ✅ ok | 0 | 12s | .pipeline/artifacts/release/logs/analyze.log |
| test | ✅ ok | 0 | 41s | 63 passed · 0 skipped · 0 failed (`tests`) |
| coverage | ✅ ok | 0 | — | 81.4% (1190/1462 lines) ≥ min 80% — from artifacts/test/verify.json |
| integration | ⚠️ skipped_env | 0 | — | no device (`--integration-device` not given) |
| build apk | ✅ ok | 0 | 2m10s | build/app/outputs/flutter-apk/app-release.apk |
| secrets scan | ✅ ok | 0 | — | 0 matches |
| applicationId | ✅ ok | — | — | com.acme.spendly |

## 3. Review trail (from reviews/ and events.log)
| Stage | Revisions | Final verdict | Human gate |
|-------|-----------|---------------|------------|
| idea | 1 | APPROVE | approved |
| planning | 2 | APPROVE | approved |
| design | 1 | APPROVE | — |
| architecture | 1 | APPROVE | — |
| test | 1 | APPROVE | — |
| qa | 3 (2 bugfix cycles) | APPROVE | — |
| release | — | — | approved |

Reviewer backend: <subagent | opencode | herdr> (<fallback note if any>) · Panel stages: <qa: security, correctness>
Malformed reports re-run: <n> · Findings total: <critical>/<major>/<minor>
Overrides: <none | each `OVERRIDE advance …` line from events.log — also in §6>

## 4. Decisions
| # | Decision | Why |
|---|----------|-----|
| DECISION-001 | org = com.acme | user-owned domain |
| DECISION-002 | drift over sqflite | typed queries, migrations |

## 5. Skills
| Capability | Skill used | Or done inline because |
|------------|-----------|------------------------|
| Idea validation | idea-validator | — |
| PRD | — | prd-generator missing → inline |

## 6. Blockers and known issues
- <F-nn or task id> — <what, where, why not fixed>

## 7. Next steps
1. `flutter-signing` → upload keystore, `android/key.properties`
2. `flutter-build` → signed AAB
3. `flutter-store-metadata` → listing assets
4. `flutter-store-compliance` → policy audit
5. `flutter-publish` → Play Console upload
- <backend / iOS on macOS / deferred features as applicable>
```

## Filling rules

- Every row in §2 comes from a `steps[]` entry in `verify.json`; do not add
  rows the script did not run. Test counts come from its `tests` object;
  the coverage row may come from `artifacts/test/verify.json` (the release
  gate does not re-measure it) — say which file.
- §3 revision counts = `revisions.<stage>` in `state.yaml`; bugfix cycles =
  `bugfix_cycles`; Human gate = `gates.<stage>` (a `-gate.md` rejection
  counts as a revision).
- §5 lists **every** preferred skill from the pipeline table, used or not.
- If any §2 row is ❌, the release stage must not have been marked done —
  the report is then a blocker report, titled accordingly. (`advance`
  refuses anyway unless the user ordered an override, which §6 then lists.)
