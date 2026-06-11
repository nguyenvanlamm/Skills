---
name: trend-ideas
description: "Fetch top 15 trending topics from Exploding Topics, brainstorm 3 ideas, validate each with idea-validator, and pick the highest-scoring idea. Not for non-English trend sources or general competitor research."
license: MIT
effort: medium
metadata:
  version: 2.0.0
  author: Luong NGUYEN <luongnv89@gmail.com>
---

# Trend Ideas

Analyze real-time trending topics from Exploding Topics and generate 3 novel business ideas that address the underlying market needs.

## Prerequisites

- Python 3.x must be installed and available in the path.
- Internet access (to fetch `explodingtopics.com/api/trends`).
- No additional Python packages required (uses only stdlib — `urllib` + `json`).
- **`idea-validator` skill** must be installed at `~/.config/opencode/skills/idea-validator/SKILL.md`. If missing, the skill will report the error and stop.

## Workflow

This skill runs fully automatically — no user approval needed between steps.

---

### Step 1: Fetch Top 15 Trending Topics

Run the fetch script:

```bash
python scripts/fetch_trends.py
```

**Expected output (stdout):** A JSON object with a `topics` array. Each topic has:
- `name` — Topic name
- `growth_pct` — 24-month growth as percentage (e.g., 3233)
- `search_volume` — Monthly search volume
- `url` — Link to the topic page
- `path` — URL path

**Edge cases handled by the script:**
- Network failure → JSON error + exit code 1
- API returns empty → JSON error + exit code 1
- Growth format: raw values (e.g., `32.33`) are multiplied by 100 for readability

---

### Step 2: Analyze Each Topic

For each of the 15 topics, determine:

| Field | Question to answer |
|-------|-------------------|
| Core Need | What fundamental need does this serve? (health, status, convenience, identity, etc.) |
| Target Audience | Demographics, psychographics, early adopters |
| Growth Drivers | Why is interest spiking now? (tech, culture, regulation, media) |
| Pain Points | What frustrates consumers in this space? |
| Existing Landscape | Current solutions and their weaknesses |

Use the **Idea Analysis Framework** in `references/idea-framework.md` for the full template.

---

### Step 3: Synthesize Patterns

1. **Cluster** the 15 topics by shared core needs
2. **Identify** which clusters have the strongest momentum (highest avg growth, largest TAM)
3. **Select** 3 opportunity spaces that combine:
   - High growth trajectory
   - Underserved or fragmented solutions
   - Feasible to execute (not capital-intensive or regulated to death)

---

### Step 4: Brainstorm 3 Ideas

For each of the 3 opportunity spaces, flesh out:

- **Name** — Short brandable name
- **Elevator Pitch** — One sentence
- **Core Need Addressed** — Which cluster's need
- **How It Works** — 2-3 sentence explanation
- **Target Audience** — Specific early adopter profile
- **Why Now** — Timeliness
- **Go-to-Market Sketch** — Channel, hook, first 90 days
- **Monetization** — Business model
- **Risk Factor** — Top risk

Template in `references/idea-framework.md`.

After brainstorming all 3, save each idea as a structured block for Step 5.

---

### Step 5: Validate Each Idea with idea-validator

For **each** of the 3 ideas produced in Step 4, run the `idea-validator` skill to get a structured evaluation and numeric score.

**Prerequisite check:** Verify `~/.config/opencode/skills/idea-validator/SKILL.md` exists. If not, report error and stop.

**Per-idea workflow:**

```
For idea N (name):
  1. Set ARGUMENTS = full idea package:
     - Name + Elevator Pitch
     - Core Need + How It Works
     - Target Audience
     - Monetization Model
     - Risk Factor

  2. Follow the idea-validator 5-phase pipeline from its SKILL.md.
     Since the idea is already fully defined in Step 4:

     Phase 1 (Clarify) — Skip user questions. Instead, immediately
     populate idea.md with the data from Step 4.

     Phase 2 (Tech Context) — Make reasonable assumptions:
       - Stack: web/mobile (choose whichever fits the idea best)
       - Timeline: 3-6 months to MVP with a small team (2-3 devs)
       - Budget: bootstrapped / pre-seed
       - Constraints: none beyond standard startup constraints

     Phase 3 (Competitive Landscape) — Run as instructed:
       Perform live web searches (at least 4-6 queries) to map
       competitors, OSS alternatives, adjacent solutions, and
       failed predecessors. Update validate.md with findings.

     Phase 4 (Critical Evaluation) — Run as instructed:
       Produce Quick Verdict (Build it / Maybe / Skip it) and
       the 4 Ratings table (each 1-10).

     Phase 5 (Improvements) — Run as instructed:
       List how to strengthen, produce enhanced version, and
       implementation roadmap.

  3. From terminal output extract the Ratings table:
     | Dimension         | Score |
     |-------------------|-------|
     | Creativity        | X/10  |
     | Feasibility       | X/10  |
     | Market Impact     | X/10  |
     | Technical Execution | X/10 |

  4. Extract Quick Verdict: Build it / Maybe / Skip it

  5. Compute composite score (0-100):
     composite = (Creativity + Feasibility + Market Impact + Technical Execution) × 2.5

  6. Record: { name, composite, verdict, creativity, feasibility, market_impact, technical_execution }
```

**Note:** idea-validator will create files (`idea.md`, `validate.md`) in its configured storage root and commit/push them. That's expected.

---

### Step 6: Select Best Idea

Compare the 3 composite scores:

1. **Primary sort:** composite score (highest wins)
2. **Tiebreaker 1:** prefer `Build it` > `Maybe` > `Skip it`
3. **Tiebreaker 2:** prefer higher Market Impact score
4. **Tiebreaker 3:** prefer higher Feasibility score

Designate the winner as **Winning Idea**.

---

### Step 7: Output Report

Produce a structured markdown report with:

```markdown
# Trend Ideas Report
*Generated: {date}*

## Top 15 Trending Topics

| # | Topic | Growth | Volume | Core Need |
|---|-------|--------|--------|-----------|
| 1 | ... | ... | ... | ... |

## 3 Ideas — Validation Scores

| Idea | Creativity | Feasibility | Market | Technical | Composite | Verdict |
|------|-----------|-------------|--------|-----------|-----------|---------|
| Idea 1 | 8/10 | 7/10 | 9/10 | 6/10 | 75/100 | Build it |
| Idea 2 | ... | ... | ... | ... | ... | ... |
| Idea 3 | ... | ... | ... | ... | ... | ... |

*Composite = (Creativity + Feasibility + Market Impact + Technical Execution) × 2.5*

## Winning Idea: {name} — {composite}/100

{Elevator pitch + rationale for why this idea scores highest}

{Full idea detail from Step 4}

### Validation Summary
{Quick Verdict + Top Strengths + Top Concerns from idea-validator output}
```

## Expected Output

After a full run, the agent produces a structured markdown report containing:
1. **Top 15 topics table** with growth, volume, and core need for each
2. **3 fully-fleshed ideas** following the idea template
3. **Validation scores** for each idea (4 sub-dimensions + composite 0-100)
4. **Winning idea** — the highest-scoring idea with full detail and validation summary

## Acceptance Criteria

A run passes when **all** of the following are true:

- [ ] `scripts/fetch_trends.py` runs without error and returns 15 topics (or fewer if the source has fewer)
- [ ] Each of the 15 topics has a clear "Core Need" identified
- [ ] 3 ideas are presented, each with elevator pitch, target audience, go-to-market sketch, monetization, and risk
- [ ] Each of the 3 ideas has been validated via `idea-validator` with all 4 ratings extracted
- [ ] Composite scores are computed correctly: (C + F + M + T) × 2.5
- [ ] Winning idea is selected by highest composite score (with tiebreakers)
- [ ] Ideas are grounded in the trend data (not generic startup advice)
- [ ] Report is output as valid markdown

## Edge Cases

- **Script fails to fetch:** Use `webfetch` tool on `https://explodingtopics.com` (text format) as fallback; parse topics manually from the text output
- **Only N < 15 topics available:** Use all available topics; note the limitation in the report
- **All topics cluster into one need:** Still generate 3 distinct ideas targeting different sub-segments or angles within that need
- **Growth values are zero/negative:** Include them but note they may be declining trends; prioritize positive-growth topics for idea generation
- **idea-validator not installed:** Report error: "idea-validator skill required at ~/.config/opencode/skills/idea-validator/". Stop and do not proceed.
- **idea-validator cannot parse ARGUMENTS:** Fall back to pasting the idea description manually when prompted by idea-validator's Phase 1
- **idea-validator verdict is "Skip it" for all 3 ideas:** Still pick the highest-scoring one, but note the risk prominently in the final report
- **Composite scores tie:** Apply tiebreakers in order: Verdict > Market Impact > Feasibility. If still tied, pick arbitrarily and note it.
