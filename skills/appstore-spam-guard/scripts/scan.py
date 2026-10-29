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

VERSION = "1.1.0"

GROUPS_BY_MODE = {
    "design": ["design"],
    "build": ["signature", "assets", "icon", "market"],
    "submit": ["signature", "assets", "icon", "metadata", "market", "portfolio",
               "footprint", "ownership", "account"],
}
ALL_GROUPS = GROUPS_BY_MODE["submit"] + ["design"]

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


def wtext(text: str) -> str:
    return " " + " ".join(words(text)) + " "


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


def code_files(project: Path):
    seen = set()
    for root in CODE_ROOTS:
        for p in walk(project / root, CODE_EXTS):
            if generated(p) or "xcassets" in str(p) or p in seen:
                continue
            seen.add(p)
            yield p


def pbx_values(project: Path, key: str) -> list[str]:
    vals: list[str] = []
    for pbx in project.glob("ios/*.xcodeproj/project.pbxproj"):
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
    return ""


def bundle_id(project: Path) -> str:
    ids = [v for v in pbx_values(project, "PRODUCT_BUNDLE_IDENTIFIER")
           if not v.lower().endswith("tests")]
    return sorted(set(ids), key=len)[0] if ids else ""


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


def check_assets(project: Path, packs: dict, rep: Report) -> None:
    core = set(packs["core_path_words"])
    ui = set(packs["ui_path_words"])
    path_re = re.compile(r"`([^`]*[/*.][^`]*)`|((?:assets|lib|ios|images|img)/[\w./*{},\-]+)")
    found: dict[str, list[tuple[str, str, str]]] = {}  # pack id → (role, evidence, path)

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

    for p in walk(project):
        if "xcassets" in str(p):
            continue
        low = rel(p, project).lower()
        for pack in packs["packs"]:
            if any(m in low for m in pack["markers"]["files"]):
                role = path_role(str(p.parent.relative_to(project)), core, ui)
                found.setdefault(pack["id"], []).append((role, rel(p, project), ""))

    if not found:
        rep.add("assets.none", "assets", "PASS",
                "no stock art pack credited or found by file name")
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
    if not cands:
        for d in ("assets/icon", "assets/icons/app", "store", "docs/store", "assets"):
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
    for p in walk(project / "assets", IMAGE_EXTS):
        stem = p.stem.lower()
        if (re.search(r"app[_-]?icon|launcher[_-]?icon|icon[_-]?(1024|master|source)", stem)
                or (p.parent.name.lower() in ("icon", "app_icon", "launcher")
                    and stem.startswith("icon"))):
            srcs.add(p.resolve())
    return srcs


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

    with Image.open(icon) as im:
        base = im.convert("RGB")
    w, h = base.size
    bg = base.getpixel((max(1, w // 64), max(1, h // 64)))
    # Square crops at several sizes, centred and nudged a little each way: an
    # icon rarely places the sprite dead centre (a drop shadow shifts it too).
    crops = []
    for frac in (1.0, 0.9, 0.8, 0.7, 0.65, 0.6, 0.55, 0.5):
        side = int(min(w, h) * frac)
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            left = (w - side) // 2 + dx * side // 25
            top = (h - side) // 2 + dy * side // 25
            if left < 0 or top < 0 or left + side > w or top + side > h:
                continue
            crops.append(dhash(base.crop((left, top, left + side, top + side))))

    best = (65, "")
    checked = 0
    skipped = icon_sources(project)
    for p in walk(project / "assets", IMAGE_EXTS):
        if "launch" in str(p).lower() or p.resolve() in skipped:
            continue
        try:
            with Image.open(p) as im:
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
        if d < best[0]:
            best = (d, rel(p, project))
        if checked >= 600:
            break

    d, where = best
    note = (f"; icon sources skipped: {', '.join(sorted(rel(s, project) for s in skipped))}"
            if skipped else "")
    if checked == 0:
        rep.add("icon.bundled", "icon", "PASS",
                "no bundled images to compare the icon with", rel(icon, project),
                "still judge the icon's subject by eye (references/checks.md J3)")
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
    for d in ("assets", "ios/Runner/Assets.xcassets/AppIcon.appiconset"):
        for p in walk(root / d):
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
    for p in walk(root / "lib", {".dart"}):
        if not generated(p):
            code[rel(p, root)] = shingles(read(p))
    return {"files": files, "code": code}


def check_portfolio(project: Path, portfolio: Path, packs: dict, rep: Report) -> None:
    core = set(packs["core_path_words"])
    me = project.resolve()
    siblings = [d for d in sorted(portfolio.iterdir()) if d.is_dir() and d.resolve() != me
                and ((d / "pubspec.yaml").exists() or list(d.glob("*.xcodeproj"))
                     or list(d.glob("ios/*.xcodeproj")))]
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
    ap.add_argument("--ledger", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--countries", default=",".join(market.DEFAULT_COUNTRIES),
                    help="storefronts whose charts the market group compares with")
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
        check_portfolio(project, (args.portfolio or project.parent).resolve(), packs, rep)
    if "footprint" in groups:
        check_footprint(project, args.url, name, olds, args.offline, rep)
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
            rep.extend(ledger.check_rows(data, team, bundle_id(project) or None))

    result = {"tool": "appstore-spam-guard", "version": VERSION, "mode": args.mode,
              "groups": groups, "project": str(project), "app": name,
              "old_names": olds, "team": team, "overall": rep.overall(),
              "checks": rep.rows}
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
