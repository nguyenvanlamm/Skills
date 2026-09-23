#!/usr/bin/env python3
"""flutter-ios-release — static App Store readiness check. Runs on Linux or macOS; builds nothing.

  python3 ios_prep_check.py --project <flutter-dir> [--expect-bundle-id <id>] [--json] [--out <file>]

Levels per check: OK | WARN | BLOCK | INFO.
  BLOCK = App Store Connect would reject the upload, review would reject the build, or the Mac
          build cannot start (missing usage string, alpha in the 1024 icon, placeholder bundle id,
          missing kit files, signing secrets tracked by git …).
  WARN  = works, but costs a round-trip later (no team id yet, placeholder icon, no privacy manifest …).
Exit 0 = no BLOCK · 1 = at least one BLOCK · 2 = usage error / not a Flutter project.
A Linux pass means "ready to build on a Mac", never "an IPA exists" — only ios-release/build-ios.sh
on macOS can say that.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ios_common as c  # noqa: E402

PLACEHOLDER = re.compile(r"(?i)(todo|tbd|lorem|placeholder|\$\(|^\s*$|usage description)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", default=".")
    ap.add_argument("--expect-bundle-id")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    P = os.path.abspath(a.project)
    if not os.path.isfile(os.path.join(P, "pubspec.yaml")):
        print("not a Flutter project: %s" % P, file=sys.stderr)
        return 2
    rows = []

    def row(cid, level, detail):
        rows.append({"check": cid, "level": level, "detail": detail})

    name, version, deps = c.pubspec(P)
    pbx_path, info_path = os.path.join(P, c.PBX), os.path.join(P, c.INFO)
    if not (os.path.isfile(pbx_path) and os.path.isfile(info_path)):
        row("ios_platform", "BLOCK", "no ios/ Xcode project — run `flutter create --platforms ios .` (works on Linux)")
        return finish(P, rows, a)
    row("ios_platform", "OK", "ios/Runner.xcodeproj + Info.plist present")
    pbx, info = c.read(pbx_path), c.load_plist(info_path)
    apps = [x for x in c.configs(pbx) if x["kind"] == "app"]
    if not apps:
        row("pbxproj", "BLOCK", "no Runner build configuration (INFOPLIST_FILE = Runner/Info.plist) found")
        return finish(P, rows, a)

    # bundle id
    bids = sorted({c.setting(x["settings"], "PRODUCT_BUNDLE_IDENTIFIER") for x in apps} - {None})
    bid = bids[0] if len(bids) == 1 else None
    if len(bids) != 1:
        row("bundle_id", "BLOCK", "Runner configs disagree or lack PRODUCT_BUNDLE_IDENTIFIER: %s" % bids)
    elif bid.startswith("com.example.") or not re.fullmatch(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", bid):
        row("bundle_id", "BLOCK", "%s is a placeholder or not reverse-DNS — set it from the org DECISION" % bid)
    elif a.expect_bundle_id and bid != a.expect_bundle_id:
        row("bundle_id", "BLOCK", "%s ≠ expected %s" % (bid, a.expect_bundle_id))
    else:
        aid = c.android_app_id(P)
        row("bundle_id", "OK" if aid in (None, bid) else "WARN",
            bid + ("" if aid in (None, bid) else " (Android applicationId is %s — intended?)" % aid))

    # team / signing
    teams = sorted({c.setting(x["settings"], "DEVELOPMENT_TEAM") for x in apps})
    if teams == [None] or teams == [""]:
        row("team_id", "WARN", "no DEVELOPMENT_TEAM — pass IOS_TEAM_ID to build-ios.sh on the Mac")
    elif len(teams) == 1 and re.fullmatch(r"[A-Z0-9]{10}", teams[0] or ""):
        row("team_id", "OK", teams[0])
    else:
        row("team_id", "BLOCK", "DEVELOPMENT_TEAM inconsistent or malformed (10 chars A-Z0-9): %s" % teams)
    styles = sorted({c.setting(x["settings"], "CODE_SIGN_STYLE") or "Automatic" for x in apps})
    row("signing_style", "OK" if styles == ["Automatic"] else "WARN",
        "CODE_SIGN_STYLE %s — build-ios.sh expects Automatic (-allowProvisioningUpdates)" % styles)

    # deployment target
    dts = c.effective(pbx, "IPHONEOS_DEPLOYMENT_TARGET")
    podfile = os.path.join(P, "ios", "Podfile")
    pod_dt = None
    if os.path.isfile(podfile):
        m = re.search(r"^\s*platform :ios, '([\d.]+)'", c.read(podfile), re.M)
        pod_dt = m.group(1) if m else None
    if len(dts) != 1 or dts[0] is None:
        row("deployment_target", "BLOCK", "IPHONEOS_DEPLOYMENT_TARGET missing or inconsistent: %s" % dts)
    elif float(dts[0].split(".")[0]) < 13:
        row("deployment_target", "BLOCK", "%s < 13.0 (Flutter minimum)" % dts[0])
    elif pod_dt and pod_dt != dts[0]:
        row("deployment_target", "WARN", "project %s, Podfile %s — align them" % (dts[0], pod_dt))
    else:
        row("deployment_target", "OK", dts[0])

    # device family / iPad orientations
    fam = c.effective(pbx, "TARGETED_DEVICE_FAMILY")[0] or "1"
    if "2" in fam.split(","):
        ipad = info.get("UISupportedInterfaceOrientations~ipad", [])
        if len(ipad) < 4 and not info.get("UIRequiresFullScreen"):
            row("device_family", "BLOCK", "universal app without all 4 iPad orientations or UIRequiresFullScreen (ITMS-90474)")
        else:
            row("device_family", "WARN", "universal (iPhone + iPad) — App Store Connect then requires iPad screenshots; "
                "phone-only apps set TARGETED_DEVICE_FAMILY = 1 (apply --device-family iphone)")
    else:
        row("device_family", "OK", "iPhone only (TARGETED_DEVICE_FAMILY = %s)" % fam)

    # Info.plist basics
    dn = info.get("CFBundleDisplayName") or info.get("CFBundleName")
    row("display_name", "OK" if dn else "BLOCK", dn or "CFBundleDisplayName missing")
    if not re.fullmatch(r"\d+\.\d+\.\d+\+\d+", version or ""):
        row("version", "BLOCK", "pubspec version '%s' — need x.y.z+build (build number must grow every upload)" % version)
    elif info.get("CFBundleVersion") != "$(FLUTTER_BUILD_NUMBER)" or info.get("CFBundleShortVersionString") != "$(FLUTTER_BUILD_NAME)":
        row("version", "WARN", "Info.plist does not use $(FLUTTER_BUILD_NAME)/$(FLUTTER_BUILD_NUMBER) — pubspec version will not reach the IPA")
    else:
        row("version", "OK", version)
    if "ITSAppUsesNonExemptEncryption" in info:
        row("encryption", "OK", "ITSAppUsesNonExemptEncryption = %s" % info["ITSAppUsesNonExemptEncryption"])
    else:
        row("encryption", "WARN", "ITSAppUsesNonExemptEncryption not set — App Store Connect asks export compliance on every build")
    row("launch_screen", "OK" if info.get("UILaunchStoryboardName") else "BLOCK",
        info.get("UILaunchStoryboardName") or "UILaunchStoryboardName missing")

    # permissions
    needed, recommended = {}, {}
    for d in sorted(deps):
        req, rec = c.PERMISSION_MAP.get(d, ([], []))
        for k in req:
            needed.setdefault(k, []).append(d)
        for k in rec:
            recommended.setdefault(k, []).append(d)
    bad = []
    for k, why in sorted(needed.items()):
        v = info.get(k)
        if not isinstance(v, str) or PLACEHOLDER.search(v) or len(v.strip()) < 12:
            bad.append("%s (for %s)%s" % (k, ",".join(why), "" if v is None else " = %r" % v))
    if bad:
        row("usage_strings", "BLOCK", "missing/placeholder: " + "; ".join(bad))
    else:
        row("usage_strings", "OK", ", ".join(sorted(needed)) or "no permission plugin in dependencies")
    miss_rec = sorted(k for k in recommended if k not in info and k not in needed)
    if miss_rec:
        row("usage_strings_recommended", "WARN", "consider %s (%s)" % (
            ", ".join(miss_rec), "; ".join("%s←%s" % (k, ",".join(recommended[k])) for k in miss_rec)))
    unused = sorted(k for k in info if k.endswith("UsageDescription") and k not in needed and k not in recommended)
    if unused:
        row("usage_strings_unused", "WARN", "declared without a known plugin — keep only if a feature uses it: %s" % ", ".join(unused))
    if "permission_handler" in deps:
        row("permission_handler", "INFO", "permission_handler present — every permission it requests needs its key (and the Podfile/SPM macro) — confirm by hand")

    # privacy manifest
    priv = os.path.isfile(os.path.join(P, c.PRIVACY))
    if priv and c.privacy_registered(pbx):
        row("privacy_manifest", "OK", "PrivacyInfo.xcprivacy present and in Runner Resources")
    elif priv:
        row("privacy_manifest", "BLOCK", "PrivacyInfo.xcprivacy exists but is not in the Xcode project — it will not be bundled")
    else:
        row("privacy_manifest", "WARN", "no app-level PrivacyInfo.xcprivacy (apply --privacy-manifest)")

    # icon
    icon = os.path.join(P, c.ICON)
    if not os.path.isfile(icon):
        row("app_icon", "BLOCK", "no 1024x1024 App Store icon in AppIcon.appiconset")
    else:
        raw = open(icon, "rb").read()
        w, h = int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
        ctype = raw[25] if raw[:8] == b"\x89PNG\r\n\x1a\n" else None
        if ctype is None or (w, h) != (1024, 1024):
            row("app_icon", "BLOCK", "1024 icon is not a 1024x1024 PNG (%sx%s)" % (w, h))
        elif ctype in (4, 6) or b"tRNS" in raw[:4096]:
            row("app_icon", "BLOCK", "1024 icon has an alpha channel (ITMS-90717) — flatten it (flutter_launcher_icons remove_alpha_ios: true)")
        elif hashlib.sha256(raw).hexdigest() in c.DEFAULT_ICON_SHA256:
            row("app_icon", "WARN", "still the default Flutter icon — review rejects placeholder icons")
        else:
            row("app_icon", "OK", "1024x1024, no alpha")

    # guideline 4.8
    tp = sorted(d for d in deps if d in c.THIRD_PARTY_LOGIN)
    if tp and "sign_in_with_apple" not in deps:
        row("sign_in_with_apple", "WARN", "third-party login (%s) without sign_in_with_apple — Guideline 4.8 usually requires it" % ", ".join(tp))

    # secrets
    tracked = []
    try:
        out = subprocess.run(["git", "-C", P, "ls-files"], capture_output=True, text=True, check=True).stdout
        tracked = [f for f in out.splitlines() if f.endswith(c.SECRET_EXT) or os.path.basename(f).startswith("AuthKey_")]
    except (OSError, subprocess.CalledProcessError):
        pass
    gi = c.read(os.path.join(P, ".gitignore")) if os.path.isfile(os.path.join(P, ".gitignore")) else ""
    if tracked:
        row("signing_secrets", "BLOCK", "tracked by git: %s — remove and rotate" % ", ".join(tracked))
    elif not all(l in gi for l in c.GITIGNORE_LINES):
        row("signing_secrets", "WARN", ".gitignore lacks %s" % ", ".join(l for l in c.GITIGNORE_LINES if l not in gi))
    else:
        row("signing_secrets", "OK", "no .p8/.p12/.mobileprovision tracked; patterns ignored")

    # kit
    kit = os.path.join(P, c.KIT)
    missing = [f for f in ("build-ios.sh", "ExportOptions.plist", "README.md") if not os.path.isfile(os.path.join(kit, f))]
    if missing:
        row("release_kit", "BLOCK", "ios-release/ missing %s (apply --kit)" % ", ".join(missing))
    else:
        eo = c.load_plist(os.path.join(kit, "ExportOptions.plist"))
        t = eo.get("teamID")
        if eo.get("method") not in ("app-store-connect", "app-store"):
            row("release_kit", "BLOCK", "ExportOptions method=%s — must be app-store-connect" % eo.get("method"))
        elif t and len(teams) == 1 and teams[0] and t != teams[0]:
            row("release_kit", "BLOCK", "ExportOptions teamID %s ≠ DEVELOPMENT_TEAM %s" % (t, teams[0]))
        else:
            row("release_kit", "OK", "build-ios.sh, ExportOptions.plist (%s), README.md" % eo.get("method"))
    row("toolchain", "INFO", "build on macOS with Xcode 26+ (iOS 26 SDK — App Store Connect minimum since 2026-04-28)")
    return finish(P, rows, a)


def finish(P, rows, a):
    levels = [r["level"] for r in rows]
    overall = "BLOCK" if "BLOCK" in levels else "WARN" if "WARN" in levels else "OK"
    rep = {"project": P, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "overall": overall, "checks": rows}
    text = json.dumps(rep, indent=2, ensure_ascii=False)
    if a.out:
        c.write(a.out, text + "\n")
    if a.json:
        print(text)
    else:
        icon = {"OK": "✅", "WARN": "⚠️", "BLOCK": "❌", "INFO": "ℹ️"}
        for r in rows:
            print("%-26s %s %-5s %s" % (r["check"], icon[r["level"]], r["level"], r["detail"]))
        print("overall: %s" % overall)
    return 1 if overall == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main())
