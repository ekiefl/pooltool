#! /usr/bin/env python

import pooltool as pt
from pooltool.tests import ball_kwargs

from pooltool.objects.ball import Ball

import numpy as np
import pytest

@pytest.fixture
def sliding_ball():
    ball = pt.Ball('slider', **ball_kwargs)
    ball.s = pt.sliding
    ball.t = 0.2683117547266862
    ball.rvw = np.array([[ 0.558495956 ,  1.1708239284,  0.028575    ],
                         [ 0.2065399331, -1.0318073007,  0.          ],
                         [23.8435883169,  4.7677823238,  0.          ]])
    return ball


@pytest.fixture
def rolling_ball():
    ball = pt.Ball('roller', **ball_kwargs)
    ball.s = pt.rolling
    ball.t = 0.8678446812335155
    ball.rvw = np.array([[  0.0793380432,   0.5162592019,   0.028575    ],
                         [ -0.9207017729,  -1.0939068711,   0.          ],
                         [ 38.2819552455, -32.2205344845,   0.          ]])
    return ball


@pytest.fixture
def spinning_ball():
    ball = pt.Ball('spinner', **ball_kwargs)
    ball.s = pt.spinning
    ball.t = 2.2394790988971039
    ball.rvw = np.array([[ 0.6663102336,  1.8105621081,  0.028575    ],
                         [-0.          , -0.          ,  0.          ],
                         [ 0.          , -0.          , -5.5525921609]])
    return ball


@pytest.fixture
def stationary_ball():
    ball = pt.Ball('still_guy', **ball_kwargs)
    ball.s = pt.stationary
    ball.t = 6.653887765968978
    ball.rvw = np.array([[ 0.6663102336,  1.8105621081,  0.028575    ],
                         [-0.          , -0.          ,  0.          ],
                         [ 0.          , -0.          ,  0.          ]])
    return ball


@pytest.fixture
def pocketed_ball():
    ball = pt.Ball('pocketed_guy', **ball_kwargs)
    ball.s = pt.pocketed
    ball.t = 4.353881365968999
    ball.rvw = np.array([[ 1.05947,  0.9906 , -0.08   ],
                         [ 0.     ,  0.     ,  0.     ],
                         [ 0.     ,  0.     ,  0.     ]])
    return ball


