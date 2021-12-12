#! /usr/bin/env python

import numpy as np
import pooltool as pt

np.random.seed(42)

table = pt.PocketTable(model_name='7_foot')
balls = pt.get_nine_ball_rack(table, ordered=True)
cue = pt.Cue(cueing_ball=balls['cue'])

# Aim at the head ball then strike the cue ball
cue.aim_at_ball(balls['1'])
cue.strike(V0=8)

# Create a system and and save it
shot = pt.System(cue=cue, table=table, balls=balls)
shot.save('benchmark_configuration.pkl')
