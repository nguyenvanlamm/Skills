#!/usr/bin/env python3
"""Fetch top trending topics from Exploding Topics API and output as JSON."""

import json
import sys
import urllib.request
import urllib.error

API_URL = "https://explodingtopics.com/api/trends?sort=growth&period=24&size=50"
TIMEOUT = 30
TOP_N = 15


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_growth(raw) -> tuple[float, str]:
    """Return (percentage, how_it_was_derived).

    The upstream field is undocumented and has been seen both as a ratio
    (0.3233 -> 32.3%) and as an already-computed percentage (3233). Blindly
    multiplying by 100 turns the second form into 323300%, and every idea then
    gets ranked on a number that is 100x wrong. Decide per value, and report
    which branch was taken so a reader can spot a bad guess.
    """
    try:
        raw = float(raw)
    except (TypeError, ValueError):
        return 0.0, "unparseable"
    if raw <= 100:                      # ratio, or a genuinely small percentage
        return round(raw * 100, 1), "ratio x100"
    return round(raw, 1), "already percent"


def extract_topics(api_data: dict) -> list[dict]:
    trends = api_data.get("trends", [])
    results = []
    for t in trends:
        raw_growth = t.get("growth", {}).get("24", 0)
        growth_pct, growth_basis = normalize_growth(raw_growth)
        volume = (
            t.get("keywordDataGlobal", {}).get("vol", 0)
            or t.get("searchVolume", 0)
            or 0
        )
        path = t.get("path", "")
        results.append({
            "name": t.get("keyword", "Unknown"),
            "growth_pct": growth_pct,
            "growth_raw": raw_growth,
            "growth_basis": growth_basis,
            "search_volume": volume,
            "path": path,
            "url": f"https://explodingtopics.com/{path}" if path else "",
        })
    results.sort(key=lambda x: x["growth_pct"], reverse=True)
    return results[:TOP_N]


def main():
    try:
        api_data = fetch_json(API_URL)
    except Exception as e:
        print(json.dumps({"error": f"Failed to fetch API: {e}"}))
        sys.exit(1)

    topics = extract_topics(api_data)
    if not topics:
        print(json.dumps({"error": "No topics found in API response"}))
        sys.exit(1)

    print(json.dumps({
        "topics": topics,
        "count": len(topics),
        "total_available": api_data.get("total", 0),
        "source": "https://explodingtopics.com",
    }, indent=2))


if __name__ == "__main__":
    main()
