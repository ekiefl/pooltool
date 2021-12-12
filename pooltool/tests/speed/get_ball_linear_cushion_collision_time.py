#! /usr/bin/env python

import pooltool as pt

import IPython

ipython = IPython.get_ipython()

def get_point():
    x = np.random.rand(3)
    x[2] = 0.0285*7/5
    return x

def get_args():
    return (
        np.random.rand(9).reshape((3,3)),
        2,
        10*np.random.rand()-5,
        10*np.random.rand()-5,
        10*np.random.rand()-5,
        get_point(),
        get_point(),
        0.06,
        0.04,
        9.8,
        0.0285
    )

def old():
    pt.physics.get_ball_linear_cushion_collision_time(*get_args())

def new():
    pt.physics.get_ball_linear_cushion_collision_time_fast(*get_args())

new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")

output1 = []
output2 = []
for _ in range(100000):
    args = get_args()
    output1.append(pt.physics.get_ball_linear_cushion_collision_time(*args))
    output2.append(pt.physics.get_ball_linear_cushion_collision_time_fast(*args))
output1 = np.array(output1)
output2 = np.array(output2)

np.testing.assert_allclose(output1, output2)


