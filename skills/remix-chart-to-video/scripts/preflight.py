#!/usr/bin/env python3
"""Check the machine and the four repos before a run.

  preflight.py [--config FILE] [--count N] [--deep]

Checks tools and ffmpeg filters, the repos and their interpreters, that every flag, route and
preset key the skill uses still exists, StemForge's environment and model files (--deep also
hashes them), disk, GPU memory, ports, image-provider keys (names only), herdr, and how many
YouTube limits are verified. Prints JSON: {"worst", "checks": [{name, status, detail}]}.
Exit 0 when nothing is FAIL, 1 otherwise, 2 usage.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rcvlib import config as cfgmod  # noqa: E402
from rcvlib import preflight  # noqa: E402
from rcvlib.common import RcvError, emit, worst  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config')
    ap.add_argument('--count', type=int)
    ap.add_argument('--deep', action='store_true')
    args = ap.parse_args(argv)
    try:
        cfg = cfgmod.load(args.config)
        checks = preflight.run_preflight(cfg, None, args.count, args.deep)
    except RcvError as exc:
        emit({'exit': exc.code, 'error': str(exc)})
        return exc.code
    verdict = worst(checks)
    emit({'worst': verdict, 'checks': checks})
    return 1 if verdict == 'FAIL' else 0


if __name__ == '__main__':
    sys.exit(main())
