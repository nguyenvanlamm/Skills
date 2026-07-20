# Chọn khách sạn và nhà hàng

File này là **nguồn duy nhất** định nghĩa ngưỡng lọc. Không file nào khác được nêu lại con số — nếu cần, tham chiếu về đây.

## Bảng ngưỡng

Mỗi tiêu chí có 3 mức. Luôn bắt đầu ở mức *Ưu tiên*, chỉ hạ xuống theo thang nới lỏng ở dưới.

### Khách sạn

| Tiêu chí | Ưu tiên | Chấp nhận | Sàn tuyệt đối |
|---|---|---|---|
| Rating | ≥ 4.2 | ≥ 4.0 | ≥ 3.8 |
| Khoảng cách tới trung tâm | ≤ 3 km | ≤ 5 km | ≤ 8 km |
| Phương tiện | không cần | có phương tiện công cộng hoặc shuttle | **bắt buộc** có phương tiện |

Dưới 3.8 thì không đề xuất, bất kể fallback đến bước nào.

### Nhà hàng

| Tiêu chí | Ưu tiên | Chấp nhận | Sàn tuyệt đối |
|---|---|---|---|
| Rating | ≥ 4.3 | ≥ 4.0 | ≥ 3.8 |
| Rẽ ngang khỏi lộ trình | ≤ 1 km | ≤ 2 km | ≤ 3 km |

### Về số lượng review

Không đặt ngưỡng cứng — số review hiếm khi tra được đáng tin qua tìm kiếm, và một ngưỡng không kiểm chứng được chỉ dẫn tới việc bịa số.

Thay vào đó: **rating không kèm số review là rating chưa xác minh.** Nếu tra được cả hai, ghi cả hai (`4.5/5, 2.800+ review`). Nếu chỉ có rating, ghi rating và nói rõ chưa xác nhận được số lượng đánh giá. Khi hai lựa chọn ngang rating, chọn cái có nhiều review hơn.

## Loại trừ

Loại ngay, không cần cân nhắc:

- Rating dưới sàn tuyệt đối
- Đã đóng cửa vĩnh viễn
- Review tiêu cực gần đây về an toàn (khách sạn) hoặc vệ sinh (nhà hàng)
- Không phù hợp đối tượng — VD quán nhậu cho gia đình có trẻ nhỏ, khách sạn không thang máy cho người già

## Thang nới lỏng

Áp dụng khi không đủ kết quả ở mức hiện tại. Đi từng bước, dừng ngay khi có đủ lựa chọn.

**Khách sạn:**
```
1. Hạ khoảng cách:  Ưu tiên (3km) → Chấp nhận (5km)
2. Hạ rating:       4.2 → 4.0
3. Mở loại hình:    khách sạn → + homestay, guesthouse, căn hộ
4. Hạ tiếp:         5km → 8km (bắt buộc có phương tiện), rating 4.0 → 3.8
5. Dừng: "Chưa tìm thấy chỗ ở đạt tiêu chuẩn trong khu vực này."
```

**Nhà hàng:**
```
1. Nới rẽ ngang:  1km → 2km
2. Hạ rating:     4.3 → 4.0
3. Mở loại hình:  + quán vỉa hè, quán bình dân
4. Hạ tiếp:       2km → 3km, rating 4.0 → 3.8
5. Dừng: gợi ý người dùng tự tìm tại chỗ cho bữa đó — vẫn giữ khung giờ trong lịch trình.
```

**Vé máy bay:**
```
1. Sân bay lân cận thay vì bay thẳng
2. Phương tiện thay thế (tàu, xe khách)
3. Đề xuất điều chỉnh điểm đến hoặc ngày đi
```

**Địa điểm đóng cửa / bảo trì:** tìm điểm tương tự trong bán kính 1 km, cùng loại (văn hóa → văn hóa), rating tương đương hoặc cao hơn.

## Tiêu chí bổ sung theo đối tượng

Áp lên khách sạn sau khi đã lọc theo bảng ngưỡng:

| Đối tượng | Yêu cầu thêm |
|-----------|--------------|
| Gia đình có trẻ em | Phòng gia đình, hồ bơi, bếp nhỏ; kiểm tra chính sách phụ thu trẻ em |
| Cặp đôi | Phòng giường lớn, không gian riêng tư |
| Người già | Thang máy, phòng tầng thấp, gần cơ sở y tế |
| Đi ô tô riêng | Bãi đỗ miễn phí |

Tiện nghi cơ bản với mọi đối tượng: điều hòa hoặc sưởi (tùy khí hậu), wifi, phòng tắm riêng, nước nóng.

## Phân bổ nhà hàng

Mỗi ngày tối thiểu 3 quán: sáng (7h–10h), trưa (11h–13h30), tối (18h–21h).

- Ưu tiên đặc sản địa phương; mỗi ngày ít nhất 1 món đặc trưng của điểm đến
- Không lặp món trong cùng chuyến đi
- Nếu người dùng nêu `cuisine`, lọc theo đó trước
- Ngân sách thấp → nghiêng về street food và quán bình dân, giảm số bữa cao cấp

## Số lượng đề xuất

Khách sạn — luôn đưa 3 lựa chọn:
1. **Top pick** — tốt nhất theo bảng ngưỡng
2. **Rẻ hơn** — hoặc khác khu vực
3. **Cao cấp hơn** — hoặc khác phong cách

Nhà hàng — 1 lựa chọn/bữa là đủ, kèm 1 phương án dự phòng cho các bữa tối.
