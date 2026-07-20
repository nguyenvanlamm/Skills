# Tra cứu dữ liệu

## Công cụ

**WebSearch** là công cụ chính. Phần lớn dữ liệu du lịch nằm sau chống-bot, nên truy vấn tìm kiếm thường cho kết quả tốt hơn là fetch thẳng.

**WebFetch** dùng cho: Wikipedia, website chính thức của điểm tham quan/khách sạn, trang tin, blog du lịch, Rome2Rio.

**Không fetch được** (chống-bot, sẽ trả về lỗi hoặc trang rỗng — đừng lãng phí lượt gọi): Booking.com, Agoda, Airbnb, Google Maps, Google Flights, Skyscanner, Tripadvisor, Foody, Yelp.

Với nhóm không fetch được, lấy dữ liệu gián tiếp qua WebSearch:

```
"tên khách sạn" review rating booking
"khách sạn 4 sao gần trung tâm [thành phố]" [năm]
"vé máy bay [A] [B] giá tháng [N]"
"quán [món đặc sản] ngon [thành phố] review"
```

Kết quả tìm kiếm thường trích rating và khoảng giá ngay trong snippet — đó là nguồn hợp lệ. Ghi lại nguồn kèm theo.

## Nguồn theo loại dữ liệu

| Loại | Ưu tiên |
|------|---------|
| Vé máy bay | Google Flights → Skyscanner → website hãng (VNA, VietJet, Bamboo) |
| Vé tàu/xe | vexere.com → Baolau → 12Go.asia → Vietnam Railways |
| Khách sạn | Booking → Agoda → Traveloka → Airbnb |
| Nhà hàng | Google Maps → Foody (VN) → Yelp (quốc tế) → Tripadvisor |
| Điểm tham quan | Google Maps → Tripadvisor → website chính thức → Wikipedia |
| Review | Reddit (`r/travel`, `r/VietNam`, `r/ThailandTourism`) → Tripadvisor → YouTube → blog |
| Thời tiết | AccuWeather → Weather.com → tra "weather [city] [month]" |
| Khoảng cách | Google Maps → Rome2Rio |

## Thứ tự ưu tiên khi các nguồn mâu thuẫn

1. Rating Google Maps (mẫu lớn nhất, khó thao túng nhất)
2. Review trong 6 tháng gần đây
3. Giá phù hợp ngân sách
4. Khoảng cách địa lý
5. Số lượng review

## Ghi nhận độ tin cậy

Mỗi đề xuất mang một trong ba trạng thái, và trạng thái phải hiện ra trong output:

| Trạng thái | Điều kiện | Cách ghi |
|---|---|---|
| **Đã xác minh** | Tra được rating + giá từ nguồn cụ thể trong phiên này | Ghi bình thường, kèm nguồn |
| **Một phần** | Có tên + rating, không có giá | "Chưa có giá chính xác — kiểm tra trên [nguồn]" |
| **Chưa xác minh** | Chỉ biết địa điểm tồn tại, không rating lẫn giá | Nêu như gợi ý để người dùng tự tra, **không** đưa vào bảng chi phí |

Không nâng cấp trạng thái bằng suy đoán. Một khách sạn "chắc khoảng 1 triệu/đêm" là số bịa, kể cả khi ước đoán nghe hợp lý.

## Khi không tra được gì

Nói thẳng phần nào thiếu, và vẫn giao phần làm được. Một kế hoạch có lịch trình đầy đủ nhưng thiếu giá khách sạn vẫn hữu ích hơn là không có gì — miễn là chỗ thiếu được ghi rõ.
