from __future__ import annotations

from functools import cached_property
from typing import Dict

import attrs

from pooltool.game.datatypes import GameType
from pooltool.utils.strenum import StrEnum, auto


@attrs.define(frozen=True, slots=False)
class BallParams:
    """Pool ball parameters and physical constants

    Most of the default values are taken from or based off of
    https://billiards.colostate.edu/faq/physics/physical-properties/. All units are SI.
    Some of the parameters aren't truly _ball_ parameters, e.g. the gravitational
    constant, however it is nice to be able to tune such parameters on a ball-by-ball
    basis.

    Attributes:
        m:
            Mass.
        R:
            Radius.
        u_s:
            Coefficient of sliding friction.
        u_r:
            Coefficient of rolling friction.
        u_sp_proportionality:
            The coefficient of spinning friction is proportional ball radius. This is
            the proportionality constant. To obtain the coefficient of spinning
            friction, use the property `u_sp`.
        e_c:
            Cushion coefficient of restitution.
        f_c:
            Cushion coefficient of friction.
        g:
            Gravitational constant.
    """

    m: float = attrs.field(default=0.170097)
    R: float = attrs.field(default=0.028575)

    u_s: float = attrs.field(default=0.2)
    u_r: float = attrs.field(default=0.01)
    u_sp_proportionality: float = attrs.field(default=10 * 2 / 5 / 9)
    e_c: float = attrs.field(default=0.85)
    f_c: float = attrs.field(default=0.2)
    g: float = attrs.field(default=9.81)

    @cached_property
    def u_sp(self) -> float:
        """Coefficient of spinning friction (radius dependent)"""
        return self.u_sp_proportionality * self.R

    def copy(self) -> BallParams:
        """Return deepish copy

        Class is frozen and attributes are immutable. Just return self
        """
        return self

    @classmethod
    def default(cls, game_type: GameType = GameType.EIGHTBALL) -> BallParams:
        return get_default_ball_params(game_type=game_type)

    @classmethod
    def prebuilt(cls, name: PrebuiltBallParams) -> BallParams:
        return prebuilt_ball_params(name)


class PrebuiltBallParams(StrEnum):
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


def get_default_ball_params(game_type: GameType) -> BallParams:
    return prebuilt_ball_params(_default_map[game_type])


def prebuilt_ball_params(name: PrebuiltBallParams) -> BallParams:
    return BALL_PARAMS[name]
