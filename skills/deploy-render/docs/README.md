# Deploy Render Skill

## Overview

Tự động deploy FastAPI server lên Render.com — từ sửa code, push GitHub, tạo database, tới deploy thành công URL.

## Usage

```bash
# Có database:
/deploy-render --server-dir <path> --slug <slug>

# Không cần database:
/deploy-render --server-dir <path> --slug <slug> --no-db
```

### Parameters

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `--server-dir` | Yes | — | Thư mục server project |
| `--slug` | Yes | — | Product slug (VD: `task-manager`) |
| `--gh-user` | No | auto | GitHub username |
| `--output` | No | server-dir | Output directory cho `deploy-output.json` |
| `--no-db` | No | false | Skip PostgreSQL setup (server không cần database) |
| `--public` | No | private | Public GitHub repo |
| `--region` | No | oregon | Render region (service + database) |
| `--health-path` | No | /docs | Route to verify; also `healthCheckPath` in render.yaml |

### Output

`deploy-output.json`:
```json
{
  "url": "https://task-manager-server.onrender.com",
  "service_id": "srv-xxx",
  "deploy_id": "dep-xxx",
  "database_id": "dpg-xxx",
  "database_status": "created",
  "repo_url": "https://github.com/user/task-manager-server",
  "status": "live",
  "http_code": "200",
  "has_db": true,
  "verified": true
}
```

Only consume `url` downstream when `verified` is true; `url` is empty (never guessed) when Render did not return one. Exit code 2 when not verified.

```
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
→ deploy-output.json với url + verified; chỉ dùng url khi verified=true
```

## Chú ý

- Render free tier: service sleep khi không có traffic, tự wake khi có request (request đầu có thể mất tới ~1 phút)
- **Free PostgreSQL hết hạn sau 30 ngày** kể từ khi tạo, 14 ngày ân hạn, sau đó Render xoá database và toàn bộ dữ liệu. (Bản README cũ ghi 90 ngày — sai.)
- Nếu deploy thất bại, log build hiện trong Render Dashboard → Service → Events
