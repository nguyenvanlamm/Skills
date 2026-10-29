#!/usr/bin/env python3
"""The App Store side of the 4.3 check: an index of the games already selling.

    python3 market.py refresh [--countries us,gb,jp,vn] [--force]
    python3 market.py search TERM ... [--country us]
    python3 market.py stats

references/signatures.json knows the few dozen hits whose clones App Review spots at a
glance. This index knows the rest: the top 100 free, paid and grossing games of every
game category, and of Games overall, in each storefront, plus what App Store search
returns for the app's own name and keywords. Each entry keeps the name, developer,
chart positions, rating count, description and icon; Pillow adds an icon hash.
scan.py's `market` group compares the app's name, listing and icon with every entry.

Sources: Apple's legacy iTunes RSS charts and the iTunes Search API (about 20 calls a
minute). Cache: ~/.cache/appstore-spam-guard, or $APPSTORE_SPAM_GUARD_CACHE; charts and
searches are fetched again after 7 days. Stdlib only, Pillow optional.
"""
from __future__ import annotations

import argparse
import difflib
import io
import json
import os
import re
import statistics
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.2.0"
UA = f"appstore-spam-guard/{VERSION}"
GAME_GENRES = {
    6014: "Games", 7001: "Action", 7002: "Adventure", 7003: "Casual", 7004: "Board",
    7005: "Card", 7006: "Casino", 7007: "Dice", 7008: "Educational", 7009: "Family",
    7011: "Music", 7012: "Puzzle", 7013: "Racing", 7014: "Role Playing",
    7015: "Simulation", 7016: "Sports", 7017: "Strategy", 7018: "Trivia", 7019: "Word",
}
FEEDS = {"free": "topfreeapplications", "paid": "toppaidapplications",
         "grossing": "topgrossingapplications"}
DEFAULT_COUNTRIES = ("us", "gb", "jp", "vn")
MAX_AGE_DAYS = 7
SEARCH_GAP = 3.2  # seconds between Search API calls: Apple allows about 20 a minute

# Calibrated on 6,902 charting games (us, gb, jp, vn; 2026-10-29) — CHANGELOG v1.1.0.
HIT_RATINGS = 5000         # a search result with this many ratings counts as a hit
COMMON_NAME_WORD = 8       # a word in this many names is a genre word, not a brand
CROWD = 5                  # this many names carrying every word of ours: a crowded name
ICON_FLAT = 15             # luminance spread of the 4x4 grid below which a hash is noise
ICON_SAME = (6, 12)        # dHash bits, mean colour difference: the same icon
ICON_ALIKE = (10, 15)      # a look-alike
SHINGLE = 6                # words per shingle when comparing descriptions
WORDING_FAIL = (30, 0.20)  # longest verbatim passage (words), share of our description
WORDING_WARN = (20, 0.10)
LEAD = {"the", "a", "an", "my", "your"}  # dropped from the front of a name …
TRAIL = {"game", "games", "app", "free", "hd", "pro", "plus", "lite", "online", "offline",
         "new", "best", "classic", "edition", "deluxe", "mobile", "3d", "2d", "the", "a",
         "of", "and", "for", "with"}     # … and from its end: "Gold Miner Classic" = "gold miner"
STOP = LEAD | TRAIL | {"to", "in", "on", "is"}
CORE_SPLIT = re.compile(r"\s[-–—|:•·~]\s|[:|]|\s[-–—]|[-–—]\s")
LEGAL = re.compile(r"privacy|terms of (?:use|service)|subscription|auto-?renew|payment will be|"
                   r"itunes|apple id|eula|https?://|www\.|@", re.I)


# --------------------------------------------------------------------------- cache

def cache_dir() -> Path:
    env = os.environ.get("APPSTORE_SPAM_GUARD_CACHE", "").strip()
    return Path(env).expanduser() if env else Path.home() / ".cache" / "appstore-spam-guard"


def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(p)


def load_store() -> dict:
    data = _read_json(cache_dir() / "store.json", {})
    if data.get("version") != 1:
        data = {"version": 1, "charts": {}, "searches": {}, "apps": {}}
    return data


def save_store(store: dict) -> None:
    _write_json(cache_dir() / "store.json", store)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def age_days(iso: str | None) -> float:
    if not iso:
        return float("inf")
    try:
        then = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return float("inf")
    return (datetime.now(timezone.utc) - then).total_seconds() / 86400


# --------------------------------------------------------------------------- network

def get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code not in (403, 429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, OSError):
            if attempt == 2:
                raise
        time.sleep(4 * (attempt + 1))
    raise OSError(f"unreachable: {url}")


def chart_url(cc: str, feed: str, genre: int) -> str:
    return f"https://itunes.apple.com/{cc}/rss/{FEEDS[feed]}/limit=100/genre={genre}/json"


def parse_chart(data: dict, cc: str, feed: str, genre: int) -> list[dict]:
    entries = data.get("feed", {}).get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]
    out = []
    for rank, e in enumerate(entries, 1):
        attrs = e.get("id", {}).get("attributes", {})
        if not attrs.get("im:id"):
            continue
        images = e.get("im:image", [])
        out.append({
            "id": attrs["im:id"], "bundle": attrs.get("im:bundleId", ""), "cc": cc,
            "name": e.get("im:name", {}).get("label", ""),
            "seller": e.get("im:artist", {}).get("label", ""),
            "url": e.get("id", {}).get("label", "").split("?")[0],
            "icon": images[-1]["label"] if images else "",
            "description": e.get("summary", {}).get("label", ""),
            "chart": f"{cc}/{feed}/{GAME_GENRES[genre]}#{rank}", "rank": rank,
        })
    return out


def merge(store: dict, app: dict) -> None:
    """One entry per app id. A storefront names an app in its own language, so every name
    is kept for matching; the shown name and the description stay English (us, gb) when
    there is one, since the listing under test is compared in English."""
    cur = store["apps"].setdefault(app["id"], {"id": app["id"], "charts": []})
    names = cur.setdefault("names", [])
    if app.get("name") and app["name"] not in names:
        names.append(app["name"])
    english = app.get("cc") in ("us", "gb")
    for k in ("name", "seller", "bundle", "url", "icon", "description", "ratings"):
        v = app.get(k)
        if v in (None, ""):
            continue
        if k in ("name", "url", "description") and cur.get("english") and not english:
            continue
        if (k == "description" and len(cur.get(k) or "") > len(v)
                and (cur.get("english") or not english)):
            continue  # a chart summary can be cut short; keep the longer text
        cur[k] = v
    if english:
        cur["english"] = True
    if app.get("chart"):
        cur["charts"].append(app["chart"])
        cur["best"] = min(cur.get("best", 999), app["rank"])


def chart_rank(c: str) -> int:
    return int(c.rsplit("#", 1)[1])


def refresh_charts(store: dict, countries, log=print) -> None:
    jobs = [(cc, f, g) for cc in countries for f in FEEDS for g in GAME_GENRES]
    for a in store["apps"].values():
        a["charts"] = []
        a.pop("best", None)
    failed: list[str] = []
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(get, chart_url(*j)): j for j in jobs}
        for n, fut in enumerate(as_completed(futs), 1):
            cc, feed, genre = futs[fut]
            try:
                apps = parse_chart(json.loads(fut.result()), cc, feed, genre)
            except Exception:  # one missing chart must not sink the index
                failed.append(f"{cc}/{feed}/{GAME_GENRES[genre]}")
                continue
            for app in apps:
                merge(store, app)
            if n % 50 == 0:
                log(f"  charts {n}/{len(jobs)}")
    searched = {i for s in store["searches"].values() for i in s["ids"]}
    store["apps"] = {k: a for k, a in store["apps"].items() if a["charts"] or k in searched}
    for a in store["apps"].values():
        a["charts"] = sorted(set(a["charts"]), key=chart_rank)[:6]
    store["charts"] = {"built": now_iso(), "countries": list(countries),
                       "fetched": len(jobs) - len(failed), "failed": failed}


def charts_fresh(store: dict, countries) -> bool:
    c = store.get("charts") or {}
    return (age_days(c.get("built")) < MAX_AGE_DAYS
            and set(countries) <= set(c.get("countries", [])))


_last_search = 0.0


def search(store: dict, term: str, country: str = "us", offline: bool = False) -> list[str]:
    """Ids of the games App Store search returns for term (cached 7 days)."""
    global _last_search
    key = f"{country}|{' '.join(term.lower().split())}"
    hit = store["searches"].get(key)
    if hit and (offline or age_days(hit["at"]) < MAX_AGE_DAYS):
        return hit["ids"]
    if offline:
        return []
    wait = SEARCH_GAP - (time.time() - _last_search)
    if wait > 0:
        time.sleep(wait)
    _last_search = time.time()
    q = urllib.parse.urlencode({"term": term, "country": country, "entity": "software",
                                "limit": 50})
    data = json.loads(get(f"https://itunes.apple.com/search?{q}"))
    ids: list[str] = []
    for r in data.get("results", []):
        if "6014" not in [str(g) for g in r.get("genreIds", [])]:
            continue  # not a game
        aid = str(r["trackId"])
        merge(store, {"id": aid, "cc": country, "name": r.get("trackName", ""),
                      "seller": r.get("sellerName") or r.get("artistName", ""),
                      "bundle": r.get("bundleId", ""),
                      "url": (r.get("trackViewUrl") or "").split("?")[0],
                      "icon": r.get("artworkUrl100", ""),
                      "description": r.get("description", ""),
                      "ratings": r.get("userRatingCount")})
        ids.append(aid)
    store["searches"][key] = {"at": now_iso(), "ids": ids}
    return ids


# --------------------------------------------------------------------------- icons

def pixels(img) -> list:
    flat = getattr(img, "get_flattened_data", None)  # Pillow ≥ 12.1; getdata goes in 14
    return list(flat() if flat else img.getdata())


def dhash(img, size: int = 8) -> int:
    from PIL import Image
    g = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = pixels(g)
    bits = 0
    for row in range(size):
        for col in range(size):
            a = px[row * (size + 1) + col]
            b = px[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if a > b else 0)
    return bits


def icon_print(img) -> str:
    """'<dHash hex>/<4x4 RGB means hex>': the shape and the colours of an icon."""
    from PIL import Image
    rgb = img.convert("RGB")
    thumb = rgb.resize((4, 4), Image.BOX)
    colours = bytes(v for px in pixels(thumb) for v in px)
    return f"{dhash(rgb):016x}/{colours.hex()}"


def icon_prints(urls, offline: bool = False, log=print) -> dict[str, str]:
    """Icon prints by URL, downloading the ones not cached yet (needs Pillow)."""
    path = cache_dir() / "icons.json"
    cache: dict[str, str] = _read_json(path, {})
    todo = [u for u in dict.fromkeys(urls) if u and u not in cache]
    if todo and not offline:
        from PIL import Image

        def job(u: str):
            try:
                with Image.open(io.BytesIO(get(u, timeout=20))) as im:
                    return u, icon_print(im)
            except Exception:  # a dead or odd image costs one comparison, not the run
                return u, None

        with ThreadPoolExecutor(12) as ex:
            for n, (u, p) in enumerate(ex.map(job, todo), 1):
                if p:
                    cache[u] = p
                if n % 1000 == 0:
                    log(f"  icons {n}/{len(todo)}")
        _write_json(path, cache)
    return {u: cache[u] for u in urls if u in cache}


def _split_print(p: str) -> tuple[int, bytes]:
    shape, colours = p.split("/")
    return int(shape, 16), bytes.fromhex(colours)


def spread(colours: bytes) -> float:
    """How far an icon is from one flat colour (0 = flat); below ICON_FLAT a hash is noise."""
    lum = [0.299 * colours[k] + 0.587 * colours[k + 1] + 0.114 * colours[k + 2]
           for k in range(0, len(colours), 3)]
    return statistics.pstdev(lum)


# --------------------------------------------------------------------------- compare

def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", re.sub(r"[™®©'’]", "", s))
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def name_words(s: str) -> list[str]:
    return re.findall(r"[^\W_]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", fold(s)).lower())


def core(name: str) -> str:
    """The brand part of a store name: 'Block Blast!' and 'Block Blast - Puzzle' → 'block blast'."""
    w = name_words(CORE_SPLIT.split(fold(name), maxsplit=1)[0])
    while w and w[0] in LEAD:
        w.pop(0)
    while w and w[-1] in TRAIL:
        w.pop()
    return " ".join(w)


def is_hit(app: dict) -> bool:
    return bool(app.get("charts")) or (app.get("ratings") or 0) >= HIT_RATINGS


def label(app: dict) -> str:
    bits = [app.get("seller", "")]
    if app.get("charts"):
        bits.append(app["charts"][0])
    if app.get("ratings"):
        bits.append(f"{app['ratings']:,} ratings")
    return f"{app['name']} ({'; '.join(b for b in bits if b)}) {app.get('url', '')}".strip()


def _shingles(w: list[str]) -> list[int]:
    return [hash(tuple(w[i:i + SHINGLE])) for i in range(len(w) - SHINGLE + 1)]


class Market:
    """The index, ready to compare one app with."""

    def __init__(self, store: dict, own_bundle: str = "", prints: dict | None = None):
        self.apps = [a for a in store["apps"].values()
                     if a.get("name") and not (own_bundle and a.get("bundle") == own_bundle)]
        self.prints = prints or {}
        # Every storefront's name of the app ('Block Blast！', 'ブロックブラスト (Block Blast)').
        self.cores = {a["id"]: [c for c in dict.fromkeys(map(core, a.get("names") or [a["name"]]))
                                if c]
                      for a in self.apps}
        self.df = Counter(t for cs in self.cores.values() for t in {t for c in cs for t in c.split()})
        self._descs: list[str] | None = None
        self._desc_df: dict[str, int] = {}

    def desc_df(self, phrase: str) -> int:
        """How many descriptions use the phrase: a brand is rare there, plain English is not."""
        if self._descs is None:
            self._descs = [" " + " ".join(name_words(a.get("description", ""))) + " "
                           for a in self.apps]
        if phrase not in self._desc_df:
            self._desc_df[phrase] = sum(1 for d in self._descs if f" {phrase} " in d)
        return self._desc_df[phrase]

    def distinctive(self, c: str) -> bool:
        """A brand, not a genre label or plain English: a word few other names use, and a
        phrase few descriptions use ('Wordscapes', 'Gossip Harbor'; not 'Chess', 'Boss Fight',
        'Pixel Art')."""
        toks = [t for t in c.split() if not t.isdigit()]
        if not any(self.df[t] < COMMON_NAME_WORD for t in toks if t not in STOP):
            return False
        if len(toks) == 1 and len(toks[0]) < 4:
            return False
        return self.desc_df(c) <= 2  # its own description and one more

    RELATIONS = ("is the name of", "contains the name of", "is part of the name of",
                 "looks like the name of")

    def relation(self, c: str, d: str) -> int | None:
        """How our name core c relates to a store name core d, strongest first."""
        if d == c:
            return 0
        if f" {d} " in f" {c} " and self.distinctive(d):
            return 1
        if f" {c} " in f" {d} " and self.distinctive(c):
            return 2
        if min(len(c), len(d)) >= 6:
            sm = difflib.SequenceMatcher(None, c, d)
            if sm.quick_ratio() >= 0.88 and sm.ratio() >= 0.88:
                return 3
        return None

    def name_rows(self, name: str) -> list[dict]:
        c = core(name)
        mine = {t for t in c.split() if not t.isdigit() and t not in STOP}
        if not mine:
            return [row("market.name", "SKIP", f"the name \"{name}\" has no words to compare")]
        found: list[tuple[str, dict]] = []
        crowd: list[dict] = []
        for a in self.apps:
            cores = self.cores[a["id"]]
            if any(mine <= set(d.split()) for d in cores):
                crowd.append(a)
            rels = [r for r in (self.relation(c, d) for d in cores) if r is not None]
            if rels:
                found.append((self.RELATIONS[min(rels)], a))
        found.sort(key=lambda x: self.RELATIONS.index(x[0]))
        rows = []
        hard = [(k, a) for k, a in found if k != "looks like the name of" and is_hit(a)]
        soft = [(k, a) for k, a in found if (k, a) not in hard]
        if hard or soft:
            k, a = (hard or soft)[0]
            rows.append(row(
                "market.name", "FAIL" if hard else "WARN",
                f"\"{name}\" {k} {'a charting game' if is_hit(a) else 'a game on the store'}: "
                f"{a['name']}",
                "; ".join(f"{k2} {label(a2)}" for k2, a2 in (hard + soft)[:4]),
                "pick a name no game on the store uses (brand-name-checker): a hit's name in "
                "yours reads as a copy (4.1, 2.3.7), and App Store Connect refuses taken names"))
        else:
            rows.append(row("market.name", "PASS",
                            f"no game among {len(self.apps):,} uses, contains or nearly "
                            f"matches \"{name}\""))
        if len(crowd) >= CROWD:
            crowd.sort(key=lambda a: a.get("best", 999))
            rows.append(row(
                "market.crowded-name", "WARN",
                f"{len(crowd)} games on the charts or in search already carry \"{c}\" in "
                "their names",
                "; ".join(label(a) for a in crowd[:5]),
                "a name made of genre words sits among look-alikes; give it a word of its own"))
        return rows

    def listing_rows(self, fields: list[tuple[str, str, str]], name: str,
                     headline: set[str]) -> list[dict]:
        """Names of charting games in the subtitle, keywords, promo text or description."""
        own = f" {core(name)} "
        hits = [(a, d) for a in self.apps if is_hit(a) for d in self.cores[a["id"]]]
        heads: list[str] = []
        body: list[str] = []
        for field, src, text in fields:
            if field == "name":
                continue
            # A name never spans a comma, quote or sentence break: '"pixel", "flow"' is two words.
            for part in re.split(r'[,;!?"“”()\[\]\n]|\.\s', text):
                wt = " " + " ".join(name_words(part)) + " "
                for a, d in hits:
                    if f" {d} " in wt and f" {d} " not in own and self.distinctive(d):
                        ev = f"{src} [{field}]: \"{d}\" = {label(a)}"
                        (heads if field in headline else body).append(ev)
        if heads:
            return [row("market.listing-names", "FAIL",
                        "the subtitle, keywords or promotional text use a charting game's name",
                        "; ".join(sorted(set(heads))[:5]),
                        "Guideline 2.3.7: no other app's name in the metadata; describe what "
                        "your game does instead")]
        if body:
            return [row("market.listing-names", "WARN",
                        "the description mentions a charting game's name",
                        "; ".join(sorted(set(body))[:5]),
                        "drop the other game's name unless it is a plain word here")]
        return [row("market.listing-names", "PASS",
                    f"the listing names none of the {len({a['id'] for a, _ in hits}):,} "
                    "charting games")]

    def icon_rows(self, ours: str, where: str) -> list[dict]:
        shape, colours = _split_print(ours)
        flat = spread(colours) < ICON_FLAT
        close: list[tuple[int, float, dict]] = []
        nearest: tuple[int, float, dict] | None = None
        compared = 0
        for a in self.apps:
            p = self.prints.get(a.get("icon", ""))
            if not p:
                continue
            compared += 1
            s2, c2 = _split_print(p)
            d = bin(shape ^ s2).count("1")
            if (flat or spread(c2) < ICON_FLAT) and d > 2:
                continue  # one flat colour: its hash bits are noise
            cd = sum(abs(x - y) for x, y in zip(colours, c2)) / len(colours)
            if nearest is None or d + cd / 3 < nearest[0] + nearest[1] / 3:
                nearest = (d, cd, a)  # shape and colour together: 3 colour steps ≈ 1 bit
            if d <= ICON_ALIKE[0] and cd <= ICON_ALIKE[1]:
                close.append((d, cd, a))
        if not compared:
            return [row("market.icon", "WARN", "no icon prints in the index to compare with",
                        where, "run scripts/market.py refresh online")]
        close.sort(key=lambda x: (x[0], x[1]))
        ev = "; ".join(f"{label(a)}: {d}/64 bits, colour {cd:.0f}" for d, cd, a in close[:4])
        note = " (our icon is nearly one flat colour: only near-copies are caught)" if flat else ""
        same = [x for x in close if x[0] <= ICON_SAME[0] and x[1] <= ICON_SAME[1]]
        if same:
            return [row("market.icon", "FAIL",
                        f"the icon is near-identical to {same[0][2]['name']}'s{note}",
                        f"{where} vs {ev}",
                        "draw an icon of your own game's character or mechanic")]
        if close:
            return [row("market.icon", "WARN",
                        f"the icon looks like {close[0][2]['name']}'s{note}",
                        f"{where} vs {ev}",
                        "compare them side by side (J3); change the subject, layout or colours "
                        "if a player could mistake one for the other")]
        closest = (f"; closest: {label(nearest[2])} at {nearest[0]}/64 bits, colour "
                   f"{nearest[1]:.0f}" if nearest else "")
        return [row("market.icon", "PASS",
                    f"the icon looks like none of {compared:,} store icons{note}",
                    where + closest)]

    def wording_rows(self, text: str, src: str) -> list[dict]:
        kept = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if not LEGAL.search(s)]
        w = name_words(" ".join(kept))
        if len(w) < 3 * SHINGLE:
            return [row("market.wording", "SKIP", "the description is too short to compare", src)]
        mine = _shingles(w)
        mset = set(mine)
        shared: dict[str, set[int]] = {}
        df: Counter = Counter()
        for a in self.apps:
            common = mset.intersection(_shingles(name_words(a.get("description", ""))))
            if common:
                shared[a["id"]] = common
                df.update(common)
        best = (0, 0.0, None, 0)  # passage words, share, app, start
        for a in self.apps:
            common = {x for x in shared.get(a["id"], ()) if df[x] < 3}  # 3+ apps: boilerplate
            if not common:
                continue
            run = longest = start = 0
            for i, x in enumerate(mine):
                run = run + 1 if x in common else 0
                if run > longest:
                    longest, start = run, i - run + 1
            words_ = longest + SHINGLE - 1
            share = len(common) / len(mset)
            if (words_, share) > best[:2]:
                best = (words_, share, a, start)
        n, share, a, start = best
        if a is None:
            return [row("market.wording", "PASS",
                        f"the description shares no passage with any of {len(self.apps):,} "
                        "store descriptions", src)]
        passage = " ".join(w[start:start + n])
        ev = f"{src}: {n} words in a row and {share:.0%} of ours also in {label(a)}: “{passage[:200]}”"
        if n >= WORDING_FAIL[0] or share >= WORDING_FAIL[1]:
            verdict = "FAIL"
        elif n >= WORDING_WARN[0] or share >= WORDING_WARN[1]:
            verdict = "WARN"
        else:
            return [row("market.wording", "PASS",
                        f"no description among {len(self.apps):,} shares more than {n} words "
                        "in a row with ours", f"closest: {label(a)}")]
        return [row("market.wording", verdict,
                    f"the description repeats {a['name']}'s wording", ev,
                    "write the description from your own game; copied store text is what "
                    "4.3 reviews and duplicate-content filters look for first")]


def row(id_: str, verdict: str, summary: str, evidence: str = "", fix: str = "") -> dict:
    return {"id": id_, "group": "market", "verdict": verdict, "summary": summary,
            "evidence": evidence, "fix": fix}


# --------------------------------------------------------------------------- cli

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="App Store game index for appstore-spam-guard")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("refresh", help="fetch the charts (and icon prints) again")
    r.add_argument("--countries", default=",".join(DEFAULT_COUNTRIES))
    r.add_argument("--force", action="store_true", help="even when younger than 7 days")
    s = sub.add_parser("search", help="add App Store search results for terms")
    s.add_argument("terms", nargs="+")
    s.add_argument("--country", default="us")
    sub.add_parser("stats", help="what the index holds")
    args = ap.parse_args(argv)

    log = lambda m: print(m, file=sys.stderr)  # noqa: E731
    store = load_store()
    if args.cmd == "refresh":
        countries = [c.strip().lower() for c in args.countries.split(",") if c.strip()]
        if args.force or not charts_fresh(store, countries):
            log(f"fetching {len(countries) * len(FEEDS) * len(GAME_GENRES)} charts …")
            refresh_charts(store, countries, log)
            save_store(store)
        try:
            import PIL  # noqa: F401
            icon_prints([a.get("icon", "") for a in store["apps"].values()], log=log)
        except ImportError:
            log("Pillow is not installed: no icon prints")
    elif args.cmd == "search":
        for t in args.terms:
            ids = search(store, t, args.country)
            log(f"{t}: {len(ids)} games")
        save_store(store)
    c = store.get("charts") or {}
    icons = _read_json(cache_dir() / "icons.json", {})
    with_icon = sum(1 for a in store["apps"].values() if a.get("icon") in icons)
    print(json.dumps({"apps": len(store["apps"]), "charts_built": c.get("built"),
                      "countries": c.get("countries"), "charts_fetched": c.get("fetched"),
                      "charts_failed": c.get("failed"), "searches": len(store["searches"]),
                      "icon_prints": with_icon, "cache": str(cache_dir())}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
