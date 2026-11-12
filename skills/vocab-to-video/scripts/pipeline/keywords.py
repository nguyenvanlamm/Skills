"""Fetch real YouTube search suggestions for an episode, to write titles and tags from.

Usage: uv run python keywords.py <episodes/NAME> ["extra query" ...]

Queries: the seed list in config.json (for A2 and B1) plus any extra queries you pass, typically
the episode's theme ("vocabulaire logement français", "déménager en france"). The result is saved
to <episode>/keywords.json: {"queries": {query: [suggestions]}, "all": [every suggestion]}.

Only the search phrases are sent, to YouTube's public autocomplete endpoint.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from common import LEVELS, load_config, write_json

ENDPOINT = "https://suggestqueries.google.com/complete/search"


def suggest(query: str, lang: str) -> list[str]:
    url = ENDPOINT + "?" + urllib.parse.urlencode({"client": "firefox", "ds": "yt", "hl": lang, "q": query})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return [s for s in json.loads(text)[1] if isinstance(s, str)]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    episode = Path(sys.argv[1]).resolve()
    cfg = load_config()
    queries: list[tuple[str, str]] = []
    for template, lang in cfg["publish"]["seed_queries"]:
        for level in LEVELS if "{level}" in template else ("",):
            queries.append((template.format(level=level), lang))
    queries += [(q, cfg["publish"]["language"]) for q in sys.argv[2:]]

    result: dict[str, list[str]] = {}
    failed = []
    for query, lang in queries:
        try:
            result[query] = suggest(query, lang)
        except Exception as exc:  # network or format error: keep going, report at the end
            failed.append(f"{query}: {exc}")
        time.sleep(0.3)
    if not result:
        print("FAIL no suggestions could be fetched:\n  " + "\n  ".join(failed))
        return 1
    every = sorted({s for group in result.values() for s in group})
    write_json(episode / "keywords.json",
               {"fetched_at": time.strftime("%Y-%m-%d"), "source": "YouTube search suggestions",
                "queries": result, "all": every})
    for query, group in result.items():
        print(f"{query}\n    " + " | ".join(group))
    for f in failed:
        print(f"WARN {f}")
    print(f"RESULT: {len(every)} suggestions -> {episode / 'keywords.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
