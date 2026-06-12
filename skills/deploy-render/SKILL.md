---
name: deploy-render
description: "Tự động deploy FastAPI server lên Render.com — sửa code hỗ trợ PostgreSQL, tạo Dockerfile, tạo GitHub repo, gọi Render API tạo database + deploy, trả về URL. Hỗ trợ --no-db cho server không cần database. Dùng khi cần deploy server lên production. Don't use for client-side deploy (Vercel/Netlify), non-FastAPI backends, or non-Render platforms."
license: MIT
effort: high
metadata:
  version: 1.1.0
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
| `--no-db` | No | false | Skip PostgreSQL setup (server không cần database) |

## Output

Sau khi chạy thành công, `$PRODUCT_DIR/deploy-output.json`:

### Với database (mặc định)
```json
{
  "url": "https://task-manager.onrender.com",
  "database_id": "db-xxx",
  "service_id": "srv-xxx",
  "repo_url": "https://github.com/user/task-manager-server",
  "status": "live",
  "has_db": true
}
```

### Không database (`--no-db`)
```json
{
  "url": "https://task-manager.onrender.com",
  "service_id": "srv-xxx",
  "repo_url": "https://github.com/user/task-manager-server",
  "status": "live",
  "has_db": false
}
```

## Workflow

### Step 1: Prepare Server Code

```bash
bash scripts/prepare-server.sh --server-dir <path> --slug <slug> [--no-db]
```

Với `--no-db`:
- Giữ nguyên `database.py` (SQLite mặc định)
- Không thêm `psycopg2-binary` vào requirements
- Không thêm auto-create tables vào `main.py`
- Sinh `render.yaml` không có database section
- Sinh `.env.production` không có DATABASE_URL

### Step 2: Push to GitHub

```bash
bash scripts/push-to-github.sh --server-dir <path> --slug <slug> [--gh-user <user>]
```

### Step 3: Deploy to Render

```bash
bash scripts/render-client.sh --slug <slug> --gh-user <user> [--no-db]
```

Với `--no-db`: bỏ qua bước tạo PostgreSQL, không set DATABASE_URL trong blueprint.

### Orchestrator

```bash
# Có database:
bash scripts/deploy.sh --server-dir <path> --slug <slug>

# Không database:
bash scripts/deploy.sh --server-dir <path> --slug <slug> --no-db
```

## Edge Cases

- **RENDER_API_KEY không có**: Báo lỗi + hướng dẫn lấy key
- **GitHub remote đã tồn tại**: Dùng remote hiện tại, skip create repo
- **Render API rate limit**: Retry sau 30s, tối đa 3 lần
- **Deploy fail (build error)**: Lấy log từ Render API, báo lỗi chi tiết
- **Free tier hết quota**: Báo lỗi, hướng dẫn upgrade
- **Region không support free PostgreSQL**: Fallback về `oregon`
- **`--no-db` mà có database.py**: Giữ nguyên database.py (vẫn dùng SQLite local), không ảnh hưởng
