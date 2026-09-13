---
name: social-brand-sync
description: "Đồng bộ thương hiệu từ website lên mạng xã hội — phân tích website (logo, tên, màu sắc), tạo ảnh đại diện + ảnh bìa đúng kích thước từng nền tảng, và cập nhật qua API. Hỗ trợ Facebook, LinkedIn, Twitter/X, TikTok, YouTube, GitHub. Không dùng cho đăng bài content, quảng cáo, hoặc nền tảng không được hỗ trợ."
license: MIT
effort: high
metadata:
  version: 3.0.0
  author: "Nguyen Van Lam"
---

# Social Brand Sync

Đồng bộ hóa thương hiệu từ website lên mạng xã hội — cập nhật ảnh đại diện, ảnh bìa và tên hiển thị để nhận diện thống nhất trên mọi nền tảng.

## Nguyên tắc

> **Mặc định không ghi.** Skill này thay avatar, ảnh bìa và tên hiển thị trên tài khoản thật, cùng lúc trên nhiều nền tảng, và không có nút hoàn tác. Lần chạy đầu luôn là dry-run: mọi mục được đánh giá và ghi vào `report.json` là `planned` / `skipped` / `manual` kèm lý do, **không gọi API ghi nào**. Chỉ `--apply` sau khi user đã đọc kế hoạch và đồng ý — và đồng ý cho một nền tảng không phải đồng ý cho tất cả.

> **Chỉ báo `updated` khi API xác nhận thay đổi đã áp vào profile.** Bản cũ báo LinkedIn "updated" sau khi upload asset mà chưa gắn vào organization, và gọi các endpoint Twitter v2 không tồn tại. Giờ mỗi `updated` tương ứng với một response 2xx của lệnh **áp dụng**, không phải lệnh upload.

**Đổi tên là hành động nặng nhất.** Facebook giới hạn số lần đổi tên Page và có thể đưa vào diện review. Mặc định nên chỉ đồng bộ ảnh (`--action profile-pic` hoặc `cover`); chỉ đổi tên khi user yêu cầu đích danh.

**Backup trước khi ghi đè.** Ảnh đại diện Facebook hiện tại được tải về `<output>/backup/<platform>/` trước khi thay. Không backup được thì script nói rõ.

**Thất bại từng phần là bình thường.** Sáu nền tảng, sáu API. Nền tảng thứ ba lỗi không hoàn tác được hai nền tảng đầu. `report.json` ghi trạng thái từng nền tảng từng mục; báo cáo cuối liệt kê từng dòng, không gộp thành "hoàn tất". Không tự retry một mục đã `updated`.

## Khi nào dùng

Dùng khi: ra mắt website mới, rebrand, muốn logo + tên thống nhất giữa website và mạng xã hội.

Không dùng cho: đăng bài / quảng cáo; nền tảng không hỗ trợ (Instagram, Discord, Reddit, Zalo); chỉnh thông tin không thuộc thương hiệu (bio, mật khẩu, email).

## Cái gì làm được qua API — thật sự

| Platform | Avatar | Cover/Banner | Tên | Ghi chú |
|----------|--------|--------------|-----|---------|
| Facebook Page | ✅ | ✅ | ✅ (giới hạn) | Graph API v22, Page token |
| LinkedIn Company | ✅ | ✅ | ✋ manual | Cần token admin của Page (`rw_organization_admin`); upload asset rồi `PARTIAL_UPDATE organization.logoV2/coverPhotoV2` |
| Twitter/X | ✅ | ✅ | ✅ | **v1.1 `account/update_profile*` + OAuth 1.0a user context** (script ký bằng `twitter_oauth1.py`). Từ 2023 cần tier API trả phí; 402/403 là vấn đề gói, không phải bug |
| TikTok | ✋ | — | ✋ | Không có API |
| YouTube | ✋ | ✅ | ✅ | `channelBanners.insert` → `channels.update`; avatar chỉ đổi trong Studio |
| GitHub | ✋ | — | ✅ | `PATCH /user` chỉ nhận `name`; avatar không có API |

✋ = script tạo ảnh đúng kích thước và ghi hướng dẫn thao tác tay vào `report.json`.

## Chuẩn bị

Tool: `curl`, `jq`, `python3` (stdlib), ImageMagick (`magick` hoặc `convert`/`identify`).

Token và ID theo nền tảng — cách lấy trong `references/api-setup.md`:

| Platform | Env |
|----------|-----|
| Facebook | `FB_PAGE_ACCESS_TOKEN`, `FB_PAGE_ID` |
| LinkedIn | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_COMPANY_ID` (tuỳ chọn `LINKEDIN_API_VERSION`, mặc định `202409`) |
| Twitter/X | `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` — **cả bốn**; bearer token không ghi được profile |
| YouTube | `YT_ACCESS_TOKEN` (scope `youtube.force-ssl`), `YT_CHANNEL_ID` |
| GitHub | `GITHUB_TOKEN` (scope `user`) |
| TikTok | không cần — chỉ tạo ảnh |

Thiếu biến của nền tảng nào → nền tảng đó `skipped` với lý do `missing env`, các nền tảng khác vẫn chạy.

## Tham số

| Param | Bắt buộc | Mô tả |
|-------|----------|-------|
| `--website` | ✅ | URL `https://` |
| `--platforms` | ✅ | `facebook,linkedin,twitter,tiktok,youtube,github` — chọn tập con |
| `--action` | ❌ | `all` (mặc định) · `profile-pic` · `cover` · `name` |
| `--brand-name` | ❌ | Ghi đè tên trích từ website |
| `--logo-url` / `--cover-url` / `--color` | ❌ | Ghi đè khi phân tích website sai hoặc site là SPA không có OG tags |
| `--output-dir` | ❌ | Mặc định `/tmp/social-brand-sync/<domain>` |
| `--apply` | ❌ | Thực hiện ghi. Không có → dry-run |

## Chạy

```bash
# 1. Dry-run toàn bộ: phân tích, tạo ảnh, lập kế hoạch từng nền tảng
bash scripts/sync.sh --website https://example.com --platforms facebook,linkedin,github

# 2. Đọc kế hoạch (stdout + <output>/report.json), sửa bằng --brand-name/--logo-url nếu cần

# 3. Áp dụng — thu hẹp phạm vi nếu chưa chắc
bash scripts/sync.sh --website https://example.com --platforms facebook,linkedin,github --action profile-pic --apply
```

| Script | Việc | Ghi |
|--------|------|-----|
| `analyze-website.py` | Fetch HTML một lần; tên (og:site_name → application-name → JSON-LD → title → alt logo → domain), logo (apple-touch-icon lớn nhất → icon → TileImage → img logo trong header), cover (og:image → twitter:image), màu (CSS `--primary` → theme-color). Ghi nguồn của từng giá trị; thiếu → `null` + liệt kê trong `missing` | `brand-info.json` |
| `process-images.sh` | Tải logo (fallback favicon), chuẩn hoá thành PNG vuông có nền màu thương hiệu, sinh ảnh từng nền tảng đúng kích thước, cover từ ảnh gốc hoặc sinh từ màu + logo, validate bằng `identify` | `<platform>/*.png`, `images-manifest.json` |
| `update-platform.sh` | Một nền tảng: kiểm tra env, từng mục → `planned` (dry-run) hoặc gọi API, retry 1 lần khi 429/5xx, backup, ghi report | `report.json` |
| `twitter_oauth1.py` | Ký HMAC-SHA1 OAuth 1.0a và gọi `account/update_profile_image|_banner|` (stdlib) | — |
| `sync.sh` | Orchestrator cho 4 bước trên; nền tảng lỗi không dừng nền tảng khác | tất cả |

Có thể chạy từng script rời — `update-platform.sh` tự tạo `report.json` và dòng của nền tảng nếu chưa có.

## Output

```
<output-dir>/
├── brand-info.json        # tên, logo_url, cover_url, màu + nguồn của từng giá trị + missing[]
├── images-manifest.json   # mỗi ảnh: path, kích thước thật, kích thước kỳ vọng, ok
├── report.json            # trạng thái từng nền tảng × {profile_pic, cover, name}
├── originals/             # logo.<ext>, logo-square.png, cover.<ext>
├── backup/<platform>/     # ảnh cũ trước khi ghi đè (khi apply)
├── facebook/  profile-pic.png 360² · cover.png 851×315
├── linkedin/  profile-pic.png 400² · cover.png 1584×396
├── twitter/   profile-pic.png 400² · header.png 1500×500
├── tiktok/    profile-pic.png 200²
├── youtube/   profile-pic.png 800² · banner.png 2560×1440
└── github/    profile-pic.png 512²
```

`report.json`:

```json
{
  "website": "https://example.com", "brand_name": "Example", "brand_info_source": "og:site_name + apple-touch-icon (180px)",
  "processed_at": "2026-09-13T10:30:00Z", "images_dir": "/tmp/social-brand-sync/example.com",
  "updates": [
    { "platform": "facebook", "mode": "apply", "profile_pic": "updated", "cover": "updated", "name": "not-requested", "profile_url": "https://facebook.com/123", "error": null },
    { "platform": "linkedin", "mode": "apply", "profile_pic": "failed", "cover": "planned", "name": "manual", "error": "profile_pic: apply: HTTP 403 …" },
    { "platform": "tiktok",   "mode": "apply", "profile_pic": "manual", "cover": "skipped", "name": "manual", "error": "profile_pic: TikTok has no profile-update API. …" }
  ]
}
```

Trạng thái: `planned` (dry-run, sẽ ghi) · `updated` · `failed` · `skipped` (thiếu file/env/không áp dụng) · `manual` (nền tảng không có API — kèm hướng dẫn) · `not-requested` (ngoài `--action`).

## Quy trình cho agent

1. Chạy `sync.sh` **không** `--apply`. Đọc `brand-info.json`: tên/logo có đúng không? SPA không có OG tags → hỏi user URL logo, chạy lại với `--logo-url`. Đừng tự đoán URL logo.
2. Trình bày kế hoạch cho user theo đúng `report.json`: nền tảng nào sẽ đổi gì, cái nào thiếu token, cái nào phải làm tay. Hỏi rõ phạm vi (`--platforms`, `--action`).
3. `--apply` đúng phạm vi đã duyệt. Đọc lại `report.json`, báo từng dòng. `failed` → trích `error`, gợi ý sửa từ `references/api-setup.md § Troubleshooting`; không tự retry mục đã `updated`.
4. Mục `manual` → đưa đường dẫn file ảnh và vị trí trong UI nền tảng.

Agent files `agents/website-analyzer.md`, `agents/image-processor.md` mô tả logic của hai script để đọc khi cần hiểu/gỡ lỗi; không cần chạy chúng "bằng tay" nữa.

## Edge cases

| Tình huống | Xử lý |
|-----------|-------|
| Website không load được | `analyze-website.py` exit 1 với lỗi; dừng |
| Không tìm thấy logo | Dùng favicon (cảnh báo độ phân giải thấp); vẫn không có → dừng, hỏi `--logo-url` |
| Logo không vuông / có nền trong suốt | Đặt lên nền màu thương hiệu, pad thành vuông — không kéo giãn |
| Không có OG image | Sinh cover từ màu + logo; `images-manifest.json → generated_covers: true` |
| Không có màu thương hiệu | Nền trung tính `#1F2937`, ghi cảnh báo |
| Thiếu token một nền tảng | Nền tảng đó `skipped (missing env: …)`, các nền tảng khác chạy tiếp |
| 429 / 5xx | Retry một lần sau 15 giây, rồi `failed` |
| Twitter 402/403 | Tier API không cho ghi profile — ghi rõ trong `error`; không phải lỗi script |
| LinkedIn apply 403 | Token không phải admin của Page hoặc thiếu `rw_organization_admin` |
| Tên quá dài | Cắt theo giới hạn nền tảng (FB 75, X 50, YT 70, GH 100) — báo trong plan |
| Nền tảng ngoài danh sách | `sync.sh` từ chối ngay, liệt kê nền tảng hợp lệ |

## Không làm

Đăng bài; Instagram/Discord/Reddit/Zalo; đổi bio/email/mật khẩu; tự tạo OAuth token thay user; bỏ qua dry-run.
