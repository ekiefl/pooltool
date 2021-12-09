#! /usr/bin/env python
"""This illustrates how shots can be visualized multiple times in a single script"""

import pooltool as pt
import pooltool.events as e

import numpy as np

N = 300
spacing_factor = 1e-3

interface = pt.ShotViewer()
best_break = 0

get_cue_pos = lambda cue, table: [cue.R + np.random.rand()*(table.w - 2*cue.R), table.l/4, cue.R]

for n in range(N):
    # setup table, cue, and cue ball
    table = pt.PocketTable()
    balls = pt.get_nine_ball_rack(table, spacing_factor=spacing_factor, ordered=True)
    balls['cue'].rvw[0] = get_cue_pos(balls['cue'], table)
    cue = pt.Cue(cueing_ball=balls['cue'])

    # Aim at the head ball then strike the cue ball
    cue.aim_at_ball(balls['1'])
    cue.strike(V0=8)

    # Evolve the shot
    shot = pt.System(cue=cue, table=table, balls=balls)
    try:
        shot.simulate(name=f"factor: {spacing_factor}; n: {n}", continuize=False)
    except KeyboardInterrupt:
        shot.progress.end()
        break
    except:
        shot.progress.end()
        shot.run.info("Shot calculation failed", ":(")
        continue

    # Count how many balls were potted, ignoring cue ball
    numbered_balls = [ball for ball in balls.values() if ball.id != 'cue']
    pocket_events = shot.events.\
        filter_type(e.type_ball_pocket).\
        filter_ball(numbered_balls)
    balls_potted = len(pocket_events)

    shot.run.info("Balls potted", balls_potted)

    shot.continuize(dt=0.01)
    interface.show(shot)

    if balls_potted > best_break:
        best_break = balls_potted


