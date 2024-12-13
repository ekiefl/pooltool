from math import isclose

import pytest

from pooltool.physics.resolve.ball_table.frictionless_inelastic import (
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
