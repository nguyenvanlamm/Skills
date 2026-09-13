#!/usr/bin/env bash
# sync.sh — the whole flow: analyze website → process images → per-platform plan (dry-run)
# → optionally apply.
#
#   bash sync.sh --website https://example.com --platforms facebook,linkedin,github
#                [--action all|profile-pic|cover|name] [--brand-name "Override"]
#                [--logo-url <url>] [--cover-url <url>] [--color '#hex']
#                [--output-dir <dir>] [--apply]
#
# Without --apply nothing is written to any platform. The dry run leaves
# <output-dir>/report.json with every item marked planned/skipped/manual, which is
# what the user reviews before a second run with --apply.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBSITE=""; PLATFORMS=""; ACTION="all"; BRAND_NAME=""; OUTPUT_DIR=""; APPLY=false
LOGO_URL=""; COVER_URL=""; COLOR=""
SUPPORTED="facebook linkedin twitter tiktok youtube github"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --website) WEBSITE="$2"; shift 2 ;;
    --platforms) PLATFORMS="$2"; shift 2 ;;
    --action) ACTION="$2"; shift 2 ;;
    --brand-name) BRAND_NAME="$2"; shift 2 ;;
    --logo-url) LOGO_URL="$2"; shift 2 ;;
    --cover-url) COVER_URL="$2"; shift 2 ;;
    --color) COLOR="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    --help|-h) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done
[ -n "$WEBSITE" ]   || { echo "❌ --website required"; exit 1; }
[ -n "$PLATFORMS" ] || { echo "❌ --platforms required (comma-separated: $SUPPORTED)"; exit 1; }
printf '%s' "$WEBSITE" | grep -qE '^https://' || { echo "❌ --website must be an https:// URL"; exit 1; }
for cmd in curl jq python3; do command -v "$cmd" >/dev/null || { echo "❌ Missing: $cmd"; exit 1; }; done
command -v magick >/dev/null || command -v convert >/dev/null || { echo "❌ ImageMagick missing (magick/convert)"; exit 1; }

IFS=',' read -ra PLIST <<< "$PLATFORMS"
for p in "${PLIST[@]}"; do
  printf ' %s ' "$SUPPORTED" | grep -q " $p " || { echo "❌ Unsupported platform '$p'. Supported: $SUPPORTED"; exit 1; }
done

DOMAIN=$(printf '%s' "$WEBSITE" | sed -E 's|^https?://||; s|/.*||')
[ -n "$OUTPUT_DIR" ] || OUTPUT_DIR="/tmp/social-brand-sync/$DOMAIN"
mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════"
echo "  Social Brand Sync — $DOMAIN  ($([ "$APPLY" = true ] && echo APPLY || echo DRY-RUN))"
echo "═══════════════════════════════════════════════"

echo "◆ 1/4 Analyzing website..."
python3 "$SCRIPT_DIR/analyze-website.py" --website "$WEBSITE" --output-dir "$OUTPUT_DIR" >/dev/null
[ -n "$BRAND_NAME" ] || BRAND_NAME=$(jq -r '.name // empty' "$OUTPUT_DIR/brand-info.json")
echo "  name:  $BRAND_NAME  (from $(jq -r '.source.name_from' "$OUTPUT_DIR/brand-info.json"))"
echo "  logo:  $(jq -r '.logo_url // "— none found"' "$OUTPUT_DIR/brand-info.json")  (from $(jq -r '.source.logo_from // "-"' "$OUTPUT_DIR/brand-info.json"))"
echo "  cover: $(jq -r '.cover_url // "— none; will be generated"' "$OUTPUT_DIR/brand-info.json")"
echo "  color: $(jq -r '.colors.primary // "— none"' "$OUTPUT_DIR/brand-info.json")"
HINT=$(jq -r '.spa_hint // empty' "$OUTPUT_DIR/brand-info.json"); [ -z "$HINT" ] || echo "  ⚠ $HINT"

echo "◆ 2/4 Processing images..."
bash "$SCRIPT_DIR/process-images.sh" --output-dir "$OUTPUT_DIR" --platforms "$PLATFORMS" \
  ${LOGO_URL:+--logo-url "$LOGO_URL"} ${COVER_URL:+--cover-url "$COVER_URL"} ${COLOR:+--color "$COLOR"}

# Fresh report for this run; platform rows are added by update-platform.sh.
jq -n --arg w "$WEBSITE" --arg b "$BRAND_NAME" --arg d "$OUTPUT_DIR" --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg src "$(jq -r '[.source.name_from, .source.logo_from] | map(select(.)) | join(" + ")' "$OUTPUT_DIR/brand-info.json")" \
  '{website:$w, brand_name:$b, brand_info_source:$src, processed_at:$t, images_dir:$d, updates:[]}' > "$OUTPUT_DIR/report.json"

echo "◆ 3/4 Platforms ($([ "$APPLY" = true ] && echo applying || echo planning))..."
APPLY_FLAG=""; [ "$APPLY" = true ] && APPLY_FLAG="--apply"
for p in "${PLIST[@]}"; do
  bash "$SCRIPT_DIR/update-platform.sh" --platform "$p" --output-dir "$OUTPUT_DIR" \
    --brand-name "$BRAND_NAME" --action "$ACTION" $APPLY_FLAG || true   # one platform failing must not stop the others
done

echo "◆ 4/4 Report → $OUTPUT_DIR/report.json"
jq -r '.updates[] | "  \(.platform | . + "          " | .[0:10])  pic=\(.profile_pic)  cover=\(.cover)  name=\(.name)\(if .error then "   [" + .error + "]" else "" end)"' "$OUTPUT_DIR/report.json"
echo ""
if [ "$APPLY" = true ]; then
  FAILED=$(jq '[.updates[] | to_entries[] | select(.value=="failed")] | length' "$OUTPUT_DIR/report.json")
  MANUAL=$(jq '[.updates[] | to_entries[] | select(.value=="manual")] | length' "$OUTPUT_DIR/report.json")
  echo "  updated where possible · $FAILED failed · $MANUAL need a manual step (see report errors/instructions)"
  echo "  backups of replaced images: $OUTPUT_DIR/backup/<platform>/"
else
  echo "  This was a dry run. Review the plan above, then re-run with --apply."
  echo "  Narrow the blast radius with --action profile-pic|cover|name or fewer --platforms."
fi
