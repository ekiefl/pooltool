import numpy as np
import pytest

import pooltool.constants as const
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.detect.stick_ball import get_next_stick_ball_event
from pooltool.system.datatypes import System


@pytest.fixture
def system() -> System:
    shot = System.example()
    shot.strike(V0=2.0, phi=90.0)
    return shot


def test_strike_is_detected_at_rest(system: System):
    event = get_next_stick_ball_event(system, CollisionCache())
    assert event.time == 0.0


def test_pocketed_cue_ball_is_not_struck(system: System):
    """Regression: striking a pocketed cue ball looped forever.

    The strike resolver keeps a ball below the cloth labelled pocketed, so the ball
    never evolves, the clock stays at zero, and the system still reads as at rest.
    Every detection then scheduled another strike at t=0.
    """
    cue_ball = system.balls[system.cue.cue_ball_id]
    cue_ball.state.rvw[0, 2] = -0.1
    cue_ball.state.s = const.pocketed

    event = get_next_stick_ball_event(system, CollisionCache())

    assert event.time == np.inf
