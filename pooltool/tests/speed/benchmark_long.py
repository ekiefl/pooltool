#! /usr/bin/env python

import pprofile
import pooltool as pt

# Run once to compile all numba functions. By doing this,
# compilation times will be excluded in the timing.
system = pt.System(path='benchmark_long.pkl')
system.simulate(continuize=False, quiet=True)

def main(args):
    system = pt.System(path='benchmark_long.pkl')

    if args.type == 'time':
        with pt.terminal.TimeCode():
            system.simulate(continuize=False, quiet=False)
    if args.type == 'profile':
        with pt.utils.PProfile(args.path):
            system.simulate(continuize=False)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--type', choices=['time', 'profile'], required=True)
    ap.add_argument('--path', default='cachegrind.out.benchmark')
    args = ap.parse_args()
    main(args)
