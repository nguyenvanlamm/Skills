---
name: social-brand-sync
description: "Đồng bộ thương hiệu từ website lên mạng xã hội — phân tích website (logo, tên, màu sắc), tạo ảnh đại diện + ảnh bìa đúng kích thước từng nền tảng, và cập nhật qua API. Hỗ trợ Facebook, LinkedIn, Twitter/X, TikTok, YouTube, GitHub. Không dùng cho đăng bài content, quảng cáo, hoặc nền tảng không được hỗ trợ."
license: MIT
effort: max
metadata:
  version: 1.0.0
  author: "Nguyen Van Lam"
---

# Social Brand Sync

Đồng bộ hóa thương hiệu từ website lên mạng xã hội — cập nhật ảnh đại diện, ảnh nền/banner, và tên hiển thị để thống nhất nhận diện thương hiệu trên tất cả nền tảng.

## When to Use

Trigger when:
- Ra mắt website mới, cập nhật brand identity lên các social platforms
- Muốn đồng bộ logo + tên thương hiệu giữa website và mạng xã hội
- Rebrand / thay đổi nhận diện thương hiệu

Do **not** use for:
- Đăng bài content / quảng cáo
- Nền tảng không được hỗ trợ (Instagram, Discord, Reddit, Zalo)
- Chỉnh sửa thông tin không liên quan đến thương hiệu (bio, password, email)

## Prerequisites

### API Tokens (cần setup 1 lần)

| Platform | Env Variable | Scope / Quyền cần |
|----------|-------------|-------------------|
| Facebook | `FB_PAGE_ACCESS_TOKEN` | `pages_manage_metadata`, `pages_read_engagement`, `pages_manage_posts` |
| LinkedIn | `LINKEDIN_ACCESS_TOKEN` | `w_organization_social`, `r_organization_admin` |
| Twitter/X | `TWITTER_ACCESS_TOKEN` + `TWITTER_ACCESS_SECRET` | `tweet.write`, `users.read`, `account.read`, `profile.write` |
| TikTok | `TIKTOK_ACCESS_TOKEN` | `user.info.basic` |
| YouTube | `YT_ACCESS_TOKEN` | `https://www.googleapis.com/auth/youtube.force-ssl` |
| GitHub | `GITHUB_TOKEN` | `user` (repo không cần) |

```bash
export FB_PAGE_ACCESS_TOKEN="EA..."
export LINKEDIN_ACCESS_TOKEN="AQV..."
export TWITTER_ACCESS_TOKEN="..."
export TWITTER_ACCESS_SECRET="..."
export TIKTOK_ACCESS_TOKEN="clt..."
export YT_ACCESS_TOKEN="ya29..."
export GITHUB_TOKEN="ghp_..."
```

### Platform Account IDs

| Platform | Env Variable | Cách lấy |
|----------|-------------|----------|
| Facebook Page ID | `FB_PAGE_ID` | Graph API Explorer → GET /me/accounts → lấy id |
| LinkedIn Company ID | `LINKEDIN_COMPANY_ID` | LinkedIn Company Page URL → `/company/{id}` |
| Twitter User ID | `TWITTER_USER_ID` | API v2: GET /2/users/me |
| TikTok User ID | `TIKTOK_USER_ID` | API: GET /v2/user/info/ |
| YouTube Channel ID | `YT_CHANNEL_ID` | YouTube Studio → Settings → Channel → Channel ID |
| GitHub Username | `GITHUB_USERNAME` | GitHub profile URL |

### Tools

| Tool | Mục đích | Kiểm tra |
|------|----------|----------|
| `curl` | Gọi REST API | `which curl` |
| `jq` | Parse JSON | `which jq` |
| `convert` (ImageMagick) | Resize / crop ảnh | `which convert` |
| `identify` (ImageMagick) | Kiểm tra kích thước ảnh | `which identify` |

```bash
which curl jq convert identify 2>/dev/null || echo "Missing tools — cài ImageMagick: sudo apt install imagemagick"
```

### Temp Directory

```bash
mkdir -p /tmp/social-brand-sync
```

## Subagent Architecture

### Pattern: Sequential Pipeline

```
                     ┌──────────────────────────┐
                     │     Main Orchestrator     │
                     │     (reads SKILL.md)      │
                     └─────────┬──────┬──────────┘
                               │      │
              ┌────────────────┘      └────────────────┐
              ▼                                          ▼
  ┌────────────────────────┐              ┌────────────────────────┐
  │   website-analyzer     │              │    image-processor     │
  │   (general agent)      │              │    (general agent)     │
  │                        │              │                        │
  │   - Fetch website      │              │   - Download logo      │
  │   - Extract logo URL   │              │   - Resize theo        │
  │   - Brand name         │              │     platform specs     │
  │   - Brand colors       │              │   - Generate cover     │
  │   - Cover / OG image   │              │   - Validate output    │
  └───────────┬────────────┘              └───────────┬────────────┘
              │                                       │
              └───────────────┬───────────────────────┘
                              ▼
              ┌──────────────────────────┐
              │   Update Platforms       │
              │   (bash + curl)          │
              │                          │
              │   Facebook  ──────────▶  │
              │   LinkedIn  ──────────▶  │
              │   Twitter/X ──────────▶  │
              │   TikTok    ──────────▶  │
              │   YouTube   ──────────▶  │
              │   GitHub    ──────────▶  │
              └──────────────────────────┘
```

### Agent Files

| File | Vai trò | Output |
|------|---------|--------|
| `agents/website-analyzer.md` | Phân tích website, lấy brand metadata | Brand info JSON |
| `agents/image-processor.md` | Download logo + resize theo platform | Directories with processed images |

## Input Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `--website` | Yes | URL website (VD: `https://example.com`) |
| `--platforms` | Yes | Danh sách platform cách nhau bằng dấu phẩy (VD: `facebook,linkedin,twitter`) |

Supported platforms: `facebook`, `linkedin`, `twitter`, `tiktok`, `youtube`, `github`

## Output

Kết quả trả về dạng JSON + thư mục ảnh đã xử lý:

```
/tmp/social-brand-sync/{domain}/
├── report.json              # Kết quả tổng hợp
├── originals/
│   ├── logo.{png,jpg}       # Logo gốc
│   └── cover.{png,jpg}      # Ảnh bìa gốc (nếu có)
├── facebook/
│   ├── profile-pic.png      # 180x180
│   └── cover.png            # 851x315
├── linkedin/
│   ├── profile-pic.png      # 400x400
│   └── cover.png            # 1584x396
├── twitter/
│   ├── profile-pic.png      # 400x400
│   └── header.png           # 1500x500
├── tiktok/
│   └── profile-pic.png      # 200x200
├── youtube/
│   ├── profile-pic.png      # 800x800
│   └── banner.png           # 2560x1440
└── github/
    └── profile-pic.png      # 512x512
```

```json
{
  "website": "https://example.com",
  "brand_name": "Example Brand",
  "processed_at": "2026-06-16T10:30:00Z",
  "updates": [
    {
      "platform": "facebook",
      "profile_pic": "updated|skipped|failed",
      "cover": "updated|skipped|failed",
      "name": "updated|skipped|failed",
      "url": "https://facebook.com/...",
      "error": null
    }
  ],
  "images_dir": "/tmp/social-brand-sync/example.com"
}
```

## Workflow

### Step 1: Parse Input & Validate

- Parse `--website`, `--platforms`
- Validate URL format, giao thức HTTPS
- Kiểm tra API tokens cho từng platform trong environment
- Kiểm tra ImageMagick (`convert`, `identify`)
- Tạo thư mục output: `/tmp/social-brand-sync/{domain}/`
- Platform thiếu token → skip, ghi vào report

```bash
DOMAIN=$(echo "$WEBSITE" | sed -E 's|https?://||' | sed 's|/.*||')
OUTPUT_DIR="/tmp/social-brand-sync/$DOMAIN"
mkdir -p "$OUTPUT_DIR"/{originals,facebook,linkedin,twitter,tiktok,youtube,github}
```

### Step 2: Analyze Website

Gọi subagent `website-analyzer`:

```bash
task --prompt "Analyze website at $WEBSITE for brand assets..." --subagent-type general
```

Subagent sẽ dùng `webfetch` và phân tích HTML để lấy:

1. **Brand name**: Từ `<title>`, `og:site_name`, logo alt text
2. **Logo URL**: Từ `apple-touch-icon`, `favicon`, OG image, manifest.json, ảnh trong header
3. **Cover image**: Từ `og:image` lớn nhất, hero image, background image
4. **Brand colors**: Từ CSS custom properties, `<meta name="theme-color">`, dominant colors từ logo

Kết quả lưu vào `$OUTPUT_DIR/brand-info.json`:

```json
{
  "name": "Example Brand",
  "logo_url": "https://example.com/logo.png",
  "cover_url": "https://example.com/og-image.jpg",
  "favicon_url": "https://example.com/favicon.ico",
  "colors": {
    "primary": "#2563eb",
    "theme_color": "#ffffff"
  },
  "source": "og:site_name + apple-touch-icon"
}
```

### Step 3: Process Images

Gọi subagent `image-processor`:

```bash
task --prompt "Download and resize brand images from $OUTPUT_DIR/brand-info.json for platforms: $PLATFORMS..." --subagent-type general
```

Subagent sẽ:

1. **Download logo** từ URL → `$OUTPUT_DIR/originals/logo.{png,jpg}`
2. **Download cover** (nếu có) → `$OUTPUT_DIR/originals/cover.{png,jpg}`
3. **Nếu không có cover**: Tạo cover từ logo + brand color với `convert`:
   ```bash
   convert -size 1584x396 "xc:$PRIMARY_COLOR" \
     \( logo.png -resize 200x200 -gravity center -geometry +0+0 -composite \) \
     "$OUTPUT_DIR/linkedin/cover.png"
   ```
4. **Resize logo** cho từng platform theo thông số trong `references/platform-specs.md`:

```bash
# Facebook profile pic (180x180)
convert logo.png -resize 180x180 -gravity center -extent 180x180 "$OUTPUT_DIR/facebook/profile-pic.png"

# LinkedIn profile pic (400x400)
convert logo.png -resize 400x400 -gravity center -extent 400x400 "$OUTPUT_DIR/linkedin/profile-pic.png"

# Twitter header (1500x500)
convert cover.png -resize 1500x500^ -gravity center -extent 1500x500 "$OUTPUT_DIR/twitter/header.png"
```

5. **Validate**: Dùng `identify` kiểm tra kích thước từng file

### Step 4: Update Platforms

Chạy script `scripts/update-platform.sh` cho từng platform (tự động cập nhật logo + banner + tên):

```bash
bash scripts/update-platform.sh \
  --platform <platform> \
  --output-dir "$OUTPUT_DIR" \
  --brand-name "$BRAND_NAME"
```

Hoặc gọi API trực tiếp bằng `curl` nếu platform đơn giản:

#### Facebook (Graph API v22.0)

```bash
# Upload profile picture
curl -X POST "https://graph.facebook.com/v22.0/$FB_PAGE_ID/picture" \
  -F "access_token=$FB_PAGE_ACCESS_TOKEN" \
  -F "source=@$OUTPUT_DIR/facebook/profile-pic.png" \
  -F "type=profile_media"

# Upload cover photo
RESP=$(curl -s -X POST "https://graph.facebook.com/v22.0/$FB_PAGE_ID/photos" \
  -F "access_token=$FB_PAGE_ACCESS_TOKEN" \
  -F "source=@$OUTPUT_DIR/facebook/cover.png" \
  -F "published=false")
PHOTO_ID=$(echo "$RESP" | jq -r '.id')
curl -s -X POST "https://graph.facebook.com/v22.0/$FB_PAGE_ID" \
  -d "cover=$PHOTO_ID&access_token=$FB_PAGE_ACCESS_TOKEN"

# Update name
curl -s -X POST "https://graph.facebook.com/v22.0/$FB_PAGE_ID" \
  -d "name=$BRAND_NAME&access_token=$FB_PAGE_ACCESS_TOKEN"
```

#### LinkedIn (API v2)

```bash
# Upload profile logo (dùng Media Upload API)
UPLOAD_URL=$(curl -s -X POST "https://api.linkedin.com/v2/assets" \
  -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "registerUploadRequest": {
      "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
      "owner": "urn:li:organization:'$LINKEDIN_COMPANY_ID'",
      "serviceRelationships": [{
        "relationshipType": "OWNER",
        "identifier": "urn:li:userGeneratedContent"
      }]
    }
  }' | jq -r '.value.uploadMechanism["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"].uploadUrl')

curl -X POST "$UPLOAD_URL" \
  -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
  -T "$OUTPUT_DIR/linkedin/profile-pic.png"

# Update company logo
ASSET_URN=$(echo $UPLOAD_RESP | jq -r '.value.asset')
curl -s -X POST "https://api.linkedin.com/v2/organizationalEntityAcls" \
  -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
  -d "{
    "patch": {
      "$orgUrn": {
        "logoV2": {
          "com.linkedin.common.VectorImage": {
            "rootUrl": \"$ASSET_URN\"
          }
        }
      }
    }
  }"
```

#### Twitter/X (API v2 + OAuth 1.0a)

Twitter API v2 yêu cầu OAuth 1.0a User Context để cập nhật profile. Dùng script riêng:

```bash
# Update profile image
curl -s -X POST "https://api.twitter.com/2/users/$TWITTER_USER_ID/profile_image" \
  -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"profile_image\": {\"media_id\": \"$MEDIA_ID\"}}"

# Upload media trước
MEDIA_ID=$(curl -s -X POST "https://upload.twitter.com/1.1/media/upload.json" \
  -H "Authorization: OAuth oauth_consumer_key=..., oauth_token=..., oauth_signature=..." \
  -F "media=@$OUTPUT_DIR/twitter/profile-pic.png" | jq -r '.media_id_string')

# Update header
curl -s -X POST "https://api.twitter.com/2/users/$TWITTER_USER_ID/profile_banner" \
  -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"banner\": {\"media_id\": \"$MEDIA_ID\"}}"

# Update name
curl -s -X PUT "https://api.twitter.com/2/users/$TWITTER_USER_ID" \
  -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$BRAND_NAME\"}"
```

#### TikTok

TikTok API không hỗ trợ cập nhật avatar/tên. Skill sẽ:
1. Tạo ảnh avatar đúng kích thước TikTok (200x200)
2. Ghi vào report là "manual — cần upload thủ công"
3. Output hướng dẫn: vào TikTok Studio → Edit profile → Upload ảnh từ thư mục `$OUTPUT_DIR/tiktok/`

#### YouTube (YouTube Data API v3)

```bash
# Update banner
curl -s -X POST "https://www.googleapis.com/upload/youtube/v3/channels?part=brandingSettings&uploadType=media" \
  -H "Authorization: Bearer $YT_ACCESS_TOKEN" \
  -H "Content-Type: image/png" \
  --data-binary "@$OUTPUT_DIR/youtube/banner.png"

# Update profile picture — cần upload lên Google Photos hoặc dùng API riêng
# YouTube API không support trực tiếp, cần dùng Google Account API

# Update channel name
curl -s -X PUT "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings&mine=true" \
  -H "Authorization: Bearer $YT_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "'$YT_CHANNEL_ID'",
    "brandingSettings": {
      "channel": {
        "title": "'$BRAND_NAME'"
      }
    }
  }'
```

#### GitHub (REST API v3)

```bash
# Update avatar (phải là URL public, hoặc upload lên GitHub trước)
# GitHub API không cho upload file trực tiếp làm avatar
# Cần upload ảnh lên 1 URL public trước, rồi:
curl -s -X PATCH "https://api.github.com/user" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "'$BRAND_NAME'",
    "avatar_url": "https://example.com/avatar.png"
  }'
```

### Step 5: Generate Report

Tổng hợp kết quả vào `$OUTPUT_DIR/report.json`:

```json
{
  "website": "https://example.com",
  "brand_name": "Example Brand",
  "brand_info_source": "og:site_name + apple-touch-icon",
  "processed_at": "2026-06-16T10:30:00Z",
  "images_dir": "/tmp/social-brand-sync/example.com",
  "updates": [
    {
      "platform": "facebook",
      "profile_pic": "updated",
      "cover": "updated",
      "name": "skipped",
      "profile_url": "https://facebook.com/example",
      "error": null
    },
    {
      "platform": "tiktok",
      "profile_pic": "manual",
      "name": "manual",
      "profile_url": null,
      "instructions": "Vào TikTok Studio → Edit profile → Upload ảnh từ /tmp/social-brand-sync/example.com/tiktok/profile-pic.png"
    }
  ]
}
```

## Edge Cases

- **Website không có logo rõ ràng**: Dùng favicon, resize lên; báo warning
- **Logo không phải square**: Cắt center, thêm padding với brand color background
- **Website không có OG image / cover**: Tạo cover đơn giản từ brand color + logo
- **API token thiếu hoặc hết hạn**: Skip platform, ghi vào report
- **Rate limit (429)**: Đợi 15s + retry 1 lần; nếu vẫn fail thì skip
- **Ảnh quá lớn (>10MB)**: Resize xuống dưới 5MB, giữ tỉ lệ
- **Platform không support action đó** (VD: TikTok không có cover): Skip action đó
- **Tên quá dài cho platform** (VD: Twitter 50 chars): Cắt ngắn + thêm "..."
- **Mạng xã hội không có trong danh sách hỗ trợ**: Báo lỗi + list platform hợp lệ
- **Website không load được (timeout/404)**: Dừng, báo lỗi

## Acceptance Criteria

- [ ] Website được phân tích thành công — lấy được brand name + logo
- [ ] Logo được download và resize đúng kích thước từng platform
- [ ] Cover image được tạo/resize (từ website hoặc auto-generate)
- [ ] Các platform có API token được cập nhật thành công
- [ ] Platform thiếu token được skip và thông báo
- [ ] TikTok output ảnh + hướng dẫn manual upload
- [ ] Report JSON được generate đầy đủ kết quả
- [ ] ImageMagick được cài đặt và sử dụng thành công
