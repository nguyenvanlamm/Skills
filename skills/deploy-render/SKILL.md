---
name: deploy-render
description: "Tự động deploy FastAPI server lên Render.com — sửa code hỗ trợ PostgreSQL, tạo Dockerfile, tạo GitHub repo, gọi Render API tạo database + deploy, verify URL. Hỗ trợ --no-db cho server không cần database. Dùng khi cần deploy server lên production. Don't use for client-side deploy (Vercel/Netlify), non-FastAPI backends, or non-Render platforms."
license: MIT
effort: high
metadata:
  version: 2.0.0
  author: "Nguyen Van Lam"
---

# Deploy Render

Deploy một FastAPI server lên Render.com: sửa code cho PostgreSQL, sinh Dockerfile + `render.yaml`, tạo repo GitHub, gọi Render API, và **kiểm chứng service thật sự trả lời**.

## Nguyên tắc

> **Trạng thái `live` của Render không có nghĩa là app chạy.** Build thành công vẫn có thể crash lúc khởi động. Script luôn `curl` vào `/docs` sau khi deploy, ghi `verified` vào output, và `exit 2` nếu không verify được — không in "hoàn tất" cho một deploy hỏng.

Hệ quả thứ hai: **không bịa URL**. Bản cũ khi không lấy được URL từ API thì đoán `https://<slug>-server.onrender.com` rồi ghi vào output — mà `deploy-netlify` lại lấy đúng giá trị đó làm `--api-url`, tức client trỏ vào hư không. Giờ không lấy được URL thì để rỗng và báo chưa verify.

## Cảnh báo free tier — đọc trước khi dùng thật

| Thứ | Giới hạn |
|-----|----------|
| **PostgreSQL free** | **Hết hạn sau 30 ngày** kể từ khi tạo. Có 14 ngày ân hạn để nâng cấp; hết ân hạn Render **xoá database và toàn bộ dữ liệu**. |
| **Web service free** | Ngủ khi không có traffic. Request đầu sau khi ngủ mất vài giây tới ~1 phút — nên timeout verify để 90 giây. |

Nói điều này với user **trước** khi họ đưa dữ liệu thật vào. Một database biến mất sau 30 ngày là hành vi đúng thiết kế của Render, không phải sự cố.

## Chuẩn bị

| Thứ | Cách lấy |
|-----|----------|
| `RENDER_API_KEY` | Render Dashboard → Account Settings → API Keys → Create |
| `gh` đã auth | `gh auth login` |
| Render ↔ GitHub | Render Dashboard → Settings → GitHub → Connect (một lần) |

```bash
mkdir -p ~/.config/render
echo "<api-key>" > ~/.config/render/api-key && chmod 600 ~/.config/render/api-key
```

Cần `curl` và `jq`. Script kiểm tra và dừng ngay nếu thiếu.

## Tham số

| Param | Bắt buộc | Mặc định | Mô tả |
|-------|----------|----------|-------|
| `--server-dir` | ✅ | — | Thư mục server |
| `--slug` | ✅ | — | Tên product; service là `<slug>-server`, db là `<slug>-db` |
| `--gh-user` | ❌ | `gh api user` | GitHub account |
| `--no-db` | ❌ | false | Bỏ qua PostgreSQL, giữ SQLite |
| `--region` | ❌ | `oregon` | Region Render |
| `--health-path` | ❌ | `/docs` | Đường dẫn dùng để verify |

## Chạy

```bash
bash scripts/deploy.sh --server-dir <path> --slug <slug> [--no-db]
```

| Script | Việc |
|--------|------|
| `prepare-server.sh` | PostgreSQL driver, Dockerfile, `render.yaml`, `.env.production` |
| `push-to-github.sh` | `git init` nếu cần, gitignore file env, tạo repo, push đúng branch |
| `render-client.sh` | Tạo/tìm database + service, deploy, poll, verify, ghi output |

Với `--no-db`: giữ `database.py` dùng SQLite, không thêm `psycopg2-binary`, `render.yaml` không có database, không set `DATABASE_URL`.

## Điểm yếu đã biết: Blueprint API

Bước tạo service đi qua `POST /v1/blueprints/sync`. Đây là phần **kém ổn định nhất** của luồng này, và hình dạng response không được tài liệu hoá rõ ràng — bản cũ xử lý bằng cách đoán qua năm dạng JSON khác nhau rồi im lặng đi tiếp khi cả năm đều trượt.

Bản này làm ngược lại: nếu blueprint sync không trả về service, script tìm service theo tên; vẫn không thấy thì **dừng và nói thẳng phải làm gì**:

> Tạo service một lần từ Dashboard (New → Blueprint, chọn repo). Sau đó script tìm thấy nó theo tên và mọi lần chạy sau đều hoạt động.

Đó là một bước thủ công một lần, và nói ra thì hữu ích hơn là giả vờ đã tự động hoá được.

## Output

`deploy-output.json`:

```json
{
  "url": "https://task-manager-server.onrender.com",
  "service_id": "srv-...",
  "deploy_id": "dep-...",
  "database_id": "dpg-...",
  "database_status": "created",
  "repo_url": "https://github.com/user/task-manager-server",
  "status": "live",
  "http_code": "200",
  "has_db": true,
  "verified": true
}
```

Chỉ dùng `url` ở downstream (ví dụ `deploy-netlify --api-url`) khi `verified: true`. `url` rỗng nghĩa là Render không trả về hostname — không có gì để trỏ tới.

## Edge cases

| Tình huống | Xử lý |
|-----------|-------|
| Thiếu `RENDER_API_KEY` | Dừng, hướng dẫn lấy key |
| Thiếu `curl`/`jq` | Dừng ngay, nêu tên lệnh |
| HTTP 429 hoặc 5xx | Retry 30s, tối đa 3 lần, rồi dừng kèm response |
| Database đã tồn tại | Dùng lại, `database_status: existing` |
| Blueprint sync không ra service | Tìm theo tên; không thấy thì dừng kèm hướng dẫn Dashboard |
| Build fail | In message + link log Dashboard, exit 2 |
| Poll quá 15 phút | `status: timeout`, exit 2 |
| Deploy `live` nhưng HTTP ≠ 200 | `verified: false`, exit 2 |
| Không lấy được URL | Để rỗng, không đoán |
| Chưa `git init` | Tự init `-b main` |
| Branch không phải `main` | Push đúng branch hiện tại |

## Không làm

Deploy client (`deploy-netlify`); backend không phải FastAPI; nền tảng khác; nâng cấp plan; cấu hình custom domain; và **không** cứu được database free đã quá hạn ân hạn — dữ liệu đã bị xoá.
