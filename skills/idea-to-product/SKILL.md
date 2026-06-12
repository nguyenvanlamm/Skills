---
name: idea-to-product
description: "End-to-end product builder from trend analysis to runnable code. Fetches trending topics, validates the best idea, generates PRD/architecture/tasks, builds a full-stack product (server + client as 2 separate GitHub repos), reviews code, adds tests, and prepares for shipping. Use when asked to build a product from scratch, turn a trend into a product, or go from idea to working app. Don't use for single-phase work — invoke the sibling skill directly."
license: MIT
effort: max
metadata:
  version: 1.0.0
  author: "Nguyen Van Lam"
---

# Idea to Product

4-phase orchestrator that takes trending topics and produces a runnable full-stack product — idea validation, product definition, implementation, and ship preparation.

Stack: FastAPI (Python) + React (Vite/Tailwind/shadcn/ui) + SQLite.

**Server và client là 2 project riêng biệt**, mỗi project là một GitHub repo độc lập để dễ dàng deploy và maintain.

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
| `firebase-auth-setup` | 1.0.0+ | 3 (bắt buộc — thay thế JWT tự build) |
| `devops-pipeline` | 1.0.0+ | 4 |
| `docs-generator` | 1.2.0+ | 4 |
| `deploy-render` | 1.0.0+ | 4 (nếu cần deploy server) |
| `deploy-netlify` | 1.0.0+ | 4 (nếu cần deploy client) |
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

1. **Resolve working directory** — where the product repos will live. If `$PRODUCT_DIR` is set, use it. Otherwise ask the user once and save to `~/.config/idea-to-product-dir.txt`. Default: `~/workspace/products`.
2. **Create parent folder**: `YYYY_MM_DD_<product-slug>/` under the resolved root.
3. **Set `$PRODUCT_DIR`** to the created folder path.
4. **Create 2 sub-directories** — one cho server, một cho client:
   ```
   $PRODUCT_DIR/
   ├── <product-slug>-server/    # FastAPI backend (Python repo)
   └── <product-slug>-client/    # React frontend (Node repo)
   ```
5. **Ask user for GitHub repo names** (hoặc dùng slug mặc định):
   - Server repo: `gh repo create <product-slug>-server --private`
   - Client repo: `gh repo create <product-slug>-client --private`
6. **Initialize git** trong từng project:
   ```bash
   cd <product-slug>-server && git init && git add . && git commit -m "Initial commit"
   cd <product-slug>-client && git init && git add . && git commit -m "Initial commit"
   ```
7. **Verify all prerequisite skills** are installed. If any missing, report the list and stop.

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

### Step 3c: Firebase Auth Setup (bắt buộc — thay thế JWT tự build)

Khi PRD có yêu cầu register/login (F1), **bắt buộc dùng Firebase Auth**. Không tự build JWT.

```markdown
/firebase-auth-setup --slug "<product-slug>" --output "$PRODUCT_DIR/firebase-config"
```

Sau khi chạy xong, đọc `$PRODUCT_DIR/firebase-config/firebase-output.json` để lấy:
- `project_id` → ghi vào server `.env` là `FIREBASE_PROJECT_ID`
- `web_app` → ghi vào client `.env` là `VITE_FIREBASE_*`
- `service_account.key_path` → ghi vào server `.env` là `GOOGLE_APPLICATION_CREDENTIALS`

---

### Step 3d: Implement Product (AI-driven) — 2 Repos Riêng

Using the PRD, architecture, and tasks as specifications, build the full product. **Server và client là 2 project riêng biệt**, mỗi project có git repo riêng để push lên GitHub.

---

#### Server Project: `<product-slug>-server/` (FastAPI + SQLite)

```
<product-slug>-server/
├── main.py              # FastAPI app entry point with CORS
├── database.py          # SQLAlchemy engine + session
├── models.py            # All database models
├── schemas.py           # Pydantic request/response schemas
├── routes/
│   ├── __init__.py
│   ├── auth.py          # Verify Firebase ID token (firebase_admin.auth.verify_id_token)
│   └── ...              # Domain-specific routes per architecture.md
├── services/
│   ├── __init__.py
│   └── ...              # Business logic layer
├── firebase_config.py   # Init firebase_admin SDK với service account key
├── requirements.txt     # fastapi, uvicorn, sqlalchemy, pydantic, firebase-admin
├── .env                 # FIREBASE_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS
├── seed.py              # Optional seed data script
├── Makefile
├── README.md
└── .gitignore
```

**Makefile (server):**
```makefile
.PHONY: install dev test lint

install:
	pip install -r requirements.txt

dev:
	uvicorn main:app --reload --port 8000

test:
	python -m pytest

lint:
	ruff check .
```

Server conventions:
- Use `SQLAlchemy 2.0` style (declarative base, async not required for SQLite)
- All routes under prefix `/api/v1`
- CORS allow client's production URL + `http://localhost:5173`
- Health check at `GET /api/v1/health`
- `README.md` ghi rõ client repo URL + cách clone cả 2 để chạy fullstack
- `routes/auth.py` verify Firebase ID token bằng `firebase_admin.auth.verify_id_token` (không hash password, không dùng JWT tự build)
- `firebase_config.py` init `firebase_admin` với service account key

---

#### Client Project: `<product-slug>-client/` (React + Vite + Tailwind + shadcn/ui)

```
<product-slug>-client/
├── src/
│   ├── api/
│   │   ├── client.ts    # API client (gọi server URL)
│   │   └── firebase.ts  # Init Firebase app + export auth (signInWithEmailAndPassword, signInWithPopup)
│   ├── pages/           # Page components
│   ├── components/      # UI components
│   ├── hooks/           # Custom hooks
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── package.json         # dependencies bao gồm firebase
├── .env                 # VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, ...
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── Makefile
├── README.md
└── .gitignore
```

**Makefile (client):**
```makefile
.PHONY: install dev test lint build

install:
	npm install

dev:
	npm run dev

test:
	npm run test

lint:
	npm run lint

build:
	npm run build
```

**vite.config.ts** proxy trỏ tới server:
```typescript
server: {
  port: 5173,
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true },
  },
}
```

Client conventions:
- API base URL: dùng relative path `/api/v1` (dev server proxy) hoặc env var `VITE_API_URL` cho production
- `README.md` ghi rõ server repo URL + cách chạy fullstack
- `src/api/firebase.ts` init Firebase app với config từ `.env` (VITE_FIREBASE_*)
- Login page dùng Firebase SDK: `signInWithEmailAndPassword` (email/password) và `signInWithPopup` (Google)

---

**Verification:** Sau khi implement cả 2 project, chạy thử fullstack:
- `cd <product-slug>-server && make dev` → `http://localhost:8000/docs` (200 OK)
- `cd <product-slug>-client && make dev` → `http://localhost:5173` (200 OK)
- Frontend gọi được API backend qua proxy
- Client login được với Email/Password hoặc Google (qua Firebase SDK)
- Server verify được Firebase ID token (kiểm tra bằng `curl /api/v1/auth/me`)
- Mỗi project có git init + initial commit sẵn sàng push

### Step 3e: Code Review

Invoke `code-review` on both repos:

```
/code-review "$PRODUCT_DIR/<slug>-server" --output "$PRODUCT_DIR/code-review-server.md"
/code-review "$PRODUCT_DIR/<slug>-client" --output "$PRODUCT_DIR/code-review-client.md"
```

Apply any critical fixes from the review before proceeding.

### Step 3f: Test Coverage

Invoke `test-coverage` on both repos:

```
/test-coverage "$PRODUCT_DIR/<slug>-server" --framework pytest --output "$PRODUCT_DIR/test-coverage-server.md"
/test-coverage "$PRODUCT_DIR/<slug>-client" --framework vitest --output "$PRODUCT_DIR/test-coverage-client.md"
```

**Check:**
- [ ] Logo assets exist (client repo)
- [ ] Client compiles and runs (`npm run dev` without errors)
- [ ] Server starts (`uvicorn main:app --reload` without errors)
- [ ] Health endpoint returns 200
- [ ] At least 1 end-to-end flow works (client → server → DB)
- [ ] Code review completed, critical issues fixed
- [ ] Test coverage gaps addressed
- [ ] Client README links to server repo
- [ ] Server README links to client repo
- [ ] Both repos have `git init` + initial commit
- [ ] Firebase project created, auth enabled, keys downloaded (từ firebase-auth-setup)
- [ ] Client login flow works (Email/Password + Google) qua Firebase SDK
- [ ] Server verifies Firebase ID token correctly

**Step Completion Report:**
```
◆ Build Product (step 3 of 4)
······································································
  Logo:                 √ pass
  Firebase auth:        √ pass (hoặc N/A nếu product không cần auth)
  Server implemented:   √ pass (<N> routes, 1 repo)
  Client implemented:   √ pass (<N> pages, 1 repo)
  Cross-links:          √ pass (READMEs link each other)
  Local dev verified:   √ pass (client + server running)
  Code review:          √ pass (<N> issues, <N> fixed)
  Tests added:          √ pass (server: <N>%, client: <N>%)
  ____________________________
  Result:               PASS
```

### GATE: Demo the running product to user for approval.

Run both servers (`make dev` trong mỗi repo), show the user the URLs, và nhờ user approve trước khi chuyển sang Phase 4.

---

## Phase 4: Ship Preparation (2 Repos)

Mỗi bước dưới đây chạy **riêng cho từng repo** (server + client), trừ khi có ghi chú khác.

### Step 4a: DevOps Pipeline

```
/devops-pipeline "$PRODUCT_DIR/<slug>-server" --output "$PRODUCT_DIR/<slug>-server"
/devops-pipeline "$PRODUCT_DIR/<slug>-client" --output "$PRODUCT_DIR/<slug>-client"
```

### Step 4b: Open Source Ready

```
/oss-ready "$PRODUCT_DIR/<slug>-server" --output "$PRODUCT_DIR/<slug>-server"
/oss-ready "$PRODUCT_DIR/<slug>-client" --output "$PRODUCT_DIR/<slug>-client"
```

### Step 4c: Documentation

```
/docs-generator "$PRODUCT_DIR/<slug>-server" --output "$PRODUCT_DIR/<slug>-server/docs"
/docs-generator "$PRODUCT_DIR/<slug>-client" --output "$PRODUCT_DIR/<slug>-client/docs"
```

### Step 4d: Push to GitHub

Push cả 2 repo lên GitHub:

```bash
cd $PRODUCT_DIR/<slug>-server
git remote add origin git@github.com:<user>/<slug>-server.git
git push -u origin main

cd $PRODUCT_DIR/<slug>-client
git remote add origin git@github.com:<user>/<slug>-client.git
git push -u origin main
```

### Step 4e: Deploy Server to Render (nếu cần)

Deploy server FastAPI lên Render.com. Kiểm tra xem server có cần database không (dựa vào PRD hoặc kiểm tra có `models.py` với `Base` không):

```bash
# Có database (mặc định):
/deploy-render --server-dir "$PRODUCT_DIR/<slug>-server" --slug "<slug>"

# Không cần database (thêm --no-db):
/deploy-render --server-dir "$PRODUCT_DIR/<slug>-server" --slug "<slug>" --no-db
```

→ URL production: `https://<slug>-server.onrender.com`

### Step 4f: Deploy Client to Netlify (nếu có client)

Deploy React client lên Netlify:

```bash
# Nếu có server:
API_URL=$(jq -r '.url' "$PRODUCT_DIR/deploy-output.json" 2>/dev/null || echo "")
if [ -n "$API_URL" ]; then
  /deploy-netlify --client-dir "$PRODUCT_DIR/<slug>-client" --slug "<slug>" --api-url "$API_URL"
else
  /deploy-netlify --client-dir "$PRODUCT_DIR/<slug>-client" --slug "<slug>"
fi
```

→ URL: `https://<slug>.netlify.app` (hoặc tên khác nếu bị trùng)

### Step 4g: Landing Page from README (client repo)

```
/readme-to-landing-page "$PRODUCT_DIR/<slug>-client/README.md" --output "$PRODUCT_DIR/<slug>-client/landing"
```

### Step 4h: Release (cả 2 repo)

```
/release-manager "$PRODUCT_DIR/<slug>-server" --version 0.1.0 --output "$PRODUCT_DIR/<slug>-server"
/release-manager "$PRODUCT_DIR/<slug>-client" --version 0.1.0 --output "$PRODUCT_DIR/<slug>-client"
```

**Check:**
- [ ] Server pushed to GitHub
- [ ] Client pushed to GitHub
- [ ] Pre-commit hooks installed (cả 2 repo)
- [ ] GitHub Actions workflow created (cả 2 repo)
- [ ] LICENSE, CONTRIBUTING, CODE_OF_CONDUCT created (cả 2 repo)
- [ ] Documentation organized under docs/ (cả 2 repo)
- [ ] [Nếu deploy] Server deployed to Render and accessible at URL
- [ ] [Nếu deploy] Client deployed to Netlify and accessible at URL
- [ ] Landing page generated (client)
- [ ] Release tagged v0.1.0 (cả 2 repo)

**Step Completion Report:**
```
◆ Ship Preparation (step 4 of 4)
······································································
  GitHub repos:         √ pass (2 repos created)
  CI/CD:                √ pass (.github/workflows/ ×2)
  Open source files:    √ pass (LICENSE, CONTRIBUTING ×2)
  Documentation:        √ pass (docs/ ×2)
  Deploy Render:        √ pass (hoặc N/A nếu không deploy)
  Deploy Netlify:       √ pass (hoặc N/A nếu không deploy)
  Landing page:         √ pass (client/landing)
  Release:              √ pass (v0.1.0 ×2)
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
  Phase 3  Build Product      √ approved (2 repos, runs locally)
  Phase 4  Ship Prep          √ pass  (pushed to GitHub)

  Parent:      $PRODUCT_DIR
  Server repo: <slug>-server  → http://localhost:8000  → GitHub
  Client repo: <slug>-client  → http://localhost:5173  → GitHub
  API docs:    http://localhost:8000/docs
  [Nếu deploy] Server production: https://<slug>-server.onrender.com
```

Final delivery summary file: `$PRODUCT_DIR/final-report.md` containing:

```markdown
# Final Report: <product-name>
*Generated: {date}*

## Summary
- **Idea**: <name> (validated <score>/100)
- **Stack**: FastAPI (server) + React/Vite/Tailwind (client) + SQLite
- **Version**: 0.1.0

## Repositories
| Repo | URL | Local path |
|------|-----|------------|
| Server | github.com/<user>/<slug>-server | <slug>-server/ |
| Client | github.com/<user>/<slug>-client | <slug>-client/ |

## What Was Built
- Server: <N> API routes, <N> database models
- Client: <N> pages, <N> components
- Tests: server <N>%, client <N>% coverage

## Quick Start
```bash
# Terminal 1 — Server
cd <slug>-server && make dev

# Terminal 2 — Client
cd <slug>-client && make dev
```

Open http://localhost:5173
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
