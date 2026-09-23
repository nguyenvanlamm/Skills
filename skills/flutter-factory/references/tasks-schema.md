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
      "id": "T12",                          // always the LAST task — see rule 9
      "title": "UI polish and licensed assets",
      "feature": "infra",
      "depends_on": ["T05", "T08", "T11"],  // every screen task
      "files": ["lib/theme/**", "lib/widgets/**", "lib/features/**/presentation/**", "assets/**", "pubspec.yaml"],
      "skill": "flutter-ui-revamp",
      "steps": [
        "flutter-ui-revamp with style/seed/keep taken from artifacts/design/design-system.md (never ask the user again)",
        "merge its ui-revamp/* branch back, re-run verify-gate --no-test",
        "copy .revamp/report.md + audit.md to artifacts/implementation/evidence/"
      ],
      "verify": "flutter analyze && flutter build apk --debug",
      "parallel_safe": false,
      "status": "pending"
    }
  ]
}
```

## Rules

1. **T01 is always the scaffold.** Nothing else may run first; its `verify`
   is `flutter analyze`. It ends by re-running `pipeline-state.sh init
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
9. **The last task is always UI polish** (`skill: flutter-ui-revamp`,
   `feature: infra`, `parallel_safe: false`), depending on every screen
   task. It runs on a working app with a clean tree — which is exactly the
   state after the previous task's commit — and never before the screens
   exist. `style`, `seed` and `keep` come from the approved
   `design-system.md`; the skill's own "ask the user" steps are answered
   from that artifact. Its `ui-revamp/*` branch is merged back and the gate
   re-run before the task is marked done. If the skill is missing → inline
   fallback (theme tokens + empty/loading states by hand), logged as
   `fallbacks.flutter-ui-revamp: inline`.

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
