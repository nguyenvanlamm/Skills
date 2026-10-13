# Quy trình clone game (bản 1.0)

Biến một game casual/puzzle đang thành công thành một game Flutter **khác rõ**, chỉ có tiếng Anh, rồi đưa lên App Store, kèm landing page. Skill `game-clone-pipeline` chạy quy trình này; file này là bản tóm tắt cho người đọc.

## Nguyên tắc

1. **Chỉ lấy sự kiện và cơ chế.** REA và video cho ra luật chơi và thông số. Không chép asset, ảnh, âm thanh, font, câu chữ, file level hay code của game gốc. Thư mục `.clone/` không đưa vào git.
2. **Tạo khác biệt trước khi vẽ.** Chủ đề, bảng màu, tên gọi và một cơ chế riêng được chốt ở bước S2. Core làm bằng hình tạm; giao diện thật áp vào ở S4.
3. **Thiết kế kinh tế game cùng vòng chơi.** Phải có điều kiện thua thì booster và IAP mới có giá trị.
4. **Game chỉ làm tiếng Anh**: chữ trong game, store listing (en-US), gói IAP, landing page, privacy, support. Tài liệu nội bộ được viết tiếng Việt.
5. **Chỉ dùng main + tag `vX.Y.Z`.** Không mở nhánh `ios` sống lâu.
6. **Cổng chỉ qua khi có bằng chứng**: lệnh thật chạy xong và exit 0, hoặc câu trả lời của người được ghi vào `.clone/status.md`.
7. **Chỉ phát hành App Store.** Không có bước Google Play.
8. **Commit ngay sau mỗi bước** bằng skill `commit`: message tiếng Anh, kèm push. Tag và release để `/ship` làm.

## Các bước

| Bước | Ai | Làm gì | Skill / công cụ | Cổng |
|---|---|---|---|---|
| S0 | Agent → Người | Chọn game: đang lên, hợp Flutter 2D, còn chỗ cho twist, chưa quá bão hoà | `idea-validator` | **G0** duyệt game |
| S1 | Agent + Người | Phân tích APK bằng REA; người chơi và quay 30–60 phút; agent làm contact sheet rồi viết `SPEC.md` | `reverse-engineer-anything`, `scripts/contact-sheet.sh` | **G0b** duyệt SPEC |
| S2 | Agent → Người | `DESIGN.md`: bảng khác biệt, kinh tế game, mục tiêu độ khó, tên game | `brand-name-checker` | **G1** duyệt thiết kế |
| S3 | Agent | Core Flutter với hình tạm: luật bằng Dart thuần, test, bot, `tool/simulate.dart` | `flutter-init`, `test-coverage` | analyze + test exit 0 |
| S4 | Agent → Người | 3 hướng UI → chọn 1 → áp vào Flutter → làm icon | `huashu-design` (hoặc `lam-design`), `flutter-ui-revamp`, `logo-designer` | **G2** chọn hướng |
| S5 | Agent + Người | IAP + Restore, booster chống farm, analytics (nếu chọn), người thật chơi thử, chỉnh lại độ khó | | **G3** duyệt gói và giá |
| S6 | Agent | Soát codebase → issue → sửa | `codebase-modernizer`, `plan-to-issues`, `issue-work-loop` | test xanh |
| S7 | Agent | Repo landing tối thiểu có privacy + support, deploy GitHub Pages | `landing-page-generator`, `templates/pages.yml` | 2 URL sống |
| S8 | Agent + Người | iOS: chuẩn bị trên Ubuntu, **build và upload trên Mac**, TestFlight, ảnh store, ASO, soát, ship, nộp | `flutter-ios-release`, `appstore-assets`, `aso-marketing`, `appstore-review-checker`, `asc`, `/ship` | **G4** duyệt nộp |
| S9 | Agent | Hoàn thiện landing, theo dõi review và số liệu | `search-optimizer`, `design-optimizer`, `asc reviews` | |

## Bước S1: ai làm gì

0. **Agent phân tích APK bằng REA.** Bạn đưa file APK, hoặc agent kéo qua adb. REA đọc manifest, quyền, SDK, engine, product ID và các file config đọc được. Kết quả ghi vào SPEC mục "Từ APK", kèm đường dẫn file làm bằng chứng. Nếu logic nằm trong IL2CPP hoặc trên remote config thì ghi "không lấy được từ APK".
1. **Bạn chơi và quay.** Chơi 30–60 phút qua nhiều level, cố tình thua một lần, mở cửa hàng/booster. Bỏ video vào `.clone/reference/`.
2. **Agent viết SPEC.** Chạy `contact-sheet.sh` (1 khung/giây, có mốc giờ), đọc ảnh, lấy trang store, rồi viết `SPEC.md`. Mỗi luật kèm mốc giây; chỗ nào đoán thì đánh dấu ❓; cuối SPEC là danh sách việc cần quay thêm.
3. **Bạn duyệt.** Trả lời các ❓ hoặc quay thêm, tối đa 2 vòng. ❓ còn lại ghi thành giả định trong `DESIGN.md`.

Khi APK và video mâu thuẫn thì tin video.

## Bước S8: build iOS

Không build trên GitHub Actions. Agent chuẩn bị file trên Ubuntu, bạn build trên Mac:

1. Agent:
   - chạy `flutter-ios-release`;
   - chép `scripts/build-ios.sh` và `ios/ExportOptions.plist` vào repo;
   - viết `docs/IOS-BUILD-ON-MAC.md`;
   - tạo bundle id và gói IAP bằng `asc`;
   - commit.
2. Bạn tạo app trên App Store Connect (web). Trên Mac: `TEAM_ID=… scripts/build-ios.sh upload`.
3. Agent chạy `asc builds wait`. Bạn thử trên TestFlight bằng tài khoản Sandbox: mua, huỷ, cài lại, Restore.
4. Agent:
   - làm ảnh store bằng `appstore-assets`, viết tên và từ khoá bằng `aso-marketing` (chỉ en-US);
   - đẩy lên bằng `asc metadata` và `asc screenshots`;
   - soát bằng `appstore-review-checker` và `asc validate` → **G4**.
5. Agent chạy `/ship --no-auto` (version, tag). Bạn build bản chính thức trên Mac. Agent chạy `asc release stage` rồi nộp.

Chi tiết lệnh ở `references/ios-release-runbook.md`.

## Đối chiếu với flow cũ

| Flow cũ | Quy trình mới |
|---|---|
| Tải APK | S1 bước 0 |
| Dùng REA | S1 bước 0: `reverse-engineer-anything` |
| Lấy thông tin, thông số | `SPEC.md` mục "Từ APK" và các luật quan sát |
| Flutter clone game tương tự | S3 |
| Đổi một ít cho hay hơn, đỡ giống | S2, có cổng khác biệt chặt hơn (`references/differentiation-gate.md`) |
| `huashu-design` ra 3 bản UI/UX | S4 |
| Chọn 1 bản, hoàn thiện UI/UX | S4: `flutter-ui-revamp` + `logo-designer` |
| Thêm IAP giá hợp lý vào cốt game | Thiết kế ở S2, làm ở S5, duyệt giá ở G3 |
| Check sang nhánh mới `ios` | **Thay** bằng main + tag |
| Chuẩn bị iOS để upload | S8: `flutter-ios-release` + bộ build trên Mac |
| `/codebase-optimiser` | S6: `codebase-modernizer` (tên đúng) |
| `/plan-to-` | S6: `plan-to-issues` |
| `/ship` | S8: `/ship --no-auto` |
| asccli | S8: `asc` (tên lệnh đúng) |
| `/appstore-assets` | S8 |
| Tạo repo landing page mới | S7, làm **trước** khi nộp vì cần URL privacy/support |
| `/search-optimiser`, `/design-optimiser` | S9: `search-optimizer`, `design-optimizer` (tên đúng) |
| Push lên GitHub Actions | S7: `templates/pages.yml` deploy lên GitHub Pages mỗi lần push main |

Bước mới thêm vào: `idea-validator`, `brand-name-checker`, `aso-marketing`, `appstore-review-checker`, `asc validate`, người thật chơi thử, `commit` sau mỗi bước.

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

Ngoài ra phải có **ít nhất một cơ chế riêng**. Lý do: Apple 4.1 (Copycats), 4.3 (Spam), và rủi ro trade dress. Bài học từ Coin Cubby: tự vẽ toàn bộ bằng code nhưng vẫn giống gần hết bản gốc.

## Checklist trước khi nộp App Store (cổng G4)

- [ ] URL privacy và support đều sống, nội dung khớp với những gì app thực sự thu thập
- [ ] Icon không có kênh alpha; `ITSAppUsesNonExemptEncryption = false`; có privacy manifest
- [ ] Gói IAP đã tạo; Restore chạy được; đã thử Sandbox; có ảnh chụp để nộp review
- [ ] Ảnh iPhone 6.9" (thêm iPad 13" nếu app hỗ trợ iPad), tất cả bằng tiếng Anh
- [ ] Tên, subtitle, từ khoá, mô tả không nhắc tới game gốc hay nhà phát hành của nó
- [ ] `appstore-review-checker` không còn lỗi chặn; `asc validate` sạch
- [ ] Build mới nhất đã VALID trên TestFlight; tag `vX.Y.Z` đã push

## Ghi chú công cụ

- **REA**: đọc APK bằng JADX và Apktool, có chụp/quay màn hình qua adb. Không nói tới Unity IL2CPP. Bản thân REA giới hạn phạm vi ở "nghiên cứu hợp pháp, phân tích phần mềm được phép".
- **asc** (của Rork, `~/.local/bin/asc`): quản lý app, bundle id, IAP, metadata, ảnh, build, validate, submit. Không tạo được app mới (phải làm trên web). Không build được IPA (cần Mac).
- **Tên skill đúng**: `codebase-modernizer`, `plan-to-issues`, `search-optimizer`, `design-optimizer`.
