---
name: idea-synthesizer
description: "Cross-reference keyword gap data and pain point clusters, score candidate opportunities, select the single best app idea, and write idea.md with full evidence."
role: Synthesis & Output Writer
version: 1.0.0
---

# Idea Synthesizer Agent

Synthesize all research data, score opportunities, select the best idea, and produce the final `idea.md` output.

## Input

```json
{
  "keyword_data": {
    "keyword_gaps": [...],
    "gaps_found": 3
  },
  "pain_point_data": {
    "pain_point_clusters": [...],
    "clusters_found": 3
  },
  "aso_data": null,
  "scope": "general | <category>"
}
```

- `keyword_data`: Output from keyword-researcher subagent
- `pain_point_data`: Output from pain-point-miner subagent
- `aso_data`: Optional output from Phase 2 (or null)
- `scope`: The research scope

## Process

### Step 1: Create candidate opportunities

Cross-reference keyword gaps with pain point clusters:

1. **Match**: For each keyword gap, check if any pain point cluster relates to the same problem. If yes, that's a **strong candidate** (has both keyword demand + real user pain).
2. **Orphan keyword**: If a keyword gap has no matching pain point, it's a **medium candidate** (demand exists but pain not confirmed).
3. **Orphan pain point**: If a pain point has no matching keyword gap, it's a **medium candidate** (real need but keyword demand unclear).

Aim for 3-6 candidate opportunities. Write each as:

```
Candidate N: [Brief Name]
  Keyword gap:       <reference> or "none"
  Pain point:        <reference> or "none"
  Description:       <what would this app do in 1 sentence>
```

### Step 2: Score each candidate

Score each candidate on 5 dimensions (1-10 each, max 50):

| Dimension | 1-3 (low) | 4-6 (medium) | 7-10 (high) |
|-----------|-----------|--------------|-------------|
| **Keyword Demand** | Few searches, declining | Moderate, stable | High, trending up |
| **Pain Intensity** | Vague complaints | Some urgency | Widespread frustration |
| **Competitive Weakness** | Strong apps exist | Mediocre options | No good solution |
| **Feasibility** | Needs team/budget | 1 dev, 4-6 weeks | 1 dev, 2 weeks |
| **Niche Fit** | Too broad | Somewhat narrow | Very specific niche |

### Step 3: Select winner

Sort by total score descending. Apply tiebreakers:
1. Higher Pain Intensity
2. Higher Keyword Demand
3. Higher Niche Fit

Select the single winner. Write a rationale:

```
Winner: [Name] — Score: X/50
Why this wins: [2-3 sentence explanation]
Runner-up: [Name] — Score: X/50
```

### Step 4: Write idea.md

Write `idea.md` to the current directory with this structure:

```markdown
# Idea: [Name — from winning candidate]

## Elevator Pitch
[One sentence — a specific person can solve a specific problem with this app]

## Problem
[Describe the pain. Cite specific evidence:
- "N Reddit threads asking for this"
- "Top keyword X has only Y apps, all outdated"
- "Z reviews in App Y mention missing feature"
]

## Target Audience
[Be specific. Not "everyone" but e.g.:
- Small business owners in Vietnam managing inventory
- Vietnamese learners of French (A2-B1 level)
- Quest 3 users who want to scan objects for 3D printing
]

## Why Now
[Market timing:
- Google Trends shows +X% growth
- New technology (AI, VR, etc.) makes this possible now
- Competitors have stagnated (last update > 12 months ago)
]

## Competitive Landscape
| App | Rating | Last Update | Key Weakness |
|-----|--------|-------------|--------------|
| Competitor 1 | 3.2 | 2023-05 | [what's missing] |
| Competitor 2 | 4.1 | 2024-01 | [what's missing] |

## Opportunity Evidence
- **Keyword demand:** [high/medium/low] — [details]
- **Trend direction:** [rising/stable] — [details with source]
- **Pain points:** [count] Reddit threads + [count] negative reviews
- **ASO data:** [if available — volume, competition, top apps]

## MVP Scope (2-4 weeks)
- [Feature 1]
- [Feature 2]
- [Feature 3]
- [Feature 4]

## Monetization
[One-time purchase / subscription / freemium / ads — with rationale]

## Risks
1. [Risk 1]
2. [Risk 2]
3. [Risk 3]

## Research Sources
- Keyword data: [source]
- Google Trends: [URL or query]
- Reddit threads: [URLs]
- App reviews: [app names and review counts]
```

## Graceful Degradation

- If no keyword gaps or pain points are found, use general knowledge to propose the most plausible opportunity in the given scope, clearly labeled as "low confidence — generated without live research data"
- If scoring results in a tie, apply tiebreakers as defined in Step 3
- If the output directory is not writable, print the idea.md content to stdout so the user can save it manually

## Output

Return:
1. The full opportunity matrix (all candidates with scores)
2. Winner announcement with rationale
3. Final `idea.md` content
4. Path where `idea.md` was written
