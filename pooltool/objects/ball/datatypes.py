#! /usr/bin/env python
from __future__ import annotations

from functools import cached_property
from typing import Any, Iterator, List, Optional, Sequence, Tuple

import numpy as np
from attrs import astuple, define, evolve, field
from numpy.typing import NDArray

import pooltool.constants as c
import pooltool.math as math
from pooltool.serialize import SerializeFormat, conversion
from pooltool.utils.dataclasses import are_dataclasses_equal


@define(frozen=True)
class BallOrientation:
    """Stores a ball's rendered orientation"""

    pos: Tuple[float, ...]
    sphere: Tuple[float, ...]

    @staticmethod
    def random() -> BallOrientation:
        quat = (tmp := 2 * np.random.rand(4) - 1) / math.norm3d(tmp)
        q0, qx, qy, qz = quat
        return BallOrientation(
            pos=(1.0, 1.0, 1.0, 1.0),
            sphere=(q0, qx, qy, qz),
        )

    def copy(self) -> BallOrientation:
        """Create a deepish copy

        Class is frozen and attributes are immutable. Just return self
        """
        return self


@define(frozen=True, slots=False)
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

    @cached_property
    def u_sp(self) -> float:
        """Coefficient of spinning friction (radius dependent)"""
        return self.u_sp_proportionality * self.R

    def copy(self) -> BallParams:
        """Return deepish copy

        Class is frozen and attributes are immutable. Just return self
        """
        return self

    @staticmethod
    def default() -> BallParams:
        return BallParams()


def _null_rvw() -> NDArray[np.float64]:
    return np.array([[np.nan, np.nan, np.nan], [0, 0, 0], [0, 0, 0]], dtype=np.float64)


@define(eq=False)
class BallState:
    rvw: NDArray[np.float64]
    s: int = field(converter=int)
    t: float = field(converter=float)

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)

    def copy(self) -> BallState:
        """Create a deep copy"""
        # 3X faster than copy.deepcopy(self)
        # 1.5X faster than evolve(self, rvw=np.copy(self.rvw))
        return BallState(
            rvw=self.rvw.copy(),
            s=self.s,
            t=self.t,
        )

    @staticmethod
    def default() -> BallState:
        return BallState(
            rvw=_null_rvw(),
            s=c.stationary,
            t=0.0,
        )


def _float64_array(x: Any) -> NDArray[np.float64]:
    return np.array(x, dtype=np.float64)


@define
class BallHistory:
    states: List[BallState] = field(factory=list)

    def __getitem__(self, idx: int) -> BallState:
        return self.states[idx]

    def __len__(self) -> int:
        return len(self.states)

    def __iter__(self) -> Iterator[BallState]:
        for state in self.states:
            yield state

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

    def vectorize(self) -> Optional[Tuple[NDArray, NDArray, NDArray]]:
        """Return rvw, s, and t as arrays"""
        if self.empty:
            return None

        return tuple(  # type: ignore
            map(_float64_array, zip(*[astuple(x) for x in self.states]))
        )

    @staticmethod
    def from_vectorization(
        vectorization: Optional[Tuple[NDArray, NDArray, NDArray]]
    ) -> BallHistory:
        history = BallHistory()

        if vectorization is None:
            return history

        for args in zip(*vectorization):
            history.add(BallState(*args))

        return history

    @staticmethod
    def factory() -> BallHistory:
        return BallHistory()


conversion.register_unstructure_hook(
    BallHistory, lambda v: v.vectorize(), which=(SerializeFormat.MSGPACK,)
)
conversion.register_structure_hook(
    BallHistory,
    lambda v, t: BallHistory.from_vectorization(v),
    which=(SerializeFormat.MSGPACK,),
)


@define
class Ball:
    """A pool ball"""

    id: str
    state: BallState = field(factory=BallState.default)
    params: BallParams = field(factory=BallParams.default)
    initial_orientation: BallOrientation = field(factory=BallOrientation.random)

    history: BallHistory = field(factory=BallHistory.factory)
    history_cts: BallHistory = field(factory=BallHistory.factory)

    @property
    def xyz(self):
        """Return the coordinate vector of the ball"""
        return self.state.rvw[0]

    def copy(self, drop_history: bool = False) -> Ball:
        """Create a deep copy"""
        if drop_history:
            return evolve(
                self,
                state=self.state.copy(),
                history=BallHistory(),
                history_cts=BallHistory(),
            )

        # `params` and `initial_orientation` are frozen
        # This is the same speed as as Ball(...)
        return evolve(
            self,
            state=self.state.copy(),
            history=self.history.copy(),
            history_cts=self.history_cts.copy(),
        )

    @staticmethod
    def create(id: str, *, xy: Optional[Sequence[float]] = None, **kwargs) -> Ball:
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
