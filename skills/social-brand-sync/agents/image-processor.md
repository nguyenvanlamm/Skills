# Image Processor Subagent

Download brand assets và resize theo thông số kỹ thuật của từng nền tảng.

## Input

- `--brand-info`: Path đến brand-info.json
- `--output-dir`: Thư mục output
- `--platforms`: Danh sách platform cần xử lý
- `--logo-override`: URL logo custom (nếu có)
- `--name-override`: Tên custom (nếu có)

## Workflow

### 1. Download Originals

```bash
# Download logo
curl -sL "$LOGO_URL" -o "$OUTPUT_DIR/originals/logo.png"

# Download cover (nếu có URL)
curl -sL "$COVER_URL" -o "$OUTPUT_DIR/originals/cover.png"
```

Nếu download thất bại, dùng favicon làm fallback.

### 2. Xác định Brand Color

Nếu brand-info.json có `colors.primary`:
```bash
PRIMARY_COLOR=$(jq -r '.colors.primary // "#2563eb"' "$BRAND_INFO")
```

Nếu không có, extract từ logo:
```bash
convert "$OUTPUT_DIR/originals/logo.png" -colors 1 -format "%c" histogram:info: | \
  grep -oP '#[0-9A-Fa-f]{6}' | head -1
```

### 3. Resize Cho Từng Platform

Dùng `convert` từ ImageMagick với thông số trong `references/platform-specs.md`:

#### Facebook
```bash
# Profile pic: 180x180 square
convert "$LOGO_PATH" \
  -resize 180x180 -gravity center -extent 180x180 \
  "$OUTPUT_DIR/facebook/profile-pic.png"

# Cover: 851x315 (nếu có cover gốc)
convert "$COVER_PATH" -resize 851x315^ -gravity center -extent 851x315 \
  "$OUTPUT_DIR/facebook/cover.png" 2>/dev/null || \
  convert -size 851x315 "xc:$PRIMARY_COLOR" \
    \( "$LOGO_PATH" -resize 120x120 -gravity center \) -composite \
    "$OUTPUT_DIR/facebook/cover.png"
```

#### LinkedIn
```bash
# Profile pic: 400x400 square
convert "$LOGO_PATH" \
  -resize 400x400 -gravity center -extent 400x400 \
  "$OUTPUT_DIR/linkedin/profile-pic.png"

# Background: 1584x396
convert "$COVER_PATH" -resize 1584x396^ -gravity center -extent 1584x396 \
  "$OUTPUT_DIR/linkedin/cover.png" 2>/dev/null || \
  convert -size 1584x396 "xc:$PRIMARY_COLOR" \
    \( "$LOGO_PATH" -resize 150x150 -gravity west -geometry +40+0 \) \
    \( -size 1584x396 xc:none -fill white -draw "rectangle 0,0 1584,2" \) \
    -composite "$OUTPUT_DIR/linkedin/cover.png"
```

#### Twitter/X
```bash
# Profile pic: 400x400 square
convert "$LOGO_PATH" \
  -resize 400x400 -gravity center -extent 400x400 \
  "$OUTPUT_DIR/twitter/profile-pic.png"

# Header: 1500x500
convert "$COVER_PATH" -resize 1500x500^ -gravity center -extent 1500x500 \
  "$OUTPUT_DIR/twitter/header.png" 2>/dev/null || \
  convert -size 1500x500 "xc:$PRIMARY_COLOR" \
    \( "$LOGO_PATH" -resize 200x200 -gravity center \) -composite \
    "$OUTPUT_DIR/twitter/header.png"
```

#### TikTok
```bash
# Avatar: 200x200 square
convert "$LOGO_PATH" \
  -resize 200x200 -gravity center -extent 200x200 \
  "$OUTPUT_DIR/tiktok/profile-pic.png"
```

#### YouTube
```bash
# Profile pic: 800x800 square
convert "$LOGO_PATH" \
  -resize 800x800 -gravity center -extent 800x800 \
  "$OUTPUT_DIR/youtube/profile-pic.png"

# Banner: 2560x1440 (safe area 1546x423 ở giữa)
convert "$COVER_PATH" -resize 2560x1440^ -gravity center -extent 2560x1440 \
  "$OUTPUT_DIR/youtube/banner.png" 2>/dev/null || \
  convert -size 2560x1440 "xc:$PRIMARY_COLOR" \
    \( "$LOGO_PATH" -resize 300x300 -gravity center \) -composite \
    "$OUTPUT_DIR/youtube/banner.png"
```

#### GitHub
```bash
# Avatar: 512x512 square
convert "$LOGO_PATH" \
  -resize 512x512 -gravity center -extent 512x512 \
  "$OUTPUT_DIR/github/profile-pic.png"
```

### 4. Validate

Kiểm tra từng file đã tạo:

```bash
for platform in facebook linkedin twitter tiktok youtube github; do
  for file in "$OUTPUT_DIR/$platform"/*.png; do
    [ -f "$file" ] || continue
    dimensions=$(identify -format "%wx%h" "$file")
    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file")
    echo "$file: ${dimensions} (${size} bytes)"
  done
done
```

## Output

- Các file PNG trong `$OUTPUT_DIR/{platform}/`
- Log validate kèm kích thước từng ảnh

## Edge Cases

- **Logo không square**: Thêm padding với brand color background thay vì kéo giãn
- **Logo trong suốt (PNG)**: Giữ nguyên trong suốt, dùng nền trắng cho nền tảng yêu cầu
- **Cover ảnh quá nhỏ**: Scale up với `-filter Lanczos`, chấp nhận giảm chất lượng
- **Download thất bại**: Dùng favicon làm fallback cho logo; auto-generate cover
- **File ảnh > 10MB**: Resize xuống, giảm quality JPEG
