#!/usr/bin/env python3
"""Short clips of the two video looks, with one frame each, for the first-run choice.

  render_video.py preview --run RUN [--looks cover,visualizer] [--seconds 8] [--config FILE]

Works as soon as the `art` stage is done: it uses the provisional cover and any audio at hand
(the mix, else a remix, else an original) and says so in "provisional". Look at the frames it
names, show them to the human, then save the choice with `pipeline.py set video.look ...`.
The final render is the pipeline's `video` stage. Prints JSON. Exit 0 ok, 1 failed, 2 usage.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rcvlib import config as cfgmod  # noqa: E402
from rcvlib import video  # noqa: E402
from rcvlib.common import RcvError, emit  # noqa: E402
from rcvlib.state import State  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('preview')
    p.add_argument('--run', required=True)
    p.add_argument('--looks', default='cover,visualizer')
    p.add_argument('--seconds', type=float, default=8.0)
    p.add_argument('--config')
    args = ap.parse_args(argv)
    try:
        run_dir = Path(args.run).resolve()
        state = State.load(run_dir)
        cfg = cfgmod.load(args.config or state.data['run'].get('config_path'))
        looks = [x.strip() for x in args.looks.split(',') if x.strip()]
        emit(video.preview(run_dir, cfg, looks, args.seconds))
        return 0
    except RcvError as exc:
        emit({'exit': exc.code, 'error': str(exc)})
        return exc.code


if __name__ == '__main__':
    sys.exit(main())
