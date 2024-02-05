"""Module that holds :class:`Ball` and all of its constituents"""

from __future__ import annotations

from typing import Iterator, List, Optional, Sequence, Tuple

import numpy as np
from attrs import define, evolve, field, validate
from numpy.typing import NDArray

import pooltool.constants as c
import pooltool.ptmath as ptmath
from pooltool.objects.ball.params import BallParams
from pooltool.objects.ball.sets import BallSet
from pooltool.serialize import SerializeFormat, conversion
from pooltool.utils.dataclasses import are_dataclasses_equal


@define(frozen=True)
class BallOrientation:
    """Stores a ball's rendered BallOrientation

    From a **practical standpoint**, what needs to be understood about this class is
    that its attributes uniquely specify a ball's rendered orientation. Less
    practically, but more specifically, these attributes correspond to the nodes, 'pos'
    and 'sphere', that make up a ball's visual rendering.
    """

    pos: Tuple[float, float, float, float]
    """A quaternion"""
    sphere: Tuple[float, float, float, float]
    """Another quaternion"""

    @staticmethod
    def random() -> BallOrientation:
        """Generate a random BallOrientation

        This generates a ball orientation from a uniform sampling of possible
        orientations.

        Returns:
            BallOrientation: A randomized ball orientation.
        """
        quat = (tmp := 2 * np.random.rand(4) - 1) / ptmath.norm3d(tmp)
        q0, qx, qy, qz = quat
        return BallOrientation(
            pos=(1.0, 1.0, 1.0, 1.0),
            sphere=(q0, qx, qy, qz),
        )

    def copy(self) -> BallOrientation:
        """Create a copy

        Returns:
            BallOrientation: A copy of the ball orientation.

        Note:
            - Since the class is frozen and its attributes are immutate, this just
              returns ``self``.
        """
        return self


def _null_rvw() -> NDArray[np.float64]:
    return np.array([[np.nan, np.nan, np.nan], [0, 0, 0], [0, 0, 0]], dtype=np.float64)


@define(eq=False)
class BallState:
    """Holds a ball's state

    The ball's *state* is defined by the following:

    - The *kinematic* state of the ball (see :attr:`rvw`)
    - A label specifying the ball's *motion state* (see :attr:`s`)
    - The point in time that the ball exists in (see :attr:`t`)
    """

    rvw: NDArray[np.float64]
    """The kinematic state of the ball

    ``rvw`` is a :math:`3\\times3` matrix that stores the 3 vectors that characterize a
    ball's kinematic state:

    (1) :math:`r`: The displacement (from origin) vector (accessed with ``rvw[0]``)
    (2) :math:`v`: The velocity vector (accessed with ``rvw[1]``)
    (3) :math:`w`: The angular velocity vector (accessed with ``rvw[2]``)
    """
    s: int = field(converter=int)
    """The motion state label of the ball

    ``s`` is an integer corresponding to the following motion state labels:

    ::

        0 = stationary
        1 = spinning
        2 = sliding
        3 = rolling
        4 = pocketed
    """
    t: float = field(converter=float, default=0)
    """The simulated time"""

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)

    def copy(self) -> BallState:
        """Create a copy

        Returns:
            BallState: A copy of the ball state.
        """
        # 3X faster than copy.deepcopy(self)
        # 1.5X faster than evolve(self, rvw=np.copy(self.rvw))
        return BallState(
            rvw=self.rvw.copy(),
            s=self.s,
            t=self.t,
        )

    @staticmethod
    def default() -> BallState:
        """Construct a default BallState

        Returns:
            BallState:
                A valid yet undercooked state.

                    >>> import pooltool as pt
                    >>> pt.BallState.default()
                    BallState(rvw=array([[nan, nan, nan],
                           [ 0.,  0.,  0.],
                           [ 0.,  0.,  0.]]), s=0, t=0.0)
        """
        return BallState(
            rvw=_null_rvw(),
            s=c.stationary,
            t=0.0,
        )


F64Array = NDArray[np.float64]


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
        """Append a state to self.states

        Note, state is not copied before appending to the history, so they share the
        same memory address.
        """
        if not self.empty:
            assert state.t >= self.states[-1].t

        self.states.append(state)

    def copy(self) -> BallHistory:
        """Create a deep copy"""
        history = BallHistory()
        for state in self.states:
            history.add(state.copy())

        return history

    def vectorize(self) -> Optional[Tuple[F64Array, F64Array, F64Array]]:
        """Return rvw, s, and t as arrays"""
        if self.empty:
            return None

        num_states = len(self.states)

        rvws = np.empty((num_states, 3, 3), dtype=np.float64)
        ss = np.empty(num_states, dtype=np.float64)
        ts = np.empty(num_states, dtype=np.float64)

        for idx, state in enumerate(self.states):
            rvws[idx] = state.rvw
            ss[idx] = state.s
            ts[idx] = state.t

        return rvws, ss, ts

    @staticmethod
    def from_vectorization(
        vectorization: Optional[Tuple[F64Array, F64Array, F64Array]]
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
    lambda v, _: BallHistory.from_vectorization(v),
    which=(SerializeFormat.MSGPACK,),
)


@define
class Ball:
    """A pool ball"""

    id: str
    state: BallState = field(factory=BallState.default)
    params: BallParams = field(factory=BallParams.default)

    ballset: Optional[BallSet] = field(default=None)
    initial_orientation: BallOrientation = field(factory=BallOrientation.random)

    history: BallHistory = field(factory=BallHistory.factory)
    history_cts: BallHistory = field(factory=BallHistory.factory)

    @property
    def xyz(self):
        """Return the coordinate vector of the ball"""
        return self.state.rvw[0]

    def set_ballset(self, ballset: BallSet) -> None:
        """Update the BallSet

        Raises:
            ValueError if any balls' IDs don't correspond to a model name
        """
        self.ballset = ballset
        validate(self)

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
    def create(
        id: str,
        *,
        xy: Optional[Sequence[float]] = None,
        ballset: Optional[BallSet] = None,
        **kwargs,
    ) -> Ball:
        """Create ball using a flattened parameter set

        Args:
            xy:
                The x and y coordinates of the ball position.
            **kwargs:
                Parameters accepted by BallParams
        """
        params = BallParams(**kwargs)
        ball = Ball(id=id, ballset=ballset, params=params)

        if xy is not None:
            ball.state.rvw[0] = [*xy, ball.params.R]

        return ball

    @staticmethod
    def dummy(id: str = "dummy") -> Ball:
        return Ball(id=id)
