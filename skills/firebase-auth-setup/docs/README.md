# Firebase Auth Setup Skill

## Overview

Tự động tạo Firebase project, cấu hình Authentication (Email/Password + Google), tạo Web App config và Service Account key — không cần thao tác tay trên Firebase Console.

## Usage

```bash
/firebase-auth-setup --slug <product-slug> [--output <dir>] [--google-client-id <id> --google-client-secret <secret>]
/firebase-auth-setup --project-id <existing-project> [--output <dir>]
```

### Parameters

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `--slug` | Yes* | — | Product slug (VD: `task-manager`). *Not needed with `--project-id` |
| `--project-id` | No | — | Reuse an existing project (quota-friendly) |
| `--output` | No | `$PWD/firebase-output` | Output directory |
| `--region` | No | `us-central` | Recorded in output only |
| `--google-client-id/-secret` | No | — | Enables Google sign-in; without them `auth_providers` is `["email"]` |

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
- **jq**, **curl**
- `gcloud auth login` and `firebase login` (ambient auth — no CI token needed)

## Integration with idea-to-product

Trong Phase 3 — Build Product, nếu PRD yêu cầu authentication:

```
/firebase-auth-setup --slug "<slug>" --output "$PRODUCT_DIR/firebase-config"
```

Sau đó đọc `firebase-output.json` và ghi vào `.env` của server và client.

## Edge Cases

- **Project name taken**: Tự động retry với random suffix khác (tối đa 3 lần)
- **Identity Platform not initialised**: script calls `initializeAuth` itself; manual "Get started" only if that fails
- **Existing project**: pass `--project-id`; Firebase is added to a plain GCP project automatically
- **No OAuth client**: Google sign-in skipped and said so; `auth_providers` reflects reality
