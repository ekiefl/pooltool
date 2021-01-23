#! /usr/bin/env python

import psim
import psim.engine as engine

import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--setup', required=False)
ap.add_argument('-s', '--skip-continuize', action='store_true')
ap.add_argument('-d', '--dimensions', type=int, choices=[2,3], default=2)
ap.add_argument('-p', '--plot', action='store_true')
ap.add_argument('-dt', '--dt', type=float, default=0.01)
ap.add_argument('--speed', type=float, default=1)
args = ap.parse_args()

if __name__ == '__main__':
    #FIXME
    from psim.ani.animate3d2 import InteractiveVisualization
    ani = InteractiveVisualization()
    ani.start()
    #FIXME

    sim = engine.ShotSimulation()
    sim.setup_test(args.setup)

    sim.simulate(name=args.setup, time=None)

    if not args.skip_continuize:
        sim.continuize(args.dt)

    if args.plot:
        sim.plot_history('cue', full=False)

    if args.dimensions == 2:
        from psim.ani.animate2d import AnimateShot

        kwargs = {
            'size': 800
        }

    elif args.dimensions == 3:
        from psim.ani.animate3d import AnimateShot

        kwargs = {
            'playback_speed': args.speed
        }

    ani = AnimateShot(sim, **kwargs)
    ani.start()
