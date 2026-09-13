#!/usr/bin/env python3
"""Download a free asset (single file or zip pack), normalise the filenames,
and record the licence in assets/CREDITS.md.

    python3 fetch_asset.py \
        --url https://kenney.nl/media/pages/assets/ui-pack/ui-pack.zip \
        --dest assets/sprites/ui \
        --name "Kenney UI Pack" --author Kenney --license CC0 \
        --source https://kenney.nl/assets/ui-pack

Licence metadata is REQUIRED, not optional. An asset in the tree with no row in
CREDITS.md is an asset nobody can prove the project is allowed to ship. If you
do not know the licence yet, you are not ready to download the file.

Dry run is the default; pass --apply to actually write to disk.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import List, Tuple
from urllib.parse import unquote, urlparse

CREDIT_REQUIRED = {"CC-BY", "CC BY", "CC-BY-SA", "CC BY-SA", "CC-BY-NC", "CC BY-NC",
                   "MIT", "APACHE-2.0", "BSD-3-CLAUSE", "OFL", "OFL-1.1"}
NO_CREDIT_NEEDED = {"CC0", "CC0-1.0", "PUBLIC DOMAIN", "UNLICENSE"}
SKIP_NAMES = {"__macosx", ".ds_store", "thumbs.db"}
LICENSE_HINTS = ("license", "licence", "readme", "copying", "credits")

# Licences this skill will not ship without an explicit --force override.
# Matched as substrings against a normalised upper-case licence string.
LICENSE_DENY_SUBSTRINGS = (
    "GPL",          # GPL, LGPL, AGPL — viral over closed-source apps
    "AGPL",
    "CC-BY-NC",     # non-commercial
    "CC BY-NC",
    "BY-NC",
    "ALL RIGHTS RESERVED",
    "ARR",
)

MAX_BYTES = 200 * 1024 * 1024  # a UI pack is a few MB; 200 MB means a wrong URL


def log(msg: str) -> None:
    print(f"[fetch] {msg}", file=sys.stderr)


def snake(name: str) -> str:
    """Dart-conventional lower_snake_case, extension preserved.

    Flutter asset paths become Dart identifiers under flutter_gen, and
    `blueButton (1).png` becomes an unusable one.
    """
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    stem = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stem)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").lower()
    stem = re.sub(r"_+", "_", stem) or "asset"
    if stem[0].isdigit():
        stem = "a_" + stem
    return f"{stem}.{ext.lower()}" if ext else stem


def download(url: str) -> bytes:
    try:
        import requests  # type: ignore
    except ImportError:
        log("requests not installed — falling back to urllib.")
        from urllib.request import Request, urlopen

        req = Request(url, headers={"User-Agent": "flutter-ui-revamp/1.0"})
        with urlopen(req, timeout=60) as resp:  # noqa: S310 (explicit user-supplied URL)
            data = resp.read(MAX_BYTES + 1)
    else:
        resp = requests.get(url, timeout=60, stream=True,
                            headers={"User-Agent": "flutter-ui-revamp/1.0"})
        resp.raise_for_status()
        data = b""
        for chunk in resp.iter_content(1 << 16):
            data += chunk
            if len(data) > MAX_BYTES:
                break
    if len(data) > MAX_BYTES:
        raise SystemExit(f"[fetch] FATAL: download exceeds {MAX_BYTES // 1024 // 1024} MB — check the URL.")
    return data


def is_zip(data: bytes) -> bool:
    return data[:2] == b"PK"


def plan_zip(data: bytes, dest: Path, flatten: bool, only: str | None
             ) -> Tuple[List[Tuple[str, Path]], List[str]]:
    """Return (extraction plan, licence-ish files found inside the archive)."""
    plan: List[Tuple[str, Path]] = []
    notices: List[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            parts = [p for p in name.split("/") if p]
            if any(p.lower() in SKIP_NAMES for p in parts):
                continue
            if any(p in ("..", "") or p.startswith("/") for p in parts):
                log(f"WARN: refusing suspicious archive path {name!r}")
                continue
            base = parts[-1]
            if any(h in base.lower() for h in LICENSE_HINTS):
                notices.append(name)
            if only and not re.search(only, name):
                continue
            rel = Path(snake(base)) if flatten else Path(*[snake(p) for p in parts])
            plan.append((name, dest / rel))
    return plan, notices


def licence_blocked(license_str: str) -> str | None:
    """Return a reason if the licence is in the denylist, else None."""
    norm = license_str.strip().upper().replace("_", "-")
    # CC0 must not match the bare "GPL" substring check via false paths — it doesn't.
    if norm in NO_CREDIT_NEEDED or norm.startswith("CC0"):
        return None
    for needle in LICENSE_DENY_SUBSTRINGS:
        if needle.upper() in norm:
            return (
                f"licence {license_str!r} matches denylist ({needle}). "
                f"This skill rejects GPL/AGPL/CC-BY-NC and all-rights-reserved "
                f"assets. Pass --force only with a written reason from the user."
            )
    return None


def credits_row(args, files: List[Path], project: Path) -> str:
    lic = args.license.strip()
    needs = "Y" if lic.upper().replace("_", "-") not in NO_CREDIT_NEEDED else "N"
    listed = ", ".join(f"`{p.relative_to(project)}`" for p in files[:4])
    if len(files) > 4:
        listed += f" +{len(files) - 4} more"
    return (f"| {args.name} | {args.type} | {listed} | {args.author} | {lic} | "
            f"{needs} | {args.source or args.url} | {date.today().isoformat()} |")


CREDITS_HEADER = """# Credits

Every third-party asset shipped in this app, with its licence. Rows marked
**Credit required = Y** must also appear on the app's About / Credits screen —
shipping the file without that attribution breaches the licence.

| Asset | Type | Files | Author | License | Credit required | Source | Downloaded |
|---|---|---|---|---|---|---|---|
"""


def update_credits(project: Path, row: str, apply: bool) -> None:
    path = project / "assets" / "CREDITS.md"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        new = text + row + "\n"
    else:
        new = CREDITS_HEADER + row + "\n"
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
        log(f"CREDITS.md updated: {path}")
    else:
        log("CREDITS.md row that would be added:")
        print(f"        {row}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="Download and normalise a free asset.")
    ap.add_argument("--url", required=True)
    ap.add_argument("--dest", required=True, help="Destination dir, e.g. assets/icons")
    ap.add_argument("--project", default=".", help="Flutter project root")
    ap.add_argument("--name", required=True, help="Human name, e.g. 'Kenney UI Pack'")
    ap.add_argument("--author", required=True)
    ap.add_argument("--license", required=True, help="CC0 / CC-BY-4.0 / OFL-1.1 / MIT / ...")
    ap.add_argument("--source", help="Landing page URL (defaults to --url)")
    ap.add_argument("--type", default="asset",
                    help="icon | illustration | font | sprite | audio | animation | texture")
    ap.add_argument("--only", help="Regex; extract only archive members matching it")
    ap.add_argument("--flatten", action="store_true",
                    help="Drop archive directory structure and dump files into --dest")
    ap.add_argument("--apply", action="store_true", help="Write to disk (default: dry run)")
    ap.add_argument("--force", action="store_true",
                    help="Allow a denylisted licence (GPL / CC-BY-NC / ARR). Requires user sign-off.")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    dest = (project / args.dest).resolve()
    if project not in dest.parents and dest != project:
        log(f"FATAL: --dest must stay inside the project ({dest} does not).")
        return 2

    blocked = licence_blocked(args.license)
    if blocked and not args.force:
        log(f"FATAL: {blocked}")
        return 2
    if blocked and args.force:
        log(f"WARN: --force overriding denylist: {blocked}")

    log(f"GET {args.url}")
    try:
        data = download(args.url)
    except SystemExit:
        raise
    except Exception as exc:
        log(f"FATAL: download failed: {exc}")
        return 1
    log(f"{len(data) / 1024:.1f} KB received")

    written: List[Path] = []
    if is_zip(data):
        plan, notices = plan_zip(data, dest, args.flatten, args.only)
        log(f"zip archive · {len(plan)} file(s) selected"
            + (f" (filter {args.only!r})" if args.only else ""))
        if notices:
            log("licence/readme files inside the archive — READ THESE before shipping:")
            for n in notices:
                print(f"        {n}", file=sys.stderr)
        else:
            log("WARN: no LICENSE/README inside the archive. Verify the licence on the source page.")
        for src_name, out_path in plan:
            print(f"        {src_name}  ->  {out_path.relative_to(project)}", file=sys.stderr)
            if args.apply:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    out_path.write_bytes(zf.read(src_name))
            written.append(out_path)
    else:
        base = snake(unquote(os.path.basename(urlparse(args.url).path)) or args.name)
        out_path = dest / base
        print(f"        {args.url}  ->  {out_path.relative_to(project)}", file=sys.stderr)
        if args.apply:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
        written.append(out_path)

    update_credits(project, credits_row(args, written, project), args.apply)

    if not args.apply:
        log("DRY RUN — nothing written. Re-run with --apply.")
        return 0
    log(f"wrote {len(written)} file(s) under {dest.relative_to(project)}")
    log("Next: python3 optimize_flutter.py --project . --dir " + args.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
