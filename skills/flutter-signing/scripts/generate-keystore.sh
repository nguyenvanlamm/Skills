#!/usr/bin/env bash
# Generate an upload keystore + key.properties for a Flutter Android project, safely.
#
#   bash generate-keystore.sh [--alias upload] [--cn "App Name"] [--keysize 4096]
#                             [--validity 10000] [--project .] [--force]
#
# Run from (or point --project at) the Flutter project root. Writes:
#   android/app/upload-keystore.jks     PKCS12, RSA <keysize>
#   android/key.properties              chmod 600
#   (appends credential patterns to .gitignore if missing)
# Prints the SHA-1 / SHA-256 fingerprints and the values the user must put in a
# password manager. Passwords are generated here and are NEVER passed on the
# command line — keytool reads them from the environment (:env), so they do not
# show up in `ps` or shell history.
#
# Why PKCS12 rather than JKS: JKS is deprecated by the JDK (keytool warns on
# every use) and keeps separate store/key passwords, which is the reason the
# interactive prompt sequence is so easy to get wrong when scripted. PKCS12 uses
# one password for both, which is what Gradle expects from key.properties anyway.
#
# Exit 0 on success. Exit 1 on a pre-existing keystore (use --force after reading
# the warning), missing keytool, or verification failure.
set -euo pipefail

ALIAS="upload"; CN=""; KEYSIZE=4096; VALIDITY=10000; PROJECT="."; FORCE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --alias) ALIAS="$2"; shift 2 ;;
    --cn) CN="$2"; shift 2 ;;
    --keysize) KEYSIZE="$2"; shift 2 ;;
    --validity) VALIDITY="$2"; shift 2 ;;
    --project) PROJECT="$2"; shift 2 ;;
    --force) FORCE=true; shift ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

cd "$PROJECT"
[ -f pubspec.yaml ] || { echo "❌ Not a Flutter project (no pubspec.yaml in $PWD)"; exit 1; }
[ -d android/app ]  || { echo "❌ No android/app/ — was the project created with the android platform?"; exit 1; }
command -v keytool >/dev/null || { echo "❌ keytool not found — install a JDK (OpenJDK 17 for AGP 8.x)"; exit 1; }
[ "$KEYSIZE" -ge 2048 ] || { echo "❌ --keysize must be >= 2048 (Play minimum)"; exit 1; }
# Play requires validity past 22 Oct 2033; 10000 days from today clears it by ~20 years.
[ "$VALIDITY" -ge 3000 ] || { echo "❌ --validity must be >= 3000 days (Play requires validity past 2033-10-22)"; exit 1; }

KS="android/app/upload-keystore.jks"
PROPS="android/key.properties"

if [ -f "$KS" ] || [ -f "$PROPS" ]; then
  if [ "$FORCE" = false ]; then
    echo "❌ $KS and/or $PROPS already exist."
    echo "   If this app has EVER been uploaded to Play, a new key breaks updates until an upload-key reset is approved."
    echo "   Re-run with --force only if you understand that. Existing files will be moved to *.bak.<timestamp>."
    exit 1
  fi
  TS=$(date +%Y%m%d%H%M%S)
  [ -f "$KS" ]    && mv "$KS" "$KS.bak.$TS"    && echo "  moved old keystore → $KS.bak.$TS"
  [ -f "$PROPS" ] && mv "$PROPS" "$PROPS.bak.$TS" && echo "  moved old key.properties → $PROPS.bak.$TS"
fi

# Already-leaked material: a key that is in git history is compromised regardless of what we do now.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  LEAKED=$(git log --all --oneline -- '*.jks' '*.keystore' 'android/key.properties' 2>/dev/null | head -3 || true)
  [ -z "$LEAKED" ] || { echo "  ⚠ A keystore or key.properties appears in git history:"; echo "$LEAKED" | sed 's/^/     /'; echo "     Deleting the file does not undo the exposure if the repo was ever pushed."; }
fi

[ -n "$CN" ] || CN=$(sed -nE 's/^name:[[:space:]]*([A-Za-z0-9_]+).*/\1/p' pubspec.yaml | head -1)
[ -n "$CN" ] || CN="upload"

# 24 random bytes → 32 base64 chars; stripped of characters that break .properties parsing.
gen_pw() {
  if command -v openssl >/dev/null; then openssl rand -base64 24; else head -c 24 /dev/urandom | base64; fi | tr -d '\n=/+' | head -c 30
}
export KS_PASS; KS_PASS=$(gen_pw)

echo "◆ Generating $KS (PKCS12, RSA $KEYSIZE, alias '$ALIAS', valid $VALIDITY days)..."
# :env → keytool reads the variable itself; nothing secret lands in argv.
keytool -genkeypair -v \
  -keystore "$KS" -storetype PKCS12 \
  -storepass:env KS_PASS -keypass:env KS_PASS \
  -alias "$ALIAS" -keyalg RSA -keysize "$KEYSIZE" -validity "$VALIDITY" \
  -dname "CN=$CN" 2>&1 | grep -viE 'password|warning' || true
[ -s "$KS" ] || { echo "❌ keytool did not produce $KS"; exit 1; }

echo "◆ Writing $PROPS (chmod 600)..."
umask 077
cat > "$PROPS" <<EOF
storePassword=$KS_PASS
keyPassword=$KS_PASS
keyAlias=$ALIAS
storeFile=upload-keystore.jks
EOF
chmod 600 "$PROPS"

echo "◆ .gitignore..."
touch .gitignore
for pattern in '*.jks' '*.keystore' 'android/key.properties' 'service-account.json'; do
  grep -qxF "$pattern" .gitignore || { echo "$pattern" >> .gitignore; echo "  + $pattern"; }
done
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git check-ignore -q "$PROPS" "$KS" && echo "  ✓ git check-ignore: both files ignored" || echo "  ⚠ git check-ignore did not match — inspect .gitignore"
fi

echo "◆ Verifying the keystore opens and contains the alias..."
LIST=$(keytool -list -v -keystore "$KS" -storepass:env KS_PASS -alias "$ALIAS" 2>/dev/null) || { echo "❌ keystore verification failed"; exit 1; }
SHA1=$(printf '%s\n' "$LIST" | awk -F': ' '/SHA1:/{print $2; exit}')
SHA256=$(printf '%s\n' "$LIST" | awk -F': ' '/SHA256:/{print $2; exit}')
VALID=$(printf '%s\n' "$LIST" | grep -m1 -oE 'until: .*' | sed 's/until: //')

cat <<EOF

FLUTTER SIGNING — keystore generated

Keystore    $KS  (PKCS12, RSA $KEYSIZE, alias "$ALIAS")
Valid       until $VALID
Config      $PROPS (chmod 600) · storeFile relative to android/app/
Ignored     *.jks, android/key.properties (check-ignore confirmed)

Fingerprints (Firebase / Google Sign-In / Maps):
  SHA-1    $SHA1
  SHA-256  $SHA256

Put this in a password manager NOW — the key exists only on this machine:
  keystore file:   $PWD/$KS  (attach the file)
  storePassword:   (in $PROPS — copy it, do not paste it into chat)
  keyPassword:     same as storePassword (PKCS12)
  keyAlias:        $ALIAS
  applicationId:   $(grep -hoE 'applicationId[[:space:]=]+"[^"]+"' android/app/build.gradle* 2>/dev/null | head -1 | grep -oE '"[^"]+"' | tr -d '"' || echo '<see android/app/build.gradle>')

Next: apply the Gradle block from references/gradle-config.md, then
      (cd android && ./gradlew signingReport) | grep -A6 "Variant: release"
EOF
