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

    Attributes:
        pos:
            A quaternion.
        sphere:
            Another quaternion.
    """

    pos: Tuple[float, float, float, float]
    sphere: Tuple[float, float, float, float]

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

        Note:
            - Since the class is frozen and its attributes are immutable, this just
              returns ``self``.
        """
        return self


def _null_rvw() -> NDArray[np.float64]:
    return np.array([[np.nan, np.nan, np.nan], [0, 0, 0], [0, 0, 0]], dtype=np.float64)


@define(eq=False)
class BallState:
    """Holds a ball's state

    The ball's *state* is defined **(1)** the *kinematic* state of the ball, **(2)** a
    label specifying the ball's *motion state*, and **(3)** the point in time that the
    ball exists in.

    Attributes:
        rvw:
            The kinematic state of the ball.

            ``rvw`` is a :math:`3\\times3` matrix that stores the 3 vectors that characterize a
            ball's kinematic state:

            (1) :math:`r`: The displacement (from origin) vector (accessed with ``rvw[0]``)
            (2) :math:`v`: The velocity vector (accessed with ``rvw[1]``)
            (3) :math:`w`: The angular velocity vector (accessed with ``rvw[2]``)
        s (int):
            The motion state label of the ball.

            ``s`` is an integer corresponding to the following motion state labels:

            ::

                0 = stationary
                1 = spinning
                2 = sliding
                3 = rolling
                4 = pocketed
        t (float):
            The simulated time.
    """

    rvw: NDArray[np.float64]
    s: int = field(converter=int)
    t: float = field(converter=float, default=0)

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)

    def copy(self) -> BallState:
        """Create a copy"""
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
                    >>> pt.objects.BallState.default()
                    BallState(rvw=array([[nan, nan, nan],
                           [ 0.,  0.,  0.],
                           [ 0.,  0.,  0.]]), s=0, t=0.0)
        """
        return BallState(
            rvw=_null_rvw(),
            s=c.stationary,
            t=0.0,
        )


@define
class BallHistory:
    """A container of BallState objects

    Attributes:
        states:
            A list of time-increasing BallState objects (*default* = ``[]``).
    """

    states: List[BallState] = field(factory=list)
    """A list of time-increasing BallState objects (*default* = ``[]``)"""

    def __getitem__(self, idx: int) -> BallState:
        return self.states[idx]

    def __len__(self) -> int:
        return len(self.states)

    def __iter__(self) -> Iterator[BallState]:
        for state in self.states:
            yield state

    @property
    def empty(self) -> bool:
        """Returns whether or not the ball history is empty

        Returns:
            bool: True if :attr:`states` has no length else False
        """
        return not bool(len(self.states))

    def add(self, state: BallState) -> None:
        """Append a state to the history

        Raises:
            AssertionError: If ``state.t < self.states[-1]``

        Notes:
            - This appends ``state`` to :attr:`states`
            - ``state`` is not copied before appending to the history, so they
              share the same memory address.
        """
        if not self.empty:
            assert state.t >= self.states[-1].t

        self.states.append(state)

    def copy(self) -> BallHistory:
        """Create a copy"""
        history = BallHistory()
        for state in self.states:
            history.add(state.copy())

        return history

    def vectorize(
        self,
    ) -> Optional[Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]]:
        """Compile the attribute from each ball state into arrays

        This method unzips each :class:`BallState` in :attr:`states`, resulting in an
        array of :attr:`BallState.rvw` values, an array of :attr:`BallState.s` values,
        and an array of :attr:`BallState.t` values.

        The vectors have the following properties:

        >>> import pooltool as pt
        >>> history = pt.simulate(pt.System.example(), continuous=True).balls["cue"].history_cts
        >>> rvws, ss, ts = history.vectorize()
        >>> # Their lengths are equal to the BallHistory
        >>> len(rvws) == len(ss) == len(ts) == len(history)
        True
        >>> # The indices of the arrays match the values of the history
        >>> pt.objects.BallState(rvws[26], ss[26], ts[26]) == history[26]
        True

        Returns:
            A length 3 tuple (``rvws``, ``ss`` and ``ts``). Returns None if ``self`` has
            no length.

        Example:

            ``vectorize`` can be useful for plotting trajectories.

            .. code:: python

                import pooltool as pt
                import matplotlib.pyplot as plt

                system = pt.System.example()
                pt.simulate(system, continuous=True, inplace=True)

                for ball in system.balls.values():
                    rvw, ss, ts = ball.history_cts.vectorize()
                    plt.plot(rvw[:, 0, 0], rvw[:, 0, 1], color=ss)

                plt.show()

        See Also:
            - :meth:`from_vectorization`
        """
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
        vectorization: Optional[
            Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]
        ],
    ) -> BallHistory:
        """Zips a vectorization into a BallHistory

        An inverse method of :meth:`vectorize`.

        Returns:
            BallHistory: A BallHistory constructed from the input vectors.

        Example:

            This illustrates a round-trip with :meth:`vectorize` and
            :meth:`from_vectorization`.

            First create history

            >>> import pooltool as pt
            >>> history = pt.simulate(pt.System.example(), continuous=True).balls["cue"].history_cts

            Illustrate a lossless round trip:

            >>> pt.objects.BallHistory.from_vectorization(history.vectorize()) == history
            True

        See Also:
            - :meth:`vectorize`
        """
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
    """A billiards ball

    This class represents a billiards ball. It stores its parameters (mass, radius,
    etc.), it's state (coordinates, velocity, spin, etc), its history (a time-resolved
    trajectory of its state), amongst other things.

    Attributes:
        id:
            An ID for the ball.

            Use strings (e.g. "1" not 1).
        state:
            The ball's state.

            This is the current state of the ball.

            See Also:
                - See the *Important* section in :class:`Ball` for a description of the
                  role of ``states`` during simulation.
        params:
            The ball's physical parameters.

            The physical parameters of the ball.
        ballset:
            The ball set that the ball belongs to.

            Important if rendering the ball in a scene.

            See Also:
                - See :meth:`Ball.set_ballset` for details
        initial_orientation:
            The initial rendered orientation of the ball.

            Important if rendering the ball in a scene.

            This is the orientation of the ball at :math:`t = 0`.
        history:
            The ball's state history

            The historical states of the ball from :math:`t_{initial}` to
            :math:`t_{final}`.

            See Also:
                - See the *Important* section in :class:`Ball` for a description of the
                  role of ``history`` during simulation.
        history_cts:
            The ball's continuous state history

            The historical states of the ball from :math:`t_{initial}` to
            :math:`t_{final}` densely sampled with respect to time.

            See Also:
                - See :func:`pooltool.evolution.continuize.continuize` for a
                  details about continuizing a simulated system.
                - See the *Important* section in :class:`Ball` for a description of the
                  role of ``history_cts`` during simulation.

    Important:
        To instantiate this class, consider using the :meth:`create` constructor. Or,
        use functions within :mod:`pooltool.layouts` to generate entire collection
        of balls. Or, of course, construct as normal with ``__init__``.

    Important:
        The following explains how a ``Ball`` object is modified when its parent system
        is simulated (:func:`pooltool.evolution.event_based.simulate.simulate`).

        At the start of the simulation process, :attr:`state` represents the ball state
        at :math:`t = 0`. A copy of :attr:`state` is appended to :attr:`history`.

        For each timestep of the simulation, :attr:`state` is used to inform how the
        system should advance forward in time. Once determined, :attr:`state` is updated
        to reflect the ball's new state. A copy of :attr:`state` is appended to
        :attr:`history`.

        When the simulation is finished, :attr:`state` represents the final resting
        state of the ball. So too does ``history[-1]``.

        Finally, if the system is continuized (see
        :func:`pooltool.evolution.continuize.continuize`), :attr:`history_cts` is
        populated. Otherwise it remains empty.
    """

    id: str
    state: BallState = field(factory=BallState.default)
    params: BallParams = field(factory=BallParams.default)
    ballset: Optional[BallSet] = field(default=None)
    initial_orientation: BallOrientation = field(factory=BallOrientation.random)
    history: BallHistory = field(factory=BallHistory.factory)
    history_cts: BallHistory = field(factory=BallHistory.factory)

    @property
    def xyz(self):
        """The displacement (from origin) vector of the ball.

        A shortcut for ``self.state.rvw[0]``.
        """
        return self.state.rvw[0]

    @property
    def vel(self):
        """The velocity vector of the ball.

        A shortcut for ``self.state.rvw[1]``.
        """
        return self.state.rvw[1]

    @property
    def avel(self):
        """The angular velocity vector of the ball.

        A shortcut for ``self.state.rvw[2]``.
        """
        return self.state.rvw[2]

    def set_ballset(self, ballset: BallSet) -> None:
        """Update the ballset

        Raises:
            ValueError:
                If the ball ID doesn't match to a model name of the ballset.

        See Also:
            - See :mod:`pooltool.objects.ball.sets` for details about ball sets.
            - See :meth:`pooltool.system.datatypes.System.set_ballset` for setting the
              ballset for all the balls in a system.
        """
        self.ballset = ballset
        validate(self)

    def copy(self, drop_history: bool = False) -> Ball:
        """Create a copy

        Args:
            drop_history:
                If True, the returned copy :attr:`history` and :attr:`history_cts`
                attributes are both set to empty :class:`BallHistory` objects.
        """
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
        """Create a ball using keyword arguments.

        This constructor flattens the tunable parameter space, allowing one to construct
        a ``Ball`` without directly instancing objects like like
        :class:`pooltool.objects.balls.params.BallParams` and :class:`BallState`.

        Args:
            xy:
                The x and y coordinates of the ball position.
            ballset:
                A ballset.
            **kwargs:
                Arguments accepted by :class:`pooltool.objects.balls.params.BallParams`
        """
        params = BallParams(**kwargs)
        ball = Ball(id=id, ballset=ballset, params=params)

        if xy is not None:
            ball.state.rvw[0] = [*xy, ball.params.R]

        return ball

    @staticmethod
    def dummy(id: str = "dummy") -> Ball:
        return Ball(id=id)
