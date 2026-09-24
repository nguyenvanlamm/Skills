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

Some sites (unDraw, Storyset/Freepik) forbid downloading through a script.
Download those by hand and import them with `--local <file> --source <page>`:
the same filename normalisation and CREDITS row apply, with no network call.

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

# Where the attribution obligation is satisfied (licensing.md § table):
#   on-screen     visible credit line on the About / Credits screen (CC BY family,
#                 Freepik/Storyset, anything custom or unknown)
#   license-page  licence text shipped via LicenseRegistry + showLicensePage
#                 (MIT / ISC / BSD / Apache-2.0 / OFL — no on-screen credit)
#   none          no obligation (CC0 / public domain / Unlicense / unDraw)
CREDIT_NONE = (r"^CC0\b", r"PUBLIC DOMAIN", r"^UNLICENSE$", r"^UNDRAW\b")
CREDIT_LICENSE_PAGE = (r"^MIT\b", r"^ISC\b", r"^BSD\b", r"^APACHE\b", r"^OFL\b",
                       r"^SIL OFL\b", r"^ITF\b", r"FONTSHARE")
CREDIT_LEVELS = ("on-screen", "license-page", "none")
SKIP_NAMES = {"__macosx", ".ds_store", "thumbs.db"}
LICENSE_HINTS = ("license", "licence", "readme", "copying", "credits", "notice", "ofl", "ffl")

# Licences this skill will not ship without an explicit --force override.
# Regexes against the normalised upper-case licence string. Word boundaries
# matter: a bare "ARR" substring would also reject "…no warranty…".
LICENSE_DENY_PATTERNS = (
    (r"\bA?L?GPL", "GPL/LGPL/AGPL — viral over closed-source apps"),
    (r"\bBY-NC\b|\bNC\b|NON-?COMMERCIAL", "non-commercial"),
    (r"PERSONAL USE", "personal use only"),
    (r"ALL RIGHTS RESERVED|\bARR\b", "all rights reserved"),
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


def is_html(data: bytes) -> bool:
    """A landing page served where a file was expected (JS download buttons,
    login walls, 404 pages returned as 200). SVG starts with `<?xml`/`<svg`."""
    head = data[:512].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    return head.startswith((b"<!doctype html", b"<html", b"<head", b"<!--")) \
        and b"<svg" not in head


def is_lfs_pointer(data: bytes) -> bool:
    """raw.githubusercontent.com serves Git LFS files as a ~130-byte text pointer."""
    return len(data) < 1024 and data.startswith(b"version https://git-lfs.github.com/spec/")


def lfs_media_url(url: str) -> str | None:
    m = re.match(r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/(.+)", url)
    return f"https://media.githubusercontent.com/media/{m[1]}/{m[2]}/{m[3]}" if m else None


NOTICE_EXT = ("", ".txt", ".md", ".html", ".htm", ".pdf", ".rtf")


def is_notice(base: str) -> bool:
    """A licence/readme file — by name AND text-like extension, so an icon
    called `credits-currency.svg` is not mistaken for a licence."""
    stem, ext = os.path.splitext(base.lower())
    return ext in NOTICE_EXT and any(h in stem for h in LICENSE_HINTS)


def plan_zip(data: bytes, dest: Path, flatten: bool, only: str | None, strip: int = 0
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
            if is_notice(base):
                notices.append(name)
            if only and not re.search(only, name):
                continue
            kept = parts[min(strip, len(parts) - 1):]  # never strip the filename itself
            rel = Path(snake(base)) if flatten else Path(*[snake(p) for p in kept])
            plan.append((name, dest / rel))
    return plan, notices


def norm_license(license_str: str) -> str:
    return license_str.strip().upper().replace("_", "-")


def licence_blocked(license_str: str) -> str | None:
    """Return a reason if the licence is in the denylist, else None."""
    norm = norm_license(license_str)
    for pattern, why in LICENSE_DENY_PATTERNS:
        if re.search(pattern, norm):
            return (
                f"licence {license_str!r} matches denylist ({why}). "
                f"This skill rejects GPL/AGPL/CC-BY-NC and all-rights-reserved "
                f"assets. Pass --force only with a written reason from the user."
            )
    return None


def credit_level(license_str: str) -> str:
    norm = norm_license(license_str)
    if any(re.search(p, norm) for p in CREDIT_NONE):
        return "none"
    if any(re.search(p, norm) for p in CREDIT_LICENSE_PAGE):
        return "license-page"
    return "on-screen"


def credits_row(args, files: List[Path], project: Path) -> str:
    listed = ", ".join(f"`{p.relative_to(project)}`" for p in files[:4])
    if len(files) > 4:
        listed += f" +{len(files) - 4} more"
    return (f"| {args.name} | {args.type} | {listed} | {args.author} | {args.license.strip()} | "
            f"{args.credit} | {args.source or args.url} | {date.today().isoformat()} |")


CREDITS_HEADER = """# Credits

Every third-party asset shipped in this app, with its licence. The **Credit**
column says where the obligation is met:

- `on-screen` — a visible credit line on the About / Credits screen. Shipping
  the file without it breaches the licence.
- `license-page` — licence text registered with `LicenseRegistry`, shown by
  `showLicensePage`. No on-screen credit line needed.
- `none` — no obligation.

| Asset | Type | Files | Author | License | Credit | Source | Downloaded |
|---|---|---|---|---|---|---|---|
"""


def update_credits(project: Path, row: str, name: str, apply: bool) -> None:
    """Append the row, or replace an existing row for the same asset name so a
    re-download does not leave two contradictory entries."""
    path = project / "assets" / "CREDITS.md"
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        key = f"| {name} |"
        hits = [k for k, ln in enumerate(lines) if ln.startswith(key)]
        if hits:
            lines[hits[0]] = row
            lines = [ln for k, ln in enumerate(lines) if k not in hits[1:]]
            log(f"CREDITS.md already has a row for {name!r} — replacing it.")
        else:
            lines.append(row)
        new = "\n".join(lines) + "\n"
    else:
        new = CREDITS_HEADER + row + "\n"
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
        log(f"CREDITS.md updated: {path}")
    else:
        log("CREDITS.md row that would be added:")
        print(f"        {row}", file=sys.stderr)


# Sites whose terms forbid downloading through a script or tool (licensing.md
# trap 9). Download these by hand in a browser and import with --local.
NO_SCRIPTED_DOWNLOAD = ("undraw.co", "storyset.com", "freepik.com", "flaticon.com", "manypixels.co")


def scripted_download_banned(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    return next((h for h in NO_SCRIPTED_DOWNLOAD if host == h or host.endswith("." + h)), None)


# Archive formats this script cannot unpack with the standard library. Saving
# one as a single opaque file puts a useless blob in the bundle.
UNSUPPORTED_ARCHIVES = (
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"Rar!\x1a\x07", "rar"),
    (b"\x1f\x8b", "gzip/tar.gz"),
)
# URL basenames that name the format, not the asset, so every download from
# that source lands on the same path.
GENERIC_STEMS = {"lottie", "animation", "data", "svg", "png", "image", "icon", "download",
                 "file", "color", "default", "a_24px", "a_48px", "a_512", "a_128"}
RE_MIXKIT_PREVIEW = re.compile(r"^(https?://assets\.mixkit\.co/active_storage/sfx/(\d+)/)\2-preview\.mp3$")


def sniff_ext(data: bytes) -> str:
    """Extension from content, for URLs whose path has none (`…/svg?seed=x`)."""
    head = data[:512].lstrip(b"\xef\xbb\xbf \t\r\n")
    if head.startswith(b"\x89PNG"):
        return ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    if head.startswith((b"<?xml", b"<svg")) and b"<svg" in data[:4096]:
        return ".svg"
    if head.startswith((b"{", b"[")):
        return ".json"
    return ""


def unsupported_archive(data: bytes) -> str | None:
    return next((kind for magic, kind in UNSUPPORTED_ARCHIVES if data.startswith(magic)), None)


def preview_instead_of_file(url: str) -> str | None:
    """Return the full-quality URL when `url` is a low-bitrate preview."""
    m = RE_MIXKIT_PREVIEW.match(url)
    return f"{m.group(1)}{m.group(2)}.wav" if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Download (or import) and normalise a free asset.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="Direct file URL to download")
    src.add_argument("--local", help="A file or zip you downloaded by hand (for sites that "
                                     "forbid scripted downloads, e.g. unDraw, Storyset)")
    ap.add_argument("--dest", required=True, help="Destination dir, e.g. assets/icons")
    ap.add_argument("--project", default=".", help="Flutter project root")
    ap.add_argument("--name", required=True, help="Human name, e.g. 'Kenney UI Pack'")
    ap.add_argument("--author", required=True)
    ap.add_argument("--license", required=True, help="CC0 / CC-BY-4.0 / OFL-1.1 / MIT / ...")
    ap.add_argument("--source", help="Landing page URL (defaults to --url; required with --local)")
    ap.add_argument("--type", default="asset",
                    help="icon | illustration | font | sprite | audio | animation | texture")
    ap.add_argument("--only", help="Regex; extract only archive members matching it")
    ap.add_argument("--flatten", action="store_true",
                    help="Drop archive directory structure and dump files into --dest")
    ap.add_argument("--strip", type=int, default=0, metavar="N",
                    help="Drop the first N directory levels of each archive path (like tar "
                         "--strip-components), e.g. keep only <author>/<icon>.svg")
    ap.add_argument("--filename",
                    help="Output name for a single-file download. Needed when the URL basename "
                         "is generic or shared (Noto `…/1f680/lottie.json`, Material Symbols "
                         "`…/24px.svg`, DiceBear `…/svg?seed=x`)")
    ap.add_argument("--apply", action="store_true", help="Write to disk (default: dry run)")
    ap.add_argument("--force", action="store_true",
                    help="Allow a denylisted licence (GPL / CC-BY-NC / ARR). Requires user sign-off.")
    ap.add_argument("--credit", choices=CREDIT_LEVELS,
                    help="Where attribution is satisfied. Default: inferred from --license "
                         "(unknown/custom licences default to on-screen)")
    args = ap.parse_args()
    if not args.credit:
        args.credit = credit_level(args.license)
        log(f"credit level inferred from licence: {args.credit}")

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

    if args.local:
        local = Path(args.local).expanduser()
        if not local.is_file():
            log(f"FATAL: --local file not found: {local}")
            return 2
        if not args.source:
            log("FATAL: --local needs --source <landing page URL> so CREDITS.md can cite it.")
            return 2
        data = local.read_bytes()
        log(f"imported {local} · {len(data) / 1024:.1f} KB")
    else:
        banned = scripted_download_banned(args.url)
        if banned:
            log(f"FATAL: {banned}'s terms forbid downloading through a script or tool. Download "
                f"the file by hand in a browser, then re-run with --local <file> --source <page>.")
            return 2
        if urlparse(args.url).path.lower().endswith((".7z", ".rar", ".tar.gz", ".tgz")):
            log("FATAL: 7z / rar / tar.gz archives cannot be unpacked by this script (checked "
                "before downloading). Download and extract by hand, then import the files you "
                "need with --local <file.zip> --source <page>.")
            return 2
        full = preview_instead_of_file(args.url)
        if full:
            log(f"FATAL: that is Mixkit's low-bitrate preview, not the sound effect. Use the full "
                f"file instead: --url {full}")
            return 2
        log(f"GET {args.url}")
        try:
            data = download(args.url)
        except SystemExit:
            raise
        except Exception as exc:
            log(f"FATAL: download failed: {exc}")
            return 1
        log(f"{len(data) / 1024:.1f} KB received")
    if is_html(data):
        log("FATAL: the URL returned an HTML page, not an asset file. The site probably "
            "serves the download behind a JS button or login. Find the direct file URL "
            "(browser devtools → Network) or download by hand. Nothing written.")
        return 1
    if is_lfs_pointer(data):
        media = lfs_media_url(args.url or "")
        log("FATAL: that is a Git LFS pointer file, not the asset. "
            + (f"Use the LFS media URL instead: --url {media}" if media
               else "Fetch the file through the host's LFS/media endpoint.") + " Nothing written.")
        return 1
    kind = unsupported_archive(data)
    if kind:
        log(f"FATAL: this is a {kind} archive, which this script cannot unpack; saving it as-is "
            f"would ship one opaque blob. Extract it by hand, pick the files you need, zip them "
            f"(or take them one by one) and re-run with --local <file.zip> --source <page>. "
            f"Nothing written.")
        return 1

    written: List[Path] = []
    if is_zip(data):
        plan, notices = plan_zip(data, dest, args.flatten, args.only, args.strip)
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
        raw_name = args.filename or (Path(args.local).name if args.local else
                                     unquote(os.path.basename(urlparse(args.url).path)))
        base = snake(raw_name or args.name)
        if "." not in base:
            base += sniff_ext(data)
        if not args.filename and os.path.splitext(base)[0] in GENERIC_STEMS:
            log(f"WARN: {base!r} is a generic name that the next download from this source "
                f"will overwrite. Pass --filename, e.g. --filename rocket.json.")
        out_path = dest / base
        print(f"        {args.local or args.url}  ->  {out_path.relative_to(project)}",
              file=sys.stderr)
        if args.apply:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
        written.append(out_path)

    update_credits(project, credits_row(args, written, project), args.name, args.apply)

    if not args.apply:
        log("DRY RUN — nothing written. Re-run with --apply.")
        return 0
    log(f"wrote {len(written)} file(s) under {dest.relative_to(project)}")
    log("Next: python3 optimize_flutter.py --project . --dir " + args.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
