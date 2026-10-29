#!/usr/bin/env python3
"""Per-team App Store submission ledger for appstore-spam-guard.

    python3 ledger.py record --team T --app NAME --bundle ID \\
        --event submitted|approved|rejected|withdrawn \\
        [--guideline "4.3(a)"] [--extended-review] [--date YYYY-MM-DD] [--note TEXT]
    python3 ledger.py check --team T [--bundle ID] [--app NAME] [--days 14]
    python3 ledger.py show [--team T]
    python3 ledger.py stats [--team T]

A `submitted` event keeps a summary of the scan behind it (--scan FILE, or the
latest submit-mode scan.py run for that bundle); `stats` then sets each
submission's verdict against App Review's answer, so the guard can be measured.

Guideline 4.3 judges the developer account, not one game, so the ledger lives
outside every repo: $APPSTORE_SPAM_GUARD_LEDGER, or
~/.config/appstore-spam-guard/ledger.json. `check` prints rows in scan.py's
shape ({id, group, verdict, summary, evidence, fix}). It knows only what was
recorded: an empty ledger is a PASS about the ledger, not about the account.
Exit 0 on success, 2 on a usage error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

EVENTS = ("submitted", "approved", "rejected", "withdrawn")

# Submissions to one team inside the window before the pace itself is a signal.
CADENCE_LIMIT = 3


def default_path() -> Path:
    env = os.environ.get("APPSTORE_SPAM_GUARD_LEDGER")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "appstore-spam-guard" / "ledger.json"


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 1, "teams": {}}
    data.setdefault("teams", {})
    return data


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def scans_dir() -> Path:
    """Where scan.py leaves its latest submit-mode summary per team and bundle."""
    env = os.environ.get("APPSTORE_SPAM_GUARD_CACHE", "").strip()
    base = Path(env).expanduser() if env else Path.home() / ".cache" / "appstore-spam-guard"
    return base / "scans"


def scan_summary(result: dict) -> dict:
    """What a submission keeps of a scan: enough to learn which rows predict App Review."""
    rows = result.get("checks", [])
    return {"version": result.get("version", ""), "mode": result.get("mode", ""),
            "overall": result.get("overall", ""), "at": result.get("at", ""),
            "fail": sorted({r["id"] for r in rows if r["verdict"] == "FAIL"}),
            "warn": sorted({r["id"] for r in rows if r["verdict"] == "WARN"})}


def save_last_scan(team: str, bundle: str, result: dict) -> None:
    p = scans_dir() / team / f"{bundle}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(scan_summary(result), ensure_ascii=False), encoding="utf-8")


def last_scan(team: str, bundle: str, max_days: int = 14) -> dict | None:
    p = scans_dir() / team / f"{bundle}.json"
    try:
        s = json.loads(p.read_text(encoding="utf-8"))
        age = dt.date.today() - dt.date.fromisoformat(s["at"][:10])
    except (OSError, ValueError, KeyError):
        return None
    return s if age.days <= max_days else None


def record(data: dict, team: str, app: str, bundle: str, event: str,
           guideline: str = "", extended_review: bool = False,
           date: str = "", note: str = "", scan: dict | None = None,
           verdict: str = "") -> dict:
    entry = {
        "date": date or dt.date.today().isoformat(),
        "app": app,
        "bundle": bundle,
        "event": event,
    }
    if guideline:
        entry["guideline"] = guideline
    if extended_review:
        entry["extended_review"] = True
    if note:
        entry["note"] = note
    if scan:
        entry["scan"] = scan
    if verdict:
        entry["verdict"] = verdict  # the gate's verdict with J1–J6, when given
    team_data = data["teams"].setdefault(team, {"events": []})
    team_data["events"].append(entry)
    team_data["events"].sort(key=lambda e: e["date"])
    return entry


def open_43(events: list[dict]) -> dict[str, dict]:
    """Bundle → its 4.3 rejection that no later approval or withdrawal closed."""
    pending: dict[str, dict] = {}
    for e in sorted(events, key=lambda e: e["date"]):
        if e["event"] == "rejected" and e.get("guideline", "").startswith("4.3"):
            pending[e["bundle"]] = e
        elif e["event"] in ("approved", "withdrawn"):
            pending.pop(e["bundle"], None)
    return pending


def same_game(a: str, b: str) -> bool:
    """One game's name inside another's ('Merge Seasons', 'Merge Seasons: Halloween'). A
    short one-word name must match whole: 'Pop' is not 'Pop Star'."""
    wa, wb = (re.findall(r"[^\W_]+", s.casefold()) for s in (a, b))
    if not wa or not wb:
        return False
    short, long_ = sorted((wa, wb), key=len)
    if short == long_:
        return True
    if len(short) == 1 and len(short[0]) < 6:
        return False
    return f" {' '.join(short)} " in f" {' '.join(long_)} "


def _row(id_: str, verdict: str, summary: str, evidence: str = "", fix: str = "") -> dict:
    return {"id": id_, "group": "account", "verdict": verdict,
            "summary": summary, "evidence": evidence, "fix": fix}


def check_rows(data: dict, team: str, bundle: str | None = None, days: int = 14,
               today: dt.date | None = None, app: str | None = None) -> list[dict]:
    today = today or dt.date.today()
    events = data.get("teams", {}).get(team, {}).get("events", [])
    if not events:
        return [_row("account.ledger", "PASS",
                     f"no submissions recorded for team {team}",
                     "the ledger knows only what `ledger.py record` was told",
                     "record every submission and every App Review answer")]

    rows: list[dict] = []
    for b, e in open_43(events).items():
        flag = " with Extended Review" if e.get("extended_review") else ""
        evidence = f"{e['date']}: {e['app']} ({b}) rejected under {e.get('guideline')}{flag}"
        if bundle and b == bundle:
            rows.append(_row(
                "account.resubmission", "WARN",
                f"resubmitting {e['app']} after its {e.get('guideline')} rejection",
                evidence,
                "resubmit once, only with the substantive changes listed in "
                "references/guideline-4.3.md (Resubmitting after 4.3), and reply in the "
                "Resolution Center"))
        else:
            rows.append(_row(
                "account.open-4.3", "FAIL",
                f"team {team} has an unresolved 4.3 rejection ({e['app']})",
                evidence,
                f"hold every new submission to team {team} until {e['app']} clears review "
                "or is withdrawn; record the outcome with `ledger.py record`"))

    # 4.3(a): the same game already on this team under another bundle ID.
    if app and bundle:
        latest = {e["bundle"]: e for e in sorted(events, key=lambda e: e["date"])
                  if e["bundle"] != bundle and same_game(app, e["app"])}
        for b, e in latest.items():
            rows.append(_row(
                "account.same-app", "WARN",
                f"team {team} already has {e['app']} ({b}): the same game under a second "
                "bundle ID",
                f"{e['date']}: {e['app']} ({b}) {e['event']}",
                "4.3(a): ship it as an update of the app the team already has, or make it a "
                "different game (art, concept, name); a rejected or withdrawn app resubmitted "
                "under a new bundle ID reads as dodging review"))

    window_start = today - dt.timedelta(days=days)
    recent = [e for e in events
              if e["event"] == "submitted" and dt.date.fromisoformat(e["date"]) >= window_start]
    if len(recent) >= CADENCE_LIMIT:
        names = ", ".join(sorted({e["app"] for e in recent}))
        rows.append(_row(
            "account.cadence", "WARN",
            f"{len(recent)} submissions to team {team} in the last {days} days",
            names,
            "space submissions out; many similar apps from one account in a short "
            "window is the 'other apps you submitted' variant of 4.3(a)"))

    if not rows:
        rows.append(_row("account.ledger", "PASS",
                         f"no open 4.3 and a normal pace on team {team}",
                         f"{len(events)} recorded events"))
    return rows


def stats(data: dict, team: str | None = None) -> dict:
    """Each submission against App Review's answer: does the guard's verdict predict 4.3?"""
    table: dict[str, dict[str, int]] = {}
    rows: dict[str, dict[str, int]] = {}
    missed: list[str] = []
    for t, td in data.get("teams", {}).items():
        if team and t != team:
            continue
        open_: dict[str, dict] = {}
        outcomes: list[tuple[dict, str]] = []
        for e in sorted(td.get("events", []), key=lambda e: e["date"]):
            if e["event"] == "submitted":
                open_[e["bundle"]] = e
            elif e["bundle"] in open_:
                sub = open_.pop(e["bundle"])
                if e["event"] == "approved":
                    outcome = "approved"
                elif e["event"] == "rejected":
                    outcome = ("rejected 4.3" if e.get("guideline", "").startswith("4.3")
                               else "rejected other")
                else:
                    outcome = "withdrawn"
                outcomes.append((sub, outcome))
        outcomes += [(s, "pending") for s in open_.values()]
        for sub, outcome in outcomes:
            scan = sub.get("scan") or {}
            verdict = sub.get("verdict") or scan.get("overall") or "unscanned"
            table.setdefault(verdict, {}).setdefault(outcome, 0)
            table[verdict][outcome] += 1
            for rid in scan.get("fail", []) + scan.get("warn", []):
                rows.setdefault(rid, {}).setdefault(outcome, 0)
                rows[rid][outcome] += 1
            if outcome == "rejected 4.3" and verdict == "PASS":
                missed.append(f"{t} {sub['date']} {sub['app']} ({sub['bundle']})")
    decided = sum(n for v in table.values() for o, n in v.items() if o != "pending")
    return {"submissions_decided": decided, "by_verdict": table,
            "rows_flagged": dict(sorted(rows.items())), "passed_but_rejected_4.3": missed,
            "note": "rows_flagged counts each WARN/FAIL row id in the scan kept with a "
                    "submission, by outcome; a row seen before 4.3 rejections and never "
                    "before approvals is one to make FAIL"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ledger", type=Path, default=None, help="ledger file")
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="append one event")
    rec.add_argument("--team", required=True)
    rec.add_argument("--app", required=True)
    rec.add_argument("--bundle", required=True)
    rec.add_argument("--event", required=True, choices=EVENTS)
    rec.add_argument("--guideline", default="")
    rec.add_argument("--extended-review", action="store_true")
    rec.add_argument("--date", default="")
    rec.add_argument("--note", default="")
    rec.add_argument("--scan", type=Path, default=None,
                     help="scan.py's JSON to keep with a submission (default: the latest "
                          "submit-mode scan of this bundle, if under 14 days old)")
    rec.add_argument("--verdict", choices=("PASS", "WARN", "FAIL"), default="",
                     help="the gate's verdict with J1–J6, when it differs from the scan's")

    st = sub.add_parser("stats", help="the guard's verdicts against App Review's answers")
    st.add_argument("--team", default=None)

    chk = sub.add_parser("check", help="rows for scan.py's account group")
    chk.add_argument("--team", required=True)
    chk.add_argument("--bundle", default=None)
    chk.add_argument("--app", default=None, help="the app's name, to find it under other bundles")
    chk.add_argument("--days", type=int, default=14)

    show = sub.add_parser("show", help="print the ledger")
    show.add_argument("--team", default=None)

    args = parser.parse_args(argv)
    path = args.ledger or default_path()
    data = load(path)

    if args.cmd == "record":
        if args.date:
            try:
                dt.date.fromisoformat(args.date)
            except ValueError:
                print(f"--date must be YYYY-MM-DD, got {args.date!r}", file=sys.stderr)
                return 2
        scan = None
        if args.scan:
            try:
                scan = scan_summary(json.loads(args.scan.read_text(encoding="utf-8")))
            except (OSError, ValueError) as e:
                print(f"--scan {args.scan}: {e}", file=sys.stderr)
                return 2
        elif args.event == "submitted":
            scan = last_scan(args.team, args.bundle)
        entry = record(data, args.team, args.app, args.bundle, args.event,
                       args.guideline, args.extended_review, args.date, args.note,
                       scan, args.verdict)
        save(path, data)
        out = {"recorded": entry, "ledger": str(path)}
        if args.event == "submitted" and not scan:
            out["warning"] = ("no scan kept with this submission: run scan.py --mode submit "
                              "first or pass --scan, or stats cannot learn from it")
        print(json.dumps(out, ensure_ascii=False))
    elif args.cmd == "stats":
        print(json.dumps(stats(data, args.team), indent=2, ensure_ascii=False))
    elif args.cmd == "check":
        print(json.dumps(check_rows(data, args.team, args.bundle, args.days, app=args.app),
                         indent=2, ensure_ascii=False))
    else:
        teams = data["teams"]
        if args.team:
            teams = {args.team: teams.get(args.team, {"events": []})}
        print(json.dumps({"ledger": str(path), "teams": teams}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
