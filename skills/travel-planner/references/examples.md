# Ví dụ về cấu trúc

> ⚠️ **Mọi con số dưới đây là placeholder minh họa định dạng.** Không lấy bất kỳ giá, rating hay tên địa điểm nào từ file này đưa vào câu trả lời thật. Giá thật phải tra trong phiên làm việc.

---

## Ví dụ: gia đình có trẻ nhỏ, 4 ngày

**Input:** Hà Nội → Đà Nẵng · 4 ngày · 2 người lớn + 2 trẻ (5 và 8 tuổi) · budget [X] VND · 4 sao · máy bay · thiên nhiên + giải trí

**Output:**

```markdown
# Tổng quan
Đà Nẵng 4 ngày 3 đêm, gia đình 2 người lớn + 2 trẻ em.
Tổng dự kiến: ~[TỔNG] VND — trong ngân sách, còn dư [X].

# Vé di chuyển
- [Hãng]: Hà Nội → Đà Nẵng, [giá]/người (tham khảo, nguồn: [nguồn])
- [Hãng]: Đà Nẵng → Hà Nội, [giá]/người
- Tổng: [giá] VND cho 4 người

# Chỗ ở
**Top pick — [Tên khách sạn] (4 sao)**
- Địa chỉ: [địa chỉ]
- Rating: [x.x]/5 ([n] review) — nguồn: [nguồn]
- Hồ bơi, phòng gia đình, buffet sáng → phù hợp trẻ nhỏ
- [giá]/đêm × 3 đêm = [tổng]

**Rẻ hơn:** [Tên] — [giá]/đêm, cách trung tâm [n] km
**Cao cấp hơn:** [Tên] — [giá]/đêm, sát biển

# Lịch trình từng ngày

### Ngày 1 — Bay vào, làm quen biển

**Buổi sáng:**
- 07:00 — Ra sân bay Nội Bài
- 09:00 — Bay Hà Nội → Đà Nẵng
- 10:30 — Đến nơi, di chuyển về khách sạn

**Buổi trưa:**
- 12:00 — Ăn trưa tại [quán], gần khách sạn
- 13:30 — Check-in, nghỉ trưa (trẻ nhỏ ngủ)

**Buổi chiều:**
- 15:30 — Bãi biển Mỹ Khê — nắng đã dịu, trẻ chơi cát
- 17:30 — Về khách sạn

**Buổi tối:**
- 18:30 — Ăn tối tại [quán hải sản], có ghế trẻ em
- 20:00 — Dạo cầu Rồng

### Ngày 2 — [Tiêu đề]
...

# Nhà hàng
| Ngày | Bữa | Tên quán | Món | Giá | Rating |
|------|-----|----------|-----|-----|--------|
| 1 | Trưa | [tên] | [món] | [giá] | [x.x] |

# Tổng chi phí
| Khoản mục | Số tiền (VND) | Ghi chú |
|-----------|---------------|---------|
| Vé máy bay | [x] | |
| Chỗ ở (3 đêm) | [x] | |
| Ăn uống | [x] | baseline trung bình |
| Di chuyển nội thành | [x] | Grab |
| Vé tham quan | [x] | |
| Phát sinh (10%) | [x] | |
| **Tổng** | **[x]** | |

# Mẹo
- [Mẹo riêng cho Đà Nẵng — VD thời điểm nên tránh Bà Nà vì đông]
- [Mẹo về đi lại]
- [Mẹo về ăn uống]
```

---

## Ghi chú cho chuyến nước ngoài

Cấu trúc giữ nguyên, khác ở hai chỗ:

- **Tiền tệ kép** — giá gốc bằng nội tệ điểm đến, quy đổi kèm ngày tra tỷ giá: `400–800 THB (≈ [x] VND, tỷ giá [ngày])`
- **Mẹo bổ sung** — sim/eSIM, app gọi xe địa phương, đổi tiền ở đâu, quy định trang phục nơi tôn giáo
