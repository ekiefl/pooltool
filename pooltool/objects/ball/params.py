from __future__ import annotations

from functools import cached_property
from typing import Dict

import attrs

from pooltool.game.datatypes import GameType
from pooltool.utils.strenum import StrEnum, auto


@attrs.define(frozen=True, slots=False)
class BallParams:
    """Ball parameters and physical constants

    Note:
        The presence of an attribute does not guarantee its usage by the physics engine.
        For example, if the frictionless elastic ball-ball collision model is used, then
        `u_b`, the ball-ball sliding coefficient of friction, will have no affect on the
        simulation.

    Attributes:
        m:
            The mass of the ball (*default* = 0.170097
        R:
            The radius of the ball (*default* = 0.028575).
        u_s:
            The sliding coefficient of friction (*default* = 0.2).

            References:
                - https://ekiefl.github.io/2020/04/24/pooltool-theory/#case-4-sliding
        u_r:
            The rolling coefficient of friction (*default* = 0.01).

            References:
                - https://ekiefl.github.io/2020/04/24/pooltool-theory/#case-3-rolling
        u_sp_proportionality:
            The spinning coefficient of friction, with R factored out (*default* = 0.01).

            See Also:
                - For the coefficient of spinning friction, use the property :meth:`u_sp`.

            References:
                - https://ekiefl.github.io/2020/04/24/pooltool-theory/#case-2-spinning
        u_b:
            The ball-ball coefficient of sliding friction (*default* = 0.05).
        e_b:
            The ball-ball coefficient of restitution (*default* = 0.95).
        e_c:
            The cushion coefficient of restitution (*default* = 0.85).

            Note:
                This is a potentially model-dependent ball-cushion parameter and should be
                placed elsewhere, either as a model parameter or as a cushion segment parameter.
        f_c:
            The cushion coefficient of friction (*default* = 0.2).

            Note:
                This is a potentially model-dependent ball-cushion parameter and should be
                placed elsewhere, either as a model parameter or as a cushion segment parameter.
        g:
            The gravitational constant (*default* = 9.81).

    Most of the default values (SI units) are taken from or based off of
    https://billiards.colostate.edu/faq/physics/physical-properties/.

    Some of the parameters aren't truly *ball* parameters, e.g. the gravitational
    constant. However, it is nice to be able to tune such parameters on a ball-by-ball
    basis, so they are included here.
    """

    m: float = attrs.field(default=0.170097)
    R: float = attrs.field(default=0.028575)
    u_s: float = attrs.field(default=0.2)
    u_r: float = attrs.field(default=0.01)
    u_sp_proportionality: float = attrs.field(default=10 * 2 / 5 / 9)
    u_b: float = attrs.field(default=0.05)
    e_b: float = attrs.field(default=0.95)
    e_c: float = attrs.field(default=0.85)
    f_c: float = attrs.field(default=0.2)
    g: float = attrs.field(default=9.81)

    @cached_property
    def u_sp(self) -> float:
        """Coefficient of spinning friction

        This is equal to :attr:`u_sp_proportionality` * :attr:`R`

        .. cached_property_note::
        """
        return self.u_sp_proportionality * self.R

    def copy(self) -> BallParams:
        """Return a copy

        Note:
            - Since the class is frozen and its attributes are immutable, this just
              returns ``self``.
        """
        return self

    @classmethod
    def default(cls, game_type: GameType = GameType.EIGHTBALL) -> BallParams:
        """Return prebuilt ball parameters based on game type

        Args:
            game_type:
                What type of game is being played?

        Returns:
            BallParams:
                The prebuilt ball parameters associated with the passed game type.
        """
        return _get_default_ball_params(game_type=game_type)

    @classmethod
    def prebuilt(cls, name: PrebuiltBallParams) -> BallParams:
        """Return prebuilt ball parameters based on name

        Args:
            name:
                A :class:`PrebuiltBallParams` member.

        All prebuilt ball parameters are named with the :class:`PrebuiltBallParams`
        Enum. This constructor takes a prebuilt name and returns the corresponding ball
        parameters.

        See Also:
            - :class:`PrebuiltBallParams`
        """
        return _prebuilt_ball_params(name)


class PrebuiltBallParams(StrEnum):
    """An Enum specifying prebuilt ball parameters"""

    POOL_GENERIC = auto()
    SNOOKER_GENERIC = auto()
    BILLIARD_GENERIC = auto()


# NOTE: nothing here is well-researched or perfect. If you think you have better
# parameters, you probably do. Please share them.

BALL_PARAMS: Dict[PrebuiltBallParams, BallParams] = {
    PrebuiltBallParams.POOL_GENERIC: BallParams(
        m=0.170097,
        R=0.028575,
        u_s=0.2,
        u_r=0.01,
        u_sp_proportionality=10 * 2 / 5 / 9,
        e_c=0.85,
        f_c=0.2,
        g=9.81,
    ),
    PrebuiltBallParams.SNOOKER_GENERIC: BallParams(
        m=0.140,
        R=0.02619375,
        u_s=0.5,
        u_r=0.01,
        u_sp_proportionality=10 * 2 / 5 / 9,
        e_c=0.85,
        f_c=0.5,
        g=9.81,
    ),
    PrebuiltBallParams.BILLIARD_GENERIC: BallParams(
        m=0.210,
        R=0.03048,
        u_s=0.5,
        u_r=0.01,
        u_sp_proportionality=10 * 2 / 5 / 9,
        e_c=0.85,
        f_c=0.5,
        g=9.81,
    ),
}


_default_map: Dict[GameType, PrebuiltBallParams] = {
    GameType.EIGHTBALL: PrebuiltBallParams.POOL_GENERIC,
    GameType.NINEBALL: PrebuiltBallParams.POOL_GENERIC,
    GameType.THREECUSHION: PrebuiltBallParams.BILLIARD_GENERIC,
    GameType.SNOOKER: PrebuiltBallParams.SNOOKER_GENERIC,
    GameType.SANDBOX: PrebuiltBallParams.POOL_GENERIC,
}


def _get_default_ball_params(game_type: GameType) -> BallParams:
    return _prebuilt_ball_params(_default_map[game_type])


def _prebuilt_ball_params(name: PrebuiltBallParams) -> BallParams:
    return BALL_PARAMS[name]
