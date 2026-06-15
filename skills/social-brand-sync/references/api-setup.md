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
   - `w_organization_social`, `r_organization_admin`
   - `w_member_social` (nếu cần personal profile)
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
- Twitter Developer account (Basic/Pro để có profile.write scope)
- Project + App trong Developer Portal

### Steps

1. **Tạo Project**
   - Vào https://developer.twitter.com/en/portal/projects
   - Create Project → "Editing Twitter profile"

2. **Tạo App**
   - OAuth 1.0a → Consumer Keys
   - OAuth 2.0 → Client ID + Secret
   - Scopes: `tweet.write`, `users.read`, `account.read`, `profile.write`, `offline.access`

3. **Lấy Access Token + Secret**
   - Keys and tokens → Access Token and Secret
   - Hoặc dùng OAuth 2.0 PKCE flow

4. **Lấy User ID**
   ```bash
   curl -s "https://api.twitter.com/2/users/me" \
     -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" | jq -r '.data.id'
   ```

### Env Variables
```bash
export TWITTER_ACCESS_TOKEN="..."
export TWITTER_ACCESS_SECRET="..."
export TWITTER_BEARER_TOKEN="AAAA..."
export TWITTER_USER_ID="123456789"
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
   # Dùng gcloud CLI hoặc OAuth 2.0 playground
   # https://developers.google.com/oauthplayground
   # Chọn YouTube Data API v3 → scope youtube.force-ssl
   ```

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

# Twitter
curl -s "https://api.twitter.com/2/users/me" -H "Authorization: Bearer $TWITTER_BEARER_TOKEN"

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
