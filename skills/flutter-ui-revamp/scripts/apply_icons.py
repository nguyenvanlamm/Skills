#!/usr/bin/env python3
"""Bulk-replace icon references across a Flutter project's lib/.

Dry run is the DEFAULT. Nothing is written without `--apply`, and `--apply`
without `--yes` asks for confirmation. Show the diff to the user before writing;
a silent bulk edit across 40 files is how a "UI revamp" turns into a bisect
session.

    # 1. see what would change
    python3 apply_icons.py --project . --map phosphor.json

    # 2. write it
    python3 apply_icons.py --project . --map phosphor.json --apply

Mapping file — either a flat object:

    { "Icons.home": "PhosphorIcons.house()", "Icons.search": "PhosphorIcons.magnifyingGlass()" }

or the full form, which is preferred because it carries the import:

    {
      "import": "package:phosphor_flutter/phosphor_flutter.dart",
      "map": {
        "Icons.home":   "PhosphorIcons.house()",
        "Icons.delete": { "to": "PhosphorIcons.trash()", "import": "package:phosphor_flutter/phosphor_flutter.dart" }
      }
    }

Matches inside comments and string literals are never touched — see dart_lex.py.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dart_lex  # noqa: E402

RE_ICON = re.compile(r"\b(?:Icons|CupertinoIcons)\.([A-Za-z0-9_]+)")
RE_IMPORT = re.compile(r"^\s*import\s+['\"]", re.M)
GENERATED = (".g.dart", ".freezed.dart", ".gr.dart", ".gen.dart")


def log(msg: str) -> None:
    print(f"[icons] {msg}", file=sys.stderr)


def load_map(path: Path) -> Tuple[Dict[str, str], Dict[str, str], str | None]:
    """Return (replacements, per_key_imports, default_import)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log(f"FATAL: mapping file not found: {path}")
        raise SystemExit(2)
    except json.JSONDecodeError as exc:
        log(f"FATAL: mapping file is not valid JSON: {exc}")
        raise SystemExit(2)

    default_import = data.get("import") if isinstance(data, dict) else None
    raw = data.get("map") if isinstance(data, dict) and "map" in data else data
    if not isinstance(raw, dict):
        log("FATAL: mapping must be an object of {source: replacement}.")
        raise SystemExit(2)

    repl: Dict[str, str] = {}
    imports: Dict[str, str] = {}
    for key, value in raw.items():
        if key in ("import", "map"):
            continue
        src = key if "." in key else f"Icons.{key}"
        if isinstance(value, str):
            repl[src] = value
            if default_import:
                imports[src] = default_import
        elif isinstance(value, dict) and value.get("to"):
            repl[src] = value["to"]
            imp = value.get("import") or default_import
            if imp:
                imports[src] = imp
        else:
            log(f"WARN: skipping malformed mapping entry for {key!r}")
    return repl, imports, default_import


def insert_import(src: str, uri: str) -> str:
    """Add `import 'uri';` in the right place, or return src unchanged."""
    if re.search(rf"""import\s+['"]{re.escape(uri)}['"]""", src):
        return src
    line = f"import '{uri}';"
    matches = list(RE_IMPORT.finditer(src))
    if matches:
        last = matches[-1]
        eol = src.find("\n", last.start())
        eol = len(src) if eol == -1 else eol
        return src[:eol] + "\n" + line + src[eol:]
    # No imports yet: go after any library/part-of directive, else at the top.
    m = re.search(r"^\s*(library|part of)\b.*?;\s*$", src, re.M)
    if m:
        return src[: m.end()] + "\n\n" + line + src[m.end():]
    return line + "\n\n" + src


RE_CONST = re.compile(r"\bconst\s+")


def const_anchor(code: str, at: int) -> Optional[int]:
    """Offset of the `const` keyword governing the expression at `at`, if any.

    `Icons.home` is a const IconData, so `const Icon(Icons.home)` compiles.
    `PhosphorIcons.house()` is a method call, so the same line after a naive
    replacement does not — the analyzer reports "Arguments of a constant
    creation must be constant expressions" across every touched file. Look back
    for the nearest `const` not separated from the match by a statement break.
    """
    window_start = max(0, at - 400)
    window = code[window_start:at]
    cut = max(window.rfind(";"), window.rfind("}"))
    if cut != -1:
        window = window[cut + 1:]
        window_start += cut + 1
    last = None
    for m in RE_CONST.finditer(window):
        last = m
    return window_start + last.start() if last else None


def rewrite(src: str, repl: Dict[str, str], imports: Dict[str, str], fix_const: bool
            ) -> Tuple[str, Counter, Counter, List[int]]:
    """Apply replacements to code positions only.

    Returns (new_src, applied, unmapped, const_hazard_lines).
    """
    code, _ = dart_lex.strip(src)
    applied: Counter = Counter()
    unmapped: Counter = Counter()
    edits: List[Tuple[int, int, str]] = []
    const_cuts: set = set()
    hazards: List[int] = []

    for m in RE_ICON.finditer(code):
        token = m.group(0)
        if token not in repl:
            unmapped[token] += 1
            continue
        replacement = repl[token]
        edits.append((m.start(), m.end(), replacement))
        applied[token] += 1
        if "(" in replacement:  # a call, not a const IconData
            anchor = const_anchor(code, m.start())
            if anchor is not None:
                hazards.append(dart_lex.line_of(src, m.start()))
                if fix_const:
                    end = anchor + len(RE_CONST.match(code, anchor).group(0))
                    const_cuts.add((anchor, end))

    if not edits:
        return src, applied, unmapped, hazards

    merged = sorted(edits + [(a, b, "") for a, b in const_cuts])
    out, cursor = [], 0
    for start, end, text in merged:
        if start < cursor:
            continue  # overlapping edit; the earlier one wins
        out.append(src[cursor:start])
        out.append(text)
        cursor = end
    out.append(src[cursor:])
    new = "".join(out)

    for uri in sorted({imports[t] for t in applied if t in imports}):
        new = insert_import(new, uri)
    return new, applied, unmapped, hazards


def main() -> int:
    ap = argparse.ArgumentParser(description="Bulk icon replacement for Flutter lib/.")
    ap.add_argument("--project", default=".", help="Flutter project root")
    ap.add_argument("--map", required=True, help="JSON mapping file")
    ap.add_argument("--dir", default="lib", help="Directory to walk (default: lib)")
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    ap.add_argument("--dry-run", action="store_true", help="Explicit dry run (the default)")
    ap.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    ap.add_argument("--fix-const", action="store_true",
                    help="Drop the governing `const` where a callable replacement lands in a "
                         "const context (otherwise the analyzer rejects the file)")
    ap.add_argument("--context", type=int, default=2, help="Diff context lines")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    root = project / args.dir
    if not root.is_dir():
        log(f"FATAL: {root} does not exist.")
        return 2
    if args.dry_run:
        args.apply = False

    repl, imports, _ = load_map(Path(args.map))
    log(f"{len(repl)} mapping(s) loaded; walking {root}")

    changed: List[Tuple[Path, str, str]] = []
    total_applied: Counter = Counter()
    total_unmapped: Counter = Counter()
    const_hazards: List[str] = []

    for path in sorted(root.rglob("*.dart")):
        if path.name.endswith(GENERATED):
            continue
        try:
            src = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            log(f"WARN: cannot read {path}: {exc}")
            continue
        new, applied, unmapped, hazards = rewrite(src, repl, imports, args.fix_const)
        total_applied.update(applied)
        total_unmapped.update(unmapped)
        const_hazards += [f"{path.relative_to(project)}:{ln}" for ln in hazards]
        if new != src:
            changed.append((path, src, new))

    if not changed:
        log("No occurrences matched. Nothing to do.")
    for path, old, new in changed:
        rel = path.relative_to(project)
        diff = difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{rel}", tofile=f"b/{rel}", n=args.context,
        )
        sys.stdout.writelines(diff)

    print("", file=sys.stderr)
    log(f"files touched: {len(changed)}")
    if total_applied:
        log("replacements:")
        for token, n in total_applied.most_common():
            print(f"        {token:<38} -> {repl[token]:<38} x{n}", file=sys.stderr)
    if total_unmapped:
        log(f"UNMAPPED — {len(total_unmapped)} icon(s) have no entry in the mapping. "
            f"Handle these by hand or extend the map:")
        for token, n in total_unmapped.most_common():
            print(f"        {token:<38} x{n}", file=sys.stderr)
    if const_hazards:
        verb = "removed the governing `const` at" if args.fix_const else "CONST HAZARD at"
        log(f"{verb} {len(const_hazards)} site(s) — a callable replacement cannot sit in a "
            f"const expression:")
        for site in const_hazards[:20]:
            print(f"        {site}", file=sys.stderr)
        if len(const_hazards) > 20:
            print(f"        … +{len(const_hazards) - 20} more", file=sys.stderr)
        if not args.fix_const:
            log("Prefer a const IconData in the mapping (LucideIcons.house, "
                "PhosphorIconsRegular.house) over a call (PhosphorIcons.house()); "
                "otherwise re-run with --fix-const.")

    if not args.apply:
        log("DRY RUN — nothing written. Re-run with --apply to write.")
        return 0
    if not changed:
        return 0
    if not args.yes:
        try:
            answer = input(f"Write {len(changed)} file(s)? [y/N] ").strip().lower()
        except EOFError:
            answer = ""
        if answer != "y":
            log("Aborted; nothing written.")
            return 1
    for path, _, new in changed:
        path.write_text(new, encoding="utf-8")
    log(f"wrote {len(changed)} file(s). Run `flutter analyze` now.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
