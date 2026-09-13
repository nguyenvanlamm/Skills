# API Setup Guide

Hướng dẫn lấy API tokens cho từng nền tảng để cập nhật profile.

---

## Facebook

### Requirements
- Facebook Developer account
- Facebook Page (để cập nhật avatar/cover page)

### Steps

1. **Tạo Facebook App**
   - Vào https://developers.facebook.com/apps/
   - Create App → Business

2. **Thêm sản phẩm**
   - Facebook Login → Settings → Valid OAuth Redirect URIs
   - Instagram Graph API (nếu cần sau này)

3. **Lấy Page Access Token**
   - Tools → Graph API Explorer
   - Chọn App + Page
   - Scopes: `pages_manage_metadata`, `pages_read_engagement`, `pages_manage_posts`, `pages_show_list`
   - Generate Access Token → Copy

4. **Lấy Page ID**
   ```bash
   curl -s "https://graph.facebook.com/v22.0/me/accounts?access_token=$FB_PAGE_ACCESS_TOKEN" | jq '.data[0].id'
   ```

### Env Variables
```bash
export FB_PAGE_ACCESS_TOKEN="EA..."
export FB_PAGE_ID="123456789"
```

---

## LinkedIn

### Requirements
- LinkedIn Developer account
- LinkedIn Company Page (Organization)

### Steps

1. **Tạo LinkedIn App**
   - Vào https://www.linkedin.com/developers/apps/
   - Create App → Điền thông tin

2. **Request scopes**
   - `rw_organization_admin` — **bắt buộc** để đổi logo/cover của Company Page (`PARTIAL_UPDATE /v2/organizations/{id}`); `w_organization_social` chỉ đủ để đăng bài
   - Cần Community Management API access và tài khoản phải là **admin** của Page
   - Đổi **tên** Company Page không có API — làm tay trong Page admin
   - Redirect URL: `https://www.linkedin.com/developers/tools/oauth/redirect`

3. **Lấy Access Token** (OAuth 2.0 Authorization Code Flow)
   ```bash
   # Step 1: Get authorization code (mở browser)
   # https://www.linkedin.com/oauth/v2/authorization
   #   ?response_type=code
   #   &client_id={CLIENT_ID}
   #   &redirect_uri={REDIRECT_URI}
   #   &scope=w_organization_social,r_organization_admin

   # Step 2: Exchange code for token
   curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
     -d "grant_type=authorization_code" \
     -d "code={CODE}" \
     -d "redirect_uri={REDIRECT_URI}" \
     -d "client_id={CLIENT_ID}" \
     -d "client_secret={CLIENT_SECRET}"
   ```

4. **Lấy Company ID**
   - Vào LinkedIn Company Page
   - URL: `https://www.linkedin.com/company/{company-id}/`
   - Hoặc dùng API: `GET https://api.linkedin.com/v2/organizationalEntityAcls`

### Env Variables
```bash
export LINKEDIN_ACCESS_TOKEN="AQV..."
export LINKEDIN_COMPANY_ID="12345678"
```

---

## Twitter / X

### Requirements
- Twitter/X Developer account với tier cho phép ghi profile (Basic trở lên — từ 2023 Free tier không gọi được `account/update_profile*`; lỗi 402/403 là vấn đề gói)
- Project + App trong Developer Portal, **App permissions = Read and write**

### Tại sao cần OAuth 1.0a
Đổi avatar/banner/tên chỉ có trên các endpoint v1.1 `account/update_profile_image`, `account/update_profile_banner`, `account/update_profile`. Chúng yêu cầu **OAuth 1.0a user context** (request ký HMAC-SHA1). Bearer token (app-only) và các endpoint kiểu `POST /2/users/:id/profile_image` **không tồn tại** — bản cũ của skill gọi chúng và luôn thất bại. `scripts/twitter_oauth1.py` ký và gọi đúng endpoint.

### Steps

1. **Tạo Project**
   - Vào https://developer.twitter.com/en/portal/projects
   - Create Project → "Editing Twitter profile"

2. **Tạo App**
   - OAuth 1.0a → Consumer Keys
   - OAuth 2.0 → Client ID + Secret
   - Scopes: `tweet.write`, `users.read`, `account.read`, `profile.write`, `offline.access`

3. **Lấy 4 khoá OAuth 1.0a**
   - Keys and tokens → **API Key and Secret** (consumer) và **Access Token and Secret** (của tài khoản sẽ đổi)
   - Nếu Access Token được tạo khi app còn Read-only → Regenerate sau khi đổi permission

4. **Kiểm tra**
   ```bash
   python3 scripts/twitter_oauth1.py verify   # 200 + screen_name là đúng khoá
   ```

### Env Variables
```bash
export TWITTER_API_KEY="..."        # consumer key
export TWITTER_API_SECRET="..."     # consumer secret
export TWITTER_ACCESS_TOKEN="..."
export TWITTER_ACCESS_SECRET="..."
```

---

## TikTok

### Requirements
- TikTok for Developers account
- Business Account

### Steps

1. **Tạo App**
   - Vào https://developers.tiktok.com/apps/
   - Create App → Scopes: `user.info.basic`

2. **Lấy Access Token**
   - OAuth 2.0 → Authorization Code flow
   - Lưu ý: TikTok API hiện tại không hỗ trợ cập nhật avatar/tên

3. **Lấy User ID**
   ```bash
   curl -s "https://open.tiktokapis.com/v2/user/info/" \
     -H "Authorization: Bearer $TIKTOK_ACCESS_TOKEN"
   ```

### Env Variables
```bash
export TIKTOK_ACCESS_TOKEN="clt..."
export TIKTOK_USER_ID="..."
```

---

## YouTube

### Requirements
- Google Cloud Project
- YouTube Data API v3 enabled

### Steps

1. **Tạo Google Cloud Project**
   - Vào https://console.cloud.google.com/
   - New Project → Enable YouTube Data API v3

2. **Tạo OAuth 2.0 Credentials**
   - APIs & Services → Credentials
   - Create OAuth client ID → Desktop app
   - Scopes: `https://www.googleapis.com/auth/youtube.force-ssl`

3. **Lấy Access Token**
   ```bash
   # OAuth 2.0 playground: https://developers.google.com/oauthplayground
   # Chọn YouTube Data API v3 → scope youtube.force-ssl → Authorize → Exchange → copy access_token
   # Token hết hạn sau 1 giờ — lấy ngay trước khi --apply
   ```

   Banner: `channelBanners.insert` (upload) rồi `channels.update` với `brandingSettings.image.bannerExternalUrl` — script làm cả hai bước. Avatar kênh **không** đổi được qua API.

4. **Lấy Channel ID**
   ```bash
   curl -s "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true" \
     -H "Authorization: Bearer $YT_ACCESS_TOKEN" | jq -r '.items[0].id'
   ```

### Env Variables
```bash
export YT_ACCESS_TOKEN="ya29..."
export YT_CHANNEL_ID="UC..."
```

---

## GitHub

### Requirements
- GitHub account

### Steps

1. **Tạo Personal Access Token**
   - Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token
   - Scope: `user` (cần để update name)
   - Lưu ý: Fine-grained token cũng được

### Env Variables
```bash
export GITHUB_TOKEN="ghp_..."
export GITHUB_USERNAME="your-username"
```

---

## Kiểm tra token

```bash
# Facebook
curl -s "https://graph.facebook.com/debug_token?input_token=$FB_PAGE_ACCESS_TOKEN&access_token=$FB_PAGE_ACCESS_TOKEN" | jq .

# LinkedIn
curl -s "https://api.linkedin.com/v2/me" -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN"

# Twitter/X (OAuth 1.0a)
python3 scripts/twitter_oauth1.py verify

# YouTube
curl -s "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true" \
  -H "Authorization: Bearer $YT_ACCESS_TOKEN"

# GitHub
curl -s "https://api.github.com/user" -H "Authorization: Bearer $GITHUB_TOKEN"
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `(#200) Missing permissions` | Token thiếu scope | Re-auth với đủ scopes |
| `Error validating access token` | Token hết hạn | Refresh / lấy lại |
| `Rate limit exceeded` | Gọi API quá nhiều | Đợi 15 phút |
| `401 Unauthorized` | Token sai / hết hạn | Kiểm tra env variable |
| `403 Forbidden` | Không có quyền | Kiểm tra scope / role |
| `404 Not Found` | Wrong ID (Page/Company) | Kiểm tra lại ID |
| TikTok API không có endpoint | TikTok không hỗ trợ update profile qua API | Upload thủ công |
| X: `402 Payment Required` / `453` | Tier API không có quyền v1.1 account endpoints | Nâng tier hoặc đổi tay trong X Settings |
| X: `401 Could not authenticate` | Sai một trong 4 khoá, hoặc Access Token tạo lúc app còn Read-only | Regenerate Access Token sau khi bật Read and write |
| LinkedIn: `403` khi PARTIAL_UPDATE | Token không phải admin Page / thiếu `rw_organization_admin` | Xin lại token với scope đúng bằng tài khoản admin |
| YouTube: `403 insufficientPermissions` | Token thiếu scope `youtube.force-ssl` hoặc không phải chủ kênh | Lấy lại token đúng scope |
