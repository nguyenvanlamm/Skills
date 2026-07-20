# Chi phí

## Nguyên tắc về giá

- Luôn ghi rõ đơn vị tiền tệ (VND, THB, USD…). Với chuyến nước ngoài, giữ giá gốc bằng nội tệ điểm đến và quy đổi thêm sang tiền của người dùng.
- **Không tự quy đổi tỷ giá bằng trí nhớ.** Tra tỷ giá trong phiên này và ghi ngày tra: `≈ 1.200.000 VND (tỷ giá 20/07/2026)`.
- Nguồn có nhiều mức giá → ghi khoảng, không ghi một con số: `800.000 – 1.200.000 VND/đêm`.
- Luôn nêu đơn vị tính: mỗi đêm, mỗi người, mỗi suất, cả nhóm — con số không có đơn vị là con số vô nghĩa.

Theo tình huống:

| Tình huống | Ghi |
|---|---|
| Giá theo mùa | "Thấp điểm: xxx / Cao điểm: yyy / Tháng [N]: khoảng zzz" |
| Nguồn cũ hơn 6 tháng | "Giá tham khảo (cập nhật [tháng/năm])" |
| Không tra được giá | "Chưa có giá chính xác — kiểm tra trên [nguồn]" |
| Giá biến động nhanh (vé bay, mùa cao điểm) | "Giá thay đổi theo thời điểm đặt, vui lòng kiểm tra lại trước khi mua" |

## Dựng baseline cho điểm đến

Chi phí sinh hoạt chênh nhau hàng chục lần giữa các điểm đến, nên **không có con số mặc định**. Với mỗi chuyến, tra baseline trước khi tính:

```
"chi phí du lịch [điểm đến] 1 ngày bao nhiêu"
"[destination] daily travel budget backpacker mid-range"
"giá thuê xe máy [điểm đến]"
"giá taxi sân bay [điểm đến] về trung tâm"
```

Lấy ra 3 số cho mỗi hạng mục (ăn uống/ngày, di chuyển nội thành/ngày) theo 3 mức: **tiết kiệm / trung bình / cao cấp**. Chọn mức khớp với `budget` và `hotel_level` của người dùng.

Nếu không tra được baseline, nói rõ và chỉ tính những khoản có giá thực (vé máy bay, khách sạn, vé tham quan), để phần ăn uống và đi lại ở dạng "chưa ước tính được".

## Công thức

```
TỔNG = VÉ_DI_CHUYỂN + CHỖ_Ở + ĂN_UỐNG + DI_CHUYỂN_NỘI_THÀNH + VÉ_THAM_QUAN + PHÁT_SINH
```

| Khoản | Cách tính |
|---|---|
| Vé di chuyển | Giá khứ hồi × số người, cộng phương tiện trung gian (phà, bus nối) nếu có |
| Chỗ ở | Giá/đêm × số đêm × số phòng. **Số đêm = số ngày − 1.** Kiểm tra phụ thu trẻ em |
| Ăn uống | Baseline ăn uống/ngày × số người × số ngày |
| Di chuyển nội thành | Baseline/ngày × số ngày, hoặc cộng từng chặng nếu đã biết lộ trình |
| Vé tham quan | Tổng vé × số người; ưu tiên combo/vé ghép nếu rẻ hơn |
| Phát sinh | **10%** tổng các khoản trên — nước, đồ ăn vặt, tip, quà, dự phòng |

Chỉ đưa vào bảng những khoản có giá đã xác minh hoặc có baseline tra được. Khoản chưa xác minh ghi `—` kèm chú thích, đừng điền số để bảng trông đầy đủ.

## So với ngân sách

```
tổng < budget × 0.9        → "Trong ngân sách, còn dư X"
budget×0.9 ≤ tổng ≤ ×1.1   → "Xấp xỉ ngân sách"
tổng > budget × 1.1        → "Vượt ngân sách X — đề xuất điều chỉnh"
```

Khi vượt, gợi ý theo thứ tự (từ ít ảnh hưởng trải nghiệm nhất):

1. Hạ hạng khách sạn một bậc
2. Đổi phương tiện (máy bay → tàu/xe khách)
3. Giảm số bữa cao cấp
4. Giảm số ngày
5. Đổi điểm đến rẻ hơn

Đưa ra con số tiết kiệm được cho mỗi phương án, đừng chỉ liệt kê.

## Định dạng bảng

| Khoản mục | Số tiền | Ghi chú |
|-----------|---------|---------|
| Vé di chuyển | xxx | |
| Chỗ ở (x đêm) | xxx | |
| Ăn uống | xxx | baseline mức trung bình |
| Di chuyển nội thành | xxx | |
| Vé tham quan | xxx | |
| Phát sinh (10%) | xxx | |
| **Tổng** | **xxx** | |
| **Ngân sách** | **xxx** | |
| **Chênh lệch** | **±xxx** | |
