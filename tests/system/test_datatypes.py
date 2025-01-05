import pytest

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
