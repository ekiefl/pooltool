#! /usr/bin/env python

import pprofile
import pooltool as pt

class PProfile(pprofile.Profile):
    """Small wrapper for pprofile that accepts a filepath and outputs cachegrind file"""
    def __init__(self, path):
        self.path = path
        pprofile.Profile.__init__(self)

    def __exit__(self, *args):
        pprofile.Profile.__exit__(self, *args)
        self.dump_stats(self.path)

# Run once to compile all numba functions. By doing this,
# compilation times will be excluded in the timing.
system = pt.System(path='benchmark_long.pkl')
system.simulate(continuize=False, quiet=True)

def main(args):
    system = pt.System(path='benchmark_long.pkl')

    if args.type == 'time':
        with pt.terminal.TimeCode():
            system.simulate(continuize=False, quiet=True)
    if args.type == 'profile':
        with PProfile(args.path):
            system.simulate(continuize=False, quiet=True)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--type', choices=('time', 'profile'), required=True)
    ap.add_argument('--path', default='cachegrind.out.benchmark', help="Define cachegrind filepath if --type profile")
    args = ap.parse_args()
    main(args)
