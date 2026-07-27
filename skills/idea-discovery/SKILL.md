---
name: idea-discovery
description: "Research market gaps across Google Play, Google Trends, Reddit, and app store reviews to discover and validate a single high-potential app idea. Outputs 1 validated idea with full evidence backing. Don't use for web/SaaS ideas without app store focus, general brainstorms without validation, or competitive analysis of an already-chosen idea (use idea-validator instead)."
license: MIT
effort: max
metadata:
  version: 2.0.0
  author: Luong NGUYEN <luongnv89@gmail.com>
  architecture: "Parallel research subagents (keyword-researcher + pain-point-miner) → synthesis agent (idea-synthesizer) → final idea.md output"
---

# Idea Discovery

Find untapped app opportunities by analyzing keyword gaps, trend data, user pain points, and competitive weaknesses — then synthesize into 1 concrete, evidence-backed app idea.

## Core principle

> **Every number in the output must come from a lookup performed in this session.** Result counts, ratings, review volumes, complaint frequencies, search interest — each one is either something you fetched and can link to, or it does not appear. "No data found" is a valid finding; an invented figure is not.

The output of this skill reads like research. That is exactly why a plausible-sounding fabricated statistic is more damaging here than anywhere else: the user will build on it. Prior knowledge about a market is for **choosing what to search for**, never for filling in a cell in the opportunity matrix.

Two things follow:

- Every claim in `idea.md` carries a link or a named source next to it. A claim that cannot be sourced gets deleted, not softened.
- The scores below are **structured judgement, not measurement**. Say so when presenting them. Summing five 1-10 opinions into "38/50" does not make it a measurement, and precision implied by a total out of 50 should not be read as accuracy.

## When to Use

Trigger this skill when the user asks to:
- Discover app ideas worth building
- Find market gaps on Google Play or App Store
- Research what people need but can't find
- Generate a validated app concept from scratch
- Explore niche opportunities in mobile apps

Do not trigger for:
- Validating an idea the user already has (use `idea-validator`)
- General startup brainstorming without app platform focus
- Web/SaaS product ideas (this skill is app-store-centric)
- Writing a PRD or tasks from an existing idea

## Prerequisites

- Internet access for web searches (Google Play, Google Trends, Reddit, App Store)
- (Optional) AppBrain, Sensor Tower, or AppTweak account for Phase 4 — skill degrades gracefully if unavailable
- `ARGUMENTS` is optional. If provided (e.g., a category like "fitness" or "education"), the skill narrows research scope to that area. If empty, research is broad.

## Workflow

```
Phase 1 ─────────────────────────────────────────────────────────────
  Start parallel research agents:
  ├── keyword-researcher  → Google Play keyword scan + Google Trends
  └── pain-point-miner    → Reddit pain points + 1-3★ app reviews
Phase 2 ─────────────────────────────────────────────────────────────
  (Optional) ASO depth check: AppBrain / Sensor Tower
Phase 3 ─────────────────────────────────────────────────────────────
  Synthesize findings → score opportunities → pick 1 best idea
Phase 4 ─────────────────────────────────────────────────────────────
  Write idea.md with full evidence, audience, MVP, and risks
```

### Phase 1: Parallel Research (load subagents)

Launch these subagents concurrently (both can run at the same time):

**Agent A — keyword-researcher** (file: `agents/keyword-researcher.md`)
- Scans Google Play with seed keywords from `references/seed-keywords.md`
- Checks: result count, app quality, ratings, last update recency
- Cross-references with Google Trends for rising queries
- Returns: keyword opportunity map (high search volume × low competition)

**Agent B — pain-point-miner** (file: `agents/pain-point-miner.md`)
- Searches Reddit communities for "I wish there was an app", "Looking for an app", "Can't find an app"
- Analyzes 1-3★ reviews of popular apps in the space
- Returns: clustered pain points with frequency estimates

**How to launch subagents:**
1. Read the agent's `.md` file to understand its input/output contract
2. Launch as a `task` with the agent tool, passing context in the prompt
3. Wait for both to complete before proceeding to Phase 2

### Phase 2: (Optional) ASO Depth Check

If the user has access to AppBrain, Sensor Tower, or AppTweak:
- For top 3 keyword candidates from Phase 1, check:
  - Monthly search volume
  - Competition level (low/medium/high)
  - Which apps dominate the keyword
- If tools unavailable, skip this phase (note in output: "ASO data: unavailable")

### Phase 3: Gap Synthesis & Idea Selection

Read `agents/idea-synthesizer.md` and run it with both research outputs as input. (The skill ships this agent; earlier versions listed it as a reference but then described doing the synthesis inline, so it never ran.)

1. Collect outputs from both research agents
2. Create an **opportunity matrix** with rows for each candidate idea:
   - Keyword demand (low/medium/high)
   - Trend direction (rising/stable/declining)
   - Pain point intensity (how many people complain)
   - Competitive weakness (how weak are existing solutions)
   - Feasibility (can 1 person build an MVP in 2-4 weeks?)
3. Score each candidate (1-10 per dimension, max 50)
4. Select the **single highest-scoring idea**

**Tiebreaker rules:**
- Prefer pain point intensity > keyword demand > trend direction
- If still tied, prefer the more niche-focused idea

**"Nothing worth building" is a permitted outcome.** If no candidate clears a weak bar — no real pain evidence, or every keyword is dominated by well-maintained apps — report that instead of promoting the least-bad option. A user who is told to stop has lost an hour; a user handed a manufactured opportunity loses weeks. Say what was searched, what came back, and what would need to be true for the answer to change.

### Phase 4: Write idea.md

Write `idea.md` to the current working directory with this structure:

```markdown
# Idea: [Name]

## Elevator Pitch
[One sentence]

## Problem
[What pain does this solve? Cite evidence from research]

## Target Audience
[Specific demographic. Be narrow.]

## Why Now
[Trend data, market timing]

## Competitive Landscape
[Key competitors, why they're weak]

## Opportunity Evidence
- **Keyword data:** [demand × competition]
- **Trend data:** [Google Trends evidence]
- **Pain points:** [Reddit/review evidence]
- **ASO data:** [if available]

## MVP Scope
[What can ship in 2-4 weeks? Bullet list]

## Monetization
[How does this make money?]

## Risks
[Top 3 risks]

## Research Sources
[Links to specific evidence]
```

## Output

After all phases, the skill produces:
- `idea.md` — 1 fully-described, evidence-backed app idea
- Terminal summary with:
  - The winning idea name and elevator pitch
  - Key evidence points
  - MVP estimate

## Acceptance Criteria

- [ ] Both research subagents complete successfully (or degrade gracefully)
- [ ] At least 3 candidate opportunities are evaluated
- [ ] Opportunity matrix scores are documented
- [ ] Winner is selected with clear rationale
- [ ] `idea.md` exists with all required sections
- [ ] Every claim in `idea.md` cites a research source, with a link where one exists
- [ ] No figure appears that was not retrieved during this run
- [ ] Cells with no data are labelled "no data", not estimated
- [ ] Scores are presented as judgement, not as measurement

## Edge Cases

- **No keyword gaps found:** Report the most promising keywords anyway with a note that competition is moderate. Add recommendation to niche further.
- **Reddit/Google Trends returns nothing useful:** Document which queries were tried. Proceed with keyword data only.
- **ASO tools unavailable:** Skip Phase 2 gracefully, note in output.
- **User provides ARGUMENTS (e.g., "fitness"):** Scope all research to that category. Append "ANDROID" or "MOBILE APP" to search queries where needed.
- **All candidates score low:** Do not dress up the least-bad one. Report "no viable opportunity found in this scope", list what was searched, and suggest a narrower or different category. Write `idea.md` only if the user asks for the strongest candidate anyway — and then lead with the weak-signal warning.
- **A source is unreachable (rate-limited, blocked, empty):** Name the source and the queries tried, and mark every dependent cell in the matrix as "no data". Never fill a gap with an estimate.
- **`idea.md` already exists:** Ask before overwriting — it may be the output of an earlier run the user is still working from.

## Step Completion Reports

After each phase, output a status report:

```
◆ [Phase Name] (phase N of 4)
··································································
  [Check 1]:          √ pass
  [Check 2]:          √ pass (note)
  [Check 3]:          × fail — reason
  ____________________________
  Result:             PASS | FAIL | PARTIAL
```

### Phase 1 checks:
```
◆ Parallel Research (phase 1 of 4)
··································································
  keyword-researcher:  √ pass (N keyword gaps found)
  pain-point-miner:    √ pass (N pain point clusters)
  ____________________________
  Result:             PASS
```

### Phase 3 checks:
```
◆ Gap Synthesis (phase 3 of 4)
··································································
  Candidates scored:   √ pass (N candidates)
  Winner selected:     √ pass ([Idea Name])
  Rationale clear:     √ pass
  ____________________________
  Result:             PASS
```

## Reference files

- [references/seed-keywords.md](references/seed-keywords.md) — seed keywords by category
- [agents/keyword-researcher.md](agents/keyword-researcher.md) — keyword research subagent
- [agents/pain-point-miner.md](agents/pain-point-miner.md) — pain point mining subagent
- [agents/idea-synthesizer.md](agents/idea-synthesizer.md) — synthesis and output subagent
