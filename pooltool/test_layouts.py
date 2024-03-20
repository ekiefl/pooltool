from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Optional

import attrs
import numpy as np
import pytest
from numpy.typing import NDArray

import pooltool.ptmath as ptmath
from pooltool.layouts import (
    BallPos,
    Dir,
    Jump,
    Pos,
    _get_anchor_translation,
    _get_ball_ids,
    generate_layout,
)
from pooltool.objects import BallParams, Table
from pooltool.objects.ball.datatypes import Ball


def test_get_ball_ids():
    anchor = (0.5, 0.5)
    trans = Jump.UP(1)
    ball_pos_1 = BallPos(loc=trans, relative_to=anchor, ids={"1", "2"})
    ball_pos_2 = BallPos(loc=trans, relative_to=anchor, ids={"1", "3", "4"})

    result = _get_ball_ids([ball_pos_1, ball_pos_2])
    assert result == {"1", "2", "3", "4"}


def test_get_anchor_translation_direct():
    """BallPos directly references an Anchor"""
    anchor = (0.5, 0.5)
    trans = Jump.UP(1)
    ball_pos = BallPos(loc=trans, relative_to=anchor, ids={"1"})

    anchor_result, translation_result = _get_anchor_translation(ball_pos)
    assert anchor_result == anchor
    assert translation_result == trans


def test_get_anchor_translation_multi_level():
    """Multiple levels of positions before reaching the Anchor"""
    anchor = (0.5, 0.5)
    trans1 = Jump.UP(1)
    pos1 = Pos(loc=trans1, relative_to=anchor)
    trans2 = Jump.LEFT(1)
    pos2 = Pos(loc=trans2, relative_to=pos1)
    trans3 = Jump.DOWN(1)
    ball_pos = BallPos(loc=trans3, relative_to=pos2, ids={"1"})

    anchor_result, translation_result = _get_anchor_translation(ball_pos)
    assert anchor_result == anchor
    assert translation_result == trans3 + trans2 + trans1


def test_get_anchor_translation_mixed_hierarchy():
    """A mix of Pos and BallPos in the parent hierarchy"""
    anchor = (0.5, 0.5)
    trans1 = Jump.UP(1)
    pos1 = Pos(loc=trans1, relative_to=anchor)
    trans2 = Jump.LEFT(1)
    ball_pos1 = BallPos(loc=trans2, relative_to=pos1, ids={"1"})
    trans3 = Jump.DOWN(1)
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
        trans = [direction] * quantity
        dx, dy = Jump.eval(trans, radius)
        x += dx
        y += dy
    assert x == expected_x
    assert y == expected_y


SPACING_FACTOR = 0.1


def get_two_ball_rack(seed: Optional[int] = None):
    R = 0.03
    ball_params = BallParams(R=R)

    return generate_layout(
        blueprint=[
            (ball_one := BallPos([], relative_to=(0.5, 0.5), ids={"1", "2"})),
            BallPos(Jump.LEFT(), relative_to=ball_one, ids={"1", "2"}),
        ],
        table=Table.default(),
        ball_params=ball_params,
        spacing_factor=SPACING_FACTOR,
        seed=seed,
    )


def test_wiggle():
    _distance_array: List[float] = []

    for _ in range(1000):
        rack = get_two_ball_rack()
        ball1 = rack["1"]
        ball2 = rack["2"]
        distance = (
            ptmath.norm3d(ball1.state.rvw[0] - ball2.state.rvw[0]) - 2 * ball1.params.R
        )

        # Distance always greater than 0
        assert distance > 0

        # Distance never greater than 4 * R * spacing_factor
        assert distance < 4 * SPACING_FACTOR * ball1.params.R

        _distance_array.append(distance)


@attrs.define
class SeedTestResult:
    ascending_order: bool
    ball1_pos: NDArray
    ball2_pos: NDArray

    @classmethod
    def from_rack(cls, balls: Dict[str, Ball]) -> SeedTestResult:
        ascending_order = balls["1"].state.rvw[0, 0] < balls["2"].state.rvw[0, 0]

        return cls(
            ascending_order=ascending_order,
            ball1_pos=balls["1"].state.rvw[0],
            ball2_pos=balls["2"].state.rvw[0],
        )


def test_seed():
    # Random seed
    results_random_seed: List[SeedTestResult] = []
    for _ in range(20):
        results_random_seed.append(
            SeedTestResult.from_rack(get_two_ball_rack(seed=None))
        )

    all_ascending = all(result.ascending_order for result in results_random_seed)
    all_descending = all(not result.ascending_order for result in results_random_seed)

    # Random, so odds of this is 1/2^19
    assert not all_ascending and not all_descending

    # Random, so positional perturbations (wiggle) ensure different vectors each trial
    for result1, result2 in combinations(results_random_seed, 2):
        assert not np.array_equal(result1.ball1_pos, result2.ball1_pos)
        assert not np.array_equal(result1.ball2_pos, result2.ball2_pos)

    # Fixed seed
    results_fixed_seed: List[SeedTestResult] = []
    for _ in range(20):
        results_fixed_seed.append(SeedTestResult.from_rack(get_two_ball_rack(seed=42)))

    all_ascending = all(result.ascending_order for result in results_fixed_seed)
    all_descending = all(not result.ascending_order for result in results_fixed_seed)

    # Fixed, so ball order is preserved
    assert all_ascending or all_descending

    # Random, so positional perturbations (wiggle) ensure different vectors each trial
    for result1, result2 in combinations(results_fixed_seed, 2):
        assert np.array_equal(result1.ball1_pos, result2.ball1_pos)
        assert np.array_equal(result1.ball2_pos, result2.ball2_pos)
