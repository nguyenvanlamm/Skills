"""Upload a finished level to YouTube: the 16:9 video with its thumbnail, then the Short.

Usage:
  uv run python upload.py auth
  uv run python upload.py plan <episodes/NAME/LEVEL> [--publish-at WHEN] [--short-publish-at WHEN] [--only long|short]
  uv run python upload.py push <episodes/NAME/LEVEL> --publish-at WHEN [--short-publish-at WHEN] [--only long|short]

WHEN is an ISO 8601 time with a time zone, e.g. 2026-11-25T18:00:00+01:00. Videos are always uploaded
as private and scheduled to go public at WHEN. `plan` prints what `push` would send and calls nothing.

Texts and file names come from out/publish.json (written by publish.py). What was uploaded is kept
in out/uploaded.json, written before any byte is sent: running push again continues an unfinished
upload and never posts a finished video twice. run.py never calls this script.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import youtube
from common import load_config, read_json, write_json

KINDS = ("long", "short")
URLS = {"long": "https://www.youtube.com/watch?v={id}", "short": "https://www.youtube.com/shorts/{id}"}
MIN_LEAD = timedelta(minutes=15)  # a time in the past makes YouTube publish at once


def parse_when(text: str, now: datetime) -> datetime:
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{text!r} is not an ISO 8601 time (example: 2026-11-25T18:00:00+01:00)")
    if when.tzinfo is None:
        raise ValueError(f"{text!r} has no time zone; add one, e.g. {text}+01:00")
    if when - now < MIN_LEAD:
        raise ValueError(f"{text} is not at least {int(MIN_LEAD.total_seconds() // 60)} minutes from now; "
                         "YouTube publishes at once when the time has passed")
    return when


def api_time(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def short_description(short: dict, long_url: str, label: str) -> str:
    """The Short's description with a link to the full video, kept above the hashtag line."""
    tail = " ".join(short["hashtags"])
    head = short["description"].removesuffix(tail).rstrip()
    return f"{head}\n\n{label.format(url=long_url)}\n\n{tail}"


def build_jobs(level_dir: Path, cfg: dict, done: dict, kinds: tuple[str, ...], publish_at: str | None,
               short_publish_at: str | None, now: datetime) -> tuple[dict, list[str]]:
    """({kind: what to send}, problems). `done` is out/uploaded.json; finished videos need no schedule."""
    problems: list[str] = []
    out = level_dir / "out"
    try:
        pub = read_json(out / "publish.json")
        checks = read_json(level_dir / "state.json")["steps"]["check"]
    except (OSError, ValueError, KeyError):
        return {}, [f"{level_dir} is not finished: run run.py to the end first (out/publish.json and the video checks are needed)"]
    ucfg = cfg["upload"]
    yt, sh = pub["youtube"], pub["youtube_shorts"]
    sources = {"long": ("16x9", yt), "short": ("short_9x16", sh)}
    jobs: dict = {}

    times: dict[str, datetime | None] = {}
    bad_time = False
    for kind, text in (("long", publish_at), ("short", short_publish_at)):
        try:
            times[kind] = parse_when(text, now) if text else None
        except ValueError as e:
            if not done.get(kind, {}).get("id"):
                problems.append(str(e))
                bad_time = True
            times[kind] = None
    if times["short"] is None and times["long"] is not None and not short_publish_at:
        times["short"] = times["long"] + timedelta(minutes=ucfg["short_delay_minutes"])

    for kind in kinds:
        fmt, block = sources[kind]
        finished = bool(done.get(kind, {}).get("id"))
        path = out / block["file"]
        if not finished:
            if fmt not in checks:
                problems.append(f"{kind}: {block['file']} was never checked; run run.py again")
            elif checks[fmt].get("problems"):
                problems.append(f"{kind}: {block['file']} failed its checks: {checks[fmt]['problems']}")
            if not path.is_file():
                problems.append(f"{kind}: missing {path}")
            if times[kind] is None and not bad_time:
                problems.append(f"{kind}: no publish time; pass --publish-at")
        job = {"kind": kind, "file": str(path), "title": block["title"], "description": block["description"],
               "tags": yt["tags"], "category_id": block["category_id"], "language": block["language"],
               "made_for_kids": block["made_for_kids"], "synthetic_media": ucfg["contains_synthetic_media"],
               "publish_at": api_time(times[kind]) if times[kind] else None, "url": URLS[kind]}
        if kind == "long":
            job["thumbnail"] = str(out / yt["thumbnail_file"])
            if not finished and not Path(job["thumbnail"]).is_file():
                problems.append(f"long: missing {job['thumbnail']}")
        jobs[kind] = job

    long_done = done.get("long", {})
    if "short" in jobs:
        if long_done.get("url"):
            jobs["short"]["description"] = short_description(sh, long_done["url"], ucfg["short_link_label"])
        elif "long" in jobs:
            jobs["short"]["needs_long_url"] = True  # filled in once the long video has an id
        elif not done.get("short", {}).get("id"):
            problems.append("short: the long video is not uploaded yet, so the Short cannot link to it; "
                            "upload the long video first")
    return jobs, problems


def show(jobs: dict, done: dict, say=print) -> None:
    for kind, job in jobs.items():
        state = done.get(kind, {})
        path = Path(job["file"])
        size = f"{path.stat().st_size / 1e6:.1f} MB" if path.is_file() else "missing"
        say(f"[{kind}] {path.name} ({size})")
        if state.get("id"):
            say(f"  already uploaded: {state['url']} ({state.get('privacy')}, public at {state.get('publish_at')})")
            if kind == "long":
                say(f"  thumbnail: {state.get('thumbnail', 'not set')}")
            continue
        if state.get("session"):
            say("  an unfinished upload will be continued")
        say(f"  title: {job['title']}")
        say(f"  private, public at {job['publish_at']} (UTC)" if job["publish_at"] else "  private, no publish time yet")
        say(f"  category {job['category_id']}, language {job['language']}, made for kids: {job['made_for_kids']}, "
            f"altered/synthetic disclosure: {job['synthetic_media']}")
        say(f"  tags ({len(job['tags'])}): {', '.join(job['tags'])}")
        if kind == "long":
            say(f"  thumbnail: {Path(job['thumbnail']).name}")
            say(f"  description: {len(job['description'])} characters (see out/publish.md)")
        else:
            note = "  (+ a link to the long video, added once it has an id)" if job.get("needs_long_url") else ""
            say(f"  description:{note}\n" + "\n".join("    " + line for line in job["description"].splitlines()))


def push(level_dir: Path, jobs: dict, done: dict, cfg: dict, uploader: youtube.Uploader, say=print) -> list[str]:
    """Upload what is not uploaded yet; returns warnings. Raises youtube.UploadError when a video fails."""
    warnings: list[str] = []
    path = level_dir / "out" / "uploaded.json"

    def save() -> None:
        write_json(path, done)

    for kind, job in jobs.items():
        state = done.setdefault(kind, {})
        if state.get("id"):
            say(f"[{kind}] already uploaded: {state['url']}")
        else:
            if job.pop("needs_long_url", False):
                pub = read_json(level_dir / "out" / "publish.json")["youtube_shorts"]
                job["description"] = short_description(pub, done["long"]["url"], cfg["upload"]["short_link_label"])
            say(f"[{kind}] uploading {Path(job['file']).name}")
            youtube.upload_video(job, state, save, uploader, say)
            say(f"  uploaded as {state['privacy']}: {state['url']}")
            if state["privacy"] != "private" or not state.get("publish_at"):
                warnings.append(f"{kind}: YouTube answered privacy={state['privacy']}, publishAt={state.get('publish_at')}; "
                                f"asked for private until {job['publish_at']}. Check the video in YouTube Studio.")
        if kind == "long" and state.get("thumbnail") != "set":
            try:
                uploader.set_thumbnail(state["id"], Path(job["thumbnail"]))
                state["thumbnail"] = "set"
                say("  thumbnail set")
            except (youtube.UploadError, OSError) as e:
                state["thumbnail"] = f"failed: {e}"
                warnings.append(f"long: {e}. The video is uploaded; set the thumbnail in YouTube Studio "
                                "(custom thumbnails need a phone-verified channel) or run push again.")
            save()
    return warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth", help="sign in to the channel's Google account once")
    for name in ("plan", "push"):
        p = sub.add_parser(name)
        p.add_argument("level_dir", type=Path)
        p.add_argument("--publish-at", required=name == "push")
        p.add_argument("--short-publish-at")
        p.add_argument("--only", choices=KINDS)
    args = ap.parse_args(argv)

    if args.cmd == "auth":
        try:
            youtube.authorize()
        except youtube.UploadError as e:
            print(f"FAIL  {e}\nRESULT: FAIL")
            return 1
        print("RESULT: PASS")
        return 0

    d = args.level_dir.resolve()
    cfg = load_config()
    done_path = d / "out" / "uploaded.json"
    done = read_json(done_path) if done_path.is_file() else {}
    kinds = (args.only,) if args.only else KINDS
    jobs, problems = build_jobs(d, cfg, done, kinds, args.publish_at, args.short_publish_at,
                                datetime.now(timezone.utc))
    if jobs:
        show(jobs, done)
    warnings: list[str] = []
    if args.cmd == "plan":
        if not youtube.connected():
            warnings.append(f"YouTube is not connected yet ({youtube.config_dir()}); see references/upload-setup.md")
        if not args.publish_at:
            problems = [p for p in problems if "no publish time" not in p]
            warnings.append("no --publish-at given: push needs one")
    elif not problems:
        try:
            warnings = push(d, jobs, done, cfg, youtube.Uploader(youtube.access_token()))
        except youtube.UploadError as e:
            problems.append(str(e))
    for w in warnings:
        print(f"WARN  {w}")
    for p in problems:
        print(f"FAIL  {p}")
    if problems:
        print("RESULT: FAIL")
        return 1
    print(f"RESULT: PASS{' (nothing was sent)' if args.cmd == 'plan' else f' -> {done_path}'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
