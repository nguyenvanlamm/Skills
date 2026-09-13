#!/usr/bin/env bash
# update-platform.sh — update profile picture / cover / name on ONE platform.
#
#   bash update-platform.sh --platform <facebook|linkedin|twitter|tiktok|youtube|github> \
#        --output-dir <dir> [--brand-name <name>] [--action all|profile-pic|cover|name] [--apply]
#
# Default is a DRY RUN: every item is evaluated and written to report.json with
# status "planned" (or "skipped"/"manual" with the reason), and nothing is sent.
# --apply performs the writes. Statuses: planned · updated · failed · skipped · manual.
#
# This script changes avatars, covers and display names on real accounts and
# there is no undo. Run the dry run, read the plan, then --apply.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPLY=false; PLATFORM=""; OUTPUT_DIR=""; BRAND_NAME=""; ACTION="all"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) PLATFORM="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --brand-name) BRAND_NAME="$2"; shift 2 ;;
    --action) ACTION="$2"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    --dry-run) APPLY=false; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done
[ -n "$PLATFORM" ]   || { echo "Missing --platform"; exit 1; }
[ -n "$OUTPUT_DIR" ] || { echo "Missing --output-dir"; exit 1; }
case "$ACTION" in all|profile-pic|cover|name) ;; *) echo "Bad --action: $ACTION"; exit 1 ;; esac
command -v jq >/dev/null || { echo "jq required"; exit 1; }
command -v curl >/dev/null || { echo "curl required"; exit 1; }

REPORT_FILE="$OUTPUT_DIR/report.json"
BACKUP_DIR="$OUTPUT_DIR/backup/$PLATFORM"
log() { echo "[$PLATFORM] $*" >&2; }   # stderr, so helper functions can return values on stdout
want() { [[ "$ACTION" == "all" || "$ACTION" == "$1" ]]; }

# --- report.json: create the file and this platform's row if absent ---------
if [ ! -f "$REPORT_FILE" ]; then
  jq -n --arg d "$OUTPUT_DIR" '{website:null, brand_name:null, processed_at:null, images_dir:$d, updates:[]}' > "$REPORT_FILE"
fi
if ! jq -e --arg p "$PLATFORM" '.updates[] | select(.platform==$p)' "$REPORT_FILE" >/dev/null; then
  tmp=$(mktemp)
  jq --arg p "$PLATFORM" '.updates += [{platform:$p, profile_pic:"pending", cover:"pending", name:"pending", profile_url:null, error:null, mode:null}]' \
    "$REPORT_FILE" > "$tmp" && mv "$tmp" "$REPORT_FILE"
fi
set_field() {  # set_field <field> <value>
  local tmp; tmp=$(mktemp)
  jq --arg p "$PLATFORM" --arg f "$1" --arg v "$2" \
    '(.updates[] | select(.platform==$p) | .[$f]) = $v' "$REPORT_FILE" > "$tmp" && mv "$tmp" "$REPORT_FILE"
}
update_report() {  # update_report <field> <status> [error]
  set_field "$1" "$2"
  if [ -n "${3:-}" ]; then
    local tmp; tmp=$(mktemp)
    jq --arg p "$PLATFORM" --arg f "$1" --arg e "$3" \
      '(.updates[] | select(.platform==$p) | .error) = ((.updates[] | select(.platform==$p) | .error // "") + (if (.updates[] | select(.platform==$p) | .error) then "; " else "" end) + $f + ": " + $e)' \
      "$REPORT_FILE" > "$tmp" && mv "$tmp" "$REPORT_FILE"
  fi
}
set_field mode "$([ "$APPLY" = true ] && echo apply || echo dry-run)"
# Each run starts with a clean error slot for this platform; a stale "missing env"
# from a previous dry run must not survive into an apply report.
tmp=$(mktemp); jq --arg p "$PLATFORM" '(.updates[] | select(.platform==$p) | .error) = null' "$REPORT_FILE" > "$tmp" && mv "$tmp" "$REPORT_FILE"

# --- item helpers -----------------------------------------------------------
# plan <field> <description>   → in dry-run: record "planned", print, return 1 (skip the write)
plan() {
  if [ "$APPLY" = true ]; then return 0; fi
  log "  [plan] $2"; update_report "$1" "planned"; return 1
}
skip() { log "  ⏭  $1 — $2"; update_report "$1" "skipped" "$2"; }
manual() { log "  ✋ $1 — manual: $2"; update_report "$1" "manual" "$2"; }

need_env() {  # need_env VAR... → 0 if all set, else marks every wanted field skipped and returns 1
  local missing=""
  for v in "$@"; do [ -n "${!v:-}" ] || missing="$missing $v"; done
  [ -z "$missing" ] && return 0
  log "no credentials — missing:$missing"
  for f in profile_pic cover name; do
    case "$f" in profile_pic) want profile-pic || continue ;; cover) want cover || continue ;; name) want name || continue ;; esac
    update_report "$f" "skipped" "missing env:$missing"
  done
  return 1
}

# http <method> <url> [curl args...] → sets HTTP_CODE and HTTP_BODY; retries once on 429/5xx
http() {
  local method="$1" url="$2"; shift 2
  local attempt=1 out
  while :; do
    out=$(curl -sS -w '\n%{http_code}' -X "$method" "$url" "$@" 2>&1) || out="$out"$'\n'"000"
    HTTP_CODE="${out##*$'\n'}"; HTTP_BODY="${out%$'\n'*}"
    case "$HTTP_CODE" in
      429|5*) if [ "$attempt" -lt 2 ]; then log "  HTTP $HTTP_CODE — retrying in 15s"; sleep 15; attempt=$((attempt+1)); continue; fi ;;
    esac
    break
  done
  [[ "$HTTP_CODE" =~ ^2 ]]
}
err_of() { printf '%s' "$HTTP_BODY" | jq -r '.error.message // .message // .errors[0].message // .error // .' 2>/dev/null | head -c 200; }

backup_current() {  # backup_current <name> <url>
  local name="$1" url="$2"
  [ -n "$url" ] || { log "  ⚠ cannot fetch current $name for backup"; return 0; }
  mkdir -p "$BACKUP_DIR"
  if curl -sSL --max-time 30 -o "$BACKUP_DIR/$name" "$url"; then log "  backup: $BACKUP_DIR/$name"; else log "  ⚠ backup of $name failed"; fi
}

[ "$APPLY" = true ] || log "DRY-RUN — nothing is sent. Add --apply to execute."

# ============================================================================
update_facebook() {
  local base="https://graph.facebook.com/v22.0"
  need_env FB_PAGE_ACCESS_TOKEN FB_PAGE_ID || return 0
  set_field profile_url "https://facebook.com/${FB_PAGE_ID}"

  if want profile-pic; then
    local f="$OUTPUT_DIR/facebook/profile-pic.png"
    if [ ! -f "$f" ]; then skip profile_pic "no file $f"
    elif plan profile_pic "set Page picture from $f"; then
      backup_current profile-pic-old "$(curl -s "$base/${FB_PAGE_ID}/picture?redirect=0&type=large&access_token=${FB_PAGE_ACCESS_TOKEN}" | jq -r '.data.url // empty')"
      if http POST "$base/${FB_PAGE_ID}/picture" -F "access_token=${FB_PAGE_ACCESS_TOKEN}" -F "source=@$f" -F "type=profile_media"; then
        log "  ✅ profile picture updated"; update_report profile_pic updated
      else log "  ❌ profile picture: $(err_of)"; update_report profile_pic failed "$(err_of)"; fi
    fi
  fi

  if want cover; then
    local f="$OUTPUT_DIR/facebook/cover.png"
    if [ ! -f "$f" ]; then skip cover "no file $f"
    elif plan cover "upload unpublished photo from $f and set it as Page cover"; then
      if http POST "$base/${FB_PAGE_ID}/photos" -F "access_token=${FB_PAGE_ACCESS_TOKEN}" -F "source=@$f" -F "published=false"; then
        local photo_id; photo_id=$(printf '%s' "$HTTP_BODY" | jq -r '.id // empty')
        if [ -n "$photo_id" ] && http POST "$base/${FB_PAGE_ID}" --data-urlencode "cover=$photo_id" --data-urlencode "access_token=${FB_PAGE_ACCESS_TOKEN}"; then
          log "  ✅ cover updated"; update_report cover updated
        else log "  ❌ cover (set): $(err_of)"; update_report cover failed "$(err_of)"; fi
      else log "  ❌ cover (upload): $(err_of)"; update_report cover failed "$(err_of)"; fi
    fi
  fi

  if want name; then
    if [ -z "$BRAND_NAME" ]; then skip name "no --brand-name"
    else
      log "  ⚠ Facebook limits how often a Page can be renamed and may put the change under review."
      if plan name "rename Page to '${BRAND_NAME:0:75}'"; then
        if http POST "$base/${FB_PAGE_ID}" --data-urlencode "name=${BRAND_NAME:0:75}" --data-urlencode "access_token=${FB_PAGE_ACCESS_TOKEN}" \
           && ! printf '%s' "$HTTP_BODY" | jq -e '.error' >/dev/null 2>&1; then
          log "  ✅ name updated"; update_report name updated
        else log "  ❌ name: $(err_of)"; update_report name failed "$(err_of)"; fi
      fi
    fi
  fi
}

# ============================================================================
update_linkedin() {
  need_env LINKEDIN_ACCESS_TOKEN LINKEDIN_COMPANY_ID || return 0
  local org="urn:li:organization:${LINKEDIN_COMPANY_ID}"
  set_field profile_url "https://www.linkedin.com/company/${LINKEDIN_COMPANY_ID}/"
  local H=(-H "Authorization: Bearer ${LINKEDIN_ACCESS_TOKEN}" -H "X-Restli-Protocol-Version: 2.0.0" -H "LinkedIn-Version: ${LINKEDIN_API_VERSION:-202409}")

  # upload_asset <file> → prints asset URN or empty. Register → PUT bytes.
  upload_asset() {
    local body; body=$(jq -n --arg o "$org" '{registerUploadRequest:{recipes:["urn:li:digitalmediaRecipe:feedshare-image"],owner:$o,serviceRelationships:[{relationshipType:"OWNER",identifier:"urn:li:userGeneratedContent"}]}}')
    http POST "https://api.linkedin.com/v2/assets?action=registerUpload" "${H[@]}" -H "Content-Type: application/json" -d "$body" || return 1
    local url asset
    url=$(printf '%s' "$HTTP_BODY" | jq -r '.value.uploadMechanism["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"].uploadUrl // empty')
    asset=$(printf '%s' "$HTTP_BODY" | jq -r '.value.asset // empty')
    [ -n "$url" ] && [ -n "$asset" ] || return 1
    http PUT "$url" -H "Authorization: Bearer ${LINKEDIN_ACCESS_TOKEN}" --upload-file "$1" || return 1
    printf '%s' "$asset"
  }
  # apply_asset <field logoV2|coverPhotoV2> <asset-urn>: PARTIAL_UPDATE on the organization.
  # Uploading alone changes nothing visible — the old script reported "updated" after this step.
  apply_asset() {
    local body; body=$(jq -n --arg f "$1" --arg a "$2" '{patch:{"$set":{($f):{original:$a}}}}')
    http POST "https://api.linkedin.com/v2/organizations/${LINKEDIN_COMPANY_ID}" "${H[@]}" -H "X-RestLi-Method: PARTIAL_UPDATE" \
      -H "Content-Type: application/json" -d "$body"
  }

  for item in "profile-pic|profile_pic|logoV2|$OUTPUT_DIR/linkedin/profile-pic.png|company logo" \
              "cover|cover|coverPhotoV2|$OUTPUT_DIR/linkedin/cover.png|company cover"; do
    IFS='|' read -r act field li_field f label <<<"$item"
    want "$act" || continue
    if [ ! -f "$f" ]; then skip "$field" "no file $f"
    elif plan "$field" "upload $f as asset, then PARTIAL_UPDATE organization.$li_field"; then
      local asset; asset=$(upload_asset "$f") || { log "  ❌ $label upload: $(err_of)"; update_report "$field" failed "upload: $(err_of)"; continue; }
      if apply_asset "$li_field" "$asset"; then log "  ✅ $label applied"; update_report "$field" updated
      else log "  ❌ $label apply (HTTP $HTTP_CODE): $(err_of) — needs an admin token with rw_organization_admin"; update_report "$field" failed "apply: HTTP $HTTP_CODE $(err_of)"; fi
    fi
  done

  if want name; then
    manual name "LinkedIn does not expose organization name changes via API (Page admin → Edit page → Name)."
  fi
}

# ============================================================================
update_twitter() {
  # Writes need OAuth 1.0a user context — see twitter_oauth1.py. A bearer token cannot do this.
  need_env TWITTER_API_KEY TWITTER_API_SECRET TWITTER_ACCESS_TOKEN TWITTER_ACCESS_SECRET || return 0
  command -v python3 >/dev/null || { for f in profile_pic cover name; do update_report $f skipped "python3 required for OAuth 1.0a signing"; done; return 0; }
  local py="$SCRIPT_DIR/twitter_oauth1.py"
  tw() {  # tw <field> <args...> → updated/failed
    local field="$1"; shift
    local out; out=$(python3 "$py" "$@" 2>&1)
    if printf '%s' "$out" | jq -e '.ok==true' >/dev/null 2>&1; then log "  ✅ $field updated"; update_report "$field" updated
    else local e; e=$(printf '%s' "$out" | jq -r '.body | if type=="object" then (.errors[0].message // tostring) else tostring end' 2>/dev/null | head -c 200); [ -n "$e" ] || e="$out"
         log "  ❌ $field: $e"; update_report "$field" failed "$e"; fi
  }
  if want profile-pic; then
    local f="$OUTPUT_DIR/twitter/profile-pic.png"
    if [ ! -f "$f" ]; then skip profile_pic "no file $f"
    elif plan profile_pic "POST 1.1/account/update_profile_image with $f (OAuth 1.0a)"; then tw profile_pic profile_image --file "$f"; fi
  fi
  if want cover; then
    local f="$OUTPUT_DIR/twitter/header.png"
    if [ ! -f "$f" ]; then skip cover "no file $f"
    elif plan cover "POST 1.1/account/update_profile_banner with $f (OAuth 1.0a)"; then tw cover profile_banner --file "$f"; fi
  fi
  if want name; then
    if [ -z "$BRAND_NAME" ]; then skip name "no --brand-name"
    elif plan name "POST 1.1/account/update_profile name='${BRAND_NAME:0:50}'"; then tw name profile --name "${BRAND_NAME:0:50}"; fi
  fi
}

# ============================================================================
update_tiktok() {
  want profile-pic && manual profile_pic "TikTok has no profile-update API. TikTok Studio → Edit profile → upload $OUTPUT_DIR/tiktok/profile-pic.png"
  want name && manual name "TikTok has no profile-update API. Settings → Edit profile → Name"
  want cover && skip cover "TikTok has no cover image"
}

# ============================================================================
update_youtube() {
  need_env YT_ACCESS_TOKEN YT_CHANNEL_ID || return 0
  set_field profile_url "https://www.youtube.com/channel/${YT_CHANNEL_ID}"
  local A=(-H "Authorization: Bearer ${YT_ACCESS_TOKEN}")

  if want cover; then
    local f="$OUTPUT_DIR/youtube/banner.png"
    if [ ! -f "$f" ]; then skip cover "no file $f"
    elif plan cover "channelBanners.insert $f, then channels.update brandingSettings.image.bannerExternalUrl"; then
      # Two steps: upload the image (returns a URL), then point the channel at it.
      # The old script POSTed the bytes to /channels, which is not an upload endpoint.
      if http POST "https://www.googleapis.com/upload/youtube/v3/channelBanners/insert?uploadType=media" "${A[@]}" \
           -H "Content-Type: image/png" --data-binary "@$f"; then
        local burl; burl=$(printf '%s' "$HTTP_BODY" | jq -r '.url // empty')
        local body; body=$(jq -n --arg id "$YT_CHANNEL_ID" --arg u "$burl" '{id:$id, brandingSettings:{image:{bannerExternalUrl:$u}}}')
        if [ -n "$burl" ] && http PUT "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings" "${A[@]}" -H "Content-Type: application/json" -d "$body"; then
          log "  ✅ banner updated"; update_report cover updated
        else log "  ❌ banner (apply): $(err_of)"; update_report cover failed "apply: $(err_of)"; fi
      else log "  ❌ banner (upload): $(err_of)"; update_report cover failed "upload: $(err_of)"; fi
    fi
  fi

  want profile-pic && manual profile_pic "YouTube Data API cannot set the channel avatar. YouTube Studio → Customization → Branding → Picture: $OUTPUT_DIR/youtube/profile-pic.png"

  if want name; then
    if [ -z "$BRAND_NAME" ]; then skip name "no --brand-name"
    elif plan name "channels.update brandingSettings.channel.title='${BRAND_NAME:0:70}'"; then
      # channels.update replaces the whole brandingSettings.channel object; fetch it first so
      # description/keywords/country are not wiped by sending only a title.
      http GET "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings&id=${YT_CHANNEL_ID}" "${A[@]}" || true
      local current; current=$(printf '%s' "$HTTP_BODY" | jq -c '.items[0].brandingSettings.channel // {}' 2>/dev/null || echo '{}')
      local body; body=$(jq -n --arg id "$YT_CHANNEL_ID" --arg t "${BRAND_NAME:0:70}" --argjson ch "$current" '{id:$id, brandingSettings:{channel:($ch + {title:$t})}}')
      if http PUT "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings" "${A[@]}" -H "Content-Type: application/json" -d "$body"; then
        log "  ✅ channel name updated"; update_report name updated
      else log "  ❌ name: $(err_of)"; update_report name failed "$(err_of)"; fi
    fi
  fi
}

# ============================================================================
update_github() {
  need_env GITHUB_TOKEN || return 0
  if want name; then
    if [ -z "$BRAND_NAME" ]; then skip name "no --brand-name"
    elif plan name "PATCH /user name='${BRAND_NAME:0:100}'"; then
      if http PATCH "https://api.github.com/user" -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json" \
           -d "$(jq -n --arg n "${BRAND_NAME:0:100}" '{name:$n}')"; then
        set_field profile_url "$(printf '%s' "$HTTP_BODY" | jq -r '.html_url // empty')"
        log "  ✅ profile name updated"; update_report name updated
      else log "  ❌ name: $(err_of)"; update_report name failed "$(err_of)"; fi
    fi
  fi
  want profile-pic && manual profile_pic "GitHub has no avatar upload API. Settings → Public profile → Profile picture: $OUTPUT_DIR/github/profile-pic.png"
  want cover && skip cover "GitHub has no cover image"
}

# ============================================================================
case "$PLATFORM" in
  facebook) update_facebook ;;
  linkedin) update_linkedin ;;
  twitter)  update_twitter ;;
  tiktok)   update_tiktok ;;
  youtube)  update_youtube ;;
  github)   update_github ;;
  *) log "Unknown platform: $PLATFORM"; echo "Supported: facebook, linkedin, twitter, tiktok, youtube, github"; exit 1 ;;
esac

# Untouched fields (action filter) stay "pending" → mark them as not requested.
for f in profile_pic cover name; do
  cur=$(jq -r --arg p "$PLATFORM" --arg f "$f" '.updates[] | select(.platform==$p) | .[$f]' "$REPORT_FILE")
  [ "$cur" = "pending" ] && set_field "$f" "not-requested"
done
log "Done → $(jq -c --arg p "$PLATFORM" '.updates[] | select(.platform==$p) | {profile_pic,cover,name}' "$REPORT_FILE")"
