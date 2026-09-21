# Reviewer prompt template

Reviewers are stateless and see none of the orchestrator's context. The
prompt below is the **entire** briefing. Fill every `{{…}}`; paste the
checklist block from `review-checklists.md`; do not add the drafting
reasoning, chat history, or earlier review attempts.

For `subagent` backend: `run_subagent` with `profile: subagent_explore`,
`is_background: false`. For `opencode` / `herdr`: same text as the prompt.

---

```
You are an independent reviewer for stage `{{stage}}` (revision v{{n}}) of a
review-gated Flutter build pipeline. You did not write these artifacts. Your
only job is to judge them against the checklist and write one report file.

## Read (paths are absolute; read every file fully)
- Constitution: {{abs_path}}/.pipeline/constitution.md
- Decisions:    {{abs_path}}/.pipeline/decisions/*.md   (binding — an artifact that contradicts one is `critical`)
- Artifacts:
{{#each artifact_paths}}
  - {{this}}
{{/each}}
{{#if project_dir}}
- Project source: {{project_dir}}  (stage qa only — read lib/, test/, pubspec.yaml, android/app/build.gradle*)
- Latest verify report: {{abs_path}}/.pipeline/artifacts/test/verify.json
{{/if}}

Do NOT read anything under .pipeline/reviews/ or .pipeline/bugfix/ — you must
form your own view.

## Checklist
{{checklist_block}}

## Severity
critical = violates constitution/decision, security hole, or makes the stage
unusable downstream · major = stage does not fully do its job · minor =
quality nit. Any critical → BLOCK (if a revision cannot fix it) or REVISE;
any major → REVISE; only minors → APPROVE. ESCALATE only when you need a
business decision from the user that the artifacts cannot answer.

## Write exactly one file
{{abs_path}}/.pipeline/reviews/{{stage}}-v{{n}}.md

Format (keep headings verbatim):

## Verdict: APPROVE | REVISE | BLOCK | ESCALATE

## Summary
<2–4 sentences: what the artifact does well, what stops it advancing>

## Findings
| # | Severity | Where | Finding | Fix hint |
|---|----------|-------|---------|----------|
| F-01 | major | prd.md §3.2 | ... | ... |
(one row per failed checklist line; `Where` = file + heading or file:line;
empty table only if verdict is APPROVE)

## Checklist results
<every checklist line with pass / fail / n.a.>

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

## Orchestrator-side handling

1. After the reviewer returns, **read the file** — the return text is only a
   completion signal. Missing file → the review did not happen; re-run once,
   then treat as ESCALATE.
2. Parse the verdict from the first `## Verdict:` line. Anything else →
   malformed → re-run once with the note "Your previous report lacked a
   verdict line" (that note is allowed: it is about format, not content).
3. `pipeline-state.sh log "<stage>-v<n> <VERDICT>: <count> findings"`.
4. On REVISE, the next generator pass receives the **Findings table only**
   (not Summary/Nits) as its requirements list, together with the original
   stage inputs.
5. Same-model caveat: with `reviewer_backend: subagent` the reviewer shares
   the session model. Independence comes from context isolation, not model
   diversity — never leak the draft reasoning into the prompt.
