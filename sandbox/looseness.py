#! /usr/bin/env python

import matplotlib.pyplot as plt
import numpy as np

import pooltool.utils as utils
from pooltool.ani.animate import ShotViewer
from pooltool.events import BallPocketCollision
from pooltool.evolution import get_shot_evolver
from pooltool.layouts import NineBallRack
from pooltool.objects.ball import Ball
from pooltool.objects.cue import Cue
from pooltool.objects.table import Table

N = 300

# These are the spacing factors I will use. e.g. [0.001, 0.00215, 0.0046, 0.01, 0.0215, 0.0464, 0.1, 0.215, 0.464, 1.]
spacing_factors = np.logspace(-4, 0, 10, base=10)

score_means = np.zeros(len(spacing_factors)).astype(int)
score_stds = np.zeros(len(spacing_factors)).astype(int)

get_cue_pos = lambda cue, table: [
    cue.R + np.random.rand() * (table.w - 2 * cue.R),
    table.l / 4,
    cue.R,
]

interface = ShotViewer()

best_break = 0
for i, spacing_factor in enumerate(spacing_factors):
    score = np.zeros(N)

    for n in range(N):
        # setup table, cue, and cue ball
        cue = Cue()
        table = Table.default()
        cue_ball = Ball("cue")
        cue_ball.state.rvw[0] = get_cue_pos(cue_ball, table)

        # Create a rack with specified spacing factor
        diamond = NineBallRack(spacing_factor=spacing_factor, ordered=True)
        diamond.center_by_table(table)
        balls = {ball.id: ball for ball in diamond.balls}
        balls["cue"] = cue_ball
        # balls = {key: val for key, val in balls.items() if key in {'1', '2', '3', 'cue'}}

        # Aim at the head ball then strike the cue ball
        cue.set_state(V0=8, theta=0, a=0, b=0, cueing_ball=balls["cue"])
        cue.aim_at(balls["1"].rvw[0])
        cue.strike()

        # Evolve the shot
        evolver = get_shot_evolver("event")
        shot = evolver(cue=cue, table=table, balls=balls)
        try:
            shot.simulate(name=f"factor: {spacing_factor}; n: {n}", continuize=False)
        except:
            shot.progress.end()
            continue

        # Count how many balls were potted, ignoring cue ball
        balls_potted = sum(
            [
                isinstance(event, BallPocketCollision) and event.agents[0].id != "cue"
                for event in shot.events
            ]
        )

        shot.run.info("Balls potted", balls_potted)
        score[n] = balls_potted

        if balls_potted > best_break:
            shot.continuize()
            interface.set_shot(shot)
            interface.start()
            best_break = balls_potted

    score_means[i] = np.mean(score)
    score_stds[i] = np.std(score)

import ipdb

ipdb.set_trace()
