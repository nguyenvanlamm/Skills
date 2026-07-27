---
name: deploy-netlify
description: "Tự động deploy React/Vite client lên Netlify — thêm netlify.toml, push GitHub, tạo site + deploy + verify. Hỗ trợ cả 2 trường hợp: có server API hoặc không cần server. Don't use for server deploy (use deploy-render), non-Vite projects, or non-Netlify platforms."
license: MIT
effort: medium
metadata:
  version: 2.0.0
  author: "Nguyen Van Lam"
---

# Deploy Netlify

Deploy một client Vite/React lên Netlify: chuẩn bị config, đẩy source lên GitHub, tạo site, deploy, và **kiểm chứng URL thật sự trả về 200**.

## Nguyên tắc

> **Deploy chỉ được coi là xong khi URL trả về 200.** API nhận file không có nghĩa là site chạy. Script luôn `curl` lại URL cuối và ghi `verified` vào output — deploy không verify được thì `exit 2`, không báo thành công.

## Khi nào dùng

Dùng khi: cần deploy client Vite/React lên Netlify, thường sau Phase 3 của `idea-to-product`, có hoặc không có backend.

Không dùng cho: deploy server (`deploy-render`), project không phải Vite, nền tảng khác.

## Chuẩn bị

**Token** (một lần):

```bash
echo "<token>" > ~/.config/netlify/token && chmod 600 ~/.config/netlify/token
```

Lấy tại Netlify Dashboard → User settings → Applications → Personal access tokens. Script cũng chấp nhận biến môi trường `NETLIFY_AUTH_TOKEN`, hoặc `NETLIFY_TOKEN_PATH` nếu để token ở chỗ khác.

**CLI cần có:** `curl`, `jq`, `npm`, `gh` (đã `gh auth login`). `netlify-cli` không cần cài sẵn — script gọi qua `npx --yes`.

## Tham số

| Param | Bắt buộc | Mô tả |
|-------|----------|-------|
| `--client-dir` | ✅ | Thư mục project client |
| `--slug` | ✅ | Tên site, **duy nhất trên toàn Netlify** |
| `--api-url` | ❌ | URL server production, nếu có backend |
| `--gh-user` | ❌ | GitHub account; mặc định lấy từ `gh api user` |
| `--output` | ❌ | Nơi ghi `netlify-output.json`; mặc định `--client-dir` |

`--slug` là namespace toàn cầu của Netlify, không phải của riêng tài khoản. `task-manager` gần như chắc chắn đã có người lấy — dùng tên cụ thể hơn (`acme-task-manager`). Script tìm site trùng tên trong tài khoản trước, chỉ tạo mới khi không thấy, và **báo lỗi rõ ràng** khi tên đã bị người khác chiếm thay vì im lặng nhận một site tên khác.

## Chạy

```bash
bash scripts/deploy.sh --client-dir <path> --slug <slug> [--api-url <url>] [--gh-user <user>]
```

Ba bước, chạy độc lập được:

| Script | Việc |
|--------|------|
| `scripts/prepare-client.sh` | `netlify.toml`, `public/_redirects`, `.env.production` |
| `scripts/push-to-github.sh` | `git init` nếu cần, gitignore file env, tạo repo, push |
| `scripts/netlify-client.sh` | Tạo/tìm site, mirror env var, build, deploy, verify |

## Env var hoạt động thế nào

Chỗ này dễ hiểu nhầm nên nói rõ:

**Build chạy ở máy local**, rồi `netlify deploy --dir=dist` chỉ upload thư mục đã build. Vite nhúng `VITE_API_URL` vào bundle **lúc build**, lấy từ `.env.production` ở local. Đó mới là giá trị thật sự đến trình duyệt.

Env var đặt trên Netlify chỉ có tác dụng cho build chạy **trên** Netlify — luồng này không có. Script vẫn mirror giá trị lên site config để phòng khi sau này liên kết repo cho continuous deploy, nhưng nếu mirror lỗi thì đó **không phải lỗi deploy**, và script nói đúng như vậy thay vì cảnh báo mơ hồ.

Hệ quả thực tế: đổi API URL thì phải **build và deploy lại**, sửa env var trên Dashboard không có tác dụng gì.

## Output

`netlify-output.json`:

```json
{
  "url": "https://acme-task-manager.netlify.app",
  "site_id": "...",
  "site_name": "acme-task-manager",
  "deploy_id": "...",
  "deploy_preview_url": "...",
  "verified": true
}
```

`verified: false` nghĩa là deploy được chấp nhận nhưng URL không trả về 200 — thường do SPA fallback thiếu hoặc build ra thư mục rỗng. Script exit 2 trong trường hợp này.

## GitHub

Push lên GitHub là để lưu source, **không** phải cơ chế deploy — repo không được liên kết với Netlify, deploy đi qua CLI. Muốn continuous deploy thì phải liên kết repo trong Netlify Dashboard, và khi đó env var trên Netlify mới có tác dụng.

Script tự thêm `.env`, `.env.*`, `node_modules/`, `dist/` vào `.gitignore`, và gỡ file env khỏi index nếu đã lỡ track. Repo mặc định `private`; `--public` nếu muốn công khai.

## Edge cases

| Tình huống | Xử lý |
|-----------|-------|
| Không có token | Dừng, hướng dẫn lấy token |
| Thiếu `curl`/`jq`/`npm` | Dừng ngay, nêu tên lệnh thiếu |
| Slug đã bị người khác chiếm | Dừng, đề nghị slug cụ thể hơn — không nhận site tên khác |
| Site đã tồn tại trong tài khoản | Dùng lại, không tạo trùng |
| Build lỗi | In 20 dòng cuối, dừng |
| Build không ra `dist/` | Dừng — thường do `publish` trong `netlify.toml` không khớp output của Vite |
| Không có `--api-url` | Bỏ qua env, deploy static thuần |
| Chưa `git init` | Tự init `-b main` |
| Branch không phải `main` | Push đúng branch hiện tại |
| Deploy xong nhưng không 200 | Ghi `verified: false`, exit 2 |

## Không làm

Deploy server (`deploy-render`); liên kết repo cho continuous deploy; cấu hình custom domain, DNS, hay Netlify Functions.
