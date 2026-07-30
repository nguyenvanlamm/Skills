#!/usr/bin/env bash
# android-game-forge — fetch the two OFL fonts for a palette preset into res/font/.
# Run from the project root:  bash fetch-fonts.sh NEON|SPACE|PAPER|CANDY
#
# These are variable fonts (single file, real weight axis). That is why the project
# targets minSdk 26: FontVariation.Settings needs API 26. Below that Android ignores
# the wght axis and the "bold" score renders at regular weight — the typography the
# whole design system rests on silently disappears.
#
# Exit 0 = both files on disk. Exit 1 = something is missing; the caller must report
# a typography FAIL rather than falling back to FontFamily.Default.
set -uo pipefail

PRESET="${1:-}"
DEST="${2:-app/src/main/res/font}"
BASE="https://raw.githubusercontent.com/google/fonts/main"

case "$PRESET" in
  NEON)  SPECS=("orbitron|ofl/orbitron/Orbitron%5Bwght%5D.ttf|Orbitron|display"
                "inter|ofl/inter/Inter%5Bopsz,wght%5D.ttf|Inter|ui") ;;
  SPACE) SPECS=("space_grotesk|ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf|Space Grotesk|display"
                "inter|ofl/inter/Inter%5Bopsz,wght%5D.ttf|Inter|ui") ;;
  PAPER) SPECS=("fraunces|ofl/fraunces/Fraunces%5BSOFT,WONK,opsz,wght%5D.ttf|Fraunces|display"
                "nunito|ofl/nunito/Nunito%5Bwght%5D.ttf|Nunito|ui") ;;
  CANDY) SPECS=("baloo2|ofl/baloo2/Baloo2%5Bwght%5D.ttf|Baloo 2|display"
                "nunito|ofl/nunito/Nunito%5Bwght%5D.ttf|Nunito|ui") ;;
  *) echo "usage: fetch-fonts.sh NEON|SPACE|PAPER|CANDY [dest]" >&2; exit 2 ;;
esac

mkdir -p "$DEST" || exit 1
rc=0
ATTRIB=""

for spec in "${SPECS[@]}"; do
  IFS='|' read -r name path family role <<< "$spec"
  out="$DEST/$name.ttf"
  if [ -s "$out" ]; then
    echo "  have  $name.ttf ($(du -h "$out" | cut -f1))"
  elif curl -sfL --max-time 60 "$BASE/$path" -o "$out" && [ -s "$out" ]; then
    echo "  got   $name.ttf ($(du -h "$out" | cut -f1))  $family"
  else
    rm -f "$out"
    echo "  MISS  $name.ttf — download failed ($family)" >&2
    rc=1
    continue
  fi
  ATTRIB="$ATTRIB- $family — SIL Open Font License 1.1 — https://fonts.google.com/specimen/${family// /+} — res/font/$name.ttf ($role)\n"
done

# res/font names must be [a-z0-9_] or aapt rejects them.
for f in "$DEST"/*.ttf; do
  [ -e "$f" ] || continue
  b=$(basename "$f")
  echo "$b" | grep -qE '^[a-z][a-z0-9_]*\.ttf$' || { echo "  BAD   $b — res/font names must match [a-z][a-z0-9_]*" >&2; rc=1; }
done

if [ $rc -eq 0 ]; then
  printf "\nFonts (OFL, bundled in res/font/):\n%b" "$ATTRIB" > /tmp/agf-font-attribution.txt
  echo "OK — append /tmp/agf-font-attribution.txt to ATTRIBUTION.md"
else
  echo "FAIL — do NOT fall back to FontFamily.Default; report typography as unverified." >&2
fi
exit $rc
