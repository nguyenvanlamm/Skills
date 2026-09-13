# Changelog

## v2.1.0 — 2026-09-13

### Fixed
- **Contract đối chiếu với SKILL.md thật của sibling** (đã cài): `idea-validator` không nhận thư mục output — điều hướng bằng `IDEAS_ROOT`; `tasks-generator` nhận đường dẫn *file* `prd.md`; `landing-page-generator` sinh copy, không sinh HTML. Bốn skill planning có "Repo Sync Before Edits" bắt buộc và dừng khi thiếu `origin` → orchestrator phải nói rõ repo local chưa có remote trong prompt.
- **Sai contract skill con**: Phase 2 gọi `prd-generator --idea "<chuỗi>"` nhưng skill đó chỉ đọc `idea.md` + `validate.md` trong một thư mục. Giờ Phase 1 để lại đúng cặp file đó ở `$PRODUCT_DIR/` (từ `trend-ideas` v2.2 hoặc `idea-validator` trực tiếp) và Phase 2 truyền thư mục.
- `architecture.md` → `tad.md`: `tasks-generator` tìm `tad.md` theo tên mặc định; tên cũ làm nó không thấy TAD.
- `docs-generator` không tồn tại → `doc-manager`.
- Edge case "trend-ideas fail → webfetch explodingtopics.com" mâu thuẫn với chính trend-ideas; bỏ. Thay bằng nhánh "user đưa idea trực tiếp".
- Firebase prerequisites table lặp lại và **sai** (yêu cầu CI token mà `firebase-auth-setup` v2 không dùng). Bỏ bảng, để skill con tự kiểm.

### Changed
- Tạo GitHub repo chuyển từ Setup sang Phase 4 (sau gate) — Setup chỉ chốt tên. Tạo repo là hành động hướng ra ngoài và trước đây xảy ra trước mọi gate.
- `main.py` template dùng `lifespan` thay `@app.on_event("startup")` (deprecated); `database.py` đọc `DATABASE_URL` từ env ngay từ đầu để `deploy-render` không phải ghi đè file.
- CORS đọc `ALLOWED_ORIGINS` từ env; Phase 4f có bước thêm URL Netlify vào và redeploy — bước hay bị bỏ quên khiến client production bị chặn.
- Nút Google sign-in chỉ sinh khi `firebase-output.json → auth_providers` có `"google"`.

### Added
- Mục "Cách gọi skill con": bảng contract đọc/ghi của từng skill; giải thích cờ `--flag` là mô tả ý định, không phải CLI.
- Nhánh Phase 1 cho user đã có idea (bỏ qua trend-ideas).
- Setup bước 8: kiểm tra runtime + port 8000/5173 **trước** khi sinh code.
- Cờ `needs_auth` / `needs_db` chốt ở Phase 2, dùng nhất quán ở Phase 3–4 (trước đây Phase 4e đoán lại từ `models.py`).
- Phase 4d: kiểm tra secret trong index trước khi push; lưu ý deploy-* đã tự tạo repo.
- Phase 4e: chỉ dùng `url` khi `verified: true`; nhắc PostgreSQL free hết hạn 30 ngày.
- docs/README: cấu trúc output đúng (2 repo + planning files), bỏ layout `backend/`/`frontend/` đã lỗi thời.

### Breaking Changes
- Tên file TAD là `tad.md` (trước: `architecture.md`). Pipeline cũ đang chạy dở cần đổi tên file.

## v2.0.0
- Gate trước Phase 4, sửa skill không tồn tại (social-poster).
