# Reviewer prompt template

Reviewers are stateless and see none of the orchestrator's context. The
prompt below is the **entire** briefing. Fill every `{{…}}`; paste the
checklist block from `review-checklists.md`; do not add the drafting
reasoning, chat history, or earlier reviews' Summary/Nits.

For `subagent` backend: `run_subagent` with `profile: subagent_explore`,
`is_background: false` (or `true` for panel members, then `read_subagent`
each). For `opencode` / `herdr`: same text as the prompt.

## What the reviewer may and may not see

| Given | Withheld |
|-------|----------|
| Stage artifacts (paths) | Orchestrator's drafting reasoning |
| `constitution.md`, `decisions/*.md` | Chat history with the user |
| Approved upstream artifacts (as **context**) | Earlier reviews' Summary / Nits / checklist results |
| **Previous revision's Findings table** (v ≥ 2, as a regression list) | Earlier reviews' reasoning, bugfix notes |
| `verify.json` of the latest gate (test/qa) | Anything under `.pipeline/bugfix/` |

Independence means *no shared reasoning*, not *no shared facts*. The
previous Findings table is a fact about the artifact's history; passing it
in is what makes revisions converge instead of drifting.

---

```
You are an independent reviewer for stage `{{stage}}` (revision v{{n}}) of a
review-gated Flutter build pipeline. You did not write these artifacts. Your
only job is to judge them against the checklist and write one report file.
{{#if lens}}
Your lens for this panel: **{{lens}}** — weigh the checklist lines about
{{lens_focus}} most heavily; still answer every line.
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
- Project source: {{project_dir}}  (stage qa only — read lib/, test/, pubspec.yaml, android/app/build.gradle*)
- Latest verify report: {{verify_json_path}}  — the ONLY acceptable evidence that analyze/test/build passed
{{/if}}
{{#if previous_findings}}
- Previous findings (regression list, from v{{n_minus_1}}):
{{previous_findings_table}}
{{/if}}

Do NOT read anything else under .pipeline/reviews/ or .pipeline/bugfix/.

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
quote the file:line, the command output, or the verify.json step that
proves it. A `pass` on an [E] line without evidence is `fail`.

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
<every checklist line with pass / fail / n.a.; [E] passes include evidence>

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

| Stage | Lenses (`lens` → `lens_focus`) |
|-------|-------------------------------|
| `qa` | `security` → secrets, storage, input validation, network · `correctness` → bugs, states, tests, architecture fidelity |
| `architecture` | `feasibility` → dependencies, SDK pins, buildability · `constitution-fit` → decisions vs constitution/PRD, over-engineering |
| `design` | `usability` → flows, states, DMMT · `consistency` → tokens, a11y, copy |

Merge into `<stage>-vN.md`: verdict = **strictest** across members
(BLOCK > ESCALATE > REVISE > APPROVE); Findings = union, de-duplicated by
`Where`+`Finding`, re-numbered continuing from the previous revision;
Regression = a finding is `resolved` only if **every** member says so.
Header line `Panel: security, correctness` after the verdict. The merged
file is what the bugfix loop and the report read; member files stay for
audit.

## Orchestrator-side handling

1. **Wait with a timeout.** `review_timeout_min` (default 15). `subagent`
   foreground: the tool blocks — no timer needed. `opencode`: wrap in
   `timeout <min>m`. `herdr`: `wait` with the same limit. Timed out or
   returned without a file → re-run **once**; still nothing → fall back to
   `subagent` for this and later reviews, `set reviewer_backend subagent`,
   log the reason.
2. **Validate, don't parse by hand:**
   `bash scripts/review-verdict.sh .pipeline/reviews/<stage>-vN.md`
   prints the verdict and counts on stdout, exit 0. Exit 1 = malformed
   (missing verdict, REVISE/BLOCK with no findings, APPROVE with
   major/critical, bad finding ids, unresolved regression not in Findings)
   → re-run once with the note *"Your previous report was rejected by the
   validator: <reason>"* (allowed: it is about format, not content). Second
   malformed report → ESCALATE.
3. `pipeline-state.sh log "<stage>-v<n> <VERDICT>: <critical>/<major>/<minor> findings"`.
4. On REVISE, the next generator pass receives the **Findings table only**
   as its requirements list, together with the original stage inputs. The
   next reviewer (v n+1) receives the same table as `previous_findings`.
5. Same-model caveat: with `reviewer_backend: subagent` the reviewer shares
   the session model. Independence comes from context isolation and, for
   `panel_stages`, from lens diversity — never leak the draft reasoning
   into the prompt.
