# Fallback Rules

## Xử lý khi thiếu dữ liệu

Các quy tắc này được áp dụng khi không tìm thấy dữ liệu đáp ứng tiêu chuẩn.

---

## 1. Khách sạn

```
Bước 1: Tăng bán kính tìm kiếm lên 2 km (từ 3km → 5km)
  ↓ Nếu vẫn không có
Bước 2: Giảm rating threshold từ 4.2 → 4.0
  ↓ Nếu vẫn không có
Bước 3: Giảm review count từ 100 → 30
  ↓ Nếu vẫn không có
Bước 4: Mở rộng sang homestay/guesthouse (không chỉ khách sạn)
  ↓ Nếu vẫn không có
Kết luận: "Hiện chưa tìm thấy khách sạn phù hợp trong khu vực."
```

## 2. Nhà hàng

```
Bước 1: Tăng bán kính thêm 500m
  ↓ Nếu vẫn không có
Bước 2: Giảm rating threshold từ 4.3 → 4.0
  ↓ Nếu vẫn không có
Bước 3: Mở sang quán vỉa hè (nếu phù hợp)
  ↓ Nếu vẫn không có (cả bữa đó)
Gợi ý người dùng tự tìm khi đến nơi.
```

## 3. Vé máy bay

```
Bước 1: Mở rộng sân bay gần nhất (thay vì bay thẳng)
  ↓ Nếu vẫn không có
Bước 2: Đề xuất phương tiện thay thế (xe khách, tàu)
  ↓ Nếu vẫn không có
Bước 3: Đề xuất điều chỉnh điểm đến
```

## 4. Nhà hàng đóng cửa

```
Tìm quán gần nhất (≤ 500m) cùng loại ẩm thực
         ↓
Cùng rating range (±0.3)
         ↓
Cùng khoảng giá
```

## 5. Địa điểm tham quan bảo trì / đóng cửa

```
Tìm điểm tương tự trong bán kính 1km
         ↓
Cùng loại (văn hóa → văn hóa, thiên nhiên → thiên nhiên)
         ↓
Rating tương đương hoặc cao hơn
```

## Nguyên tắc vàng

> **KHÔNG BAO GIỜ BỊA DỮ LIỆU.**

Nếu đã áp dụng tất cả các bước fallback mà vẫn không tìm thấy:

> "Hiện chưa có dữ liệu đáng tin cậy cho yêu cầu này. Bạn có thể thử:
> - Điều chỉnh tiêu chí (giảm hạng sao, tăng ngân sách, đổi điểm đến khác)
> - Hoặc liên hệ mình để tôi tìm phương án khác."
