#! /usr/bin/env python
from __future__ import annotations

from dataclasses import astuple, dataclass, field, replace
from typing import Any, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

import pooltool.constants as c
from pooltool.utils.dataclasses import are_dataclasses_equal


@dataclass(frozen=True)
class BallOrientation:
    """Stores a ball's rendered orientation"""

    pos: Tuple[float, ...]
    sphere: Tuple[float, ...]

    @staticmethod
    def random() -> BallOrientation:
        quat = (tmp := 2 * np.random.rand(4) - 1) / np.linalg.norm(tmp)
        q0, qx, qy, qz = quat
        return BallOrientation(
            pos=(1, 0, 0, 0),
            sphere=(q0, qx, qy, qz),
        )

    def copy(self) -> BallOrientation:
        """Create a deep copy"""
        return replace(self)


@dataclass(frozen=True)
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

    m: float = field(default=0.170097)
    R: float = field(default=0.028575)

    u_s: float = field(default=0.2)
    u_r: float = field(default=0.01)
    u_sp_proportionality: float = field(default=10 * 2 / 5 / 9)
    e_c: float = field(default=0.85)
    f_c: float = field(default=0.2)
    g: float = field(default=9.8)

    @property
    def u_sp(self) -> float:
        """Coefficient of spinning friction (radius dependent)"""
        return self.u_sp_proportionality * self.R

    @staticmethod
    def default() -> BallParams:
        return BallParams()


def _null_rvw() -> NDArray[np.float64]:
    return np.array([[np.nan, np.nan, np.nan], [0, 0, 0], [0, 0, 0]], dtype=np.float64)


@dataclass(eq=False)
class BallState:
    rvw: NDArray[np.float64]
    s: float
    t: float

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)

    def set(self, rvw, s=None, t=None) -> None:
        self.rvw = rvw
        if s is not None:
            self.s = s
        if t is not None:
            self.t = t

    def copy(self) -> BallState:
        """Create a deep copy"""
        # Twice as fast as copy.deepcopy(self)
        return replace(self, rvw=np.copy(self.rvw))

    @staticmethod
    def default() -> BallState:
        return BallState(
            rvw=_null_rvw(),
            s=c.stationary,
            t=0,
        )


def _float64_array(x: Any) -> NDArray[np.float64]:
    return np.array(x, dtype=np.float64)


@dataclass
class BallHistory:
    states: List[BallState] = field(default_factory=list)

    def __getitem__(self, idx: int) -> BallState:
        return self.states[idx]

    def __len__(self) -> int:
        return len(self.states)

    @property
    def empty(self) -> bool:
        return not bool(len(self.states))

    def add(self, state: BallState) -> None:
        """Append a state to self.states"""
        new = state.copy()

        if not self.empty:
            assert new.t >= self.states[-1].t

        self.states.append(new)

    def copy(self) -> BallHistory:
        """Create a deep copy"""
        history = BallHistory()
        for state in self.states:
            history.add(state)

        return history

    def vectorize(self) -> Tuple[NDArray, NDArray, NDArray]:
        """Return rvw, s, and t as arrays"""
        assert not self.empty, "History is empty"

        return tuple(  # type: ignore
            map(_float64_array, zip(*[astuple(x) for x in self.states]))
        )

    @staticmethod
    def factory() -> BallHistory:
        return BallHistory()


@dataclass
class Ball:
    """A pool ball"""

    id: str
    state: BallState = field(default_factory=BallState.default)
    params: BallParams = field(default_factory=BallParams.default)
    initial_orientation: BallOrientation = field(default_factory=BallOrientation.random)

    history: BallHistory = field(default_factory=BallHistory.factory)
    history_cts: BallHistory = field(default_factory=BallHistory.factory)

    def copy(self) -> Ball:
        """Create a deep copy"""
        # `params` and `initial_orientation` are frozen
        return replace(
            self,
            state=self.state.copy(),
            history=self.history.copy(),
            history_cts=self.history_cts.copy(),
        )

    @staticmethod
    def create(id: str, *, xy: Optional[List[float]] = None, **kwargs) -> Ball:
        """Create ball using a flattened parameter set

        Args:
            xy:
                The x and y coordinates of the ball position.
            **kwargs:
                Parameters accepted by BallParams
        """
        params = BallParams(**kwargs)
        ball = Ball(id=id, params=params)

        if xy is not None:
            ball.state.rvw[0] = [*xy, ball.params.R]

        return ball

    @staticmethod
    def dummy(id: str = "dummy") -> Ball:
        return Ball(id=id)
