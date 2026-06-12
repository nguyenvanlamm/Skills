# Trend Ideas Skill

## Overview

Fetch top 15 trending topics from Exploding Topics, brainstorm 3 product ideas, validate each with `idea-validator`, and pick the highest-scoring idea.

## Workflow

```
Step 1: Fetch 15 trending topics from Exploding Topics API
Step 2: Analyze each topic (core need, audience, growth drivers)
Step 3: Synthesize patterns → 3 opportunity spaces
Step 4: Brainstorm 3 fully-fleshed ideas
Step 5: Validate each idea via idea-validator (4-dimension scoring)
Step 6: Select best idea (composite score + tiebreakers)
Step 7: Output structured markdown report
```

## Prerequisites

- **Python 3.x** (stdlib only — `urllib` + `json`, no pip packages)
- **Internet access** to fetch `explodingtopics.com`
- **idea-validator** skill installed at `~/.config/opencode/skills/idea-validator/`

## Usage

```bash
/trend-ideas --output "$PRODUCT_DIR/trend-report.md"
```

### Output

`trend-report.md` containing:
- Top 15 topics table (growth %, volume, core need)
- 3 validated ideas with composite scores (0-100)
- Winning idea with full detail and validation summary

### Score Formula

```
Composite = (Creativity + Feasibility + Market Impact + Technical Execution) × 2.5
```

## Edge Cases

- **API fetch fails**: Fallback to `webfetch` on `https://explodingtopics.com` (text mode)
- **Fewer than 15 topics**: Use all available; note in report
- **Negative/zero growth**: Include but prioritize positive growth
- **All topics same cluster**: Generate 3 distinct angles/sub-segments
- **All ideas scored "Skip it"**: Still pick highest; flag risk in report

## Integration with idea-to-product

Trong Phase 1 — Idea Generation:

```
/trend-ideas --output "$PRODUCT_DIR/trend-report.md"
```

Kết quả được dùng làm input cho `idea-validator` → `prd-generator` → build.
