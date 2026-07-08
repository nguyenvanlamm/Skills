# Input Schema

## Danh sách trường đầu vào

| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|------|----------|-------|
| `departure` | string | ✅ | Điểm xuất phát (thành phố/tỉnh) |
| `destination` | string | ✅ | Điểm đến (thành phố/tỉnh/quốc gia) |
| `days` | integer | ✅ | Số ngày du lịch |
| `adults` | integer | ❌ | Số người lớn (mặc định: 2) |
| `children` | integer | ❌ | Số trẻ em (mặc định: 0) |
| `budget` | integer | ❌ | Tổng ngân sách (VND hoặc USD) |
| `hotel_level` | enum | ❌ | 2 sao, 3 sao, 4 sao, 5 sao |
| `transportation` | enum | ❌ | Máy bay, Xe khách, Tàu, Ô tô |
| `interests` | array | ❌ | Sở thích: văn hóa, ẩm thực, thiên nhiên, mua sắm, giải trí, lịch sử |
| `pace` | enum | ❌ | Tốc độ: thoải mái, vừa phải, nhanh (mặc định: vừa phải) |
| `cuisine` | string | ❌ | Loại ẩm thực mong muốn (VD: hải sản, chay, đặc sản địa phương) |
| `special_requirements` | string | ❌ | Yêu cầu đặc biệt (VD: người già đi bộ khó, cần xe lăn, dị ứng thực phẩm) |
| `start_date` | date | ❌ | Ngày khởi hành (để tra thời tiết, giá mùa) |

## Định dạng khi hỏi

Nếu người dùng chưa cung cấp đủ, hãy hỏi dạng:

> "Mình cần thêm vài thông tin để lên lịch tốt nhất nhé:
> - Điểm xuất phát của bạn là...?
> - Bạn muốn đi trong bao nhiêu ngày?
> - Ngân sách dự kiến khoảng bao nhiêu?
> - Bạn đi cùng gia đình, bạn bè hay một mình?"
