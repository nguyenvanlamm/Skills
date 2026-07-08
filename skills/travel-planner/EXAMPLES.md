# Examples

## 1. Du lịch gia đình (Đà Nẵng — 4 ngày, 2 người lớn + 2 trẻ em)

**Input:**
- departure: Hà Nội
- destination: Đà Nẵng
- days: 4
- adults: 2
- children: 2 (5 tuổi và 8 tuổi)
- budget: 20.000.000 VND
- hotel_level: 4 sao
- transportation: Máy bay
- interests: thiên nhiên, giải trí

**Output:**
```
# Tổng quan
Chuyến đi Đà Nẵng 4 ngày 3 đêm cho gia đình 2 người lớn + 2 trẻ em.
Tổng chi phí dự kiến: ~17.500.000 VND (trong ngân sách).

# Vé di chuyển
- Vietnam Airlines: Hà Nội → Đà Nẵng, 1.200.000 VND/người (tham khảo)
- Vietnam Airlines: Đà Nẵng → Hà Nội, 1.200.000 VND/người (tham khảo)
- Tổng vé máy bay: 4.800.000 VND

# Khách sạn
- Novotel Danang Premier Han River (4 sao)
- Địa chỉ: 36 Bạch Đằng, Đà Nẵng
- Rating: 4.5/5 (2.800+ review)
- Hồ bơi, phòng gia đình, buffet sáng
- Giá: ~1.800.000 VND/đêm
- 3 đêm: 5.400.000 VND

# Lịch trình từng ngày

### Ngày 1 — Hà Nội → Đà Nẵng, check-in

Buổi sáng:
- 07:00 — Ra sân bay Nội Bài
- 09:00 — Bay Hà Nội → Đà Nẵng
- 10:30 — Đến Đà Nẵng, di chuyển về khách sạn

Buổi trưa:
- 12:00 — Ăn trưa tại Mỳ Quảng Bà Vị (gần khách sạn)
- 13:30 — Check-in khách sạn, nghỉ ngơi

Buổi chiều:
- 15:30 — Bãi biển Mỹ Khê (cho trẻ em chơi cát, bơi)
- 17:30 — Về khách sạn tắm rửa

Buổi tối:
- 18:30 — Ăn tối tại Nhà hàng Bến Lội (hải sản, trẻ em có ghế ngồi)
- 20:00 — Dạo cầu Rồng, xem cầu quay

### Ngày 2 — Bà Nà Hills

Buổi sáng:
- 07:00 — Ăn sáng tại khách sạn
- 08:00 — Di chuyển lên Bà Nà Hills
- 09:00 — Tham quan Cầu Vàng, chụp ảnh
- 11:00 — Khu vườn hoa Le Jardin d'Amour

Buổi trưa:
- 12:00 — Ăn trưa tại nhà hàng trong khu Bà Nà
- 13:30 — Khu giải trí Fantasy Park (trẻ em thích)

Buổi chiều:
- 15:30 — Xuống núi, về khách sạn
- 17:00 — Nghỉ ngơi

Buổi tối:
- 18:30 — Ăn tối tại Chả Cá Lục Vân (cá lăng nướng)
- 20:00 — Dạo phố đi bộ Bạch Đằng

### Ngày 3 — Hội An (tối)

Buổi sáng:
- 07:30 — Ăn sáng buffet khách sạn
- 08:30 — Di chuyển xuống Hội An (30km)
- 09:30 — Tham quan Phố cổ Hội An: Chùa Cầu, nhà cổ
- 11:30 — Ăn trưa tại Cao Lầu Bá Lễ

Buổi chiều:
- 13:00 — Về khách sạn, cho trẻ ngủ trưa
- 15:00 — Bơi hồ bơi khách sạn
- 17:00 — Di chuyển trở lại Hội An

Buổi tối:
- 18:00 — Đi thuyền hoa đăng trên sông Hoài
- 19:00 — Ăn tối tại White Rose
- 20:00 — Thả đèn hoa đăng, dạo chợ đêm

### Ngày 4 — Sơn Trà, về Hà Nội

Buổi sáng:
- 07:00 — Ăn sáng
- 08:00 — Check-out khách sạn, gửi hành lý
- 08:30 — Bán đảo Sơn Trà, chùa Linh Ứng, ngắm view
- 10:30 — Chợ Cồn (mua quà)

Buổi trưa:
- 12:00 — Ăn trưa tại Bánh Tráng Thịt Heo Mệ Tuyết
- 13:30 — Về khách sạn lấy hành lý, ra sân bay

Buổi chiều:
- 15:30 — Bay Đà Nẵng → Hà Nội

# Nhà hàng

| Ngày | Bữa | Tên quán | Món | Giá | Rating |
|------|-----|----------|-----|-----|--------|
| 1 | Trưa | Mỳ Quảng Bà Vị | Mỳ Quảng | 35k-50k | 4.4 |
| 1 | Tối | Bến Lội | Hải sản | 200k-400k/ng | 4.5 |
| 2 | Sáng | Buffet khách sạn | — | free | — |
| 2 | Tối | Chả Cá Lục Vân | Cá lăng | 150k-250k | 4.3 |
| 3 | Trưa | Cao Lầu Bá Lễ | Cao lầu | 30k-50k | 4.4 |
| 3 | Tối | White Rose | Bánh bao, hoành thánh | 20k-50k | 4.5 |
| 4 | Trưa | Mệ Tuyết | Bánh tráng cuốn | 50k-80k | 4.3 |

# Điểm tham quan

| Điểm | Giá vé | Thời gian |
|------|--------|-----------|
| Bà Nà Hills | 750k/ng lớn, 600k/trẻ | Cả ngày |
| Cầu Vàng | Trong vé Bà Nà | 30 phút |
| Phố cổ Hội An | 120k/ng (5 điểm) | 2-3 giờ |
| Bán đảo Sơn Trà | Free | 2 giờ |
| Biển Mỹ Khê | Free | 1-2 giờ |

# Tổng chi phí

| Khoản mục | Số tiền |
|-----------|---------|
| Vé máy bay | 4.800.000 |
| Khách sạn (3 đêm) | 5.400.000 |
| Ăn uống (4 ngày) | 2.500.000 |
| Bà Nà Hills vé | 2.700.000 |
| Taxi/Thuê xe | 1.500.000 |
| Vé tham quan + thuyền | 500.000 |
| Phát sinh 10% | 1.100.000 |
| Tổng | ~17.500.000 |

Trong ngân sách 20.000.000, còn dư ~2.500.000.

# Mẹo
- Đặt vé máy bay trước 2-3 tuần để có giá tốt
- Bà Nà Hills nên đi ngày thường để tránh đông
- Mang áo khoác khi lên Bà Nà (nhiệt độ thấp hơn)
- Thuê xe riêng (700k-900k/ngày) nếu đi Hội An + Bà Nà
```

---

## 2. Du lịch cặp đôi (Đà Lạt — 3 ngày, 2 người lớn)

**Input:**
- departure: Sài Gòn
- destination: Đà Lạt
- days: 3
- adults: 2
- budget: 10.000.000 VND
- hotel_level: 4 sao
- transportation: Xe khách
- interests: thiên nhiên, ẩm thực, chụp ảnh

**Output:**
```
# Tổng quan
Chuyến đi Đà Lạt 3 ngày 2 đêm cho cặp đôi.
Tổng chi phí dự kiến: ~9.000.000 VND (trong ngân sách).

# Vé di chuyển
- Xe Limousine Sài Gòn → Đà Lạt: 350.000 VND/người (tham khảo)
- Xe Limousine Đà Lạt → Sài Gòn: 350.000 VND/người
- Tổng: 1.400.000 VND

# Khách sạn
- Ana Mandara Villas Dalat (4 sao)
- Địa chỉ: Đường Lê Lai, Đà Lạt
- Rating: 4.6/5 (1.500+ review)
- Phong cách Pháp cổ, view đồi thông
- Giá: ~1.500.000 VND/đêm
- 2 đêm: 3.000.000 VND

# Lịch trình

### Ngày 1 — Đến Đà Lạt, khám phá trung tâm

Buổi sáng:
- 07:00 — Xuất phát từ Sài Gòn
- 12:00 — Đến Đà Lạt, check-in homestay

Buổi trưa:
- 12:30 — Ăn trưa tại Bánh Căn Nhà Gỗ
- 13:30 — Nghỉ ngơi

Buổi chiều:
- 15:00 — Quảng trường Lâm Viên, hồ Xuân Hương
- 16:30 — Café Mộc (view đẹp, chụp ảnh)

Buổi tối:
- 18:30 — Ăn tối tại Lẩu Gà Lá É
- 20:00 — Chợ Đà Lạt, chợ âm thực

### Ngày 2 — Thiên nhiên và săn mây

Buổi sáng:
- 05:00 — Săn mây tại Cầu Đất Farm (chụp bình minh)
- 08:00 — Ăn sáng tại Tiệm Bánh Cối Xay Gió
- 09:00 — Thung lũng Tình Yêu

Buổi trưa:
- 12:00 — Ăn trưa tại Dũng Béo (đặc sản Đà Lạt)
- 13:30 — Về homestay nghỉ

Buổi chiều:
- 15:00 — Đồi chè Cầu Đất
- 17:00 — Café Tùng (view hoàng hôn)

Buổi tối:
- 18:30 — Ăn tối tại Nem Nướng Bà Hùng
- 20:00 — Dạo Hồ Xuân Hương tối

### Ngày 3 — Tham quan nhẹ, về Sài Gòn

Buổi sáng:
- 08:00 — Ăn sáng tại Bánh Mì Nguyên Sơn
- 09:00 — Thiền viện Trúc Lâm + hồ Tuyền Lâm
- 11:00 — Vườn hoa Cẩm Tú Cầu

Buổi trưa:
- 12:00 — Ăn trưa tại Cơm Niêu Đà Lạt
- 13:30 — Về homestay lấy đồ, ra xe

Buổi chiều:
- 14:00 — Về Sài Gòn

# Tổng chi phí
| Khoản | Số tiền |
|-------|---------|
| Xe Limousine | 1.400.000 |
| Homestay (2 đêm) | 3.000.000 |
| Ăn uống | 1.800.000 |
| Thuê xe máy (3 ngày) | 450.000 |
| Vé tham quan | 400.000 |
| Café | 300.000 |
| Phát sinh 10% | 650.000 |
| Tổng | ~9.000.000 |

# Mẹo
- Săn mây nên đi 4-5h sáng, mang áo ấm
- Đặt xe limousine trước 1 ngày
- Thuê xe máy 150k/ngày để chủ động di chuyển
```

---

## 3. Du lịch tiết kiệm (Phú Quốc — 3 ngày, 2 người lớn)

**Input:**
- departure: Cần Thơ
- destination: Phú Quốc
- days: 3
- adults: 2
- budget: 6.000.000 VND
- hotel_level: 2 sao
- transportation: Xe khách + Phà
- interests: thiên nhiên, biển

**Output:**
```
# Tổng quan
Chuyến đi Phú Quốc 3 ngày 2 đêm tiết kiệm cho 2 người.
Tổng chi phí: ~5.500.000 VND (trong ngân sách).

# Vé di chuyển
- Xe khách Cần Thơ → Rạch Giá: 120.000 VND/người
- Phà Rạch Giá → Phú Quốc: 200.000 VND/người
- Ngược lại: tương tự
- Tổng: 1.280.000 VND

# Khách sạn
- Nhà nghỉ Bình Minh (gần bãi Trường)
- Rating: 4.0/5 (120 review)
- Giá: 400.000 VND/đêm
- 2 đêm: 800.000 VND

# Lịch trình

### Ngày 1 — Di chuyển, bãi biển

Sáng: Đi xe + phà
Trưa: 12h đến PQ, ăn trưa Bún Quậy Kiến Xây
Chiều: Bãi Trường tắm biển
Tối: Chợ đêm Phú Quốc (hải sản bình dân)

### Ngày 2 — Dây Dưa + Bãi Sao

Sáng: 7h đi Dây Dưa (snorkel)
Trưa: Bãi Sao, ăn trưa hải sản
Chiều: Nhà thùng nước mắm + vườn tiêu
Tối: Ăn bánh canh ghẹ

### Ngày 3 — Chợ, về

Sáng: Chợ Dương Đông mua quà
Trưa: 12h xuống phà về

# Tổng chi phí
| Khoản | Số tiền |
|-------|---------|
| Xe + Phà | 1.280.000 |
| Nhà nghỉ (2 đêm) | 800.000 |
| Ăn uống | 1.500.000 |
| Thuê xe máy (2 ngày) | 300.000 |
| Vé tham quan | 600.000 |
| Phát sinh | 500.000 |
| Tổng | ~5.500.000 |

# Mẹo
- Mang đồ ăn nhẹ đi phà
- Thuê xe máy 150k/ngày tiết kiệm nhất
- Mua hải sản ở chợ Dương Đông rẻ hơn chợ đêm
```

---

## 4. Du lịch nghỉ dưỡng (Phú Quốc — 5 ngày, 2 người lớn)

**Input:**
- departure: Hà Nội
- destination: Phú Quốc
- days: 5
- adults: 2
- budget: 40.000.000 VND
- hotel_level: 5 sao
- transportation: Máy bay
- interests: nghỉ dưỡng, biển, spa

**Output:**
```
# Tổng quan
Chuyến nghỉ dưỡng Phú Quốc 5 ngày 4 đêm, 2 người lớn.
Tổng chi phí: ~37.000.000 VND (trong ngân sách).

# Vé di chuyển
- Vietnam Airlines: Hà Nội → Phú Quốc, 3.500.000 VND/người
- Vietnam Airlines: Phú Quốc → Hà Nội, 3.500.000 VND/người
- Tổng: 14.000.000 VND

# Khách sạn
- JW Marriott Phú Quốc (5 sao)
- Địa chỉ: Bãi Khem, Phú Quốc
- Rating: 4.8/5 (3.200+ review)
- Spa, hồ bơi vô cực, beachfront
- Giá: ~4.000.000 VND/đêm
- 4 đêm: 16.000.000 VND

# Lịch trình (tinh thần nghỉ dưỡng, không gấp)

### Ngày 1 — Bay, check-in resort
Chiều: Bay đến PQ, resort đón, check-in
Tối: Dinner tại resort

### Ngày 2 — Spa + Bãi Khem
Sáng: Ăn sáng buffet, bơi hồ bơi
Trưa: Spa couples massage
Chiều: Bãi Khem tắm biển
Tối: Nhà hàng The Vagabond (Italy)

### Ngày 3 — Sunset Sanato + Grand World
Chiều: Sunset Sanato chụp ảnh
Tối: Grand World (biểu diễn Venice, Casino)

### Ngày 4 — Bãi Sao + Hòn Thơm
Cả ngày: Đi Hòn Thơm (cáp treo 3 dây dài nhất)
Tối: Dinner tại resort

### Ngày 5 — Bay về
Sáng: Ăn sáng, bơi lần cuối
Trưa: Check-out, bay HN

# Tổng chi phí
| Khoản | Số tiền |
|-------|---------|
| Vé máy bay | 14.000.000 |
| Resort (4 đêm) | 16.000.000 |
| Ăn uống | 4.000.000 |
| Cáp treo Hòn Thơm | 1.200.000 |
| Spa | 2.000.000 |
| Phát sinh 10% | 3.200.000 |
| Tổng | ~37.000.000 |

# Mẹo
- Book resort trước 1 tháng giá tốt hơn
- Mang kem chống nắng, mũ, kính râm
- Resort có shuttle bus đi Grand World free
```

---

## 5. Du lịch nước ngoài (Bangkok — 4 ngày, 2 người lớn)

**Input:**
- departure: Hà Nội
- destination: Bangkok, Thái Lan
- days: 4
- adults: 2
- budget: 20.000.000 VND
- hotel_level: 4 sao
- transportation: Máy bay
- interests: văn hóa, ẩm thực, mua sắm

**Output:**
```
# Tổng quan
Bangkok 4 ngày 3 đêm cho 2 người.
Tổng chi phí: ~18.000.000 VND (trong ngân sách).

# Vé di chuyển
- VietJet: Hà Nội → Bangkok (DMK), 1.500.000 VND/người
- VietJet: Bangkok → Hà Nội, 1.500.000 VND/người
- Tổng: 6.000.000 VND

# Khách sạn
- Pullman Bangkok Grand Sukhumvit (4 sao)
- Địa chỉ: Sukhumvit, Bangkok
- Rating: 4.5/5 (2.100+ review)
- Hồ bơi rooftop, gần BTS
- Giá: ~1.800.000 VND/đêm
- 3 đêm: 5.400.000 VND

# Lịch trình

### Ngày 1 — Đến Bangkok, Asiatique

Sáng: Bay HAN → DMK, Grab vào trung tâm
Trưa: Check-in, ăn trưa tại Pad Thai Thipsamai
Chiều: Wat Pho (Phật nằm)
Tối: Asiatique Night Market + dinner

### Ngày 2 — Chùa + Chatuchak

Sáng: Grand Palace + Wat Phra Kaew
Trưa: Ăn Tom Yum Kung tại Jay Fai (nếu xếp hàng được)
Chiều: Chợ Chatuchak (cuối tuần) hoặc Siam Paragon
Tối: Yaowarat (Phố Tàu) ăn tối street food

### Ngày 3 — Floating Market + Rooftop Bar

Sáng: Damnoen Saduak Floating Market
Trưa: Ăn tại quán ven kênh
Chiều: ICONSIAM (mát, siêu to)
Tối: Rooftop Bar Tichuca (view Bangkok)

### Ngày 4 — Mua sắm, về

Sáng: MBK Center mua quà
Trưa: 12h ra sân bay
Chiều: Bay Bangkok → Hà Nội

# Nhà hàng
- Jay Fai: Tom Yum Kung, 400-800 THB/món, ★ Michelin
- Thipsamai: Pad Thai, 100-200 THB
- Yaowarat: Street food, 50-100 THB/món
- Tichuca Rooftop Bar: 300-600 THB/drink

# Tổng chi phí
| Khoản | VND |
|-------|-----|
| Vé máy bay | 6.000.000 |
| KS (3 đêm) | 5.400.000 |
| Ăn uống | 2.500.000 |
| Grab + BTS | 1.500.000 |
| Vé tham quan | 1.000.000 |
| Shopping | 1.000.000 |
| Phát sinh | 1.100.000 |
| Tổng | ~18.000.000 |

# Mẹo
- Mua sim Thái 7 ngày ở sân bay (~200 THB)
- Cài Grab (xe máy rẻ hơn taxi)
- Đổi Bath trước ở HN hoặc ATM ở BKK
- Mặc quần dài, kín vai vào Grand Palace
```
