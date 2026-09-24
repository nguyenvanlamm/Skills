#!/usr/bin/env python3
"""Download assets from sites that need an account, through their OFFICIAL APIs.

You log in once in a browser to create an API key or token, store it locally,
and this script resolves the asset's metadata (title, author, licence, landing
page) from the API. It then hands the file to fetch_asset.py, which applies the
same licence denylist, filename normalisation and CREDITS.md row as any other
download. The licence comes from the API response, not from memory.

    python3 fetch_api.py check                              # which keys are configured
    python3 fetch_api.py auth freesound                     # one-time OAuth2 login
    python3 fetch_api.py get sketchfab <uid> --dest assets/models --apply
    python3 fetch_api.py get freesound 14854 --dest assets/audio/sfx --apply
    python3 fetch_api.py get smithsonian <id> --dest assets/images --apply

Credentials are read from environment variables first, then from
~/.config/flutter-ui-revamp/credentials (KEY=VALUE lines, must be chmod 600).
Values are never printed, logged, or passed on the command line.

Providers and what you need (all keys are free, created while logged in):
    freesound    FREESOUND_API_KEY (search, HQ previews) + OAuth2 for original
                 files: FREESOUND_CLIENT_ID, then `fetch_api.py auth freesound`
    sketchfab    SKETCHFAB_API_TOKEN  (sketchfab.com/settings/password → API token)
    pixabay      PIXABAY_API_KEY      (pixabay.com/api/docs, shown when logged in)
    pexels       PEXELS_API_KEY       (pexels.com/api)
    polypizza    POLY_PIZZA_API_KEY   (poly.pizza/settings/api)
    smithsonian  DATA_GOV_API_KEY     (api.data.gov/signup; falls back to DEMO_KEY)

Dry run is the default, exactly as in fetch_asset.py; pass --apply to write.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import stat
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_asset  # noqa: E402

CRED_FILE = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "flutter-ui-revamp" / "credentials"
UA = "flutter-ui-revamp/1.0"


def log(msg: str) -> None:
    print(f"[api] {msg}", file=sys.stderr)


class ApiError(Exception):
    pass


# ── credentials ─────────────────────────────────────────────────────────────

def _read_cred_file() -> Dict[str, str]:
    if not CRED_FILE.exists():
        return {}
    mode = CRED_FILE.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ApiError(f"{CRED_FILE} is readable by other users. Run: chmod 600 {CRED_FILE}")
    out = {}
    for line in CRED_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def cred(name: str, required: bool = True, hint: str = "") -> Optional[str]:
    val = os.environ.get(name) or _read_cred_file().get(name)
    if not val and required:
        raise ApiError(f"{name} is not set. Create it while logged in ({hint}), then either "
                       f"`export {name}=…` or add `{name}=…` to {CRED_FILE} (chmod 600). "
                       f"Do not paste it into chat or commit it.")
    return val


def save_creds(values: Dict[str, str]) -> None:
    CRED_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(CRED_FILE.parent, 0o700)
    current = _read_cred_file()
    current.update(values)
    body = "".join(f"{k}={v}\n" for k, v in current.items())
    fd = os.open(CRED_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(body)
    os.chmod(CRED_FILE, 0o600)
    log(f"saved {', '.join(values)} to {CRED_FILE} (mode 600)")


# ── HTTP ────────────────────────────────────────────────────────────────────

def http_json(url: str, headers: Optional[Dict[str, str]] = None, data: Optional[Dict[str, str]] = None):
    req = Request(url, data=urlencode(data).encode() if data else None,
                  headers={"User-Agent": UA, "Accept": "application/json", **(headers or {})})
    try:
        with urlopen(req, timeout=60) as resp:  # noqa: S310 (fixed API hosts)
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        raise ApiError(f"HTTP {exc.code} from {url.split('?')[0]}: {body}") from None


def pick(d: dict, *keys, default=None):
    """Case-insensitive key lookup (Poly Pizza has used both `Title` and `title`)."""
    low = {k.lower(): v for k, v in d.items()} if isinstance(d, dict) else {}
    for k in keys:
        if k.lower() in low and low[k.lower()] not in (None, ""):
            return low[k.lower()]
    return default


# ── licence normalisation ───────────────────────────────────────────────────

def cc_from_text(text: str) -> str:
    """Map a CC URL or label ('Attribution', 'CC-BY 3.0', '.../by-nc/4.0/') to an
    SPDX-style id that fetch_asset's denylist and credit inference understand."""
    t = (text or "").strip()
    low = t.lower()
    ver = re.search(r"(\d\.\d)", low)
    v = ver.group(1) if ver else ""
    if "publicdomain/zero" in low or re.search(r"\bcc0\b|creative commons 0|public domain", low):
        return "CC0"
    m = re.search(r"/licenses/([a-z-]+)/", low)
    if m:
        parts = m.group(1)
    else:
        parts = "by"
        if "noncommercial" in low or "-nc" in low or " nc" in low:
            parts += "-nc"
        if "sharealike" in low or "-sa" in low or " sa" in low:
            parts += "-sa"
        if "noderiv" in low or "-nd" in low or " nd" in low:
            parts += "-nd"
        if not re.search(r"attribution|\bby\b|cc-by|cc by", low):
            return t or "UNKNOWN"
    return f"CC-{parts.upper()}" + (f"-{v}" if v else "")


# ── providers ───────────────────────────────────────────────────────────────
# Each resolver returns a dict: url, name, author, license, source, type,
# filename (optional), auth (headers needed for the file URL itself, optional).

def freesound(item: str, opts) -> dict:
    fields = "id,name,username,license,url,type,previews"
    access = cred("FREESOUND_ACCESS_TOKEN", required=False)
    api_key = cred("FREESOUND_API_KEY", required=False)
    if opts.quality == "original":
        if not access:
            raise ApiError("Original Freesound files need OAuth2. Run `fetch_api.py auth freesound` "
                           "once (log in, paste the code), or use --quality preview with "
                           "FREESOUND_API_KEY for the lossy HQ OGG/MP3 preview (~192 kbps OGG).")
        access = _freesound_fresh_token()
        hdr = {"Authorization": f"Bearer {access}"}
    else:
        if not (api_key or access):
            cred("FREESOUND_API_KEY", hint="freesound.org/apiv2/apply")
        hdr = {"Authorization": f"Token {api_key}"} if api_key else {"Authorization": f"Bearer {access}"}
    meta = http_json(f"https://freesound.org/apiv2/sounds/{int(item)}/?fields={fields}", hdr)
    lic = cc_from_text(meta.get("license", ""))
    stem = fetch_asset.snake(f"{meta['name'].rsplit('.', 1)[0]}_{meta['id']}")
    if opts.quality == "original":
        url = f"https://freesound.org/apiv2/sounds/{meta['id']}/download/"
        filename, auth = f"{stem}.{meta.get('type') or 'wav'}", hdr
    else:
        previews = meta.get("previews") or {}
        url = previews.get("preview-hq-ogg") or previews.get("preview-hq-mp3")
        if not url:
            raise ApiError("no HQ preview in the API response")
        filename, auth = f"{stem}.{url.rsplit('.', 1)[-1]}", None
    return dict(url=url, name=meta["name"], author=meta["username"], license=lic,
                source=meta.get("url") or f"https://freesound.org/s/{meta['id']}/", type="audio",
                filename=filename, auth=auth)


def _freesound_fresh_token() -> str:
    exp = float(cred("FREESOUND_TOKEN_EXPIRES", required=False) or 0)
    if time.time() < exp - 120:
        return cred("FREESOUND_ACCESS_TOKEN")
    log("Freesound access token expired — refreshing with the stored refresh token.")
    tok = http_json("https://freesound.org/apiv2/oauth2/access_token/", data={
        "client_id": cred("FREESOUND_CLIENT_ID"), "client_secret": cred("FREESOUND_API_KEY"),
        "grant_type": "refresh_token", "refresh_token": cred("FREESOUND_REFRESH_TOKEN")})
    _store_freesound(tok)
    return tok["access_token"]


def _store_freesound(tok: dict) -> None:
    save_creds({"FREESOUND_ACCESS_TOKEN": tok["access_token"],
                "FREESOUND_REFRESH_TOKEN": tok["refresh_token"],
                "FREESOUND_TOKEN_EXPIRES": str(int(time.time() + int(tok.get("expires_in", 86399))))})


SKETCHFAB_LICENSES = {
    "cc0 public domain": "CC0", "cc attribution": "CC-BY-4.0",
    "cc attribution-sharealike": "CC-BY-SA-4.0", "cc attribution-noderivs": "CC-BY-ND-4.0",
    "cc attribution-noncommercial": "CC-BY-NC-4.0",
    "cc attribution-noncommercial-sharealike": "CC-BY-NC-SA-4.0",
    "cc attribution-noncommercial-noderivs": "CC-BY-NC-ND-4.0",
    "free standard": "Sketchfab Free Standard", "standard": "Sketchfab Standard",
    "editorial": "Sketchfab Editorial (NON-COMMERCIAL)",
}


def sketchfab(item: str, opts) -> dict:
    meta = http_json(f"https://api.sketchfab.com/v3/models/{item}")
    if not meta.get("isDownloadable"):
        raise ApiError(f"'{meta.get('name')}' is not downloadable on Sketchfab.")
    label = (meta.get("license") or {}).get("label", "")
    lic = SKETCHFAB_LICENSES.get(label.lower(), label or "UNKNOWN")
    token = cred("SKETCHFAB_OAUTH_TOKEN", required=False)
    hdr = ({"Authorization": f"Bearer {token}"} if token else
           {"Authorization": f"Token {cred('SKETCHFAB_API_TOKEN', hint='sketchfab.com/settings/password → API token')}"})
    links = http_json(f"https://api.sketchfab.com/v3/models/{item}/download", hdr)
    fmt = opts.format if opts.format in links else next((f for f in ("glb", "gltf", "usdz") if f in links), None)
    if not fmt:
        raise ApiError(f"no downloadable format in response (got {list(links)})")
    if fmt != opts.format:
        log(f"--format {opts.format} not offered for this model; using {fmt}")
    user = meta.get("user") or {}
    stem = fetch_asset.snake(meta.get("name") or item)
    ext = {"glb": "glb", "usdz": "usdz", "gltf": "zip"}[fmt]
    return dict(url=links[fmt]["url"], name=meta.get("name") or item,
                author=user.get("displayName") or user.get("username") or "unknown",
                license=lic, source=meta.get("viewerUrl") or f"https://sketchfab.com/3d-models/{item}",
                type="model", filename=None if fmt == "gltf" else f"{stem}.{ext}")


def pixabay(item: str, opts) -> dict:
    key = cred("PIXABAY_API_KEY", hint="pixabay.com/api/docs, shown when logged in")
    video = opts.kind == "video"
    base = "https://pixabay.com/api/videos/" if video else "https://pixabay.com/api/"
    hits = http_json(f"{base}?{urlencode({'key': key, 'id': item})}").get("hits") or []
    if not hits:
        raise ApiError(f"no Pixabay item with id {item}")
    h = hits[0]
    if video:
        vids = h.get("videos") or {}
        v = vids.get(opts.size) or vids.get("medium") or next(iter(vids.values()))
        url = v["url"]
    else:
        field = {"web": "webformatURL", "large": "largeImageURL", "full": "imageURL",
                 "vector": "vectorURL"}.get(opts.size, "largeImageURL")
        url = h.get(field) or h.get("largeImageURL")
        if field in ("imageURL", "vectorURL") and not h.get(field):
            log(f"{field} needs Pixabay 'full API access' approval; falling back to largeImageURL (1280 px)")
    return dict(url=url, name=f"Pixabay {item} — {h.get('tags', '')[:40]}".strip(" —"),
                author=h.get("user", "unknown"), license="Pixabay Content License",
                source=h.get("pageURL") or f"https://pixabay.com/id-{item}/",
                type="video" if video else "illustration",
                filename=f"pixabay_{item}.{url.split('?')[0].rsplit('.', 1)[-1]}")


def pexels(item: str, opts) -> dict:
    hdr = {"Authorization": cred("PEXELS_API_KEY", hint="pexels.com/api")}
    if opts.kind == "video":
        meta = http_json(f"https://api.pexels.com/videos/videos/{int(item)}", hdr)
        files = sorted(meta.get("video_files") or [], key=lambda f: f.get("width") or 0)
        want = {"web": 640, "large": 1280, "full": 10 ** 6}.get(opts.size, 1280)
        f = [x for x in files if (x.get("width") or 0) <= want][-1:] or files[:1]
        if not f:
            raise ApiError("no video files in response")
        url, author = f[0]["link"], (meta.get("user") or {}).get("name", "unknown")
        typ, ext = "video", (f[0].get("file_type") or "video/mp4").split("/")[-1]
    else:
        meta = http_json(f"https://api.pexels.com/v1/photos/{int(item)}", hdr)
        src = meta.get("src") or {}
        url = src.get({"web": "large", "large": "large2x", "full": "original"}.get(opts.size, "large2x")) or src["original"]
        author, typ, ext = meta.get("photographer", "unknown"), "illustration", "jpg"
    return dict(url=url, name=(meta.get("alt") or f"Pexels {item}")[:80], author=author,
                license="Pexels License", source=meta.get("url") or f"https://www.pexels.com/photo/{item}/",
                type=typ, filename=f"pexels_{item}.{ext}")


def polypizza(item: str, opts) -> dict:
    meta = http_json(f"https://api.poly.pizza/v1.1/model/{item}",
                     {"x-auth-token": cred("POLY_PIZZA_API_KEY", hint="poly.pizza/settings/api")})
    creator = pick(meta, "Creator") or {}
    url = pick(meta, "Download")
    if not url:
        raise ApiError("no Download URL in the Poly Pizza response")
    title = pick(meta, "Title", default=item)
    return dict(url=url, name=title,
                author=pick(creator, "Username", "name", default="unknown"),
                license=cc_from_text(pick(meta, "Licence", "License", default="")),
                source=f"https://poly.pizza/m/{item}", type="model",
                filename=f"{fetch_asset.snake(title)}.glb")


def smithsonian(item: str, opts) -> dict:
    key = cred("DATA_GOV_API_KEY", required=False)
    if not key:
        log("DATA_GOV_API_KEY not set — using DEMO_KEY (low hourly rate limit). "
            "A free key: api.data.gov/signup")
        key = "DEMO_KEY"
    row = http_json(f"https://api.si.edu/openaccess/api/v1.0/content/{item}?api_key={key}").get("response") or {}
    dn = (row.get("content") or {}).get("descriptiveNonRepeating") or {}
    media = [m for m in (dn.get("online_media") or {}).get("media", [])
             if (m.get("usage") or {}).get("access") == "CC0"]
    if not media:
        raise ApiError("this record has no media marked CC0 — its images keep usage restrictions")
    m = media[0]
    # TIFF is never offered: Flutter cannot decode it. High-res JPEGs can be 15+ MB.
    want = "Screen Image" if opts.size == "web" else "High-resolution JPEG"
    res = {r.get("label"): r.get("url") for r in m.get("resources") or []}
    url = res.get(want) or m.get("content")
    return dict(url=url, name=row.get("title") or item, author=dn.get("data_source") or "Smithsonian Institution",
                license="CC0", source=dn.get("record_link") or f"https://collections.si.edu/search/detail/{item}",
                type="illustration",
                filename=f"{fetch_asset.snake(row.get('title') or 'si')}_{fetch_asset.snake(m.get('idsId', 'img'))}.jpg")


PROVIDERS: Dict[str, Callable] = {"freesound": freesound, "sketchfab": sketchfab, "pixabay": pixabay,
                                  "pexels": pexels, "polypizza": polypizza, "smithsonian": smithsonian}

NOTES = {
    "freesound": "Freesound API terms: free keys are for light, non-commercial use of the API itself; "
                 "commercial *API* use is negotiated with UPF. Each sound keeps its own CC licence "
                 "(CC-BY-NC is refused by fetch_asset).",
    "sketchfab": "Sketchfab API terms §4.7: show the CC licence and credit the creator "
                 "(username + model link) for CC-BY models.",
    "pixabay": "Pixabay API: download and bundle (no permanent hotlinking); no systematic mass downloads.",
    "polypizza": "Poly Pizza says its API is free for hobby use and pay-as-you-go for commercial "
                 "use — check poly.pizza/settings/api for your plan before using it for a paid app.",
}


# ── commands ────────────────────────────────────────────────────────────────

def cmd_check(_args) -> int:
    rows = [("freesound", "FREESOUND_API_KEY"), ("freesound (OAuth2)", "FREESOUND_ACCESS_TOKEN"),
            ("sketchfab", "SKETCHFAB_API_TOKEN"), ("pixabay", "PIXABAY_API_KEY"),
            ("pexels", "PEXELS_API_KEY"), ("polypizza", "POLY_PIZZA_API_KEY"),
            ("smithsonian", "DATA_GOV_API_KEY")]
    try:
        file_vals = _read_cred_file()
    except ApiError as exc:
        log(f"FATAL: {exc}")
        return 2
    for label, var in rows:
        where = "env" if os.environ.get(var) else ("file" if file_vals.get(var) else "")
        print(f"  {label:20} {var:24} {'set (' + where + ')' if where else 'missing'}")
    print(f"  credentials file: {CRED_FILE} {'(exists)' if CRED_FILE.exists() else '(not created)'}")
    return 0


def cmd_auth(args) -> int:
    if args.provider != "freesound":
        log(f"{args.provider} uses a static key — no login flow needed. See `fetch_api.py --help`.")
        return 0
    try:
        client_id = cred("FREESOUND_CLIENT_ID", hint="freesound.org/apiv2/apply → 'Client id'")
        secret = cred("FREESOUND_API_KEY", hint="freesound.org/apiv2/apply → 'Client secret/Api key'")
    except ApiError as exc:
        log(f"FATAL: {exc}")
        return 2
    print("1. Open this URL in your browser, log in to Freesound and click 'Authorize':\n"
          f"   https://freesound.org/apiv2/oauth2/authorize/?client_id={client_id}&response_type=code\n"
          "2. Freesound shows an authorization code. Paste it below (input is hidden).",
          file=sys.stderr)
    code = sys.stdin.readline().strip() if args.code_stdin else getpass.getpass("   code: ").strip()
    if not code:
        log("FATAL: no code entered")
        return 2
    try:
        tok = http_json("https://freesound.org/apiv2/oauth2/access_token/", data={
            "client_id": client_id, "client_secret": secret,
            "grant_type": "authorization_code", "code": code})
    except ApiError as exc:
        log(f"FATAL: {exc}")
        return 1
    _store_freesound(tok)
    log("Freesound OAuth2 ready. The access token lasts 24 h and is refreshed automatically.")
    return 0


def cmd_get(args, passthrough: List[str]) -> int:
    try:
        info = PROVIDERS[args.provider](args.item, args)
    except (ApiError, KeyError, ValueError) as exc:
        log(f"FATAL: {exc}")
        return 1
    if args.provider in NOTES:
        log(f"NOTE: {NOTES[args.provider]}")
    log(f"{args.provider}: '{info['name']}' by {info['author']} — licence from API: {info['license']}")
    argv = ["--url", info["url"], "--dest", args.dest, "--project", args.project,
            "--name", args.name or info["name"], "--author", info["author"],
            "--license", info["license"], "--source", info["source"], "--type", info["type"]]
    if info.get("filename") and not any(a.startswith("--filename") for a in passthrough):
        argv += ["--filename", info["filename"]]
    return fetch_asset.main(argv + passthrough, auth=info.get("auth"))


# ── self-test (no network, no keys) ─────────────────────────────────────────

def self_test() -> int:
    cases = [("http://creativecommons.org/publicdomain/zero/1.0/", "CC0"),
             ("Creative Commons 0", "CC0"), ("CC0 1.0", "CC0"),
             ("https://creativecommons.org/licenses/by/4.0/", "CC-BY-4.0"),
             ("http://creativecommons.org/licenses/by-nc/3.0/", "CC-BY-NC-3.0"),
             ("Attribution", "CC-BY"), ("Attribution NonCommercial", "CC-BY-NC"),
             ("CC-BY 3.0", "CC-BY-3.0"), ("CC-BY-SA 4.0", "CC-BY-SA-4.0")]
    bad = [(i, o, cc_from_text(i)) for i, o in cases if cc_from_text(i) != o]
    for lic, blocked in [("CC-BY-NC-3.0", True), ("Sketchfab Editorial (NON-COMMERCIAL)", True),
                         ("CC-BY-4.0", False), ("CC0", False), ("Pixabay Content License", False)]:
        if bool(fetch_asset.licence_blocked(lic)) != blocked:
            bad.append((lic, f"blocked={blocked}", "mismatch"))
    for lic, level in [("CC0", "none"), ("CC-BY-4.0", "on-screen"), ("Pexels License", "none"),
                       ("Pixabay Content License", "none"), ("Sketchfab Free Standard", "on-screen")]:
        if fetch_asset.credit_level(lic) != level:
            bad.append((lic, level, fetch_asset.credit_level(lic)))
    assert pick({"Title": "a"}, "title") == "a" and pick({"title": "b"}, "Title") == "b"
    for b in bad:
        print("FAIL", b)
    print("self-test:", "OK" if not bad else f"{len(bad)} failure(s)")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="Any unrecognised flag (--apply, --only, --flatten, --credit, "
                                        "--filename, --force) is passed through to fetch_asset.py.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="Show which API keys are configured (values are never printed)")
    sub.add_parser("self-test", help="Offline test of licence mapping")
    pa = sub.add_parser("auth", help="One-time login flow (Freesound OAuth2)")
    pa.add_argument("provider", choices=sorted(PROVIDERS))
    pa.add_argument("--code-stdin", action="store_true", help="Read the code from stdin instead of a hidden prompt")
    pg = sub.add_parser("get", help="Resolve an asset through the provider API and download it")
    pg.add_argument("provider", choices=sorted(PROVIDERS))
    pg.add_argument("item", help="Provider id: Freesound sound id, Sketchfab model uid, Pixabay/Pexels id, "
                                 "Poly Pizza id, Smithsonian record id")
    pg.add_argument("--dest", required=True)
    pg.add_argument("--project", default=".")
    pg.add_argument("--name", help="Override the asset name used in CREDITS.md")
    pg.add_argument("--quality", choices=("original", "preview"), default="original", help="Freesound")
    pg.add_argument("--format", choices=("glb", "gltf", "usdz"), default="glb", help="Sketchfab")
    pg.add_argument("--kind", choices=("image", "video"), default="image", help="Pixabay / Pexels")
    pg.add_argument("--size", choices=("web", "large", "full", "vector"), default="large",
                    help="Pixabay / Pexels / Smithsonian (web = small; Smithsonian default screen size)")
    args, rest = ap.parse_known_args()
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "self-test":
        return self_test()
    if args.cmd == "auth":
        return cmd_auth(args)
    if args.provider == "smithsonian" and args.size == "large" and "--size" not in sys.argv:
        args.size = "web"
    return cmd_get(args, rest)


if __name__ == "__main__":
    sys.exit(main())
