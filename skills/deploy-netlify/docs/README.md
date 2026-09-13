# Deploy Netlify Skill

## Overview

Tự động deploy React client lên Netlify — thêm config, push GitHub, tạo site + deploy. Hỗ trợ cả 2 trường hợp: có server API hoặc static site thuần.

## Usage

```bash
# Có server backend:
/deploy-netlify --client-dir <path> --slug <slug> --api-url <server-url>

# Static site (không cần server):
/deploy-netlify --client-dir <path> --slug <slug>
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `--client-dir` | Yes | Thư mục client project |
| `--slug` | Yes | Product slug |
| `--api-url` | No | URL server production (nếu có) |
| `--gh-user` | No | GitHub username (auto-detected) |
| `--public` | No | Public GitHub repo (default private) |
| `--skip-github` | No | Deploy only, no GitHub repo |
| `--output` | No | Where to write `netlify-output.json` |

### Output

`netlify-output.json`:
```json
{
  "url": "https://<slug>.netlify.app",
  "site_id": "xxx-xxx",
  "site_name": "<slug>",
  "deploy_id": "yyy",
  "deploy_preview_url": "https://yyy--<slug>.netlify.app",
  "verified": true
}
```

`verified: false` → exit code 2. Only consume `url` downstream when `verified` is true.

```
```

## Prerequisites

```bash
# Netlify token (1 lần)
echo "<token>" > ~/.config/netlify/token
chmod 600 ~/.config/netlify/token

# GitHub CLI (nếu chưa có)
gh auth login
```

## Two Scenarios

| | Có server | Static site |
|--|-----------|-------------|
| `--api-url` | Required | Không cần |
| `VITE_API_URL` | Baked into the bundle at local build time from `.env.production` (also mirrored to Netlify env for a possible future repo link) | Không set |
| netlify.toml | Có | Có |
| `_redirects` | Có (SPA) | Có (SPA) |

## Integration with idea-to-product

Phase 4, sau `deploy-render`:

```
# Nếu có server:
API_URL=$(jq -r 'select(.verified==true) | .url // empty' $PRODUCT_DIR/<slug>-server/deploy-output.json)
/deploy-netlify --client-dir "$PRODUCT_DIR/<slug>-client" --slug "<slug>" --api-url "$API_URL"

# Nếu không có server:
/deploy-netlify --client-dir "$PRODUCT_DIR/<slug>-client" --slug "<slug>"
```
