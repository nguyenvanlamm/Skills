#!/usr/bin/env python3
"""flutter-ios-release — make a Flutter project's iOS side App Store-ready. Idempotent; builds nothing.

  python3 ios_prep_apply.py --project <flutter-dir>
      [--bundle-id com.acme.app] [--team-id ABCDE12345] [--display-name "Spendly"]
      [--deployment-target 15.0] [--device-family iphone|universal]
      [--encryption-exempt | --uses-non-exempt-encryption]
      [--usage NSCameraUsageDescription="Scan receipts to add expenses."]...
      [--privacy-manifest] [--kit] [--dry-run]

Edits only: ios/Runner/Info.plist, ios/Runner.xcodeproj/project.pbxproj (Runner + RunnerTests
build settings, PrivacyInfo.xcprivacy registration), ios/Runner/PrivacyInfo.xcprivacy,
ios/Podfile (platform line, if the file exists), ios-release/{build-ios.sh,ExportOptions.plist,README.md},
.gitignore (signing-secret patterns). Prints one line per change. Exit 0 ok · 1 something could
not be applied (reason printed) · 2 usage error.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ios_common as c  # noqa: E402

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
PRIVACY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>NSPrivacyTracking</key>
	<false/>
	<key>NSPrivacyTrackingDomains</key>
	<array/>
	<key>NSPrivacyCollectedDataTypes</key>
	<array/>
	<key>NSPrivacyAccessedAPITypes</key>
	<array/>
</dict>
</plist>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", default=".")
    ap.add_argument("--bundle-id")
    ap.add_argument("--team-id")
    ap.add_argument("--display-name")
    ap.add_argument("--deployment-target")
    ap.add_argument("--device-family", choices=["iphone", "universal"])
    enc = ap.add_mutually_exclusive_group()
    enc.add_argument("--encryption-exempt", action="store_true", help="ITSAppUsesNonExemptEncryption = false (HTTPS/OS crypto only)")
    enc.add_argument("--uses-non-exempt-encryption", action="store_true")
    ap.add_argument("--usage", action="append", default=[], metavar="KEY=TEXT")
    ap.add_argument("--privacy-manifest", action="store_true")
    ap.add_argument("--kit", action="store_true", help="write ios-release/ (build-ios.sh, ExportOptions.plist, README.md)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    P = os.path.abspath(a.project)
    pbx_path, info_path = os.path.join(P, c.PBX), os.path.join(P, c.INFO)
    if not os.path.isfile(os.path.join(P, "pubspec.yaml")):
        print("not a Flutter project: %s" % P, file=sys.stderr)
        return 2
    if not (os.path.isfile(pbx_path) and os.path.isfile(info_path)):
        print("no ios/ project — run: flutter create --platforms ios .   (works on Linux)", file=sys.stderr)
        return 1
    if a.bundle_id and (a.bundle_id.startswith("com.example.") or not re.fullmatch(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", a.bundle_id)):
        print("--bundle-id %s is a placeholder or not reverse-DNS" % a.bundle_id, file=sys.stderr)
        return 2
    if a.team_id and not re.fullmatch(r"[A-Z0-9]{10}", a.team_id):
        print("--team-id must be the 10-character Apple team id (A-Z0-9)", file=sys.stderr)
        return 2
    if a.deployment_target and not re.fullmatch(r"\d+\.\d+", a.deployment_target):
        print("--deployment-target like 15.0", file=sys.stderr)
        return 2
    usage = {}
    for u in a.usage:
        k, sep, v = u.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z]+UsageDescription", k) or len(v.strip()) < 12:
            print("--usage needs KEY=TEXT with a *UsageDescription key and a real sentence: %r" % u, file=sys.stderr)
            return 2
        usage[k] = v.strip()

    changes, errors = [], []
    pbx0 = pbx = c.read(pbx_path)
    info = c.load_plist(info_path)
    info0 = dict(info)

    if a.bundle_id:
        pbx = c.edit_configs(pbx, {"app"}, lambda s: c.set_setting(s, "PRODUCT_BUNDLE_IDENTIFIER", a.bundle_id))
        pbx = c.edit_configs(pbx, {"tests"}, lambda s: c.set_setting(s, "PRODUCT_BUNDLE_IDENTIFIER", a.bundle_id + ".RunnerTests"))
    if a.team_id:
        pbx = c.edit_configs(pbx, {"app", "tests"}, lambda s: c.set_setting(s, "DEVELOPMENT_TEAM", a.team_id))
    if a.device_family:
        fam = "1" if a.device_family == "iphone" else "1,2"
        pbx = c.edit_configs(pbx, {"app"}, lambda s: c.set_setting(s, "TARGETED_DEVICE_FAMILY", fam))
        if a.device_family == "iphone":
            info.pop("UISupportedInterfaceOrientations~ipad", None)
    if a.deployment_target:
        pbx = re.sub(r"(\t+IPHONEOS_DEPLOYMENT_TARGET = )[\d.]+;", r"\g<1>%s;" % a.deployment_target, pbx)
        podfile = os.path.join(P, "ios", "Podfile")
        if os.path.isfile(podfile):
            pf = c.read(podfile)
            pf2 = re.sub(r"^#?\s*platform :ios, '[\d.]+'", "platform :ios, '%s'" % a.deployment_target, pf, count=1, flags=re.M)
            if pf2 != pf:
                changes.append("ios/Podfile: platform :ios, '%s'" % a.deployment_target)
                if not a.dry_run:
                    c.write(podfile, pf2)
    if a.privacy_manifest:
        priv = os.path.join(P, c.PRIVACY)
        if not os.path.isfile(priv):
            changes.append("%s: created (no tracking, no collected data — edit if the app collects any)" % c.PRIVACY)
            if not a.dry_run:
                c.write(priv, PRIVACY_XML)
        pbx, err = c.register_privacy(pbx)
        if err:
            errors.append(err)

    if a.display_name:
        info["CFBundleDisplayName"] = a.display_name
    if a.encryption_exempt:
        info["ITSAppUsesNonExemptEncryption"] = False
    if a.uses_non_exempt_encryption:
        info["ITSAppUsesNonExemptEncryption"] = True
    info.update(usage)

    if pbx != pbx0:
        changes.append("%s: build settings / resources updated" % c.PBX)
        if not a.dry_run:
            c.write(pbx_path, pbx)
    for k in sorted(set(info) | set(info0)):
        if info.get(k) != info0.get(k):
            changes.append("%s: %s = %r" % (c.INFO, k, info.get(k, "<removed>")))
    if info != info0 and not a.dry_run:
        c.save_plist(info_path, info)

    gi_path = os.path.join(P, ".gitignore")
    gi = c.read(gi_path) if os.path.isfile(gi_path) else ""
    add = [l for l in c.GITIGNORE_LINES if l not in gi]
    if add:
        changes.append(".gitignore: + %s" % " ".join(add))
        if not a.dry_run:
            c.write(gi_path, gi.rstrip("\n") + "\n\n# iOS signing secrets (flutter-ios-release)\n" + "\n".join(add) + "\n")

    if a.kit:
        kit = os.path.join(P, c.KIT)
        teams = sorted({c.setting(x["settings"], "DEVELOPMENT_TEAM") for x in c.configs(pbx) if x["kind"] == "app"} - {None})
        team = a.team_id or (teams[0] if len(teams) == 1 else "")
        bid = a.bundle_id or (sorted({c.setting(x["settings"], "PRODUCT_BUNDLE_IDENTIFIER") for x in c.configs(pbx) if x["kind"] == "app"} - {None}) or [""])[0]
        eo = {"method": "app-store-connect", "destination": "export", "signingStyle": "automatic",
              "uploadSymbols": True, "manageAppVersionAndBuildNumber": False}
        if team:
            eo["teamID"] = team
        name, version, _ = c.pubspec(P)
        subs = {"{{BUNDLE_ID}}": bid, "{{TEAM_ID}}": team or "(not set — pass IOS_TEAM_ID)", "{{APP}}": a.display_name or info.get("CFBundleDisplayName") or name,
                "{{VERSION}}": version}
        for fname in ("build-ios.sh", "README.md"):
            text = c.read(os.path.join(TEMPLATES, fname))
            for k, v in subs.items():
                text = text.replace(k, v)
            dst = os.path.join(kit, fname)
            if not os.path.isfile(dst) or c.read(dst) != text:
                changes.append("%s/%s: written" % (c.KIT, fname))
                if not a.dry_run:
                    c.write(dst, text)
                    if fname.endswith(".sh"):
                        os.chmod(dst, 0o755)
        eo_path = os.path.join(kit, "ExportOptions.plist")
        if not os.path.isfile(eo_path) or c.load_plist(eo_path) != eo:
            changes.append("%s/ExportOptions.plist: method=app-store-connect destination=export%s" % (c.KIT, " teamID=" + team if team else ""))
            if not a.dry_run:
                os.makedirs(kit, exist_ok=True)
                c.save_plist(eo_path, eo)

    for ch in changes:
        print(("would change: " if a.dry_run else "changed: ") + ch)
    if not changes:
        print("nothing to change")
    for e in errors:
        print("ERROR: " + e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
