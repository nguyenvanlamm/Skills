#!/usr/bin/env python3
"""YouTube research with the official Data API v3. Standard library only.

Subcommands
  find     Rank young, fast-growing channels for a set of keywords.
  analyze  Summarise one channel's recent uploads (format signals).

Auth   An API key in $YOUTUBE_API_KEY or --api-key. Read-only, public data.
Quota  search.list costs 100 units per page; every other call here costs 1.
       The default project quota is 10,000 units/day, so keep --pages low.

Examples
  python yt_research.py find -k "lịch sử thế giới" -k "giải thích khoa học" \
      --region VN --lang vi --max-channel-age 180 --out research/
  python yt_research.py analyze @somehandle --recent 30 --out research/
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.googleapis.com/youtube/v3/"
UTC = dt.timezone.utc


# --------------------------------------------------------------------------- #
# API client
# --------------------------------------------------------------------------- #
class Client:
    def __init__(self, key: str):
        self.key = key
        self.units = 0

    def get(self, endpoint: str, cost: int = 1, soft: bool = False, **params):
        """GET one API page. With soft=True a 4xx returns None instead of exiting."""
        params = {k: v for k, v in params.items() if v not in (None, "")}
        params["key"] = self.key
        url = f"{API}{endpoint}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                self.units += cost
                return json.load(resp)
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8", "replace")
            try:
                detail = json.loads(body)["error"]
                reason = (detail.get("errors") or [{}])[0].get("reason", "")
                message = detail.get("message", body)
            except Exception:
                reason, message = "", body[:300]
            if soft and err.code in (403, 404) and reason != "quotaExceeded":
                return None
            hints = {
                "quotaExceeded": "Daily quota is used up. It resets at midnight Pacific time.",
                "keyInvalid": "The API key is wrong. Check $YOUTUBE_API_KEY.",
                "accessNotConfigured": "Enable 'YouTube Data API v3' for this Google Cloud project.",
            }
            hint = hints.get(reason, "")
            sys.exit(f"YouTube API error {err.code} ({reason}): {message} {hint}".strip())
        except urllib.error.URLError as err:
            sys.exit(
                f"Cannot reach googleapis.com ({err.reason}). This script needs open "
                "internet access; a sandbox with a restricted network cannot run it."
            )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def parse_time(value: str) -> dt.datetime:
    value = re.sub(r"\.\d+", "", value).replace("Z", "+00:00")
    return dt.datetime.fromisoformat(value)


def parse_duration(iso: str | None) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def chunks(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def fmt_num(n: float) -> str:
    n = float(n)
    for unit, div in (("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return f"{n:.0f}"


def fmt_dur(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


# --------------------------------------------------------------------------- #
# Fetchers
# --------------------------------------------------------------------------- #
def fetch_channels(client: Client, ids: list[str], now: dt.datetime) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for batch in chunks(ids, 50):
        data = client.get(
            "channels", part="snippet,statistics,contentDetails", id=",".join(batch), maxResults=50
        )
        for item in data.get("items", []):
            out[item["id"]] = channel_record(item, now)
    return out


def channel_record(item: dict, now: dt.datetime) -> dict:
    sn, st = item.get("snippet", {}), item.get("statistics", {})
    created = parse_time(sn["publishedAt"])
    handle = sn.get("customUrl") or ""
    age_days = max((now - created).days, 1)
    total_views = to_int(st.get("viewCount"))
    return {
        "id": item["id"],
        "title": sn.get("title", ""),
        "handle": handle,
        "url": f"https://www.youtube.com/{handle}" if handle else f"https://www.youtube.com/channel/{item['id']}",
        "description": (sn.get("description") or "")[:500],
        "country": sn.get("country"),
        "created": created.date().isoformat(),
        "age_days": age_days,
        "subscribers": None if st.get("hiddenSubscriberCount") else to_int(st.get("subscriberCount")),
        "total_views": total_views,
        "video_count": to_int(st.get("videoCount")),
        "views_per_day": round(total_views / age_days, 1),
        "uploads_playlist": item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
    }


def fetch_recent_videos(client: Client, playlist_id: str | None, limit: int) -> list[dict]:
    if not playlist_id:
        return []
    ids: list[str] = []
    token = None
    while len(ids) < limit:
        data = client.get(
            "playlistItems",
            soft=True,
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=min(50, limit - len(ids)),
            pageToken=token,
        )
        if not data:
            break
        ids += [it["contentDetails"]["videoId"] for it in data.get("items", [])]
        token = data.get("nextPageToken")
        if not token:
            break
    videos: list[dict] = []
    for batch in chunks(ids, 50):
        data = client.get("videos", part="snippet,statistics,contentDetails", id=",".join(batch))
        for it in data.get("items", []):
            sn, st = it.get("snippet", {}), it.get("statistics", {})
            thumbs = sn.get("thumbnails", {})
            thumb = (thumbs.get("maxres") or thumbs.get("high") or thumbs.get("default") or {}).get("url")
            videos.append(
                {
                    "id": it["id"],
                    "url": f"https://www.youtube.com/watch?v={it['id']}",
                    "title": sn.get("title", ""),
                    "published": sn.get("publishedAt"),
                    "views": to_int(st.get("viewCount")),
                    "likes": to_int(st.get("likeCount")),
                    "comments": to_int(st.get("commentCount")),
                    "duration_s": parse_duration(it.get("contentDetails", {}).get("duration")),
                    "tags": sn.get("tags", []),
                    "category_id": sn.get("categoryId"),
                    "language": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage"),
                    "live": sn.get("liveBroadcastContent", "none") != "none",
                    "thumbnail": thumb,
                    "description_head": (sn.get("description") or "")[:300],
                }
            )
    videos.sort(key=lambda v: v["published"] or "", reverse=True)
    return videos


def summarise_videos(videos: list[dict]) -> dict:
    """Signals from a sample of recent uploads. Medians resist one viral outlier."""
    views = [v["views"] for v in videos]
    durations = [v["duration_s"] for v in videos if v["duration_s"]]
    times = sorted(parse_time(v["published"]) for v in videos if v["published"])
    span_days = (times[-1] - times[0]).total_seconds() / 86400 if len(times) > 1 else 0
    return {
        "sampled_videos": len(videos),
        "median_views": int(statistics.median(views)) if views else 0,
        "max_views": max(views) if views else 0,
        "median_duration_s": int(statistics.median(durations)) if durations else 0,
        "share_under_3min": round(sum(d <= 180 for d in durations) / len(durations), 2) if durations else None,
        "uploads_per_week": round((len(times) - 1) / span_days * 7, 1) if span_days > 0 else None,
        "last_upload": times[-1].date().isoformat() if times else None,
    }


# --------------------------------------------------------------------------- #
# find
# --------------------------------------------------------------------------- #
def momentum_score(row: dict, max_age: int) -> float:
    """Sorting aid only, not a verdict. Each term is roughly 0..7, 0..7, 0..1, 0..1.

    views/day and median views are log-scaled so one huge channel does not bury
    the rest; views-per-subscriber rewards videos that travel beyond the existing
    audience (the algorithm is pushing them); youth rewards doing it quickly.
    """
    reach = min(row.get("views_per_sub") or 0, 5) / 5
    youth = 1 - min(row["age_days"], max_age) / max_age
    return round(
        math.log10(1 + row["views_per_day"]) + math.log10(1 + row["median_views"]) + reach + youth, 2
    )


def cmd_find(args, client: Client) -> None:
    now = dt.datetime.now(UTC)
    keywords = [k.strip() for raw in args.keyword for k in raw.split(",") if k.strip()]
    if not keywords:
        sys.exit("Give at least one --keyword.")
    after = (now - dt.timedelta(days=args.published_within)).strftime("%Y-%m-%dT%H:%M:%SZ")

    found: dict[str, set[str]] = {}
    for kw in keywords:
        token = None
        for _ in range(args.pages):
            data = client.get(
                "search",
                cost=100,
                part="snippet",
                type="video",
                q=kw,
                order="viewCount",
                publishedAfter=after,
                maxResults=50,
                regionCode=args.region,
                relevanceLanguage=args.lang,
                videoDuration=None if args.duration == "any" else args.duration,
                pageToken=token,
            )
            for item in data.get("items", []):
                found.setdefault(item["snippet"]["channelId"], set()).add(kw)
            token = data.get("nextPageToken")
            if not token:
                break
    print(f"[find] {len(found)} channels behind recent high-view videos", file=sys.stderr)

    channels = fetch_channels(client, list(found), now)
    young = [
        c for c in channels.values()
        if c["age_days"] <= args.max_channel_age and c["video_count"] >= args.min_videos
    ]
    young.sort(key=lambda c: c["views_per_day"], reverse=True)
    young = young[: args.sample_limit]
    print(f"[find] {len(young)} are at most {args.max_channel_age} days old; sampling uploads", file=sys.stderr)

    rows = []
    for ch in young:
        videos = fetch_recent_videos(client, ch["uploads_playlist"], args.recent)
        if not videos:
            continue
        stats = summarise_videos(videos)
        if stats["median_views"] < args.min_median_views:
            continue
        row = {**ch, **stats}
        subs = row["subscribers"]
        row["views_per_sub"] = round(stats["median_views"] / subs, 2) if subs else None
        row["matched_keywords"] = sorted(found[ch["id"]])
        row["top_videos"] = [
            {k: v[k] for k in ("title", "views", "duration_s", "published", "url", "thumbnail")}
            for v in sorted(videos, key=lambda v: v["views"], reverse=True)[:5]
        ]
        row["score"] = momentum_score(row, args.max_channel_age)
        row.pop("uploads_playlist", None)
        rows.append(row)
    rows.sort(key=lambda r: r["score"], reverse=True)
    rows = rows[: args.top]

    lines = [
        f"# Young channels with momentum ({now.date().isoformat()})",
        "",
        f"Keywords: {', '.join(keywords)} | region={args.region or '-'} lang={args.lang or '-'} "
        f"| channel age <= {args.max_channel_age}d | API units used: {client.units}",
        "",
        "| # | Channel | Age (d) | Subs | Videos | Views/day | Median views | Views/sub | Uploads/wk | Median length | <3 min | Score |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | [{r['title']}]({r['url']}) | {r['age_days']} | "
            f"{fmt_num(r['subscribers']) if r['subscribers'] is not None else 'hidden'} | {r['video_count']} | "
            f"{fmt_num(r['views_per_day'])} | {fmt_num(r['median_views'])} | "
            f"{r['views_per_sub'] if r['views_per_sub'] is not None else '-'} | "
            f"{r['uploads_per_week'] if r['uploads_per_week'] is not None else '-'} | "
            f"{fmt_dur(r['median_duration_s'])} | "
            f"{int(r['share_under_3min'] * 100) if r['share_under_3min'] is not None else '-'}% | {r['score']} |"
        )
    if not rows:
        lines.append("| - | No channel passed the filters. Widen keywords, age, or lower --min-median-views. |||||||||||")
    lines += ["", "## Top videos per channel", ""]
    for r in rows:
        lines.append(f"**{r['title']}** ({', '.join(r['matched_keywords'])})")
        for v in r["top_videos"]:
            lines.append(f"- {fmt_num(v['views'])} views, {fmt_dur(v['duration_s'])}: {v['title']} ({v['url']})")
        lines.append("")
    write_outputs(args.out, "channels", {"generated": now.isoformat(), "keywords": keywords, "channels": rows}, lines)


# --------------------------------------------------------------------------- #
# analyze
# --------------------------------------------------------------------------- #
def resolve_channel(client: Client, ref: str) -> dict:
    ref = ref.strip()
    m = re.search(r"(UC[0-9A-Za-z_-]{22})", ref)
    params: dict = {}
    if m:
        params["id"] = m.group(1)
    else:
        h = re.search(r"@([\w.\-]+)", ref)
        if h:
            params["forHandle"] = "@" + h.group(1)
        else:
            data = client.get("search", cost=100, part="snippet", type="channel", q=ref, maxResults=1)
            items = data.get("items", [])
            if not items:
                sys.exit(f"No channel found for '{ref}'. Pass a channel URL, @handle or UC… id.")
            params["id"] = items[0]["snippet"]["channelId"]
    data = client.get("channels", part="snippet,statistics,contentDetails", **params)
    items = data.get("items", [])
    if not items:
        sys.exit(f"No channel found for '{ref}'.")
    return channel_record(items[0], dt.datetime.now(UTC))


def title_patterns(titles: list[str]) -> dict:
    if not titles:
        return {}
    words: collections.Counter = collections.Counter()
    bigrams: collections.Counter = collections.Counter()
    for t in titles:
        toks = [w for w in re.findall(r"[^\W\d_]+", t.lower()) if len(w) > 1]
        words.update(toks)
        bigrams.update(zip(toks, toks[1:]))
    n = len(titles)
    return {
        "median_length_chars": int(statistics.median(len(t) for t in titles)),
        "share_with_number": round(sum(bool(re.search(r"\d", t)) for t in titles) / n, 2),
        "share_question": round(sum("?" in t for t in titles) / n, 2),
        "share_with_caps_word": round(
            sum(any(w.isupper() and len(w) >= 3 for w in re.findall(r"[^\W\d_]+", t)) for t in titles) / n, 2
        ),
        "share_with_separator": round(sum(bool(re.search(r"[|:\-–—]", t)) for t in titles) / n, 2),
        "frequent_words": [w for w, c in words.most_common(15) if c > 1],
        "frequent_bigrams": [" ".join(b) for b, c in bigrams.most_common(10) if c > 1],
    }


def cmd_analyze(args, client: Client) -> None:
    ch = resolve_channel(client, args.channel)
    videos = fetch_recent_videos(client, ch.pop("uploads_playlist"), args.recent)
    if not videos:
        sys.exit("This channel has no public uploads to analyse.")
    stats = summarise_videos(videos)
    median = stats["median_views"] or 1
    for v in videos:
        v["x_median"] = round(v["views"] / median, 1)
    outliers = sorted((v for v in videos if v["x_median"] >= 2), key=lambda v: v["views"], reverse=True)
    weak = sorted((v for v in videos if v["x_median"] <= 0.5), key=lambda v: v["views"])
    tags = collections.Counter(t.lower() for v in videos for t in v["tags"])
    weekdays = collections.Counter(parse_time(v["published"]).strftime("%a") for v in videos)
    hours = collections.Counter(parse_time(v["published"]).hour for v in videos)
    durations = sorted(v["duration_s"] for v in videos if v["duration_s"])
    summary = {
        "channel": ch,
        "stats": stats,
        "duration_range_s": [durations[0], durations[-1]] if durations else None,
        "title_patterns": title_patterns([v["title"] for v in videos]),
        "outlier_titles": title_patterns([v["title"] for v in outliers]) if len(outliers) >= 3 else None,
        "common_tags": [t for t, _ in tags.most_common(20)],
        "upload_weekdays_utc": dict(weekdays.most_common()),
        "upload_hours_utc": dict(sorted(hours.items())),
        "categories": dict(collections.Counter(v["category_id"] for v in videos)),
        "outliers": outliers[:10],
        "underperformers": weak[:5],
        "videos": videos,
    }

    tp = summary["title_patterns"]
    lines = [
        f"# {ch['title']}: format signals",
        "",
        f"{ch['url']} | created {ch['created']} ({ch['age_days']} days) | "
        f"subs {fmt_num(ch['subscribers']) if ch['subscribers'] is not None else 'hidden'} | "
        f"{ch['video_count']} videos | {fmt_num(ch['total_views'])} views | API units used: {client.units}",
        "",
        f"- Sample: last {stats['sampled_videos']} uploads, median {fmt_num(stats['median_views'])} views, "
        f"best {fmt_num(stats['max_views'])}",
        f"- Cadence: {stats['uploads_per_week']} uploads/week, last upload {stats['last_upload']}",
        f"- Length: median {fmt_dur(stats['median_duration_s'])}"
        + (f", range {fmt_dur(durations[0])} to {fmt_dur(durations[-1])}" if durations else "")
        + (f", {int(stats['share_under_3min'] * 100)}% under 3 min" if stats["share_under_3min"] is not None else ""),
        f"- Titles: median {tp.get('median_length_chars')} chars, {int(tp.get('share_with_number', 0) * 100)}% with a number, "
        f"{int(tp.get('share_question', 0) * 100)}% questions, {int(tp.get('share_with_caps_word', 0) * 100)}% with an ALL-CAPS word",
        f"- Recurring title words: {', '.join(tp.get('frequent_words', [])) or '-'}",
        f"- Recurring title phrases: {', '.join(tp.get('frequent_bigrams', [])) or '-'}",
        f"- Common tags: {', '.join(summary['common_tags'][:12]) or '-'}",
        f"- Upload weekdays (UTC): {summary['upload_weekdays_utc']}",
        "",
        "## Outliers (at least 2x the channel median): what the audience rewards",
        "",
    ]
    for v in outliers[:10]:
        lines.append(f"- {v['x_median']}x | {fmt_num(v['views'])} views | {fmt_dur(v['duration_s'])} | {v['title']} ({v['url']})")
    if not outliers:
        lines.append("- none in this sample")
    lines += ["", "## Underperformers (at most 0.5x median): what to avoid", ""]
    for v in weak[:5]:
        lines.append(f"- {v['x_median']}x | {fmt_num(v['views'])} views | {fmt_dur(v['duration_s'])} | {v['title']}")
    if not weak:
        lines.append("- none in this sample")
    lines += ["", "## All sampled uploads (newest first)", ""]
    for v in videos:
        lines.append(f"- {v['published'][:10]} | {fmt_num(v['views'])} | {fmt_dur(v['duration_s'])} | {v['title']}")
    write_outputs(args.out, f"channel_{ch['id']}", summary, lines)


# --------------------------------------------------------------------------- #
def write_outputs(out_dir: str, stem: str, payload: dict, md_lines: list[str]) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{stem}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    text = "\n".join(md_lines) + "\n"
    (out / f"{stem}.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"[saved] {out / (stem + '.md')} and {out / (stem + '.json')}", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api-key", default=os.environ.get("YOUTUBE_API_KEY"))
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("find", help="find young channels with momentum")
    f.add_argument("-k", "--keyword", action="append", default=[], help="repeatable, or comma-separated")
    f.add_argument("--region", default=None, help="ISO country code, e.g. VN, US")
    f.add_argument("--lang", default=None, help="ISO language code, e.g. vi, en")
    f.add_argument("--published-within", type=int, default=30, help="only videos from the last N days (default 30)")
    f.add_argument("--max-channel-age", type=int, default=180, help="channel created within N days (default 180)")
    f.add_argument("--min-videos", type=int, default=3)
    f.add_argument("--min-median-views", type=int, default=1000)
    f.add_argument("--duration", choices=["any", "short", "medium", "long"], default="any",
                   help="API buckets: short <4 min, medium 4-20 min, long >20 min")
    f.add_argument("--pages", type=int, default=1, help="search pages per keyword, 100 quota units each")
    f.add_argument("--recent", type=int, default=12, help="uploads sampled per channel")
    f.add_argument("--sample-limit", type=int, default=60, help="max young channels to sample")
    f.add_argument("--top", type=int, default=15)
    f.add_argument("--out", default="research")

    a = sub.add_parser("analyze", help="summarise one channel's recent uploads")
    a.add_argument("channel", help="channel URL, @handle, UC… id, or a name to search for")
    a.add_argument("--recent", type=int, default=30)
    a.add_argument("--out", default="research")

    args = p.parse_args()
    if not args.api_key:
        sys.exit("Missing API key. Set $YOUTUBE_API_KEY or pass --api-key (see references/setup.md).")
    client = Client(args.api_key)
    {"find": cmd_find, "analyze": cmd_analyze}[args.cmd](args, client)


if __name__ == "__main__":
    main()
