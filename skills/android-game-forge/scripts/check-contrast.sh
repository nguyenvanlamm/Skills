#!/usr/bin/env bash
# android-game-forge — palette gate. Two checks on the Palette.kt that was actually
# generated, not on the spec:
#   1. every token matches the locked design system character for character
#   2. every required foreground/background pair clears WCAG 4.5:1
#
#   bash check-contrast.sh <path/to/Palette.kt> <NEON|SPACE|PAPER|CANDY>
#
# Reading the generated file is the point: it catches "the model invented a nicer blue"
# and "the model copied the table but wired the wrong preset" alike. Exit 0 = both clean.
#
# Portable awk only — no strtonum/IGNORECASE, so this runs on mawk as well as gawk.
set -uo pipefail

FILE="${1:-}"; PRESET="${2:-}"
[ -f "$FILE" ] || { echo "FATAL: no Palette.kt at '$FILE'"; exit 2; }
[ -n "$PRESET" ] || { echo "usage: check-contrast.sh <Palette.kt> <PRESET>"; exit 2; }

# Pull "token = Color(0xFFRRGGBB)" pairs out of the named preset's block only.
BLOCK=$(awk -v p="$(echo "$PRESET" | tr '[:upper:]' '[:lower:]')" '
  { low = tolower($0) }
  !on && low ~ ("val +" p "[a-z]*palette") { on = 1 }
  on { print }
  on && /^\)/ { exit }
' "$FILE")

[ -n "$BLOCK" ] || { echo "FATAL: preset '$PRESET' not found in $FILE"; exit 2; }

TOKENS=$(echo "$BLOCK" | grep -oE '[A-Za-z]+ *= *Color\(0x[0-9A-Fa-f]{8}\)' \
        | sed -E 's/ *= *Color\(0x[0-9A-Fa-f]{2}/ /; s/\)$//' | tr -d '\r')

get() { echo "$TOKENS" | awk -v k="$(echo "$1" | tr '[:upper:]' '[:lower:]')" \
        'tolower($1)==k { print toupper($2); exit }'; }

# Required pairs: foreground background label
PAIRS="
textPrimary   surface   text-on-panel
textSecondary surface   secondary-on-panel
textTertiary  surface   tertiary-on-panel
primaryInk    surface   primary-as-text
accentInk     surface   accent-as-text
success       surface   success-as-text
warning       surface   warning-as-text
danger        surface   danger-as-text
onBg          bgTop     body-on-gradient-top
onBg          bgBottom  body-on-gradient-bottom
onBgMuted     bgTop     muted-on-gradient-top
onBgMuted     bgBottom  muted-on-gradient-bottom
onPrimary     primary   label-on-primary-fill
onAccent      accent    label-on-accent-fill
"

ratio() { # ratio RRGGBB RRGGBB
  awk -v a="$1" -v b="$2" '
    function hx(s,   i,c,n){ n=0
      for(i=1;i<=length(s);i++){ c=index("0123456789ABCDEF", substr(s,i,1)); n=n*16+(c-1) }
      return n }
    function chan(h,i,  v){ v=hx(substr(h,i,2))/255
      return (v<=0.03928) ? v/12.92 : ((v+0.055)/1.055)^2.4 }
    function lum(h){ return 0.2126*chan(h,1)+0.7152*chan(h,3)+0.0722*chan(h,5) }
    BEGIN{ la=lum(a); lb=lum(b); hi=(la>lb?la:lb); lo=(la>lb?lb:la)
           printf "%.2f", (hi+0.05)/(lo+0.05) }'
}

# ---- 1. exact match against the locked design system -----------------------------
SPEC_NEON="bgTop 0B0F2B bgBottom 1A0B2E surface 1C2145 primary 00E5FF accent FF3DA6
 onPrimary 00606B onAccent 56002F primaryInk 00E5FF accentInk FF3DA6
 textPrimary F2F5FF textSecondary B9C0E0 textTertiary 838BAE onBg F2F5FF onBgMuted B9C0E0
 success 3DD68C warning FFB020 danger FF5C5C"
SPEC_SPACE="bgTop 040A1F bgBottom 0E1B3D surface 15234A primary 6C8CFF accent FFC978
 onPrimary 001C80 onAccent 824E00 primaryInk 6C8CFF accentInk FFC978
 textPrimary EAF0FF textSecondary A9B6DC textTertiary 828DB1 onBg EAF0FF onBgMuted A9B6DC
 success 3DD68C warning FFB020 danger FF5C5C"
SPEC_PAPER="bgTop FBF3E4 bgBottom F3E6D0 surface FFFBF2 primary E9714B accent 2E9E8F
 onPrimary 4F1A0A onAccent 0D2B27 primaryInk CE4519 accentInk 257E72
 textPrimary 2B2118 textSecondary 6B5B4B textTertiary 82715D onBg 2B2118 onBgMuted 6B5B4B
 success 1C8251 warning A06700 danger E60000"
SPEC_CANDY="bgTop 3A24B8 bgBottom 7C29C6 surface FFFFFF primary FF6B9D accent FFD166
 onPrimary 700026 onAccent 7A5600 primaryInk EB004F accentInk 996B00
 textPrimary 2A1B4A textSecondary 6E5F91 textTertiary 7D6BA5 onBg FFFFFF onBgMuted D9C9FF
 success 1C8653 warning A56A00 danger EB0000"

eval "SPEC=\${SPEC_$PRESET:-}"
[ -n "$SPEC" ] || { echo "FATAL: no locked spec for preset '$PRESET'"; exit 2; }

drift=0; want=0
set -- $SPEC
while [ $# -ge 2 ]; do
  tok=$1; hex=$2; shift 2; want=$((want+1))
  got=$(get "$tok")
  if [ -z "$got" ]; then
    printf '    \033[31mABSENT\033[0m %-14s expected #%s\n' "$tok" "$hex"; drift=$((drift+1))
  elif [ "$got" != "$hex" ]; then
    printf '    \033[31mDRIFT \033[0m %-14s expected #%s, found #%s\n' "$tok" "$hex" "$got"; drift=$((drift+1))
  fi
done
echo "  palette $PRESET — $((want-drift))/$want tokens match the locked spec exactly"

# ---- 2. measured contrast ---------------------------------------------------------
fail=0; n=0
while read -r fg bg label; do
  [ -z "${fg:-}" ] && continue
  A=$(get "$fg"); B=$(get "$bg")
  if [ -z "$A" ] || [ -z "$B" ]; then
    printf '    \033[31mMISSING\033[0m %-26s (%s or %s not defined)\n' "$label" "$fg" "$bg"
    fail=$((fail+1)); n=$((n+1)); continue
  fi
  R=$(ratio "$A" "$B"); n=$((n+1))
  if awk -v r="$R" 'BEGIN{ exit !(r>=4.5) }'; then
    printf '    \033[32m%5s\033[0m  %-26s %s on %s\n' "$R" "$label" "#$A" "#$B"
  else
    printf '    \033[31m%5s\033[0m  %-26s %s on %s  <- below 4.5:1\n' "$R" "$label" "#$A" "#$B"
    fail=$((fail+1))
  fi
done <<< "$PAIRS"

echo "  contrast: $((n-fail))/$n pairs clear 4.5:1"
exit $(( (fail + drift) > 0 ? 1 : 0 ))
