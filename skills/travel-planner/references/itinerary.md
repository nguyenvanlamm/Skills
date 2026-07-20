# Lập lịch trình

## 1. Mật độ điểm tham quan

Định nghĩa duy nhất về số điểm/ngày. Không file nào khác được đặt trần khác.

| `pace` | Điểm lớn/ngày | Phù hợp |
|--------|---------------|---------|
| Thoải mái | 1–2 | Nghỉ dưỡng, có người già hoặc trẻ nhỏ |
| Vừa phải (mặc định) | 2–3 | Đa số du khách |
| Nhanh | 3–4 | Người trẻ, khỏe, thích khám phá |

"Điểm lớn" = nơi cần ≥1 giờ tham quan. Quán ăn, café, dạo phố không tính.

Điều chỉnh theo đối tượng cộng dồn với bảng trên, nhưng **sàn cứng là 1 điểm lớn/ngày** — một ngày không có điểm nào là lịch trình hỏng, không phải lịch trình thoải mái.

## 2. Tối ưu lộ trình

**Không đi ngược đường.** Sắp xếp các điểm theo một tuyến liên tục từ sáng đến tối. Không quay lại khu vực đã rời khỏi (sáng ở A → chiều sang B → tối lại về A).

**Gom theo cụm.** Nhóm các điểm gần nhau vào cùng một buổi, và chỉ di chuyển giữa các cụm 1 lần/ngày.

> Cụm trung tâm: Hồ Gươm, Nhà thờ Lớn, Phố cổ
> Cụm Tây Hồ: Chùa Trấn Quốc, Phủ Tây Hồ

Trước khi chốt thứ tự, kiểm tra khoảng cách thực tế giữa các điểm (xem `search.md`) — đừng dựa vào cảm giác về bản đồ.

## 3. Khung giờ trong ngày

**Sáng (6h–11h)** — điểm ngoài trời: thắng cảnh, công viên, biển, núi. Hoạt động cần sức: trekking, di tích rộng. Ăn sáng 7h–9h. Check-out nếu đổi chỗ ở.

**Trưa (11h–14h)** — ăn trưa, nghỉ, check-in. Mùa nóng: ưu tiên điểm trong nhà. Trẻ nhỏ ngủ trưa.

**Chiều (14h–17h)** — bảo tàng, mua sắm, café, chợ, dạo phố. Đây cũng là khung dự phòng khi trời mưa.

**Tối (18h–22h)** — ăn tối, phố đi bộ, chợ đêm, điểm có view hoàng hôn hoặc đèn đêm.

Mốc giờ thường gặp: check-in 14h–15h, check-out 11h–12h; bảo tàng đóng cửa ~17h; chợ đêm 18h–23h. Nhà hàng đông nhất 11h30–12h30 và 18h30–19h30 — né các khung này nếu đi đông người.

## 4. Điều chỉnh theo đối tượng

**Trẻ em** — giảm 1 điểm/ngày so với `pace` (không xuống dưới sàn 1 điểm). Nghỉ 15–30 phút sau mỗi 2 giờ. Đi bộ ≤ 3 km/ngày. Không leo núi. Có ít nhất 1 điểm vui chơi hoặc không gian rộng trong chuyến đi.

**Người già** — đi bộ ≤ 2 km/ngày, hạn chế cầu thang, di chuyển giữa các điểm ≤ 30 phút. Cần chỗ ngồi nghỉ dọc đường và bóng mát. Tránh khung nắng gắt.

**Cặp đôi** — thêm điểm lãng mạn (hoàng hôn, café view, rooftop), chừa nhiều thời gian tự do hơn, có thể thêm 1 bữa tối cao cấp.

**Đi một mình** — nghiêng về tiết kiệm (hostel, quán bình dân) và thêm điểm giao lưu: phố Tây, tour ghép, lớp học nấu ăn.

Nếu `special_requirements` có yêu cầu về vận động (xe lăn, đi bộ khó), nó **ghi đè** mọi mục trên: kiểm tra khả năng tiếp cận của từng điểm trước khi đưa vào lịch.

## 5. Điều chỉnh theo thời tiết

Chỉ áp dụng khi đã tra được dự báo hoặc khí hậu mùa cho `start_date`. Không suy đoán thời tiết.

**Nắng nóng** — hoạt động ngoài trời dồn vào sáng sớm và chiều muộn; 11h–14h ở trong nhà có máy lạnh. Nhắc mang nước, mũ, kem chống nắng.

**Mưa** — đổi điểm ngoài trời sang trong nhà, hạn chế di chuyển xa. Mỗi ngày nên có sẵn một phương án B trong nhà.

**Lạnh** — hoạt động ngoài trời vào khung trưa ấm nhất, buổi tối ưu tiên trong nhà, gợi ý món ăn nóng.

## 6. Định dạng mỗi ngày

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
