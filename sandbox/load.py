#! /usr/bin/env python
"""Load a shot and visualize it

If you don't have a shot to load, you could run

python break.py --no-viz --save a_shot.msgpack

to solve that problem.
"""

import pooltool as pt


def main(args):
    pt.show(pt.System.load(args.path))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--path", type=str, required=True, help="Filepath of the shot")

    args = ap.parse_args()
    main(args)
