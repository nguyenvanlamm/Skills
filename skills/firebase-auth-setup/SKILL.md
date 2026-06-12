---
name: firebase-auth-setup
description: "Tự động tạo Firebase project, bật Authentication (Email/Password + Google), tạo Web App config và Service Account key. Dùng khi sản phẩm cần đăng nhập qua Firebase Auth. Don't use for local-only auth (JWT + SQLite) or non-Firebase auth providers."
license: MIT
effort: medium
metadata:
  version: 1.0.0
  author: "Nguyen Van Lam"
---

# Firebase Auth Setup

Tự động tạo Firebase project, cấu hình Authentication providers, tạo web app và service account — không cần thao tác tay trên Firebase Console.

## When to Use

Trigger when:
- Một skill khác (VD: `idea-to-product`) cần Firebase Auth cho sản phẩm
- Cần auto-provision Firebase project + auth config từ CLI
- Cần lấy web app config + service account key để tích hợp

Do **not** use for:
- Auth local (JWT + SQLite) — không cần Firebase
- Dùng project Firebase đã có sẵn (skill này luôn tạo mới)
- Auth provider khác ngoài Email/Password và Google

## Prerequisites

### Required CLIs

| CLI | Install | Check |
|-----|---------|-------|
| `firebase-tools` | `npm install -g firebase-tools` | `firebase --version` |
| `gcloud` | `https://cloud.google.com/sdk/docs/install` | `gcloud --version` |
| `jq` | `apt install jq` / `brew install jq` | `jq --version` |

### Firebase CI Token (bắt buộc, chạy 1 lần)

```bash
firebase login:ci --no-localhost
# Copy token output, lưu vào ~/.config/firebase/ci-token
```

### Gcloud Auth

```bash
gcloud auth login
# Hoặc dùng service account:
gcloud auth activate-service-account --key-file=<path>
```

## Input Parameters

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `--slug` | Yes | — | Product slug (VD: `task-manager`). Dùng làm tên project. |
| `--output` | No | `$PWD/firebase-output` | Thư mục chứa output files. |
| `--region` | No | `us-central` | GCP region cho project. |

## Output

Sau khi chạy thành công, thư mục `--output` sẽ có:

```
<output>/
├── firebase-output.json       # Toàn bộ thông tin (project_id, web_config, service_account_path)
├── service-account-key.json   # Service account private key (secret, add to .gitignore)
└── firebase-web-config.json   # Web app config cho client
```

**firebase-output.json** schema:
```json
{
  "project_id": "task-manager-a1b2",
  "project_number": "123456789",
  "web_app": {
    "app_id": "1:123:web:abc",
    "api_key": "AIzaSy...",
    "auth_domain": "task-manager-a1b2.firebaseapp.com",
    "storage_bucket": "task-manager-a1b2.appspot.com",
    "messaging_sender_id": "123456789",
    "app_url": "https://task-manager-a1b2.web.app"
  },
  "service_account": {
    "email": "firebase-adminsdk-xxxx@task-manager-a1b2.iam.gserviceaccount.com",
    "key_path": "/abs/path/to/service-account-key.json"
  },
  "auth_providers": ["email", "google"]
}
```

## Workflow

### Step 1: Check Prerequisites

```bash
bash scripts/check-prereqs.sh
```

Kiểm tra `firebase`, `gcloud`, `jq` đã installed và CI token tồn tại. Nếu thiếu → báo lỗi + hướng dẫn cài đặt, dừng lại.

### Step 2: Create Firebase Project

```bash
bash scripts/create-project.sh --slug <slug> --output <output>
```

- Gọi `firebase projects:create` với tên `{slug}-{rand4}`
- Lưu `project_id` vào output

### Step 3: Enable Auth Providers

```bash
bash scripts/enable-auth.sh --project <project_id> --output <output>
```

- Bật Identity Toolkit API qua `gcloud services enable`
- Cấu hình Email/Password và Google sign-in qua Firebase Management REST API
- Cần CI token để gọi REST API

### Step 4: Create Web App

```bash
bash scripts/create-web-app.sh --project <project_id> --output <output>
```

- `firebase apps:create WEB <slug>`
- Lấy config object (apiKey, authDomain, appId, ...)
- Ghi ra `firebase-web-config.json` và `firebase-output.json`

### Step 5: Create Service Account + Key

```bash
bash scripts/create-service-account.sh --project <project_id> --project-number <number> --output <output>
```

- Tạo service account `firebase-adminsdk` qua `gcloud iam service-accounts create`
- Gán role `Firebase Admin SDK Administrator`
- Tạo và download key JSON

### Orchestrator

```bash
bash scripts/setup.sh --slug <slug> [--output <dir>] [--region <region>]
```

Chạy tuần tự 5 bước trên. Nếu bước nào fail → dừng, báo lỗi.

## Usage from other Skills

### Từ `idea-to-product`

Trong Phase 3 — Build Product, sau bước Frontend Scaffold, thêm:

```markdown
Nếu PRD yêu cầu authentication:
  1. /firebase-auth-setup --slug "<product-slug>" --output "$PRODUCT_DIR/firebase-config"
  2. Đọc $PRODUCT_DIR/firebase-config/firebase-output.json
  3. Server:
     - Thêm `firebase-admin` vào requirements.txt
     - Thêm `firebase_config.py` init firebase_admin với service account
     - `routes/auth.py` verify Firebase ID token (không hash password)
     - .env thêm FIREBASE_PROJECT_ID=<value>
  4. Client:
     - Thêm `firebase` vào package.json dependencies
     - Tạo `src/api/firebase.ts` init Firebase app
     - Login page dùng Firebase SDK signInWithPopup/signInWithEmailAndPassword
     - .env thêm VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, ...
```

### Từ skill khác

Gọi tương tự:
```markdown
/firebase-auth-setup --slug "<product-slug>" --output "<path>"
```

Output JSON chứa tất cả thông tin cần thiết để ghi vào .env và code.

## Edge Cases

- **firebase projects:create fail (name taken)**: Tự động thử lại với random suffix khác. Tối đa 3 lần.
- **CI token expired**: Báo lỗi + hướng dẫn chạy lại `firebase login:ci`.
- **gcloud không authenticated**: Báo lỗi + hướng dẫn `gcloud auth login`.
- **Project đã tồn tại**: Kiểm tra bằng `firebase projects:list`, nếu có rồi thì dùng project đó (ghi log warning).
- **REST API call fail**: Retry 1 lần, nếu vẫn fail thì báo lỗi + dừng.
