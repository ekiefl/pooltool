import pytest

from pooltool.objects.ball.datatypes import Ball
from pooltool.system.datatypes import System


def test_cue_ball_id_mismatch():
    system = System.example()

    # Cannot create instance with cue_ball_id not in balls
    system.cue.cue_ball_id = "absent"
    with pytest.raises(ValueError):
        System(
            cue=system.cue,
            balls=system.balls,
            table=system.table,
        )


def test_system_raises_on_unequal_radii():
    b1 = Ball.create("1", R=1.0)
    b2 = Ball.create("2", R=1.5)

    template = System.example()

    with pytest.raises(AssertionError, match="different radius"):
        System(balls={"1": b1, "2": b2}, cue=template.cue, table=template.table)
