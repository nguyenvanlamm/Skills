---
name: idea-to-product
description: "End-to-end product builder from trend analysis to runnable code. Fetches trending topics, validates the best idea, generates PRD/architecture/tasks, builds a full-stack product (server + client as 2 separate GitHub repos), reviews code, adds tests, and prepares for shipping. Use when asked to build a product from scratch, turn a trend into a product, or go from idea to working app. Don't use for single-phase work — invoke the sibling skill directly."
license: MIT
effort: max
metadata:
  version: 2.1.0
  author: "Nguyen Van Lam"
---

# Idea to Product

4-phase orchestrator that takes trending topics and produces a runnable full-stack product — idea validation, product definition, implementation, and ship preparation.

Stack: FastAPI (Python) + React (Vite/Tailwind/shadcn/ui) + SQLite (local) / PostgreSQL (Render).

**Server và client là 2 project riêng biệt**, mỗi project là một GitHub repo độc lập để dễ dàng deploy và maintain.

## Cách gọi skill con

Các lệnh dạng `/skill-name --flag value` trong file này là **mô tả ý định**, không phải CLI thật. Trên mỗi host (Devin CLI, Claude Code, opencode) hãy gọi skill qua cơ chế của host (skill tool, `/name`, …) và truyền các giá trị đó trong prompt. Mỗi skill con có contract input/output riêng — bảng dưới ghi đúng contract đã đọc từ SKILL.md của chúng:

| Skill | Đọc (`$ARGUMENTS`) | Ghi |
|-------|-----|-----|
| `trend-ideas` | `output`, `output_dir` | `trend-report.md`, `ideas/…`, và `idea.md` + `validate.md` của idea thắng tại `output_dir` (v2.2+) |
| `idea-validator` | mô tả idea (chuỗi). **Không nhận thư mục output** — tự tạo `$IDEAS_ROOT/YYYY_MM_DD_<name>/` và echo path | `idea.md` + `validate.md` trong thư mục đó |
| `prd-generator` | **đường dẫn thư mục** chứa `idea.md` + `validate.md` — không nhận idea dạng chuỗi | `prd.md` cùng thư mục |
| `tad-generator` | đường dẫn thư mục chứa `prd.md` | `tad.md` cùng thư mục |
| `tasks-generator` | **đường dẫn file `prd.md`**; tự tìm `tad.md` cùng thư mục | `tasks.md` cạnh `prd.md` |

Vì vậy mọi file planning nằm **cùng một thư mục** `$PRODUCT_DIR/` — đừng đổi tên `tad.md` thành `architecture.md` hay tách thư mục, downstream tìm theo tên mặc định.

**"Repo Sync Before Edits" của bốn skill planning.** `idea-validator`, `prd-generator`, `tad-generator`, `tasks-generator` đều có bước bắt buộc `git fetch origin && git pull --rebase` trước khi ghi file, và **dừng hỏi user nếu thiếu `origin`**. `$PRODUCT_DIR` chỉ có remote từ Phase 4. Vì thế mỗi lần gọi skill planning, ghi rõ trong prompt: *"`$PRODUCT_DIR` là repo git local chưa có remote — bỏ qua Repo Sync, commit local được, không push."* Thiếu câu này, Phase 1–2 đứng giữa chừng chờ một câu trả lời không cần thiết.

**Kiểm tra skill có sẵn:** không dò đường dẫn. Trước mỗi phase, liệt kê skill phase đó cần; nếu host báo không có skill nào, dừng ở đầu phase và nêu tên — đừng chạy nửa phase rồi mới phát hiện.

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

### Required Skills

Các skill `deploy-*`, `firebase-auth-setup`, `trend-ideas` nằm trong repo này; phần còn lại là skill global.

All of these must be installed before starting:

| Skill | Version | Phase |
|-------|---------|-------|
| `trend-ideas` | 2.2.0+ | 1 |
| `idea-validator` | 1.2.0+ | 1 (được `trend-ideas` gọi; gọi trực tiếp khi user đưa idea sẵn) |
| `prd-generator` | 1.2.0+ | 2 |
| `tad-generator` | 1.2.0+ | 2 |
| `tasks-generator` | 1.2.0+ | 2 |
| `logo-designer` | 1.2.0+ | 3 |
| `frontend-design` | 1.2.0+ | 3 |
| `code-review` | 1.0.0+ | 3 |
| `test-coverage` | 1.2.0+ | 3 |
| `firebase-auth-setup` | 2.1.0+ | 3 (chỉ khi PRD có đăng nhập) |
| `devops-pipeline` | 1.0.0+ | 4 |
| `doc-manager` | 1.0.0+ | 4 (bản cũ ghi `docs-generator` — skill đó không tồn tại) |
| `deploy-render` | 2.0.0+ | 4 (nếu cần deploy server) |
| `deploy-netlify` | 2.0.0+ | 4 (nếu cần deploy client) |
| `oss-ready` | 1.1.0+ | 4 |
| `seo-ai-optimizer` | 1.0.0+ | 4 |
| `landing-page-generator` | 1.0.0+ | 4 |
| `release-manager` | 2.4.0+ | 4 |

### Install Command

```bash
npx skills add https://github.com/nguyenvanlamm/Skills --skill <skill-name>
```

Or install all at once:
```bash
npx skills add https://github.com/nguyenvanlamm/Skills
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
5. **Chốt tên GitHub repo** với user (mặc định `<slug>-server`, `<slug>-client`, private) — **chỉ ghi nhận**, chưa tạo. Tạo repo là hành động hướng ra ngoài, thuộc Phase 4 sau gate.
6. **Initialize git** trong từng project (`git init -b main`); commit đầu tiên chỉ sau khi Phase 3 có code — commit một thư mục rỗng không có giá trị.
7. **Verify prerequisite skills** cho Phase 1–2 (xem "Cách gọi skill con"). Thiếu thì dừng, nêu tên.
8. **Kiểm tra runtime + port** một lần, để lỗi lộ ra trước khi tốn 30 phút sinh code:
   ```bash
   python3 --version && node --version && npm --version && git config user.email
   for p in 8000 5173; do (command -v ss >/dev/null && ss -ltn | grep -q ":$p " || lsof -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1) && echo "port $p BUSY"; done
   ```
   Port bận → hỏi user giải phóng hoặc chốt port khác **ngay bây giờ**, và dùng port đó nhất quán trong Makefile, vite proxy và CORS ở Phase 3.

## Workflow

```
Phase 1 — Idea Generation  → trend-ideas + idea-validator
Phase 2 — Product Planning (GATE) → prd-generator + tad-generator + tasks-generator
Phase 3 — Build Product (GATE) → logo-designer + frontend-design + implement + code-review + test-coverage
Phase 4 — Ship Prep → devops-pipeline + doc-manager + oss-ready + seo-ai-optimizer + landing-page-generator + release-manager
```

Approval gates after Phase 1, 2, and 3: **must not advance** without explicit user approval.

**Và một gate trước Phase 4.** Phase 4 đẩy code lên GitHub, deploy site công khai, và cắt release — những việc hướng ra ngoài, khó rút lại, và đụng tới tài khoản thật của user. Trước khi bắt đầu Phase 4, liệt kê chính xác: repo nào sẽ được tạo (public hay private), URL nào sẽ công khai, tag nào sẽ được đẩy. Chờ user đồng ý. Đồng ý cho deploy không phải đồng ý cho release.

---

## Phase 1: Idea Generation & Validation

**Nếu user đã có idea** → bỏ qua `trend-ideas`: set `IDEAS_ROOT="$PRODUCT_DIR"`, gọi `idea-validator` với mô tả idea làm `$ARGUMENTS`. Nó tạo `$PRODUCT_DIR/YYYY_MM_DD_<name>/{idea.md,validate.md}` và echo path; copy hai file đó lên `$PRODUCT_DIR/` rồi sang gate.

Ngược lại, invoke `trend-ideas` to fetch trends, brainstorm 3 ideas, validate each via `idea-validator`, and select the winning idea:

```
/trend-ideas --output "$PRODUCT_DIR/trend-report.md" --output-dir "$PRODUCT_DIR"
```

**Output:**
- `$PRODUCT_DIR/trend-report.md` — top topics, 3 ideas with composite scores, winner
- `$PRODUCT_DIR/ideas/YYYY_MM_DD_<slug>/{idea.md,validate.md}` — mỗi idea một thư mục do `idea-validator` tạo
- **`$PRODUCT_DIR/idea.md` + `$PRODUCT_DIR/validate.md`** — cặp của idea thắng; đây là input thật của Phase 2

**Check:**
- [ ] trend-report.md exists
- [ ] `$PRODUCT_DIR/idea.md` và `validate.md` tồn tại và là của idea thắng (tên khớp report)
- [ ] `validate.md` có đủ 4 ratings (Creativity, Feasibility, Market Impact, Technical Execution) và Quick Verdict

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

If not approved, do not advance. User chọn idea khác trong `ideas/YYYY_MM_DD_…/` → copy cặp `idea.md`/`validate.md` đó lên `$PRODUCT_DIR/` rồi gate lại; hoặc re-run Phase 1.

---

## Phase 2: Product Definition

Cả ba skill đọc/ghi trong **`$PRODUCT_DIR/`** theo tên file mặc định của chúng. Truyền `$PRODUCT_DIR` làm project directory, không truyền nội dung.

### Step 2a: Generate PRD

```
/prd-generator "$PRODUCT_DIR"      ← $ARGUMENTS = thư mục chứa idea.md + validate.md → ghi prd.md
```

Thêm vào prompt ràng buộc stack của orchestrator này (FastAPI + React/Vite + SQLite/PostgreSQL, 2 repo, Firebase Auth nếu có đăng nhập) để PRD không đề xuất stack khác.

**Output:** `$PRODUCT_DIR/prd.md`.

### Step 2b: Generate Technical Architecture

```
/tad-generator "$PRODUCT_DIR"      ← $ARGUMENTS = thư mục chứa prd.md → ghi tad.md
```

**Output:** `$PRODUCT_DIR/tad.md` — data flow, component tree, API routes, DB schema. Giữ tên `tad.md`; `tasks-generator` tìm đúng tên này.

### Step 2c: Generate Tasks

```
/tasks-generator "$PRODUCT_DIR/prd.md"   ← $ARGUMENTS = đường dẫn FILE prd.md; tự thấy tad.md cùng thư mục → ghi tasks.md cạnh prd.md
```

**Output:** `$PRODUCT_DIR/tasks.md`.

**Check:**
- [ ] prd.md exists with features, user stories, success criteria, và stack khớp orchestrator
- [ ] tad.md exists with API routes, DB schema, component tree
- [ ] tasks.md exists with phased task breakdown
- [ ] Xác định `needs_auth` (PRD có register/login) và `needs_db` (PRD có dữ liệu bền vững) — ghi lại, Phase 3–4 dùng

**Step Completion Report:**
```
◆ Product Definition (step 2 of 4)
······································································
  PRD written:           √ pass (prd.md)
  Architecture doc:      √ pass (tad.md)
  Task breakdown:        √ pass (tasks.md — <N> tasks)
  Flags:                 needs_auth=<bool> needs_db=<bool>
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

### Step 3c: Firebase Auth Setup (chỉ khi `needs_auth`)

Khi PRD có yêu cầu register/login, **dùng Firebase Auth**. Không tự build JWT/hash password. Không có đăng nhập → bỏ qua bước này, ghi `N/A` trong report.

`firebase-auth-setup` tự kiểm tra prerequisites (`firebase-tools`, `gcloud`, `jq`, `gcloud auth`) trong `check-prereqs.sh` và dừng với hướng dẫn nếu thiếu — không cần kiểm tra lại ở đây. Lưu ý: tạo project Firebase **tốn quota** (~10–12 project/tài khoản); nếu user đã có project, truyền `--project-id` để dùng lại thay vì tạo mới.

```
/firebase-auth-setup --slug "<product-slug>" --output "$PRODUCT_DIR/firebase-config"
```

Sau khi chạy xong, đọc `$PRODUCT_DIR/firebase-config/firebase-output.json`:
- `project_id` → server `.env`: `FIREBASE_PROJECT_ID`
- `web_app.*` → client `.env`: `VITE_FIREBASE_*`
- `service_account.key_path` → server `.env`: `GOOGLE_APPLICATION_CREDENTIALS`
- **`auth_providers`** → quyết định UI login: chỉ sinh nút Google (`signInWithPopup`) khi mảng có `"google"`. Mặc định skill chỉ bật `email` — Google cần OAuth client mà API không tự tạo được. Sinh nút Google khi provider chưa bật là bug UI lộ ra ngay lần click đầu.

`firebase-config/` phải nằm trong `.gitignore` của **cả hai** repo (chứa service account key).

**Verify end-to-end** sau khi setup:
1. Server start: `make dev` → `GET /api/v1/health` 200
2. Client init Firebase không lỗi console
3. Login Email/Password trên client → gọi `GET /api/v1/auth/me` với ID token → 200 và trả về `uid`

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
│   └── ...              # Domain-specific routes per tad.md
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
- `database.py` đọc **`DATABASE_URL` từ env**, mặc định SQLite (template trong `references/tech-stack.md`). Nhờ vậy `deploy-render` không phải ghi đè file này khi chuyển sang PostgreSQL.
- All routes under prefix `/api/v1`
- CORS: đọc `ALLOWED_ORIGINS` từ env (mặc định `http://localhost:5173`), không hardcode `*`. Production URL của client được thêm vào ở Phase 4f **sau khi** biết URL Netlify.
- Health check at `GET /api/v1/health`
- `README.md` ghi rõ client repo URL + cách clone cả 2 để chạy fullstack
- Nếu `needs_auth`: `routes/auth.py` verify Firebase ID token bằng `firebase_admin.auth.verify_id_token`; `firebase_config.py` init `firebase_admin` với service account key. Nếu không: bỏ hai file này và `firebase-admin` khỏi requirements.

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
/doc-manager "$PRODUCT_DIR/<slug>-server"   → docs/ khớp code, mỗi claim trích path:line
/doc-manager "$PRODUCT_DIR/<slug>-client"
```

### Step 4d: Tạo repo và push lên GitHub

Tên repo và visibility đã chốt ở Setup và được user duyệt ở gate Phase 4. Với mỗi repo:

```bash
cd "$PRODUCT_DIR/<slug>-server"
git add -A && git commit -qm "feat: initial <product-name> server" || true
gh repo create "<user>/<slug>-server" --private --source=. --remote=origin --push
```

Trước khi push, xác nhận không có secret trong index: `git ls-files | grep -E '\.env$|service-account|firebase-config'` phải rỗng. Có → gỡ khỏi index, thêm `.gitignore`, và coi giá trị đó là đã lộ nếu repo từng public.

Nếu **có deploy** (4e/4f), có thể bỏ 4d: `deploy-render` và `deploy-netlify` tự tạo repo `<slug>-server` / `<slug>-client` và push. Chạy cả hai chỉ tạo commit "chore" thừa.

### Step 4e: Deploy Server to Render (nếu cần)

Dùng cờ `needs_db` từ Phase 2 (không đoán lại từ `models.py`):

```bash
/deploy-render --server-dir "$PRODUCT_DIR/<slug>-server" --slug "<slug>"          # needs_db
/deploy-render --server-dir "$PRODUCT_DIR/<slug>-server" --slug "<slug>" --no-db  # không có DB
```

Đọc `deploy-output.json`: chỉ dùng `url` khi **`verified: true`**. `url` rỗng hay `verified: false` → server chưa chạy, **không** deploy client trỏ vào nó; sửa server trước. Nhắc user: PostgreSQL free của Render **hết hạn sau 30 ngày** (skill con đã cảnh báo, nhắc lại ở final report).

### Step 4f: Deploy Client to Netlify (nếu có client)

```bash
API_URL=$(jq -r 'select(.verified==true) | .url // empty' "$PRODUCT_DIR/<slug>-server/deploy-output.json" 2>/dev/null)
/deploy-netlify --client-dir "$PRODUCT_DIR/<slug>-client" --slug "<slug>" ${API_URL:+--api-url "$API_URL"}
```

`--slug` là namespace **toàn cầu** của Netlify — `task-manager` gần chắc đã có người lấy; dùng slug đủ riêng.

Sau khi có URL Netlify: thêm nó vào `ALLOWED_ORIGINS` của server (env trên Render Dashboard hoặc `render.yaml`) và redeploy server, nếu không mọi request từ client production bị CORS chặn. Đây là bước hay bị quên nhất của Phase 4 — kiểm tra bằng một request thật từ URL Netlify tới `/api/v1/health`.

### Step 4g: Landing Page copy (client repo)

```
/landing-page-generator  (brief từ README client → copy PAS/AIDA/StoryBrand)
```

Skill này sinh **nội dung** (headline, hero, CTA, proof points), không sinh HTML. Lưu vào `$PRODUCT_DIR/<slug>-client/landing/copy.md`; muốn có trang thật thì đưa copy đó cho `frontend-design`, hoặc để user tự dựng.

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

- **Missing prerequisite skill**: Report the list of missing skills and stop at the start of the phase that needs them. Provide the install command.
- **trend-ideas fails to fetch trends**: script đã retry 3×; không scrape HTML (xem trend-ideas v2.2). Hỏi user đưa idea trực tiếp → nhánh "user đã có idea" ở Phase 1.
- **deploy-render `verified: false`**: không deploy client; đọc Dashboard log, sửa, chạy lại. Không ghi URL chưa verify vào final report.
- **Client production bị CORS**: `ALLOWED_ORIGINS` chưa có URL Netlify — xem 4f.
- **User disapproves at Phase 1 gate**: Ask which idea they prefer or if they want to re-run Phase 1.
- **User disapproves at Phase 2 gate**: Revise PRD/tasks per user feedback.
- **User disapproves at Phase 3 gate**: Fix specific issues before moving to Phase 4.
- **Build errors**: Stop, fix errors, re-verify before proceeding.
- **localhost ports 5173/8000 in use**: Detect and report. Ask user to free ports or use alternatives.
- **Python/Node not installed**: Report missing runtime and instructions to install.
- **npm install or pip install fails**: Check network, retry once. If still fails, note in report and stop.
