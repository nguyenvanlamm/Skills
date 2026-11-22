"""Dialogue -> video, one level folder at a time.

Usage:
  uv run python run.py <episodes/NAME/LEVEL> [--until tts|build|publish|thumbnail|render|check] [--format 16x9|9x16|short_9x16]

The folder must contain dialogue.json. Steps: validate -> tts -> build -> publish (upload fields) -> thumbnail -> render -> check.
Progress is written to state.json; finished work (unchanged TTS lines, up-to-date videos) is reused.
state.json also holds `progress` (the step being worked on, the steps done in this run, the last
FAIL line), which steps_pane.py shows to the human.
"""
from __future__ import annotations

import argparse
import builtins
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

from build_episode import build
from check_video import check, shot_moments
from publish import build_publish, precheck
from common import VIDEO, design_digest, load_config, read_json, render_digest, write_json
from tts import synth_lines
from validate_dialogue import validate

# output name -> (composition, size, timeline it is rendered from)
FORMATS = {"16x9": ("Toon16x9", (1920, 1080), "episode"),
           "9x16": ("Toon9x16", (1080, 1920), "episode"),
           "short_9x16": ("Toon9x16", (1080, 1920), "short")}
STEPS = ["validate", "tts", "build", "publish", "thumbnail", "render", "check"]


# The run in progress, kept here so that main() can close it whatever way the pipeline ends.
LIVE: dict = {}


def print(*args, **kwargs) -> None:
    """print, and remember the last FAIL line so the steps pane can show why a step stopped."""
    text = " ".join(str(a) for a in args).strip()
    if text.startswith("FAIL") and LIVE:
        LIVE["state"]["progress"]["error"] = text[4:].strip()
    builtins.print(*args, **kwargs, flush=True)


def finish(code: int) -> None:
    """Close the run's progress: every step done, or stopped at the current one."""
    if not LIVE:
        return
    prog = LIVE["state"]["progress"]
    if code == 0:
        if prog["current"] and prog["current"] not in prog["done"]:
            prog["done"].append(prog["current"])
        prog.update(status="done", current=None, detail="")
    else:
        prog["status"] = "failed"
    prog["updated_at"] = time.time()
    write_json(LIVE["path"], LIVE["state"])


def remotion(*args: str) -> int:
    """Run one Remotion command. Only one runs at a time on this machine: two at once (the two
    levels of an episode started together) fight over the bundler's cache and one of them dies,
    and a render uses every core anyway."""
    lock = Path(tempfile.gettempdir()) / "vocab-to-video-remotion.lock"
    with open(lock, "w") as held:
        try:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("  waiting for another render on this machine to finish")
            fcntl.flock(held, fcntl.LOCK_EX)
        return subprocess.run(["npx", "remotion", *args, "--log=error"], cwd=VIDEO).returncode


def image_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def run_pipeline() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("level_dir", type=Path)
    ap.add_argument("--until", choices=STEPS[1:], default="check")
    ap.add_argument("--format", choices=list(FORMATS), action="append")
    args = ap.parse_args()

    d = args.level_dir.resolve()
    cfg = load_config()
    dialogue = read_json(d / "dialogue.json")
    state_path = d / "state.json"
    try:
        state = read_json(state_path) if state_path.is_file() else {"steps": {}}
    except ValueError:  # a state file cut short by a crash: start again, the work files are still there
        state = {"steps": {}}
    state.setdefault("steps", {})

    state["progress"] = {"status": "running", "current": None, "detail": "", "done": [], "error": None,
                         "until": args.until, "pid": os.getpid(), "started_at": time.time(),
                         "step_started_at": time.time(), "updated_at": time.time()}
    LIVE.update(path=state_path, state=state)

    def begin(step: str, detail: str = "") -> None:
        """Tell the steps pane which step starts now; the step before it counts as done."""
        prog = state["progress"]
        if prog["current"] != step:
            if prog["current"] and prog["current"] not in prog["done"]:
                prog["done"].append(prog["current"])
            prog["step_started_at"] = time.time()
        prog.update(current=step, detail=detail, updated_at=time.time())
        write_json(state_path, state)

    def mark(step: str, **info) -> None:
        state["steps"][step] = {"done_at": time.strftime("%Y-%m-%dT%H:%M:%S"), **info}
        write_json(state_path, state)

    begin("validate")
    print(f"[validate] {d}")
    errors, warnings, stats = validate(dialogue, cfg)
    for w in warnings:
        print(f"  WARN {w}")
    if errors:
        for e in errors:
            print(f"  FAIL {e}")
        return 1
    print(f"  {stats['words']} words, {stats['turns']} turns; uses of each new word: {stats['vocab_uses']}")
    if args.until not in ("tts", "build"):
        # The upload texts are checked now, before a minute of speech is made for nothing.
        problems = precheck(d, dialogue, cfg)
        if problems:
            for p in problems:
                print(f"  FAIL {p}")
            print("  Fix metadata.json and run again.")
            return 1
    mark("validate", **stats)

    begin("tts")
    print("[tts]")
    metas = synth_lines(dialogue, cfg, d / "lines")
    mark("tts", lines=len(metas))
    if args.until == "tts":
        return 0

    begin("build")
    print("[build]")
    full = [m for m in metas if m["index"] > 0]
    hook = [m for m in metas if m["index"] == 0]
    episode = build(d, dialogue, hook + full, cfg, name="episode")
    cut = dialogue["short"]
    short = build(d, dialogue, hook + full[cut["from"] - 1:cut["to"]], cfg, name="short")
    seconds, short_s = episode["durationMs"] / 1000, short["durationMs"] / 1000
    mark("build", duration_s=seconds, short_duration_s=short_s)
    lo, hi = cfg["duration_s"]
    if not lo <= seconds <= hi:
        print(f"  FAIL audio is {seconds:.1f}s; target is {lo}-{hi}s. "
              f"{'Add' if seconds < lo else 'Remove'} turns in dialogue.json and run again.")
        return 1
    lo, hi = cfg["short_duration_s"]
    if not lo <= short_s <= hi:
        print(f"  FAIL the short cut is {short_s:.1f}s; target is {lo}-{hi}s. "
              f"{'Widen' if short_s < lo else 'Narrow'} the 'short' line range in dialogue.json and run again.")
        return 1
    if args.until == "build":
        return 0

    begin("publish")
    print("[publish]")
    problems, warnings = build_publish(d, dialogue, episode, cfg)
    for w in warnings:
        print(f"  WARN {w}")
    if problems:
        for p in problems:
            print(f"  FAIL {p}")
        print("  Fix metadata.json and run again.")
        return 1
    mark("publish", file=str(d / "out" / "publish.md"))
    print(f"  upload fields: {d / 'out' / 'publish.md'}")
    if args.until == "publish":
        return 0

    begin("thumbnail")
    print("[thumbnail]")
    meta = read_json(d / "metadata.json")
    base = f"{d.parent.name}_{dialogue['level']}"
    (d / "out").mkdir(exist_ok=True)
    opening = episode["shots"][0] if episode["shots"] else {}
    shared = {"level": dialogue["level"], "vocab": episode["vocab"], "speakers": episode["speakers"],
              "cast": episode["cast"], "fonts": True,
              "scene": {k: opening[k] for k in ("set", "time", "wall", "shop") if k in opening}}
    design = design_digest()
    stills = state["steps"].get("thumbnail", {}).get("files", {})
    for comp, name, text, size in (
            ("Thumbnail16x9", "thumbnail", meta["thumbnail_text"], (1280, 720)),
            ("Cover9x16", "cover", meta["thumbnail_text"], (1080, 1920))):
        props = {"text": text, **shared}
        out = d / "out" / f"{base}_{name}.jpg"
        # Redraw when the text changes or when the thumbnail design itself changes.
        digest = hashlib.sha256(json.dumps(props, sort_keys=True).encode() + design).hexdigest()[:16]
        if stills.get(name) != digest or not out.is_file():
            write_json(d / f"{name}_props.json", props)
            code = remotion("still", comp, str(out), f"--props={d / f'{name}_props.json'}",
                            f"--public-dir={d / 'public'}", "--image-format=jpeg", "--jpeg-quality=92")
            if code != 0:
                print(f"  FAIL remotion still exited {code}")
                return 1
            stills[name] = digest
            mark("thumbnail", files=stills)
        got = image_size(out)
        kb = out.stat().st_size // 1024
        if got != size or kb > 2000:
            print(f"  FAIL {out.name}: {got[0]}x{got[1]}, {kb} KB (need {size[0]}x{size[1]}, under 2 MB)")
            return 1
        print(f"  {out} ({got[0]}x{got[1]}, {kb} KB)")
    if args.until == "thumbnail":
        return 0

    out_dir = d / "out"
    out_dir.mkdir(exist_ok=True)
    name = f"{d.parent.name}_{dialogue['level']}"
    rendered = state["steps"].get("render", {}).get("files", {})
    failed = False
    formats = args.format or list(FORMATS)
    for n, fmt in enumerate(formats, 1):
        begin("render", f"{fmt} {n}/{len(formats)}")
        comp, size, source = FORMATS[fmt]
        props = d / f"{source}.json"
        timeline = read_json(props)
        expect_s = timeline["durationMs"] / 1000
        # A video is up to date only if its timeline, its audio track and the video design are unchanged.
        digest = render_digest(d, source, design)
        checks = state["steps"].setdefault("check", {})
        out = out_dir / f"{name}_{fmt}.mp4"
        if rendered.get(fmt) == digest and out.is_file():
            print(f"[render] {fmt}: up to date")
        else:
            print(f"[render] {fmt} -> {out}")
            t0 = time.time()
            # From here on the old video and its check say nothing about the file in out/.
            rendered.pop(fmt, None)
            checks.pop(fmt, None)
            write_json(state_path, state)
            code = remotion("render", comp, str(out), f"--props={props}", f"--public-dir={d / 'public'}")
            if code != 0:
                print(f"  FAIL remotion render exited {code}")
                return 1
            rendered[fmt] = digest
            mark("render", files=rendered)
            print(f"  rendered in {time.time() - t0:.0f}s")
        if args.until == "render":
            continue
        begin("render", f"{fmt} {n}/{len(formats)} kiểm tra")
        problems, vstats = check(out, size, expect_s, cfg["loudness_lufs"], d / "check", cfg["fps"],
                                 shot_moments(timeline))
        print(f"[check] {fmt}: {vstats['duration_s']}s, {vstats.get('fps')} fps, {vstats.get('lufs')} LUFS")
        for p in problems:
            print(f"  FAIL {p}")
        for f in vstats["sheets"]:
            print(f"  sheet {f}")
        if vstats["frames"]:
            print(f"  one frame per shot ({len(vstats['frames'])}): {Path(vstats['frames'][0]).parent}")
        failed = failed or bool(problems)
        checks[fmt] = {"problems": problems, "digest": digest, **vstats}
        write_json(state_path, state)
    print("RESULT: FAIL" if failed else "RESULT: PASS")
    return 1 if failed else 0


def main() -> int:
    code = 1
    try:
        code = run_pipeline()
        return code
    except Exception as exc:  # a failed download, a missing tool, a broken file: say it as a FAIL line
        traceback.print_exc()
        print(f"FAIL {type(exc).__name__}: {str(exc).strip() or 'no message'}")
        return 1
    finally:
        finish(code)


if __name__ == "__main__":
    sys.exit(main())
