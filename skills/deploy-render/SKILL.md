---
name: deploy-render
description: "Tự động deploy FastAPI server lên Render.com — sửa code hỗ trợ PostgreSQL, tạo Dockerfile, tạo GitHub repo, gọi Render API tạo database + deploy, trả về URL. Dùng khi cần deploy server lên production. Don't use for client-side deploy (Vercel/Netlify), non-FastAPI backends, or non-Render platforms."
license: MIT
effort: high
metadata:
  version: 1.0.0
  author: "Nguyen Van Lam"
---

# Deploy Render

Tự động deploy FastAPI server từ `idea-to-product` lên Render.com — từ modify code đến deploy thành công URL thật, không cần vào Render Dashboard.

## When to Use

Trigger when:
- Cần deploy server FastAPI lên Render.com
- Sau Phase 3 (Build) của `idea-to-product`
- Muốn auto từ code → URL production

Do **not** use for:
- Client-side deploy (dùng Vercel / Netlify)
- Non-FastAPI backends
- Non-Render platforms

## Prerequisites

### Required CLIs / Tokens (chỉ cần setup 1 lần)

| Thứ | Cách lấy |
|-----|----------|
| `RENDER_API_KEY` | Render Dashboard → Account Settings → API Keys → Create |
| `gh` CLI + auth | `gh auth login` — thường đã có nếu dùng `idea-to-product` |
| `git` | Đã có |
| Render kết nối GitHub | Vào Render Dashboard → Settings → GitHub → Connect (1 lần) |

Lưu `RENDER_API_KEY` vào `~/.config/render/api-key`:
```bash
mkdir -p ~/.config/render
echo "<your-api-key>" > ~/.config/render/api-key
chmod 600 ~/.config/render/api-key
```

## Input Parameters

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `--server-dir` | Yes | — | Thư mục server project (VD: `$PRODUCT_DIR/task-manager-server`) |
| `--slug` | Yes | — | Product slug (VD: `task-manager`) |
| `--gh-user` | No | — | GitHub username. Nếu không có, đọc từ `gh auth status`. |

## Output

Sau khi chạy thành công, `$PRODUCT_DIR/deploy-output.json`:

```json
{
  "url": "https://task-manager.onrender.com",
  "database_url": "postgres://...",
  "service_id": "srv-xxx",
  "database_id": "db-xxx",
  "repo_url": "https://github.com/user/task-manager-server"
}
```

## Workflow

### Step 1: Prepare Server Code

```bash
bash scripts/prepare-server.sh --server-dir <path> --slug <slug>
```

- Modify `database.py` → đọc `DATABASE_URL` từ env, fallback SQLite local
- Add `psycopg2-binary`, `gunicorn` vào `requirements.txt`
- Tạo `Dockerfile`
- Tạo `entrypoint.sh` (wait DB → create tables → start gunicorn)
- Tạo `.dockerignore`
- Tạo `render.yaml` (Blueprint)
- Tạo `.env.production` mẫu

### Step 2: Push to GitHub

```bash
bash scripts/push-to-github.sh --server-dir <path> --slug <slug> [--gh-user <user>]
```

- Kiểm tra GitHub remote đã có chưa
- Nếu chưa: `gh repo create <slug>-server --private`
- `git add . && git commit -m "Add Dockerfile + Render config"`
- `git push -u origin main`

### Step 3: Deploy to Render

```bash
bash scripts/render-client.sh --server-dir <path> --slug <slug> [--gh-user <user>] [--output <dir>]
```

- Render API: tạo PostgreSQL database (free tier)
- Render API: sync Blueprint từ GitHub repo
- Render API: poll deploy đến khi `status = live`
- Render API: lấy URL service
- Ghi output JSON

### Orchestrator

```bash
bash scripts/deploy.sh --server-dir <path> --slug <slug> [--gh-user <user>] [--output <dir>]
```

Chạy tuần tự 3 bước. Nếu bước nào fail → dừng, báo lỗi.

## Render API Reference

Các endpoint sử dụng:

```
# Tạo PostgreSQL
POST https://api.render.com/v1/postgres
Authorization: Bearer <RENDER_API_KEY>
{ "name": "<slug>-db", "plan": "free", "region": "oregon", "version": "16" }

# Sync Blueprint
POST https://api.render.com/v1/blueprints/sync
{ "repoUrl": "https://github.com/<user>/<slug>-server", "branch": "main" }

# List services (lấy serviceId từ blueprint sync)
GET https://api.render.com/v1/services

# Poll deploy
GET https://api.render.com/v1/services/{serviceId}/deploys/{deployId}

# Get service URL
GET https://api.render.com/v1/services/{serviceId}
```

## Edge Cases

- **RENDER_API_KEY không có**: Báo lỗi + hướng dẫn lấy key
- **GitHub remote đã tồn tại**: Dùng remote hiện tại, skip create repo
- **Render API rate limit**: Retry sau 30s, tối đa 3 lần
- **Deploy fail (build error)**: Lấy log từ Render API, báo lỗi chi tiết
- **Free tier hết quota**: Báo lỗi, hướng dẫn upgrade
- **Region không support free PostgreSQL**: Fallback về `oregon`
