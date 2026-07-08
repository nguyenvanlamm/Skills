# Itinerary Rules

## Thuật toán lập lịch

Đây là file quan trọng nhất — quy định cách sắp xếp lịch trình.

---

## 1. Nguyên tắc tối ưu hóa

### 1.1. Không đi ngược đường
- Sắp xếp điểm tham quan theo tuyến đường thẳng từ sáng đến tối
- Không quay vòng (VD: sáng điểm A → chiều điểm B → tối lại điểm A)
- Nhóm địa điểm gần nhau vào cùng buổi

### 1.2. Nhóm địa điểm theo cụm

Ví dụ:

> Cụm trung tâm: Hồ Gươm, Nhà thờ Lớn, Phố cổ
> Cụm Tây Hồ: Chùa Trấn Quốc, Phố Tây, Lăng Bác

Chỉ di chuyển giữa các cụm 1 lần/ngày.

### 1.3. Tối đa điểm tham quan

| Mật độ | Số điểm lớn/ngày | Phù hợp |
|--------|------------------|---------|
| Thoải mái | 1-2 | Nghỉ dưỡng, người già, trẻ em |
| Vừa phải (mặc định) | 2-3 | Đa số du khách |
| Nhanh | 3-4 | Người trẻ, khỏe, thích khám phá |

## 2. Sắp xếp theo thời gian

### 2.1. Buổi sáng (6h-11h)
- Địa điểm ngoài trời: thắng cảnh, công viên, biển, núi
- Hoạt động cần sức: trekking, tham quan di tích rộng
- Check-out khách sạn (nếu có)
- Ăn sáng: 7h-9h

### 2.2. Buổi trưa (11h-14h)
- Ăn trưa
- Nghỉ trưa / check-in khách sạn
- Tránh nắng (mùa hè): ưu tiên địa điểm trong nhà
- Trẻ em ngủ trưa

### 2.3. Buổi chiều (14h-17h)
- Địa điểm trong nhà: bảo tàng, mua sắm, café
- Hoạt động nhẹ: dạo phố, chợ
- Khi trời mưa: đổi sang điểm trong nhà

### 2.4. Buổi tối (18h-22h)
- Ăn tối
- Hoạt động giải trí: phố đi bộ, chợ đêm, bar
- Điểm có view hoàng hôn hoặc ánh sáng đẹp

## 3. Điều chỉnh theo đối tượng

### Trẻ em
- Giảm 1 điểm/ngày so với mặc định
- Mỗi 2h nghỉ 15-30 phút
- Có điểm vui chơi hoặc không gian rộng
- Không leo núi hoặc đi bộ > 3km/ngày
- Có bữa ăn phù hợp trẻ em

### Người già
- Giảm quãng đường đi bộ (< 2km/ngày)
- Hạn chế leo cầu thang
- Có chỗ ngồi nghỉ dọc đường
- Tránh nắng gắt, ưu tiên điểm có bóng mát
- Thời gian di chuyển giữa các điểm ≤ 30 phút

### Cặp đôi
- Có điểm lãng mạn: hoàng hôn, café view, nhà hàng rooftop
- Thời gian tự do nhiều hơn
- Có thể thêm 1 bữa tối cao cấp

### Đi một mình
- Tiết kiệm tối đa (ăn uống bình dân, hostel)
- Có điểm giao lưu: phố Tây, tour ghép, lớp học nấu ăn

## 4. Điều chỉnh theo thời tiết

### Trời nắng / mùa hè
- Sáng sớm và chiều tối hoạt động ngoài trời
- Giữa trưa (11h-14h): trong nhà, có máy lạnh
- Mang nước, kem chống nắng, mũ

### Trời mưa
- Đổi điểm ngoài trời → trong nhà
- Có plan B trong nhà: bảo tàng, trung tâm thương mại, spa
- Hạn chế di chuyển xa

### Mùa đông / lạnh
- Ưu tiên điểm trong nhà buổi tối
- Hoạt động ngoài trời vào trưa ấm nhất
- Gợi ý món ăn ấm (lẩu, cháo, súp)

## 5. Lưu ý thời gian cụ thể

- Check-in: 14h-15h
- Check-out: 11h-12h
- Nhà hàng đông: 11h30-12h30 (trưa), 18h30-19h30 (tối)
- Bảo tàng thường đóng cửa: 17h
- Chợ đêm: 18h-23h

## 6. Format mỗi ngày

```
### Ngày [N] — [Tiêu đề ngày]

**Buổi sáng:**
- [Giờ] — [Hoạt động]

**Buổi trưa:**
- [Giờ] — [Hoạt động]

**Buổi chiều:**
- [Giờ] — [Hoạt động]

**Buổi tối:**
- [Giờ] — [Hoạt động]
```
