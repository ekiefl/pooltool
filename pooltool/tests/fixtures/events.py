#! /usr/bin/env python

import pooltool as pt
import pooltool.events as e

from pooltool.objects.ball import Ball
from pooltool.objects.table import LinearCushionSegment
from pooltool.tests import ball_kwargs

import numpy as np
import pytest


@pytest.fixture
def ball_ball_collision_pack():
    ball1 = pt.Ball('bb_col_1', **ball_kwargs)
    ball1.t = 0.31675163783635946
    ball1.s = pt.rolling
    ball1.rvw = np.array([[ 0.7156550785,  1.3592112575,  0.028575    ],
                         [ 0.768198785 , -0.442058814 ,  0.          ],
                         [15.4701247249, 26.8835970251,  0.          ]])

    ball2 = pt.Ball('bb_col_2', **ball_kwargs)
    ball2.t = 0.31675163783635946
    ball2.s = pt.sliding
    ball2.rvw = np.array([[  0.762834946 ,   1.3914631195,   0.028575    ],
                         [ -3.7111259659,  -2.3636516807,   0.          ],
                         [-26.5315725209, -38.6639930306,  78.7217015808]])

    ball1_expected =  np.array([[ 0.7156550785,  1.3592112575,  0.028575    ],
                                [-3.1798091395, -3.1408923089,  0.          ],
                                [15.4701247249, 26.8835970251,  0.          ]])

    ball2_expected =  np.array([[  0.762834946 ,   1.3914631195,   0.028575    ],
                                [  0.2368819586,   0.3351818142,   0.          ],
                                [-26.5315725209, -38.6639930306,  78.7217015808]])

    return ball1, ball2, ball1_expected, ball2_expected


@pytest.fixture
def ball_cushion_collision_pack():
    ball = pt.Ball('ball', **ball_kwargs)
    ball.t = 1.8225386505474912
    ball.s = pt.rolling
    ball.rvw = np.array([[  0.962025    ,   1.7859591294,   0.028575    ],
                         [  0.9251162591,   1.4537628231,   0.          ],
                         [-50.8753393928,  32.3750221915,  64.0105147063]])

    ball_expected = np.array([[  0.962025    ,   1.7859591294,   0.028575    ],
                              [ -0.746901863 ,   0.4204048651,   0.          ],
                              [-25.5612336846,   2.7750019021, -22.7807048646]])

    p1 = [0.9906, 1.8901982772122183, 0.036576]
    p2 = [0.9906, 1.0661162692312498, 0.036576]
    cushion = LinearCushionSegment('cushion', p1, p2)

    return ball, cushion, ball_expected
