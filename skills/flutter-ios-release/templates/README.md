# {{APP}} — iOS release kit

Prepared by `flutter-ios-release`. Everything the iOS build needs is already in the repo; the only
things this machine could not do are the ones that need macOS and your Apple account.

| | |
|---|---|
| Bundle id | `{{BUNDLE_ID}}` |
| Team id | `{{TEAM_ID}}` |
| Version | `{{VERSION}}` (from `pubspec.yaml` — bump `+build` before every upload) |
| Export | `ExportOptions.plist` — `app-store-connect`, `destination: export` (builds the IPA, never uploads) |

## One-time setup (on the Mac / in your Apple account)

1. **Apple Developer Program** membership for the team above (developer.apple.com → Membership shows the team id).
2. **Xcode 26 or newer** from the App Store, opened once (installs components), plus Flutter.
3. **App Store Connect → Apps → +** — create the app record with bundle id `{{BUNDLE_ID}}`
   (automatic signing registers the App ID on the first build if it does not exist yet).
4. **Authentication for signing**, one of:
   - Xcode → Settings → Accounts → sign in with an Apple ID that is Admin/App Manager on the team, or
   - an App Store Connect API key (Users and Access → Integrations → Keys, role *App Manager*):
     keep `AuthKey_XXXXXXXXXX.p8` **outside the repo** and export
     `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_KEY_PATH=/abs/path/AuthKey_XXXXXXXXXX.p8`.

## Build

```bash
bash ios-release/build-ios.sh            # --team-id ABCDE12345 if the team id above is not set
```

It checks Xcode ≥ 26, runs `flutter test`, archives with automatic signing, exports the IPA to
`build/ios/ipa/`, and verifies it: bundle id, version = pubspec, iOS 26+ SDK, Apple Distribution
signature, embedded profile, privacy manifest bundled. Result: `ios-release/build-verify.json`.

## Upload (only when you decide to)

- Transporter (Mac App Store) → drag the `.ipa` → Deliver, or
- `xcrun altool --upload-app -t ios -f build/ios/ipa/<name>.ipa --apiKey $ASC_KEY_ID --apiIssuer $ASC_ISSUER_ID`
  (altool looks for the key in `~/.appstoreconnect/private_keys/`).

Before submitting for review, App Store Connect still needs: screenshots (6.9" iPhone; iPad too if
the app is universal), description, keywords, support + privacy-policy URLs, the App Privacy
questionnaire (must match `ios/Runner/PrivacyInfo.xcprivacy` and the SDKs you use), age rating, and
review notes / a demo account if the app has login.

Never commit `.p8`, `.p12`, `.mobileprovision` or `.cer` files — `.gitignore` already blocks them.
