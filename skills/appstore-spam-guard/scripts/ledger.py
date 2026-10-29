#!/usr/bin/env python3
"""Per-team App Store submission ledger for appstore-spam-guard.

    python3 ledger.py record --team T --app NAME --bundle ID \\
        --event submitted|approved|rejected|withdrawn \\
        [--guideline "4.3(a)"] [--extended-review] [--date YYYY-MM-DD] [--note TEXT]
    python3 ledger.py check --team T [--bundle ID] [--days 14]
    python3 ledger.py show [--team T]

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


def record(data: dict, team: str, app: str, bundle: str, event: str,
           guideline: str = "", extended_review: bool = False,
           date: str = "", note: str = "") -> dict:
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


def _row(id_: str, verdict: str, summary: str, evidence: str = "", fix: str = "") -> dict:
    return {"id": id_, "group": "account", "verdict": verdict,
            "summary": summary, "evidence": evidence, "fix": fix}


def check_rows(data: dict, team: str, bundle: str | None = None, days: int = 14,
               today: dt.date | None = None) -> list[dict]:
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

    chk = sub.add_parser("check", help="rows for scan.py's account group")
    chk.add_argument("--team", required=True)
    chk.add_argument("--bundle", default=None)
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
        entry = record(data, args.team, args.app, args.bundle, args.event,
                       args.guideline, args.extended_review, args.date, args.note)
        save(path, data)
        print(json.dumps({"recorded": entry, "ledger": str(path)}, ensure_ascii=False))
    elif args.cmd == "check":
        print(json.dumps(check_rows(data, args.team, args.bundle, args.days),
                         indent=2, ensure_ascii=False))
    else:
        teams = data["teams"]
        if args.team:
            teams = {args.team: teams.get(args.team, {"events": []})}
        print(json.dumps({"ledger": str(path), "teams": teams}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
