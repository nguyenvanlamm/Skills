#!/usr/bin/env python3
"""Fetch top trending topics from Exploding Topics and print them as JSON.

    python3 fetch_trends.py [--limit N] [--min-volume V] [--from-file raw.json]
                            [--save-raw raw.json] [--retries N]

Exit codes: 0 ok · 1 fetch failed / empty · 2 bad arguments.
stdout is always a single JSON object; diagnostics go to stderr.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://explodingtopics.com/api/trends?sort=growth&period=24&size=50"
TIMEOUT = 30
DEFAULT_TOP_N = 15
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def fetch_json(url: str, retries: int) -> dict:
    """GET with exponential backoff on network errors and 429/5xx."""
    delay = 2.0
    last = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
        })
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
        if attempt < retries:
            log(f"attempt {attempt}/{retries} failed ({last}); retrying in {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"gave up after {retries} attempts: {last}")


def normalize_growth(raw) -> tuple[float, str]:
    """Return (percentage, how_it_was_derived).

    Verified against topic pages (2026-09): `growth["24"]` is a **multiplier**.
    2.12 renders as "+212%", and 99 renders as "+99X+" — the upstream cap for
    breakout topics, not 99%. So the value is always multiplied by 100, and a
    capped value is labelled so nobody ranks on "9900%" as if it were measured.
    Values above 100 have not been observed; they are passed through with a
    label in case the API ever emits a pre-computed percentage.
    """
    try:
        raw = float(raw)
    except (TypeError, ValueError):
        return 0.0, "unparseable"
    if raw >= 99 and raw <= 100:
        return round(raw * 100, 1), "capped 99x+ (upstream cap, not a measurement)"
    if raw <= 100:
        return round(raw * 100, 1), "multiplier x100"
    return round(raw, 1), "already percent (unexpected — verify on the topic page)"


def extract_topics(api_data: dict, top_n: int, min_volume: int) -> list[dict]:
    trends = api_data.get("trends") or api_data.get("data") or []
    results = []
    for t in trends:
        growth_field = t.get("growth", {})
        raw_growth = growth_field.get("24", 0) if isinstance(growth_field, dict) else growth_field
        growth_pct, growth_basis = normalize_growth(raw_growth)
        volume = (
            (t.get("keywordDataGlobal") or {}).get("vol", 0)
            or t.get("searchVolume", 0)
            or 0
        )
        try:
            volume = int(volume)
        except (TypeError, ValueError):
            volume = 0
        if volume < min_volume:
            continue
        path = t.get("path", "") or ""
        results.append({
            "name": t.get("keyword") or t.get("name") or "Unknown",
            "growth_pct": growth_pct,
            "growth_raw": raw_growth,
            "growth_basis": growth_basis,
            "search_volume": volume,
            "path": path,
            # Topic pages live under /topic/<path>; the bare path 404s.
            "url": f"https://explodingtopics.com/topic/{path.lstrip('/')}" if path else "",
        })
    results.sort(key=lambda x: x["growth_pct"], reverse=True)
    return results[:top_n]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=DEFAULT_TOP_N, help=f"topics to return (default {DEFAULT_TOP_N})")
    ap.add_argument("--min-volume", type=int, default=0, help="drop topics below this monthly search volume")
    ap.add_argument("--from-file", help="parse a previously saved raw API response instead of fetching")
    ap.add_argument("--save-raw", help="write the raw API response here (for --from-file later)")
    ap.add_argument("--retries", type=int, default=3, help="network attempts before giving up (default 3)")
    args = ap.parse_args()
    if args.limit < 1:
        log("--limit must be >= 1")
        return 2

    try:
        if args.from_file:
            with open(args.from_file, encoding="utf-8") as fh:
                api_data = json.load(fh)
            source = f"file:{args.from_file}"
        else:
            api_data = fetch_json(API_URL, max(1, args.retries))
            source = "https://explodingtopics.com"
    except Exception as e:  # noqa: BLE001 — one JSON error object is the contract
        print(json.dumps({"error": f"Failed to fetch API: {e}", "source": API_URL}))
        return 1

    if args.save_raw and not args.from_file:
        with open(args.save_raw, "w", encoding="utf-8") as fh:
            json.dump(api_data, fh)

    topics = extract_topics(api_data, args.limit, args.min_volume)
    if not topics:
        print(json.dumps({"error": "No topics found in API response", "source": source}))
        return 1

    print(json.dumps({
        "topics": topics,
        "count": len(topics),
        "requested": args.limit,
        "total_available": api_data.get("total", len(api_data.get("trends", []))),
        "source": source,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
