# Website Analyzer Subagent

Phân tích website để trích xuất brand assets: tên thương hiệu, logo, cover image, màu sắc chủ đạo.

## Input

- `--website`: URL website cần phân tích
- `--output-dir`: Thư mục lưu kết quả

## Workflow

### 1. Fetch Website Content

```bash
webfetch "$WEBSITE" --format html > "$OUTPUT_DIR/page.html"
```

### 2. Extract Brand Name

Tìm theo thứ tự ưu tiên:
1. `<meta property="og:site_name" content="...">`
2. `<meta name="application-name" content="...">`
3. `<title>...</title>` (loại bỏ suffix như " — Tagline")
4. Logo `<img>` alt text trong `<header>` hoặc `<nav>`
5. `<meta property="og:title" content="...">`
6. JSON-LD `@type: Organization` → `name`

### 3. Extract Logo URL

Tìm theo thứ tự ưu tiên:
1. `<link rel="apple-touch-icon" sizes="180x180" href="...">` (kích thước lớn nhất)
2. `<link rel="icon" sizes="..." href="...">` (kích thước lớn nhất)
3. `og:image` — filter ảnh có tỉ lệ gần 1:1
4. `<meta name="msapplication-TileImage" content="...">`
5. Logo trong `<header>`: tìm `<img>` mà class/id chứa "logo", "brand"
6. manifest.json → `icons[].src` (kích thước lớn nhất)

### 4. Extract Cover Image

Tìm theo thứ tự ưu tiên:
1. `og:image` — ảnh có tỉ lệ 1.91:1 hoặc kích thước >= 1200x630
2. `twitter:image`
3. Hero section: `<section class="hero">` hoặc `<div class="hero">` background image
4. First large `<img>` trong `<main>`

### 5. Extract Brand Colors

Tìm theo thứ tự ưu tiên:
1. `<meta name="theme-color" content="#...">`
2. CSS custom properties: `--primary`, `--brand-color`, `--color-primary`
3. `:root` style block
4. Dominant color từ logo (dùng `convert logo.png -colors 1 -format "%c" histogram:info:`)

### 6. Save Result

```json
{
  "name": "Example Brand",
  "logo_url": "https://example.com/apple-touch-icon.png",
  "cover_url": "https://example.com/og-image.jpg",
  "favicon_url": "https://example.com/favicon.ico",
  "colors": {
    "primary": "#2563eb",
    "secondary": "#...",
    "theme_color": "#ffffff"
  },
  "source": {
    "name_from": "og:site_name",
    "logo_from": "apple-touch-icon",
    "cover_from": "og:image",
    "color_from": "meta:theme-color"
  }
}
```

## Output

File `$OUTPUT_DIR/brand-info.json`

## Edge Cases

- **Website SPA (React/Vue)**: OG tags phải có trong SSR HTML; nếu không, thử dùng `/?_escaped_fragment_=` hoặc phiên bản cached
- **Logo relative URL**: Resolve thành full URL: `$base_url + $relative_path`
- **Không tìm thấy logo**: Fallback về favicon, báo warning
- **Không tìm thấy brand name**: Dùng domain name (loại bỏ .com, .app, etc.)
- **Nhiều ảnh logo**: Chọn ảnh có kích thước lớn nhất, tỉ lệ gần 1:1 nhất
- **Website không load được**: Trả về lỗi, dừng workflow
