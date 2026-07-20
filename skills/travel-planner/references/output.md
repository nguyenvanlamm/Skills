# Kiểm tra và xuất kết quả

## Checklist

Chạy trước khi gửi phản hồi. Mục nào không đạt thì quay lại sửa, đừng gửi kèm lời xin lỗi.

**Tính trung thực của dữ liệu** — quan trọng nhất:
- [ ] Mọi giá và rating trong output đều đến từ một lần tra cứu trong phiên này
- [ ] Không có số nào được điền từ trí nhớ hoặc ước đoán
- [ ] Khoản chưa tra được đã ghi `—` hoặc "chưa có giá chính xác", không bị điền bừa
- [ ] Tỷ giá quy đổi (nếu có) kèm ngày tra

**Đầy đủ:**
- [ ] Có phương tiện di chuyển: loại, hãng, giá
- [ ] Có 3 lựa chọn chỗ ở: tên, rating, giá, địa chỉ
- [ ] Có lịch trình đủ 4 buổi mỗi ngày
- [ ] Có tối thiểu 3 bữa/ngày (sáng, trưa, tối)
- [ ] Có bảng tổng chi phí và so sánh với ngân sách (nếu người dùng nêu `budget`)
- [ ] Có ít nhất 3 mẹo cụ thể cho điểm đến này

**Chất lượng lịch trình:**
- [ ] Số điểm lớn mỗi ngày nằm trong khoảng của `pace` đã chọn, và ≥ 1
- [ ] Đã kiểm tra khoảng cách thực tế giữa các điểm liên tiếp — không có ngày nào quay lại khu vực đã rời
- [ ] Không lặp địa điểm trong cùng chuyến đi
- [ ] Số đêm khách sạn = số ngày − 1
- [ ] Nếu có trẻ em hoặc người già: đã giảm mật độ và quãng đường đi bộ
- [ ] Nếu có `special_requirements`: đã kiểm tra từng điểm có đáp ứng không
- [ ] Nếu tra được thời tiết: lịch đã điều chỉnh theo

## Cấu trúc output

Dùng đúng thứ tự các mục sau.

### Tổng quan
Điểm đi → điểm đến, số ngày/đêm, số người, tổng chi phí dự kiến, kết luận một dòng so với ngân sách.

### Vé di chuyển
Loại phương tiện, hãng, giờ khởi hành, giá (kèm nhãn tham khảo), link đặt nếu có.

### Chỗ ở
Top pick + 2 phương án. Mỗi mục: tên, địa chỉ, rating (+ số review nếu tra được), tiện nghi nổi bật liên quan tới đối tượng đi, giá/đêm, nguồn.

### Lịch trình từng ngày
Theo định dạng trong `itinerary.md`. Mỗi ngày có tiêu đề gợi nội dung chính, không chỉ "Ngày 2".

### Nhà hàng
| Ngày | Bữa | Tên quán | Món đặc trưng | Giá | Rating |
|------|-----|----------|---------------|-----|--------|

### Điểm tham quan
| Điểm | Loại | Giá vé | Thời gian tham quan | Ghi chú |
|------|------|--------|---------------------|---------|

### Tổng chi phí
Bảng theo `cost.md`.

### Mẹo
Ít nhất 3 mẹo **riêng cho điểm đến này** — sim/thẻ đi lại, tập quán địa phương, cách tránh bẫy giá, thời điểm nên né. Không viết mẹo chung chung kiểu "nhớ mang theo giấy tờ".

## Giọng văn

Tiếng Việt, trừ tên riêng và thương hiệu. Trình bày có cấu trúc, dễ quét mắt. Khi đề xuất nhiều lựa chọn, nói rõ **vì sao** cái này được chọn làm top pick thay vì chỉ liệt kê.
