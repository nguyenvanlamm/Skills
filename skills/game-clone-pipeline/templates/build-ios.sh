#!/usr/bin/env bash
# Archive the game for the App Store (macOS + Xcode only). Copy to scripts/build-ios.sh.
#
#   TEAM_ID=ABCDE12345 scripts/build-ios.sh            # → build/ios/ipa/*.ipa
#   TEAM_ID=ABCDE12345 scripts/build-ios.sh upload     # archive and upload to App Store Connect
#
# Signing is automatic. Locally, Xcode uses the Apple ID signed in under Settings → Accounts.
# On CI, set ASC_KEY_PATH / ASC_KEY_ID / ASC_ISSUER_ID (an App Store Connect API key with the
# Admin or App Manager role) and Xcode fetches certificates and profiles with it.
# BUILD_NUMBER overrides the build number in pubspec.yaml (each upload needs a new one).
set -euo pipefail
: "${TEAM_ID:?set TEAM_ID to your Apple Developer team ID}"
destination="${1:-export}"
[[ "$destination" == export || "$destination" == upload ]] || { echo "usage: $0 [export|upload]" >&2; exit 64; }

cd "$(dirname "$0")/.."

flutter pub get
flutter analyze
flutter test
flutter build ios --release --config-only ${BUILD_NUMBER:+--build-number "$BUILD_NUMBER"}

auth=()
if [[ -n "${ASC_KEY_PATH:-}" ]]; then
  : "${ASC_KEY_ID:?set ASC_KEY_ID with ASC_KEY_PATH}" "${ASC_ISSUER_ID:?set ASC_ISSUER_ID with ASC_KEY_PATH}"
  auth=(-authenticationKeyPath "$ASC_KEY_PATH" -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID")
fi

archive=build/ios/Runner.xcarchive
xcodebuild -workspace ios/Runner.xcworkspace -scheme Runner -configuration Release \
  -destination 'generic/platform=iOS' -archivePath "$archive" \
  DEVELOPMENT_TEAM="$TEAM_ID" CODE_SIGN_STYLE=Automatic \
  -allowProvisioningUpdates ${auth[@]+"${auth[@]}"} archive

options=$(mktemp -t ExportOptions.XXXXXX)
sed -e "s/__TEAM_ID__/$TEAM_ID/" -e "s/__DESTINATION__/$destination/" ios/ExportOptions.plist > "$options"
xcodebuild -exportArchive -archivePath "$archive" -exportOptionsPlist "$options" -exportPath build/ios/ipa \
  -allowProvisioningUpdates ${auth[@]+"${auth[@]}"}
rm -f "$options"

if [[ "$destination" == export ]]; then
  ls -1 build/ios/ipa/*.ipa
else
  echo "Uploaded. The build shows up in App Store Connect → TestFlight after processing."
fi
