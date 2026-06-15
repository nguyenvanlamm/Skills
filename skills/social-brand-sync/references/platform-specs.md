# Platform Image Specs

Thông số kỹ thuật ảnh cho từng nền tảng.

## Profile Picture (Ảnh đại diện)

| Platform | Display Size | Upload Min | Ratio | Format | Max Size |
|----------|-------------|-----------|-------|--------|----------|
| Facebook Page | 180x180 | 180x180 | 1:1 | JPG/PNG | 8MB |
| LinkedIn Company | 300x300 | 400x400 | 1:1 | JPG/PNG | 8MB |
| Twitter/X | 400x400 | 400x400 | 1:1 | JPG/PNG/GIF | 5MB |
| TikTok | 200x200 | 200x200 | 1:1 | JPG/PNG | 5MB |
| YouTube | 800x800 | 800x800 | 1:1 | JPG/PNG | 5MB |
| GitHub | 512x512 | 512x512 | 1:1 | JPG/PNG | 10MB |

## Cover / Banner / Header

| Platform | Type | Dimensions | Ratio | Safe Zone | Notes |
|----------|------|-----------|-------|-----------|-------|
| Facebook Page | Cover | 851x315 | ~2.7:1 | Center | Min 400x150 |
| Facebook Page (mobile) | Cover | 560x304 | ~1.84:1 | Center | Auto-crop từ desktop |
| LinkedIn Company | Background | 1584x396 | 4:1 | Top 1128px center | Hiển thị tốt nhất ở 1584x396 |
| Twitter/X | Header | 1500x500 | 3:1 | Center | Hiển thị tốt nhất |
| YouTube | Banner | 2560x1440 | 16:9 | 1546x423 ở giữa | Desktop: 2560x423, Mobile: 1546x423, Tablet: 1855x423 |
| GitHub | — | — | — | — | GitHub không có cover/banner |

### YouTube Banner Safe Zones

```
┌─────────────────────────────────────────────────────┐
│                   2560 x 1440                        │
│  ┌───────────────────────────────────────────────┐  │
│  │              Desktop: 2560 x 423              │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │         Tablet: 1855 x 423             │  │  │
│  │  │  ┌───────────────────────────────────┐  │  │  │
│  │  │  │     Mobile: 1546 x 423           │  │  │  │
│  │  │  │     (Nội dung chính)             │  │  │  │
│  │  │  └───────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Display Name Limits

| Platform | Max Length | Notes |
|----------|-----------|-------|
| Facebook Page | 75 chars | Không thể thay đổi quá thường xuyên |
| LinkedIn Company | 100 chars | Cần xác minh để đổi |
| Twitter/X | 50 chars | |
| TikTok | 30 chars | API không hỗ trợ |
| YouTube | 70 chars | Cần verify account |
| GitHub | 100 chars | |

## Image Processing Commands (ImageMagick)

### Resize & Crop Square
```bash
convert input.png -resize ${SIZE}x${SIZE}^ -gravity center -extent ${SIZE}x${SIZE} output.png
```

### Resize Cover (giữ tỉ lệ, crop center)
```bash
convert input.png -resize ${WIDTH}x${HEIGHT}^ -gravity center -extent ${WIDTH}x${HEIGHT} output.png
```

### Auto-Generate Cover từ Brand Color + Logo
```bash
convert -size ${WIDTH}x${HEIGHT} "xc:$COLOR" \
  \( logo.png -resize ${LOGO_SIZE}x${LOGO_SIZE} -gravity center \) -composite \
  output.png
```

### Thêm Border/Padding
```bash
convert input.png -resize ${SIZE}x${SIZE} \
  -background white -gravity center -extent ${SIZE}x${SIZE} \
  output.png
```

### Kiểm tra kích thước
```bash
identify -format "%wx%h %f" output.png
```

### Nén ảnh (giảm dung lượng)
```bash
convert input.png -quality 85 -define png:compression-level=9 output.png
```
