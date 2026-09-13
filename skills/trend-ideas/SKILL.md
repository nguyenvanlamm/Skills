---
name: trend-ideas
description: "Fetch top 15 trending topics from Exploding Topics, brainstorm 3 ideas, validate each with idea-validator, and pick the highest-scoring idea. Not for non-English trend sources or general competitor research."
license: MIT
effort: medium
metadata:
  version: 2.2.0
  author: Luong NGUYEN <luongnv89@gmail.com>
---

# Trend Ideas

Analyze real-time trending topics from Exploding Topics and generate 3 novel business ideas that address the underlying market needs, then let `idea-validator` score them.

## Core principle

> **Numbers in the report come from the script or from `idea-validator` — never from this skill's own judgement.** Growth and volume are copied from `fetch_trends.py` output. Ratings and verdicts are copied from `idea-validator`. If either source is unavailable, the report says so; it does not fill the gap with an estimate and call it "validated".

## Prerequisites

- Python 3.9+ on the path. The script is stdlib-only (`urllib`, `json`, `argparse`).
- Internet access to `explodingtopics.com` — **or** a saved raw response passed with `--from-file`.
- The **`idea-validator` skill** must be invokable by the host (skill tool, `/idea-validator`, or equivalent). Do not probe a filesystem path — skills live in different places on different hosts, and a path check that fails makes this skill refuse to run where the skill is in fact present. Confirm availability by attempting the invocation at Step 5, not by guessing earlier.

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `output` | ❌ | stdout | Path for the markdown report (e.g. `$PRODUCT_DIR/trend-report.md`) |
| `output_dir` | ❌ | dir of `output`, else `.` | Where per-idea `idea.md` / `validate.md` files are written (see Step 5) |
| `limit` | ❌ | 15 | Topics to fetch |
| `from_file` | ❌ | — | Reuse a saved raw API response (offline, or to reproduce a previous run) |

## Workflow

Fully automatic — no user approval between steps.

---

### Step 1: Fetch trending topics

The script lives beside this file. Resolve its path from the skill directory, not from the working directory:

```bash
python3 "<skill-dir>/scripts/fetch_trends.py" --limit 15 --save-raw "<output_dir>/trends-raw.json"
```

`--save-raw` keeps the raw response so a re-run with `--from-file trends-raw.json` reproduces the same topic list without another network call.

**stdout** is one JSON object: `topics[]` (`name`, `growth_pct`, `growth_raw`, `growth_basis`, `search_volume`, `url`), `count`, `total_available`, `source`, `fetched_at`.

**Failure handling — one rule, no exceptions:** exit code 1 with `{"error": ...}` means the data is unavailable. The script already retried 3× with backoff. **Stop and report that trends could not be fetched.** Do not scrape `explodingtopics.com` HTML as a fallback — the page is client-rendered and the numbers you would read off it are not the API's numbers; a report built that way claims a source it did not use. The user may supply `--from-file` from an earlier run, or provide an idea directly (then this skill does not apply — use `idea-validator`).

**Two caveats to carry into the report:**

`explodingtopics.com/api/trends` is an **undocumented internal endpoint**. It can change shape or refuse requests at any time.

`growth["24"]` is a **multiplier** (verified against topic pages, 2026-09): `2.12` renders as +212%, and `99` renders as **+99X+** — the upstream cap for breakout topics, not 99%. The script multiplies by 100 and labels capped values `capped 99x+ (upstream cap, not a measurement)` in `growth_basis`. Treat capped topics as "exploding, magnitude unknown": rank them highly, but never quote "9900%" as a measured figure. `search_volume` is `0` for many of them — a real signal that the topic is too new for volume data.

---

### Step 2: Analyze each topic

For each topic, fill the Topic Analysis Template in `references/idea-framework.md`: Core Need, Target Audience, Growth Drivers, Pain Points, Existing Landscape. This is analysis, not lookup — no numbers are introduced here.

---

### Step 3: Synthesize patterns

1. **Cluster** topics by shared core need.
2. **Rank** clusters by momentum (average `growth_pct`, total `search_volume`).
3. **Select** 3 opportunity spaces that combine high growth, underserved or fragmented solutions, and feasibility (not capital-intensive or heavily regulated).

If everything clusters into one need, still produce 3 distinct angles or sub-segments within it.

---

### Step 4: Brainstorm 3 ideas

One per opportunity space, using the Idea Template in `references/idea-framework.md`: Name, Elevator Pitch, Core Need, How It Works, Target Audience, Why Now, Go-to-Market Sketch, Monetization, Risk Factor.

---

### Step 5: Validate each idea with idea-validator

`idea-validator` reads an `idea.md` and writes a `validate.md` beside it. Give each idea its own directory so the three runs do not overwrite each other, and so downstream skills (`prd-generator` needs exactly these two files) can consume the winner without re-extraction:

```
<output_dir>/ideas/
├── 1-<slug>/idea.md      ← written by this skill from Step 4
│            validate.md  ← written by idea-validator
├── 2-<slug>/…
└── 3-<slug>/…
```

Write `idea.md` first (the full idea package from Step 4), then invoke `idea-validator` on that directory. Its Phase 1 (Clarify) needs no user questions — the idea is already fully specified. For Phase 2 (Tech Context), state these assumptions rather than asking: web/mobile stack as fits the idea; 3–6 months to MVP with 2–3 devs; bootstrapped; standard startup constraints. Phases 3–5 (competitive landscape with live searches, critical evaluation, improvements) run as that skill instructs.

From each `validate.md` extract, verbatim:

| Field | Source line in idea-validator output |
|-------|--------------------------------------|
| Quick Verdict | `Build it` / `Maybe` / `Skip it` |
| Creativity, Feasibility, Market Impact, Technical Execution | the 4-row Ratings table, each `X/10` |

Then compute `composite = (C + F + M + T) × 2.5` (0–100) and record `{ name, dir, composite, verdict, c, f, m, t }`.

**If `idea-validator` is not invokable:** stop after writing the three `idea.md` files and report that validation could not run. Do not score the ideas yourself and label the result "validated" — that misrepresents where the numbers came from. The three `idea.md` files are still useful output; say so.

---

### Step 6: Select the winner

1. Highest composite.
2. Tie → `Build it` > `Maybe` > `Skip it`.
3. Tie → higher Market Impact.
4. Tie → higher Feasibility.
5. Still tied → pick the first and say the tie was broken arbitrarily.

Copy the winner's `idea.md` and `validate.md` to `<output_dir>/idea.md` and `<output_dir>/validate.md`. That pair is the contract downstream orchestrators (`idea-to-product`, `idea-to-play-store`) rely on.

If all three are `Skip it`, still pick the highest — and put that fact in the first line of the Winning Idea section, not in a footnote.

---

### Step 7: Report

```markdown
# Trend Ideas Report
*Generated: {fetched_at} · source: {source} · {count}/{requested} topics*

## Top {count} Trending Topics

| # | Topic | Growth | Basis | Volume | Core Need |
|---|-------|--------|-------|--------|-----------|
| 1 | ... | +212% | multiplier x100 | 246,000 | ... |
| 2 | ... | 99x+ (capped) | capped 99x+ | 0 | ... |

## 3 Ideas — Validation Scores

| Idea | Creativity | Feasibility | Market | Technical | Composite | Verdict | Files |
|------|-----------|-------------|--------|-----------|-----------|---------|-------|
| Idea 1 | 8/10 | 7/10 | 9/10 | 6/10 | 75/100 | Build it | ideas/1-… |

*Composite = (Creativity + Feasibility + Market Impact + Technical Execution) × 2.5*

## Winning Idea: {name} — {composite}/100 ({verdict})

{Elevator pitch + why it outscored the others}

{Full idea from Step 4}

### Validation Summary
{Quick Verdict + top strengths + top concerns, quoted from validate.md}

## Caveats
- Endpoint is undocumented; growth basis per topic in the table above.
- {fewer than requested topics / all Skip it / tie broken arbitrarily — whichever applied}
```

Write to `output` if given, else print.

## Acceptance criteria

- [ ] `fetch_trends.py` exit 0; report shows `count`/`requested` and `source`
- [ ] Every topic has a Core Need
- [ ] 3 ideas, each with all template fields
- [ ] 3 × `idea.md` written; 3 × `validate.md` present (or the run stopped with a clear "validation unavailable")
- [ ] All 4 ratings per idea copied from `validate.md`, composite arithmetic correct
- [ ] Winner chosen by composite + tiebreakers; `<output_dir>/idea.md` + `validate.md` are the winner's
- [ ] No growth/volume/rating figure appears that is not in the script output or a `validate.md`

## Edge cases

| Situation | Handling |
|-----------|----------|
| Fetch fails after retries | Stop. Report unavailable. Offer `--from-file` or direct `idea-validator` use. **No HTML scraping.** |
| Fewer than `limit` topics | Use all; state `count/requested` in the report header |
| Zero or negative growth | Keep in the table, flagged; do not build ideas on them |
| All topics one cluster | 3 sub-segment angles |
| `idea-validator` unavailable | Write the 3 `idea.md`, stop, say validation did not run |
| `idea-validator` output missing a rating | Re-read `validate.md`; if truly absent, mark that idea `incomplete` and exclude it from the winner selection, saying so |
| All verdicts `Skip it` | Pick highest composite; lead the Winning Idea section with the warning |
| Composite tie | Tiebreakers in order; arbitrary last, disclosed |
| `<output_dir>/idea.md` already exists | Ask before overwriting — it may be a previous winner the user is working from |
