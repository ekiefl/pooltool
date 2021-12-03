#! /usr/bin/env python

import pooltool as pt
import pooltool.events as e

from pooltool.objects.ball import Ball

import numpy as np
import pytest


@pytest.fixture
def ball_ball_collision_pack():
    ball1 = pt.Ball('bb_col_1', R=0.028575)
    ball1.t = 0.31675163783635946
    ball1.s = pt.rolling
    ball1.rvw = np.array([[ 0.7156550785,  1.3592112575,  0.028575    ],
                         [ 0.768198785 , -0.442058814 ,  0.          ],
                         [15.4701247249, 26.8835970251,  0.          ]])

    ball2 = pt.Ball('bb_col_2', R=0.028575)
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

