---
name: travel-planner
description: "Lập kế hoạch du lịch toàn diện — đề xuất khách sạn, nhà hàng, phương tiện, lịch trình từng ngày và ước tính chi phí. Dùng khi người dùng muốn lên lịch trình cho một chuyến đi cụ thể. Không dùng để đặt vé/phòng, tư vấn visa - hộ chiếu - thủ tục pháp lý, hay tổ chức du lịch công vụ - hội nghị."
license: MIT
effort: medium
metadata:
  version: 2.0.0
  author: "Nguyen Van Lam"
---

# Travel Planner

Lập kế hoạch du lịch dựa trên dữ liệu tra cứu được, không dựa trên trí nhớ.

## Nguyên tắc cốt lõi

> **Không bịa số.** Mọi giá, rating, tên địa điểm phải đến từ một lần tra cứu trong phiên làm việc này. Không có dữ liệu thì ghi rõ là không có — đó là câu trả lời hợp lệ, còn một con số bịa thì không.

Kiến thức nội tại về một điểm đến chỉ dùng để **định hướng tìm kiếm** (biết nên tra cái gì), không dùng để **điền vào output**.

## Quy trình

Chạy tuần tự. Mỗi bước ghi rõ file cần đọc — đọc khi tới bước đó, không đọc trước.

**Bước 1 — Thu thập input.** Đối chiếu với bảng dưới. Thiếu trường bắt buộc thì hỏi, đừng đoán.

**Bước 2 — Tra cứu.** Đọc `references/search.md`. File này quy định nguồn nào cho loại dữ liệu nào, dùng tool gì, và xử lý ra sao khi nguồn không truy cập được.

**Bước 3 — Chọn khách sạn và nhà hàng.** Đọc `references/selection.md`. Chứa toàn bộ ngưỡng lọc (rating, khoảng cách) và quy tắc nới lỏng khi không đủ kết quả.

**Bước 4 — Lập lịch trình.** Đọc `references/itinerary.md`. Quy tắc gom cụm địa điểm, mật độ theo `pace`, điều chỉnh theo đối tượng và thời tiết.

**Bước 5 — Ước tính chi phí.** Đọc `references/cost.md`. Cách dựng baseline chi phí cho điểm đến, công thức tổng, và cách xử lý khi vượt ngân sách.

**Bước 6 — Kiểm tra và xuất.** Đọc `references/output.md`. Chứa checklist bắt buộc chạy trước khi trả lời, và cấu trúc output.

`references/examples.md` — chỉ đọc khi cần tham khảo cách trình bày. Đó là ví dụ về **cấu trúc**, mọi con số trong đó là placeholder.

## Input

| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|------|----------|-------|
| `departure` | string | ✅ | Điểm xuất phát |
| `destination` | string | ✅ | Điểm đến |
| `days` | integer | ✅ | Số ngày (1–30) |
| `adults` | integer | | Số người lớn (mặc định 2) |
| `children` | integer | | Số trẻ em + tuổi (mặc định 0) |
| `budget` | integer | | Tổng ngân sách, kèm đơn vị tiền tệ |
| `hotel_level` | enum | | 2–5 sao |
| `transportation` | enum | | Máy bay / Xe khách / Tàu / Ô tô |
| `interests` | array | | văn hóa, ẩm thực, thiên nhiên, mua sắm, giải trí, lịch sử |
| `pace` | enum | | thoải mái / vừa phải / nhanh (mặc định vừa phải) |
| `cuisine` | string | | VD: hải sản, chay, đặc sản địa phương |
| `special_requirements` | string | | VD: xe lăn, dị ứng thực phẩm, đi bộ khó |
| `start_date` | date | | Để tra thời tiết và giá theo mùa |

Khi hỏi thêm, gộp thành một lượt — đừng hỏi từng câu:

> "Mình cần thêm vài thông tin để lên lịch sát nhất:
> - Bạn xuất phát từ đâu, đi mấy ngày?
> - Ngân sách dự kiến khoảng bao nhiêu?
> - Đi cùng ai (gia đình có trẻ nhỏ, cặp đôi, nhóm bạn, một mình)?
> - Có ngày khởi hành cụ thể chưa?"

Nếu `start_date` đã ở quá khứ so với hôm nay, hỏi lại thay vì lập kế hoạch.

## Phạm vi

Hỗ trợ: du lịch trong nước và nước ngoài, chuyến 1–30 ngày, mọi hình thức (gia đình, cặp đôi, nhóm, một mình; tiết kiệm, nghỉ dưỡng, khám phá).

Không làm: đặt vé/phòng/dịch vụ thay người dùng; tư vấn visa, hộ chiếu, thủ tục pháp lý; du lịch công vụ và hội nghị.

Giá đưa ra luôn là giá tham khảo tại thời điểm tra cứu, có thể thay đổi theo mùa và thời điểm đặt.
