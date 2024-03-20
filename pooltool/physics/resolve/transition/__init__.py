"""Defining and handling ball state transitions

Note:
    If this module is ever extended to support multiple treatments for ball transitions,
    expand this file into a file structure modelled after ../ball_ball or
    ../ball_cushion
"""

from typing import Dict, Optional, Protocol, Tuple, Type

import numpy as np

import pooltool.constants as const
from pooltool.events.datatypes import EventType
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class BallTransitionStrategy(Protocol):
    """Ball transition models must satisfy this protocol"""

    def resolve(self, ball: Ball, transition: EventType, inplace: bool = False) -> Ball:
        """This method resolves a ball transition"""
        ...


class CanonicalTransition:
    def resolve(self, ball: Ball, transition: EventType, inplace: bool = False) -> Ball:
        if not inplace:
            ball = ball.copy()

        assert transition.is_transition()
        start, end = _ball_transition_motion_states(transition)

        assert (
            ball.state.s == start
        ), f"Start state was {ball.state.s}, expected {start}"
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


class BallTransitionModel(StrEnum):
    """An Enum for different transition models

    Attributes:
        CANONICAL:
            Sets the ball to appropriate state. Sets any residual quantities to 0 when
            appropriate (:class:`CanonicalTransition`).
    """

    CANONICAL = auto()


_ball_transition_models: Dict[BallTransitionModel, Type[BallTransitionStrategy]] = {
    BallTransitionModel.CANONICAL: CanonicalTransition,
}


def get_transition_model(
    model: Optional[BallTransitionModel] = None,
    params: ModelArgs = {},
) -> BallTransitionStrategy:
    """Returns a transition model

    Args:
        model:
            An Enum specifying the desired model. If not passed,
            :class:`CanonicalTransition` is passed with empty params.
        params:
            A mapping of parameters accepted by the model.

    Returns:
        An instantiated model that satisfies the :class:`BallTransitionStrategy`
        protocol.
    """
    if model is None:
        return CanonicalTransition()

    return _ball_transition_models[model](**params)
