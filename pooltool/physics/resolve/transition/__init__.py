"""Defining and handling ball state transitions

Note:
    If this module is ever extended to support multiple treatments for ball transitions,
    it should be expanded into a subpackage to match the other event types.
"""

from typing import Dict, Protocol, Tuple, Type, cast

import attrs
import numpy as np

import pooltool.constants as const
from pooltool.events.datatypes import EventType
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.models import BallTransitionModel


class BallTransitionStrategy(Protocol):
    """Ball transition models must satisfy this protocol"""

    def resolve(self, ball: Ball, transition: EventType, inplace: bool = False) -> Ball:
        """This method resolves a ball transition"""
        ...


@attrs.define
class CanonicalTransition:
    model: BallTransitionModel = attrs.field(
        default=BallTransitionModel.CANONICAL, init=False, repr=False
    )

    def resolve(self, ball: Ball, transition: EventType, inplace: bool = False) -> Ball:
        if not inplace:
            ball = ball.copy()

        assert transition.is_transition()
        start, end = _ball_transition_motion_states(transition)

        assert ball.state.s == start, (
            f"Start state was {ball.state.s}, expected {start}"
        )
        ball.state.s = end

        if end == const.spinning:
            # Assert that the velocity components are nearly 0, and that the x and y
            # angular velocity components are nearly 0. Then set them to exactly 0.
            v = ball.state.rvw[1]
            w = ball.state.rvw[2]
            assert (np.abs(v) < const.EPS_SPACE).all()
            assert (np.abs(w[:2]) < const.EPS_SPACE).all()

            ball.state.rvw[1, :] = [0.0, 0.0, 0.0]
            ball.state.rvw[2, :2] = [0.0, 0.0]

        if end == const.stationary:
            # Assert that the linear and angular velocity components are nearly 0, then
            # set them to exactly 0.
            v = ball.state.rvw[1]
            w = ball.state.rvw[2]
            assert (np.abs(v) < const.EPS_SPACE).all()
            assert (np.abs(w) < const.EPS_SPACE).all()

            ball.state.rvw[1, :] = [0.0, 0.0, 0.0]
            ball.state.rvw[2, :] = [0.0, 0.0, 0.0]

        return ball


def _ball_transition_motion_states(event_type: EventType) -> Tuple[int, int]:
    """Return the ball motion states before and after a transition"""
    assert event_type.is_transition()

    if event_type == EventType.SPINNING_STATIONARY:
        return const.spinning, const.stationary
    elif event_type == EventType.ROLLING_STATIONARY:
        return const.rolling, const.stationary
    elif event_type == EventType.ROLLING_SPINNING:
        return const.rolling, const.spinning
    elif event_type == EventType.SLIDING_ROLLING:
        return const.sliding, const.rolling

    raise NotImplementedError()


_ball_transition_model_registry: Tuple[Type[BallTransitionStrategy], ...] = (
    CanonicalTransition,
)

ball_transition_models: Dict[BallTransitionModel, Type[BallTransitionStrategy]] = {
    cast(BallTransitionModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_transition_model_registry
}
