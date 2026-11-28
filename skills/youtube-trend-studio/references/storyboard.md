# Định dạng storyboard.json

`build_video.py` đọc một file JSON mô tả toàn bộ video. Mẫu đầy đủ: `assets/storyboard.example.json`.

## Cấp video

| Trường | Mặc định | Ý nghĩa |
|---|---|---|
| `title` | | Tên video, chỉ để ghi vào báo cáo |
| `resolution` | `[1920, 1080]` | `[1080, 1920]` cho Shorts. Bố cục tự co theo khung |
| `fps` | `30` | |
| `voice` | `en-US-AriaNeural` | Giọng edge-tts, ví dụ `vi-VN-HoaiMyNeural` |
| `tts` | `edge` | `edge`, `cmd`, `files`, `silent`. Tham số `--tts` ghi đè |
| `style` | | `bg`, `fg`, `muted`, `accent` (mã màu hex), `font`, `font_bold` (đường dẫn .ttf), `overlay` (0 đến 1, độ tối phủ lên ảnh nền) |
| `scenes` | bắt buộc | Danh sách cảnh, theo thứ tự |

Font mặc định được dò trong hệ thống (Noto Sans, DejaVu Sans, Arial, Segoe UI), đều có dấu tiếng Việt. Muốn nhận diện riêng thì đặt `style.font` và `style.font_bold` tới file .ttf có giấy phép dùng (Google Fonts là nguồn an toàn).

## Cấp cảnh

| Trường | Ý nghĩa |
|---|---|
| `id` | Tên ngắn không dấu. Dùng để khớp file thu âm khi `--tts files` |
| `narration` | Lời đọc. Thời lượng cảnh bằng độ dài lời đọc cộng `pause` |
| `heading` | Chữ chính trên màn hình |
| `body` | Chữ phụ, xuống dòng bằng `\n` |
| `kicker` | Nhãn nhỏ phía trên heading ("Phần 1", "Sai lầm số 3") |
| `layout` | `title`, `text`, `caption`. Xem bên dưới |
| `image` | Ảnh nền, đường dẫn tương đối so với file storyboard |
| `image_fit` | `cover` (mặc định, cắt cho kín khung) hoặc `contain` (giữ nguyên ảnh). Biểu đồ và sơ đồ nên dùng `contain` cùng layout `caption` để không bị cắt hay làm tối |
| `video` | Clip nền thay cho ảnh. Tự lặp hoặc cắt cho vừa thời lượng cảnh, tiếng gốc của clip bị bỏ |
| `overlay` | Độ tối phủ lên ảnh hoặc clip của riêng cảnh này |
| `motion` | `zoom` hoặc `none`. Mặc định ảnh nền được zoom chậm, chữ đứng yên |
| `pause` | Khoảng lặng sau lời đọc, mặc định 0,35 giây |
| `duration` | Thời lượng tối thiểu. Cảnh không có lời đọc mặc định dài 3 giây |
| `chapter` | Tên chương. Cảnh có trường này được ghi mốc thời gian vào `chapters.txt` |

## Ba layout

- **`title`**: heading lớn căn giữa. Dùng cho hook, chuyển phần, câu chốt.
- **`text`** (mặc định): kicker, heading, body căn trái. Dùng cho nội dung chính. Có ảnh hoặc clip nền thì nền được làm tối để chữ nổi.
- **`caption`** (mặc định khi cảnh có ảnh mà không có body): ảnh hoặc clip chiếm toàn khung, heading nằm trên dải tối phía dưới. Ở khung dọc, dải chữ tự nâng lên để tránh giao diện Shorts.

Chữ dài quá sẽ tự thu nhỏ cho vừa, nhưng chữ nhỏ là dấu hiệu nên cắt bớt. Kiểm tra bằng `--only-frames`.

## Viết cảnh cho tốt

- **Một cảnh, một ý.** Cảnh dài quá 15 giây mà hình không đổi thì người xem bỏ đi. Tách ra, hoặc dùng clip nền.
- **Chữ trên màn hình bổ sung cho lời đọc**, không lặp lại nó. Lời đọc giải thích, màn hình hiện con số, từ khoá hoặc kết luận.
- **Cảnh đầu quyết định tất cả.** Dành nhiều công nhất cho 15 giây đầu: hình mạnh nhất, câu gọn nhất.
- **Xen kẽ layout** theo nhịp trong blueprint để video không đều đều: `title` để ngắt, `text` để giải thích, `caption` để cho xem.
- **Đặt `chapter`** ở cảnh mở đầu mỗi phần. YouTube cần chương đầu tại 00:00, ít nhất 3 chương, mỗi chương từ 10 giây.
- **Lời đọc viết cho TTS**: viết số bằng chữ khi cách đọc có thể sai ("năm 1969" thường ổn, "3,5%" nên viết "ba phẩy năm phần trăm"), phiên âm tên nước ngoài nếu giọng Việt đọc sai, bỏ ký hiệu và ngoặc đơn.

## Ví dụ một cảnh

```json
{
  "id": "tam-phut",
  "chapter": "Ánh sáng đi mất bao lâu",
  "layout": "text",
  "kicker": "Phần 2",
  "heading": "Hơn tám phút để tới Trái Đất",
  "body": "Bạn luôn nhìn thấy Mặt Trời của tám phút trước.",
  "image": "assets/mat-troi.jpg",
  "overlay": 0.7,
  "narration": "Ánh sáng rời Mặt Trời phải mất hơn tám phút mới tới được mắt bạn. Nghĩa là mỗi lần ngẩng lên, bạn đang nhìn về quá khứ."
}
```
