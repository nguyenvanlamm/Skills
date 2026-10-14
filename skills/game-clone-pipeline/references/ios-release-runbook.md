# iOS release runbook (stage S8): prepare on Ubuntu, build and upload on a Mac

> **`asc` is deferred (SKILL.md hard rule 12).** Skip every `asc` command below. Write what it
> would send into `docs/APP-STORE-CONNECT.md` and `store/`; the human does those steps in the App
> Store Connect web UI. The `asc` commands stay here for when the rule is lifted.

No CI build. The agent prepares every file on the Linux machine; a human builds and uploads on
a Mac. App Store Connect work that needs no Xcode is done from Ubuntu with `asc`
(`~/.local/bin/asc`, Rork's App Store Connect CLI; `asc <cmd> --help` for flags). Everything
user-facing is English (en-US). Generalized from tile_bloom's `docs/APP-STORE.md`.

## 0. One time per Apple account (human)

1. Apple Developer Program membership; note the **Team ID** (10 characters).
2. App Store Connect → Business: sign the **Paid Apps Agreement**, bank and tax. Without it
   IAP can be neither sold nor tested.
3. App Store Connect → Users and Access → Integrations → **API key** with App Manager (or
   Admin) role; download the `.p8` once. `asc auth login --name main --key-id … --issuer-id …
   --private-key AuthKey_….p8`, then `asc auth doctor`.
4. Sandbox tester account (Users and Access → Sandbox) for IAP tests.

## 1. Per game, on Ubuntu (agent)

1. Run the **`flutter-ios-release`** skill: bundle id, team, device family, deployment target,
   Info.plist usage strings, `ITSAppUsesNonExemptEncryption = false`, privacy manifest,
   icon without alpha. `ios-release/prep-report.json` must exit 0.
   - iPhone-only unless the game is designed for iPad: an iPad target needs an iPad
     screenshot set.
2. Copy the build kit from this skill:
   - `templates/build-ios.sh` → `scripts/build-ios.sh` (`chmod +x`)
   - `templates/ExportOptions.plist` → `ios/ExportOptions.plist`
   `flutter-ios-release` also writes `ios-release/build-ios.sh`, which exports but never uploads;
   keep it as a fallback, the documented path is `scripts/build-ios.sh`.
3. Write `docs/IOS-BUILD-ON-MAC.md` in the game repo from section 2 below (fill the team ID
   placeholder only if the user gives it; never commit keys).
4. Register the bundle id: `asc bundle-ids create --identifier "<bundle id>" --name "<Game>" --platform IOS`.
   Create the app record in the App Store Connect web UI (Apps → +; English (U.S.); the API
   cannot create apps). Note the numeric app ID: `asc apps list --bundle-id "<bundle id>"`.
5. Create IAP products from DESIGN.md: e.g.
   `asc iap setup --app APP_ID --type NON_CONSUMABLE --reference-name "Full game" --product-id "full_game" --price "3.99" --base-territory "United States"`
   (`asc iap create … --type CONSUMABLE` for packs). Product IDs must match the code.
6. Commit with the `commit` skill: "build(ios): add Mac build kit and App Store prep".

## 2. On the Mac (human, the agent writes these steps into docs/IOS-BUILD-ON-MAC.md)

```bash
# once: Xcode (latest), Flutter (same version as pubspec / .metadata), CocoaPods
git clone <repo> && cd <repo>
flutter pub get
# signing, either:
#   a) Xcode → Settings → Accounts: sign in with the Apple ID of the team, or
#   b) export ASC_KEY_PATH=~/keys/AuthKey_XXXX.p8 ASC_KEY_ID=XXXX ASC_ISSUER_ID=…
TEAM_ID=ABCDE12345 scripts/build-ios.sh            # archive + export → build/ios/ipa/*.ipa (check only)
TEAM_ID=ABCDE12345 BUILD_NUMBER=2 scripts/build-ios.sh upload   # archive + upload to App Store Connect
```

- Every upload needs a new build number (`BUILD_NUMBER`, or bump `pubspec.yaml`).
  `asc builds next-build-number --app APP_ID` gives the next free one.
- The first run creates `ios/Podfile` and runs CocoaPods; commit it back if it changed.
- Alternative upload: export the `.ipa` on the Mac, then from any machine
  `asc publish appstore --app APP_ID --ipa build/ios/ipa/<Game>.ipa --version X.Y.Z` (upload,
  attach to the version, no submit).

## 3. TestFlight (human + agent)

1. `asc builds list --app APP_ID` then `asc builds wait …` until the build is VALID (5–30 min).
2. Install from TestFlight; with the Sandbox account: buy every product, cancel one purchase,
   delete and reinstall, **Restore purchases**. Screenshot the purchase sheet for IAP review.
3. Anything wrong → fix on main, commit, rebuild with a new build number.

## 4. Store listing (agent, en-US only)

1. `appstore-assets` skill → `appstore-assets/<version>/` (iPhone 6.9"; iPad 13" only if the
   app targets iPad).
2. `aso-marketing` skill → name (30), subtitle (30), keywords (100), promotional text (170),
   description. No original game or publisher names in any field.
3. Push: `asc metadata …` (description, keywords, support URL, privacy policy URL, marketing
   URL), `asc screenshots plan|apply …`, `asc age-rating …`, `asc categories …`, review notes
   (`asc review …`): how to reach every IAP, "no sign-in required".
4. App Privacy answers must match `templates/privacy.html` as filled in and the shipped SDKs.

## 5. Checks → gate G4 (agent, then human)

1. `appstore-review-checker` skill on the repo and listing (4.1 copycats, 4.3 spam, 3.1.1 IAP
   + restore, 2.3.x metadata, 5.1 privacy).
2. `asc validate --app APP_ID --version X.Y.Z` (add `--check-urls`): fix everything it lists.
3. Present both reports; the human approves **G4** before anything is submitted.

## 6. Release (after G4)

1. `/ship --no-auto`: bumps the version everywhere, changelog, tag `vX.Y.Z`, push (asks before
   each step). No CI runs on the tag.
2. On the Mac: pull, `TEAM_ID=… BUILD_NUMBER=<next> scripts/build-ios.sh upload`;
   `asc builds wait`.
3. Stage from Ubuntu: `asc builds list --app APP_ID` for the BUILD_ID, then
   `asc release stage --app APP_ID --version X.Y.Z --build-id BUILD_ID --metadata-dir ./metadata`
   (creates/updates the version, applies metadata, attaches the build, runs readiness checks,
   stops before submitting; rerun after fixing what it lists).
4. Submit: App Store Connect → the version → select the first IAP under In-App Purchases →
   **Add for Review**. Or, if the Mac exported an `.ipa` instead of uploading, do upload +
   attach + submit in one command:
   `asc publish appstore --app APP_ID --ipa <Game>.ipa --version X.Y.Z --metadata-dir ./metadata --submit --dry-run`,
   then the same with `--submit --confirm`. Check later with `asc submit status`.
5. Record build number, version and submission date in `.clone/status.md`; `commit`.

## Troubleshooting

- `No profiles for '<bundle id>'`: sign in under Xcode → Accounts, or pass the API key
  variables; the key needs App Manager/Admin.
- Upload rejected for a duplicate build number: bump `BUILD_NUMBER`.
- Icon with alpha / missing usage string / encryption question: re-run `flutter-ios-release`'s
  `ios_prep_check.py`.
