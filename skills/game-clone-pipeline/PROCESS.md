# Quy trình clone game (bản 1.17.1)

Biến một game casual/puzzle đang thành công, hoặc một ý tưởng game (đặt cạnh các game thành công gần nhất), thành một game Flutter **khác rõ**, chỉ có tiếng Anh, rồi đưa lên App Store, kèm landing page. Skill `game-clone-pipeline` chạy quy trình này; file này là bản tóm tắt cho người đọc.

## Nguyên tắc

1. **Chỉ lấy sự kiện và cơ chế.** APK, data game, video và mô tả cho ra luật chơi và thông số. Không chép asset, ảnh, âm thanh, font, câu chữ, file level hay code của game gốc. `.clone/reference/`, `.clone/apk/` và `.clone/data/` không đưa vào git; riêng `.clone/status.md` được commit để phiên sau chạy tiếp.
2. **Tạo khác biệt trước khi vẽ.** Chủ đề, bảng màu, tên gọi và một cơ chế riêng được chốt ở bước S2. Core làm bằng hình tạm; giao diện thật áp vào ở S4.
3. **Thiết kế kinh tế game cùng vòng chơi.** Phải có điều kiện thua thì booster và IAP mới có giá trị.
4. **Game chỉ làm tiếng Anh**: chữ trong game, store listing (en-US), gói IAP, landing page, privacy, support. Tài liệu nội bộ được viết tiếng Việt.
5. **Chỉ dùng main + tag `vX.Y.Z`.** Không mở nhánh `ios` sống lâu. Nhánh tạm chỉ do skill con tạo (nhánh test ở S3, mỗi issue một nhánh ở S6) và phải được merge vào `main` rồi xóa ngay cuối bước tạo ra nó. Chỉ push `main`, tag và nhánh của PR. Nhánh PR (S6) đã merge mà auto mode không cho xoá trên GitHub thì agent ghi lệnh xoá vào `## Deferred (human)` để bạn chạy. Phiên chạy nền thì làm trong worktree của bước, và skill con commit thẳng lên nhánh của worktree đó. Trước S8 chỉ còn `main` (trừ các nhánh đang chờ bạn xoá) và không còn PR nào mở.
6. **Cổng chỉ qua khi có bằng chứng**: lệnh thật chạy xong và exit 0, hoặc câu trả lời của người được ghi vào `.clone/status.md`.
7. **Chỉ phát hành App Store.** Không có bước Google Play.
8. **Commit ngay sau mỗi bước** bằng skill `commit`: message tiếng Anh, kèm push. Tag và release để `/ship` làm.
9. **Đặt tên repo theo tên game.** Repo game (thư mục và GitHub) mang đúng tên game viết thường, nối bằng gạch ngang (Moss Lantern → `moss-lantern`); repo landing là `<tên-game>-site`. Không bao giờ có đuôi `-clone`. Trước G1 dùng tên tạm theo ý tưởng (cũng không có `-clone`); duyệt tên ở G1 xong thì đổi tên repo và thư mục.
10. **Telegram chỉ là cổng thêm.** Ngồi ở máy thì vẫn quyết trong chat; chỉ khi bạn bật chế độ vắng mặt (`/away`) agent mới hỏi qua Telegram. Từ điện thoại bạn cũng mở được phiên Claude (`/open`, `/new`). Không gửi mật khẩu hay tài khoản Apple qua Telegram.
11. **Agent ở yên trong repo game.** Muốn xem repo khác (ví dụ `DESIGN.md` của game trước), agent đọc bằng đường dẫn đầy đủ chứ không `cd` sang đó. Repo landing (S7, S9) cũng vậy: agent tạo cho nó một worktree riêng bằng `git -C` rồi sửa trong đó. Phiên chạy nền làm mỗi bước trong một worktree riêng và chỉ ra khi xong bước, merge vào `main`. Cổng nằm giữa bước (ví dụ G4) thì chờ ngay trong worktree đó, không sang bước sau trước. Không bao giờ quay lại một worktree đã rời: từ repo khác, việc đó bật một hộp xin quyền chỉ bấm được ở máy, và phiên đứng chờ ở đó.
12. **Code mua hàng lấy từ mẫu, không chép game trước.** S5 bắt đầu từ `templates/store/`. Mẫu này có sẵn test cho các điểm sau:
    - chỉ báo App Store "giao dịch xong" sau khi đã lưu;
    - chỉ nhận giao dịch StoreKit 2 đã xác minh;
    - shop không bao giờ kẹt (Ask to Buy, lỗi kết nối);
    - máy không lưu được thì game vẫn chạy và tạm ngừng bán gói;
    - gói đã mua không bị cắt bởi mức trần.

    Chép code của game trước từng làm cùng một lỗi lan ra 11 game.
13. **`Waiting on:` chỉ ghi khi agent thật sự dừng chờ bạn.** Việc hoãn cho bạn (các bước Apple) nằm ở mục `## Deferred (human)` trong status.md, còn agent vẫn làm tiếp phần khác. Khi `Waiting on:` có chữ, bot không báo lúc phiên chết giữa chừng. Khi chỉ còn chờ bước Apple, status.md ghi đúng một dạng: `Now: S8 · 6 waiting for the Apple steps` và `Waiting on: S8-apple: build VALID + Apple ID`.
14. **Phiên chạy nền gọi Bash từng lệnh đơn.** Cơ chế cô lập worktree từ chối những lệnh nó không kiểm được (lệnh ghép, `cd`, biến, heredoc); những lần bị từ chối này chiếm 54% số lỗi của các lần chạy trước. Agent sửa file bằng công cụ Edit/Write. Repo mới phải có commit đầu tiên trước khi vào worktree. Worktree mới phải chạy `flutter pub get` trước lần commit đầu, nếu không hook có `--no-pub` sẽ crash.

## Các bước

| Bước | Ai | Làm gì | Skill / công cụ | Cổng |
|---|---|---|---|---|
| S0 | Agent → Người | Chọn game (hoặc ý tưởng) và game tham chiếu: đang lên, hợp Flutter 2D, còn chỗ cho twist, chưa quá bão hoà | `idea-validator` | **G0** duyệt game + tham chiếu |
| S1 | Agent + Người | Dùng những gì bạn có (APK, data game, video vài phút, mô tả); agent lấy thêm trang store rồi viết `SPEC.md` | `reverse-engineer-anything`, `scripts/contact-sheet.sh` | **G0b** duyệt SPEC |
| S2 | Agent → Người | `DESIGN.md`: bảng khác biệt, kinh tế game, mục tiêu độ khó, tên game | `brand-name-checker`, `appstore-spam-guard` (`design`) | **G1** duyệt thiết kế |
| S3 | Agent | Tạo project ngay trong repo game đã có (use in place, không `git init` lại, gộp `.gitignore`); core Flutter với hình tạm: luật bằng Dart thuần, test, bot, `tool/simulate.dart`; cài hook kiểm tra trước mỗi commit (`tool/check.sh` từ `templates/tool/`) | `flutter-init`, `test-coverage` | analyze + test exit 0 |
| S4 | Agent → Người | 3 hướng UI → chọn 1 → áp vào Flutter → làm icon (nhân vật/cơ chế của chính game, không emoji, không sprite có sẵn) | `huashu-design` (hoặc `lam-design`), dựng mockup bằng Flutter theo `references/mockup-to-flutter.md`, `logo-designer`, `appstore-spam-guard` (`build`) | **G2** chọn hướng |
| S5 | Agent + Người | IAP + Restore từ `templates/store/`, booster chống farm, analytics (nếu chọn), người thật chơi thử, chỉnh lại độ khó. Chưa chơi thử thì ghi vào mục hoãn, không chặn G3 | | **G3** duyệt gói và giá |
| S6 | Agent | Soát codebase → issue → sửa, merge từng PR rồi xóa nhánh | `codebase-modernizer`, `plan-to-issues`, `issue-work-loop` | test xanh, chỉ còn `main` |
| S7 | Agent | Repo landing tối thiểu có privacy + support, GitHub Pages deploy thẳng từ nhánh `main` (không dùng Actions) | `landing-page-generator` | 2 URL sống |
| S8 | Agent + Người | iOS: chuẩn bị trên Ubuntu, **build và upload trên Mac**, TestFlight, ảnh store, ASO, soát, ship, nộp, ghi sổ nộp | `flutter-ios-release`, `appstore-assets`, `aso-marketing`, `appstore-review-checker`, `appstore-spam-guard` (`submit`), `/ship` (không `asc`, luật 12) | **G4** duyệt nộp |
| S9 | Agent | Hoàn thiện landing (chạy thật cả hai skill trên site của game này) và khai báo site trong `robots.txt` và `llms.txt` của repo Pages gốc, rồi tick S9; badge App Store chờ app lên store, ghi ở mục hoãn. Sau khi ra mắt, bạn đọc review và số liệu trên App Store Connect rồi chuyển lại | `search-optimizer`, `design-optimizer` | |

## Ô các bước

Khi chạy trong herdr, agent tách pane của mình và mở một ô bên phải tên `clone-steps`. Ô này liệt kê S0–S9 và tự vẽ lại mỗi khi `.clone/status.md` thay đổi:

- `✓` là bước đã xong, `▶` là bước đang làm, `·` là bước chưa tới;
- cột cổng có `✓` khi cổng đã duyệt, và hiện `⏸` khi agent đang chờ bạn;
- dòng cuối ghi "Đang làm" (dòng `Now:` trong status.md) và "Chờ bạn" (dòng `Waiting on:`);
- ô đọc bản status.md mới nhất, kể cả bản trong worktree của bước đang chạy (dòng "Cập nhật" ghi tên worktree), nên thấy được tiến độ thật trước khi bước được merge vào `main`. Bước đang làm lấy từ `Now: S<n> · …`; dòng `Now:` viết kiểu khác thì ô coi bước chưa tick đầu tiên là bước đang làm.

Nếu lỡ đóng ô, mở lại bằng `python3 ~/.claude/skills/game-clone-pipeline/scripts/steps_pane.py open .` trong repo game. Khi không có herdr, agent in khối này vào chat mỗi lần đổi bước.

## Điều khiển qua Telegram khi ở xa

Không bắt buộc. Ngồi ở máy thì mọi thứ như cũ, bạn quyết trong chat. Khi ra ngoài, bạn quyết, ra lệnh và mở phiên Claude bằng điện thoại.

**Cài một lần:**
1. Trên Telegram, nhắn @BotFather lệnh `/newbot` để tạo **một bot riêng cho pipeline**. Đừng dùng lại bot mà chương trình khác (ví dụ Hermes) đang đọc: mỗi bot chỉ có một chương trình nhận tin được.
2. Trong terminal của bạn (không gõ token vào chat với agent), chạy `python3 ~/.claude/skills/game-clone-pipeline/scripts/telegram_bridge.py setup`, dán token khi được hỏi (token không hiện ra màn hình), rồi bấm Start trong bot trên điện thoại.
3. Chạy tiếp `python3 ~/.claude/skills/game-clone-pipeline/scripts/telegram_bridge.py install-service`. Bot chạy thành dịch vụ nền (systemd), nên điện thoại vẫn điều khiển được kể cả khi không mở Claude nào. Gỡ bằng `uninstall-service`.
4. Token, chat id và thư mục chứa game (`GAMES_DIR`, mặc định `~/Documents/projects`) được lưu ở `~/.config/game-clone-pipeline/telegram.env` (chỉ bạn đọc được), không bao giờ nằm trong repo. Bot chỉ nghe đúng chat của bạn.

**Quyết định và ra lệnh:**

| Bạn làm | Kết quả |
|---|---|
| Gõ `/away` trên điện thoại, hoặc nói "tôi ra ngoài" trong chat | Bật chế độ vắng mặt: câu hỏi đang chờ (nếu có) được gửi ngay lên Telegram kèm nút Duyệt / Làm lại / Từ chối; mỗi lần đổi bước bạn nhận tin; máy được giữ thức (màn hình vẫn tắt và khoá bình thường) |
| Bấm nút hoặc nhắn câu trả lời | Agent nhận quyết định và chạy tiếp; nhật ký cổng ghi `via Telegram`. Nếu lúc đó không còn phiên Claude nào chạy cho game ấy, bot tự mở phiên mới để làm tiếp |
| Gõ `/back`, hoặc trả lời một câu ngay trên máy | Telegram im lặng trở lại, máy được phép ngủ như thường; tin đang chờ trên Telegram được đánh dấu "đã quyết trên máy tính" |
| `/status [game]` | Xem game đang ở bước nào (giống ô các bước) |
| `/pause`, `/resume` | Dừng sau bước hiện tại, chạy tiếp |
| `/skip <bước>`, `/redo <S…>`, `/note <chữ>` hay nhắn chữ tự do | Ghi vào hộp thư của game đang chọn; agent đọc ở ranh giới bước tới. Với chữ tự do, bot trả lời ngay game đang làm gì, chờ gì và phiên Claude ghi lần cuối bao lâu trước. Quyết định chỉ người được làm (cổng, giá, nộp app) vẫn phải qua cổng |
| Nhắn `help` (không cần dấu `/`) | Bot gửi danh sách lệnh |
| Gửi video, APK, file data | Lưu thẳng vào `.clone/reference/`, `.clone/apk/` hoặc `.clone/data/` của game đang chọn (không đưa vào git). Tối đa 20 MB một file; lớn hơn thì gửi link hoặc cắt ngắn |

**Mở Claude từ điện thoại:**

| Lệnh | Kết quả |
|---|---|
| `/games` | Danh sách game: đang ở bước nào, có phiên Claude đang chạy không, đang hỏi gì |
| `/hide <game>`, `/unhide <game>` | Ẩn game khỏi `/games` (ví dụ game chỉ còn chờ bạn làm App Store) hoặc hiện lại. Game ẩn vẫn hỏi, vẫn nhận trả lời và vẫn dùng được `/use`, `/status`, `/log`; `/open` tự hiện lại |
| `/use <game>` | Chọn game để nói chuyện (gõ một phần tên là đủ) |
| `/open [game]` | Mở một phiên Claude chạy nền trong repo game đó và chạy tiếp từ `.clone/status.md`. Nếu game đã có phiên đang chạy thì bot báo, không mở thêm |
| `/new <ý tưởng hoặc link store>` | Mở phiên Claude bắt đầu game mới trong `GAMES_DIR`; agent tạo repo rồi hỏi tiếp bạn qua Telegram |
| `/log [game]` | Xem phiên Claude vừa nói gì và vừa chạy lệnh gì (12 mục gần nhất) |
| `/stop [game]` | Dừng phiên chạy nền do điện thoại mở (phiên đang mở trên máy tính thì không dừng từ xa được) |
| Về máy: `claude attach <mã phiên>` (mã bot gửi kèm tin) | Mở phiên đó trong terminal và làm tiếp như bình thường. Phiên mở bằng `/new` mang tên ý tưởng chứ không phải tên game, nên gõ tên game sẽ không thấy; dùng mã phiên. Chạy trong terminal thường, không qua profile mcc (`maisie`): mỗi thư mục cấu hình Claude chỉ thấy phiên của nó |

Phiên mở từ điện thoại chạy với chế độ quyền `auto`: Claude Code tự cho phép thao tác an toàn và chặn thao tác rủi ro. Nếu phiên vẫn phải dừng chờ cấp quyền, bot nhắn bạn kèm tên game và lệnh `claude attach <mã phiên>`; từ điện thoại không bấm cho phép được, về máy chạy đúng lệnh đó để xử lý. `/games` cũng hiện game đó là "🟡 Claude chờ xác nhận trên máy" kèm lệnh. Phiên mở từ điện thoại còn có một hook chặn trước thao tác hay gây hộp xin quyền này (vào lại worktree bằng `path:`), báo agent làm cách khác thay vì đứng chờ.

Khi đang ở chế độ vắng mặt, nếu một phiên Claude đang chạy mà 30 phút không ghi gì và không có câu hỏi nào chờ bạn, bot nhắn **một lần** kèm lệnh cuối cùng phiên đó chạy. Thường là phiên đang chờ một xác nhận chỉ bấm được trên máy. Xem bằng `/log`; mở lại bằng `/stop` rồi `/open`, hoặc về máy `claude attach`.

Bot cũng nhắn **một lần** khi phiên của game đã dừng hẳn (từ 10 phút đến 24 giờ trước) mà game chưa xong, không có câu hỏi nào chờ bạn, và `Waiting on:` trống hoặc câu trả lời của bạn chưa được phiên nào đọc. Tin nhắn kèm câu cuối của phiên, ví dụ "Login expired" khi Claude hết hạn đăng nhập. Chạy tiếp bằng `/open <game>`. Agent chỉ được dừng ở chỗ cần bạn quyết (luật 16), nên tin này nghĩa là phiên dừng ngoài ý muốn.

Bot nhận ra cả những phiên đang làm trong worktree của game (`.claude/worktrees/…`). Repo do pipeline tạo từ điện thoại chưa được Claude trust, nên `/open` sẽ mở phiên từ thư mục cha (`GAMES_DIR`) và báo cho bạn. Muốn sửa hẳn, ở máy chạy `claude` một lần trong repo đó và chấp nhận.

Mọi tin trên Telegram có dạng thẻ gọn để đọc trên điện thoại. Dòng đầu in đậm, gồm biểu tượng, tên game và tên bước (ví dụ "❓ Moss Lantern · Duyệt gói App Store (G4)"). Sau đó mỗi ý một dòng ngắn. Dòng 👉 ở cuối nói bạn cần bấm hay gõ gì. Lệnh hiện bằng chữ đơn cách, chạm vào là copy.

Ảnh và file đi kèm được gửi mỗi file một tin, theo đúng thứ tự, có chú thích riêng. Ở bước chọn giao diện (G2), agent gửi đủ 3 ảnh A, B, C, mỗi ảnh ghi tên hướng của nó, rồi mới hỏi bạn chọn.

**Lưu ý:**
- Máy đang ngủ hay ngủ đông thì không chạy gì cả, Telegram cũng không đánh thức được máy. Lúc bật `/away`, máy được chặn ngủ tự động. Nếu máy vẫn ngủ (bạn tự cho ngủ, mất điện), bot cố nhắn trước "máy sắp ngủ". Khi máy thức dậy, bot báo và chạy các lệnh đã gửi trong vòng 24 giờ.
- Phiên Claude chạy nền mà đứng chờ quá khoảng 1 giờ thì Claude Code tự dừng nó (cuộc trò chuyện vẫn được giữ). Không sao: khi bạn trả lời, bot mở phiên mới và phiên này đọc câu trả lời từ `.clone/telegram/`.
- Không gửi mật khẩu, token hay tài khoản Apple qua Telegram.

## Bước S1: dùng những gì bạn có

Chỉ cần một nguồn là bắt đầu được. Có thêm nguồn nào thì bớt được ❓ chừng đó. Agent không bắt bạn kiếm thứ bạn không có.

| Bạn có | Bỏ vào | Agent làm gì | Cho ra |
|---|---|---|---|
| File APK / XAPK / AAB | `.clone/apk/` | Đọc bằng REA: manifest, quyền, SDK, engine, product ID, config đọc được. Logic trong IL2CPP hay remote config thì ghi "không lấy được từ APK" | engine, SDK, gói IAP, thông số gốc |
| Data game: file config JSON/CSV, file level, bản dump remote config hay save, asset bundle | `.clone/data/` | Đọc bằng Python/jq, file nhị phân thì dùng REA. Chỉ lấy con số và phân bố, không lấy nguyên bố cục level | kích thước bàn, bảng spawn, giá, thời gian, đường độ khó |
| Video chơi game, vài phút là đủ | `.clone/reference/` | Chạy `contact-sheet.sh` (1 khung/giây, có mốc giờ) rồi đọc ảnh | luật chơi, nhịp, hiệu ứng, điều kiện thua |
| Tên hoặc link game | — | Tự lấy trang store, ảnh store, video công khai | thông tin store, cách kiếm tiền, giao diện cần tránh |
| Mô tả game hoặc ý tưởng bằng chữ | gõ vào chat | Chép từng luật vào SPEC, ghi nguồn "description"; chỗ còn bỏ ngỏ đánh ❓ | luật theo ý bạn |

Sau đó:

1. **Agent viết SPEC.** Mỗi luật ghi nguồn (mốc giây, file + key, ảnh store, hay "description"). Chỗ nào đoán thì đánh ❓. Cuối SPEC là danh sách việc nhỏ nhất cần thêm, ví dụ "1 clip 1 phút lấp đầy bàn", "ảnh màn hình cửa hàng".
2. **Bạn duyệt (G0b).** Trả lời ❓, gửi thêm, hoặc chấp nhận để trống; tối đa 2 vòng. ❓ còn lại ghi thành giả định trong `DESIGN.md`.

Khi các nguồn mâu thuẫn: video thắng data game và APK; data game thắng con số ước từ video; mô tả thua mọi nguồn khác.

Nếu chỉ có ý tưởng mà không có game gốc: ở S0 agent tìm 1–3 game thành công gần nhất làm tham chiếu và bạn chốt ở G0. SPEC và cổng khác biệt sẽ so với các game đó.

## Bước S8: build iOS

Không dùng GitHub Actions (luật 11). Agent chuẩn bị file trên Ubuntu, bạn build trên Mac:

1. Agent:
   - chạy `flutter-ios-release`;
   - chép `scripts/build-ios.sh` và `ios/ExportOptions.plist` vào repo;
   - viết `docs/IOS-BUILD-ON-MAC.md` và `docs/APP-STORE-CONNECT.md` (bundle id, gói IAP, giá, URL, ghi chú review, checklist);
   - commit.
2. Bạn làm trên web App Store Connect theo `docs/APP-STORE-CONNECT.md`: bundle id, app, gói IAP. Trên Mac: `TEAM_ID=… scripts/build-ios.sh upload`. Khi build VALID trên TestFlight, bạn gõ số build và Apple ID của app (mục App Information, một dãy số).
3. Bạn thử trên TestFlight bằng tài khoản Sandbox: mua, huỷ, cài lại, Restore. Đến lúc này code mua hàng mới chỉ được test với bản giả lập, nên cần xem kỹ gói đã mua: nó phải vào đúng một lần và vẫn còn sau khi tắt rồi mở lại app.
   - Lần nào mở app gói cũng vào lại: giao dịch chưa bao giờ được báo "xong".
   - Gói không vào: bước xác minh StoreKit 2 đã từ chối.
4. Agent:
   - làm ảnh store bằng `appstore-assets`, viết tên và từ khoá bằng `aso-marketing` (chỉ en-US), lưu vào `store/`;
   - soát bằng `appstore-review-checker` → **G4**. Câu hỏi G4 gộp luôn phần duyệt kế hoạch của `aso-marketing`, và hỏi một lần xem S9 có được quét site bằng isitagentready.com (dịch vụ bên ngoài) không. Bạn dán nội dung `store/` lên web. Agent chờ G4 ngay trong worktree của S8; duyệt xong mới merge và sang S9.
5. Agent chạy `/ship --no-auto` (version, tag). Bạn build bản chính thức trên Mac và bấm nộp trên web.

**Hoãn việc cần tài khoản Apple (luật 13):** bước 2–3 (làm trên web App Store Connect, build/upload trên Mac, thử TestFlight) mặc định để sau, ghi vào `## Deferred (human)` trong status.md. Agent không dừng chờ mà làm tiếp bước 4 (ảnh store, ASO) và soát; chỉ bước 5 (ship, nộp) chờ bạn làm xong phần hoãn. Câu hỏi về phần hoãn chỉ có một nút "Để sau". Muốn báo xong thì bạn gõ số build và Apple ID của app; bấm nút hay gõ "xong" không được tính. Từng có game bị gắn tag và ghi "đã nộp" chỉ nhờ vài cú bấm nút, trong khi chưa có bản build nào. Bot tự kiểm tra việc này: tin bạn gõ mà thiếu số build hoặc Apple ID thì không được tính là câu trả lời, câu hỏi vẫn mở, tin đó chỉ chuyển cho agent như một ghi chú. Trước khi ghi nhận, agent xem trên GitHub repo game có được clone lần nào trong 14 ngày qua không (build trên Mac phải clone repo về trước). Nếu chưa có lượt nào, agent hỏi lại bạn một lần.

**Hoãn `asc` (luật 12):** agent không chạy lệnh `asc` nào; mọi việc trên App Store Connect bạn làm trên web từ file agent chuẩn bị.

Chi tiết lệnh ở `references/ios-release-runbook.md`.

## Đối chiếu với flow cũ

| Flow cũ | Quy trình mới |
|---|---|
| Tải APK | S1: một trong các nguồn (APK, data game, video, mô tả) |
| Dùng REA | S1: `reverse-engineer-anything` cho APK và data nhị phân |
| Lấy thông tin, thông số | `SPEC.md` mục 2 (APK và data game) và mục 4 (luật chơi) |
| Flutter clone game tương tự | S3 |
| Đổi một ít cho hay hơn, đỡ giống | S2, có cổng khác biệt chặt hơn (`references/differentiation-gate.md`) |
| `huashu-design` ra 3 bản UI/UX | S4 |
| Chọn 1 bản, hoàn thiện UI/UX | S4: dựng đúng mockup đã chọn bằng Flutter (`references/mockup-to-flutter.md`) + `logo-designer` |
| Thêm IAP giá hợp lý vào cốt game | Thiết kế ở S2, làm ở S5, duyệt giá ở G3 |
| Check sang nhánh mới `ios` | **Thay** bằng main + tag |
| Chuẩn bị iOS để upload | S8: `flutter-ios-release` + bộ build trên Mac |
| `/codebase-optimiser` | S6: `codebase-modernizer` (tên đúng) |
| `/plan-to-` | S6: `plan-to-issues` |
| `/ship` | S8: `/ship --no-auto` |
| asccli | **Hoãn** (luật 12): không chạy `asc`; agent chuẩn bị file, bạn làm trên web App Store Connect |
| `/appstore-assets` | S8 |
| Tạo repo landing page mới | S7, làm **trước** khi nộp vì cần URL privacy/support |
| `/search-optimiser`, `/design-optimiser` | S9: `search-optimizer`, `design-optimizer` (tên đúng) |
| Push lên GitHub Actions | **Bỏ.** Không dùng GitHub Actions ở đâu cả (luật 11): kiểm tra chạy trên máy (analyze, test, pre-commit); landing deploy Pages từ nhánh `main` |

Bước mới thêm vào: `idea-validator`, `brand-name-checker`, `aso-marketing`, `appstore-review-checker`, người thật chơi thử, `commit` sau mỗi bước.

## Checklist khác biệt (cổng G1, soát lại ở S4 và trước khi nộp)

Phải khác rõ ở tất cả các mục sau:
- tên game, icon;
- chủ đề (đồ vật trong game *là* gì);
- bảng màu và cách gán màu theo giá trị;
- cách trình bày khu vực chơi;
- bố cục HUD;
- chữ và icon của nút chính;
- chữ khen, âm thanh, hiệu ứng đặc trưng;
- phong cách ảnh store.

Phải khác cả các game trước của bạn: thao tác chính, chủ đề, bảng màu, icon. Bộ gói IAP không chép y nguyên của game trước; 8/12 game đầu bán cùng một bộ "mở khoá + gói nhỏ + gói lớn". Apple 4.3 tính cả các app na ná nhau của cùng một nhà phát triển.

Ngoài ra phải có **ít nhất một cơ chế riêng**. Lý do: Apple 4.1 (Copycats), 4.3 (Spam), và rủi ro trade dress. Bài học từ một game clone trước: tự vẽ toàn bộ bằng code nhưng vẫn giống gần hết bản gốc.

Hai dòng bắt buộc thêm từ vụ Fruit Mischief (bị reject 4.3(a) ngày 2026-10-23, tài khoản bị Extended Review): hình vật thể chính và icon phải tự vẽ, không lấy từ pack stock hay emoji; cơ chế riêng phải hiện ra trong 30 giây đầu của một bản cài mới. `appstore-spam-guard` đo những điều này ở S2, S4, S8 (luật 17), và so tên, icon, mô tả với khoảng 7.000 game trên bảng xếp hạng App Store (us, gb, jp, vn); có FAIL là chặn cổng. Sổ nộp của nó giữ cả tài khoản: team đang có vụ 4.3 chưa xong thì không nộp game khác lên team đó.

## Checklist trước khi nộp App Store (cổng G4)

- [ ] URL privacy và support đều sống, nội dung khớp với những gì app thực sự thu thập
- [ ] Icon không có kênh alpha; `ITSAppUsesNonExemptEncryption = false`; có privacy manifest
- [ ] Gói IAP đã tạo; Restore chạy được; đã thử Sandbox (gói mua vào đúng một lần, còn sau khi mở lại app); có ảnh chụp để nộp review
- [ ] Ảnh iPhone 6.9" (thêm iPad 13" nếu app hỗ trợ iPad), tất cả bằng tiếng Anh
- [ ] Tên, subtitle, từ khoá, mô tả không nhắc tới game gốc hay nhà phát hành của nó
- [ ] `appstore-review-checker` không còn lỗi chặn; checklist `docs/APP-STORE-CONNECT.md` đã điền đủ trên web
- [ ] `appstore-spam-guard --mode submit` không còn FAIL (kể cả J1–J6); team nộp lên không có vụ 4.3 nào đang mở; sau khi nộp đã ghi `ledger.py record`
- [ ] Build mới nhất đã VALID trên TestFlight; tag `vX.Y.Z` đã push

## Ghi chú công cụ

- **REA**: đọc APK bằng JADX và Apktool, có chụp/quay màn hình qua adb. Không nói tới Unity IL2CPP. Bản thân REA giới hạn phạm vi ở "nghiên cứu hợp pháp, phân tích phần mềm được phép".
- **asc** (của Rork, `~/.local/bin/asc`): **đang hoãn** (luật 12), agent không dùng. Khi bỏ hoãn: quản lý bundle id, IAP, metadata, ảnh, build, validate, submit; không tạo được app mới, không build được IPA.
- **Tên skill đúng**: `codebase-modernizer`, `plan-to-issues`, `search-optimizer`, `design-optimizer`.
