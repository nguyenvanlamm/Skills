<!-- DO NOT READ THIS FILE -->
<!-- This file is for human browsing only. AI agents should read SKILL.md -->

# Idea to Product

**4-phase orchestrator** that goes from trending topics → validated idea → PRD → runnable full-stack product → ship-ready.

## Pipeline

| Phase | What happens | Output |
|-------|-------------|--------|
| 1 — Idea Generation | Fetch trends, brainstorm 3 ideas, validate with idea-validator | Winning idea + validation scores |
| 2 — Product Definition | Generate PRD, architecture docs, task breakdown | prd.md, tad.md, tasks.md |
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

This umbrella depends on 15+ sibling skills (`trend-ideas`, `idea-validator`, `prd-generator`, `tad-generator`, `tasks-generator`, `logo-designer`, `frontend-design`, `code-review`, `test-coverage`, `firebase-auth-setup`, `devops-pipeline`, `doc-manager`, `oss-ready`, `seo-ai-optimizer`, `landing-page-generator`, `release-manager`, `deploy-render`, `deploy-netlify`). Install them all:

```bash
npx skills add https://github.com/nguyenvanlamm/Skills
```

Availability is checked per phase by invoking through the host's skill mechanism — never by probing a path.

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
YYYY_MM_DD_<slug>/
├── trend-report.md · idea.md · validate.md · prd.md · tad.md · tasks.md
├── ideas/YYYY_MM_DD_<slug>/{idea.md,validate.md}  # all 3 candidates (created by idea-validator)
├── firebase-config/                            # only if the PRD needs login (gitignored)
├── <slug>-server/    # FastAPI — its own GitHub repo (Makefile, docs/, .github/workflows/)
├── <slug>-client/    # React + Vite — its own GitHub repo (landing/, docs/, .github/workflows/)
└── final-report.md
```
