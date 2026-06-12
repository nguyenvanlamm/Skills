---
name: deploy-netlify
description: "Tự động deploy React client lên Netlify — thêm netlify.toml, push GitHub, tạo site + deploy. Hỗ trợ cả 2 trường hợp: có server API hoặc không cần server. Don't use for server deploy (use deploy-render), non-React projects, or non-Netlify platforms."
license: MIT
effort: medium
metadata:
  version: 1.0.0
  author: "Nguyen Van Lam"
---

# Deploy Netlify

Tự động deploy React client từ `idea-to-product` lên Netlify — từ prepare code đến URL production, không cần Dashboard.

## When to Use

Trigger when:
- Cần deploy client React lên Netlify
- Sau Phase 3 (Build) của `idea-to-product`
- Có hoặc không có server backend

Do **not** use for:
- Server deploy (dùng `deploy-render`)
- Non-React / non-Vite projects
- Non-Netlify platforms

## Prerequisites

### Auth (cần setup 1 lần)

```bash
echo "<token>" > ~/.config/netlify/token
chmod 600 ~/.config/netlify/token
```

Lấy token: Netlify Dashboard → User Settings → Applications → Personal access tokens → Generate

### CLIs

| CLI | Cài đặt |
|-----|---------|
| `netlify-cli` | `npm install -g netlify-cli` |
| `gh` | `gh auth login` (nếu chưa có) |

## Input Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `--client-dir` | Yes | Thư mục client project |
| `--slug` | Yes | Product slug (VD: `task-manager`) |
| `--api-url` | No | URL server production (nếu có backend) |
| `--gh-user` | No | GitHub username (auto nếu bỏ qua) |

## Output

`$PRODUCT_DIR/netlify-output.json`:

```json
{
  "url": "https://task-manager.netlify.app",
  "site_id": "xxx-xxx-xxx",
  "site_name": "task-manager",
  "deploy_id": "yyy"
}
```

## Workflow

### Step 1: Prepare Client Code

Thêm config cho Netlify:
- `netlify.toml` — build command, publish directory, env
- `_redirects` — SPA fallback (`/* /index.html 200`)
- `.env.production` — `VITE_API_URL` (nếu có `--api-url`)

### Step 2: Push to GitHub

- Tạo GitHub repo (nếu chưa có)
- Commit + push code

### Step 3: Deploy to Netlify

```bash
# 1. Create site
netlify api createSite -d "{\"name\":\"$SLUG\",\"ssl\":true}"

# 2. Set env vars (nếu có api-url)
netlify api updateEnvVars -d "{\"key\":\"VITE_API_URL\",\"value\":\"$API_URL\",\"scopes\":[\"builds\",\"functions\"]}"

# 3. Build & deploy
cd $CLIENT_DIR && npm run build
netlify deploy --dir=dist --prod --site=$SITE_ID
```

### Orchestrator

```bash
bash scripts/deploy.sh \
  --client-dir <path> \
  --slug <slug> \
  [--api-url <url>] \
  [--gh-user <user>]
```

## Edge Cases

- **NETLIFY_AUTH_TOKEN missing**: Báo lỗi + hướng dẫn lấy token
- **Site name đã tồn tại**: Netlify API tự sinh tên khác, ghi log
- **Build fails**: Hiển thị log lỗi build, dừng
- **`--api-url` không có**: Bỏ qua env var, deploy static site thuần
- **GitHub remote đã tồn tại**: Dùng remote hiện có
