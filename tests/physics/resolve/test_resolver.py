import attrs
import pytest

import pooltool.constants as const
from pooltool.error import SimulateError
from pooltool.events import ball_linear_cushion_collision
from pooltool.objects import Ball, LinearCushionSegment
from pooltool.physics.resolve.resolver import default_resolver
from pooltool.system.datatypes import System

ON_TABLE_STATES = [const.stationary, const.spinning, const.sliding, const.rolling]


@attrs.define
class RiggedLinearCushionModel:
    """A stand-in strategy that plants a prescribed post-collision height and state."""

    z: float
    s: int

    def resolve(
        self, ball: Ball, cushion: LinearCushionSegment, inplace: bool = False
    ) -> tuple[Ball, LinearCushionSegment]:
        ball.state.rvw[0, 2] = self.z
        ball.state.s = self.s
        return ball, cushion


@pytest.fixture
def shot() -> System:
    return System.example()


def resolve_rigged(shot: System, z: float, s: int) -> None:
    """Resolve a cushion event whose strategy leaves the cue ball at height z, state s."""
    resolver = attrs.evolve(
        default_resolver(), ball_linear_cushion=RiggedLinearCushionModel(z, s)
    )
    ball = shot.balls["cue"]
    cushion = next(iter(shot.table.cushion_segments.linear.values()))
    event = ball_linear_cushion_collision(ball, cushion, time=0.0)
    resolver.resolve(shot, event)


@pytest.mark.parametrize("s", [*ON_TABLE_STATES, const.airborne])
def test_resolve_allows_ball_at_exact_table_height(shot: System, s: int) -> None:
    R = shot.balls["cue"].params.R

    resolve_rigged(shot, R, s)

    assert shot.balls["cue"].state.rvw[0, 2] == R


@pytest.mark.parametrize("s", [*ON_TABLE_STATES, const.airborne])
@pytest.mark.parametrize("deficit", [1e-16, 0.01])
def test_resolve_rejects_underground_ball(shot: System, s: int, deficit: float) -> None:
    R = shot.balls["cue"].params.R

    with pytest.raises(SimulateError, match="underground"):
        resolve_rigged(shot, R - deficit, s)


@pytest.mark.parametrize("s", ON_TABLE_STATES)
@pytest.mark.parametrize("excess", [1e-16, 0.05])
def test_resolve_rejects_floating_on_table_ball(
    shot: System, s: int, excess: float
) -> None:
    R = shot.balls["cue"].params.R

    with pytest.raises(SimulateError, match="floating"):
        resolve_rigged(shot, R + excess, s)


def test_resolve_allows_airborne_ball_above_table(shot: System) -> None:
    R = shot.balls["cue"].params.R

    resolve_rigged(shot, R + 0.05, const.airborne)

    assert shot.balls["cue"].state.rvw[0, 2] == R + 0.05


def test_resolve_allows_pocketed_ball_below_table(shot: System) -> None:
    resolve_rigged(shot, -0.1, const.pocketed)

    assert shot.balls["cue"].state.rvw[0, 2] == -0.1
