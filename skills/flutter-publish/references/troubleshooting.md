# Upload errors and rejections

## Upload-time errors

Play states these at upload. Every one of them means: fix, bump the build number in `pubspec.yaml`, rebuild, re-upload. **A version code that Play has seen is burned even if the release was discarded** — never try to reuse it.

| Message | Cause | Fix |
|---------|-------|-----|
| "Version code N has already been used" | Reused build number | Bump `version: x.y.z+N` in `pubspec.yaml` |
| "Upload a new version with a higher version code" | Build number lower than a live release | Bump above the highest ever uploaded, not above the current one |
| "You uploaded an APK/bundle that is not signed" | No signing config | Check `android/key.properties`; rerun `flutter-signing` |
| "You uploaded an APK signed with a certificate that's not the correct one" | Wrong keystore | Use the original upload key. If lost: Play Console → Setup → App signing → request an upload key reset |
| "You uploaded a debuggable APK" | `android:debuggable=true` | Build with `--release` |
| "Your app currently targets API level N" | targetSdk below the current floor | Raise `targetSdk`, rebuild — see `preflight.md` Gate 3 |
| "This bundle contains native code and doesn't support 16 KB" | Misaligned `.so` | See `preflight.md` Gate 4 |
| "The package name is already in use" | Someone else owns the ID, or the user's other account does | The applicationId must change — it cannot be reclaimed |
| "Your app bundle contains a x86 native library but no arm64" | Missing ABI | Build a normal AAB; do not restrict `target-platform` for Play |
| Upload just hangs or 500s | Play-side | Retry in an hour; use Console upload if the API keeps failing |

## Review rejections

The rejection email names a policy section. Read that section before acting — the fix is usually specific and small.

| Rejection | Common actual cause | Fix |
|-----------|--------------------|-----|
| App access / login | Reviewer could not get past a login | Add working `test_credentials` + exact steps in App content → App access. Verify the account still works. |
| Data safety inaccurate | Declaration contradicts the privacy policy or observed SDK behavior | Reconcile all three: the app's real behaviour, `data-safety.csv`, and the privacy policy |
| Privacy policy | URL 404s, is not HTTPS, or does not mention the data actually collected | Host it publicly; name every data type the app collects |
| Broken functionality | Crash on the reviewer's device, or a dead-end screen | Read the pre-launch report — it usually reproduces it |
| Deceptive/misleading listing | Screenshots or description promise features that are not there | Make the listing match the app |
| Impersonation / IP | Name, icon, or content resembles another brand | Rebrand; this one is not negotiable |
| Permissions | Sensitive permission with no declared, in-app justification | Remove the permission, or file the Permissions Declaration Form |
| Ads policy | Interstitials that block navigation, ads before content | Fix ad placement |

Process:

1. Fix the specific thing named. Do not ship a broad rewrite in response — it adds new review surface.
2. Bump the version code, rebuild, upload, resubmit.
3. If the rejection is wrong, use the appeal link in the email. Appeals want evidence: screenshots, the relevant code, the policy text. Appeals are slower than fixing.
4. Repeated violations escalate to account termination. Treat the second rejection on the same issue as serious.

## Account-level problems

| Situation | Reality |
|-----------|---------|
| App stuck "In review" > 7 days | Normal for first submissions; use the Play Console help contact form after 7 days |
| "Production access required" | The 12-tester closed test has not been completed — see `testing-track.md` |
| Account under review at signup | Identity/D-U-N-S verification; nothing to do but wait |
| App removed after being live | Check the Policy status page in Console for the specific violation; there is a fixed appeal window |

Do not tell the user a timeline Google has not committed to. Review durations are typical values, not guarantees.
