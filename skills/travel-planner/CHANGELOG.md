# Changelog

## v2.1.0 — 2026-09-13

### Added
- **Bước 1b — kiểm tra khả thi trước khi tra cứu**: thời gian vs quãng đường, ngân sách/người/ngày, ngày đi (quá khứ / cực cao điểm). Fail-fast thay vì tra 20 lượt rồi kết luận "vượt ngân sách 300%".
- **Ngân sách tra cứu** (`references/search.md`): trần số lượt theo hạng mục và cách gộp truy vấn. Chuyến 3–5 ngày rơi vào 15–25 lượt thay vì 60.
- Hỗ trợ **nhiều điểm đến nối tiếp**: cách chia ngày, chặng di chuyển giữa các điểm phải xuất hiện trong lịch trình và bảng chi phí.
- Checklist **tự kiểm tra số học**: tổng = cộng các dòng, số bữa = 3 × ngày, điểm tham quan ↔ lịch trình khớp nhau.

### Improved
- Chuẩn hoá input: `days` ngoài 1–30, `children` thiếu tuổi, `budget` thiếu đơn vị tiền tệ → hỏi lại thay vì đoán.
- Tên tool viết host-agnostic (`web_search`/`WebSearch`, `webfetch`/`WebFetch`) — skill chạy được trên Devin CLI, Claude Code, opencode mà không cần sửa.

### Changed
- Không có thay đổi behavior với input hợp lệ. Output structure giữ nguyên.

### Breaking Changes
- None.

## v2.0.0
- Phiên bản trước: nguyên tắc "không bịa số", 6 bước, ngưỡng lọc tập trung trong `selection.md`.
