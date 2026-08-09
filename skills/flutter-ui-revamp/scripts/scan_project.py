#!/usr/bin/env python3
"""Audit an existing Flutter project before a UI revamp.

Produces `.revamp/audit.json` (machine-readable, consumed by the other
scripts) and `.revamp/audit.md` (for the human and for the agent to read
back). Nothing is modified — this script only reads.

    python3 scan_project.py [--project .] [--out .revamp] [--top 25]

Every number in the revamp report should trace back to this file. A weakness the
agent asserts without a line here is a guess.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dart_lex  # noqa: E402

# ── Thresholds. These are the same numbers the skill's hard rules quote. ──────
HEAVY_FILE_BYTES = 500 * 1024
HEAVY_AUDIO_BYTES = 1024 * 1024
BUNDLE_WARN_BYTES = 30 * 1024 * 1024

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
VECTOR_EXT = {".svg", ".vec"}
AUDIO_EXT = {".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac"}
ANIM_EXT = {".riv", ".json"}
FONT_EXT = {".ttf", ".otf", ".woff", ".woff2"}

RE_ICON = re.compile(r"\b(Icons|CupertinoIcons)\.([A-Za-z0-9_]+)")
RE_COLOR_LITERAL = re.compile(r"\bColor\(\s*0x([0-9A-Fa-f]{6,8})\s*\)")
RE_COLOR_ARGB = re.compile(r"\bColor\.fromARGB\(|\bColor\.fromRGBO\(")
RE_COLOR_NAMED = re.compile(r"\bColors\.([A-Za-z]+)(?:\.shade(\d+))?")
RE_TEXTSTYLE = re.compile(r"\bTextStyle\s*\(")
RE_ASSET_PATH = re.compile(r"^(assets|lib/assets|packages/[^/]+/assets)/\S+$")
RE_PROGRESS = re.compile(r"\b(CircularProgressIndicator|LinearProgressIndicator)\s*\(")
RE_MAGIC_PAD = re.compile(
    r"\b(?:EdgeInsets\.(?:all|symmetric|only|fromLTRB)|SizedBox|BorderRadius\.circular)\b"
)

STATE_PACKAGES = [
    "flutter_riverpod", "riverpod", "hooks_riverpod", "provider", "flutter_bloc",
    "bloc", "get", "getx", "mobx", "flutter_mobx", "redux", "signals",
    "stacked", "get_it",
]
UI_ASSET_PACKAGES = [
    "flutter_svg", "vector_graphics", "vector_graphics_compiler", "rive", "lottie",
    "google_fonts", "cached_network_image", "flutter_gen", "flutter_gen_runner",
    "lucide_icons", "phosphor_flutter", "hugeicons", "ionicons", "flutter_animate",
    "shimmer", "skeletonizer",
]
GAME_PACKAGES = ["flame", "flame_audio", "flame_forge2d", "flame_tiled", "just_audio", "audioplayers"]


def log(msg: str) -> None:
    print(f"[scan] {msg}", file=sys.stderr)


# ── pubspec ──────────────────────────────────────────────────────────────────

def parse_pubspec(path: Path) -> Dict[str, Any]:
    """Parse pubspec.yaml. Uses PyYAML when present, falls back to an
    indentation walker so the audit still runs on a bare Python install."""
    if not path.exists():
        return {"error": "pubspec.yaml not found", "found": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        return _shape_pubspec(data, found=True, parser="pyyaml")
    except ImportError:
        log("PyYAML not installed — falling back to the built-in parser (less exact).")
    except Exception as exc:  # malformed yaml is the user's problem, but keep going
        log(f"PyYAML failed to parse pubspec.yaml ({exc}); falling back.")
    return _shape_pubspec(_fallback_yaml(text), found=True, parser="fallback")


def _fallback_yaml(text: str) -> Dict[str, Any]:
    """Enough of a YAML reader for the handful of keys this audit needs."""
    out: Dict[str, Any] = {}
    section: str | None = None
    flutter_sub: str | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0 and line.endswith(":"):
            section = line[:-1]
            flutter_sub = None
            out.setdefault(section, {} if section != "flutter" else {})
            continue
        if indent == 0 and ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
            section = None
            continue
        if section in ("dependencies", "dev_dependencies") and indent == 2 and ":" in line:
            k, v = line.split(":", 1)
            out.setdefault(section, {})[k.strip()] = v.strip() or None
        elif section == "flutter":
            if indent == 2 and line.endswith(":"):
                flutter_sub = line[:-1]
                out.setdefault("flutter", {}).setdefault(flutter_sub, [])
            elif line.startswith("- ") and flutter_sub == "assets":
                out.setdefault("flutter", {}).setdefault("assets", []).append(line[2:].strip())
            elif flutter_sub == "fonts" and line.startswith("- family:"):
                fam = line.split(":", 1)[1].strip()
                out.setdefault("flutter", {}).setdefault("fonts", []).append({"family": fam, "fonts": []})
            elif flutter_sub == "fonts" and "asset:" in line:
                fonts = out.get("flutter", {}).get("fonts", [])
                if fonts:
                    fonts[-1].setdefault("fonts", []).append(
                        {"asset": line.split("asset:", 1)[1].strip()}
                    )
    return out


def _shape_pubspec(data: Dict[str, Any], found: bool, parser: str) -> Dict[str, Any]:
    flutter = data.get("flutter") or {}
    if not isinstance(flutter, dict):
        flutter = {}
    fonts = flutter.get("fonts") or []
    families = []
    font_assets = []
    if isinstance(fonts, list):
        for entry in fonts:
            if isinstance(entry, dict):
                families.append(entry.get("family"))
                for f in entry.get("fonts") or []:
                    if isinstance(f, dict) and f.get("asset"):
                        font_assets.append(f["asset"])
    deps = data.get("dependencies") or {}
    dev = data.get("dev_dependencies") or {}
    return {
        "found": found,
        "parser": parser,
        "name": data.get("name"),
        "dependencies": sorted(deps.keys()) if isinstance(deps, dict) else [],
        "dev_dependencies": sorted(dev.keys()) if isinstance(dev, dict) else [],
        "declared_assets": [a for a in (flutter.get("assets") or []) if isinstance(a, str)],
        "font_families": [f for f in families if f],
        "font_assets": font_assets,
        "uses_material": flutter.get("uses-material-design", None),
    }


# ── lib/ scan ────────────────────────────────────────────────────────────────

def scan_lib(project: Path, lib: Path) -> Dict[str, Any]:
    icons: Counter = Counter()
    icon_files: Dict[str, set] = defaultdict(set)
    colors: List[Dict[str, Any]] = []
    textstyles: List[Dict[str, Any]] = []
    asset_refs: Dict[str, set] = defaultdict(set)
    progress: List[Dict[str, Any]] = []
    per_file: Dict[str, Dict[str, int]] = {}
    dart_files: List[Path] = []
    signals = Counter()

    if not lib.is_dir():
        return {"error": "lib/ not found", "dart_files": 0}

    for path in sorted(lib.rglob("*.dart")):
        if path.name.endswith((".g.dart", ".freezed.dart", ".gr.dart", ".gen.dart")):
            continue  # generated code is not ours to restyle
        dart_files.append(path)
        src = path.read_text(encoding="utf-8", errors="replace")
        code, literals = dart_lex.strip(src)
        rel = str(path.relative_to(project)).replace("\\", "/")
        counts = Counter()

        for m in RE_ICON.finditer(code):
            name = f"{m.group(1)}.{m.group(2)}"
            icons[name] += 1
            icon_files[name].add(rel)
            counts["icons"] += 1

        in_theme = "/theme/" in rel or rel.endswith(("app_colors.dart", "app_theme.dart"))
        for m in RE_COLOR_LITERAL.finditer(code):
            colors.append({"file": rel, "line": dart_lex.line_of(src, m.start()),
                           "value": f"0x{m.group(1).upper()}", "kind": "literal",
                           "in_theme": in_theme})
            counts["colors"] += 1
        for m in RE_COLOR_NAMED.finditer(code):
            name = m.group(1)
            if name in ("of", "hashCode", "runtimeType"):
                continue
            colors.append({"file": rel, "line": dart_lex.line_of(src, m.start()),
                           "value": f"Colors.{name}" + (f".shade{m.group(2)}" if m.group(2) else ""),
                           "kind": "named", "in_theme": in_theme})
            counts["colors"] += 1
        for m in RE_COLOR_ARGB.finditer(code):
            colors.append({"file": rel, "line": dart_lex.line_of(src, m.start()),
                           "value": m.group(0).rstrip("("), "kind": "constructor",
                           "in_theme": in_theme})
            counts["colors"] += 1

        for m in RE_TEXTSTYLE.finditer(code):
            textstyles.append({"file": rel, "line": dart_lex.line_of(src, m.start()),
                               "in_theme": in_theme})
            counts["textstyles"] += 1

        for m in RE_PROGRESS.finditer(code):
            progress.append({"file": rel, "line": dart_lex.line_of(src, m.start()),
                             "widget": m.group(1)})

        for lit in literals:
            v = lit.value.strip()
            if RE_ASSET_PATH.match(v):
                asset_refs[v].add(rel)

        counts["padding_sites"] = len(RE_MAGIC_PAD.findall(code))
        per_file[rel] = dict(counts)

        for token, key in (
            ("CupertinoApp", "cupertino"), ("CupertinoPageScaffold", "cupertino"),
            ("MaterialApp", "material"), ("useMaterial3", "material3"),
            ("darkTheme:", "dark_theme"), ("ThemeMode.", "theme_mode"),
            ("FlameGame", "flame"), ("extends Game", "flame"),
            ("ThemeExtension", "theme_extension"), ("Hero(", "hero"),
            ("HapticFeedback", "haptics"), ("Semantics(", "semantics"),
            ("semanticLabel", "semantic_label"), ("Skeleton", "skeleton"),
            ("Shimmer", "shimmer"), ("RiveAnimation", "rive"), ("Lottie.", "lottie"),
            ("SvgPicture", "svg"), ("GoogleFonts.", "google_fonts"),
            # IconButton.tooltip feeds the semantics tree — count it as a11y signal.
            ("tooltip:", "tooltip"),
        ):
            if token in code:
                signals[key] += 1

    # Rank screens by presentation-layer density for large-app prioritization.
    ranked = sorted(
        (
            {
                "file": f,
                "score": (
                    c.get("icons", 0) * 2
                    + c.get("colors", 0) * 3
                    + c.get("textstyles", 0) * 2
                    + c.get("padding_sites", 0)
                ),
                **c,
            }
            for f, c in per_file.items()
            if not f.startswith("lib/theme/") and "/theme/" not in f
            and not f.startswith("lib/widgets/") and "/widgets/" not in f
        ),
        key=lambda x: -x["score"],
    )

    return {
        "dart_files": len(dart_files),
        "icons": [{"name": k, "count": v, "files": sorted(icon_files[k])}
                  for k, v in icons.most_common()],
        "icon_total": sum(icons.values()),
        "icon_distinct": len(icons),
        "colors": colors,
        "colors_outside_theme": sum(1 for c in colors if not c["in_theme"]),
        "textstyles": textstyles,
        "textstyles_outside_theme": sum(1 for t in textstyles if not t["in_theme"]),
        "progress_indicators": progress,
        "asset_refs": {k: sorted(v) for k, v in sorted(asset_refs.items())},
        "signals": dict(signals),
        "per_file": per_file,
        "priority_screens": ranked[:15],
    }


# ── assets/ scan ─────────────────────────────────────────────────────────────

# Flutter resolution-aware density folders. A file under …/2.0x/foo.webp is a
# variant of …/foo.webp — it ships with the main asset and needs no pubspec line.
DENSITY_DIRS = frozenset({"1.0x", "1.5x", "2.0x", "3.0x", "4.0x"})


def _strip_density_segment(rel: str) -> str | None:
    """If rel sits in a density folder, return the logical 1.0x path; else None."""
    parts = rel.split("/")
    for i, p in enumerate(parts):
        if p in DENSITY_DIRS and i + 1 < len(parts):
            return "/".join(parts[:i] + parts[i + 1:])
    return None


def _declared_match(rel: str, declared: List[str]) -> bool:
    """True if Flutter's asset bundle would include this file.

    Directory entries cover immediate children only (Flutter does not recurse).
    Density-bucket variants (2.0x/, 3.0x/, …) are included automatically when
    their 1.0x sibling is declared — they must not be reported as orphans.
    """
    candidates = [rel]
    logical = _strip_density_segment(rel)
    if logical is not None:
        candidates.append(logical)

    for candidate in candidates:
        for d in declared:
            d = d.strip()
            if not d:
                continue
            if d.endswith("/"):
                if candidate.startswith(d) and "/" not in candidate[len(d):]:
                    return True
            elif candidate == d:
                return True
    return False


def scan_assets(project: Path, declared: List[str]) -> Dict[str, Any]:
    root = project / "assets"
    files: List[Dict[str, Any]] = []
    by_kind: Counter = Counter()
    bytes_by_kind: Counter = Counter()
    total = 0
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_dir() or path.name.startswith("."):
                continue
            rel = str(path.relative_to(project)).replace("\\", "/")
            size = path.stat().st_size
            ext = path.suffix.lower()
            kind = ("image" if ext in IMAGE_EXT else "vector" if ext in VECTOR_EXT
                    else "audio" if ext in AUDIO_EXT else "font" if ext in FONT_EXT
                    else "animation" if ext in ANIM_EXT else "other")
            limit = HEAVY_AUDIO_BYTES if kind == "audio" else HEAVY_FILE_BYTES
            files.append({
                "path": rel, "bytes": size, "ext": ext, "kind": kind,
                "declared": _declared_match(rel, declared),
                "heavy": size > limit,
            })
            by_kind[kind] += 1
            bytes_by_kind[kind] += size
            total += size

    declared_missing = []
    existing = {f["path"] for f in files}
    for d in declared:
        d = d.strip()
        if not d:
            continue
        if d.endswith("/"):
            if not (project / d).is_dir():
                declared_missing.append(d)
        elif d not in existing and not (project / d).exists():
            declared_missing.append(d)

    return {
        "root_exists": root.is_dir(),
        "files": files,
        "count": len(files),
        "total_bytes": total,
        "by_kind": dict(by_kind),
        "bytes_by_kind": dict(bytes_by_kind),
        "orphans": [f["path"] for f in files if not f["declared"]],
        "declared_missing": declared_missing,
        "heavy": [{"path": f["path"], "bytes": f["bytes"]} for f in files if f["heavy"]],
        "over_budget": total > BUNDLE_WARN_BYTES,
    }


# ── findings ─────────────────────────────────────────────────────────────────

def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n} B"


def derive(pubspec: Dict[str, Any], lib: Dict[str, Any], assets: Dict[str, Any]) -> Dict[str, Any]:
    deps = set(pubspec.get("dependencies", [])) | set(pubspec.get("dev_dependencies", []))
    sig = lib.get("signals", {})
    findings: List[Dict[str, str]] = []

    def add(level: str, code: str, text: str) -> None:
        findings.append({"level": level, "code": code, "text": text})

    is_game = bool(sig.get("flame")) or any(p in deps for p in GAME_PACKAGES)

    if not sig.get("dark_theme"):
        add("high", "NO_DARK_MODE", "No `darkTheme:` found — the app has no dark mode.")
    if not sig.get("material3"):
        add("med", "NO_M3", "`useMaterial3` not set — the app renders on the Material 2 baseline.")
    if lib.get("colors_outside_theme", 0) > 0:
        add("high", "HARDCODED_COLORS",
            f"{lib['colors_outside_theme']} hardcoded colors outside lib/theme/.")
    if lib.get("textstyles_outside_theme", 0) > 0:
        add("high", "INLINE_TEXTSTYLE",
            f"{lib['textstyles_outside_theme']} inline TextStyle() outside lib/theme/.")
    if not pubspec.get("font_families") and "google_fonts" not in deps:
        add("high", "DEFAULT_FONT", "No bundled font family — the app is on the platform default (Roboto/SF).")
    if "google_fonts" in deps and not pubspec.get("font_families"):
        add("med", "RUNTIME_FONT",
            "google_fonts is used without bundled font files — fonts download at runtime (FOUT + offline break).")
    if lib.get("icon_distinct", 0) and not any(
        p in deps for p in ("lucide_icons", "phosphor_flutter", "hugeicons", "ionicons")
    ):
        add("med", "DEFAULT_ICONS",
            f"{lib['icon_distinct']} distinct default Material/Cupertino icons — no custom icon set.")
    if lib.get("progress_indicators"):
        add("low", "PLAIN_LOADER",
            f"{len(lib['progress_indicators'])} plain ProgressIndicator(s) — no branded loading state.")
    if not sig.get("hero"):
        add("low", "NO_HERO", "No Hero transitions — screen changes are hard cuts.")
    if not sig.get("haptics"):
        add("low", "NO_HAPTICS", "No HapticFeedback calls — buttons have no physical response.")
    # IconButton.tooltip also feeds the semantics tree (see refactor-patterns §1).
    has_a11y_labels = bool(
        sig.get("semantic_label") or sig.get("tooltip") or sig.get("semantics")
    )
    if not has_a11y_labels and lib.get("icon_total", 0) > 0:
        add("med", "NO_SEMANTICS",
            "No semanticLabel, IconButton.tooltip, or Semantics() — "
            "icon-only controls may be silent to screen readers.")
    if not any(p in deps for p in ("rive", "lottie", "flutter_animate")):
        add("low", "NO_ANIMATION", "No animation package (rive / lottie / flutter_animate).")
    if assets.get("orphans"):
        add("med", "ORPHAN_ASSETS",
            f"{len(assets['orphans'])} asset file(s) on disk but not declared in pubspec.yaml.")
    if assets.get("declared_missing"):
        add("high", "MISSING_ASSETS",
            f"{len(assets['declared_missing'])} pubspec asset entr(ies) point at nothing on disk — this is a runtime crash.")
    if assets.get("heavy"):
        add("med", "HEAVY_ASSETS", f"{len(assets['heavy'])} asset(s) over the size threshold.")
    if assets.get("over_budget"):
        add("high", "BUNDLE_BUDGET",
            f"Assets total {human(assets['total_bytes'])}, over the 30 MB budget.")
    if not any(f.get("ext") in VECTOR_EXT for f in assets.get("files", [])) and assets.get("count"):
        add("low", "NO_VECTORS", "No SVG/.vec assets — everything is raster.")
    png = sum(1 for f in assets.get("files", []) if f["ext"] == ".png")
    webp = sum(1 for f in assets.get("files", []) if f["ext"] == ".webp")
    if png and not webp:
        add("low", "NO_WEBP", f"{png} PNG(s) and no WebP — typically 25–35% of image bytes are wasted.")
    buckets = any("/2.0x/" in f["path"] or "/3.0x/" in f["path"] for f in assets.get("files", []))
    if assets.get("by_kind", {}).get("image") and not buckets:
        add("med", "NO_DENSITY_BUCKETS",
            "No 2.0x/3.0x density buckets — raster images will be resampled on most phones.")

    return {
        "is_game": is_game,
        "app_type": "flame_game" if is_game else "standard_app",
        "ui_framework": ("cupertino" if sig.get("cupertino") and not sig.get("material")
                         else "mixed" if sig.get("cupertino") else "material"),
        "state_management": sorted(p for p in STATE_PACKAGES if p in deps) or ["setState / unknown"],
        "ui_asset_packages": sorted(p for p in UI_ASSET_PACKAGES if p in deps),
        "game_packages": sorted(p for p in GAME_PACKAGES if p in deps),
        "has_theme_dir": any(k.startswith("lib/theme/") or "/theme/" in k
                             for k in lib.get("per_file", {})),
        "findings": findings,
    }


# ── report ───────────────────────────────────────────────────────────────────

def render_md(a: Dict[str, Any], top: int) -> str:
    p, lib, assets, d = a["pubspec"], a["lib"], a["assets"], a["derived"]
    L: List[str] = []
    w = L.append

    w(f"# UI audit — {p.get('name') or a['project']}")
    w("")
    w(f"_Generated {a['generated_at']} by flutter-ui-revamp/scan_project.py_")
    w("")
    w("## Shape of the project")
    w("")
    w("| | |")
    w("|---|---|")
    w(f"| Type | {d['app_type']} |")
    w(f"| UI framework | {d['ui_framework']} |")
    w(f"| State management | {', '.join(d['state_management'])} |")
    w(f"| Dart files scanned | {lib.get('dart_files', 0)} |")
    w(f"| Existing theme dir | {'yes' if d['has_theme_dir'] else 'no'} |")
    w(f"| Dark theme | {'yes' if lib.get('signals', {}).get('dark_theme') else 'NO'} |")
    w(f"| Material 3 | {'yes' if lib.get('signals', {}).get('material3') else 'NO'} |")
    w(f"| Bundled font families | {', '.join(p.get('font_families') or []) or 'none'} |")
    w(f"| UI/asset packages | {', '.join(d['ui_asset_packages']) or 'none'} |")
    if d["game_packages"]:
        w(f"| Game packages | {', '.join(d['game_packages'])} |")
    w(f"| Asset files | {assets.get('count', 0)} · {human(assets.get('total_bytes', 0))} |")
    w("")

    w("## Findings")
    w("")
    if not d["findings"]:
        w("No structural weaknesses detected. Verify visually before concluding the UI is fine.")
    else:
        w("| Severity | Code | Finding |")
        w("|---|---|---|")
        order = {"high": 0, "med": 1, "low": 2}
        for f in sorted(d["findings"], key=lambda x: order.get(x["level"], 3)):
            w(f"| {f['level'].upper()} | `{f['code']}` | {f['text']} |")
    w("")

    w(f"## Icons in use ({lib.get('icon_distinct', 0)} distinct, {lib.get('icon_total', 0)} occurrences)")
    w("")
    if lib.get("icons"):
        w("| Icon | Uses | Files |")
        w("|---|---:|---|")
        for it in lib["icons"][:top]:
            files = ", ".join(Path(f).name for f in it["files"][:3])
            more = f" +{len(it['files']) - 3}" if len(it["files"]) > 3 else ""
            w(f"| `{it['name']}` | {it['count']} | {files}{more} |")
        if len(lib["icons"]) > top:
            w(f"| … | | {len(lib['icons']) - top} more in audit.json |")
    else:
        w("_None found._")
    w("")

    w(f"## Hardcoded colors ({lib.get('colors_outside_theme', 0)} outside lib/theme/)")
    w("")
    outside = [c for c in lib.get("colors", []) if not c["in_theme"]]
    if outside:
        counts = Counter(c["value"] for c in outside)
        w("| Value | Uses | First seen |")
        w("|---|---:|---|")
        for value, n in counts.most_common(top):
            first = next(c for c in outside if c["value"] == value)
            w(f"| `{value}` | {n} | {first['file']}:{first['line']} |")
    else:
        w("_None outside the theme layer._")
    w("")

    w(f"## Inline TextStyle ({lib.get('textstyles_outside_theme', 0)} outside lib/theme/)")
    w("")
    outside_ts = [t for t in lib.get("textstyles", []) if not t["in_theme"]]
    if outside_ts:
        per = Counter(t["file"] for t in outside_ts)
        w("| File | Count |")
        w("|---|---:|")
        for f, n in per.most_common(top):
            w(f"| {f} | {n} |")
    else:
        w("_None outside the theme layer._")
    w("")

    w("## Assets")
    w("")
    if not assets.get("root_exists"):
        w("_No `assets/` directory._")
    else:
        w("| Kind | Files | Bytes |")
        w("|---|---:|---:|")
        for kind, n in sorted(assets.get("by_kind", {}).items()):
            w(f"| {kind} | {n} | {human(assets['bytes_by_kind'].get(kind, 0))} |")
        w(f"| **total** | **{assets['count']}** | **{human(assets['total_bytes'])}** |")
        w("")
        if assets.get("heavy"):
            w("**Heavy files**")
            w("")
            for f in sorted(assets["heavy"], key=lambda x: -x["bytes"])[:top]:
                w(f"- `{f['path']}` — {human(f['bytes'])}")
            w("")
        if assets.get("orphans"):
            w(f"**Orphans** (on disk, not declared — dead weight or a broken reference): {len(assets['orphans'])}")
            w("")
            for o in assets["orphans"][:top]:
                w(f"- `{o}`")
            w("")
        if assets.get("declared_missing"):
            w("**Declared but missing** (these throw at runtime):")
            w("")
            for m in assets["declared_missing"]:
                w(f"- `{m}`")
            w("")

    refs = lib.get("asset_refs", {})
    unresolved = [r for r in refs if not (Path(a["project"]) / r).exists()]
    if unresolved:
        w("## Asset paths referenced in code but absent from disk")
        w("")
        for r in unresolved[:top]:
            w(f"- `{r}` — referenced by {', '.join(refs[r][:2])}")
        w("")

    priority = lib.get("priority_screens") or []
    if priority and lib.get("dart_files", 0) >= 12:
        w("## Suggested screen priority (by presentation density)")
        w("")
        w("When `scope` is unset and the app is large, start with these files:")
        w("")
        w("| File | Score | Icons | Colors | TextStyles |")
        w("|---|---:|---:|---:|---:|")
        for row in priority[:8]:
            w(f"| `{row['file']}` | {row['score']} | {row.get('icons', 0)} | "
              f"{row.get('colors', 0)} | {row.get('textstyles', 0)} |")
        w("")

    w("## Next")
    w("")
    w("Step 2 of the skill: lock the design direction before downloading anything.")
    w("Every claim in the final report should cite a row above.")
    w("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit a Flutter project before a UI revamp.")
    ap.add_argument("--project", default=".", help="Flutter project root (default: .)")
    ap.add_argument("--out", default=".revamp",
                    help="Output dir, relative to --project (default: .revamp)")
    ap.add_argument("--top", type=int, default=25, help="Rows per table in audit.md")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    if not (project / "pubspec.yaml").exists():
        print(f"[scan] FATAL: {project} has no pubspec.yaml — not a Flutter project.", file=sys.stderr)
        return 2

    log(f"scanning {project}")
    pubspec = parse_pubspec(project / "pubspec.yaml")
    lib = scan_lib(project, project / "lib")
    assets = scan_assets(project, pubspec.get("declared_assets", []))
    derived = derive(pubspec, lib, assets)

    audit = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "project": str(project),
        "pubspec": pubspec,
        "lib": lib,
        "assets": assets,
        "derived": derived,
        "thresholds": {
            "heavy_file_bytes": HEAVY_FILE_BYTES,
            "heavy_audio_bytes": HEAVY_AUDIO_BYTES,
            "bundle_warn_bytes": BUNDLE_WARN_BYTES,
        },
    }

    out = project / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (out / "audit.md").write_text(render_md(audit, args.top), encoding="utf-8")

    high = sum(1 for f in derived["findings"] if f["level"] == "high")
    log(f"wrote {out / 'audit.json'} and {out / 'audit.md'}")
    log(f"{len(derived['findings'])} findings ({high} high) · "
        f"{lib.get('icon_distinct', 0)} distinct icons · "
        f"{lib.get('colors_outside_theme', 0)} hardcoded colors · "
        f"assets {human(assets.get('total_bytes', 0))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
