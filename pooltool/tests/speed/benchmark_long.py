#! /usr/bin/env python
"""For some reason, `numba_cache` in pooltool/constants.py must be set to False prior to running this script"""

from pathlib import Path

import pooltool as pt

path = Path(pt.__file__).parent / "tests" / "speed" / "benchmark_long.pkl"


def main(args):
    # Run once to compile all numba functions. By doing this,
    # compilation times will be excluded in the timing.
    system = pt.System(path=path)
    system.simulate(continuize=False, quiet=True)

    system = pt.System(path=path)

    if args.type == "time":
        with pt.terminal.TimeCode():
            system.simulate(continuize=False, quiet=False)
    if args.type == "profile":
        with pt.utils.PProfile(args.path):
            system.simulate(continuize=False)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="For some reason, `numba_cache` in pooltool/constants.py must be set to False prior to running this script"
    )
    ap.add_argument("--type", choices=["time", "profile"], required=True)
    ap.add_argument("--path", default="cachegrind.out.benchmark")
    args = ap.parse_args()
    main(args)
