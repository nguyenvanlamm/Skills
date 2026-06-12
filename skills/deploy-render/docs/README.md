# Deploy Render Skill

## Overview

Tự động deploy FastAPI server lên Render.com — từ sửa code, push GitHub, tạo database, tới deploy thành công URL.

## Usage

```bash
/deploy-render --server-dir <path> --slug <slug> [--gh-user <user>] [--output <dir>]
```

### Parameters

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `--server-dir` | Yes | — | Thư mục server project |
| `--slug` | Yes | — | Product slug (VD: `task-manager`) |
| `--gh-user` | No | auto | GitHub username |
| `--output` | No | server-dir | Output directory cho `deploy-output.json` |

### Output

`deploy-output.json`:
```json
{
  "url": "https://task-manager-server.onrender.com",
  "database_id": "db-xxx",
  "service_id": "srv-xxx",
  "repo_url": "https://github.com/user/task-manager-server",
  "status": "live"
}
```

## Prerequisites

- **RENDER_API_KEY**: Render Dashboard → Account Settings → API Keys
- **gh CLI**: `gh auth login`
- **Render kết nối GitHub**: Settings → GitHub → Connect (1 lần)

Lưu key:
```bash
echo "<api-key>" > ~/.config/render/api-key
chmod 600 ~/.config/render/api-key
```

## Workflow

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `prepare-server.sh` | Sửa database.py → PostgreSQL, thêm Dockerfile, entrypoint, render.yaml |
| 2 | `push-to-github.sh` | Tạo GitHub repo (nếu chưa có), commit & push |
| 3 | `render-client.sh` | Render API: tạo DB, sync blueprint, poll deploy, lấy URL |

## Integration with idea-to-product

Thêm vào Phase 4 — Ship Preparation:

```
/deploy-render --server-dir "$PRODUCT_DIR/<slug>-server" --slug "<slug>"
→ ✅ Deployed at https://<slug>-server.onrender.com
```

## Chú ý

- Render free tier: service sleep sau 15 phút không dùng, tự wake khi có request (chậm ~30s)
- Free PostgreSQL: 1GB, expire sau 90 ngày
- Nếu deploy thất bại, log build hiện trong Render Dashboard → Service → Events
