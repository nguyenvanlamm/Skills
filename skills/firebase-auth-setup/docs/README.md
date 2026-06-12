# Firebase Auth Setup Skill

## Overview

Tự động tạo Firebase project, cấu hình Authentication (Email/Password + Google), tạo Web App config và Service Account key — không cần thao tác tay trên Firebase Console.

## Usage

```bash
/firebase-auth-setup --slug <product-slug> [--output <dir>] [--region <region>]
```

### Parameters

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `--slug` | Yes | — | Product slug (VD: `task-manager`) |
| `--output` | No | `$PWD/firebase-output` | Output directory |
| `--region` | No | `us-central` | GCP region |

### Output

```
<output>/
├── firebase-output.json         # All config in one place
├── firebase-web-config.json     # Web app config (for client .env)
└── service-account-key.json     # 🔒 Service account private key
```

## Prerequisites

- **firebase-tools**: `npm install -g firebase-tools`
- **gcloud CLI**: https://cloud.google.com/sdk/docs/install
- **jq**: `apt install jq` or `brew install jq`
- **Firebase CI token**: Run `firebase login:ci --no-localhost` once

## Integration with idea-to-product

Trong Phase 3 — Build Product, nếu PRD yêu cầu authentication:

```
/firebase-auth-setup --slug "<slug>" --output "$PRODUCT_DIR/firebase-config"
```

Sau đó đọc `firebase-output.json` và ghi vào `.env` của server và client.

## Edge Cases

- **Project name taken**: Tự động retry với random suffix khác (tối đa 3 lần)
- **CI token expired**: Báo lỗi + hướng dẫn chạy lại `firebase login:ci`
- **Existing project**: Nếu project đã tồn tại, dùng lại (ghi log warning)
