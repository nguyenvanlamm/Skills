# Release notes / run report template

Save as `.pipeline/artifacts/release/notes.md`. Fill **only** from
`verify.json` files, `state.yaml`, `events.log`, `reviews/` and `tasks.json`
— never from memory. Write in the user's language. `✅` = the command ran and
exited 0 in this run; `⚠️` = `skipped_env`; `❌` = failed and left as a
blocker.

```markdown
# <App name> v<version> — release report

Run: <started_at> → <finished_at> · pipeline flutter-factory v2.0.0
Project: `<project_dir>` · applicationId `<org>.<slug>` · tag `v<version>`

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
| test | ✅ ok | 0 | 41s | 63 tests |
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

Reviewer backend: <subagent | opencode | herdr> (<fallback note if any>)

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
  rows the script did not run.
- §3 revision counts = `revisions.<stage>` in `state.yaml`; bugfix cycles =
  `bugfix_cycles`.
- §5 lists **every** preferred skill from the pipeline table, used or not.
- If any §2 row is ❌, the release stage must not have been marked done —
  the report is then a blocker report, titled accordingly.
