#! /usr/bin/env python

import IPython

import pooltool as pt

ipython = IPython.get_ipython()


def get_args():
    return (
        np.random.rand(9).reshape((3, 3)),
        np.random.rand(9).reshape((3, 3)),
        2,
        3,
        0.18,
        0.04,
        0.05,
        0.05,
        9.8,
        9.8,
        0.0285,
    )


def old():
    pt.physics.get_ball_ball_collision_coeffs(*get_args())


def new():
    pt.physics.get_ball_ball_collision_coeffs_fast(*get_args())


new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")

args = get_args()
output1 = pt.physics.get_ball_ball_collision_coeffs(*args)
output2 = pt.physics.get_ball_ball_collision_coeffs_fast(*args)
np.testing.assert_allclose(output1, output2)
