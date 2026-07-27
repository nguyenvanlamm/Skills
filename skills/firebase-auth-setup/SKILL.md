---
name: firebase-auth-setup
description: "Tự động tạo Firebase project, bật Email/Password Authentication, tạo Web App config và Service Account key. Google sign-in cần OAuth client riêng. Dùng khi sản phẩm cần đăng nhập qua Firebase Auth. Don't use for local-only auth (JWT + SQLite) or non-Firebase auth providers."
license: MIT
effort: medium
metadata:
  version: 2.0.0
  author: "Nguyen Van Lam"
---

# Firebase Auth Setup

Provision một Firebase project, bật Authentication, tạo web app config và service account — hạn chế tối đa thao tác tay trên Console.

## Nguyên tắc

> **Output chỉ ghi những gì thật sự bật được.** Bản cũ ghi `auth_providers: ["email","google"]` ngay lúc tạo project, **trước** khi bước bật provider chạy — nên output nói Google đã bật kể cả khi bước đó thất bại, và code sinh ra ở downstream tin theo. Giờ danh sách provider được ghi sau khi cấu hình, chỉ gồm những cái trả về 200.

## Google sign-in: cần OAuth client, không tự tạo được

Đây là điểm quan trọng nhất và bản cũ nói sai. Google **không phải** một cờ bật/tắt trong config — nó là federated IdP, cần **OAuth 2.0 client ID + secret**, mà API này không tạo ra được. Bản cũ gọi `PATCH /config` với `{"signInProviders":{"google":true}}`, một field không tồn tại trong Identity Platform API, rồi coi như đã bật.

Hai đường đi thật:

```bash
# Đã có OAuth client:
bash scripts/enable-auth.sh --project <id> --output <dir> \
  --google-client-id <id> --google-client-secret <secret>
```

Tạo client tại Google Cloud Console → APIs & Services → Credentials → OAuth client ID (Web application).

Hoặc bật trong Firebase Console → Authentication → Sign-in method → Google — Console tự tạo client. Một thao tác tay, một lần.

Không truyền client thì script **bỏ qua Google, nói rõ lý do**, và `auth_providers` chỉ có `email`.

## Chuẩn bị

| CLI | Cài |
|-----|-----|
| `firebase-tools` | `npm install -g firebase-tools` |
| `gcloud` | https://cloud.google.com/sdk/docs/install |
| `jq`, `curl` | `apt install jq` / `brew install jq` |

```bash
gcloud auth login
firebase login
```

Không cần `firebase login:ci` — script dùng ambient auth. Token CI vốn được đọc ở bản cũ nhưng **không dùng vào việc gì**; phần đó đã bỏ.

**Hạn mức project:** tài khoản Google Cloud thường bị giới hạn ~10–12 project. Mỗi lần chạy skill này tạo **một project mới** — dùng nhiều lần sẽ chạm trần và phải xoá project cũ (xoá xong còn 30 ngày chờ mới giải phóng quota).

## Tham số

| Param | Bắt buộc | Mặc định | Mô tả |
|-------|----------|----------|-------|
| `--slug` | ✅ | — | Tên project; phải hợp lệ làm GCP project id |
| `--output` | ❌ | `$PWD/firebase-output` | Thư mục output |
| `--region` | ❌ | `us-central` | Region |
| `--google-client-id` | ❌ | — | OAuth client cho Google sign-in |
| `--google-client-secret` | ❌ | — | Kèm theo client id |

`--slug` sinh ra project id `<slug>-<rand4>`, phải khớp luật GCP: **6–30 ký tự, bắt đầu bằng chữ thường, chỉ a-z 0-9 và `-`**. Script kiểm tra trước khi gọi API thay vì để API trả lỗi khó hiểu.

## Chạy

```bash
bash scripts/setup.sh --slug <slug> [--output <dir>] [--region <region>]
```

| Script | Việc |
|--------|------|
| `check-prereqs.sh` | Kiểm tra CLI và auth |
| `create-project.sh` | Tạo project, validate id, retry khi trùng tên |
| `enable-auth.sh` | Bật Identity Toolkit, Email/Password, Google (nếu có client) |
| `create-web-app.sh` | Tạo web app, lấy config |
| `create-service-account.sh` | Tạo service account + key |

## Output

```
<output>/
├── firebase-output.json
├── firebase-web-config.json
└── service-account-key.json     ← SECRET
```

```json
{
  "project_id": "task-manager-a1b2",
  "project_number": "123456789",
  "web_app": { "app_id": "...", "api_key": "...", "auth_domain": "..." },
  "service_account": { "email": "...", "key_path": "/abs/path/..." },
  "auth_providers": ["email"]
}
```

`auth_providers` phản ánh trạng thái thật. Code sinh ra ở downstream phải đọc field này, không giả định có Google.

## Xử lý credential

`service-account-key.json` là **khoá riêng có quyền admin** trên Firebase project: đọc/ghi mọi dữ liệu, tạo custom token, mạo danh bất kỳ user nào. Không có cơ chế thu hồi nào ngoài việc xoá khoá.

Bắt buộc, ngay sau khi chạy:

```bash
echo "service-account-key.json" >> .gitignore
echo "firebase-output.json"     >> .gitignore   # chứa key_path và api_key
chmod 600 <output>/service-account-key.json
```

Lộ khoá thì xoá nó đi, đừng chỉ gỡ khỏi repo:

```bash
gcloud iam service-accounts keys delete <key-id> --iam-account=<sa-email>
```

`api_key` trong web config **không phải** secret — nó nằm trong bundle client và Firebase thiết kế như vậy. Bảo mật đến từ Security Rules và App Check, không đến từ việc giấu api key.

## Tích hợp

Từ `idea-to-product` Phase 3, khi PRD yêu cầu auth:

```bash
/firebase-auth-setup --slug "<product-slug>" --output "$PRODUCT_DIR/firebase-config"
```

Rồi đọc `firebase-output.json`:

- **Server**: `firebase-admin` vào requirements, init bằng service account, route verify ID token (không tự hash password), `.env` thêm `FIREBASE_PROJECT_ID`
- **Client**: `firebase` vào package.json, `src/api/firebase.ts`, login dùng `signInWithEmailAndPassword`; chỉ thêm `signInWithPopup` khi `auth_providers` có `google`

## Edge cases

| Tình huống | Xử lý |
|-----------|-------|
| Thiếu CLI hoặc chưa auth | Dừng, hướng dẫn |
| Slug không hợp lệ làm project id | Dừng trước khi gọi API, nêu luật |
| Tên project đã bị chiếm | Đổi suffix ngẫu nhiên, tối đa 3 lần |
| Hết quota project | Lỗi từ GCP; phải xoá project cũ |
| Identity Platform chưa khởi tạo | HTTP lỗi ở bước Email/Password — mở Console → Authentication → Get started một lần rồi chạy lại |
| Không có OAuth client | Bỏ qua Google, ghi rõ, `auth_providers: ["email"]` |
| Google IdP đã tồn tại | Chuyển từ POST sang PATCH |

## Không làm

Dùng lại project Firebase có sẵn (luôn tạo mới); provider ngoài Email/Password và Google; Firestore, Storage, Hosting, App Check; và **không** tạo được OAuth client cho Google.
