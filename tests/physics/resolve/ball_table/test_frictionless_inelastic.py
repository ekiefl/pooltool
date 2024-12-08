from math import isclose

import pytest

from pooltool.physics.resolve.ball_table.frictionless_inelastic import (
    _bounce_height,
    _resolve_ball_table,
)


@pytest.mark.parametrize(
    "vz0,e_t,expected",
    [
        (-5.0, 0.9, 4.5),
        (-1.0, 1.0, 1.0),
        (-2.0, 0.5, 1.0),
        (-3.5, 0.75, 2.625),
    ],
)
def test_resolve_ball_table_valid(vz0, e_t, expected):
    result = _resolve_ball_table(vz0, e_t)
    assert isclose(result, expected), f"Expected {expected}, got {result}"


@pytest.mark.parametrize("vz0,e_t", [(0.0, 1.0), (1.0, 0.5), (2.0, 0.9)])
def test_resolve_ball_table_invalid(vz0, e_t):
    with pytest.raises(ValueError, match="can't collide with table surface"):
        _resolve_ball_table(vz0, e_t)


@pytest.mark.parametrize(
    "vz,g,expected",
    [
        (4.0, 9.8, 0.5 * 16 / 9.8),  # Typical scenario
        (0.0, 9.8, 0.0),  # No velocity, no bounce height
        (10.0, 9.8, 0.5 * 100 / 9.8),
        (2.5, 10.0, 0.5 * 6.25 / 10.0),
    ],
)
def test_bounce_height(vz, g, expected):
    result = _bounce_height(vz, g)
    assert isclose(result, expected, rel_tol=1e-7), f"Expected {expected}, got {result}"


def test_bounce_height_negative_vz():
    # The function doesn't specify behavior for negative vz, but it still returns
    # a mathematically valid height based on vz^2. Let's just check correctness.
    vz = -3.0
    g = 9.8
    expected = 0.5 * (vz**2) / g
    result = _bounce_height(vz, g)
    assert isclose(result, expected, rel_tol=1e-7), f"Expected {expected}, got {result}"
