<!-- DO NOT READ THIS FILE -->
<!-- This file is for human browsing only. AI agents should read SKILL.md -->

# Idea to Product

**4-phase orchestrator** that goes from trending topics → validated idea → PRD → runnable full-stack product → ship-ready.

## Pipeline

| Phase | What happens | Output |
|-------|-------------|--------|
| 1 — Idea Generation | Fetch trends, brainstorm 3 ideas, validate with idea-validator | Winning idea + validation scores |
| 2 — Product Definition | Generate PRD, architecture docs, task breakdown | prd.md, architecture.md, tasks.md |
| 3 — Build Product | Logo, frontend scaffold, implement full-stack app, code review, tests | Runnable product (make dev) |
| 4 — Ship Prep | CI/CD, docs, landing page, SEO, release | v0.1.0 release-ready |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite + Tailwind CSS + shadcn/ui |
| Backend | Python FastAPI + SQLAlchemy + SQLite |
| Dev run | `make install` → `make dev` |
| Test | pytest (backend) + vitest (frontend) |

## Required Skills

This umbrella depends on 15+ skills from [luongnv89/skills](https://github.com/luongnv89/skills). Install them all:

```bash
npx skills add https://github.com/luongnv89/skills
```

## Quick Start

```bash
# 1. Install the umbrella skill
npx skills add https://github.com/nguyenvanlamm/Skills --skill idea-to-product

# 2. Trigger the workflow
# "Build a product from trending ideas"
```

## Output

After a full run, you get:

```
product-name/
├── backend/          # FastAPI application
├── frontend/         # React + Vite application
├── tests/            # pytest + vitest
├── Makefile          # install, dev, test, lint, build
├── README.md
├── docs/
├── landing/
├── .github/workflows/
└── final-report.md
```
