"""Shared helpers for flutter-ios-release: pubspec, Info.plist, project.pbxproj.

Standard library only (runs on Linux and on the macOS python3 that ships with Xcode CLT).
The pbxproj helpers are deliberately narrow: they only understand the layout that
`flutter create` generates (one `Runner` app target identified by
`INFOPLIST_FILE = Runner/Info.plist`, one `RunnerTests` target). Anything they cannot
locate is reported, never guessed.
"""
import os
import plistlib
import re
import secrets

# package → (required Info.plist keys, recommended keys). Heuristic: a plugin that is present
# normally needs these keys; the PRD decides the wording. Missing required key = the upload is
# rejected (ITMS-90683) or the app crashes on first use.
PERMISSION_MAP = {
    "image_picker": (["NSPhotoLibraryUsageDescription", "NSCameraUsageDescription"], ["NSMicrophoneUsageDescription"]),
    "camera": (["NSCameraUsageDescription"], ["NSMicrophoneUsageDescription"]),
    "mobile_scanner": (["NSCameraUsageDescription"], []),
    "qr_code_scanner": (["NSCameraUsageDescription"], []),
    "qr_code_scanner_plus": (["NSCameraUsageDescription"], []),
    "geolocator": (["NSLocationWhenInUseUsageDescription"], []),
    "location": (["NSLocationWhenInUseUsageDescription"], []),
    "google_maps_flutter": ([], ["NSLocationWhenInUseUsageDescription"]),
    "local_auth": (["NSFaceIDUsageDescription"], []),
    "flutter_contacts": (["NSContactsUsageDescription"], []),
    "contacts_service": (["NSContactsUsageDescription"], []),
    "speech_to_text": (["NSSpeechRecognitionUsageDescription", "NSMicrophoneUsageDescription"], []),
    "record": (["NSMicrophoneUsageDescription"], []),
    "flutter_sound": (["NSMicrophoneUsageDescription"], []),
    "audio_waveforms": (["NSMicrophoneUsageDescription"], []),
    "photo_manager": (["NSPhotoLibraryUsageDescription"], []),
    "wechat_assets_picker": (["NSPhotoLibraryUsageDescription"], []),
    "gal": (["NSPhotoLibraryAddUsageDescription"], []),
    "image_gallery_saver": (["NSPhotoLibraryAddUsageDescription"], []),
    "image_gallery_saver_plus": (["NSPhotoLibraryAddUsageDescription"], []),
    "saver_gallery": (["NSPhotoLibraryAddUsageDescription"], []),
    "flutter_blue_plus": (["NSBluetoothAlwaysUsageDescription"], []),
    "flutter_reactive_ble": (["NSBluetoothAlwaysUsageDescription"], []),
    "health": (["NSHealthShareUsageDescription", "NSHealthUpdateUsageDescription"], []),
    "app_tracking_transparency": (["NSUserTrackingUsageDescription"], []),
    "device_calendar": (["NSCalendarsFullAccessUsageDescription"], ["NSCalendarsUsageDescription"]),
    "nfc_manager": (["NFCReaderUsageDescription"], []),
}
THIRD_PARTY_LOGIN = ["google_sign_in", "flutter_facebook_auth", "twitter_login", "flutter_login_facebook"]
SECRET_EXT = (".p8", ".p12", ".mobileprovision", ".cer", ".certSigningRequest")
GITIGNORE_LINES = ["*.p8", "*.p12", "*.mobileprovision", "*.cer", "*.certSigningRequest"]
# sha256 of the 1024 px icon `flutter create` ships (Flutter 3.47) — a placeholder icon is rejected in review
DEFAULT_ICON_SHA256 = {"7770183009e914112de7d8ef1d235a6a30c5834424858e0d2f8253f6b8d31926"}

PBX = "ios/Runner.xcodeproj/project.pbxproj"
INFO = "ios/Runner/Info.plist"
PRIVACY = "ios/Runner/PrivacyInfo.xcprivacy"
ICON = "ios/Runner/Assets.xcassets/AppIcon.appiconset/Icon-App-1024x1024@1x.png"
KIT = "ios-release"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def pubspec(project):
    """→ (name, version, set of dependency names). Minimal YAML reading, no PyYAML."""
    text = read(os.path.join(project, "pubspec.yaml"))
    name = (re.search(r"^name:\s*(\S+)", text, re.M) or [None, ""])[1]
    version = (re.search(r"^version:\s*(\S+)", text, re.M) or [None, ""])[1]
    deps, section = set(), None
    for line in text.splitlines():
        if re.match(r"^\S", line):
            section = line.split(":")[0].strip()
            continue
        m = re.match(r"^  ([A-Za-z0-9_]+):", line)
        if m and section == "dependencies":  # dev_dependencies never ship in the IPA
            deps.add(m.group(1))
    return name, version, deps


def load_plist(path):
    with open(path, "rb") as f:
        return plistlib.load(f)


def save_plist(path, data):
    with open(path, "wb") as f:
        plistlib.dump(data, f, sort_keys=False)


# ---- project.pbxproj ------------------------------------------------------------------------
CONF_RE = re.compile(
    r"(\t\t(?P<id>[0-9A-F]{24}) /\* (?P<name>[^*]+) \*/ = \{\n\t\t\tisa = XCBuildConfiguration;\n"
    r"(?:.*?\n)*?\t\t\tbuildSettings = \{\n)(?P<settings>(?:.*?\n)*?)(\t\t\t\};)",
)


def configs(pbx):
    """All XCBuildConfiguration blocks → list of dicts {id, name, start, end, settings, kind}.
    kind: app (Runner target) | tests (RunnerTests) | project (project-level)."""
    out = []
    for m in CONF_RE.finditer(pbx):
        s = m.group("settings")
        if "INFOPLIST_FILE = Runner/Info.plist;" in s:
            kind = "app"
        elif "TEST_HOST" in s or "BUNDLE_LOADER" in s:
            kind = "tests"
        else:
            kind = "project"
        out.append({"id": m.group("id"), "name": m.group("name"), "start": m.start("settings"),
                    "end": m.end("settings"), "settings": s, "kind": kind})
    return out


def setting(settings, key):
    m = re.search(r"^\t\t\t\t%s = (.*);$" % re.escape(key), settings, re.M)
    return m.group(1).strip('"') if m else None


def quote(value):
    return value if re.fullmatch(r"[A-Za-z0-9_./$()-]+", value) else '"%s"' % value


def set_setting(settings, key, value):
    line = "\t\t\t\t%s = %s;\n" % (key, quote(value))
    pat = re.compile(r"^\t\t\t\t%s = .*;\n" % re.escape(key), re.M)
    if pat.search(settings):
        return pat.sub(lambda _: line, settings)
    lines = settings.splitlines(keepends=True)  # keep keys sorted like Xcode does
    for i, existing in enumerate(lines):
        m = re.match(r"^\t\t\t\t([A-Za-z0-9_\"\[\]=*]+) = ", existing)
        if m and m.group(1).strip('"') > key:
            return "".join(lines[:i] + [line] + lines[i:])
    return settings + line


def edit_configs(pbx, kinds, fn):
    """Apply fn(settings) → settings to every config whose kind is in kinds (back to front)."""
    for c in sorted(configs(pbx), key=lambda c: c["start"], reverse=True):
        if c["kind"] in kinds:
            pbx = pbx[:c["start"]] + fn(c["settings"]) + pbx[c["end"]:]
    return pbx


def effective(pbx, key):
    """Runner app value(s) of key: target-level, else project-level. → sorted list of values."""
    confs = configs(pbx)
    vals = {setting(c["settings"], key) for c in confs if c["kind"] == "app"}
    if vals == {None}:
        vals = {setting(c["settings"], key) for c in confs if c["kind"] == "project"}
    return sorted(v for v in vals if v is not None) or [None]


def new_id(pbx):
    while True:
        i = secrets.token_hex(12).upper()
        if i not in pbx:
            return i


def privacy_registered(pbx):
    return "PrivacyInfo.xcprivacy in Resources" in pbx and "path = PrivacyInfo.xcprivacy;" in pbx


def register_privacy(pbx):
    """Add ios/Runner/PrivacyInfo.xcprivacy to the Runner group and the Runner Resources phase.
    → (pbx, error or None)."""
    if privacy_registered(pbx):
        return pbx, None
    group = re.search(r"(\t\t[0-9A-F]{24} /\* Runner \*/ = \{\n\t\t\tisa = PBXGroup;\n\t\t\tchildren = \(\n)", pbx)
    res = re.search(r"(\t\t[0-9A-F]{24} /\* Resources \*/ = \{\n\t\t\tisa = PBXResourcesBuildPhase;\n"
                    r"\t\t\tbuildActionMask = \d+;\n\t\t\tfiles = \(\n)(?=(?:\t\t\t\t.*\n)*?"
                    r"\t\t\t\t[0-9A-F]{24} /\* Assets\.xcassets in Resources \*/)", pbx)
    if not (group and res and "/* End PBXBuildFile section */" in pbx and "/* End PBXFileReference section */" in pbx):
        return pbx, "could not locate the Runner group / Resources phase — add PrivacyInfo.xcprivacy to the Runner target in Xcode"
    ref = new_id(pbx)
    bld = new_id(pbx + ref)
    pbx = pbx.replace("/* End PBXBuildFile section */",
                      "\t\t%s /* PrivacyInfo.xcprivacy in Resources */ = {isa = PBXBuildFile; fileRef = %s /* PrivacyInfo.xcprivacy */; };\n"
                      "/* End PBXBuildFile section */" % (bld, ref), 1)
    pbx = pbx.replace("/* End PBXFileReference section */",
                      "\t\t%s /* PrivacyInfo.xcprivacy */ = {isa = PBXFileReference; lastKnownFileType = text.xml; path = PrivacyInfo.xcprivacy; sourceTree = \"<group>\"; };\n"
                      "/* End PBXFileReference section */" % ref, 1)
    group = re.search(r"(\t\t[0-9A-F]{24} /\* Runner \*/ = \{\n\t\t\tisa = PBXGroup;\n\t\t\tchildren = \(\n)", pbx)
    pbx = pbx[:group.end()] + "\t\t\t\t%s /* PrivacyInfo.xcprivacy */,\n" % ref + pbx[group.end():]
    res = re.search(r"(\t\t[0-9A-F]{24} /\* Resources \*/ = \{\n\t\t\tisa = PBXResourcesBuildPhase;\n"
                    r"\t\t\tbuildActionMask = \d+;\n\t\t\tfiles = \(\n)(?=(?:\t\t\t\t.*\n)*?"
                    r"\t\t\t\t[0-9A-F]{24} /\* Assets\.xcassets in Resources \*/)", pbx)
    pbx = pbx[:res.end()] + "\t\t\t\t%s /* PrivacyInfo.xcprivacy in Resources */,\n" % bld + pbx[res.end():]
    return pbx, None


def android_app_id(project):
    for n in ("build.gradle.kts", "build.gradle"):
        p = os.path.join(project, "android", "app", n)
        if os.path.exists(p):
            m = re.search(r"applicationId\s*=?\s*[\"']([^\"']+)[\"']", read(p))
            if m:
                return m.group(1)
    return None
