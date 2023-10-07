from typing import Any, List, Literal

import numpy as np
import pytest

import pooltool.math as math
from pooltool.game.layouts import (
    BallPos,
    Dir,
    Pos,
    Trans,
    _get_anchor_translation,
    _get_ball_ids,
    _get_rack,
    get_nine_ball_rack,
)
from pooltool.objects import Ball, BallParams, Table
from pooltool.physics.utils import is_overlapping


def test_get_ball_ids():
    anchor = (0.5, 0.5)
    trans = [Trans(direction=Dir.UP, quantity=1)]
    ball_pos_1 = BallPos(loc=trans, relative_to=anchor, ids={"1", "2"})
    ball_pos_2 = BallPos(loc=trans, relative_to=anchor, ids={"1", "3", "4"})

    result = _get_ball_ids([ball_pos_1, ball_pos_2])
    assert result == {"1", "2", "3", "4"}


def test_get_anchor_translation_direct():
    """BallPos directly references an Anchor"""
    anchor = (0.5, 0.5)
    trans = [Trans(direction=Dir.UP, quantity=1)]
    ball_pos = BallPos(loc=trans, relative_to=anchor, ids={"1"})

    anchor_result, translation_result = _get_anchor_translation(ball_pos)
    assert anchor_result == anchor
    assert translation_result == trans


def test_get_anchor_translation_multi_level():
    """Multiple levels of positions before reaching the Anchor"""
    anchor = (0.5, 0.5)
    trans1 = [Trans(direction=Dir.UP, quantity=1)]
    pos1 = Pos(loc=trans1, relative_to=anchor)
    trans2 = [Trans(direction=Dir.LEFT, quantity=1)]
    pos2 = Pos(loc=trans2, relative_to=pos1)
    trans3 = [Trans(direction=Dir.DOWN, quantity=1)]
    ball_pos = BallPos(loc=trans3, relative_to=pos2, ids={"1"})

    anchor_result, translation_result = _get_anchor_translation(ball_pos)
    assert anchor_result == anchor
    assert translation_result == trans3 + trans2 + trans1


def test_get_anchor_translation_mixed_hierarchy():
    """A mix of Pos and BallPos in the parent hierarchy"""
    anchor = (0.5, 0.5)
    trans1 = [Trans(direction=Dir.UP, quantity=1)]
    pos1 = Pos(loc=trans1, relative_to=anchor)
    trans2 = [Trans(direction=Dir.LEFT, quantity=1)]
    ball_pos1 = BallPos(loc=trans2, relative_to=pos1, ids={"1"})
    trans3 = [Trans(direction=Dir.DOWN, quantity=1)]
    ball_pos2 = BallPos(loc=trans3, relative_to=ball_pos1, ids={"2"})

    anchor_result, translation_result = _get_anchor_translation(ball_pos2)
    assert anchor_result == anchor
    assert translation_result == trans3 + trans2 + trans1


@pytest.fixture
def radius():
    """Arbitrary radius value for testing"""
    return 10


@pytest.mark.parametrize(
    "directions,quantities,expected_x,expected_y",
    [
        ([Dir.LEFT], [1], -20, 0),
        ([Dir.RIGHT], [1], 20, 0),
        ([Dir.UP], [1], 0, 20),
        ([Dir.DOWN], [1], 0, -20),
        ([Dir.UPRIGHT], [1], 10, 10 * np.sqrt(3)),
        ([Dir.DOWNRIGHT], [1], 10, -10 * np.sqrt(3)),
        ([Dir.UPLEFT], [1], -10, 10 * np.sqrt(3)),
        ([Dir.DOWNLEFT], [1], -10, -10 * np.sqrt(3)),
        # Neutralizations
        ([Dir.LEFT, Dir.RIGHT], [1, 1], 0, 0),
        ([Dir.UP, Dir.DOWN], [1, 1], 0, 0),
        ([Dir.UPLEFT, Dir.DOWNRIGHT], [1, 1], 0, 0),
        ([Dir.UPRIGHT, Dir.DOWNLEFT], [1, 1], 0, 0),
    ],
)
def test_get_translation(directions, quantities, expected_x, expected_y, radius):
    x, y = 0, 0
    for direction, quantity in zip(directions, quantities):
        trans = Trans(direction, quantity)
        dx, dy = trans.eval(radius)
        x += dx
        y += dy
    assert x == expected_x
    assert y == expected_y


SPACING_FACTOR = 0.1


def _two_ball_rack():
    R = 0.03
    ball_params = BallParams(R=R)

    return _get_rack(
        blueprint=[
            (ball_one := BallPos([], relative_to=(0.5, 0.5), ids={"1"})),
            BallPos([Trans(Dir.LEFT)], relative_to=ball_one, ids={"2"}),
        ],
        table=Table.pocket_table(),
        ball_params=ball_params,
        spacing_factor=SPACING_FACTOR,
    )


def test_wiggle():
    _distance_array: List[float] = []

    for _ in range(1000):
        rack = _two_ball_rack()
        ball1 = rack["1"]
        ball2 = rack["2"]
        distance = (
            math.norm3d(ball1.state.rvw[0] - ball2.state.rvw[0]) - 2 * ball1.params.R
        )

        # Distance always greater than 0
        assert distance > 0

        # Distance never greater than 4 * R * spacing_factor
        assert distance < 4 * SPACING_FACTOR * ball1.params.R

        _distance_array.append(distance)
