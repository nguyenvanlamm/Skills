# Reviewer prompt template

Reviewers are stateless and see none of the orchestrator's context. The
prompt below is the **entire** briefing. Fill every `{{…}}`; paste the
checklist block from `review-checklists.md`; do not add the drafting
reasoning, chat history, or earlier reviews' Summary/Nits.

For `subagent` backend: `run_subagent` with `profile: subagent_explore`,
`is_background: false` (or `true` for panel members, then `read_subagent`
each). For `opencode` / `herdr`: same text as the prompt.

## Backends (`reviewer_backend`)

| Backend | How | Result delivery | Model diversity |
|---|---|---|---|
| `subagent` (default) | `run_subagent` profile `subagent_explore` (read-only), foreground | synchronous | none — same model as the session |
| `opencode` | `opencode run "<review prompt>"`; set up via the `opencode-runner` skill | stdout when the command exits | yes — free cloud models |
| `herdr` | spawn a pane via the `herdr-agent` skill, send the prompt, `wait` + capture | async — orchestrator waits + captures | yes — whatever the pane runs |

If the backend is not `subagent`, check it exists before the first review
(`command -v opencode`, herdr CLI/socket). Missing → fall back to
`subagent`, `pipeline-state.sh set reviewer_backend subagent`, log the
fallback. Reviewer rules are identical across backends — only the
transport differs.

## What the reviewer may and may not see

| Given | Withheld |
|-------|----------|
| Stage artifacts (paths) | Orchestrator's drafting reasoning |
| `constitution.md`, `decisions/*.md` | Chat history with the user |
| Approved upstream artifacts (as **context**) | Earlier reviews' Summary / Nits / checklist results |
| **Previous revision's Findings table** (v ≥ 2, as a regression list) | Earlier reviews' reasoning, bugfix notes |
| `verify.json` of the latest gate (test/qa) | Anything under `.pipeline/bugfix/` |
| **Evidence pack** `artifacts/<stage>/evidence/` — tool output + reports from sibling skills the orchestrator ran | The orchestrator's interpretation of that evidence |
| **Methodology files** of review skills (paths to `code-review/references/*.md`, `krug-principles.md`) | The skill tool itself — the reviewer is read-only and cannot invoke skills |

Independence means *no shared reasoning*, not *no shared facts*. The
previous Findings table is a fact about the artifact's history; passing it
in is what makes revisions converge instead of drifting.

## How review skills take part

The reviewer profile (`subagent_explore`) has no `skill` tool and no shell,
so it cannot run `code-review`, `flutter-store-compliance` or
`dont-make-me-think` itself. They still contribute, in two read-only ways:

1. **Evidence pack (facts).** Before the review the orchestrator runs
   `scripts/evidence-pack.sh --project <dir> --stage qa` (analyze, pub
   outdated, deps, secrets, manifest, gradle, risky Dart patterns) and, when
   the skills are installed, `code-review mode:review` (its
   `<project>/CODE_REVIEW.md` moved to `evidence/code-review-report.md`),
   `flutter-store-compliance` (its `store-metadata/compliance-report.json`
   copied to `evidence/compliance-report.json`, only `store_bound`), and for `design`
   `dont-make-me-think` on `ux.md`/`ui.md` → `evidence/dmmt-report.md`.
   Everything lands in `artifacts/<stage>/evidence/`; `index.json` lists what
   exists. Missing skill → no file, and the reviewer is told so.
2. **Methodology (method).** The orchestrator resolves the installed skill
   directories once (`skill search`) and passes the absolute paths of their
   reference files — `code-review/references/review-mode.md`,
   `code-review/references/code-smells.md`,
   `dont-make-me-think/references/krug-principles.md` — for the reviewer to
   read and apply as an extension of the checklist.

The checklist remains the **verdict contract**: skill reports are inputs to
its `[E]` lines (`→ file` hints in `review-checklists.md`), never a verdict
to copy. A finding from `code-review-report.md` becomes an `F-nn` only after
the reviewer has opened the `file:line` and confirmed it.

---

```
You are an independent reviewer for stage `{{stage}}` (revision v{{n}}) of a
review-gated Flutter build pipeline. You did not write these artifacts. Your
only job is to judge them against the checklist and write one report file.
{{#if lens}}
Your lens for this panel: **[{{lens}}]** ({{lens_focus}}). Checklist lines
tagged **[{{lens}}]** and untagged lines are yours — answer them in full.
Lines tagged with another lens may be `n.a.` unless something is obviously
wrong, in which case report it anyway.
{{/if}}

## Read (paths are absolute; read every file fully)
- Constitution: {{abs_path}}/.pipeline/constitution.md
- Decisions:    {{abs_path}}/.pipeline/decisions/*.md   (binding — an artifact that contradicts one is `critical`)
- Artifacts under review:
{{#each artifact_paths}}
  - {{this}}
{{/each}}
- Approved upstream context (do NOT review these; see Scope):
{{#each upstream_paths}}
  - {{this}}
{{/each}}
{{#if project_dir}}
- Project source: {{project_dir}}  (stages test and qa — read lib/, test/, pubspec.yaml, android/app/build.gradle*)
- Latest verify report: {{verify_json_path}}  — the ONLY acceptable evidence that analyze/test/build passed
  (`tests` = pass/skip/fail counts, `coverage.percent` = line coverage, `git_sha` = the commit it verified)
{{/if}}
{{#if evidence_dir}}
- Evidence pack: {{evidence_dir}}  (read index.json first; every file is tool output or a
  sibling-skill report — facts to cite for [E] lines, not conclusions to copy)
{{#each missing_evidence}}
  - not available: {{this}} — answer the related lines by reading the source, and say so
{{/each}}
{{/if}}
{{#if methodology_paths}}
- Methodology to apply in addition to the checklist (read fully):
{{#each methodology_paths}}
  - {{this}}
{{/each}}
{{/if}}
{{#if previous_findings}}
- Previous findings (regression list, from v{{n_minus_1}}):
{{previous_findings_table}}
{{/if}}

Do NOT read anything else under .pipeline/reviews/ or .pipeline/bugfix/.
You cannot run commands or skills; if a check needs one, cite the evidence
file that already contains its output or mark the line `fail — no evidence`.

## Scope
Only the artifacts under review are the subject. Approved upstream
artifacts are context: if one of them has a defect that makes this stage
impossible to do correctly, do not REVISE this stage for it — write the
verdict ESCALATE and name the upstream artifact and defect. Do not ask for
changes to upstream artifacts in Findings.

## Checklist
{{checklist_block}}

## Evidence
Lines marked **[E]** in the checklist may only be `pass` with evidence:
quote the file:line, the evidence-pack file and section, or the verify.json
step that proves it. A `pass` on an [E] line without evidence is `fail`.
A hit listed in the evidence pack is a *candidate*: open the source, confirm
it, then report it with the real file:line. A skill report's own severity or
verdict is not binding — apply this checklist's severity scale.

## Severity
critical = violates constitution/decision, security hole, or makes the stage
unusable downstream · major = stage does not fully do its job · minor =
quality nit. Any critical → BLOCK (if a revision cannot fix it) or REVISE;
any major → REVISE; only minors → APPROVE. ESCALATE only when you need a
business decision from the user, or for the upstream case in Scope.

## Numbering
{{#if previous_findings}}
Previous findings keep their ids. New findings start at F-{{next_id}}.
{{else}}
Findings are numbered F-01, F-02, … in order of severity (critical first).
{{/if}}

## Write exactly one file
{{abs_path}}/.pipeline/reviews/{{stage}}-v{{n}}{{#if lens}}-{{lens}}{{/if}}.md

Format (keep headings verbatim; the file is machine-validated):

## Verdict: APPROVE | REVISE | BLOCK | ESCALATE

## Summary
<2–4 sentences: what the artifact does well, what stops it advancing>
{{#if previous_findings}}

## Regression
| # | Status | Evidence |
|---|--------|----------|
| F-01 | resolved | prd.md §3.2 now lists acceptance criteria |
| F-02 | unresolved | still no offline requirement |
(one row per previous finding; `unresolved` rows must also appear in Findings)
{{/if}}

## Findings
| # | Severity | Where | Finding | Fix hint |
|---|----------|-------|---------|----------|
| F-06 | major | prd.md §3.2 | ... | ... |
(one row per failed checklist line and per unresolved regression;
`Where` = file + heading or file:line; empty table only if verdict is APPROVE)

## Checklist results
- [pass] <checklist line> — <evidence: file:line / evidence file § / verify.json step>
- [fail] <checklist line> — F-07
- [n.a.] <checklist line> — <why it does not apply>
(one bullet per checklist line, status in square brackets exactly as above;
[E] passes include evidence; every [fail] names its finding)

## Nits
<minor items that do not affect the verdict>

## Rules
- Judge the artifact, not the effort. Do not soften a REVISE into an APPROVE
  because most lines pass.
- Every `fail` must appear in Findings with a number; every finding must be
  actionable in one sentence.
- Do not fix the artifacts yourself. Do not create any other file.
- End your reply with the single line: REVIEW WRITTEN: <path>
```

---

## Panel review (`panel_stages`)

For stages listed in `config.yaml → panel_stages` (default `[qa]`), spawn
one reviewer per lens **in parallel**, each with the same prompt plus its
lens, writing `<stage>-vN-<lens>.md`:

| Stage | Lenses (`lens` → `lens_focus`) — tags match `review-checklists.md` |
|-------|-------------------------------|
| `qa` | `sec` → security & data: secrets, storage, manifest, network, dependencies · `cor` → correctness, performance, fidelity |
| `architecture` | `feas` → buildability: dependencies, SDK pins, error/offline/test seams · `fit` → decisions vs constitution/PRD, simplicity |
| `design` | `use` → flows, states, navigation, responsive, DMMT · `cons` → tokens, contrast, a11y, copy, asset licences |

Every checklist line carries its lens tag, so each member knows exactly
which lines it owns; untagged lines are answered by every member.

Merge into `<stage>-vN.md`: verdict = **strictest** across members
(BLOCK > ESCALATE > REVISE > APPROVE); Findings = union, de-duplicated by
`Where`+`Finding`, re-numbered continuing from the previous revision;
Regression = a finding is `resolved` only if **every** member says so.
Header line `Panel: security, correctness` after the verdict. Validate
each member file and the merged file (`--prev` from v2). The merged file
is what `advance`, the bugfix loop and the report read; member files stay
for audit. Lens diversity is the cheap substitute for model diversity when
the backend is `subagent`.

## Orchestrator-side handling

0. **Build the evidence pack** (stages `qa`, and `design` when
   `dont-make-me-think` is installed): run `scripts/evidence-pack.sh`, then
   the installed review skills with output redirected into
   `artifacts/<stage>/evidence/`; resolve methodology paths with `skill
   search`. Record missing skills in `fallbacks.*` and pass them as
   `missing_evidence`. Never summarise the evidence for the reviewer.
1. **Wait with a timeout.** `review_timeout_min` (default 15). `subagent`
   foreground: the tool blocks — no timer needed. `opencode`: wrap in
   `timeout <min>m`. `herdr`: `wait` with the same limit. Timed out or
   returned without a file → re-run **once**; still nothing → fall back to
   `subagent` for this and later reviews, `set reviewer_backend subagent`,
   log the reason.
2. **Validate, don't parse by hand:**
   `bash scripts/review-verdict.sh .pipeline/reviews/<stage>-vN.md --prev <previous>`
   (`--prev` from v2 on: the previous merged report, or `<stage>-v(N-1)-gate.md`
   after a human rejection) prints the verdict and counts on stdout, exit
   0. Exit 1 = malformed (missing verdict, REVISE/BLOCK with no findings,
   APPROVE with major/critical, bad or reused finding ids, a previous
   finding without exactly one Regression row, a `resolved` id still in
   Findings, unresolved regression not in Findings, Checklist results not
   in `- [status]` form, more `[fail]` lines than findings)
   → re-run once with the note *"Your previous report was rejected by the
   validator: <reason>"* (allowed: it is about format, not content). Second
   malformed report → ESCALATE. Panel: validate each member file, then the
   merged file.
3. `pipeline-state.sh log "<stage>-v<n> <VERDICT>: <critical>/<major>/<minor> findings"`.
4. On REVISE, the next generator pass receives the **Findings table only**
   as its requirements list, together with the original stage inputs. The
   next reviewer (v n+1) receives the same table as `previous_findings`.
5. Same-model caveat: with `reviewer_backend: subagent` the reviewer shares
   the session model. Independence comes from context isolation and, for
   `panel_stages`, from lens diversity — never leak the draft reasoning
   into the prompt.
