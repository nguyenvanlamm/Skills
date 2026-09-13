# Trend Ideas Skill

## Overview

Fetch top 15 trending topics from Exploding Topics, brainstorm 3 product ideas, validate each with `idea-validator`, and pick the highest-scoring idea.

## Workflow

```
Step 1: Fetch trending topics (scripts/fetch_trends.py, retries + --save-raw)
Step 2: Analyze each topic (core need, audience, growth drivers)
Step 3: Synthesize patterns → 3 opportunity spaces
Step 4: Brainstorm 3 fully-fleshed ideas
Step 5: IDEAS_ROOT=<output_dir>/ideas → idea-validator creates YYYY_MM_DD_<slug>/{idea.md,validate.md} per idea
Step 6: Select best idea (composite + tiebreakers) → copy winner to <output_dir>/idea.md + validate.md
Step 7: Output structured markdown report
```

## Prerequisites

- **Python 3.9+** (stdlib only — no pip packages)
- **Internet access** to `explodingtopics.com`, or a saved raw response via `--from-file`
- **idea-validator** skill invokable by the host (any location — the skill does not probe paths)

## Script

```bash
python3 scripts/fetch_trends.py --limit 15 --save-raw trends-raw.json   # live
python3 scripts/fetch_trends.py --from-file trends-raw.json              # offline / reproducible
python3 scripts/fetch_trends.py --min-volume 1000                        # drop tiny topics
```

Exit 0 with `{"topics": [...]}`; exit 1 with `{"error": "..."}`. Diagnostics go to stderr.

## Output

- `<output>` — markdown report (topics table with `growth_basis`, 3 ideas with scores, winner)
- `<output_dir>/ideas/YYYY_MM_DD_<slug>/{idea.md,validate.md}` — one folder per idea, created by idea-validator
- `<output_dir>/idea.md` + `validate.md` — the winner, in the exact shape `prd-generator` consumes

### Score formula

```
Composite = (Creativity + Feasibility + Market Impact + Technical Execution) × 2.5
```

## Edge cases

- **API fetch fails** after 3 retries: stop and say so. No HTML scraping fallback — it would claim a source that was not used.
- **Fewer than 15 topics**: use all; report `count/requested`.
- **idea-validator unavailable**: write the 3 `idea.md`, stop, report validation did not run.
- **All ideas "Skip it"**: pick highest; lead the winner section with the warning.

## Integration with idea-to-product / idea-to-play-store

Phase 1 invokes this skill with `output=$PRODUCT_DIR/trend-report.md` and `output_dir=$PRODUCT_DIR`. The orchestrator then hands `$PRODUCT_DIR/idea.md` + `validate.md` to `prd-generator` without re-running validation.
