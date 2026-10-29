#!/usr/bin/env python3
"""Self-test for appstore-spam-guard: builds two throwaway projects and checks
that scan.py flags the clone and clears the original.

    python3 selftest.py [--keep]

`clone` repeats every 4.3(a) pattern from the Fruit Mischief case: a Suika
progression, Fluent Emoji fruit, an icon made from a bundled sprite, a listing
that names Suika, a sibling repo with the same code and art, a publisher who is
not the copyright holder, and a team with an open 4.3 — and against a small
fixture App Store index, a charting game's name, its icon and its description.
`original` has none of them. The PNGs are drawn here with the stdlib and the
index is written here too, so the repo carries no fixture binaries and the test
never touches the network. Exit 0 when every expectation holds, 1 otherwise.
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

PBX = "DEVELOPMENT_TEAM = {team};\nPRODUCT_BUNDLE_IDENTIFIER = {bundle};\n"
PLIST = ("<plist><dict><key>CFBundleDisplayName</key><string>{name}</string>"
         "</dict></plist>\n")


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


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
        if any(c["id"] == "market.crowded-name" for c in r["checks"]):
            errors.append("original: market.crowded-name should not appear")
        if r["overall"] != ("PASS" if HAVE_PIL else "WARN"):
            errors.append(f"original: overall expected PASS, got {r['overall']}")

        d = scan(orig, ledger_path, "--mode", "design")
        errors += expect(d, {"design.clean": "PASS"}, "original design")
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
