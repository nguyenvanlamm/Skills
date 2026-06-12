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

### Output

`netlify-output.json`:
```json
{
  "url": "https://<slug>.netlify.app",
  "site_id": "xxx-xxx",
  "site_name": "<slug>",
  "deploy_id": "yyy"
}
```

## Prerequisites

```bash
# Netlify token (1 lần)
echo "<token>" > ~/.config/netlify/token
chmod 600 ~/.config/netlify/token

# Netlify CLI
npm install -g netlify-cli

# GitHub CLI (nếu chưa có)
gh auth login
```

## Two Scenarios

| | Có server | Static site |
|--|-----------|-------------|
| `--api-url` | Required | Không cần |
| `VITE_API_URL` | Set trên Netlify env | Không set |
| netlify.toml | Có | Có |
| `_redirects` | Có (SPA) | Có (SPA) |

## Integration with idea-to-product

Phase 4, sau `deploy-render`:

```
# Nếu có server:
API_URL=$(jq -r '.url' $PRODUCT_DIR/deploy-output.json)
/deploy-netlify --client-dir "$PRODUCT_DIR/<slug>-client" --slug "<slug>" --api-url "$API_URL"

# Nếu không có server:
/deploy-netlify --client-dir "$PRODUCT_DIR/<slug>-client" --slug "<slug>"
```
