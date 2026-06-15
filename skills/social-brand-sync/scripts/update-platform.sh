#!/usr/bin/env bash
# update-platform.sh — Cập nhật profile picture / cover / name cho 1 platform
# Usage: bash scripts/update-platform.sh \
#   --platform <facebook|linkedin|twitter|tiktok|youtube|github> \
#   --output-dir <path> \
#   --brand-name <name> \
#   --action <all|profile-pic|cover|name>

set -euo pipefail

# === Parse arguments ===
while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) PLATFORM="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --brand-name) BRAND_NAME="$2"; shift 2 ;;
    --action) ACTION="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

: "${PLATFORM:?Missing --platform}"
: "${OUTPUT_DIR:?Missing --output-dir}"
: "${BRAND_NAME:=}"
: "${ACTION:=all}"

REPORT_FILE="$OUTPUT_DIR/report.json"

# === Helper: ghi log ===
log() {
  echo "[$PLATFORM] $*"
}

update_report() {
  local field="$1" status="$2" error="${3:-null}"
  # Cập nhật JSON report — dùng jq nếu có
  if command -v jq &>/dev/null && [ -f "$REPORT_FILE" ]; then
    local tmp=$(mktemp)
    jq --arg p "$PLATFORM" --arg f "$field" --arg s "$status" --arg e "$error" \
      '(.updates[] | select(.platform == $p) | .[$f]) = $s
      | if $e != "null" then (.updates[] | select(.platform == $p) | .error) = $e else . end' \
      "$REPORT_FILE" > "$tmp" && mv "$tmp" "$REPORT_FILE"
  fi
}

# === Platform-specific updates ===

update_facebook() {
  log "Updating Facebook..."

  if [[ "$ACTION" == "all" || "$ACTION" == "profile-pic" ]]; then
    if [ -f "$OUTPUT_DIR/facebook/profile-pic.png" ]; then
      log "Uploading profile picture..."
      local resp
      resp=$(curl -s -X POST "https://graph.facebook.com/v22.0/${FB_PAGE_ID}/picture" \
        -F "access_token=${FB_PAGE_ACCESS_TOKEN}" \
        -F "source=@$OUTPUT_DIR/facebook/profile-pic.png" \
        -F "type=profile_media")
      if echo "$resp" | jq -e '.error' &>/dev/null; then
        local err=$(echo "$resp" | jq -r '.error.message // "Unknown"')
        log "Profile pic failed: $err"
        update_report "profile_pic" "failed" "$err"
      else
        log "Profile picture updated"
        update_report "profile_pic" "updated"
      fi
    else
      log "No profile pic found — skipping"
      update_report "profile_pic" "skipped" "no file"
    fi
  fi

  if [[ "$ACTION" == "all" || "$ACTION" == "cover" ]]; then
    if [ -f "$OUTPUT_DIR/facebook/cover.png" ]; then
      log "Uploading cover photo..."
      local resp
      resp=$(curl -s -X POST "https://graph.facebook.com/v22.0/${FB_PAGE_ID}/photos" \
        -F "access_token=${FB_PAGE_ACCESS_TOKEN}" \
        -F "source=@$OUTPUT_DIR/facebook/cover.png" \
        -F "published=false")
      local photo_id
      photo_id=$(echo "$resp" | jq -r '.id // empty')
      if [ -n "$photo_id" ]; then
        curl -s -X POST "https://graph.facebook.com/v22.0/${FB_PAGE_ID}" \
          -d "cover=$photo_id" \
          -d "access_token=${FB_PAGE_ACCESS_TOKEN}" > /dev/null
        log "Cover photo updated"
        update_report "cover" "updated"
      else
        local err=$(echo "$resp" | jq -r '.error.message // "Unknown"')
        log "Cover failed: $err"
        update_report "cover" "failed" "$err"
      fi
    else
      log "No cover found — skipping"
      update_report "cover" "skipped" "no file"
    fi
  fi

  if [[ "$ACTION" == "all" || "$ACTION" == "name" ]]; then
    if [ -n "$BRAND_NAME" ]; then
      log "Updating page name..."
      local resp
      resp=$(curl -s -X POST "https://graph.facebook.com/v22.0/${FB_PAGE_ID}" \
        -d "name=${BRAND_NAME}" \
        -d "access_token=${FB_PAGE_ACCESS_TOKEN}")
      if echo "$resp" | jq -e '.error' &>/dev/null; then
        local err=$(echo "$resp" | jq -r '.error.message // "Unknown"')
        log "Name update failed: $err"
        update_report "name" "failed" "$err"
      else
        log "Page name updated"
        update_report "name" "updated"
      fi
    else
      log "No brand name — skipping"
      update_report "name" "skipped" "no name"
    fi
  fi
}

update_linkedin() {
  log "Updating LinkedIn..."

  if [[ "$ACTION" == "all" || "$ACTION" == "profile-pic" ]]; then
    if [ -f "$OUTPUT_DIR/linkedin/profile-pic.png" ]; then
      log "Uploading company logo..."
      local resp
      resp=$(curl -s -X POST "https://api.linkedin.com/v2/assets" \
        -H "Authorization: Bearer ${LINKEDIN_ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
          \"registerUploadRequest\": {
            \"recipes\": [\"urn:li:digitalmediaRecipe:feedshare-image\"],
            \"owner\": \"urn:li:organization:${LINKEDIN_COMPANY_ID}\",
            \"serviceRelationships\": [{
              \"relationshipType\": \"OWNER\",
              \"identifier\": \"urn:li:userGeneratedContent\"
            }]
          }
        }")
      local upload_url
      upload_url=$(echo "$resp" | jq -r '.value.uploadMechanism["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"].uploadUrl // empty')
      if [ -n "$upload_url" ]; then
        curl -s -X POST "$upload_url" \
          -H "Authorization: Bearer ${LINKEDIN_ACCESS_TOKEN}" \
          -T "$OUTPUT_DIR/linkedin/profile-pic.png" > /dev/null
        log "Logo uploaded"
        update_report "profile_pic" "updated"
      else
        local err=$(echo "$resp" | jq -r '.message // "Upload registration failed"')
        log "Logo upload failed: $err"
        update_report "profile_pic" "failed" "$err"
      fi
    else
      update_report "profile_pic" "skipped" "no file"
    fi
  fi

  if [[ "$ACTION" == "all" || "$ACTION" == "cover" ]]; then
    if [ -f "$OUTPUT_DIR/linkedin/cover.png" ]; then
      log "Uploading company background..."
      local resp
      resp=$(curl -s -X POST "https://api.linkedin.com/v2/assets" \
        -H "Authorization: Bearer ${LINKEDIN_ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
          \"registerUploadRequest\": {
            \"recipes\": [\"urn:li:digitalmediaRecipe:feedshare-image\"],
            \"owner\": \"urn:li:organization:${LINKEDIN_COMPANY_ID}\",
            \"serviceRelationships\": [{
              \"relationshipType\": \"OWNER\",
              \"identifier\": \"urn:li:userGeneratedContent\"
            }]
          }
        }")
      local upload_url
      upload_url=$(echo "$resp" | jq -r '.value.uploadMechanism["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"].uploadUrl // empty')
      if [ -n "$upload_url" ]; then
        curl -s -X POST "$upload_url" \
          -H "Authorization: Bearer ${LINKEDIN_ACCESS_TOKEN}" \
          -T "$OUTPUT_DIR/linkedin/cover.png" > /dev/null
        log "Background cover uploaded"
        update_report "cover" "updated"
      else
        local err=$(echo "$resp" | jq -r '.message // "Upload registration failed"')
        log "Cover upload failed: $err"
        update_report "cover" "failed" "$err"
      fi
    else
      update_report "cover" "skipped" "no file"
    fi
  fi
}

update_twitter() {
  log "Updating Twitter/X..."

  if [[ "$ACTION" == "all" || "$ACTION" == "profile-pic" ]]; then
    if [ -f "$OUTPUT_DIR/twitter/profile-pic.png" ]; then
      log "Uploading profile image via v1.1 media/upload..."
      local media_resp
      media_resp=$(curl -s -X POST "https://upload.twitter.com/1.1/media/upload.json" \
        -H "Authorization: OAuth oauth_consumer_key=\"${TWITTER_API_KEY}\", oauth_token=\"${TWITTER_ACCESS_TOKEN}\"" \
        -F "media=@$OUTPUT_DIR/twitter/profile-pic.png")
      local media_id
      media_id=$(echo "$media_resp" | jq -r '.media_id_string // empty')
      if [ -n "$media_id" ]; then
        local resp
        resp=$(curl -s -X POST "https://api.twitter.com/2/users/${TWITTER_USER_ID}/profile_image" \
          -H "Authorization: Bearer ${TWITTER_BEARER_TOKEN}" \
          -H "Content-Type: application/json" \
          -d "{\"profile_image\": {\"media_id\": \"$media_id\"}}")
        if echo "$resp" | jq -e '.errors' &>/dev/null; then
          local err=$(echo "$resp" | jq -r '.errors[0].message // "Unknown"')
          log "Profile image failed: $err"
          update_report "profile_pic" "failed" "$err"
        else
          log "Profile image updated"
          update_report "profile_pic" "updated"
        fi
      else
        log "Media upload failed: $(echo "$media_resp" | jq -r '.errors[0].message // "Unknown"')"
        update_report "profile_pic" "failed" "media upload"
      fi
    else
      update_report "profile_pic" "skipped" "no file"
    fi
  fi

  if [[ "$ACTION" == "all" || "$ACTION" == "cover" ]]; then
    if [ -f "$OUTPUT_DIR/twitter/header.png" ]; then
      local media_resp
      media_resp=$(curl -s -X POST "https://upload.twitter.com/1.1/media/upload.json" \
        -H "Authorization: OAuth oauth_consumer_key=\"${TWITTER_API_KEY}\", oauth_token=\"${TWITTER_ACCESS_TOKEN}\"" \
        -F "media=@$OUTPUT_DIR/twitter/header.png")
      local media_id
      media_id=$(echo "$media_resp" | jq -r '.media_id_string // empty')
      if [ -n "$media_id" ]; then
        local resp
        resp=$(curl -s -X POST "https://api.twitter.com/2/users/${TWITTER_USER_ID}/profile_banner" \
          -H "Authorization: Bearer ${TWITTER_BEARER_TOKEN}" \
          -H "Content-Type: application/json" \
          -d "{\"banner\": {\"media_id\": \"$media_id\"}}")
        if echo "$resp" | jq -e '.errors' &>/dev/null; then
          local err=$(echo "$resp" | jq -r '.errors[0].message // "Unknown"')
          log "Header update failed: $err"
          update_report "cover" "failed" "$err"
        else
          log "Header updated"
          update_report "cover" "updated"
        fi
      fi
    else
      update_report "cover" "skipped" "no file"
    fi
  fi

  if [[ "$ACTION" == "all" || "$ACTION" == "name" ]]; then
    if [ -n "$BRAND_NAME" ]; then
      local resp
      resp=$(curl -s -X PUT "https://api.twitter.com/2/users/${TWITTER_USER_ID}" \
        -H "Authorization: Bearer ${TWITTER_BEARER_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"${BRAND_NAME:0:50}\"}")
      if echo "$resp" | jq -e '.errors' &>/dev/null; then
        local err=$(echo "$resp" | jq -r '.errors[0].message // "Unknown"')
        log "Name update failed: $err"
        update_report "name" "failed" "$err"
      else
        log "Display name updated"
        update_report "name" "updated"
      fi
    else
      update_report "name" "skipped" "no name"
    fi
  fi
}

update_tiktok() {
  log "TikTok API does not support profile updates — generating manual upload guide."

  update_report "profile_pic" "manual" "TikTok API không hỗ trợ update avatar. Upload thủ công tại TikTok Studio."
  update_report "name" "manual" "TikTok API không hỗ trợ update tên. Vào Settings → Edit profile."
}

update_youtube() {
  log "Updating YouTube..."

  if [[ "$ACTION" == "all" || "$ACTION" == "cover" ]]; then
    if [ -f "$OUTPUT_DIR/youtube/banner.png" ]; then
      log "Uploading banner..."
      local resp
      resp=$(curl -s -X POST "https://www.googleapis.com/upload/youtube/v3/channels?part=brandingSettings&uploadType=media" \
        -H "Authorization: Bearer ${YT_ACCESS_TOKEN}" \
        -H "Content-Type: image/png" \
        --data-binary "@$OUTPUT_DIR/youtube/banner.png")
      if echo "$resp" | jq -e '.error' &>/dev/null; then
        local err=$(echo "$resp" | jq -r '.error.message // "Unknown"')
        log "Banner upload failed: $err"
        update_report "cover" "failed" "$err"
      else
        log "Banner updated"
        update_report "cover" "updated"
      fi
    else
      update_report "cover" "skipped" "no file"
    fi
  fi

  if [[ "$ACTION" == "all" || "$ACTION" == "profile-pic" ]]; then
    update_report "profile_pic" "manual" "YouTube API không hỗ trợ update avatar qua API. Upload tại youtube.com/channel/.../branding."
  fi

  if [[ "$ACTION" == "all" || "$ACTION" == "name" ]]; then
    if [ -n "$BRAND_NAME" ]; then
      log "Updating channel name..."
      local resp
      resp=$(curl -s -X PUT "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings&mine=true" \
        -H "Authorization: Bearer ${YT_ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
          \"id\": \"${YT_CHANNEL_ID}\",
          \"brandingSettings\": {
            \"channel\": {
              \"title\": \"${BRAND_NAME:0:70}\"
            }
          }
        }")
      if echo "$resp" | jq -e '.error' &>/dev/null; then
        local err=$(echo "$resp" | jq -r '.error.message // "Unknown"')
        log "Channel name update failed: $err"
        update_report "name" "failed" "$err"
      else
        log "Channel name updated"
        update_report "name" "updated"
      fi
    else
      update_report "name" "skipped" "no name"
    fi
  fi
}

update_github() {
  log "Updating GitHub..."

  if [[ "$ACTION" == "all" || "$ACTION" == "name" ]]; then
    if [ -n "$BRAND_NAME" ]; then
      local resp
      resp=$(curl -s -X PATCH "https://api.github.com/user" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"${BRAND_NAME:0:100}\"}")
      if echo "$resp" | jq -e '.message' &>/dev/null && [ "$(echo "$resp" | jq -r '.message')" != "null" ]; then
        local err=$(echo "$resp" | jq -r '.message // "Unknown"')
        log "Name update failed: $err"
        update_report "name" "failed" "$err"
      else
        log "Profile name updated"
        update_report "name" "updated"
      fi
    else
      update_report "name" "skipped" "no name"
    fi
  fi

  if [[ "$ACTION" == "all" || "$ACTION" == "profile-pic" ]]; then
    # GitHub avatar cần URL public — không thể upload trực tiếp
    update_report "profile_pic" "manual" "GitHub avatar cần URL public. Upload ảnh từ $OUTPUT_DIR/github/profile-pic.png lên GitHub Settings → Profile picture."
  fi
}

# === Main ===
case "$PLATFORM" in
  facebook) update_facebook ;;
  linkedin) update_linkedin ;;
  twitter)  update_twitter ;;
  tiktok)   update_tiktok ;;
  youtube)  update_youtube ;;
  github)   update_github ;;
  *)
    log "Unknown platform: $PLATFORM"
    echo "Supported: facebook, linkedin, twitter, tiktok, youtube, github"
    exit 1
    ;;
esac

log "Done."
