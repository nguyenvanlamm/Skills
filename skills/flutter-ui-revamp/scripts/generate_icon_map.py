#!/usr/bin/env python3
"""Build an icons.json mapping from a scan_project audit + a known set.

Closes the audit → apply_icons loop so the agent does not hand-write every
Icons.* → Lucide/Phosphor line.

    python3 generate_icon_map.py \
        --audit .revamp/audit.json \
        --set lucide \
        --out icons.json

Prints the map, lists UNMAPPED icons from the audit, and writes JSON with
--apply (or always when --out is given — write is intentional for this script).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Keep in sync with references/refactor-patterns.md § mapping table.
# Prefer const IconData targets (no call parentheses).
LUCIDE: Dict[str, str] = {
    "Icons.home": "LucideIcons.house",
    "Icons.search": "LucideIcons.search",
    "Icons.settings": "LucideIcons.settings",
    "Icons.person": "LucideIcons.user",
    "Icons.add": "LucideIcons.plus",
    "Icons.delete": "LucideIcons.trash2",
    "Icons.edit": "LucideIcons.pencil",
    "Icons.favorite": "LucideIcons.heart",
    "Icons.favorite_border": "LucideIcons.heart",
    "Icons.share": "LucideIcons.share2",
    "Icons.menu": "LucideIcons.menu",
    "Icons.close": "LucideIcons.x",
    "Icons.check": "LucideIcons.check",
    "Icons.arrow_back": "LucideIcons.arrowLeft",
    "Icons.arrow_forward": "LucideIcons.arrowRight",
    "Icons.chevron_right": "LucideIcons.chevronRight",
    "Icons.chevron_left": "LucideIcons.chevronLeft",
    "Icons.notifications": "LucideIcons.bell",
    "Icons.shopping_cart": "LucideIcons.shoppingCart",
    "Icons.more_vert": "LucideIcons.moreVertical",
    "Icons.more_horiz": "LucideIcons.moreHorizontal",
    "Icons.star": "LucideIcons.star",
    "Icons.star_border": "LucideIcons.star",
    "Icons.calendar_today": "LucideIcons.calendar",
    "Icons.camera_alt": "LucideIcons.camera",
    "Icons.download": "LucideIcons.download",
    "Icons.filter_list": "LucideIcons.filter",
    "Icons.info_outline": "LucideIcons.info",
    "Icons.info": "LucideIcons.info",
    "Icons.lock": "LucideIcons.lock",
    "Icons.logout": "LucideIcons.logOut",
    "Icons.mail": "LucideIcons.mail",
    "Icons.email": "LucideIcons.mail",
    "Icons.refresh": "LucideIcons.refreshCw",
    "Icons.visibility": "LucideIcons.eye",
    "Icons.visibility_off": "LucideIcons.eyeOff",
    "Icons.warning": "LucideIcons.alertTriangle",
    "Icons.location_on": "LucideIcons.mapPin",
    "Icons.play_arrow": "LucideIcons.play",
    "Icons.pause": "LucideIcons.pause",
    "Icons.send": "LucideIcons.send",
    "Icons.bookmark": "LucideIcons.bookmark",
    "Icons.bookmark_border": "LucideIcons.bookmark",
    "Icons.check_circle": "LucideIcons.checkCircle2",
    "Icons.radio_button_unchecked": "LucideIcons.circle",
    "Icons.remove": "LucideIcons.minus",
    "Icons.clear": "LucideIcons.x",
    "Icons.done": "LucideIcons.check",
    "Icons.error": "LucideIcons.circleAlert",
    "Icons.error_outline": "LucideIcons.circleAlert",
    "Icons.help_outline": "LucideIcons.circleHelp",
    "Icons.image": "LucideIcons.image",
    "Icons.photo": "LucideIcons.image",
    "Icons.phone": "LucideIcons.phone",
    "Icons.place": "LucideIcons.mapPin",
    "Icons.account_circle": "LucideIcons.circleUser",
    "Icons.people": "LucideIcons.users",
    "Icons.list": "LucideIcons.list",
    "Icons.grid_view": "LucideIcons.layoutGrid",
    "Icons.home_outlined": "LucideIcons.house",
    "Icons.settings_outlined": "LucideIcons.settings",
}

PHOSPHOR: Dict[str, str] = {
    "Icons.home": "PhosphorIconsRegular.house",
    "Icons.search": "PhosphorIconsRegular.magnifyingGlass",
    "Icons.settings": "PhosphorIconsRegular.gear",
    "Icons.person": "PhosphorIconsRegular.user",
    "Icons.add": "PhosphorIconsRegular.plus",
    "Icons.delete": "PhosphorIconsRegular.trash",
    "Icons.edit": "PhosphorIconsRegular.pencilSimple",
    "Icons.favorite": "PhosphorIconsFill.heart",
    "Icons.favorite_border": "PhosphorIconsRegular.heart",
    "Icons.share": "PhosphorIconsRegular.shareNetwork",
    "Icons.menu": "PhosphorIconsRegular.list",
    "Icons.close": "PhosphorIconsRegular.x",
    "Icons.check": "PhosphorIconsRegular.check",
    "Icons.arrow_back": "PhosphorIconsRegular.arrowLeft",
    "Icons.arrow_forward": "PhosphorIconsRegular.arrowRight",
    "Icons.chevron_right": "PhosphorIconsRegular.caretRight",
    "Icons.chevron_left": "PhosphorIconsRegular.caretLeft",
    "Icons.notifications": "PhosphorIconsRegular.bell",
    "Icons.shopping_cart": "PhosphorIconsRegular.shoppingCart",
    "Icons.more_vert": "PhosphorIconsRegular.dotsThreeVertical",
    "Icons.more_horiz": "PhosphorIconsRegular.dotsThree",
    "Icons.star": "PhosphorIconsRegular.star",
    "Icons.star_border": "PhosphorIconsRegular.star",
    "Icons.calendar_today": "PhosphorIconsRegular.calendarBlank",
    "Icons.camera_alt": "PhosphorIconsRegular.camera",
    "Icons.download": "PhosphorIconsRegular.downloadSimple",
    "Icons.filter_list": "PhosphorIconsRegular.funnel",
    "Icons.info_outline": "PhosphorIconsRegular.info",
    "Icons.info": "PhosphorIconsRegular.info",
    "Icons.lock": "PhosphorIconsRegular.lock",
    "Icons.logout": "PhosphorIconsRegular.signOut",
    "Icons.mail": "PhosphorIconsRegular.envelope",
    "Icons.email": "PhosphorIconsRegular.envelope",
    "Icons.refresh": "PhosphorIconsRegular.arrowsClockwise",
    "Icons.visibility": "PhosphorIconsRegular.eye",
    "Icons.visibility_off": "PhosphorIconsRegular.eyeSlash",
    "Icons.warning": "PhosphorIconsRegular.warning",
    "Icons.location_on": "PhosphorIconsRegular.mapPin",
    "Icons.play_arrow": "PhosphorIconsFill.play",
    "Icons.pause": "PhosphorIconsFill.pause",
    "Icons.send": "PhosphorIconsRegular.paperPlaneTilt",
    "Icons.bookmark": "PhosphorIconsRegular.bookmarkSimple",
    "Icons.bookmark_border": "PhosphorIconsRegular.bookmarkSimple",
    "Icons.check_circle": "PhosphorIconsRegular.checkCircle",
    "Icons.radio_button_unchecked": "PhosphorIconsRegular.circle",
    "Icons.remove": "PhosphorIconsRegular.minus",
    "Icons.clear": "PhosphorIconsRegular.x",
    "Icons.done": "PhosphorIconsRegular.check",
    "Icons.error": "PhosphorIconsRegular.warningCircle",
    "Icons.error_outline": "PhosphorIconsRegular.warningCircle",
    "Icons.help_outline": "PhosphorIconsRegular.question",
    "Icons.image": "PhosphorIconsRegular.image",
    "Icons.photo": "PhosphorIconsRegular.image",
    "Icons.phone": "PhosphorIconsRegular.phone",
    "Icons.place": "PhosphorIconsRegular.mapPin",
    "Icons.account_circle": "PhosphorIconsRegular.userCircle",
    "Icons.people": "PhosphorIconsRegular.users",
    "Icons.list": "PhosphorIconsRegular.list",
    "Icons.grid_view": "PhosphorIconsRegular.squaresFour",
    "Icons.home_outlined": "PhosphorIconsRegular.house",
    "Icons.settings_outlined": "PhosphorIconsRegular.gear",
}

SETS = {
    "lucide": {
        "import": "package:lucide_icons/lucide_icons.dart",
        "map": LUCIDE,
        "note": "Verify each constant against the installed lucide_icons version; "
                "upstream renames (home→house) are already applied here.",
    },
    "phosphor": {
        "import": "package:phosphor_flutter/phosphor_flutter.dart",
        "map": PHOSPHOR,
        "note": "Uses const constants (PhosphorIconsRegular.*), not PhosphorIcons.x() calls.",
    },
}


def log(msg: str) -> None:
    print(f"[icon-map] {msg}", file=sys.stderr)


def load_audit_icons(path: Path) -> List[Tuple[str, int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    icons = data.get("lib", {}).get("icons") or []
    out: List[Tuple[str, int]] = []
    for it in icons:
        name = it.get("name") or ""
        if name.startswith("Icons.") or name.startswith("CupertinoIcons."):
            out.append((name, int(it.get("count") or 0)))
    return out


def build(audit_icons: List[Tuple[str, int]], set_key: str
          ) -> Tuple[dict, List[Tuple[str, int]], List[Tuple[str, int]]]:
    conf = SETS[set_key]
    full_map: Dict[str, str] = conf["map"]
    mapped: Dict[str, str] = {}
    used: List[Tuple[str, int]] = []
    unmapped: List[Tuple[str, int]] = []

    for name, count in audit_icons:
        # Only Material Icons.* are in the tables; Cupertino stays unless added.
        if name in full_map:
            mapped[name] = full_map[name]
            used.append((name, count))
        elif name.startswith("Icons."):
            unmapped.append((name, count))
        # CupertinoIcons.* listed as unmapped for visibility
        elif name.startswith("CupertinoIcons."):
            unmapped.append((name, count))

    payload = {
        "import": conf["import"],
        "map": mapped,
        "_meta": {
            "set": set_key,
            "mapped": len(mapped),
            "unmapped": len(unmapped),
            "note": conf["note"],
        },
    }
    return payload, used, unmapped


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate apply_icons.py mapping from audit.json")
    ap.add_argument("--audit", default=".revamp/audit.json",
                    help="Path to audit.json from scan_project.py")
    ap.add_argument("--set", choices=sorted(SETS.keys()), default="lucide",
                    help="Icon set to map into (default: lucide)")
    ap.add_argument("--out", default="icons.json", help="Output mapping JSON path")
    ap.add_argument("--project", default=".", help="Project root (resolves relative paths)")
    ap.add_argument("--all-known", action="store_true",
                    help="Emit the full known table, not only icons found in the audit")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    audit_path = Path(args.audit)
    if not audit_path.is_absolute():
        audit_path = project / audit_path
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = project / out_path

    if not audit_path.is_file() and not args.all_known:
        log(f"FATAL: audit not found: {audit_path}. Run scan_project.py first, "
            f"or pass --all-known to emit the full table without an audit.")
        return 2

    if args.all_known and not audit_path.is_file():
        audit_icons = [(k, 0) for k in SETS[args.set]["map"]]
    else:
        audit_icons = load_audit_icons(audit_path)
        if args.all_known:
            # Union: every known key, plus any audit-only for unmapped reporting
            known = set(SETS[args.set]["map"])
            seen = {n for n, _ in audit_icons}
            for k in known - seen:
                audit_icons.append((k, 0))

    if not audit_icons:
        log("No Icons.* / CupertinoIcons.* in audit. Nothing to map.")
        return 0

    payload, used, unmapped = build(audit_icons, args.set)
    # Strip _meta from file written for apply_icons (it accepts unknown keys
    # only if not inside map — keep meta out of map, sibling is fine; apply
    # ignores non-map keys at top level except import/map).
    write_body = {"import": payload["import"], "map": payload["map"]}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(write_body, indent=2) + "\n", encoding="utf-8")
    log(f"wrote {out_path} · {len(payload['map'])} mapped, {len(unmapped)} unmapped")
    log(SETS[args.set]["note"])

    if used:
        log("mapped from audit:")
        for name, n in sorted(used, key=lambda x: -x[1])[:30]:
            print(f"        {name:<40} -> {payload['map'][name]:<40} x{n}", file=sys.stderr)
    if unmapped:
        log(f"UNMAPPED ({len(unmapped)}) — leave Material, or extend the table in "
            f"generate_icon_map.py / refactor-patterns.md:")
        for name, n in sorted(unmapped, key=lambda x: -x[1])[:40]:
            print(f"        {name:<40} x{n}", file=sys.stderr)

    log(f"Next: python3 apply_icons.py --project . --map {out_path.name}")
    log("Show the dry-run diff to the user before --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
