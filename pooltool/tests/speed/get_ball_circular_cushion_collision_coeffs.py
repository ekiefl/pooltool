#! /usr/bin/env python

import pooltool as pt

import IPython

ipython = IPython.get_ipython()

def get_args():
    return (
        np.random.rand(9).reshape((3,3)),
        2,
        0.42,
        0.18,
        0.05,
        0.06,
        0.02,
        9.8,
        0.0285
    )

def old():
    pt.physics.get_ball_circular_cushion_collision_coeffs(*get_args())

def new():
    pt.physics.get_ball_circular_cushion_collision_coeffs_fast(*get_args())

new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")

args = get_args()
output1 = pt.physics.get_ball_circular_cushion_collision_coeffs(*args)
output2 = pt.physics.get_ball_circular_cushion_collision_coeffs_fast(*args)
np.testing.assert_allclose(output1, output2)


