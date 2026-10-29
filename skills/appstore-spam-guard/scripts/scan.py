#!/usr/bin/env python3
"""App Store Guideline 4.3 (spam) / 4.1 (copycat) preflight — the mechanical checks.

    python3 scan.py --project . [--mode design|build|submit] [--groups a,b]
        [--docs FILE ...] [--listing PATH ...] [--portfolio DIR]
        [--url URL ...] [--name NAME] [--old-name NAME ...]
        [--team ID] [--account-holder NAME] [--ledger FILE]
        [--countries us,gb,jp,vn] [--offline] [--out FILE]

Modes pick the groups: design → design; build → signature, assets, icon,
market; submit → all nine (signature, assets, icon, metadata, market,
portfolio, footprint, ownership, account). --groups overrides the mode.
market compares with the live App Store charts (scripts/market.py; cached a
week, so the first run is online and takes a few minutes).

Prints {"tool", "version", "mode", "project", "overall", "checks": [{id, group,
verdict, summary, evidence, fix}]} to stdout (or --out) and one line per check
to stderr. Verdicts: PASS · WARN · FAIL · SKIP; overall is FAIL if any check
fails, else WARN if any warns, else PASS. Exit 0 always — the report decides;
exit 2 on a usage error.

Stdlib only. Pillow, when installed, adds the icon comparison; without it the
icon check is WARN, never PASS. Judgement checks (fresh-eyes comparison, the
first 30 seconds, the icon's subject) are in references/checks.md, not here.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import itertools
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFS = HERE.parent / "references"
sys.path.insert(0, str(HERE))
import ledger  # noqa: E402  (sibling modules, path set above)
import market  # noqa: E402
from market import dhash  # noqa: E402

VERSION = "1.3.0"

GROUPS_BY_MODE = {
    "design": ["design"],
    "build": ["signature", "assets", "icon", "market"],
    "submit": ["signature", "assets", "icon", "metadata", "market", "portfolio",
               "footprint", "ownership", "account"],
}
ALL_GROUPS = GROUPS_BY_MODE["submit"] + ["design", "binary"]

SKIP_DIRS = {"build", "node_modules", "Pods", "DerivedData", "ephemeral",
             "__pycache__", "dist", "coverage"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
AUDIO_EXTS = {".ogg", ".mp3", ".wav", ".m4a", ".caf", ".aac", ".flac"}
FONT_EXTS = {".ttf", ".otf", ".woff", ".woff2"}
TEXT_LICENSE = re.compile(r"(licen[cs]e|ofl|readme|copying|notice|credits?)", re.I)
AUDIO_WORDS = {"audio", "sfx", "sound", "sounds", "music", "ogg", "mp3", "wav"}
FONT_WORDS = {"font", "fonts", "ttf", "otf", "woff", "woff2"}

CODE_ROOTS = ["lib", "src", "Sources", "ios/Runner", "assets"]
CODE_EXTS = {".dart", ".swift", ".kt", ".ts", ".js", ".arb", ".strings",
             ".xcstrings", ".json", ".yaml", ".yml", ".csv"}
LISTING_DIRS = ["store", "docs/store", "store-metadata", "metadata",
                "fastlane/metadata", "ios/fastlane/metadata"]
LISTING_KEYS = {
    "name": "name", "title": "name", "app_name": "name", "appname": "name",
    "subtitle": "subtitle", "keywords": "keywords", "description": "description",
    "promotionaltext": "promotional", "promotional_text": "promotional",
    "whatsnew": "whatsnew", "whats_new": "whatsnew", "releasenotes": "whatsnew",
    "release_notes": "whatsnew", "shortdescription": "subtitle",
    "short_description": "subtitle", "reviewnotes": "reviewnotes",
    "review_notes": "reviewnotes",
}
HEADLINE_FIELDS = {"name", "subtitle", "keywords", "promotional"}
URL_HINT = re.compile(r"privacy|support|marketing|website|landing|homepage", re.I)
URL_SKIP_HOSTS = ("apple.com", "github.com", "githubusercontent.com", "flutter.dev",
                  "pub.dev", "google.com", "googleapis.com", "w3.org", "example.com",
                  "kenney.nl", "game-icons.net", "conventionalcommits.org")
# Folders that hold a game's art when the pubspec does not say (it adds its own).
ART_DIRS = ("assets", "images", "img", "graphics", "art", "sprites")

# What the emoji font draws: pictographs, and the symbols shown as emoji on their own (⭐)
# or with VS16 (❤️). Card suits, chess men, arrows and mahjong tiles stay type.
EMOJI_BMP = "⌚⌛⏩⏪⏫⏬⏰⏳◽◾☔☕♈♉♊♋♌♍♎♏♐♑♒♓♿⚓⚡⚪⚫⚽⚾⛄⛅⛎⛔⛪⛲⛳⛵⛺⛽✅✊✋✨❌❎❓❔❕❗➕➖➗➰➿⬛⬜⭐⭕"
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001F3FA\U0001F400-\U0001F64F\U0001F680-\U0001F6FF\U0001F7E0-\U0001F7EB"
    "\U0001F90C-\U0001F9FF\U0001FA70-\U0001FAFF\U0001F004\U0001F0CF" + EMOJI_BMP + "]"
    "|[\u2000-\u32ff]\ufe0f|[\U0001F1E6-\U0001F1FF]{2}")
# Joiners, selectors, skin tones and tags: parts of one emoji, never one of their own.
EMOJI_GLUE = re.compile("[\\s\ufe0e\ufe0f\u200d\u20e3\U0001F3FB-\U0001F3FF\U000E0020-\U000E007F]")
EMOJI_MIN = 3  # distinct emoji drawn as text before it is a style, not a toast
STR_LIT = re.compile(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\\n])*`")
# A line that opens the list, call or type an emoji sits in: `const pieces = [`, `Fruit(`.
OPENER = re.compile(r"[(\[{]\s*$|\b(?:enum|class)\b|=\s*(?:const\s*)?[\[{(]|=>\s*[\[{]")

APP_PRODUCT = "com.apple.product-type.application"
# Bundle IDs of builds that never reach the App Store: environments and tests …
ENV_WORDS = {"dev", "develop", "development", "debug", "staging", "stage", "stg", "qa", "test",
             "tests", "testing", "uat", "beta", "alpha", "internal", "local", "sandbox",
             "preview", "nightly", "canary", "profile"}
# … and, when the Xcode project's targets cannot be read, extensions that ride along.
EXT_WORDS = {"widget", "widgets", "extension", "extensions", "notification", "notifications",
             "service", "share", "intent", "intents", "keyboard", "watch", "watchkitapp",
             "watchkitextension", "clip", "appclip", "stickers", "imessage", "today", "siri",
             "liveactivity", "broadcast"}


# --------------------------------------------------------------------------- report

class Report:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, id_: str, group: str, verdict: str, summary: str,
            evidence: str = "", fix: str = "") -> None:
        self.rows.append({"id": id_, "group": group, "verdict": verdict,
                          "summary": summary, "evidence": evidence, "fix": fix})
        print(f"  {verdict:<5} {id_:<38} {summary}", file=sys.stderr)

    def extend(self, rows: list[dict]) -> None:
        for r in rows:
            self.add(r["id"], r["group"], r["verdict"], r["summary"],
                     r.get("evidence", ""), r.get("fix", ""))

    def overall(self) -> str:
        verdicts = {r["verdict"] for r in self.rows}
        if "FAIL" in verdicts:
            return "FAIL"
        if "WARN" in verdicts:
            return "WARN"
        return "PASS"


# --------------------------------------------------------------------------- helpers

def walk(root: Path, exts: set[str] | None = None):
    if not root.exists():
        return
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            p = Path(dirpath) / name
            if exts is None or p.suffix.lower() in exts:
                yield p


def read(p: Path, limit: int = 3_000_000) -> str:
    try:
        with open(p, "rb") as fh:
            return fh.read(limit).decode("utf-8", "replace")
    except OSError:
        return ""


def words(text: str) -> list[str]:
    """Lowercase words, splitting camelCase and snake_case identifiers."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.findall(r"[^\W_]+", text.lower())


def spell_emoji(text: str) -> str:
    """Emoji as their Unicode names ('🍉' → ' watermelon '), so a progression drawn in emoji
    reads like one spelled out. Flags drop out; line numbers stay as they were."""
    return EMOJI_RE.sub(lambda m: " " if len(m.group()) == 2 and m.group()[1] != "\ufe0f"
                        else f" {unicodedata.name(m.group()[0], '').lower()} ", text)


def wtext(text: str) -> str:
    return " " + " ".join(words(spell_emoji(text))) + " "


def has_phrase(haystack_wtext: str, phrase: str) -> bool:
    needle = " ".join(words(phrase))
    return bool(needle) and f" {needle} " in haystack_wtext


def rel(p: Path, base: Path) -> str:
    try:
        return str(p.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(p)


def line_of(text: str, needle: str) -> int:
    i = text.lower().find(needle.lower())
    return text.count("\n", 0, i) + 1 if i >= 0 else 0


def ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def git(project: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(project), *args], capture_output=True,
                             text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout if out.returncode == 0 else ""


def load_json(name: str) -> dict:
    return json.loads((REFS / name).read_text(encoding="utf-8"))


def generated(p: Path) -> bool:
    n = p.name
    return (n.endswith((".g.dart", ".freezed.dart", ".gr.dart"))
            or n.startswith("app_localizations") or n == "firebase_options.dart")


def stack(project: Path) -> str:
    """flutter, unity, godot, native (an Xcode project of its own) or other."""
    if (project / "pubspec.yaml").exists():
        return "flutter"
    if (project / "ProjectSettings").is_dir() and (project / "Assets").is_dir():
        return "unity"
    if (project / "project.godot").exists():
        return "godot"
    if xcode_projects(project):
        return "native"
    return "other"


def xcode_projects(project: Path) -> list[Path]:
    """project.pbxproj files of the app: ios/ for Flutter, the top two levels otherwise."""
    found = list(project.glob("ios/*.xcodeproj/project.pbxproj"))
    found += [p for p in (*project.glob("*.xcodeproj/project.pbxproj"),
                          *project.glob("*/*.xcodeproj/project.pbxproj"))
              if "Pods" not in p.parts and p not in found]
    return found


# Code and data of each stack: the folders to read and the file types in them. A root of
# "." walks the whole project but its docs, store and build folders.
STACK_CODE = {
    "flutter": (CODE_ROOTS, CODE_EXTS),
    "unity": (["Assets"], CODE_EXTS | {".cs"}),
    "godot": (["."], CODE_EXTS | {".gd", ".tscn", ".tres", ".cfg"}),
    "native": (["."], CODE_EXTS | {".m", ".mm", ".h"}),
    "other": (CODE_ROOTS, CODE_EXTS | {".cs", ".gd", ".lua", ".m", ".mm"}),
}
NOT_CODE = {"docs", "store", "fastlane", "screenshots", "marketing", "design", "export",
            "Library", "Temp", "Logs", "obj", "UserSettings", "ios", "android", "macos",
            "linux", "windows", "web", "test", "tests"}
PROGRAM_EXTS = {".dart", ".cs", ".gd", ".swift", ".kt", ".m", ".mm", ".ts", ".js"}


def code_files(project: Path):
    roots, exts = STACK_CODE[stack(project)]
    seen = set()
    for root in roots:
        for p in walk(project / root, exts):
            if root == "." and set(p.relative_to(project).parts[:-1]) & NOT_CODE:
                continue
            if generated(p) or "xcassets" in str(p) or p in seen:
                continue
            seen.add(p)
            yield p


def pbx_values(project: Path, key: str) -> list[str]:
    vals: list[str] = []
    for pbx in xcode_projects(project):
        vals += re.findall(rf"{key} = \"?([^\";]+)\"?;", read(pbx))
    return [v.strip() for v in vals if v.strip() and "$(" not in v]


def team_id(project: Path) -> str:
    """The Apple team ID: ten capitals and digits; placeholders don't count."""
    valid = re.compile(r"^[A-Z0-9]{10}$")
    teams = sorted({t for t in pbx_values(project, "DEVELOPMENT_TEAM") if valid.match(t)})
    if teams:
        return teams[0]
    for plist in project.glob("ios/ExportOptions*.plist"):
        m = re.search(r"<key>teamID</key>\s*<string>([^<]+)</string>", read(plist))
        if m and valid.match(m.group(1).strip()):
            return m.group(1).strip()
    for m in (re.search(r"appleDeveloperTeamID:\s*(\w+)",
                        read(project / "ProjectSettings/ProjectSettings.asset")),
              re.search(r'app_store_team_id="(\w+)"', read(project / "export_presets.cfg"))):
        if m and valid.match(m.group(1)):
            return m.group(1)
    return ""


def bundle_id(project: Path) -> str:
    ids = [v for v in pbx_values(project, "PRODUCT_BUNDLE_IDENTIFIER")
           if not v.lower().endswith("tests")] or list(engine_bundle_ids(project))
    return sorted(set(ids), key=len)[0] if ids else ""


def engine_bundle_ids(project: Path) -> dict[str, list[str]]:
    """iOS bundle IDs a game engine keeps in its own settings (Unity, Godot)."""
    ids: dict[str, list[str]] = {}
    unity = read(project / "ProjectSettings/ProjectSettings.asset")
    m = re.search(r"applicationIdentifier:\s*\n((?:\s+\S+: .*\n)+)", unity)
    if m:
        for v in re.findall(r"^\s+iPhone: (\S+)", m.group(1), re.M):
            ids.setdefault(v, []).append("ProjectSettings.asset")
    for v in re.findall(r'application/bundle_identifier="([^"]+)"',
                        read(project / "export_presets.cfg")):
        ids.setdefault(v, []).append("export_presets.cfg")
    return ids


def pbx_objects(text: str, isa: str) -> list[tuple[str, str]]:
    """(id, body) of every object of one isa in a project.pbxproj, in Xcode's own layout."""
    return re.findall(r"^\t\t(\w+) (?:/\*[^\n]*?\*/ )?= \{\s*isa = " + re.escape(isa)
                      + r";(.*?)^\t\t\};", text, re.S | re.M)


def app_bundle_ids(project: Path) -> dict[str, list[str]]:
    """Bundle ID → the build configurations that set it, for the application targets of
    the iOS project. Test, extension, watch and App Clip targets ride along with their app."""
    ids: dict[str, list[str]] = {}
    bid_re = re.compile(r'PRODUCT_BUNDLE_IDENTIFIER = "?([^";]+)"?;')
    for pbx in xcode_projects(project):
        text = read(pbx)
        targets = pbx_objects(text, "PBXNativeTarget")
        if not targets:  # not Xcode's layout: every bundle ID but a test's or an extension's
            for v in bid_re.findall(text):
                if "$(" not in v and not set(words(v.rsplit(".", 1)[-1])) & (ENV_WORDS | EXT_WORDS):
                    ids.setdefault(v.strip(), []).append(pbx.parent.name)
            continue
        configs = dict(pbx_objects(text, "XCBuildConfiguration"))
        lists = {}
        for lid, body in pbx_objects(text, "XCConfigurationList"):
            m = re.search(r"buildConfigurations = \((.*?)\);", body, re.S)
            lists[lid] = re.findall(r"^\s*(\w+)", m.group(1), re.M) if m else []
        for _, body in targets:
            ptype = re.search(r'productType = "([^"]+)"', body)
            clist = re.search(r"buildConfigurationList = (\w+)", body)
            if not ptype or ptype.group(1) != APP_PRODUCT or not clist:
                continue
            for cid in lists.get(clist.group(1), []):
                cfg = configs.get(cid, "")
                bid = bid_re.search(cfg)
                name = re.search(r'^\t\t\tname = "?([^";]+)"?;', cfg, re.M)
                if bid and "$(" not in bid.group(1):
                    ids.setdefault(bid.group(1).strip(), []).append(name.group(1) if name else cid)
    for xc in walk(project / "ios", {".xcconfig"}):  # flavors kept in .xcconfig files
        for v in re.findall(r"^\s*PRODUCT_BUNDLE_IDENTIFIER\s*=\s*([^\s;]+)", read(xc), re.M):
            if "$(" not in v:
                ids.setdefault(v, []).append(xc.name)
    for b, where in engine_bundle_ids(project).items():
        ids.setdefault(b, []).extend(where)
    return ids


def store_apps(ids: dict[str, list[str]]) -> dict[str, list[str]]:
    """The bundle IDs that would each go to the App Store as an app of their own: not an
    environment (.dev, appstaging, set only in Debug-dev and Profile-dev) or a test."""
    def env(bid: str, cfgs: list[str]) -> bool:
        if set(words(bid.rsplit(".", 1)[-1])) & ENV_WORDS:
            return True
        if cfgs and all(set(words(c)) & ENV_WORDS for c in cfgs):
            return True
        return any(bid != o and bid.startswith(o) and words(bid[len(o):])
                   and set(words(bid[len(o):])) <= ENV_WORDS for o in ids)
    kept = {b: c for b, c in ids.items() if not env(b, c)}
    return kept or dict(sorted(ids.items(), key=lambda x: len(x[0]))[:1])


def pubspec_assets(project: Path) -> list[str]:
    """The asset paths a Flutter pubspec bundles (`flutter: assets:`, plain or `- path:`)."""
    out: list[str] = []
    in_flutter = in_assets = False
    indent = 0
    for line in read(project / "pubspec.yaml").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        lead = len(line) - len(line.lstrip())
        if lead == 0:
            in_flutter, in_assets = line.startswith("flutter:"), False
        elif in_flutter and re.match(r"\s*assets:\s*$", line):
            in_assets, indent = True, lead
        elif in_assets and lead <= indent and not line.lstrip().startswith("-"):
            in_assets = False
        elif in_assets:
            m = re.match(r"\s*-\s*(?:path:\s*)?[\"']?([^\"'#\s]+)", line)
            if m:
                out.append(m.group(1))
    return out


def art_roots(project: Path) -> list[Path]:
    """Where the bundled images are. A Flutter app bundles assets/ and what its pubspec lists
    (an art/ folder it does not list never reaches the binary); other projects, the usual art
    folders. A path inside another one is left to it."""
    base = project.resolve()
    kind = stack(project)
    if kind == "flutter":
        names = ["assets", *pubspec_assets(project)]
    elif kind == "unity":
        names = ["Assets"]
    elif kind in ("godot", "native"):
        names = ["."]  # art sits beside the code; art_images leaves docs and icons out
    else:
        names = list(ART_DIRS)
    found = [p for p in dict.fromkeys((project / n).resolve() for n in names)
             if p.exists() and p.is_relative_to(base)]
    return [p for p in found if not any(o != p and p.is_relative_to(o) for o in found)]


def art_images(project: Path):
    """Every image file under the art roots, once: not the app icon set, docs or store art."""
    seen: set[Path] = set()
    base = project.resolve()
    for root in art_roots(project):
        for p in walk(root, IMAGE_EXTS):
            parts = p.resolve().relative_to(base).parts[:-1]
            if ".appiconset" in str(p) or (root == base and set(parts) & NOT_CODE):
                continue
            if p.resolve() not in seen:
                seen.add(p.resolve())
                yield p


def app_name(project: Path, override: str | None) -> str:
    if override:
        return override
    plist = read(project / "ios/Runner/Info.plist")
    for key in ("CFBundleDisplayName", "CFBundleName"):
        m = re.search(rf"<key>{key}</key>\s*<string>([^<]+)</string>", plist)
        if m and "$(" not in m.group(1):
            return m.group(1).strip()
    for strings in sorted(project.glob("ios/Runner/*.lproj/InfoPlist.strings")):
        m = re.search(r'CFBundleDisplayName\s*=\s*"([^"]+)"', read(strings))
        if m:
            return m.group(1).strip()
    for m in (re.search(r"^\s*productName: (.+)$",
                        read(project / "ProjectSettings/ProjectSettings.asset"), re.M),
              re.search(r'^config/name="([^"]+)"', read(project / "project.godot"), re.M),
              *(re.search(r'INFOPLIST_KEY_CFBundleDisplayName = "?([^";]+)"?;', read(x))
                for x in xcode_projects(project))):
        if m and "$(" not in m.group(1):
            return m.group(1).strip()
    return project.resolve().name


def old_names(project: Path, current: str, extra: list[str]) -> list[str]:
    """Earlier display names, from --old-name and the bundle's git history."""
    names = list(extra)
    log = git(project, "log", "-p", "--format=", "--", "ios/Runner/Info.plist",
              "ios/Runner/*.lproj/InfoPlist.strings")
    after_key = False  # inside the lines that follow a CFBundle(Display)Name key
    for line in log.splitlines():
        if re.search(r"<key>CFBundle(?:Display)?Name</key>", line):
            after_key = True
            continue
        if after_key:
            m = re.match(r"-\s*<string>([^<]+)</string>", line)
            if m:
                names.append(m.group(1).strip())
            elif "<key>" in line or ("<string>" in line and not line.startswith("-")):
                after_key = False
        m = re.match(r'-\s*"?CFBundle(?:Display)?Name"?\s*=\s*"([^"]+)"', line)
        if m:
            names.append(m.group(1).strip())
    out: list[str] = []
    for n in names:
        if ("$(" in n or ("_" in n and " " not in n) or n.lower() == current.lower()
                or n.lower() in (o.lower() for o in out)):
            continue
        out.append(n)
    return out


# --------------------------------------------------------------------------- signature

def chain_count(wlist: list[str], chain: list[list[str]]) -> tuple[int, list[str], bool]:
    first: dict[str, int] = {}
    for i, w in enumerate(wlist):
        first.setdefault(w, i)
    hits: list[tuple[int, str]] = []
    for syns in chain:
        best = None
        for s in syns:
            sw = words(s)
            if len(sw) == 1 and sw[0] in first:
                if best is None or first[sw[0]] < best[0]:
                    best = (first[sw[0]], s)
        if best:
            hits.append(best)
    idx = [h[0] for h in hits]
    return len(hits), [h[1] for h in hits], idx == sorted(idx)


def spellings(item) -> list[str]:
    """A marker is one name or a list of its spellings, counted once."""
    return [item] if isinstance(item, str) else list(item)


def scan_signature_texts(texts: list[tuple[str, str]], sigs: list[dict], group: str,
                         rep: Report, where: str) -> bool:
    """Chain, alias and marker fingerprints over (label, text) pairs. True if anything hit."""
    hit = False
    prepared = []
    for label, text in texts:
        text = spell_emoji(text)
        wl = words(text)
        prepared.append((label, text, wl, " " + " ".join(wl) + " "))
    for sig in sigs:
        best = (0, "", [], False)
        alias_files: list[str] = []
        markers: dict[str, str] = {}  # first spelling → where it was found
        for label, text, wl, wt in prepared:
            if sig.get("chain"):
                n, matched, ordered = chain_count(wl, sig["chain"])
                if n > best[0]:
                    best = (n, label, matched, ordered)
            for alias in sig.get("aliases", []):
                if words(alias) and not all(w.isdigit() for w in words(alias)) \
                        and has_phrase(wt, alias):
                    alias_files.append(f"{label}:{line_of(text, alias) or '?'} ({alias})")
                    break
            for item in sig.get("markers", []):
                names = spellings(item)
                if names[0] in markers:
                    continue
                found = next((s for s in names if has_phrase(wt, s)), None)
                if found:
                    markers[names[0]] = f"{found} ({label}:{line_of(text, found) or '?'})"
        n, label, matched, ordered = best
        # Out of order, the words are a palette (fruit-named colours), not a
        # progression: one level softer, and nothing below the fail count.
        verdict = None
        if sig.get("chain") and n >= sig.get("chain_fail", 99):
            verdict = "FAIL" if ordered else "WARN"
        elif sig.get("chain") and n >= sig.get("chain_warn", 99) and ordered:
            verdict = "WARN"
        if verdict:
            hit = True
            rep.add(f"{group}.{sig['id']}.chain", group, verdict,
                    f"{n}/{len(sig['chain'])} steps of the {sig['title']} progression "
                    f"in one {where}{' (in order)' if ordered else ''}",
                    f"{label}: {', '.join(matched)}",
                    f"replace the progression; keep at most {sig.get('chain_warn', 4) - 1} "
                    f"of its steps, and change the max-step rule too ({sig.get('rules', '')})")
        if alias_files:
            hit = True
            rep.add(f"{group}.{sig['id']}.alias", group, "WARN",
                    f"{where} names {sig['title']}",
                    "; ".join(alias_files[:5]),
                    "remove the original's name from shipped code and strings; keep it "
                    "only in internal docs")
        if markers:
            hit = True
            need = sig.get("markers_fail", 3)
            rep.add(f"{group}.{sig['id']}.markers", group,
                    "FAIL" if len(markers) >= need else "WARN",
                    f"{len(markers)} of {sig['title']}'s own names (characters, items, "
                    f"levels) in the {where}s",
                    "; ".join(list(markers.values())[:6]),
                    "rename them: the original's characters, items and level names are its "
                    "expression, and often trademarks")
    return hit


def check_signature(project: Path, sigs: list[dict], rep: Report) -> None:
    texts = [(rel(p, project), read(p)) for p in code_files(project)]
    if not texts:
        rep.add("signature.sources", "signature", "SKIP",
                "no code or localisation found under lib/, src/, Sources/, ios/Runner/ "
                "or assets/")
        return
    if not scan_signature_texts(texts, sigs, "signature", rep, "file"):
        rep.add("signature.none", "signature", "PASS",
                f"no famous-game fingerprint in {len(texts)} code, localisation and "
                "data files")


# --------------------------------------------------------------------------- design

def ours_text(md: str) -> str:
    """Prose plus only the 'Ours' column of tables that have one."""
    out: list[str] = []
    ours_col = None
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if ours_col is None and any(c.lower() == "ours" for c in cells):
                ours_col = [c.lower() for c in cells].index("ours")
                continue
            if set(s) <= set("|-: "):
                continue
            if ours_col is not None:
                if ours_col < len(cells):
                    out.append(cells[ours_col])
            else:
                out.append(" ".join(cells))
        else:
            ours_col = None
            out.append(line)
    return "\n".join(out)


def check_design(project: Path, docs: list[Path], sigs: list[dict], packs: dict,
                 rep: Report) -> None:
    if not docs:
        docs = [p for p in (project / "DESIGN.md", project / "docs/DESIGN.md",
                            project / "design.md") if p.exists()]
    if not docs:
        rep.add("design.sources", "design", "SKIP",
                "no DESIGN.md found; pass the design doc with --docs")
        return
    texts = [(rel(d, project), ours_text(read(d))) for d in docs]
    hit = scan_signature_texts(texts, sigs, "design", rep, "design doc")
    for pack in packs["packs"]:
        if pack["kind"] not in ("emoji", "art"):
            continue
        for label, text in texts:
            low = text.lower()
            marker = next((m for m in pack["markers"]["credits"] if m in low), None)
            if marker:
                hit = True
                rep.add(f"design.stock.{pack['id']}", "design", "WARN",
                        f"the design plans {pack['name']} art",
                        f"{label}:{line_of(text, marker)}",
                        "main objects and the icon must be original art; a stock pack "
                        "may only dress UI chrome")
                break
    if not hit:
        rep.add("design.clean", "design", "PASS",
                "our design names no famous-game progression, original or stock art pack")


# --------------------------------------------------------------------------- assets

def path_role(path_text: str, core: set[str], ui: set[str]) -> str:
    parts = set(words(path_text))
    if parts & AUDIO_WORDS:
        return "audio"
    if parts & FONT_WORDS:
        return "font"
    if parts & core:
        return "core"
    if parts & ui:
        return "ui"
    return "unknown"


def asset_verdict(kind: str, role: str) -> str:
    if role in ("audio", "font"):
        return "PASS"
    if role == "core":
        return "FAIL"
    if role == "ui":
        return "WARN" if kind == "emoji" else "PASS"
    return "WARN"


def credit_sources(project: Path):
    name_re = re.compile(r"^(credits?|attributions?|third[_-]?party\w*|notices?|"
                         r"licen[cs]es|acknowledg\w*)$", re.I)
    for p in walk(project):
        if p.suffix.lower() in IMAGE_EXTS | AUDIO_EXTS | FONT_EXTS:
            continue
        if name_re.match(p.stem):
            yield p
    if (project / "README.md").exists():
        yield project / "README.md"
    for p in walk(project / "lib", {".arb", ".dart"}):
        if not generated(p):
            yield p


def emoji_only(token: str) -> str | None:
    """The emoji of a string that holds nothing else ('🍒', '❤️', '👍🏽'), at most four."""
    found = EMOJI_RE.findall(token)
    if not found or len(found) > 4 or EMOJI_GLUE.sub("", EMOJI_RE.sub("", token)):
        return None
    return "".join(found).replace("\ufe0f", "")


def emoji_tokens(p: Path, text: str):
    """(line, emoji) for every string literal — or YAML/CSV value — that is only emoji."""
    if p.suffix.lower() in (".yaml", ".yml", ".csv"):
        for n, line in enumerate(text.splitlines(), 1):
            for v in re.split(r"[,:\t]", line):
                e = emoji_only(v.strip().lstrip("-").strip().strip("'\""))
                if e:
                    yield n, e
        return
    line, pos = 1, 0
    for m in STR_LIT.finditer(text):
        e = emoji_only(m.group()[1:-1])
        if e:
            line, pos = line + text.count("\n", pos, m.start()), m.start()
            yield line, e


def emoji_role(lines: list[str], n: int, core: set[str], ui: set[str]) -> str:
    """core, ui or unknown, from the words on the emoji's line and on the two lines above
    that open the list, call or type it sits in (`const pieces = [`, `Badge(`)."""
    ctx = set(words(lines[n - 1]))
    opened = 0
    for k in range(n - 2, max(-1, n - 42), -1):
        if OPENER.search(lines[k]):
            ctx |= set(words(lines[k]))
            opened += 1
            if opened == 2:
                break
    return "core" if ctx & core else "ui" if ctx & ui else "unknown"


def check_emoji(project: Path, packs: dict) -> dict | None:
    """Emoji drawn as text in code or game data — the system emoji font as the art. No file
    and no credit line to find, so the pack check alone misses it."""
    core = set(packs.get("core_code_words") or packs["core_path_words"])
    ui = set(packs.get("ui_code_words") or packs["ui_path_words"])
    rank = {"core": 2, "unknown": 1, "ui": 0}
    glyphs: dict[str, tuple[str, str, int]] = {}  # emoji → (role, file, line)
    for p in code_files(project):
        text = read(p)
        if not EMOJI_RE.search(text):
            continue
        lines = text.splitlines()
        for n, e in emoji_tokens(p, text):
            role = emoji_role(lines, n, core, ui)
            if e not in glyphs or rank[role] > rank[glyphs[e][0]]:
                glyphs[e] = (role, rel(p, project), n)
    if len(glyphs) < EMOJI_MIN:
        return None
    by_role = {r: [g for g, v in glyphs.items() if v[0] == r] for r in rank}
    places: dict[tuple[str, str], list] = {}  # (file, role) → [first line, emoji …]
    for g, (role, f, n) in sorted(glyphs.items(), key=lambda x: (x[1][1], x[1][2])):
        places.setdefault((f, role), [n]).append(g)
    evidence = "; ".join(f"{f}:{v[0]} [{role}] {' '.join(v[1:9])}{' …' if len(v) > 9 else ''}"
                         for (f, role), v in sorted(places.items(),
                                                    key=lambda x: -rank[x[0][1]])[:5])
    if len(by_role["core"]) >= EMOJI_MIN:
        return {"id": "assets.emoji-glyphs", "verdict": "FAIL",
                "summary": f"{len(by_role['core'])} emoji drawn as text are the game's main objects",
                "evidence": evidence,
                "fix": "draw the main objects as original art (vector in code or your own "
                       "sprites): an emoji is the same picture on every iPhone and in every "
                       "other emoji game, so the binary and the screenshots match them"}
    split = ", ".join(f"{len(v)} {r}" for r, v in by_role.items() if v)
    return {"id": "assets.emoji-glyphs", "verdict": "WARN",
            "summary": f"{len(glyphs)} emoji drawn as text in the code ({split})",
            "evidence": evidence,
            "fix": "confirm none draws a main object or the icon; emoji UI next to original "
                   "art reads as low effort, so draw the ones a player sees most"}


def check_assets(project: Path, packs: dict, rep: Report) -> None:
    core = set(packs["core_path_words"])
    ui = set(packs["ui_path_words"])
    path_re = re.compile(r"`([^`]*[/*.][^`]*)`|((?:assets|lib|ios|images|img)/[\w./*{},\-]+)")
    found: dict[str, list[tuple[str, str, str]]] = {}  # pack id → (role, evidence, path)
    emoji = check_emoji(project, packs)
    if emoji:
        rep.add(emoji["id"], "assets", emoji["verdict"], emoji["summary"], emoji["evidence"],
                emoji["fix"])

    for src in credit_sources(project):
        text = read(src)
        for n, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            for pack in packs["packs"]:
                if not any(m in low for m in pack["markers"]["credits"]):
                    continue
                paths = [a or b for a, b in path_re.findall(line)]
                roles = {path_role(p, core, ui) for p in paths} or {"unknown"}
                for role in roles:
                    found.setdefault(pack["id"], []).append(
                        (role, f"{rel(src, project)}:{n}", ", ".join(paths[:3])))

    template_files: dict[str, dict[str, str]] = {}  # template id → marker → a path
    templated = False
    for p in walk(project):
        if "xcassets" in str(p):
            continue
        low = rel(p, project).lower()
        for pack in packs["packs"]:
            hit = next((m for m in pack["markers"]["files"] if m in low), None)
            if not hit:
                continue
            if pack["kind"] == "template":
                template_files.setdefault(pack["id"], {}).setdefault(hit, rel(p, project))
                continue
            role = path_role(str(p.parent.relative_to(project)), core, ui)
            found.setdefault(pack["id"], []).append((role, rel(p, project), ""))
    for pack in packs["packs"]:
        if pack["kind"] != "template":
            continue
        credits = found.pop(pack["id"], [])
        files = template_files.get(pack["id"], {})
        if credits or len(files) >= pack.get("markers_min", 1):
            templated = True
            rep.add(f"assets.template.{pack['id']}", "assets", "WARN",
                    f"the project looks built from {pack['name']}",
                    "; ".join([h[1] for h in credits[:3]] + list(files.values())[:4]),
                    "Guideline 4.2.6 turns away apps made from a commercial template unless "
                    "the content's owner submits them, and every game built from one template "
                    "shares its binary: keep only plumbing from it, behind your own screens, "
                    "names and art")

    if not found:
        if not emoji and not templated:
            rep.add("assets.none", "assets", "PASS",
                    "no stock art pack credited or found by file name, and no emoji drawn "
                    "as text")
        return

    by_id = {p["id"]: p for p in packs["packs"]}
    order = {"FAIL": 2, "WARN": 1, "PASS": 0}
    for pid, hits in found.items():
        pack = by_id[pid]
        known = [h for h in hits if h[0] != "unknown"] or hits
        worst = max(known, key=lambda h: order[asset_verdict(pack["kind"], h[0])])
        verdict = asset_verdict(pack["kind"], worst[0])
        roles = sorted({h[0] for h in known})
        evidence = "; ".join(f"{h[1]} [{h[0]}] {h[2]}".strip() for h in known[:4])
        if verdict == "FAIL":
            summary = f"{pack['name']} draws the game's main objects"
            fix = ("draw the main objects (and the icon) as original art; a stock pack "
                   "shared by many store apps makes the binary and screenshots match them")
        elif verdict == "WARN":
            summary = (f"{pack['name']} ({pack['kind']}) is shipped; its role is "
                       f"{'/'.join(roles)}")
            fix = ("confirm it is UI chrome only and not the icon or a main object; say so "
                   "in the credits file with the asset paths")
        else:
            summary = f"{pack['name']} used for {'/'.join(roles)} only"
            fix = ""
        rep.add(f"assets.stock.{pid}", "assets", verdict, summary, evidence, fix)


# --------------------------------------------------------------------------- icon

def find_icon(project: Path) -> Path | None:
    cands = [p for p in walk(project / "ios", {".png"}) if "AppIcon.appiconset" in str(p)]
    if not cands and stack(project) != "flutter":
        cands = [p for p in walk(project, {".png"}) if "AppIcon.appiconset" in str(p)]
        m = re.search(r'icons/app_store_1024x1024="res://([^"]+)"',
                      read(project / "export_presets.cfg"))
        if m and (project / m.group(1)).exists():
            return project / m.group(1)
    if not cands:
        for d in ("assets/icon", "assets/icons/app", "store", "docs/store", "assets",
                  "Assets", "Assets/Icons"):
            cands += [p for p in walk(project / d, {".png"})
                      if re.search(r"(app[_-]?icon|icon[_-]?1024|^icon\.png$)", p.name, re.I)]
    if not cands:
        return None
    big = [p for p in cands if "1024" in p.name]
    return (big or sorted(cands, key=lambda p: p.stat().st_size))[-1]


def icon_sources(project: Path) -> set[Path]:
    """Files the app icon is generated from — they match it by construction."""
    srcs: set[Path] = set()
    for m in re.finditer(r"^\s*(?:image_path\w*|adaptive_icon_foreground|"
                         r"adaptive_icon_background|ios_image_path)\s*:\s*[\"']?([^\"'\s#]+)",
                         read(project / "pubspec.yaml"), re.M):
        if not m.group(1).startswith("#"):
            srcs.add((project / m.group(1)).resolve())
    for p in art_images(project):
        stem = p.stem.lower()
        if (re.search(r"app[_-]?icon|launcher[_-]?icon|icon[_-]?(1024|master|source)", stem)
                or (p.parent.name.lower() in ("icon", "app_icon", "launcher")
                    and stem.startswith("icon"))):
            srcs.add(p.resolve())
    return srcs


def icon_match(icon, images) -> tuple[int, str, int]:
    """(closest dHash distance, its label, images compared) between an icon and images
    given as (label, path or bytes). Each image is centred on the icon's background and
    matched against square crops of the icon at several sizes, nudged a little each way:
    an icon rarely places the sprite dead centre (a drop shadow shifts it too)."""
    from PIL import Image
    base = icon.convert("RGB")
    w, h = base.size
    bg = base.getpixel((max(1, w // 64), max(1, h // 64)))
    crops = []
    for frac in (1.0, 0.9, 0.8, 0.7, 0.65, 0.6, 0.55, 0.5):
        side = int(min(w, h) * frac)
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            left = (w - side) // 2 + dx * side // 25
            top = (h - side) // 2 + dy * side // 25
            if left < 0 or top < 0 or left + side > w or top + side > h:
                continue
            crops.append(dhash(base.crop((left, top, left + side, top + side))))
    best, where, checked = 65, "", 0
    for label, src in images:
        try:
            with Image.open(io.BytesIO(src) if isinstance(src, bytes) else src) as im:
                if min(im.size) < 32:
                    continue
                img = im.convert("RGBA")
        except Exception:  # unreadable or exotic format: not this check's business
            continue
        bbox = img.getchannel("A").getbbox()
        if bbox:
            img = img.crop(bbox)
        side = max(img.size)
        canvas = Image.new("RGB", (side, side), bg)
        canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
        hsh = dhash(canvas)
        checked += 1
        d = min(bin(c ^ hsh).count("1") for c in crops)
        if d < best:
            best, where = d, label
        if checked >= 600:
            break
    return best, where, checked


def check_icon(project: Path, rep: Report) -> None:
    icon = find_icon(project)
    if icon is None:
        rep.add("icon.missing", "icon", "SKIP", "no app icon found (AppIcon.appiconset)")
        return
    try:
        from PIL import Image
    except ImportError:
        rep.add("icon.unverified", "icon", "WARN",
                "Pillow is not installed, so the icon was not compared with bundled art",
                rel(icon, project),
                "pip install pillow and rerun, and judge the icon by eye (references/checks.md J3)")
        return

    skipped = icon_sources(project)
    with Image.open(icon) as im:
        d, where, checked = icon_match(
            im, ((rel(p, project), p) for p in art_images(project)
                 if "launch" not in str(p).lower() and p.resolve() not in skipped
                 and p.resolve() != icon.resolve()))
    best = (d, where)

    d, where = best
    note = (f"; icon sources skipped: {', '.join(sorted(rel(s, project) for s in skipped))}"
            if skipped else "")
    if checked == 0:
        looked = ", ".join(rel(r, project) + ("/" if r.is_dir() else "")
                           for r in art_roots(project))
        rep.add("icon.bundled", "icon", "SKIP",
                "no bundled images to compare the icon with (looked in "
                f"{looked or 'assets/, the usual art folders and the pubspec asset paths'})",
                rel(icon, project),
                "judge the icon's subject by eye (references/checks.md J3); if the art lives "
                "elsewhere, list it under flutter: assets: in pubspec.yaml")
    elif d <= 10:
        rep.add("icon.bundled", "icon", "FAIL",
                f"the icon reproduces a bundled image ({where})",
                f"{rel(icon, project)} vs {where}: dHash distance {d}/64",
                "draw an icon of the game's own character or mechanic; an icon made from a "
                "stock sprite matches every other app built from that sprite")
    elif d <= 14:
        rep.add("icon.bundled", "icon", "WARN",
                f"the icon resembles a bundled image ({where})",
                f"{rel(icon, project)} vs {where}: dHash distance {d}/64",
                "compare the two by eye; if the icon is that asset, redraw it")
    else:
        rep.add("icon.bundled", "icon", "PASS",
                f"the icon is not a copy of any of {checked} bundled images",
                f"{rel(icon, project)}; closest {where or '-'} at {d}/64{note}",
                "")


# --------------------------------------------------------------------------- metadata

def listing_fields(project: Path, listing: list[Path]) -> list[tuple[str, str, str]]:
    """(field, source, text) for every listing string found."""
    out: list[tuple[str, str, str]] = []

    def from_json(obj, src: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = re.sub(r"[^a-z_]", "", k.lower())
                if isinstance(v, str) and key in LISTING_KEYS:
                    out.append((LISTING_KEYS[key], src, v))
                else:
                    from_json(v, src)
        elif isinstance(obj, list):
            for v in obj:
                from_json(v, src)

    files: list[Path] = []
    if listing:
        for p in listing:
            files += list(walk(p, {".json", ".txt", ".md"}))
    else:
        for d in LISTING_DIRS:
            for p in walk(project / d, {".json", ".txt", ".md"}):
                stem = p.stem.lower()
                if p.suffix == ".json" or stem in LISTING_KEYS or "listing" in stem:
                    files.append(p)
        # Listing docs kept as markdown (docs/APP-STORE.md, docs/release/store_listing.md);
        # audits and runbooks quote other apps' names on purpose, so they are left out.
        for p in [*walk(project / "docs", {".md"}), *project.glob("*.md")]:
            stem = p.stem.lower()
            if (re.search(r"app[-_ ]?store|listing", stem)
                    and not re.search(r"audit|review|checklist|runbook|status|plan|release",
                                      stem)):
                files.append(p)
    seen: set[Path] = set()
    for p in files:
        if p.resolve() in seen:
            continue
        seen.add(p.resolve())
        src = rel(p, project)
        stem = re.sub(r"[^a-z_]", "", p.stem.lower())
        if p.suffix == ".json":
            try:
                from_json(json.loads(read(p)), src)
            except json.JSONDecodeError:
                continue
        elif stem in LISTING_KEYS:
            out.append((LISTING_KEYS[stem], src, read(p)))
        else:
            out.append(("listing", src, prose(read(p))))
    return out


def prose(md: str) -> str:
    """Markdown minus code spans, URLs and paths — `.clone/status.md` is no copy."""
    md = re.sub(r"```.*?```", " ", md, flags=re.S)
    md = re.sub(r"`[^`]*`", " ", md)
    return re.sub(r"\S*[/\\]\S*", " ", md)


def snippet(text: str, needle: str, width: int = 60) -> str:
    i = text.lower().find(needle.lower())
    if i < 0:
        return ""
    s = text[max(0, i - width): i + len(needle) + width].replace("\n", " ")
    return f"…{s.strip()}…"


def check_metadata(project: Path, sigs: dict, listing: list[Path], name: str,
                   olds: list[str], rep: Report) -> None:
    fields = listing_fields(project, listing)
    if not fields:
        rep.add("metadata.sources", "metadata", "WARN",
                "no store listing found — the listing is half of what 4.3 judges; only the "
                "app name was checked",
                f"looked in {', '.join(LISTING_DIRS)} and docs/*app-store*.md, *listing*.md",
                "pass the listing files or folder with --listing")
    fields.append(("name", "ios/Runner/Info.plist", name))
    hit = False
    prepared = [(field, src, wtext(text)) for field, src, text in fields]
    for sig in sigs["signatures"]:
        for kind, verdict in (("aliases", "FAIL"), ("phrases", "FAIL"), ("markers", "FAIL"),
                              ("terms", "WARN")):
            ev: list[str] = []
            for field, src, wt in prepared:
                if kind == "terms" and field not in HEADLINE_FIELDS:
                    continue
                for item in sig.get(kind, []):
                    found = next((s for s in spellings(item) if has_phrase(wt, s)), None)
                    if found:
                        ev.append(f"{src} [{field}]: \"{found}\"")
            if ev:
                hit = True
                label = {"aliases": "names", "phrases": "uses the signature wording of",
                         "markers": "uses the character, item or level names of",
                         "terms": "leans on the genre words of"}[kind]
                rep.add(f"metadata.{sig['id']}.{kind[:-1] if kind != 'aliases' else 'alias'}",
                        "metadata", verdict, f"the listing {label} {sig['title']}",
                        "; ".join(sorted(set(ev))[:6]),
                        "lead with the game's own twist; drop the original's name, its "
                        "progression and its signature words from name, subtitle, keywords "
                        "and description")
    for field, src, text in fields:
        wt = wtext(text)
        if field in ("name", "subtitle"):
            for g in sigs.get("generic_names", []):
                if has_phrase(wt, g):
                    hit = True
                    rep.add("metadata.generic-name", "metadata", "WARN",
                            f"the {field} uses the genre label \"{g}\"", f"{src}: {text[:80]}",
                            "pick a distinctive name (brand-name-checker); generic genre "
                            "names put the app among dozens of look-alikes")
                    break
        # A hyphenated name (game-clone-pipeline, rotate-rings-clone) is a tool or a
        # folder, not the listing calling itself a clone.
        wt_copy = wtext(re.sub(r"\S*\w-clone\b\S*|\S*\bclone-\w\S*", " ", text, flags=re.I))
        for c in sigs.get("copycat_wording", []):
            if has_phrase(wt_copy, c):
                hit = True
                rep.add("metadata.copycat-wording", "metadata", "WARN",
                        f"the {field} says \"{c}\"", f"{src}: {snippet(text, c)}",
                        "describe the game on its own terms; never position it against "
                        "another app")
                break
        for o in olds:
            if has_phrase(wt, o):
                hit = True
                rep.add("metadata.old-name", "metadata", "WARN",
                        f"the {field} still says the old name \"{o}\"", src,
                        "replace every old name in the listing")
                break
    # 4.3(b): a new game in a crowded category is taken only when it is meaningfully
    # different — which no scan can tell, so the row hands it to J1 and J2.
    crowded: dict[str, set[str]] = {}
    headline_only = set(sigs.get("generic_names_headline_only", []))
    for field, src, text in fields:
        if field in ("whatsnew", "reviewnotes"):
            continue
        if field == "listing":
            # Listing docs keep ASO notes beside the copy: a table row or a quoted word
            # talks about a word ("'sudoku' would target other games") rather than using it.
            text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("|"))
            text = re.sub(r'"[^"\n]*"|“[^”\n]*”', " ", text)
        # A label never spans a comma or a sentence: "block, puzzle" is two keywords.
        for part in re.split(r'[,;!?"“”()\[\]\n]|\.\s', text):
            wt = wtext(part)
            for g in sigs.get("generic_names", []):
                if g in headline_only and field not in ("name", "subtitle", "keywords"):
                    continue  # "two free slots" in a sentence is no casino
                if has_phrase(wt, g):
                    crowded.setdefault(g, set()).add(f"{src} [{field}]")
    crowded = {g: s for g, s in crowded.items()
               if not any(g != o and has_phrase(f" {o} ", g) for o in crowded)}
    if crowded:
        hit = True
        labels = sorted(crowded, key=lambda g: (-len(crowded[g]), g))
        rep.add("metadata.saturated-genre", "metadata", "WARN",
                f"the listing places the game in a crowded category: {', '.join(labels[:4])}",
                "; ".join(f"\"{g}\" in {', '.join(sorted(crowded[g])[:3])}" for g in labels[:4]),
                "4.3(b) turns away 'variants of existing app categories': name the own mechanic "
                "in one sentence, show it on the first screen (J2) and lead the subtitle and "
                "the first sentence with it (J4). The classic game with levels, hints and "
                "themes is the variant; J1 and J2 decide, and fail it")
    if not hit:
        rep.add("metadata.clean", "metadata", "PASS",
                f"{len(fields)} listing fields name no famous game, signature wording, "
                "generic label or old name")


# --------------------------------------------------------------------------- market

def search_terms(name: str, fields: list[tuple[str, str, str]]) -> list[str]:
    """What a player would type to find this game: its name, subtitle and keywords."""
    terms = [name]
    for field, _, text in fields:
        if field == "subtitle":
            terms.append(text)
        elif field == "keywords":
            terms += text.split(",")
    out: list[str] = []
    for t in terms:
        t = " ".join(t.split())
        if len(t) >= 3 and t.lower() not in (o.lower() for o in out):
            out.append(t)
    return out[:8]


def check_market(project: Path, listing: list[Path], name: str, with_listing: bool,
                 countries: list[str], offline: bool, rep: Report) -> None:
    log = lambda m: print(m, file=sys.stderr)  # noqa: E731
    store = market.load_store()
    note = ""
    if not market.charts_fresh(store, countries):
        if offline:
            note = " (stale: --offline)" if store["apps"] else ""
        else:
            log(f"  … fetching the App Store charts for {', '.join(countries)} "
                "(weekly, about 3 minutes)")
            try:
                market.refresh_charts(store, countries, log)
                market.save_store(store)
            except Exception as e:  # network trouble: keep what is cached
                note = f" (refresh failed: {e})"
    fields = listing_fields(project, listing) if with_listing else []
    terms = search_terms(name, fields)
    searched = []
    for t in terms:
        try:
            if market.search(store, t, countries[0], offline) or not offline:
                searched.append(t)
        except Exception:  # one failed search is a smaller neighbourhood, not a stop
            continue
    if not store["apps"]:
        rep.add("market.index", "market", "WARN",
                "no App Store index: offline and nothing cached", "",
                "rerun online, or run scripts/market.py refresh first")
        return
    if not offline:
        market.save_store(store)
    try:
        from PIL import Image
    except ImportError:
        Image = None
    prints = (market.icon_prints([a.get("icon", "") for a in store["apps"].values()],
                                 offline, log) if Image else {})
    m = market.Market(store, own_bundle=bundle_id(project), prints=prints)
    charts = store.get("charts") or {}
    rep.add("market.index", "market", "WARN" if note else "PASS",
            f"compared with {len(m.apps):,} games on the App Store{note}",
            f"top 100 free, paid and grossing in {len(market.GAME_GENRES)} game charts of "
            f"{', '.join(charts.get('countries', []))} (fetched {charts.get('built', 'never')}); "
            f"search: {', '.join(searched) or 'none'}",
            "rerun online so the index is under a week old" if note else "")
    rep.extend(m.name_rows(name))
    if fields:
        rep.extend(m.listing_rows(fields, name, HEADLINE_FIELDS))
    icon = find_icon(project)
    if icon is None:
        rep.add("market.icon", "market", "SKIP", "no app icon found (AppIcon.appiconset)")
    elif Image is None:
        rep.add("market.icon", "market", "WARN",
                "Pillow is not installed, so the icon was not compared with store icons",
                rel(icon, project), "pip install pillow and rerun")
    else:
        with Image.open(icon) as im:
            rep.extend(m.icon_rows(market.icon_print(im), rel(icon, project)))
    desc = [(src, text) for field, src, text in fields if field in ("description", "promotional")]
    desc = desc or [(src, text) for field, src, text in fields if field == "listing"]
    if desc:
        rep.extend(m.wording_rows("\n".join(t for _, t in desc),
                                  ", ".join(sorted({s for s, _ in desc}))))


# --------------------------------------------------------------------------- portfolio

STRING_RE = re.compile(r"'''.*?'''|\"\"\".*?\"\"\"|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"",
                       re.S)
COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
TOKEN_RE = re.compile(r"[A-Za-z_$][\w$]*|\d+(?:\.\d+)?|[^\s\w]")


def shingles(code: str, k: int = 5) -> set[int]:
    code = STRING_RE.sub(" S ", code)
    code = COMMENT_RE.sub(" ", code)
    toks = TOKEN_RE.findall(code)
    return {hash(tuple(toks[i:i + k])) for i in range(len(toks) - k + 1)}


def repo_fingerprint(root: Path, core: set[str]) -> dict:
    files: dict[str, tuple[str, str]] = {}  # sha → (relpath, kind)
    for d in (*art_roots(root), root / "ios/Runner/Assets.xcassets/AppIcon.appiconset"):
        for p in walk(d):
            ext = p.suffix.lower()
            if ext in (".json", ".txt", ".md") or TEXT_LICENSE.search(p.stem):
                continue
            if "AppIcon" in str(p):
                kind = "icon"
            elif ext in FONT_EXTS:
                kind = "font"
            elif ext in AUDIO_EXTS:
                kind = "audio"
            elif ext in IMAGE_EXTS | {".svg"}:
                kind = "core-image" if set(words(rel(p, root))) & core else "image"
            else:
                kind = "other"
            try:
                if p.stat().st_size > 20_000_000:
                    continue
                sha = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                continue
            files.setdefault(sha, (rel(p, root), kind))
    code: dict[str, set[int]] = {}
    programs = (walk(root / "lib", {".dart"}) if stack(root) == "flutter"
                else (p for p in code_files(root) if p.suffix.lower() in PROGRAM_EXTS))
    for p in programs:
        if not generated(p):
            code[rel(p, root)] = shingles(read(p))
    return {"files": files, "code": code}


def check_bundles(project: Path, rep: Report) -> None:
    """4.3(a) to the letter: one game shipped under several bundle IDs."""
    apps = store_apps(app_bundle_ids(project))
    if not apps:
        rep.add("portfolio.bundle-ids", "portfolio", "SKIP",
                "no bundle ID in ios/*.xcodeproj or its .xcconfig files")
        return
    evidence = "; ".join(f"{b} ({', '.join(sorted(set(c))[:4])})" for b, c in sorted(apps.items()))
    if len(apps) == 1:
        rep.add("portfolio.bundle-ids", "portfolio", "PASS",
                f"one App Store bundle ID: {next(iter(apps))}", evidence)
        return
    rep.add("portfolio.bundle-ids", "portfolio", "FAIL",
            f"this project builds {len(apps)} App Store apps: one game under several bundle "
            "IDs is what 4.3(a) forbids",
            evidence,
            "ship one app and offer the variants (seasons, themes, level packs) inside it, as "
            "in-app purchases if they cost money; if an ID is only a test or internal build, "
            "name it so (.dev, .staging, .beta) or drop its target")


def sibling_repos(project: Path, portfolio: Path) -> list[Path]:
    me = project.resolve()
    return [d for d in sorted(portfolio.iterdir()) if d.is_dir() and d.resolve() != me
            and stack(d) != "other"]


# App Store screenshot sizes (portrait; landscape is the same swapped): iPhone 6.9" to 5.5",
# iPad 13" and 11". A file of one of these sizes is a store screenshot, wherever it is kept.
SHOT_SIZES = {(1320, 2868), (1290, 2796), (1260, 2736), (1284, 2778), (1242, 2688),
              (1206, 2622), (1179, 2556), (1170, 2532), (1125, 2436), (1080, 2340),
              (1242, 2208), (2064, 2752), (2048, 2732), (1668, 2420), (1668, 2388),
              (1640, 2360), (1488, 2266)}
SHOT_SIZES |= {(h, w) for w, h in SHOT_SIZES}
SHOT_SKIP = {"ios", "android", "macos", "linux", "windows", "web", "test", "integration_test"}
SHOT_SAME, SHOT_ALIKE = 24, 40  # bits of 256: one screenshot reused / nearly


def store_shots(root: Path, limit: int = 60) -> list[Path]:
    """The store screenshots kept in a repo: images of an App Store screenshot size."""
    from PIL import Image
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS | SHOT_SKIP
                       and not d.startswith(".")]
        for f in sorted(filenames):
            if Path(f).suffix.lower() not in (".png", ".jpg", ".jpeg"):
                continue
            try:
                with Image.open(Path(dirpath) / f) as im:
                    if im.size in SHOT_SIZES:
                        out.append(Path(dirpath) / f)
            except Exception:  # unreadable image: not a screenshot we can compare
                continue
            if len(out) >= limit:
                return out
    return out


def check_screenshots(project: Path, siblings: list[Path], live: list[dict], offline: bool,
                      rep: Report) -> None:
    """Our store screenshots against our other games' — local repos and live apps. A
    screenshot shipped by two of a team's games is the 'apps you submitted' variant."""
    try:
        from PIL import Image
    except ImportError:
        rep.add("portfolio.screenshots", "portfolio", "WARN",
                "Pillow is not installed, so the screenshots were not compared", "",
                "pip install pillow and rerun")
        return
    ours = store_shots(project)
    if not ours:
        rep.add("portfolio.screenshots", "portfolio", "SKIP",
                "no store screenshot (an App Store screenshot size) in the repo", "",
                "keep the screenshots you upload in the repo so they can be compared")
        return

    def prints(paths):
        out = []
        for p in paths:
            with Image.open(p) as im:
                out.append((p, market.shot_print(im)))
        return out

    mine = prints(ours)
    theirs: list[tuple[str, str]] = []  # (where, print)
    for sib in siblings:
        theirs += [(f"{sib.name}/{rel(p, sib)}", h) for p, h in prints(store_shots(sib, 30))]
    urls = {u: a for a in live for u in a.get("shots", [])}
    for u, h in market.shot_prints(list(urls), offline).items():
        theirs.append((f"{urls[u]['name']} on the App Store ({u.rsplit('/', 1)[-1]})", h))
    if not theirs:
        rep.add("portfolio.screenshots", "portfolio", "PASS",
                f"{len(mine)} store screenshot(s); no other game of yours to compare with",
                ", ".join(rel(p, project) for p, _ in mine[:4]))
        return
    best = min(((market.shot_distance(h, t), rel(p, project), w)
                for p, h in mine for w, t in theirs), key=lambda x: x[0])
    d, ours_p, where = best
    ev = f"{ours_p} vs {where}: {d}/256 bits ({len(mine)} ours, {len(theirs)} theirs)"
    if d <= SHOT_SAME:
        rep.add("portfolio.screenshots", "portfolio", "FAIL",
                "a store screenshot is the same image as one of another of your games", ev,
                "capture this game's own screens; one screenshot in two apps is what the "
                "'apps you submitted' variant of 4.3(a) compares")
    elif d <= SHOT_ALIKE:
        rep.add("portfolio.screenshots", "portfolio", "WARN",
                "a store screenshot nearly repeats one of another of your games", ev,
                "compare the two by eye; recapture it if a player could take one for the other")
    else:
        rep.add("portfolio.screenshots", "portfolio", "PASS",
                "no store screenshot repeats one of your other games'",
                ev + "; whether the sets share one template is J1's call")


def check_store_catalogue(project: Path, name: str, apps: list[dict], artists: list[str],
                          how: str, fields: list[tuple[str, str, str]], offline: bool,
                          rep: Report) -> None:
    """The games the team already sells: the same name, icon or description again is the
    'apps you submitted' variant, whether or not their repos are on this machine."""
    own = bundle_id(project)
    others = [a for a in apps if a.get("bundle") != own and a.get("name")]
    if not artists:
        hint = ("pass --artist-id (the number in apps.apple.com/…/developer/…/id<N>) or "
                "--account-holder with the seller name the App Store shows")
        if how:
            rep.add("portfolio.store", "portfolio", "SKIP",
                    f"no app of this team found on the App Store (looked up by {how})", "",
                    "if the team does sell apps, " + hint)
        else:
            rep.add("portfolio.store", "portfolio", "WARN",
                    "the team's live apps were not checked (offline, nothing cached)", "",
                    "rerun online; " + hint)
        return
    games = [a for a in others if a.get("game")]
    summary = (f"{len(others)} other app(s) live on the team ({len(games)} games) from "
               f"developer id {', '.join(artists)}")
    rows = 0
    mine = core_name(name)
    for a in others:
        if mine and core_name(a["name"]) == mine:
            rep.add("portfolio.store-name", "portfolio", "FAIL",
                    f"the team already sells {a['name']}: the same game name on a second app",
                    f"{a['name']} ({a.get('bundle')}) {a.get('url', '')}",
                    "4.3(a): update the app you have, or name and make a different game")
            rows += 1
        elif ledger.same_game(name, a["name"]):
            rep.add("portfolio.store-name", "portfolio", "WARN",
                    f"the name is one of the team's live apps' with a word more or less: "
                    f"{a['name']}", f"{a['name']} ({a.get('bundle')}) {a.get('url', '')}",
                    "a sequel or variant of a live app reads as 4.3(a) unless it is plainly "
                    "a different game; say how in the review notes")
            rows += 1
    try:
        from PIL import Image
    except ImportError:
        Image = None
    icon = find_icon(project)
    if Image and icon and others:
        prints = market.icon_prints([a.get("icon", "") for a in others], offline)
        m = market.Market({"apps": {a["id"]: a for a in others}}, own_bundle=own, prints=prints)
        with Image.open(icon) as im:
            for r in m.icon_rows(market.icon_print(im), rel(icon, project)):
                if r["verdict"] in ("FAIL", "WARN"):
                    rep.add("portfolio.store-icon", "portfolio", r["verdict"],
                            r["summary"].replace("the icon", "the icon (vs the team's live apps)"),
                            r["evidence"], "draw this game's own icon; one look across a "
                            "team's icons is the 'apps you submitted' variant")
                    rows += 1
    desc = "\n".join(t for f, _, t in fields if f in ("description", "promotional"))
    if desc and others:
        m = market.Market({"apps": {a["id"]: a for a in others}}, own_bundle=own)
        for r in m.wording_rows(desc, "listing"):
            if r["verdict"] in ("FAIL", "WARN"):
                rep.add("portfolio.store-wording", "portfolio", r["verdict"],
                        r["summary"] + " (one of the team's live apps)", r["evidence"],
                        "write this game's description from this game; a listing shared "
                        "across a team's apps is what 4.3(a) compares")
                rows += 1
    recent = sorted(a["released"] for a in games
                    if a.get("released") and market.age_days(a["released"] + "T00:00:00Z") <= 30)
    if len(recent) >= 3:
        rep.add("portfolio.store-pace", "portfolio", "WARN",
                f"the team released {len(recent)} games in the last 30 days",
                ", ".join(recent), "space releases out; a burst of games from one account is "
                "the 'apps you submitted' variant's other half")
        rows += 1
    if not rows:
        rep.add("portfolio.store", "portfolio", "PASS",
                summary + ": none shares this game's name, icon or wording", "; ".join(
                    f"{a['name']} ({a.get('released', '')})" for a in others[:8]))


def core_name(name: str) -> str:
    return market.core(name)


def check_portfolio(project: Path, portfolio: Path, packs: dict, rep: Report) -> None:
    check_bundles(project, rep)
    core = set(packs["core_path_words"])
    siblings = sibling_repos(project, portfolio)
    if not siblings:
        rep.add("portfolio.none", "portfolio", "SKIP",
                f"no sibling app repos in {portfolio}", "",
                "pass the folder holding your other apps with --portfolio")
        return
    mine = repo_fingerprint(project, core)
    my_all: set[int] = set().union(*mine["code"].values()) if mine["code"] else set()
    my_media = sum(1 for _, kind in mine["files"].values() if kind != "font")
    flagged = False
    scores: list[tuple[float, str]] = []

    for sib in siblings:
        theirs = repo_fingerprint(sib, core)
        shared = [(mine["files"][sha], theirs["files"][sha][0])
                  for sha in mine["files"].keys() & theirs["files"].keys()]
        their_all: set[int] = set().union(*theirs["code"].values()) if theirs["code"] else set()
        contain = len(my_all & their_all) / len(my_all) if my_all else 0.0
        scores.append((contain, sib.name))

        near: list[str] = []
        for path, sh in mine["code"].items():
            if len(sh) < 50:
                continue
            for tpath, tsh in theirs["code"].items():
                if tsh and len(sh & tsh) / len(sh) >= 0.8:
                    near.append(f"{path} ≈ {sib.name}/{tpath}")
                    break

        heavy = [s for s in shared if s[0][1] in ("icon", "core-image")]
        media = [s for s in shared if s[0][1] in ("image", "audio", "other")]
        fonts = [s for s in shared if s[0][1] == "font"]

        verdict, why = "PASS", []
        if contain >= 0.5:
            verdict = "FAIL"
            why.append(f"{contain:.0%} of our code also appears in {sib.name}")
        elif contain >= 0.25:
            verdict = "WARN"
            why.append(f"{contain:.0%} of our code also appears in {sib.name}")
        if heavy:
            verdict = "FAIL"
            why.append(f"{len(heavy)} icon/main-object image(s) identical to {sib.name}")
        if media and (len(media) >= 10 or (my_media and len(media) / my_media >= 0.25)):
            verdict = "WARN" if verdict == "PASS" else verdict
            why.append(f"{len(media)} identical image/audio file(s) with {sib.name}")
        if verdict == "PASS":
            continue
        flagged = True
        ev = [f"{a[0]} = {sib.name}/{b}" for a, b in (heavy + media)[:4]] + near[:4]
        if fonts:
            ev.append(f"{len(fonts)} identical font file(s) (common, not a finding)")
        rep.add(f"portfolio.{sib.name}", "portfolio", verdict, "; ".join(why),
                "; ".join(ev),
                "make each app its own: original art and icon per game, and shared code "
                "kept to plumbing (purchases, settings) behind a different look — a "
                "reviewer must not see a re-skin of your earlier app")

    if not flagged:
        top = ", ".join(f"{n} {c:.0%}" for c, n in sorted(scores, reverse=True)[:3])
        rep.add("portfolio.clear", "portfolio", "PASS",
                f"no sibling app shares much code or any main art with this one "
                f"({len(siblings)} compared)",
                f"closest by shared code: {top}")


# --------------------------------------------------------------------------- footprint

def fetch(url: str, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": f"appstore-spam-guard/{VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, OSError, ValueError) as e:
        return -1, str(e)


def discover_urls(project: Path) -> list[str]:
    urls: list[str] = []
    sources = list(walk(project / "docs/store", {".md", ".json", ".txt"})) + \
        list(walk(project / "store", {".md", ".json", ".txt"})) + \
        [p for p in (project / "README.md",) if p.exists()]
    for p in sources:
        for line in read(p).splitlines():
            if not URL_HINT.search(line):
                continue
            for u in re.findall(r"https?://[^\s)>\"'`\]]+", line):
                u = u.rstrip(".,;")
                if any(h in u for h in URL_SKIP_HOSTS) or u in urls:
                    continue
                urls.append(u)
    return urls[:8]


def github_repo(url_or_remote: str) -> str | None:
    m = re.search(r"github\.com[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?(?:[/#?]|$)", url_or_remote)
    if not m or m.group(1) in ("en", "site", "about", "features", "orgs", "sponsors"):
        return None
    return f"{m.group(1)}/{m.group(2)}"


def check_footprint(project: Path, urls: list[str], name: str, olds: list[str],
                    offline: bool, rep: Report) -> None:
    urls = urls or discover_urls(project)
    origin = git(project, "remote", "get-url", "origin").strip()
    repos: dict[str, str] = {}
    if origin and github_repo(origin):
        repos[github_repo(origin)] = "this game's own repo"
    if not urls and not repos:
        rep.add("footprint.none", "footprint", "SKIP",
                "no privacy/support/marketing URL or GitHub remote found", "",
                "pass the URLs the listing uses with --url")
        return
    if offline:
        rep.add("footprint.offline", "footprint", "WARN",
                f"{len(urls)} URL(s) and {len(repos)} repo(s) not fetched (--offline)",
                ", ".join(urls), "rerun online before submitting")
        return

    flagged = False
    for url in urls:
        status, body = fetch(url)
        if status != 200:
            flagged = True
            rep.add("footprint.url", "footprint", "WARN",
                    f"{url} answered {status if status > 0 else 'nothing'}",
                    body[:120] if status < 0 else "",
                    "every URL in the listing must load (HTTP 200) for the reviewer")
            continue
        text = html.unescape(re.sub(r"<[^>]+>", " ", body))
        wt = wtext(text)
        problems = []
        if name and not has_phrase(wt, name):
            problems.append(f"does not show the app name \"{name}\"")
        stale = [o for o in olds if has_phrase(wt, o)]
        if stale:
            problems.append(f"still shows old name(s) {', '.join(stale)}")
        if problems:
            flagged = True
            rep.add("footprint.page", "footprint", "WARN", f"{url} " + "; ".join(problems),
                    url, "update the page the reviewer opens so it names this app only")
        for href in re.findall(r"https?://github\.com/[^\s\"'<>]+", body):
            r = github_repo(href)
            if r and r not in repos:
                repos[r] = f"linked from {url}"

    for repo, why in list(repos.items())[:8]:
        status, body = fetch(f"https://api.github.com/repos/{repo}")
        if status == 404:
            continue  # private or gone — nothing public to find
        if status != 200:
            flagged = True
            rep.add("footprint.github", "footprint", "WARN",
                    f"could not check github.com/{repo} ({status})", why,
                    "check by hand whether it is public and what it shows")
            continue
        meta = json.loads(body)
        desc = f"{meta.get('description') or ''} {meta.get('homepage') or ''}"
        stale = [o for o in olds if has_phrase(wtext(desc), o)]
        cstatus, cbody = fetch(f"https://api.github.com/repos/{repo}/contents")
        names = {c.get("name") for c in json.loads(cbody)} if cstatus == 200 and cbody.startswith("[") else set()
        source = bool(names & {"pubspec.yaml", "lib", "ios", "Package.swift"})
        notes = []
        if stale:
            notes.append(f"its description still says {', '.join(stale)}")
        if source:
            notes.append("it holds the app's source code")
        if meta.get("fork"):
            notes.append(f"it is a fork of {(meta.get('parent') or {}).get('full_name', 'another repo')}"
                         " — code that is public elsewhere")
        if meta.get("template_repository"):
            notes.append(f"it was created from the template "
                         f"{meta['template_repository'].get('full_name', '')}")
        if notes:
            flagged = True
            rep.add("footprint.github", "footprint", "WARN",
                    f"public repo github.com/{repo} ({why}): " + "; ".join(notes),
                    desc.strip()[:160],
                    "make the source repo private and update public descriptions — a public "
                    "build is easy to republish, and a copy on a terminated account can "
                    "trigger the 'terminated developer account' 4.3(a) variant")
    if not flagged:
        rep.add("footprint.clear", "footprint", "PASS",
                f"{len(urls)} page(s) load and name \"{name}\"; no public repo shows an old "
                "name or the source",
                ", ".join(urls))


# --------------------------------------------------------------------------- ownership

def person_tokens(s: str) -> set[str]:
    return {w for w in words(ascii_fold(s)) if len(w) > 1 and not w.isdigit()}


def same_person(a: str, b: str) -> bool:
    """Two name strings for one person. One shared token is not enough: a shared
    family name (Nguyen, Tran, Smith) says nothing about who owns what."""
    ta, tb = person_tokens(a), person_tokens(b)
    if len(ta & tb) >= 2 or (ta and ta == tb):
        return True
    # A one-word side (a handle, a bundle-id segment) must be one of the other's words.
    for one, other in ((ta, tb), (tb, ta)):
        if len(one) == 1 and next(iter(one)) in other:
            return True
    sa, sb = "".join(words(ascii_fold(a))), "".join(words(ascii_fold(b)))
    if sa and sa == sb:
        return True

    def squashed_into(tokens: set[str], s: str) -> bool:
        return 1 < len(tokens) <= 4 and any(
            "".join(p) in s for p in itertools.permutations(tokens))

    return squashed_into(ta, sb) or squashed_into(tb, sa)


def check_ownership(project: Path, holder_arg: str | None, team: str, rep: Report) -> None:
    ids: dict[str, str] = {}
    copyright_re = re.compile(r"copyright[^\n]{0,30}?(?:©|\(c\))?\s*`?(\d{4})\s+"
                              r"([A-Za-z][^`\n\"*|.,;(<\[]{2,40})", re.I)
    font_line = re.compile(r"project authors|reserved font name|open font|\bofl\b", re.I)

    def first_holder(paths) -> str | None:
        for p in paths:
            lines = read(p).splitlines()
            for i, line in enumerate(lines):
                # Prose wraps: "… Copyright is\n`2026 Luong NGUYEN`." is one statement.
                both = f"{line} {lines[i + 1] if i + 1 < len(lines) else ''}"
                m = copyright_re.search(both)
                if (m and m.start() < len(line)
                        and not font_line.search(both[m.start():m.end() + 30])):
                    return m.group(2).strip()
        return None

    # The App Store copyright field first, then store docs, then the repo LICENSE.
    for d in LISTING_DIRS:
        for p in walk(project / d, {".json"}):
            try:
                found = re.search(r'"copyright"\s*:\s*"(?:©\s*)?(?:\d{4}\s+)?([^"]+)"',
                                  read(p), re.I)
            except re.error:
                found = None
            if found:
                ids["copyright"] = found.group(1).strip()
                break
        if "copyright" in ids:
            break
    if "copyright" not in ids:
        docs = [p for d in ("docs/store", "store", "docs") for p in walk(project / d)
                if p.suffix in (".md", ".txt") and not TEXT_LICENSE.search(p.stem)]
        holder = first_holder(docs) or first_holder(
            [p for p in (project / "LICENSE", project / "LICENSE.md") if p.exists()])
        if holder:
            ids["copyright"] = holder
    emails = set()
    for d in ("lib", "docs/store", "store"):
        for p in walk(project / d, {".arb", ".dart", ".md", ".json", ".txt"}):
            if generated(p):
                continue
            emails |= set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", read(p)))
    emails = {e for e in emails if not re.search(r"noreply|example|sentry|apple\.com", e)}
    log = git(project, "shortlog", "-sne", "HEAD")
    top = re.match(r"\s*\d+\s+(.+?)\s+<", log)
    if top:
        ids["top git author"] = top.group(1)
    bid = bundle_id(project)
    if bid.count(".") >= 2:
        ids["bundle id owner"] = bid.split(".")[1]
    if holder_arg:
        ids["account holder"] = holder_arg

    if "copyright" not in ids:
        rep.add("ownership.copyright", "ownership", "SKIP",
                "no copyright line found in docs/store, store/ or LICENSE", "",
                "set the App Store copyright to whoever owns the game's IP")
        return
    # 5.2.1 turns on who submits: the account holder, or — when not given — the
    # bundle-id owner as its stand-in. The git author is evidence, not a criterion.
    publisher_key = "account holder" if "account holder" in ids else "bundle id owner"
    publisher = ids.get(publisher_key)
    evidence = "; ".join(f"{k}: {v}" for k, v in ids.items())
    if emails:
        evidence += "; contact: " + ", ".join(sorted(emails)[:3])
    if team:
        evidence += f"; team {team}"
    if publisher and not same_person(ids["copyright"], publisher):
        rep.add("ownership.publisher", "ownership", "WARN",
                f"the copyright holder ({ids['copyright']}) is not the {publisher_key} "
                f"({publisher})",
                evidence,
                "Guideline 5.2.1: apps are submitted by the IP owner or a licensee. Keep the "
                "written publishing authorization ready and say who owns the game in the "
                "review notes")
    elif publisher:
        rep.add("ownership.consistent", "ownership", "PASS",
                f"the copyright holder is the {publisher_key}", evidence)
    else:
        rep.add("ownership.unknown", "ownership", "WARN",
                "no account holder or bundle id to compare the copyright holder with",
                evidence, "pass --account-holder")


# --------------------------------------------------------------------------- binary

def uncrush_png(data: bytes) -> bytes:
    """A PNG as Xcode leaves it in an app bundle ('CgBI': raw deflate, BGRA, premultiplied)
    turned back into one Pillow reads; any other PNG comes back unchanged."""
    if data[12:16] != b"CgBI":
        return data
    import struct
    import zlib
    chunks, pos, idat = [], 8, b""
    width = height = 0
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            width, height = struct.unpack(">II", body[:8])
        if kind == b"IDAT":
            idat += body
        elif kind not in (b"CgBI", b"IEND"):
            chunks.append((kind, body))
    raw = bytearray(zlib.decompress(idat, -15))
    stride = width * 4 + 1
    for y in range(height):
        row = y * stride + 1
        for x in range(row, row + width * 4, 4):
            raw[x], raw[x + 2] = raw[x + 2], raw[x]  # BGRA → RGBA; filters work bytewise
    def chunk(kind: bytes, body: bytes) -> bytes:
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n" + b"".join(chunk(k, b) for k, b in chunks)
            + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b""))


def bundle_files(path: Path) -> tuple[str, dict[str, bytes]] | None:
    """(app folder name, {path inside the .app: bytes}) of an .ipa, a .xcarchive or an .app."""
    files: dict[str, bytes] = {}
    if path.is_file():
        import zipfile
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                m = re.match(r"Payload/([^/]+\.app)/(.+)", n)
                if m and not n.endswith("/") and z.getinfo(n).file_size < 200_000_000:
                    files[m.group(2)] = z.read(n)
                    app = m.group(1)
        return (app, files) if files else None
    apps = [path] if path.suffix == ".app" else sorted(path.glob("**/*.app"))
    if not apps:
        return None
    for p in apps[0].rglob("*"):
        if p.is_file() and p.stat().st_size < 200_000_000:
            files[str(p.relative_to(apps[0]))] = p.read_bytes()
    return apps[0].name, files


def binary_strings(data: bytes, min_len: int = 4) -> str:
    """Printable text in a compiled binary: ASCII runs and UTF-16 runs (Dart keeps both)."""
    ascii_ = re.findall(rb"[\x20-\x7e]{%d,}" % min_len, data)
    utf16 = re.findall(rb"(?:[\x20-\x7e]\x00){%d,}" % min_len, data)
    return "\n".join([s.decode("ascii") for s in ascii_]
                     + [s.decode("utf-16-le", "replace") for s in utf16])


def check_binary(project: Path, ipa: Path, name: str, sigs: dict, packs: dict,
                 rep: Report) -> None:
    """What App Review compares is the build: the files bundled (package assets too), the
    icon it ships, its Info.plist and the text compiled into it."""
    got = bundle_files(ipa) if ipa.exists() else None
    if not got:
        rep.add("binary.bundle", "binary", "WARN", f"no .app found in {ipa}", "",
                "pass the .ipa, the .xcarchive or the .app that will be uploaded")
        return
    app, files = got
    flutter = "Frameworks/App.framework/flutter_assets/"
    bundled = sorted(f for f in files if f.startswith(flutter))
    from_packages = sorted({f[len(flutter):].split("/")[1] for f in bundled
                            if f[len(flutter):].startswith("packages/")})
    rep.add("binary.bundle", "binary", "PASS",
            f"{app}: {len(files)} files, {len(bundled)} Flutter assets"
            + (f", assets from packages {', '.join(from_packages[:6])}" if from_packages else ""),
            str(ipa))

    import plistlib
    try:
        info = plistlib.loads(files.get("Info.plist", b""))
    except Exception:  # an unreadable plist is a broken build, not a 4.3 matter
        info = {}
    shown = info.get("CFBundleDisplayName") or info.get("CFBundleName") or ""
    bid = info.get("CFBundleIdentifier", "")
    problems = []
    if bid and store_apps(app_bundle_ids(project)) and bid not in store_apps(app_bundle_ids(project)):
        problems.append(f"bundle ID {bid} is not this project's")
    if shown and name and shown.lower() != name.lower():
        problems.append(f"the home-screen name is \"{shown}\", the listing's \"{name}\"")
    stale = [o for o in old_names(project, name, []) if shown and has_phrase(wtext(shown), o)]
    if stale:
        problems.append(f"the build still says the old name {', '.join(stale)}")
    rep.add("binary.info", "binary", "WARN" if problems else "PASS",
            "; ".join(problems) or f"Info.plist: {shown} ({bid})", "Info.plist",
            "build from the project being submitted, under its current name" if problems else "")

    core = set(packs["core_path_words"])
    ui = set(packs["ui_path_words"])
    found: dict[str, list[tuple[str, str]]] = {}
    for f in files:
        low = f.lower()
        for pack in packs["packs"]:
            if any(mk in low for mk in pack["markers"]["files"]):
                found.setdefault(pack["id"], []).append((path_role(f, core, ui), f))
    by_id = {p["id"]: p for p in packs["packs"]}
    order = {"FAIL": 2, "WARN": 1, "PASS": 0}
    for pid, hits in found.items():
        pack = by_id[pid]
        verdict = max((asset_verdict(pack["kind"], r) for r, _ in hits), key=order.get)
        rep.add(f"binary.stock.{pid}", "binary", verdict,
                f"the build ships {pack['name']} files ({len(hits)})",
                "; ".join(f"{f} [{r}]" for r, f in hits[:4]),
                "" if verdict == "PASS" else "a package or a forgotten folder brought them in: "
                "replace them with original art, or leave them out of the build")

    try:
        from PIL import Image
    except ImportError:
        Image = None
    icons = sorted((f for f in files if re.match(r"AppIcon[^/]*\.png$", f)),
                   key=lambda f: len(files[f]))
    if Image and icons:
        images = [(f[len(flutter):], uncrush_png(files[f])) for f in bundled
                  if Path(f).suffix.lower() in IMAGE_EXTS and "launch" not in f.lower()]
        with Image.open(io.BytesIO(uncrush_png(files[icons[-1]]))) as im:
            d, where, checked = icon_match(im, images)
        if not checked:
            rep.add("binary.icon", "binary", "SKIP", "the build bundles no image to compare "
                    "its icon with", icons[-1])
        else:
            verdict = "FAIL" if d <= 10 else "WARN" if d <= 14 else "PASS"
            rep.add("binary.icon", "binary", verdict,
                    {"FAIL": f"the shipped icon reproduces a bundled image ({where})",
                     "WARN": f"the shipped icon resembles a bundled image ({where})",
                     "PASS": f"the shipped icon is not a copy of any of {checked} bundled "
                             "images"}[verdict],
                    f"{icons[-1]} vs {where}: dHash distance {d}/64",
                    "" if verdict == "PASS" else "draw an icon of the game's own character "
                    "or mechanic")

    texts = [(f"{app}/{f}", files[f].decode("utf-8", "replace")) for f in bundled
             if Path(f).suffix.lower() in (".json", ".txt", ".arb", ".csv", ".yaml")
             and len(files[f]) < 3_000_000]
    dart = files.get("Frameworks/App.framework/App")
    if dart:
        texts.append((f"{app}/Frameworks/App.framework/App", binary_strings(dart)))
    if not scan_signature_texts(texts, sigs["signatures"], "binary", rep, "bundled file"):
        rep.add("binary.signature", "binary", "PASS",
                f"no famous-game fingerprint in the compiled code or {len(texts) - bool(dart)} "
                "bundled text files")


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="App Store 4.3 spam / 4.1 copycat preflight")
    ap.add_argument("--project", type=Path, default=Path("."))
    ap.add_argument("--mode", choices=GROUPS_BY_MODE, default="submit")
    ap.add_argument("--groups", default="", help="comma list overriding --mode")
    ap.add_argument("--docs", type=Path, nargs="*", default=[])
    ap.add_argument("--listing", type=Path, nargs="*", default=[])
    ap.add_argument("--portfolio", type=Path, default=None)
    ap.add_argument("--url", nargs="*", default=[])
    ap.add_argument("--name", default=None)
    ap.add_argument("--old-name", nargs="*", default=[])
    ap.add_argument("--team", default=None)
    ap.add_argument("--account-holder", default=None)
    ap.add_argument("--artist-id", nargs="*", default=[],
                    help="the team's App Store developer id(s), for its live apps")
    ap.add_argument("--ledger", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--countries", default=",".join(market.DEFAULT_COUNTRIES),
                    help="storefronts whose charts the market group compares with")
    ap.add_argument("--ipa", type=Path, default=None,
                    help="the .ipa, .xcarchive or .app to be uploaded: adds the binary group")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    project = args.project.resolve()
    if not project.is_dir():
        print(f"--project {project} is not a directory", file=sys.stderr)
        return 2
    groups = [g.strip() for g in args.groups.split(",") if g.strip()] or GROUPS_BY_MODE[args.mode]
    unknown = [g for g in groups if g not in ALL_GROUPS]
    if unknown:
        print(f"unknown group(s): {', '.join(unknown)}; choose from {', '.join(ALL_GROUPS)}",
              file=sys.stderr)
        return 2

    sigs = load_json("signatures.json")
    packs = load_json("stock-assets.json")
    name = app_name(project, args.name)
    olds = old_names(project, name, args.old_name)
    team = args.team or os.environ.get("TEAM_ID", "").strip() or team_id(project)
    rep = Report()
    print(f"appstore-spam-guard {VERSION} · {project.name} · {name} · groups: "
          f"{', '.join(groups)}", file=sys.stderr)

    if "design" in groups:
        check_design(project, args.docs, sigs["signatures"], packs, rep)
    if "signature" in groups:
        check_signature(project, sigs["signatures"], rep)
    if "assets" in groups:
        check_assets(project, packs, rep)
    if "icon" in groups:
        check_icon(project, rep)
    if "metadata" in groups:
        check_metadata(project, sigs, args.listing, name, olds, rep)
    if "market" in groups:
        countries = [c.strip().lower() for c in args.countries.split(",") if c.strip()]
        check_market(project, args.listing, name, args.mode == "submit" or "metadata" in groups,
                     countries or list(market.DEFAULT_COUNTRIES), args.offline, rep)
    if "portfolio" in groups:
        folder = (args.portfolio or project.parent).resolve()
        check_portfolio(project, folder, packs, rep)
        countries = [c.strip().lower() for c in args.countries.split(",") if c.strip()]
        store = market.load_store()
        live, artists, how = [], [], ""
        if team:
            data = ledger.load(args.ledger or ledger.default_path())
            approved = {e["bundle"] for e in data.get("teams", {}).get(team, {}).get("events", [])
                        if e["event"] == "approved"} | ({bundle_id(project)} - {""})
            try:
                live, artists, how = market.team_apps(store, team, countries, args.artist_id,
                                                 args.account_holder or "", sorted(approved),
                                                 args.offline,
                                                 lambda m: print(m, file=sys.stderr))
                if not args.offline:
                    market.save_store(store)
            except Exception as e:  # network trouble: say so, never pass silently
                rep.add("portfolio.store", "portfolio", "WARN",
                        f"the team's live apps could not be read ({e})", "",
                        "rerun online")
                artists = None
        if team and artists is not None:
            check_store_catalogue(project, name, live, artists, how,
                                  listing_fields(project, args.listing), args.offline, rep)
        elif not team:
            rep.add("portfolio.store", "portfolio", "SKIP",
                    "the team's live apps were not checked: no team ID (see account.team)", "",
                    "pass --team, and --artist-id or --account-holder")
        check_screenshots(project, sibling_repos(project, folder), live, args.offline, rep)
    if "footprint" in groups:
        check_footprint(project, args.url, name, olds, args.offline, rep)
    if args.ipa and "binary" not in groups:
        groups.append("binary")
    if "binary" in groups:
        if args.ipa:
            check_binary(project, args.ipa.resolve(), name, sigs, packs, rep)
        else:
            rep.add("binary.bundle", "binary", "SKIP", "no --ipa given")
    if "ownership" in groups:
        check_ownership(project, args.account_holder, team, rep)
    if "account" in groups:
        if not team:
            rep.add("account.team", "account", "WARN",
                    "no team ID in --team, $TEAM_ID, the Xcode project or "
                    "ExportOptions.plist", "",
                    "pass --team (the Apple team the app will be submitted from) so the "
                    "ledger can be checked")
        else:
            data = ledger.load(args.ledger or ledger.default_path())
            rep.extend(ledger.check_rows(data, team, bundle_id(project) or None, app=name))

    result = {"tool": "appstore-spam-guard", "version": VERSION, "mode": args.mode,
              "groups": groups, "project": str(project), "app": name,
              "old_names": olds, "team": team, "overall": rep.overall(),
              "at": market.now_iso(), "checks": rep.rows}
    if args.mode == "submit" and not args.groups and team and bundle_id(project):
        try:  # ledger.py record --event submitted keeps it with the submission
            ledger.save_last_scan(team, bundle_id(project), result)
        except OSError:
            pass
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    print(f"overall: {result['overall']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
