#!/usr/bin/env python3
"""Extract brand assets from a website into brand-info.json (stdlib only).

    python3 analyze-website.py --website https://example.com --output-dir /tmp/social-brand-sync/example.com

Reads the HTML once, resolves relative URLs, and records *where* every value
came from so the operator can judge it. Nothing is guessed: a field with no
evidence is null and listed in `missing`.

Exit 0 on success (even with missing fields); 1 when the page cannot be fetched.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; social-brand-sync/3.0; +https://github.com/nguyenvanlamm/Skills)"
TIMEOUT = 20


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metas = []       # list of dict(attrs)
        self.links = []
        self.imgs = []
        self.title = None
        self._in_title = False
        self._in_header = 0
        self.jsonld = []
        self._in_jsonld = False
        self._buf = ""

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag == "img":
            a["_in_header"] = self._in_header > 0
            self.imgs.append(a)
        elif tag == "title":
            self._in_title = True
        elif tag in ("header", "nav"):
            self._in_header += 1
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._buf = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("header", "nav") and self._in_header:
            self._in_header -= 1
        elif tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            try:
                self.jsonld.append(json.loads(self._buf))
            except json.JSONDecodeError:
                pass

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data
        if self._in_jsonld:
            self._buf += data


def fetch(url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        final = resp.geturl()
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace"), final


def meta(page: Page, **match) -> str | None:
    for m in page.metas:
        if all(m.get(k, "").lower() == v.lower() for k, v in match.items()):
            return m.get("content") or None
    return None


def size_of(attr: str | None) -> int:
    """'180x180' -> 180; 'any'/missing -> 0."""
    if not attr:
        return 0
    m = re.search(r"(\d+)x(\d+)", attr)
    return int(m.group(1)) if m else 0


def pick_logo(page: Page, base: str) -> tuple[str | None, str | None]:
    candidates: list[tuple[int, str, str]] = []  # (size, url, source)
    for l in page.links:
        rel = l.get("rel", "").lower()
        href = l.get("href")
        if not href:
            continue
        if "apple-touch-icon" in rel:
            candidates.append((size_of(l.get("sizes")) or 180, href, "apple-touch-icon"))
        elif "icon" in rel:
            candidates.append((size_of(l.get("sizes")), href, "link[rel=icon]"))
    tile = meta(page, name="msapplication-TileImage")
    if tile:
        candidates.append((144, tile, "msapplication-TileImage"))
    for img in page.imgs:
        blob = " ".join([img.get("class", ""), img.get("id", ""), img.get("alt", ""), img.get("src", "")]).lower()
        if img.get("src") and ("logo" in blob or "brand" in blob) and img.get("_in_header"):
            candidates.append((150, img["src"], "header img[logo]"))
    if not candidates:
        return None, None
    candidates.sort(key=lambda c: c[0], reverse=True)
    size, href, src = candidates[0]
    return urllib.parse.urljoin(base, href), f"{src} ({size}px)" if size else src


def pick_cover(page: Page, base: str) -> tuple[str | None, str | None]:
    for key, src in (("og:image", "og:image"), ("twitter:image", "twitter:image")):
        v = meta(page, property=key) or meta(page, name=key)
        if v:
            return urllib.parse.urljoin(base, v), src
    return None, None


def pick_name(page: Page, host: str) -> tuple[str, str]:
    for key, src in (("og:site_name", "og:site_name"), ("application-name", "application-name")):
        v = meta(page, property=key) or meta(page, name=key)
        if v and v.strip():
            return v.strip(), src
    for node in page.jsonld:
        items = node if isinstance(node, list) else [node]
        for it in items:
            if isinstance(it, dict) and it.get("@type") in ("Organization", "Brand", "WebSite") and it.get("name"):
                return str(it["name"]).strip(), "json-ld"
    if page.title and page.title.strip():
        t = re.split(r"\s+[|\-–—:·]\s+", page.title.strip())[0]
        return t.strip(), "title"
    for img in page.imgs:
        if img.get("_in_header") and img.get("alt") and "logo" in img.get("alt", "").lower():
            return img["alt"].replace("logo", "").strip(" -"), "header img alt"
    return host.split(".")[0].capitalize(), "domain (fallback)"


def pick_colors(page: Page, html: str) -> dict:
    out = {"primary": None, "theme_color": None, "source": None}
    tc = meta(page, name="theme-color")
    if tc:
        out["theme_color"] = tc.strip()
    m = re.search(r"--(?:primary|brand|color-primary|brand-color|accent)\s*:\s*(#[0-9a-fA-F]{3,8})", html)
    if m:
        out["primary"], out["source"] = m.group(1), "css custom property"
    elif tc and re.match(r"^#[0-9a-fA-F]{3,8}$", tc.strip()):
        out["primary"], out["source"] = tc.strip(), "meta theme-color"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--website", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    url = args.website if re.match(r"^https?://", args.website) else "https://" + args.website
    try:
        html, final_url = fetch(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
        print(json.dumps({"error": f"cannot fetch {url}: {e}"}))
        return 1

    page = Page()
    page.feed(html)
    host = urllib.parse.urlparse(final_url).netloc

    name, name_src = pick_name(page, host)
    logo, logo_src = pick_logo(page, final_url)
    cover, cover_src = pick_cover(page, final_url)
    colors = pick_colors(page, html)
    favicon = None
    for l in page.links:
        if "icon" in l.get("rel", "").lower() and l.get("href"):
            favicon = urllib.parse.urljoin(final_url, l["href"])
            break
    if not favicon:
        favicon = urllib.parse.urljoin(final_url, "/favicon.ico")

    missing = [k for k, v in (("logo_url", logo), ("cover_url", cover), ("colors.primary", colors["primary"])) if not v]

    info = {
        "website": final_url,
        "domain": host,
        "name": name,
        "logo_url": logo,
        "cover_url": cover,
        "favicon_url": favicon,
        "colors": {"primary": colors["primary"], "theme_color": colors["theme_color"]},
        "source": {"name_from": name_src, "logo_from": logo_src, "cover_from": cover_src, "color_from": colors["source"]},
        "missing": missing,
        "spa_hint": (len(page.imgs) == 0 and not meta(page, property="og:image")) and "html has no images or og tags — likely client-rendered; assets may need a manual URL" or None,
    }

    import os
    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, "brand-info.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2, ensure_ascii=False)
    print(json.dumps(info, indent=2, ensure_ascii=False))
    print(f"\nwrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
