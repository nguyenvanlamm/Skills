#!/usr/bin/env python3
"""Self-test for appstore-spam-guard: builds two throwaway projects and checks
that scan.py flags the clone and clears the original.

    python3 selftest.py [--keep]

`clone` repeats every 4.3(a) pattern from the Fruit Mischief case: a Suika
progression, Fluent Emoji fruit, an icon made from a bundled sprite, a listing
that names Suika, a sibling repo with the same code and art, a publisher who is
not the copyright holder, and a team with an open 4.3 — and against a small
fixture App Store index, a charting game's name, its icon and its description.
`original` has none of them. Five small projects cover the blind spots of
v1.1.0: a progression drawn as emoji text, emoji on badges only, an icon cut
from a sprite kept outside assets/, one game under several bundle IDs (and on
the ledger under another one), and a plain sudoku. The PNGs are drawn here with
the stdlib and the index is written here too, so the repo carries no fixture
binaries and the test never touches the network. Exit 0 when every expectation
holds, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAN = HERE / "scan.py"
LEDGER = HERE / "ledger.py"
sys.path.insert(0, str(HERE))
import market  # noqa: E402  (sibling module, path set above)

try:
    import PIL  # noqa: F401
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


# ---------------------------------------------------------------- tiny PNG writer

def write_png(path: Path, w: int, h: int, pixel) -> None:
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.extend(pixel(x, y))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                     + chunk(b"IEND", b""))


def melon(x: float, y: float, size: int = 256) -> tuple[int, int, int, int]:
    """A watermelon-ish disc: green rind, red flesh, dark seeds."""
    c = size / 2
    d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
    if d > size * 0.43:
        return (0, 0, 0, 0)
    if d > size * 0.36:
        return (60, 150, 60, 255)
    if ((int(x) // 18) + (int(y) // 18)) % 5 == 0 and d < size * 0.3:
        return (30, 20, 30, 255)
    return (225, 50, 70, 255)


def clone_icon(x: int, y: int, size: int = 512) -> tuple[int, int, int, int]:
    scale = 256 / (size * 0.62)
    u, v = (x - size * 0.19) * scale, (y - size * 0.19) * scale
    if 0 <= u < 256 and 0 <= v < 256:
        p = melon(u, v)
        if p[3]:
            return p
    return (70, 35, 95, 255)


def blob(x: int, y: int) -> tuple[int, int, int, int]:
    d = ((x - 64) ** 2 + (y - 64) ** 2) ** 0.5
    return (60, 110, 220, 255) if d < 50 else (0, 0, 0, 0)


def original_icon(x: int, y: int) -> tuple[int, int, int, int]:
    return (250, 250, 240, 255) if (x + y) // 40 % 2 else (240, 140, 40, 255)


# ---------------------------------------------------------------- fixtures

CLONE_DART = """// Plays like Suika: drop fruit, merge pairs.
const fruits = ['cherry', 'strawberry', 'grape', 'orange', 'persimmon', 'apple',
    'pear', 'peach', 'pineapple', 'melon', 'watermelon'];

class Bin {
  final List<int> tiers = [];
  int score = 0;

  void drop(int tier) {
    tiers.add(tier);
    for (var i = 0; i < tiers.length - 1; i++) {
      if (tiers[i] == tiers[i + 1]) {
        final merged = tiers[i] + 1;
        tiers.removeAt(i + 1);
        tiers[i] = merged;
        score += merged * 3;
      }
    }
  }

  bool get full => tiers.length > 40;
}
"""

ORIGINAL_DART = """// Pebble Pals: stack stones until the mountain wakes up.
const stones = ['pebble', 'shard', 'cobble', 'stone', 'rock', 'boulder', 'crag'];

class Mountain {
  final Map<String, int> layers = {};

  int wake(String stone) => layers.update(stone, (n) => n + 2, ifAbsent: () => 1);
}
"""

HIT_DESC = ("Drop juicy fruit into the jar and watch matching pairs merge into bigger, "
            "sweeter fruit. Plan every drop, chain combos for huge scores and climb the "
            "weekly leaderboard with friends. Fruit Drop Saga is free to play with daily "
            "challenges, cute themes and new fruit every season.")

EMOJI_DART = """// Juicy Stack: drop pieces into the jar; two alike join into the next one.
const pieces = ['🍒', '🍓', '🍇', '🍊', '🍎', '🍐', '🍑', '🍍', '🍈', '🍉'];

Widget piece(int tier) => Text(pieces[tier], style: TextStyle(fontSize: 24.0 + tier * 8));
"""

BADGES_DART = """// Achievement cards: the only emoji in the game.
class Badge {
  const Badge(this.title, this.icon);
  final String title;
  final String icon;
}

const badges = [
  Badge('First stack', '🏅'),
  Badge('Ten stacks', '🏆'),
  Badge('Mountain wakes', '⭐'),
];
"""

SUDOKU_LISTING = {
    "name": "Grid Calm",
    "subtitle": "Relaxing number puzzles",
    "keywords": "sudoku,numbers,logic,classic",
    "description": "Classic 9x9 sudoku with four difficulty levels, notes, hints and daily "
                   "challenges. Fill every row, column and box with the numbers 1 to 9 before "
                   "your two free slots run out.",
}
ASO_NOTES = ("# Listing\n\nRelaxing number puzzles for short breaks.\n\n## ASO notes\n\n"
             "| Keyword | Why |\n|---|---|\n| nonogram | kept out: another puzzle type |\n\n"
             "We leave \"minesweeper\" out on purpose.\n")

PBX = "DEVELOPMENT_TEAM = {team};\nPRODUCT_BUNDLE_IDENTIFIER = {bundle};\n"
PLIST = ("<plist><dict><key>CFBundleDisplayName</key><string>{name}</string>"
         "</dict></plist>\n")


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def pbxproj(team: str, targets: list[tuple[str, str, list[tuple[str, str]]]]) -> str:
    """A project.pbxproj in Xcode's own layout: (target, product type, [(config, bundle)])."""
    nums = iter(range(1, 1000))
    natives, configs, lists = [], [], []
    for name, ptype, builds in targets:
        tid, lid = f"{next(nums):024X}", f"{next(nums):024X}"
        cids = []
        for config, bundle in builds:
            cids.append(f"{next(nums):024X}")
            configs.append(f"\t\t{cids[-1]} /* {config} */ = {{\n\t\t\tisa = XCBuildConfiguration;\n"
                           f"\t\t\tbuildSettings = {{\n\t\t\t\tDEVELOPMENT_TEAM = {team};\n"
                           f"\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {bundle};\n\t\t\t}};\n"
                           f"\t\t\tname = \"{config}\";\n\t\t}};\n")
        lists.append(f"\t\t{lid} /* Build configuration list for PBXNativeTarget \"{name}\" */ = {{\n"
                     "\t\t\tisa = XCConfigurationList;\n\t\t\tbuildConfigurations = (\n"
                     + "".join(f"\t\t\t\t{c} /* config */,\n" for c in cids)
                     + "\t\t\t);\n\t\t\tdefaultConfigurationName = Release;\n\t\t};\n")
        natives.append(f"\t\t{tid} /* {name} */ = {{\n\t\t\tisa = PBXNativeTarget;\n"
                       f"\t\t\tbuildConfigurationList = {lid};\n\t\t\tname = {name};\n"
                       f"\t\t\tproductType = \"{ptype}\";\n\t\t}};\n")
    return ("// !$*UTF8*$!\n{\n\tobjects = {\n\n"
            "/* Begin PBXNativeTarget section */\n" + "".join(natives)
            + "/* End PBXNativeTarget section */\n\n/* Begin XCBuildConfiguration section */\n"
            + "".join(configs) + "/* End XCBuildConfiguration section */\n\n"
            "/* Begin XCConfigurationList section */\n" + "".join(lists)
            + "/* End XCConfigurationList section */\n\t};\n}\n")


def build_clone(parent: Path) -> Path:
    root = parent / "clone"
    write(root, "pubspec.yaml", "name: clone\n")
    write(root, "lib/main.dart", CLONE_DART)
    arb = {f"fruit{n.title()}": n.title() for n in
           ["cherry", "strawberry", "grape", "orange", "persimmon", "apple", "pear",
            "peach", "pineapple", "melon", "watermelon"]}
    arb["creditsArt"] = "Fruit art: Fluent Emoji — Microsoft (MIT)"
    write(root, "lib/l10n/app_en.arb", json.dumps(arb, indent=2))
    write(root, "assets/CREDITS.md",
          "| Asset | Type | Files |\n|---|---|---|\n"
          "| Fluent Emoji (11 fruits) | sprite | `assets/fruits/*.png` |\n"
          "| Kenney Interface Sounds | audio | `assets/audio/sfx/*.ogg` |\n")
    write_png(root / "assets/fruits/watermelon.png", 256, 256, melon)
    write_png(root / "ios/Runner/Assets.xcassets/AppIcon.appiconset/"
                     "Icon-App-1024x1024@1x.png", 512, 512, clone_icon)
    write(root, "ios/Runner.xcodeproj/project.pbxproj",
          PBX.format(team="TEAMTEST01", bundle="com.example.clone"))
    write(root, "ios/Runner/Info.plist", PLIST.format(name="Fruit Drop"))
    write(root, "store/listing.json", json.dumps({
        "name": "Fruit Drop",
        "subtitle": "Merge fruit like Suika",
        "keywords": "watermelon,merge fruit,drop",
        "description": "Merge from cherry to watermelon. A clone of the famous game. "
                       + HIT_DESC,
    }))
    write(root, "LICENSE", "Copyright (c) 2026 Alice Example\n")
    write(root, "DESIGN.md",
          "| # | Aspect | Reference | Ours | Verdict |\n|---|---|---|---|---|\n"
          "| 1 | Chain | Suika | cherry, strawberry, grape, orange, persimmon, apple, "
          "pear, peach, pineapple, melon, watermelon | same |\n"
          "| 2 | Art | emoji | Fluent Emoji fruit | close |\n")
    # A sibling app with the same code and the same main art.
    sib = parent / "sibling"
    write(sib, "pubspec.yaml", "name: sibling\n")
    write(sib, "lib/main.dart", CLONE_DART)
    (sib / "assets/fruits").mkdir(parents=True, exist_ok=True)
    shutil.copy(root / "assets/fruits/watermelon.png", sib / "assets/fruits/watermelon.png")
    return root


def build_original(parent: Path) -> Path:
    root = parent / "original"
    write(root, "pubspec.yaml", "name: original\n")
    write(root, "lib/main.dart", ORIGINAL_DART)
    write(root, "lib/l10n/app_en.arb", json.dumps(
        {"stonePebble": "Pebble", "stoneBoulder": "Boulder", "appTitle": "Pebble Pals"}))
    write(root, "assets/CREDITS.md",
          "| Asset | Type | Files |\n|---|---|---|\n"
          "| Kenney Interface Sounds | audio | `assets/audio/sfx/*.ogg` |\n")
    write_png(root / "assets/creatures/blob.png", 128, 128, blob)
    write_png(root / "ios/Runner/Assets.xcassets/AppIcon.appiconset/"
                     "Icon-App-1024x1024@1x.png", 512, 512, original_icon)
    write(root, "ios/Runner.xcodeproj/project.pbxproj",
          PBX.format(team="TEAMTEST02", bundle="com.example.original"))
    write(root, "ios/Runner/Info.plist", PLIST.format(name="Pebble Pals"))
    write(root, "store/listing.json", json.dumps({
        "name": "Pebble Pals",
        "subtitle": "Stack stones, wake the mountain",
        "keywords": "stones,stacking,strategy,mountain",
        "description": "Every run starts with a choice of three charms. Stack river "
                       "pebbles on a sleeping mountain; each charm bends the rules of the "
                       "stack until the mountain stirs and the next run begins.",
    }))
    write(root, "LICENSE", "Copyright (c) 2026 Alice Example\n")
    write(root, "DESIGN.md",
          "| # | Aspect | Reference | Ours | Verdict |\n|---|---|---|---|---|\n"
          "| 1 | Chain | cherry, strawberry, grape, orange, persimmon, apple, pear, "
          "peach, pineapple, melon, watermelon | pebble to crag | different |\n")
    return root


def build_blind_spots(parent: Path) -> dict[str, Path]:
    """One small project per blind spot of v1.1.0, each in a folder of its own."""
    icon = "ios/Runner/Assets.xcassets/AppIcon.appiconset/Icon-App-1024x1024@1x.png"
    roots = {k: parent / k / k for k in ("emoji", "badges", "art", "flavors", "sudoku")}
    for k, root in roots.items():
        write(root, "pubspec.yaml", f"name: {k}\n")
    write(roots["emoji"], "lib/main.dart", EMOJI_DART)
    write(roots["badges"], "lib/badges.dart", BADGES_DART)
    # The icon is the main sprite, which lives in images/ — listed in the pubspec.
    write(roots["art"], "pubspec.yaml", "name: art\nflutter:\n  assets:\n    - images/pieces/\n")
    write_png(roots["art"] / "images/pieces/melon.png", 256, 256, melon)
    write_png(roots["art"] / icon, 512, 512, clone_icon)
    # One game as three App Store apps; a .dev flavor, tests and a widget ride along. Its
    # icon is the sprite in art/, which the pubspec does not list: not in the binary.
    seasons = "com.example.mergeseasons"
    write(roots["flavors"], "ios/Runner.xcodeproj/project.pbxproj", pbxproj("TEAMTEST03", [
        ("Runner", "com.apple.product-type.application",
         [("Debug", seasons), ("Release", seasons), ("Profile", seasons),
          ("Debug-dev", f"{seasons}.dev"), ("Release-dev", f"{seasons}.dev"),
          ("Release-halloween", f"{seasons}.halloween"),
          ("Release-christmas", f"{seasons}.christmas")]),
        ("RunnerTests", "com.apple.product-type.bundle.unit-test",
         [("Debug", f"{seasons}.RunnerTests")]),
        ("SeasonWidget", "com.apple.product-type.app-extension",
         [("Release", f"{seasons}.SeasonWidget")]),
    ]))
    write(roots["flavors"], "ios/Runner/Info.plist", PLIST.format(name="Merge Seasons"))
    write_png(roots["flavors"] / "art/melon.png", 256, 256, melon)
    write_png(roots["flavors"] / icon, 512, 512, clone_icon)
    write(roots["sudoku"], "ios/Runner/Info.plist", PLIST.format(name="Grid Calm"))
    write(roots["sudoku"], "store/listing.json", json.dumps(SUDOKU_LISTING))
    write(roots["sudoku"], "store/aso-listing.md", ASO_NOTES)
    return roots


def build_store(cache: Path, clone_icon_png: Path) -> None:
    """A tiny App Store index: one charting game the clone copies, five more that share
    its genre-word name, and nothing like the original. Fresh, so --offline uses it."""
    def app(i: int, name: str, **kw) -> dict:
        return {"id": str(900000000 + i), "name": name, "names": [name], "seller": "Hit Studio",
                "bundle": f"com.hit.app{i}", "url": f"https://apps.apple.com/us/app/id{i}",
                "icon": f"https://fixture.invalid/{i}.png", "description": "", "charts": [],
                "english": True, **kw}
    apps = [app(1, "Fruit Drop™: Merge Saga", charts=["us/free/Puzzle#3"], best=3,
                description=HIT_DESC)]
    apps += [app(i, n) for i, n in enumerate(
        ["Fruit Drop Party", "Super Fruit Drop", "Fruit Drop Pop", "Fruit Drop Kingdom",
         "Tiny Fruit Drop"], 2)]
    store = {"version": 1, "searches": {}, "apps": {a["id"]: a for a in apps},
             "charts": {"built": market.now_iso(), "countries": list(market.DEFAULT_COUNTRIES),
                        "fetched": 1, "failed": []}}
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "store.json").write_text(json.dumps(store), encoding="utf-8")
    if HAVE_PIL:
        from PIL import Image
        with Image.open(clone_icon_png) as im:
            hit_print = market.icon_print(im)
        (cache / "icons.json").write_text(
            json.dumps({"https://fixture.invalid/1.png": hit_print}), encoding="utf-8")


# ---------------------------------------------------------------- run

def scan(project: Path, ledger_path: Path, *extra: str) -> dict:
    out = project.parent / f"{project.name}-scan.json"
    cmd = [sys.executable, str(SCAN), "--project", str(project), "--ledger",
           str(ledger_path), "--out", str(out), *extra]
    env = {**os.environ, "APPSTORE_SPAM_GUARD_CACHE": str(ledger_path.parent / "cache")}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise SystemExit(f"scan.py exited {proc.returncode}:\n{proc.stderr}")
    return json.loads(out.read_text(encoding="utf-8"))


def expect(result: dict, wanted: dict[str, str], label: str) -> list[str]:
    got = {r["id"]: r["verdict"] for r in result["checks"]}
    errors = []
    for id_, verdict in wanted.items():
        if got.get(id_) != verdict:
            errors.append(f"{label}: {id_} expected {verdict}, got {got.get(id_)}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="keep the fixtures and print where")
    args = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="spam-guard-selftest-"))
    errors: list[str] = []
    try:
        ledger_path = tmp / "ledger.json"
        rec = subprocess.run(
            [sys.executable, str(LEDGER), "--ledger", str(ledger_path), "record",
             "--team", "TEAMTEST01", "--app", "Other Game", "--bundle", "com.example.other",
             "--event", "rejected", "--guideline", "4.3(a)", "--extended-review",
             "--date", "2026-10-01"], capture_output=True, text=True)
        if rec.returncode != 0:
            errors.append(f"ledger record failed: {rec.stderr}")

        clone_parent = tmp / "clone-world"
        clone = build_clone(clone_parent)
        build_store(tmp / "cache", clone / "ios/Runner/Assets.xcassets/AppIcon.appiconset/"
                                           "Icon-App-1024x1024@1x.png")
        r = scan(clone, ledger_path, "--mode", "submit", "--offline",
                 "--account-holder", "Bob Other")
        wanted = {
            "signature.suika.chain": "FAIL",
            "signature.suika.alias": "WARN",
            "assets.stock.fluent-emoji": "FAIL",
            "assets.stock.kenney": "PASS",
            "metadata.suika.alias": "FAIL",
            "metadata.suika.phrase": "FAIL",
            "metadata.suika.term": "WARN",
            "metadata.generic-name": "WARN",
            "metadata.copycat-wording": "WARN",
            "metadata.saturated-genre": "WARN",
            "portfolio.bundle-ids": "PASS",
            "portfolio.sibling": "FAIL",
            "footprint.none": "SKIP",
            "ownership.publisher": "WARN",
            "account.open-4.3": "FAIL",
            "market.index": "PASS",
            "market.name": "FAIL",
            "market.crowded-name": "WARN",
            "market.icon": "FAIL" if HAVE_PIL else "WARN",
            "market.wording": "FAIL",
        }
        wanted["icon.bundled" if HAVE_PIL else "icon.unverified"] = \
            "FAIL" if HAVE_PIL else "WARN"
        errors += expect(r, wanted, "clone")
        if r["overall"] != "FAIL":
            errors.append(f"clone: overall expected FAIL, got {r['overall']}")

        d = scan(clone, ledger_path, "--mode", "design")
        errors += expect(d, {"design.suika.chain": "FAIL",
                             "design.stock.fluent-emoji": "WARN"}, "clone design")

        orig_parent = tmp / "original-world"
        orig = build_original(orig_parent)
        r = scan(orig, ledger_path, "--mode", "submit", "--offline",
                 "--account-holder", "Alice Example")
        wanted = {
            "signature.none": "PASS",
            "assets.stock.kenney": "PASS",
            "metadata.clean": "PASS",
            "portfolio.bundle-ids": "PASS",
            "portfolio.none": "SKIP",
            "footprint.none": "SKIP",
            "ownership.consistent": "PASS",
            "account.ledger": "PASS",
            "market.index": "PASS",
            "market.name": "PASS",
            "market.listing-names": "PASS",
            "market.icon": "PASS" if HAVE_PIL else "WARN",
            "market.wording": "PASS",
        }
        wanted["icon.bundled" if HAVE_PIL else "icon.unverified"] = \
            "PASS" if HAVE_PIL else "WARN"
        errors += expect(r, wanted, "original")
        for id_ in ("market.crowded-name", "assets.emoji-glyphs", "metadata.saturated-genre"):
            if any(c["id"] == id_ for c in r["checks"]):
                errors.append(f"original: {id_} should not appear")
        if r["overall"] != ("PASS" if HAVE_PIL else "WARN"):
            errors.append(f"original: overall expected PASS, got {r['overall']}")

        d = scan(orig, ledger_path, "--mode", "design")
        errors += expect(d, {"design.clean": "PASS"}, "original design")

        # The blind spots of v1.1.0, each of which passed it.
        spots = build_blind_spots(tmp / "spots")
        r = scan(spots["emoji"], ledger_path, "--groups", "signature,assets")
        errors += expect(r, {"signature.suika.chain": "FAIL", "assets.emoji-glyphs": "FAIL"},
                         "emoji")
        r = scan(spots["badges"], ledger_path, "--groups", "signature,assets")
        errors += expect(r, {"signature.none": "PASS", "assets.emoji-glyphs": "WARN"}, "badges")
        r = scan(spots["art"], ledger_path, "--groups", "icon")
        errors += expect(r, {"icon.bundled": "FAIL"} if HAVE_PIL
                         else {"icon.unverified": "WARN"}, "art outside assets/")
        rec = subprocess.run(
            [sys.executable, str(LEDGER), "--ledger", str(ledger_path), "record",
             "--team", "TEAMTEST03", "--app", "Merge Seasons", "--bundle",
             "com.example.seasons.merge", "--event", "approved", "--date", "2026-09-01"],
            capture_output=True, text=True)
        if rec.returncode != 0:
            errors.append(f"ledger record failed: {rec.stderr}")
        r = scan(spots["flavors"], ledger_path, "--groups", "icon,portfolio,account")
        wanted = {"portfolio.bundle-ids": "FAIL", "account.same-app": "WARN"}
        wanted["icon.bundled" if HAVE_PIL else "icon.unverified"] = \
            "SKIP" if HAVE_PIL else "WARN"
        errors += expect(r, wanted, "flavors")
        ev = next((c["evidence"] for c in r["checks"] if c["id"] == "portfolio.bundle-ids"), "")
        if not ("halloween" in ev and "christmas" in ev) or any(
                x in ev for x in (".dev", "RunnerTests", "SeasonWidget")):
            errors.append(f"flavors: bundle-ids evidence should be the three store apps: {ev}")
        r = scan(spots["sudoku"], ledger_path, "--groups", "metadata")
        errors += expect(r, {"metadata.saturated-genre": "WARN"}, "sudoku")
        ev = next((c["evidence"] for c in r["checks"] if c["id"] == "metadata.saturated-genre"), "")
        if any(x in ev for x in ("slots", "nonogram", "minesweeper")):
            errors.append(f"sudoku: a description's 'slots' or an ASO note counted: {ev}")
    finally:
        if args.keep:
            print(f"fixtures kept in {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    if errors:
        print("selftest FAILED", *errors, sep="\n  ")
        return 1
    print(f"selftest passed (Pillow {'present' if HAVE_PIL else 'absent: icon check skipped'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
