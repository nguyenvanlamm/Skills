---
name: youtube-trend-studio
description: Tìm kênh YouTube mới đang tăng trưởng nhanh mà Claude có thể làm theo (faceless, dựa trên kịch bản và lồng tiếng), giải mã công thức của kênh, rồi sản xuất video gốc cùng định dạng và đăng lên YouTube. Dùng skill này mỗi khi người dùng muốn tìm kênh hoặc ngách YouTube đang hot, nghiên cứu kênh đối thủ, "làm video giống kênh X", xây kênh faceless, viết kịch bản và dựng video YouTube bằng Claude, hoặc upload video lên YouTube, kể cả khi họ chỉ cần một phần của quy trình (chỉ tìm kênh, chỉ phân tích, chỉ dựng video, chỉ đăng). Also use for English requests such as finding trending new YouTube channels, faceless channel ideas, modelling a channel's format, or making and uploading a YouTube video.
compatibility: Python 3.9+, ffmpeg, Pillow. Tìm kênh và đăng video cần mạng tới googleapis.com (Claude Code hoặc Cowork trên máy người dùng), một YouTube Data API key và một OAuth client. Trong sandbox bị giới hạn mạng chỉ chạy được phần kịch bản và dựng video.
---

# YouTube Trend Studio

Skill này đưa người dùng đi từ câu hỏi "ngách nào đang lên?" tới một video đã nằm trên kênh của họ, qua năm giai đoạn:

1. **Tìm** kênh mới đang tăng nhanh mà Claude làm theo được
2. **Giải mã** công thức của kênh được chọn thành một bản blueprint
3. **Viết** kịch bản gốc và storyboard theo blueprint
4. **Dựng** video, phụ đề, thumbnail
5. **Đăng** lên kênh YouTube của người dùng

Người dùng có thể bước vào ở bất kỳ giai đoạn nào. "Phân tích kênh @abc giúp tôi" bắt đầu từ giai đoạn 2; "đăng file này lên YouTube" chỉ là giai đoạn 5. Làm đúng phần được nhờ, không ép chạy cả quy trình.

## Ba nguyên tắc xuyên suốt

### 1. Học công thức, không sao chép nội dung

"Làm video tương tự" ở đây nghĩa là cùng ngách, cùng định dạng, cùng nhịp, với kịch bản, hình ảnh, giọng đọc, tiêu đề và thumbnail tự làm.

| Được mượn | Không mượn |
|---|---|
| Cấu trúc video, độ dài, nhịp chuyển cảnh | Câu chữ trong kịch bản, kể cả viết lại sát ý từng câu |
| Kiểu tiêu đề, kiểu hook, tần suất đăng | Footage, ảnh, nhạc, giọng đọc của kênh gốc |
| Chủ đề và góc nhìn chung của ngách | Thumbnail, tên kênh, logo, nhận diện |

Lý do không chỉ là phép lịch sự. Nội dung chép lại dính Content ID và gậy bản quyền (ba gậy là mất kênh). YouTube cũng không bật kiếm tiền cho nội dung hàng loạt, lặp lại hoặc tái sử dụng. Và về mặt cạnh tranh, một bản sao luôn thua bản gốc vì đến sau với cùng một lời hứa. Thứ đáng học là lý do khán giả bấm vào và xem hết, rồi áp nó cho một chủ đề kênh gốc chưa làm hoặc làm chưa tới.

Nếu người dùng muốn reup hoặc chép nguyên kịch bản, giải thích ngắn gọn các rủi ro trên và đề xuất làm theo công thức.

### 2. Số liệu thật, không ước đoán

Người dùng sẽ bỏ nhiều tuần công sức dựa trên danh sách kênh này. Mọi con số (sub, view, tuổi kênh) phải lấy từ kết quả API hoặc trang đã mở và ghi rõ ngày lấy. Thiếu công cụ để lấy số thì nói thẳng là thiếu, không điền bằng trí nhớ. Phân biệt rõ điều đã kiểm chứng ("API trả về") với điều suy ra từ tiêu đề và mô tả ("có vẻ là faceless, cần bạn xem xác nhận").

### 3. Ba điểm dừng

Càng về sau mỗi bước càng tốn (thời gian render, tiền TTS, uy tín kênh), nên dừng lại hỏi ở ba chỗ:

- **Dừng 1**, sau danh sách kênh: người dùng chọn kênh để làm theo.
- **Dừng 2**, sau blueprint và các đề xuất chủ đề: người dùng chọn chủ đề, độ dài, giọng đọc.
- **Dừng 3**, trước khi đăng: người dùng xem video và metadata.

Nếu người dùng nói trước "cứ chạy hết, không cần hỏi", có thể tự chọn ở Dừng 1 và 2 (chọn ứng viên tốt nhất, nêu lý do). Dừng 3 vẫn giữ cho mọi video công khai: Claude không nghe được âm thanh nên không thể tự phát hiện TTS đọc sai, và video đã công khai thì khó rút lại. Chỉ đăng thẳng khi người dùng đã đồng ý trước, và khi đó đăng ở chế độ riêng tư.

## Chuẩn bị

Kiểm tra môi trường trước khi hứa điều gì:

```bash
ffmpeg -version | head -1
python3 -c "import PIL; print('Pillow', PIL.__version__)"
curl -sS -m 8 -o /dev/null -w "%{http_code}\n" https://www.googleapis.com/youtube/v3/videos   # có mạng thì ra 4xx
[ -n "$YOUTUBE_API_KEY" ] && echo "có API key" || echo "chưa có API key"
```

- **Không ra được googleapis.com** (ví dụ sandbox của claude.ai): giai đoạn 1 và 5 không chạy được. Nói rõ ngay từ đầu, vẫn làm giai đoạn 2 đến 4 nếu người dùng cho biết kênh mẫu, rồi giao gói file để họ tự đăng. Khuyên chạy skill trong Claude Code hoặc Cowork để có đủ quy trình.
- **Chưa có API key hoặc OAuth client**: hướng dẫn theo `references/setup.md`. Mất khoảng 10 phút, làm một lần.

Thông tin cần có trước khi tìm kênh. Hỏi gộp trong một lượt, chỉ hỏi phần chưa biết:

- Ngách hoặc 3 đến 6 cụm từ khoá, viết theo cách khán giả gõ tìm
- Thị trường và ngôn ngữ (ví dụ VN + vi, US + en)
- Dạng video: dài nằm ngang hay Shorts dọc
- Kênh của người dùng nếu đã có, để tránh trùng chủ đề

Nếu người dùng chưa có ngách, đề xuất 5 đến 6 ngách hợp với sản xuất faceless (giải thích khoa học, lịch sử, tài chính cá nhân, tâm lý học, top list, công nghệ, thần thoại, học ngoại ngữ) và chạy tìm kiếm trên các ngách họ chọn.

Giữ mọi thứ của một dự án trong một thư mục:

```
du-an/
├── research/            channels.md, channel_<id>.md, blueprint_<kênh>.md, log.md
└── videos/<slug>/       script.md, sources.md, storyboard.json, assets/, build/
```

## Giai đoạn 1: Tìm kênh

```bash
python scripts/yt_research.py find \
  -k "giải thích khoa học" -k "vì sao" -k "sự thật thú vị" \
  --region VN --lang vi --max-channel-age 180 --published-within 30 --out research/
```

Script tìm các video nhiều view nhất trong 30 ngày qua cho từng từ khoá, lấy kênh đứng sau, giữ lại kênh mới tạo, rồi lấy mẫu các video gần đây của từng kênh. Mỗi từ khoá tốn 100 đơn vị quota (hạn mức mặc định 10.000 mỗi ngày), nên chọn từ khoá có chủ đích thay vì rải thật nhiều. `--duration short|medium|long` lọc theo độ dài nếu người dùng chỉ làm một dạng.

Cách đọc bảng kết quả:

- **Views/day** và **Median views**: sức kéo thật. Dùng trung vị vì một video viral đơn lẻ làm trung bình ảo.
- **Views/sub** (median view chia số sub): trên 1 nghĩa là video đi xa hơn tệp người đăng ký, tức thuật toán đang đẩy. Đây là tín hiệu "đang hot" đáng tin nhất.
- **Uploads/wk**: nhịp đăng phải theo kịp nếu muốn cạnh tranh trong ngách.
- **Score**: chỉ để sắp xếp sơ bộ. Quyết định cuối là đánh giá bên dưới.

Điểm số không biết kênh đó có làm lại được hay không, nên đọc `research/channels.json` (tiêu đề, mô tả, thumbnail của các video hàng đầu) và chấm từng ứng viên theo thang "Claude làm được không?" trong `references/blueprint.md`. Nếu có công cụ duyệt web, mở 2 đến 3 video hàng đầu của mỗi ứng viên để xác nhận định dạng. Nếu không, ghi rõ nhận định là suy ra từ metadata và nhờ người dùng xem lướt để xác nhận.

Loại các bẫy thường gặp:

- Kênh có một video viral còn lại rất thấp (max cao, median thấp)
- Kênh reup, compilation, nhạc, clip phim: tăng nhanh nhờ nội dung của người khác, không có công thức nào để học
- Kênh phụ thuộc vào gương mặt, cá tính hoặc footage tự quay
- Kênh tin nóng cần footage thời sự theo giờ
- Kênh thiếu nhi: video "made for kids" bị tắt bình luận và hạn chế quảng cáo

**Kết quả trình bày cho người dùng** là bảng 5 đến 8 kênh với các cột: kênh (kèm link), tuổi kênh, sub, median view, view/sub, định dạng, điểm làm được (trên 10), vì sao đáng chú ý, rủi ro. Kết bằng 1 đến 2 kênh đề xuất và lý do. Sau đó **Dừng 1**.

Không có API key: nếu có công cụ tìm kiếm web thì dùng nó để tìm ứng viên và nói rõ số liệu kém chính xác hơn. Nếu không có cả hai, nhờ người dùng đưa vài kênh họ đã thấy rồi làm tiếp từ giai đoạn 2.

## Giai đoạn 2: Giải mã công thức

```bash
python scripts/yt_research.py analyze "https://www.youtube.com/@kenh-mau" --recent 30 --out research/
```

Đọc file `.md` vừa tạo. Phần giá trị nhất là so sánh **outlier** (từ 2 lần median trở lên) với **video kém** (từ 0,5 lần trở xuống): các video thắng có chung điều gì về chủ đề, cách đặt tiêu đề, độ dài mà video thua không có?

Tìm hiểu thêm những gì số liệu không cho thấy:

- **Thumbnail**: URL nằm trong file JSON. Nếu tải được thì xem trực tiếp để ghi lại quy ước (số chữ, màu, bố cục).
- **Cấu trúc bên trong video**: nếu có công cụ lấy transcript, hoặc người dùng dán transcript của 1 đến 2 video outlier, hãy phân tích hook 15 giây đầu, cách chia đoạn, độ dài câu, tốc độ nói, vị trí kêu gọi hành động. Transcript chỉ dùng để hiểu cấu trúc, không tái sử dụng câu chữ.

Viết blueprint theo mẫu trong `references/blueprint.md`, lưu vào `research/blueprint_<kênh>.md`. Sau đó đề xuất 5 chủ đề cho video đầu tiên. Mỗi chủ đề gồm tiêu đề dự kiến, góc nhìn, nó khớp với mẫu outlier nào, và nó khác video kênh gốc đã làm ở đâu. Đọc `research/log.md` nếu có để không lặp chủ đề cũ.

**Dừng 2**: người dùng chọn chủ đề và xác nhận độ dài, giọng đọc, nguồn hình ảnh.

## Giai đoạn 3: Kịch bản và storyboard

Làm trong `videos/<slug>/`.

**Kiểm chứng trước khi viết.** Video sai kiến thức sẽ bị bình luận vạch ra và làm hỏng kênh mới. Ghi nguồn cho mọi số liệu và sự kiện vào `sources.md`. Không có công cụ tìm kiếm thì đánh dấu các chi tiết cần người dùng kiểm tra lại.

**Viết cho tai nghe**, lưu vào `script.md`:

- Mở đầu theo kiểu hook của blueprint: lời hứa và sự tò mò trong 5 đến 15 giây đầu, chưa chào hỏi
- Câu ngắn, văn nói, số làm tròn, không ngoặc đơn, không viết tắt mà TTS sẽ đọc sai
- Mỗi 30 đến 60 giây có một điểm kéo lại (câu hỏi mở, chi tiết bất ngờ, lời hứa cho phần sau)
- Ước lượng độ dài: khoảng 15 ký tự mỗi giây, tức 900 ký tự cho một phút
- Từng câu là của mình. Thấy mình đang nhớ lại câu của kênh gốc thì viết lại từ ý

**Chuyển thành storyboard.** Đọc `references/storyboard.md` để biết các trường và layout, rồi tạo `storyboard.json` (mẫu ở `assets/storyboard.example.json`). Mỗi cảnh một ý, dài 5 đến 15 giây hoặc theo nhịp chuyển cảnh trong blueprint. Chữ trên màn hình là ý chính tối đa khoảng 8 từ, không phải bản chép lời đọc.

**Hình ảnh và clip nền** chỉ lấy từ các nguồn dùng được:

- Tự tạo bằng code: biểu đồ, sơ đồ, bản đồ, minh hoạ (matplotlib, Pillow, SVG, ảnh chụp trang HTML tự viết)
- File người dùng cung cấp, hoặc kho stock mà họ có giấy phép
- Ảnh và clip public domain hoặc CC0, có ghi nguồn
- Công cụ tạo ảnh hoặc video AI nếu người dùng có

Ghi nguồn và giấy phép của từng file vào `assets/CREDITS.md`. Ảnh tìm trên mạng không rõ giấy phép và khung hình cắt từ video người khác thì không dùng.

## Giai đoạn 4: Dựng video

Kiểm tra bố cục trước, vì bước này chỉ mất vài giây:

```bash
python scripts/build_video.py videos/<slug>/storyboard.json --only-frames --out videos/<slug>/build
```

Mở vài file `build/work/scene_*.png` để xem chữ có tràn, có đè lên vùng quan trọng của ảnh, dấu tiếng Việt có hiển thị đúng không. Sửa storyboard rồi mới dựng thật:

```bash
python scripts/build_video.py videos/<slug>/storyboard.json --out videos/<slug>/build \
  --music assets/nhac-nen.mp3 --music-volume 0.08
```

Kết quả gồm `video.mp4`, `captions.srt`, `chapters.txt`, `build_report.json`.

**Giọng đọc** (`--tts`):

- `edge` (mặc định): giọng neural miễn phí, ví dụ `vi-VN-HoaiMyNeural`, `vi-VN-NamMinhNeural`, `en-US-AriaNeural`. Tốt cho bản nháp. Đây là cổng không chính thức, nên với kênh định kiếm tiền hãy khuyên người dùng chuyển sang TTS có giấy phép thương mại hoặc tự thu âm.
- `cmd`: bất kỳ TTS nào người dùng có, qua `--tts-cmd "lệnh {text_file} {out}"`
- `files`: file thu âm sẵn trong `--audio-dir`
- `silent`: không tiếng, để thử nhịp

Lời đọc không đổi thì không bị tạo lại, nên sửa một cảnh rồi dựng lại rất nhanh.

**Nhạc nền** chỉ dùng file người dùng có quyền (YouTube Audio Library, nhạc đã mua giấy phép). Không có thì bỏ nhạc.

**Khi định dạng cần hơn slide và b-roll** (hoạt hình, biểu đồ chuyển động, quay màn hình): viết code riêng để tạo clip cho từng cảnh (Manim, Remotion, matplotlib animation, quay trang HTML bằng Playwright), rồi đưa clip vào trường `video` của cảnh. Storyboard vẫn giữ vai trò điều khiển lời đọc và thời lượng.

**Thumbnail**: tạo bằng Pillow, 1280×720, dưới 2 MB, lưu `build/thumbnail.png`. Một điểm nhấn hình ảnh, tối đa 4 từ chữ lớn, tương phản mạnh. Thu nhỏ còn 320 px ngang rồi xem lại, vì đó là kích thước khán giả thấy. Theo quy ước chung của ngách thì được, dựng lại bố cục riêng của kênh gốc thì không.

**Tự kiểm tra trước khi đưa cho người dùng:**

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 build/video.mp4
for t in 3 30 90 150; do ffmpeg -y -loglevel error -ss $t -i build/video.mp4 -frames:v 1 build/check_$t.png; done
```

So thời lượng với mục tiêu trong blueprint, xem các khung hình đã trích, đọc lướt `captions.srt`. Ghi lại những chỗ TTS dễ đọc sai (tên riêng, số, từ nước ngoài) để người dùng nghe kỹ các đoạn đó.

## Giai đoạn 5: Đăng lên YouTube

**Soạn metadata** vào `build/description.txt` và `build/metadata.json`:

- **Tiêu đề**: theo kiểu trong blueprint, tối đa 100 ký tự, phần quan trọng nằm trong 60 ký tự đầu. Lời hứa trong tiêu đề phải được video thực hiện.
- **Mô tả**: hai dòng đầu tóm tắt giá trị video. Tiếp theo là chương mục từ `chapters.txt` (YouTube yêu cầu chương đầu ở 00:00, ít nhất 3 chương, mỗi chương từ 10 giây), nguồn tham khảo, ghi công hình ảnh và nhạc.
- **Tags**: 5 đến 10 cụm sát chủ đề. **Category** và **ngôn ngữ** cho đúng.
- **Made for kids**: chỉ bật khi nội dung nhắm tới trẻ em. Không chắc thì hỏi người dùng.
- **Nội dung tổng hợp** (`--synthetic-media`): YouTube yêu cầu khai báo khi nội dung trông như thật có thể bị nhầm là người, sự kiện hoặc địa điểm thật, ví dụ giọng nhái người thật hay cảnh AI tả thực. Slide, hoạt hình và giọng TTS thông thường không thuộc diện bắt buộc. Phân vân thì khai báo: theo YouTube, nhãn này không hạn chế phân phối hay kiếm tiền, còn bỏ sót khai báo nhiều lần thì có thể bị xử lý.

**Dừng 3.** Đưa cho người dùng: file video, thumbnail, tiêu đề, mô tả, danh sách đoạn cần nghe kỹ, và chế độ đăng dự kiến. Nhờ họ xem hết video. Chờ họ đồng ý.

**Đăng.** Chạy khô trước để bắt lỗi, rồi đăng thật:

```bash
python scripts/upload_youtube.py --file build/video.mp4 --title "..." \
  --description-file build/description.txt --tags "a,b,c" --category 27 --language vi \
  --thumbnail build/thumbnail.png --captions build/captions.srt --dry-run
```

- Mặc định là `private`. Người dùng xem lại trong YouTube Studio rồi tự bấm công khai, hoặc hẹn giờ bằng `--publish-at 2026-12-01T19:00:00+07:00`.
- `--privacy public --confirm-public` chỉ dùng khi người dùng đã xem video và nói rõ là đăng công khai ngay.
- Lần đầu chạy sẽ mở trình duyệt để người dùng đăng nhập và cấp quyền. Token lưu ở `~/.config/youtube-trend-studio/`.

Sau khi đăng, báo lại link video, link Studio, trạng thái thực tế và các cảnh báo script in ra. Nếu YouTube tự đặt video về riêng tư dù đã yêu cầu khác, đó là giới hạn của project API chưa qua audit (xem `references/setup.md`). Khi đó người dùng tải file lên thủ công trong Studio, mọi thứ đã soạn sẵn.

Không đăng được từ môi trường hiện tại thì giao gói gồm `video.mp4`, `thumbnail.png`, `captions.srt`, `description.txt` kèm tiêu đề và tags để người dùng tự tải lên.

**Ghi nhật ký.** Thêm một dòng vào `research/log.md`: ngày, kênh mẫu, chủ đề, tiêu đề, video ID. Lần chạy sau đọc file này để không lặp chủ đề, và sau vài tuần người dùng có dữ liệu để so video nào hiệu quả.

## Làm nhiều video

Một video không nói lên điều gì; công thức chỉ lộ ra hiệu quả sau khoảng 5 đến 10 video. Khi người dùng muốn làm hàng loạt, giữ blueprint cố định và đổi chủ đề, nhưng mỗi video vẫn cần nghiên cứu và góc nhìn riêng. Sản xuất hàng loạt từ một khuôn với nội dung gần như giống nhau là đúng thứ chính sách kiếm tiền của YouTube loại ra. Sau mỗi 5 video, đề nghị chạy lại `analyze` trên chính kênh của người dùng để xem khán giả của họ thưởng cho điều gì, rồi cập nhật blueprint theo dữ liệu đó thay vì tiếp tục bám theo kênh mẫu.
