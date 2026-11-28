# Cài đặt một lần

Mục lục: 1. Phần mềm · 2. API key (tìm kênh) · 3. OAuth client (đăng video) · 4. Quota · 5. Giới hạn cần biết trước khi đăng · 6. Giọng đọc

## 1. Phần mềm

```bash
# ffmpeg: macOS `brew install ffmpeg`, Ubuntu `sudo apt install ffmpeg`, Windows `winget install ffmpeg`
pip install pillow edge-tts
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2   # chỉ cần cho bước đăng
```

Tìm kênh (`yt_research.py`) chỉ dùng thư viện chuẩn của Python.

## 2. API key để tìm và phân tích kênh

1. Vào https://console.cloud.google.com, tạo một project mới.
2. **APIs & Services → Library**, tìm "YouTube Data API v3", bấm **Enable**.
3. **APIs & Services → Credentials → Create credentials → API key**.
4. Nên bấm vào key vừa tạo và giới hạn nó chỉ dùng cho YouTube Data API v3.
5. Đặt vào biến môi trường:

```bash
export YOUTUBE_API_KEY="AIza..."          # macOS, Linux
setx YOUTUBE_API_KEY "AIza..."            # Windows, mở lại terminal sau đó
```

API key chỉ đọc dữ liệu công khai. Nó không đụng được tới kênh của bạn.

## 3. OAuth client để đăng video

Đăng video là hành động thay mặt chủ kênh nên cần đăng nhập Google, không dùng API key được.

1. Trong cùng project: **APIs & Services → OAuth consent screen**. Chọn **External**, điền tên ứng dụng và email.
2. Ở phần **Test users**, thêm chính tài khoản Google sở hữu kênh.
3. **Credentials → Create credentials → OAuth client ID**, loại **Desktop app**.
4. Tải file JSON về, đổi tên thành `client_secret.json`, đặt trong thư mục dự án (hoặc chỉ đường dẫn bằng `--client-secrets`).
5. Lần đầu chạy `upload_youtube.py`, trình duyệt mở ra. Đăng nhập đúng tài khoản chủ kênh và bấm cho phép. Nếu thấy cảnh báo "Google hasn't verified this app", chọn **Advanced → Go to ...**, vì đây là ứng dụng của chính bạn.

Token được lưu tại `~/.config/youtube-trend-studio/token.json`. Đừng đưa `client_secret.json` và token lên git hay gửi cho người khác.

Khi consent screen còn ở trạng thái **Testing**, Google cho token hết hạn sau 7 ngày, nên mỗi tuần sẽ phải đăng nhập lại một lần. Chuyển sang **In production** thì hết giới hạn này.

## 4. Quota

Mỗi project mặc định có 10.000 đơn vị mỗi ngày, đặt lại lúc nửa đêm giờ Thái Bình Dương.

| Việc | Chi phí |
|---|---|
| Tìm kiếm (`search.list`), mỗi trang | 100 |
| Đọc thông tin kênh, playlist, video | 1 mỗi lần gọi |
| Một lượt `find` với 4 từ khoá | khoảng 450 đến 550 |
| Một lượt `analyze` | khoảng 3 đến 5 |
| Đăng một video (`videos.insert`) | từng là 1.600, Google có điều chỉnh. Xem bảng hiện hành |

Bảng chi phí hiện hành: https://developers.google.com/youtube/v3/determine_quota_cost

## 5. Giới hạn cần biết trước khi đăng

**Project chưa audit thì video đăng qua API bị khoá ở chế độ riêng tư.** Theo tài liệu của `videos.insert`, mọi video đăng từ project API chưa được YouTube xác minh (tạo sau ngày 28/7/2020) sẽ bị giới hạn ở chế độ private, và bạn không tự mở công khai được cho tới khi project qua audit. Cách xử lý:

- **Thử trước**: đăng một video thử ở chế độ private, vào YouTube Studio xem có đổi sang công khai được không.
- **Nếu bị khoá**: nộp đơn audit tại https://support.google.com/youtube/contact/yt_api_form (miễn phí, chờ vài ngày đến vài tuần). Trong lúc chờ, dùng skill để làm video và soạn metadata, rồi tự tải file lên trong YouTube Studio. Mọi thứ đã có sẵn trong thư mục `build/`.

Chính sách này có thể thay đổi. Kiểm tra tại https://developers.google.com/youtube/v3/docs/videos/insert

**Các điểm khác:**

- Thumbnail tuỳ chỉnh và video dài hơn 15 phút cần kênh đã xác minh số điện thoại: https://www.youtube.com/verify
- Kênh mới có giới hạn số video đăng mỗi ngày.
- Chính sách kiếm tiền loại nội dung sản xuất hàng loạt, lặp lại hoặc tái sử dụng. Xem https://support.google.com/youtube/answer/1311392
- Khai báo nội dung tổng hợp hoặc đã chỉnh sửa: https://support.google.com/youtube/answer/14328491

## 6. Giọng đọc

| Lựa chọn | Dùng khi | Cách dùng |
|---|---|---|
| `edge` (mặc định) | Bản nháp, thử định dạng | `pip install edge-tts`. Xem giọng bằng `edge-tts --list-voices`. Tiếng Việt: `vi-VN-HoaiMyNeural` (nữ), `vi-VN-NamMinhNeural` (nam) |
| `cmd` | Kênh kiếm tiền, cần giọng có giấy phép thương mại | Viết một lệnh hoặc script nhỏ gọi dịch vụ TTS bạn trả tiền, nhận `{text_file}` và ghi ra `{out}` |
| `files` | Tự thu âm hoặc thuê người đọc | Đặt file vào một thư mục, tên theo `id` của cảnh hoặc `001.mp3`, `002.mp3`... |
| `silent` | Thử nhịp và bố cục | Không cần gì thêm |

`edge` dùng cổng dịch vụ không chính thức của Microsoft Edge, có thể ngừng hoạt động bất cứ lúc nào và không có điều khoản cho phép dùng thương mại rõ ràng. Tự thu âm vẫn là cách tốt nhất để video có nét riêng.
