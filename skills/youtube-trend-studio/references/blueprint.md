# Đánh giá kênh và viết blueprint

## Thang "Claude làm được không?"

Chấm mỗi tiêu chí 0, 1 hoặc 2 điểm, tổng trên 10. Từ 8 điểm là ứng viên tốt, 5 đến 7 là làm được nhưng cần người dùng góp thêm, dưới 5 thì loại.

| Tiêu chí | 0 điểm | 1 điểm | 2 điểm |
|---|---|---|---|
| **Người dẫn** | Lộ mặt, cá tính người dẫn là lý do xem | Có giọng người thật đặc trưng | Faceless, giọng đọc trung tính hoặc TTS |
| **Nguồn hình** | Tự quay, footage độc quyền, gameplay | Stock và ảnh tư liệu cần tìm và xin phép | Slide, biểu đồ, bản đồ, minh hoạ tạo được bằng code hoặc AI |
| **Giá trị nằm ở đâu** | Trải nghiệm, phản ứng, quan hệ với cộng đồng | Pha trộn | Thông tin và cách kể, tức là kịch bản |
| **Nguồn kiến thức** | Tin độc quyền, trải nghiệm riêng, tin nóng theo giờ | Cần cập nhật theo tuần | Kiến thức tra cứu và kiểm chứng được |
| **Độ phức tạp dựng** | Hoạt hình nhân vật, dựng phim nhiều lớp | Motion graphics vừa phải | Cắt cảnh đơn giản, chữ, zoom nhẹ |

Ghi kèm mỗi điểm số là dựa trên điều đã thấy (đã xem video, đã xem thumbnail) hay suy ra từ tiêu đề và mô tả. Đừng cho 2 điểm ở "Người dẫn" chỉ vì tiêu đề nghe giống kênh faceless.

Hai câu hỏi phụ quyết định có nên theo hay không:

- **Còn chỗ không?** Nếu đã có 20 kênh giống hệt nhau cùng mọc lên trong ba tháng, công thức đã bão hoà. Tìm biến thể: cùng định dạng nhưng ngách hẹp hơn, ngôn ngữ khác, hoặc độ dài khác.
- **Người dùng có theo nổi nhịp không?** Kênh mẫu đăng 7 video mỗi tuần mà người dùng chỉ làm được 2 thì cần chọn công thức khác hoặc tính lại.

## Mẫu blueprint

Lưu thành `research/blueprint_<tên-kênh>.md`. Mỗi mục ghi điều quan sát được kèm bằng chứng (video nào, số nào), không ghi cảm nhận chung chung.

```markdown
# Blueprint: <tên kênh mẫu> (<link>)
Ngày phân tích: <YYYY-MM-DD> · Mẫu: <N> video gần nhất · Điểm làm được: <x>/10

## 1. Lời hứa của kênh
Một câu: kênh này cho ai, họ nhận được gì, khác các kênh cùng ngách ở đâu.

## 2. Số liệu
- Tuổi kênh, sub, median view, view/sub, nhịp đăng, ngày giờ đăng thường gặp
- Độ dài: median, khoảng dao động, tỷ lệ Shorts

## 3. Chủ đề thắng và thua
- Nhóm chủ đề của các outlier (từ 2 lần median): ...
- Nhóm chủ đề của video kém (từ 0,5 lần median trở xuống): ...
- Giả thuyết vì sao: ...

## 4. Công thức tiêu đề
- 2 đến 3 khuôn tiêu đề, viết dạng trừu tượng. Ví dụ: "[Con số] + [điều tưởng đã biết] + [bị lật ngược]"
- Độ dài, có số hay không, câu hỏi hay khẳng định, từ in hoa

## 5. Quy ước thumbnail
- Số chữ, màu chủ đạo, bố cục, có mặt người hay không, quan hệ giữa chữ thumbnail và tiêu đề

## 6. Cấu trúc video
- Hook (0 đến 15 giây): kiểu mở đầu, có chào hỏi không
- Thân bài: số phần, độ dài mỗi phần, cách kéo lại sự chú ý giữa các phần
- Kết: tóm tắt, câu hỏi cho bình luận, dẫn sang video khác
- Nhịp hình: trung bình mấy giây đổi cảnh, loại hình ảnh chính

## 7. Giọng và lời
- Xưng hô, tốc độ nói, độ dài câu, mức độ hài hước hay nghiêm túc, nhạc nền

## 8. Kế hoạch của mình
- Giữ lại: những yếu tố định dạng sẽ áp dụng
- Làm khác: góc nhìn, nhận diện, giọng riêng để không thành bản sao
- Khoảng trống: chủ đề khán giả của ngách muốn mà kênh mẫu chưa làm (đọc bình luận nếu xem được)
- Mục tiêu video đầu: độ dài, số cảnh, giọng đọc, nguồn hình

## 9. Điều chưa kiểm chứng
- Những nhận định suy ra từ metadata, cần người dùng xem xác nhận
```

## Đề xuất chủ đề

Sau blueprint, đưa 5 chủ đề cho video đầu. Với mỗi chủ đề:

- **Tiêu đề dự kiến**, theo một khuôn ở mục 4
- **Góc nhìn**: một câu nói video này khẳng định điều gì
- **Khớp mẫu nào**: outlier nào của kênh mẫu cho thấy khán giả thích dạng này
- **Khác ở đâu**: kênh mẫu chưa làm chủ đề này, hoặc đã làm nhưng mình có góc khác

Chủ đề thì ai cũng làm được, nên trùng chủ đề với kênh mẫu không sai. Làm lại đúng video của họ theo từng ý thì sai, và cũng không có lý do gì để khán giả chọn bản đến sau.
