---
name: idea-to-product
description: "End-to-end product builder from trend analysis to runnable code. Fetches trending topics, validates the best idea, generates PRD/architecture/tasks, builds a full-stack product (FastAPI + React/Vite/Tailwind), reviews code, adds tests, and prepares for shipping. Use when asked to build a product from scratch, turn a trend into a product, or go from idea to working app. Don't use for single-phase work — invoke the sibling skill directly."
license: MIT
effort: max
metadata:
  version: 1.0.0
  author: "Nguyen Van Lam"
---

# Idea to Product

4-phase orchestrator that takes trending topics and produces a runnable full-stack product — idea validation, product definition, implementation, and ship preparation.

Stack: FastAPI (Python) + React (Vite/Tailwind/shadcn/ui) + SQLite. Runs locally with `make dev`.

## When to Use

Trigger when the user asks to:
- Build a product from an idea or trend
- "Go from idea to working app"
- Turn trending topics into a real product
- Create a full-stack MVP from scratch

Do **not** use for:
- Single-phase work (use the specific sibling skill directly)
- Cloning existing websites (use `website-cloner`)
- Non-technical product planning only

## Prerequisites

### Required Skills (from `luongnv89/skills`)

All of these must be installed before starting:

| Skill | Version | Phase |
|-------|---------|-------|
| `trend-ideas` | 2.0.0+ | 1 |
| `idea-validator` | 1.2.0+ | 1 |
| `prd-generator` | 1.2.0+ | 2 |
| `tad-generator` | 1.2.0+ | 2 |
| `tasks-generator` | 1.2.0+ | 2 |
| `logo-designer` | 1.2.0+ | 3 |
| `frontend-design` | 1.2.0+ | 3 |
| `code-review` | 1.0.0+ | 3 |
| `test-coverage` | 1.2.0+ | 3 |
| `devops-pipeline` | 1.0.0+ | 4 |
| `docs-generator` | 1.2.0+ | 4 |
| `oss-ready` | 1.1.0+ | 4 |
| `seo-ai-optimizer` | 1.0.0+ | 4 |
| `readme-to-landing-page` | 2.0.0+ | 4 |
| `release-manager` | 2.4.0+ | 4 |

### Install Command

```bash
npx skills add https://github.com/luongnv89/skills --skill <skill-name>
```

Or install all at once:
```bash
npx skills add https://github.com/luongnv89/skills
```

### Runtime Requirements

- **Python 3.10+** with `pip`
- **Node.js 18+** with `npm`
- **Git** configured with user.name and user.email

## Setup

1. **Resolve working directory** — where the product will be built. If `$PRODUCT_DIR` is set, use it. Otherwise ask the user once and save to `~/.config/idea-to-product-dir.txt`. Default: `~/workspace/products`.
2. **Create project folder**: `YYYY_MM_DD_<product-slug>/` under the resolved root.
3. **Set `$PRODUCT_DIR`** to the created folder path.
4. **Verify all prerequisite skills** are installed. If any missing, report the list and stop.

## Workflow

```
Phase 1 — Idea Generation  → trend-ideas + idea-validator
Phase 2 — Product Planning (GATE) → prd-generator + tad-generator + tasks-generator
Phase 3 — Build Product (GATE) → logo-designer + frontend-design + implement + code-review + test-coverage
Phase 4 — Ship Prep → devops-pipeline + docs-generator + oss-ready + seo-ai-optimizer + readme-to-landing-page + release-manager
```

Approval gates after Phase 1, 2, and 3: **must not advance** without explicit user approval.

---

## Phase 1: Idea Generation & Validation

Invoke `trend-ideas` to fetch trends, brainstorm 3 ideas, validate each via `idea-validator`, and select the winning idea.

```
/trend-ideas --output "$PRODUCT_DIR/trend-report.md"
```

**Output:** `$PRODUCT_DIR/trend-report.md` containing:
- Top 15 trending topics with growth/volume/core-need
- 3 validated ideas with composite scores
- Winning idea with full detail and validation summary

**Check:**
- [ ] trend-report.md exists
- [ ] Winning idea clearly identified with name and score
- [ ] All 4 validation dimensions present (Creativity, Feasibility, Market Impact, Technical Execution)

**Step Completion Report:**
```
◆ Idea Generation (step 1 of 4)
······································································
  Topics fetched:        √ pass (<N> topics)
  Ideas generated:       √ pass (3 ideas)
  Ideas validated:       √ pass (3/3 scored)
  Winning idea:          √ pass (<name> — <score>/100)
  ____________________________
  Result:                PASS
```

### GATE: Present winning idea to user for approval.

If not approved, do not advance. Ask the user to choose a different idea or re-run Phase 1.

---

## Phase 2: Product Definition

### Step 2a: Generate PRD

Invoke `prd-generator` with the winning idea from the trend report:

```
/prd-generator --idea "$(extract winning idea from trend-report.md)" --output "$PRODUCT_DIR/prd.md"
```

**Output:** `$PRODUCT_DIR/prd.md` — structured PRD with features, user stories, success criteria, and scope.

### Step 2b: Generate Technical Architecture

Invoke `tad-generator` with the PRD:

```
/tad-generator "$PRODUCT_DIR/prd.md" --output "$PRODUCT_DIR/architecture.md"
```

**Output:** `$PRODUCT_DIR/architecture.md` — data flow diagrams, component tree, API routes, database schema.

### Step 2c: Generate Tasks

Invoke `tasks-generator` with the PRD and architecture:

```
/tasks-generator "$PRODUCT_DIR/prd.md" --arch "$PRODUCT_DIR/architecture.md" --output "$PRODUCT_DIR/tasks.md"
```

**Output:** `$PRODUCT_DIR/tasks.md` — sprint-ready task breakdown with effort estimates.

**Check:**
- [ ] prd.md exists with features, user stories, success criteria
- [ ] architecture.md exists with API routes, DB schema, component tree
- [ ] tasks.md exists with phased task breakdown

**Step Completion Report:**
```
◆ Product Definition (step 2 of 4)
······································································
  PRD written:           √ pass (prd.md)
  Architecture doc:      √ pass (architecture.md)
  Task breakdown:        √ pass (tasks.md — <N> tasks)
  ____________________________
  Result:                PASS
```

### GATE: Present PRD + tasks to user for approval.

---

## Phase 3: Build Product

### Step 3a: Logo & Brand Assets

Invoke `logo-designer`:

```
/logo-designer --product "<product-name>" --output "$PRODUCT_DIR/assets/logo"
```

### Step 3b: Frontend Scaffold

Invoke `frontend-design` to generate the UI shell:

```
/frontend-design --product "<product-name>" --output "$PRODUCT_DIR/frontend" --framework react --styling tailwind --components shadcn
```

### Step 3c: Implement Product (AI-driven)

Using the PRD, architecture, and tasks as specifications, build the full product. The AI agent writes all code.

**Backend (FastAPI + SQLite):**

Create `$PRODUCT_DIR/backend/` with:

```
backend/
├── main.py              # FastAPI app entry point with CORS
├── database.py          # SQLAlchemy engine + session
├── models.py            # All database models
├── schemas.py           # Pydantic request/response schemas
├── routes/
│   ├── __init__.py
│   ├── auth.py          # If needed
│   ├── items.py         # Domain-specific routes per architecture.md
│   └── ...
├── services/
│   ├── __init__.py
│   └── ...              # Business logic layer
├── requirements.txt     # fastapi, uvicorn, sqlalchemy, pydantic, ...
└── seed.py              # Optional seed data script
```

Backend conventions:
- Use `SQLAlchemy 2.0` style (declarative base, async not required for SQLite)
- All routes under prefix `/api/v1`
- CORS allow `http://localhost:5173` (Vite dev server)
- Health check at `GET /api/v1/health`

**Frontend (React + Vite + Tailwind + shadcn/ui):**

The `frontend-design` skill already scaffolded the frontend. Now implement:

- Pages per PRD requirements (in `frontend/src/pages/`)
- API client layer (in `frontend/src/api/`) using `fetch` or `axios`
- Auth flow if specified in PRD
- All business logic interactions with backend
- Responsive layout per Tailwind design

**Root project files:**

Create at `$PRODUCT_DIR/`:

- `Makefile` — targets: `install`, `dev`, `test`, `lint`, `build`
- `README.md` — project description, quick start, tech stack
- `.gitignore` — Python + Node defaults

**Makefile template:**

```makefile
.PHONY: install dev test lint build

install:
	cd frontend && npm install
	cd backend && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

dev:
	@echo "Starting frontend (http://localhost:5173) and backend (http://localhost:8000)..."
	cd frontend && npm run dev &
	cd backend && uvicorn main:app --reload --port 8000 &
	wait

test:
	cd frontend && npm run test
	cd backend && . venv/bin/activate && python -m pytest

lint:
	cd frontend && npm run lint
	cd backend && . venv/bin/activate && ruff check .

build:
	cd frontend && npm run build
```

**Verification:** After implementation, start both servers and confirm:
- Frontend loads at `http://localhost:5173`
- Backend health check: `curl http://localhost:8000/api/v1/health` → `200 OK`
- At least one API endpoint returns real data
- Frontend can communicate with backend (check browser console for CORS/network errors)

### Step 3d: Code Review

Invoke `code-review` on the full product:

```
/code-review "$PRODUCT_DIR/backend" "$PRODUCT_DIR/frontend" --output "$PRODUCT_DIR/code-review-report.md"
```

Apply any critical fixes from the review before proceeding.

### Step 3e: Test Coverage

Invoke `test-coverage` on both frontend and backend:

```
/test-coverage "$PRODUCT_DIR/backend" --framework pytest --output "$PRODUCT_DIR/test-coverage-backend.md"
/test-coverage "$PRODUCT_DIR/frontend" --framework vitest --output "$PRODUCT_DIR/test-coverage-frontend.md"
```

**Check:**
- [ ] Logo assets exist
- [ ] Frontend compiles and runs (`npm run dev` without errors)
- [ ] Backend starts (`uvicorn main:app --reload` without errors)
- [ ] Health endpoint returns 200
- [ ] At least 1 end-to-end flow works (frontend → backend → DB)
- [ ] Code review completed, critical issues fixed
- [ ] Test coverage gaps addressed

**Step Completion Report:**
```
◆ Build Product (step 3 of 4)
······································································
  Logo:                 √ pass
  Frontend scaffold:    √ pass
  Backend implemented:  √ pass (<N> routes)
  Frontend implemented: √ pass (<N> pages)
  Local dev verified:   √ pass (frontend + backend running)
  Code review:          √ pass (<N> issues, <N> fixed)
  Tests added:          √ pass (backend: <N>%, frontend: <N>%)
  ____________________________
  Result:               PASS
```

### GATE: Demo the running product to user for approval.

Run both servers (`make dev` in a terminal or background), show the user the URLs, and ask them to approve before proceeding to Phase 4.

---

## Phase 4: Ship Preparation

### Step 4a: DevOps Pipeline

Invoke `devops-pipeline` at the product root:

```
/devops-pipeline "$PRODUCT_DIR" --output "$PRODUCT_DIR"
```

Sets up pre-commit hooks and GitHub Actions workflow.

### Step 4b: Open Source Ready

Invoke `oss-ready`:

```
/oss-ready "$PRODUCT_DIR" --output "$PRODUCT_DIR"
```

Generates LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md, issue/PR templates.

### Step 4c: Documentation

Invoke `docs-generator`:

```
/docs-generator "$PRODUCT_DIR" --output "$PRODUCT_DIR/docs"
```

Restructures and organizes project documentation.

### Step 4d: SEO Optimization

Invoke `seo-ai-optimizer` on the project landing page (README → landing page output):

```
/seo-ai-optimizer "$PRODUCT_DIR/landing" --output "$PRODUCT_DIR/seo-report.md"
```

### Step 4e: Landing Page from README

Invoke `readme-to-landing-page`:

```
/readme-to-landing-page "$PRODUCT_DIR/README.md" --output "$PRODUCT_DIR/landing"
```

### Step 4f: Release

Invoke `release-manager` to create the first release:

```
/release-manager "$PRODUCT_DIR" --version 0.1.0 --output "$PRODUCT_DIR"
```

**Check:**
- [ ] Pre-commit hooks installed
- [ ] GitHub Actions workflow created
- [ ] LICENSE, CONTRIBUTING, CODE_OF_CONDUCT created
- [ ] Documentation organized under docs/
- [ ] Landing page generated
- [ ] SEO report produced
- [ ] Release tagged (v0.1.0)

**Step Completion Report:**
```
◆ Ship Preparation (step 4 of 4)
······································································
  CI/CD:                √ pass (.github/workflows/)
  Open source files:    √ pass (LICENSE, CONTRIBUTING, etc.)
  Documentation:        √ pass (docs/)
  Landing page:         √ pass (landing/)
  SEO audit:            √ pass (seo-report.md)
  Release:              √ pass (v0.1.0)
  ____________________________
  Result:               PASS
```

---

## Expected Output

```
◆ Idea to Product — <product-name>
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
  Phase 1  Idea Generation    √ pass  (<name> — <score>/100)
  Phase 2  Product Planning   √ approved (prd.md + tasks.md)
  Phase 3  Build Product      √ approved (runs locally)
  Phase 4  Ship Prep          √ pass  (v0.1.0)

  Product:   $PRODUCT_DIR
  Frontend:  http://localhost:5173
  Backend:   http://localhost:8000
  API docs:  http://localhost:8000/docs
```

Final delivery summary file: `$PRODUCT_DIR/final-report.md` containing:

```markdown
# Final Report: <product-name>
*Generated: {date}*

## Summary
- **Idea**: <name> (validated <score>/100)
- **Stack**: FastAPI + React/Vite/Tailwind + SQLite
- **Local run**: `make dev`
- **Version**: 0.1.0

## What Was Built
- Backend: <N> API routes, <N> database models
- Frontend: <N> pages, <N> components
- Tests: backend <N>%, frontend <N>% coverage

## Artifacts
- PRD: prd.md
- Architecture: architecture.md
- Tasks: tasks.md
- Code review: code-review-report.md
- SEO report: seo-report.md
- Landing page: landing/

## Quick Start
```bash
cd <product-dir>
make install
make dev
```
```

---

## Edge Cases

- **Missing prerequisite skill**: Report the list of missing skills and stop. Provide the install command.
- **trend-ideas fails to fetch trends**: Retry once. If still fails, use `webfetch` on `https://explodingtopics.com` as fallback. If both fail, ask user to provide an idea directly.
- **User disapproves at Phase 1 gate**: Ask which idea they prefer or if they want to re-run Phase 1.
- **User disapproves at Phase 2 gate**: Revise PRD/tasks per user feedback.
- **User disapproves at Phase 3 gate**: Fix specific issues before moving to Phase 4.
- **Build errors**: Stop, fix errors, re-verify before proceeding.
- **localhost ports 5173/8000 in use**: Detect and report. Ask user to free ports or use alternatives.
- **Python/Node not installed**: Report missing runtime and instructions to install.
- **npm install or pip install fails**: Check network, retry once. If still fails, note in report and stop.
