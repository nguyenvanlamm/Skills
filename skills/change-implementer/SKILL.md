---
name: change-implementer
description: "Implement a requested change from a natural-language instruction. Analyzes the request, inspects the existing code, generates a task-specific mini-prompt, implements, verifies, and reports. Use when the user asks to change, fix, add, remove, or adjust something in an existing project. Don't use for greenfield projects, planning-only requests, or code review without changes."
license: MIT
effort: medium
metadata:
  version: 1.1.0
  author: "Nguyen Van Lam"
---

# Change Implementer

Implement requested changes from natural-language user instructions.

Every change request MUST be transformed into a task-specific mini-prompt before it is implemented. The mini-prompt is internal — do not show it unless the user asks.

## Flow

Always follow this exact flow:

```
Natural Request → Analyze → Generate Mini-Prompt → Implement → Verify → Result
```

1. Receive natural-language change request.
2. Analyze the request and understand the intended result.
3. Inspect the existing project/code when necessary.
4. Generate a concise mini-prompt specifically for this task.
5. Use the mini-prompt as the implementation instruction.
6. Implement the requested change.
7. Verify the implementation.
8. Return the result.

Do not skip or reorder steps. Do not implement before Analyze and Mini-Prompt are done.

---

## 1. Analyze

Determine:

- What the user wants to change.
- The expected behavior/result.
- Which part of the project is affected (files, modules, components).
- Existing implementation relevant to the request — read it, do not guess.
- Constraints that must be preserved (public API, existing tests, conventions, dependencies).

Use search/read tools to locate the affected code. Check for project rules files (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`) and existing verification commands (`package.json` scripts, `Makefile`, CI config).

If the request is ambiguous after inspecting the codebase, ask ONE focused clarifying question before continuing. Otherwise proceed.

---

## 2. Generate Mini-Prompt

Create a small, task-specific prompt from the analysis. Include only what is necessary for implementation.

Format:

```
### Task
What needs to be changed.

### Context
Relevant facts discovered from the existing project (file paths, functions, patterns, conventions).

### Expected Result
What the final behavior should be.

### Constraints
What must not be broken or changed.

### Implementation
The concrete approach: which files to touch, what to add/modify, in what order.
```

Rules:

- The mini-prompt is dynamically generated for each request. Never reuse a generic prompt.
- Reference concrete paths and symbols from the codebase, not abstractions.
- Keep it short — this is an execution instruction, not documentation.
- Do not output it to the user unless explicitly requested.

See `references/mini-prompt-examples.md` for worked examples (bug fix, UI, CLI feature, removal) and anti-patterns.

---

## 3. Implement

Implement exactly what the mini-prompt specifies.

Rules:

- Modify the existing project rather than creating unnecessary replacements.
- Reuse existing architecture, utilities, and patterns.
- Keep changes focused on the requested task.
- Do not modify unrelated functionality.
- Follow the project's existing coding conventions (style, naming, imports, error handling).
- Do not introduce new dependencies unless the task cannot be done without them; if one is needed, verify the project does not already have an equivalent.
- Preserve existing behavior outside the requested scope.
- Do not add or remove comments unless asked.
- Prefer editing files over rewriting them.

If the project has test infrastructure and the change is a bug fix, write a failing test first when practical, then make it pass.

---

## 4. Verify

After implementation, verify the change works using the most appropriate check available in the project:

| Check | When |
|---|---|
| Tests | Test suite exists and covers the area, or a new test was written |
| Type check | Typed language / `tsc`, `mypy`, `dart analyze`, etc. |
| Lint | Linter configured in project |
| Build | Compiled project or bundler present |
| Runtime check | Script / CLI / server — run it and exercise the changed path |
| Command execution | Any project-specific verification command from rules files |

For UI changes, verify the affected behavior and check for obvious regressions in adjacent UI.

Run the narrowest check first (single test file / package), then widen if the change touches shared code. See `references/verification.md` for stack detection, commands per stack, and runtime checks when no test suite exists.

If verification fails:

1. Analyze the error.
2. Fix the implementation.
3. Verify again.

Never report success when verification has clearly failed. If no verification is possible, say so explicitly in Notes.

If a failure is pre-existing and unrelated to the change, do not fix it silently — report it in Notes.

---

## 5. Result

Return a concise result:

```
### Changed
What was implemented (files touched, behavior added/modified).

### Verification
What was checked and the outcome (command + pass/fail).

### Notes
Remaining issues, limitations, or follow-ups. "None" if clean.
```

Do not include the internal mini-prompt unless the user asks for it.

---

## Core Rule

The user's request describes **WHAT** should change.
The skill determines **HOW** to implement it.

```
Natural Request → Analyze → Mini-Prompt → Implement → Verify → Result
```
