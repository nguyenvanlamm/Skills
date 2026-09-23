# `tasks.json` schema

Produced at `planning`, consumed at `implementation`. `tasks-generator`
(if present) produces sprint markdown — convert its output into this JSON;
the pipeline never executes from prose.

```jsonc
{
  "version": 1,
  "project_dir": "./spendly",              // relative to repo root; created by task T01
  "tasks": [
    {
      "id": "T01",                          // unique, sortable
      "title": "Scaffold Flutter project",  // English — it becomes the commit subject
      "feature": "infra",                   // MVP feature name from idea.md, or "infra"
      "depends_on": [],                     // ids; graph must be acyclic
      "files": ["pubspec.yaml", "lib/main.dart", "android/**", "ios/**"],
      "skill": "flutter-init",              // preferred sibling skill or null
      "steps": [
        "flutter-init with project_name=spendly org=<DECISION-001> platforms=android,ios (no nested git init if the workspace is already a repo)",
        "pin compileSdk/targetSdk per architecture.md",
        "pipeline-state.sh init --project spendly (records project_dir, excludes .pipeline/ from the repo)"
      ],
      "verify": "flutter analyze",          // shell command, exit 0 = done
      "parallel_safe": false,
      "status": "pending"                   // pending | in_progress | done | blocked
    },
    {
      "id": "T04",
      "title": "Expense model + repository",
      "feature": "Add expense",
      "depends_on": ["T01"],
      "files": ["lib/features/expense/data/**", "test/features/expense/data/**"],
      "skill": null,
      "steps": ["Expense model (freezed only if JSON)", "ExpenseRepository interface + drift impl", "unit tests"],
      "verify": "flutter test test/features/expense/data",
      "parallel_safe": true,
      "status": "pending"
    },
    {
      "id": "T12",                          // last screen-affecting task — see rule 9
      "title": "UI polish and licensed assets",
      "feature": "infra",
      "depends_on": ["T05", "T08", "T11"],  // every screen task
      "files": [                            // app-shell / router paths: take them from folder-structure.md
        "lib/theme/**", "lib/widgets/**", "lib/features/**/presentation/**", "lib/features/about/**",
        "lib/main.dart", "lib/app.dart", "lib/core/router/**", "lib/l10n/**",
        "assets/**", "pubspec.yaml", "pubspec.lock", "test/**", ".gitignore"
      ],
      "skill": "flutter-ui-revamp",
      "steps": [
        "flutter-ui-revamp with project/style/seed/scope/keep from design-system.md + ux.md and every question pre-answered (sibling-contracts.md)",
        "dependency-table row + DECISION-NNN for each package it added (lucide_icons_flutter, rive, flutter_gen, …)",
        "update widget tests whose finders used the old icons (find.byIcon)",
        "copy .revamp/report.md + audit.md to artifacts/implementation/evidence/",
        "git merge --no-ff --no-commit ui-revamp/*; add .revamp/ to .gitignore (git rm -r --cached .revamp if committed); git commit -m 'feat(infra): UI polish and licensed assets [T12]'",
        "re-run verify-gate --no-test on the merge commit"
      ],
      "verify": "flutter analyze && flutter build apk --debug",  // chosen per rule 9 from release_build + env.md
      "parallel_safe": false,
      "status": "pending"
    },
    {
      "id": "T13",                          // only when config ios_release: true — see rule 10
      "title": "App Store release kit for iOS",
      "feature": "infra",
      "depends_on": ["T12"],
      "files": ["ios/**", "ios-release/**", ".gitignore"],
      "skill": "flutter-ios-release",
      "steps": [
        "ios_prep_apply.py with bundle id / team / device family / encryption from DECISION-00x and one English usage string per permission the PRD features need",
        "ios_prep_check.py --out ios-release/prep-report.json — no BLOCK"
      ],
      "verify": "python3 <flutter-ios-release>/scripts/ios_prep_check.py --project . && flutter analyze",
      "parallel_safe": false,
      "status": "pending"
    }
  ]
}
```

## Rules

1. **T01 is always the scaffold.** Nothing else may run first; its `verify`
   is `flutter analyze`. With `ios_release: true` its platforms include
   `ios` even on Linux (creating `ios/` needs no Mac). It ends by re-running `pipeline-state.sh init
   --project <dir>` (SKILL.md → Git layout).
2. **Every task has `verify`.** The reviewer rejects a plan with a task that
   cannot prove itself. Prefer scoped commands (`flutter test <dir>`) so
   failures point at the task.
3. **`files` is the contract for parallelism.** Two tasks may run in
   parallel only if both are `parallel_safe: true`, their `files` globs do not
   overlap, and neither depends on the other transitively. Shared files
   (`pubspec.yaml`, `router.dart`, `main.dart`) belong to serial tasks.
4. **Order = data flow.** models → repositories → state/providers → screens
   → platform adaptation → polish. A screen task depends on its repository
   task.
5. **Size.** ≤ ~1 day of work, ≤ ~10 files. Split anything bigger.
6. **Feature traceability.** Every MVP feature in `idea.md` appears in ≥ 1
   task's `feature`; a task whose feature is not in the PRD is a planning
   finding.
7. **Status is mirrored to state.** On completion the orchestrator sets
   `status: done` here **and** `pipeline-state.sh set task.<id> done`, and
   commits with message `feat(<feature>): <title> [<id>]`.
8. **English only in `title` and `feature`.** Both are interpolated into
   the commit message, and every commit the pipeline makes is in English
   (SKILL.md rule 8) — even when `idea.md`/`prd.md` are written in another
   language. Translate when converting `tasks-generator` output.
9. **The last screen-affecting task is always UI polish** (`skill:
   flutter-ui-revamp`, `feature: infra`, `parallel_safe: false`), depending
   on every screen task; only the iOS kit (rule 10) may follow it. It runs on a working app with a clean tree — which is exactly the
   state after the previous task's commit — and never before the screens
   exist. `style`, `seed` and `keep` come from the approved
   `design-system.md`; the skill's own "ask the user" steps are answered
   from that artifact. Its `ui-revamp/*` branch is merged back and the gate
   re-run before the task is marked done. If the skill is missing → inline
   fallback (theme tokens + empty/loading states by hand), logged as
   `fallbacks.flutter-ui-revamp: inline`.
   - **`files`** must cover everything the revamp legitimately touches:
     theme/widgets/presentation, the app shell that wires `theme:` /
     `darkTheme:` and holds `RiveNative.init()` (`lib/main.dart`,
     `lib/app.dart`), the router and an About/Credits feature when
     attribution is needed, `lib/l10n/**` (its new strings go to
     `app_en.arb`), `assets/**`, `pubspec.{yaml,lock}` and `test/**`
     (icon-based finders break after the swap). Use the real paths from
     `folder-structure.md`.
   - **`verify`** follows `release_build` and `env.md`: `apk`/`appbundle`
     with an Android SDK → `flutter analyze && flutter build apk --debug`;
     `web` → `flutter analyze && flutter build web`; `none` or no SDK →
     `flutter analyze` (the release gate then reports the build `skipped_env`).
   - The task commit is the **merge commit** of its `ui-revamp/*` branch
     (`git merge --no-ff --no-commit`, `.revamp/` added to `.gitignore` and
     untracked, then `git commit -m "feat(infra): <title> [<id>]"`); the
     skill's grouped commits stay underneath it.
10. **iOS kit task** — when `config.yaml` has `ios_release: true`, the very
    last task is `skill: flutter-ios-release`, depending on the UI-polish
    task (the app icon and display name are final by then). `files`:
    `ios/**`, `ios-release/**`, `.gitignore` — it never touches `lib/`, so it
    cannot break a screen. Inputs come from the architecture iOS decision
    (bundle id = Android `applicationId` unless decided otherwise, team id
    or "at build time", device family, encryption exemption) and from the
    PRD features (one English usage string per permission). `verify` is the
    skill's `ios_prep_check.py` (exit 0 = no BLOCK) plus `flutter analyze`.
    It prepares; it never claims an IPA — that is built on macOS later with
    `ios-release/build-ios.sh`. Skill missing → inline: set the same keys by
    hand, write `ios-release/README.md` with the Mac build steps, log
    `fallbacks.flutter-ios-release: inline`.

## Orchestrator loop

```
for task in topological order:
    discover skill (task.skill by name → capability search → inline)
    implement steps
    bash verify-gate.sh --project <project_dir> --no-test --stage implementation
    run task.verify
    both ok → commit → mark done
    fail     → fix (max 3 rounds) → still failing → status: blocked, continue
               with tasks that do not depend on it, then ESCALATE at stage end
after the last task:
    bash verify-gate.sh --project <project_dir> --no-test --stage implementation   # on the committed tree
    pipeline-state.sh advance                                                     # checks sha = HEAD, no pending task
```

With `parallel_implementation: true`, take the largest set of ready,
`parallel_safe`, pairwise-disjoint tasks. A single checkout can only have
one branch checked out, so each task gets its **own git worktree**:

```bash
git -C <project_dir> worktree add ../wt-<id> -b task/<id>     # one per task, from the working-branch HEAD
```

Give each to a `subagent_general` with constitution + architecture +
decisions + **its task object only** + the absolute worktree path. The
subagent works only inside that worktree (`flutter pub get` there first),
runs `task.verify`, and commits on `task/<id>` with the English message
`feat(<feature>): <title> [<id>]` (state it in the subagent prompt); it
never merges and never touches the main checkout. When all are done, the
orchestrator merges `task/<id>` into the working branch in id order
(`git merge --no-ff`), running `verify-gate --no-test` after each merge,
then `git worktree remove ../wt-<id>` and `git branch -d task/<id>`. A red
merge is fixed by the orchestrator, never by re-spawning the subagent with
the conflict.
