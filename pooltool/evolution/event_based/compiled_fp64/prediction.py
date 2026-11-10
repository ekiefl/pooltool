"""Stock planar event prediction from packed state using Pooltool's native roots."""

import numpy as np
from numba import njit

from pooltool import constants as const
from pooltool import ptmath
from pooltool.evolution.event_based.detect.ball_ball import ball_ball_collision_time_2d
from pooltool.evolution.event_based.detect.ball_cushion import (
    ball_vertical_cylinder_collision_time,
    ball_vertical_plane_collision_time,
)
from pooltool.evolution.event_based.detect.ball_pocket import ball_pocket_collision_time
from pooltool.physics.utils import get_roll_time, get_slide_time, get_spin_time


@njit(cache=True)
def _translating(state):
    return state == const.sliding or state == const.rolling


@njit(cache=True)
def _friction(state, params):
    return params[2] if state == const.sliding else params[4]


@njit(cache=True)
def ball_ball_time(left, right, left_state, right_state, left_params, right_params):
    if left_state == const.pocketed or right_state == const.pocketed:
        return np.inf
    if not _translating(left_state) and not _translating(right_state):
        return np.inf
    if ptmath.norm3d(left[0] - right[0]) < left_params[0] + right_params[0]:
        return 0.0
    return ball_ball_collision_time_2d(
        left,
        right,
        left_state,
        right_state,
        _friction(left_state, left_params),
        _friction(right_state, right_params),
        left_params[1],
        right_params[1],
        left_params[5],
        right_params[5],
        left_params[0],
    )


@njit(cache=True)
def transition_time(rvw, state, params):
    if state == const.stationary or state == const.pocketed:
        return np.inf, state
    if state == const.sliding:
        return get_slide_time(rvw, params[0], params[2], params[5]), const.rolling
    spin = get_spin_time(rvw, params[0], params[3], params[5])
    if state == const.spinning:
        return spin, const.stationary
    if state == const.rolling:
        roll = get_roll_time(rvw, params[4], params[5])
        return roll, const.spinning if spin > roll else const.stationary
    raise ValueError("Unknown planar motion state")


@njit(cache=True)
def linear_time(rvw, state, params, row):
    return ball_vertical_plane_collision_time(
        rvw,
        state,
        row[0],
        row[1],
        row[2],
        row[6:9],
        row[9:12],
        int(row[3]),
        _friction(state, params),
        params[1],
        params[5],
        params[0],
        row[4],
        row[5],
    )


@njit(cache=True)
def circular_time(rvw, state, params, row):
    return ball_vertical_cylinder_collision_time(
        rvw,
        state,
        row[0],
        row[1],
        row[2],
        _friction(state, params),
        params[1],
        params[5],
        params[0],
    )


@njit(cache=True)
def pocket_time(rvw, state, params, row):
    return ball_pocket_collision_time(
        rvw,
        state,
        row[0],
        row[1],
        row[2],
        _friction(state, params),
        params[1],
        params[5],
        params[0],
    )
