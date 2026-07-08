# Cost Estimation

## Công thức tính tổng chi phí

```
TỔNG = VÉ_DI_CHUYỂN + KHÁCH_SẠN + ĂN_UỐNG + DI_CHUYỂN_NỘI_THÀNH + VÉ_THAM_QUAN + CHI_PHÍ_PHÁT_SINH
```

### Chi tiết từng khoản

#### Vé di chuyển
- Vé máy bay/tàu/xe khách (khứ hồi) × số người
- Nếu có phương tiện trung gian (phà, bus): cộng thêm

#### Khách sạn
- Giá/đêm × số đêm × số phòng
- Nếu trẻ em: kiểm tra chính sách phụ thu

#### Ăn uống
- Sáng: 30k-50k × số người × số ngày
- Trưa: 50k-150k × số người × số ngày
- Tối: 100k-300k × số người × số ngày
- (Điều chỉnh theo mức sống điểm đến)

#### Di chuyển nội thành
- Taxi / Grab: ước tính theo khoảng cách
- Thuê xe máy: 100k-200k/ngày
- Thuê xe ô tô: 500k-1.000k/ngày
- Xe bus: 5k-20k/lượt

#### Vé tham quan
- Tổng các vé điểm tham quan × số người
- Nếu có combo/vé ghép: ưu tiên

#### Chi phí phát sinh
- **10%** tổng các khoản trên
- Bao gồm: nước uống, đồ ăn vặt, tip, mua quà, khẩn cấp

---

## So sánh với ngân sách

Nếu người dùng có `budget`:

```
nếu tổng < budget * 0.9:
    → "Trong ngân sách, còn dư X"
nếu budget * 0.9 <= tổng <= budget * 1.1:
    → "Xấp xỉ ngân sách"
nếu tổng > budget * 1.1:
    → "Vượt ngân sách X. Đề xuất điều chỉnh..."
```

## Điều chỉnh nếu vượt ngân sách

Gợi ý (theo thứ tự):

1. Giảm hạng khách sạn (5 sao → 4 sao, 4 sao → 3 sao)
2. Đổi phương tiện (máy bay → xe khách)
3. Giảm số bữa ăn cao cấp
4. Giảm số ngày
5. Chọn điểm đến rẻ hơn

## Format output

| Khoản mục | Số tiền (VND) |
|-----------|--------------|
| Vé di chuyển | xxx |
| Khách sạn (x đêm) | xxx |
| Ăn uống | xxx |
| Taxi / Thuê xe | xxx |
| Vé tham quan | xxx |
| Chi phí phát sinh (10%) | xxx |
| **Tổng** | **xxx** |
| **Ngân sách** | **xxx** |
| **Chênh lệch** | **±xxx** |
