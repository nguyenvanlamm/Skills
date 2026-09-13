#!/usr/bin/env bash
# Download the brand originals and produce every platform-sized image.
#   bash process-images.sh --output-dir <dir> [--platforms facebook,linkedin,...]
#                          [--logo-url <url>] [--cover-url <url>] [--color '#2563eb']
# Reads <output-dir>/brand-info.json (from analyze-website.py) unless overridden.
# Writes <output-dir>/<platform>/*.png and <output-dir>/images-manifest.json.
# Exit 0 when every requested image exists at the right size; 1 otherwise.
set -euo pipefail

OUTPUT_DIR=""; PLATFORMS="facebook,linkedin,twitter,tiktok,youtube,github"
LOGO_URL=""; COVER_URL=""; COLOR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --platforms) PLATFORMS="$2"; shift 2 ;;
    --logo-url) LOGO_URL="$2"; shift 2 ;;
    --cover-url) COVER_URL="$2"; shift 2 ;;
    --color) COLOR="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done
[ -n "$OUTPUT_DIR" ] || { echo "❌ --output-dir required"; exit 1; }

# ImageMagick 7 ships `magick`; 6 ships `convert`/`identify`. Support both.
if command -v magick >/dev/null; then IM="magick"; IDENT="magick identify"
elif command -v convert >/dev/null; then IM="convert"; IDENT="identify"
else echo "❌ ImageMagick not found (apt install imagemagick / brew install imagemagick)"; exit 1; fi
command -v jq >/dev/null || { echo "❌ jq required"; exit 1; }

INFO="$OUTPUT_DIR/brand-info.json"
if [ -f "$INFO" ]; then
  [ -n "$LOGO_URL" ]  || LOGO_URL=$(jq -r '.logo_url // .favicon_url // empty' "$INFO")
  [ -n "$COVER_URL" ] || COVER_URL=$(jq -r '.cover_url // empty' "$INFO")
  [ -n "$COLOR" ]     || COLOR=$(jq -r '.colors.primary // .colors.theme_color // empty' "$INFO")
fi
[ -n "$LOGO_URL" ] || { echo "❌ No logo URL (brand-info.json has none; pass --logo-url)"; exit 1; }
printf '%s' "$COLOR" | grep -qE '^#[0-9a-fA-F]{6}$' || { echo "  ⚠ No usable brand colour — covers will use neutral #1F2937"; COLOR="#1F2937"; }

mkdir -p "$OUTPUT_DIR/originals"
cd "$OUTPUT_DIR"

dl() {  # dl <url> <dest-without-ext> -> prints final path or empty
  local url="$1" dest="$2" tmp; tmp=$(mktemp)
  if curl -sSL --max-time 30 -A "Mozilla/5.0 social-brand-sync" -o "$tmp" "$url" && [ -s "$tmp" ]; then
    local fmt; fmt=$($IDENT -format '%m' "$tmp[0]" 2>/dev/null | tr 'A-Z' 'a-z' || true)
    case "$fmt" in
      png|jpeg|jpg|gif|webp|svg|ico|mvg) ;;
      *) rm -f "$tmp"; echo ""; return ;;
    esac
    [ "$fmt" = "jpeg" ] && fmt=jpg
    mv "$tmp" "$dest.$fmt"; echo "$dest.$fmt"
  else rm -f "$tmp"; echo ""; fi
}

echo "◆ Downloading originals..."
LOGO=$(dl "$LOGO_URL" originals/logo)
if [ -z "$LOGO" ]; then
  FAV=$(jq -r '.favicon_url // empty' "$INFO" 2>/dev/null || true)
  [ -n "$FAV" ] && LOGO=$(dl "$FAV" originals/logo) || true
  [ -n "$LOGO" ] && echo "  ⚠ logo download failed — using favicon (low resolution)"
fi
[ -n "$LOGO" ] || { echo "❌ Could not download a logo from $LOGO_URL"; exit 1; }
echo "  logo:  $LOGO ($($IDENT -format '%wx%h' "$LOGO[0]"))"

# Normalise the logo to a flattened square PNG once; everything derives from it.
# Transparent logos get the brand colour behind them so no platform shows black.
$IM "$LOGO[0]" -background "$COLOR" -alpha remove -alpha off \
  -resize 1024x1024 -gravity center -background "$COLOR" -extent 1024x1024 originals/logo-square.png

COVER=""
if [ -n "$COVER_URL" ]; then
  COVER=$(dl "$COVER_URL" originals/cover) || true
  [ -n "$COVER" ] && echo "  cover: $COVER ($($IDENT -format '%wx%h' "$COVER[0]"))" || echo "  ⚠ cover download failed — covers will be generated"
fi

square() {  # square <platform> <size>
  mkdir -p "$1"
  $IM originals/logo-square.png -resize "${2}x${2}" "$1/profile-pic.png"
}
banner() {  # banner <platform> <file> <WxH> <logo-size>
  mkdir -p "$1"
  if [ -n "$COVER" ]; then
    $IM "$COVER[0]" -resize "$3^" -gravity center -extent "$3" -alpha remove -alpha off "$1/$2"
  else
    # Generated cover: brand colour field, logo centred, kept inside the safe zone.
    $IM -size "$3" "xc:$COLOR" \( "$LOGO[0]" -resize "${4}x${4}" -background none -gravity center \) \
      -gravity center -composite -alpha remove -alpha off "$1/$2"
  fi
}

echo "◆ Generating platform images..."
IFS=',' read -ra PLIST <<< "$PLATFORMS"
for p in "${PLIST[@]}"; do
  case "$p" in
    facebook) square facebook 360;   banner facebook cover.png 851x315 120 ;;
    linkedin) square linkedin 400;   banner linkedin cover.png 1584x396 150 ;;
    twitter)  square twitter 400;    banner twitter header.png 1500x500 200 ;;
    tiktok)   square tiktok 200 ;;
    youtube)  square youtube 800;    banner youtube banner.png 2560x1440 300 ;;
    github)   square github 512 ;;
    *) echo "  ⚠ unknown platform '$p' — skipped" ;;
  esac
done

# Facebook renders the page picture at 170/180px but rejects tiny uploads and
# downsamples large ones; 360 is the documented sweet spot.

echo "◆ Validating..."
EXPECT='{"facebook":{"profile-pic.png":"360x360","cover.png":"851x315"},
"linkedin":{"profile-pic.png":"400x400","cover.png":"1584x396"},
"twitter":{"profile-pic.png":"400x400","header.png":"1500x500"},
"tiktok":{"profile-pic.png":"200x200"},
"youtube":{"profile-pic.png":"800x800","banner.png":"2560x1440"},
"github":{"profile-pic.png":"512x512"}}'
FAIL=0; MANIFEST="[]"
for p in "${PLIST[@]}"; do
  for f in $(jq -r --arg p "$p" '.[$p] // {} | keys[]' <<<"$EXPECT"); do
    want=$(jq -r --arg p "$p" --arg f "$f" '.[$p][$f]' <<<"$EXPECT")
    if [ -f "$p/$f" ]; then
      got=$($IDENT -format '%wx%h' "$p/$f"); bytes=$(stat -c%s "$p/$f" 2>/dev/null || stat -f%z "$p/$f")
      ok=$([ "$got" = "$want" ] && echo true || echo false); [ "$ok" = true ] || FAIL=1
      printf '  %-9s %-16s %-10s %7s bytes  %s\n' "$p" "$f" "$got" "$bytes" "$([ "$ok" = true ] && echo ✓ || echo "✗ want $want")"
    else
      ok=false; got=""; bytes=0; FAIL=1; printf '  %-9s %-16s MISSING\n' "$p" "$f"
    fi
    MANIFEST=$(jq --arg p "$p" --arg f "$f" --arg path "$OUTPUT_DIR/$p/$f" --arg got "$got" --arg want "$want" \
      --argjson bytes "$bytes" --argjson ok "$ok" \
      '. + [{platform:$p, file:$f, path:$path, size:$got, expected:$want, bytes:$bytes, ok:$ok}]' <<<"$MANIFEST")
  done
done
jq -n --arg logo "$OUTPUT_DIR/$LOGO" --arg cover "${COVER:+$OUTPUT_DIR/$COVER}" --arg color "$COLOR" \
  --argjson images "$MANIFEST" --argjson generated_covers "$([ -z "$COVER" ] && echo true || echo false)" \
  '{logo_original:$logo, cover_original:(if $cover=="" then null else $cover end), color:$color, generated_covers:$generated_covers, images:$images}' \
  > images-manifest.json
echo "  manifest: $OUTPUT_DIR/images-manifest.json"
[ "$FAIL" -eq 0 ] && echo "✅ All images ready" || { echo "❌ Some images missing or wrong size"; exit 1; }
