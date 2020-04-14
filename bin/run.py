#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.engine as engine
import psim.physics as physics

import numpy as np
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--choice', choices=['evolve', 'collision'])
args = ap.parse_args()

if __name__ == '__main__':
    sim = engine.ShotSimulation()
    sim.setup_test()

    # -----------------------------------------------------------------

    if args.choice == 'evolve':
        for t in np.arange(0, 3.3477846015, 0.05):
            for ball_id, ball in sim.balls.items():
                ball = sim.balls[ball_id]
                rvw, s = physics.evolve_ball_motion(
                    state=ball.s,
                    rvw=ball.rvw,
                    R=ball.R,
                    m=ball.m,
                    u_s=sim.table.u_s,
                    u_sp=sim.table.u_sp,
                    u_r=sim.table.u_r,
                    g=psim.g,
                    t=t,
                )
                ball.store(t, rvw, s)

    print(sim.balls['1'].history)
    sim.plot_history(ball_states=True)

    # -----------------------------------------------------------------

    if args.choice == 'collision':
        cueball = sim.balls['cue']
        oneball = sim.balls['1']

        times = physics.get_ball_ball_collision_time(
            rvw1=cueball.rvw,
            rvw2=oneball.rvw,
            s1=cueball.s,
            s2=oneball.s,
            mu1=(sim.table.u_s if cueball.s == psim.sliding else sim.table.u_r),
            mu2=(sim.table.u_s if oneball.s == psim.sliding else sim.table.u_r),
            m1=cueball.m,
            m2=oneball.m,
            g=psim.g,
            R=cueball.R
        )

