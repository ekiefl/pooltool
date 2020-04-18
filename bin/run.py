#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.engine as engine
import psim.physics as physics
import psim.ani.animate as animate

import numpy as np
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--choice', required=True, choices=['col', 'ani'])
args = ap.parse_args()

if __name__ == '__main__':
    sim = engine.ShotSimulation()
    sim.setup_test('straight_shot')

    # -----------------------------------------------------------------

    if args.choice == 'col':

        event = engine.Event(None, None, 0)

        while event.tau < np.inf:
            sim.print_ball_states()

            event = sim.get_next_event()
            print(event)

            sim.evolve(event.tau)
            #sim.resolve(event)

            print()

        ani = animate.AnimateShot(sim, size=2000)
        ani.start()


    # -----------------------------------------------------------------

    if args.choice == 'ani':
        for t in np.arange(0, 1, 0.0033):
            sim.evolve(t)

        print(sim.balls['cue'].plot_history(full=True))

        ani = animate.AnimateShot(sim, size=500)
        ani.start()





