#! /usr/bin/env python

import pooltool.utils as utils
import pooltool.events as e

from pooltool.layouts import NineBallRack
from pooltool.evolution import get_shot_evolver
from pooltool.objects.cue import Cue
from pooltool.ani.animate import ShotViewer
from pooltool.objects.ball import Ball
from pooltool.objects.table import Table

import numpy as np

N = 300
spacing_factor = 0.01

interface = ShotViewer()
best_break = 0

get_cue_pos = lambda cue, table: [cue.R + np.random.rand()*(table.w - 2*cue.R), table.l/4, cue.R]

for n in range(N):
    # setup table, cue, and cue ball
    cue = Cue()
    table = Table()
    cue_ball = Ball('cue')
    cue_ball.rvw[0] = get_cue_pos(cue_ball, table)

    # Create a rack with specified spacing factor
    diamond = NineBallRack(spacing_factor=spacing_factor, ordered=True)
    diamond.center_by_table(table)
    balls = diamond.get_balls_dict()
    balls['cue'] = cue_ball

    # Aim at the head ball then strike the cue ball
    cue.set_state(V0=8, theta=0, a=0, b=0, cueing_ball=balls['cue'])
    cue.aim_at(balls['1'].rvw[0])
    cue.strike()

    # Evolve the shot
    evolver = get_shot_evolver('event')
    shot = evolver(cue=cue, table=table, balls=balls)
    try:
        shot.simulate(name=f"factor: {spacing_factor}; n: {n}", continuize=False)
    except:
        shot.progress.end()
        continue

    # Count how many balls were potted, ignoring cue ball
    numbered_balls = [ball for ball in balls.values() if ball.id != 'cue']
    pocket_events = shot.\
        filter_type(e.type_ball_pocket).\
        filter_ball(numbered_balls)
    balls_potted = pocket_events.num_events

    shot.run.info("Balls potted", balls_potted)

    if balls_potted > best_break:
        shot.continuize(dt=0.001)
        interface.set_shot(shot)
        interface.start()
        best_break = balls_potted


