#! /usr/bin/env python

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

import numpy as np
from attrs import define, field

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.events import Event
from pooltool.objects.ball.datatypes import Ball, BallHistory
from pooltool.objects.ball.sets import BallSet
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.serialize import conversion
from pooltool.serialize.serializers import Pathish


def _convert_balls(balls: Any) -> Dict[str, Ball]:
    if isinstance(balls, dict):
        return balls

    return {ball.id: ball for ball in balls}


@define
class System:
    """A class representing the billiards system.

    This class holds:

    (1) a collection of balls (:class:`pooltool.objects.ball.datatypes.Ball`)
    (2) a cue stick (:class:`pooltool.objects.cue.datatypes.Cue`)
    (3) a table (:class:`pooltool.objects.table.datatypes.Table`)

    Together, these objects, referred to as the `system`, fully describe the billiards
    system.

    This object is a mutable object that can be evolved over the course of system's
    evolution. When a billiards system is simulated, a list of
    :class:`pooltool.events.datatypes.Event` objects is stored in this class.

    This class also stores the duration of simulated time elapsed as ``t``, measured in
    seconds.

    Attributes:
        cue:
            A cue stick.
        table:
            A table.
        balls:
            A dictionary of balls.

            Warning:
                Each key must match each value's ``id`` (`e.g.` ``{"2": Ball(id="1")}``
                is invalid).

            Note:
                If, during construction, a sequence (`e.g.` list, tuple, etc.) of balls
                is passed instead of a dictionary, it will be converted to a dictionary.
        t:
            The elapsed simulation time. If the system is in the process of being
            simulated, ``t`` is updated to be the number of seconds the system has
            evolved. After being simulated, ``t`` remains at the final simulation time.
        events:
            The sequence of events in the simulation. Like ``t``, this is updated
            incrementally as the system is evolved. (*default* = ``[]``)

    Examples:

        Constructing a system requires a cue, a table, and a dictionary of balls:

        >>> import pooltool as pt
        >>> pt.System(
        >>>     cue=pt.Cue.default(),
        >>>     table=pt.Table.default(),
        >>>     balls={"1": pt.Ball.create("1", xy=(0.2, 0.3))},
        >>> )

        If you need a quick system to experiment with, call :meth:`example`:

        >>> import pooltool as pt
        >>> system = pt.System.example()

        You can simulate this system and introspect its attributes:

        >>> pt.simulate(system, inplace=True)
        >>> system.simulated
        True
        >>> len(system.events)
        14
        >>> system.cue
        <Cue object at 0x7fb838080190>
         ├── V0    : 1.5
         ├── phi   : 95.07668213305062
         ├── a     : 0.0
         ├── b     : -0.3
         └── theta : 0.0

        This ``system`` can also be visualized in the GUI:

        >>> pt.show(system)
    """

    cue: Cue = field()
    table: Table = field()
    balls: Dict[str, Ball] = field(converter=_convert_balls)
    t: float = field(default=0.0)
    events: List[Event] = field(factory=list)

    @balls.validator  # type: ignore
    def _validate_balls(self, _, value) -> None:
        first_ball_m = None
        first_ball_R = None

        for key, ball in value.items():
            assert key == ball.id, f"Key {key} does not match ball's id {ball.id}"

            # This safeguards against a current limitation in pooltool, namely, that
            # balls must have equal masses and radii. Equal mass is due to the current
            # ball-ball resolver, and equal radius is due to the current ball-ball
            # resolver as well as the quartic solver used for ball-ball collision
            # detection
            if first_ball_m is None and first_ball_R is None:
                first_ball_m = ball.params.m
                first_ball_R = ball.params.R
            else:
                assert (
                    ball.params.m == first_ball_m
                ), f"Ball with id {ball.id} has a different mass"
                assert (
                    ball.params.R == first_ball_R
                ), f"Ball with id {ball.id} has a different radius"

    @property
    def continuized(self):
        """Checks if all balls have a non-empty continuous history.

        Returns:
            bool: True if all balls have a non-empty continuous history, False otherwise.

        See Also:
            For a proper definition of *continuous history*, please see
            :attr:`pooltool.objects.ball.datatypes.Ball.history_cts`.
        """
        return all(not ball.history_cts.empty for ball in self.balls.values())

    @property
    def simulated(self):
        """Checks if the simulation has any events.

        If there are events, it is assumed that the system has been simulated.

        Returns:
            bool: True if there are events, False otherwise.
        """
        return bool(len(self.events))

    def set_ballset(self, ballset: BallSet) -> None:
        """Sets the ballset for each ball in the system.

        Important only if rendering the system in a scene and you are manually creating
        balls (rather than relying on built-in utilities in
        :mod:`pooltool.layouts`)

        In this case, you need to manually associate a
        :class:`pooltool.objects.ball.sets.BallSet` to the balls in the system, so that
        the proper `model skin` can be applied to each. That's what this method does.

        Args:
            ballset: The ballset to be assigned to each ball.

        Raises:
            ValueError:
                If any ball's ID does not correspond to a model name associated with the
                ball set.

        See Also:
            - See :mod:`pooltool.objects.ball.sets` for details about ball sets.
            - See :meth:`pooltool.objects.ball.datatypes.Ball.set_ballset` for setting
              the ballset of an individual ball.
        """
        for ball in self.balls.values():
            ball.set_ballset(ballset)

    def _update_history(self, event: Event):
        """Updates the history for all balls based on the given event.

        Args:
            event (Event): The event to update the ball histories with.
        """
        self.t = event.time

        for ball in self.balls.values():
            ball.state.t = event.time
            ball.history.add(ball.state)

        self.events.append(event)

    def reset_history(self):
        """Resets the history for all balls, clearing events and resetting time.

        Operations that this method performs:

        (1) :attr:`t` is set to ``0.0``
        (2) :attr:`events` is set to ``[]``

        Additionally for each ball in ``self.balls``,

        (1) :attr:`pooltool.objects.ball.datatypes.Ball.history` is set to
        ``BallHistory()``
        (2) :attr:`pooltool.objects.ball.datatypes.Ball.history_cts` is set to
        ``BallHistory()``
        (3) The ``t`` attribute of :attr:`pooltool.objects.ball.datatypes.Ball.state`
        is set to ``0.0``

        Calling this method thus erases any history.
        """

        self.t = 0.0

        for ball in self.balls.values():
            ball.history = BallHistory()
            ball.history_cts = BallHistory()
            ball.state.t = 0.0

        self.events = []

    def reset_balls(self):
        """Resets balls to their initial states based on their history

        This sets the state of each ball to the ball's initial historical state (`i.e.`
        before evolving the system). It doesn't erase the history.

        Example:
            This example shows that calling this method resets the ball's states to
            before the system is simulated.

            First, create a system and store the cue ball's state

            >>> import pooltool as pt
            >>> system = pt.System.example()
            >>> cue_ball_initial_state = system.balls["cue"].state.copy()
            >>> cue_ball_initial_state
            BallState(rvw=array([[0.4953  , 0.9906  , 0.028575],
                   [0.      , 0.      , 0.      ],
                   [0.      , 0.      , 0.      ]]), s=0, t=0.0)

            Now simulate the system and assert that the cue ball's new state has changed:

            >>> pt.simulate(system, inplace=True)
            >>> assert system.balls["cue"].state != cue_ball_initial_state

            But after resetting the balls, the cue ball state once again matches the
            state before simulation.

            >>> system.reset_balls()
            >>> assert system.balls["cue"].state == cue_ball_initial_state

            The system history is not erased:

            >>> system.simulated
            True
            >>> len(system.events)
            14
            >>> system.t
            5.193035203405666
        """
        for ball in self.balls.values():
            if not ball.history.empty:
                ball.state = ball.history[0].copy()

    def stop_balls(self):
        """Change ball states to stationary and remove all momentum

        This method removes all kinetic energy from the system by:

        (1) Setting the velocity and angular velocity vectors of each ball to <0, 0, 0>
        (2) Setting the balls' motion states to stationary (`i.e.` 0)
        """
        for ball in self.balls.values():
            ball.state.s = const.stationary
            ball.state.rvw[1] = np.array([0.0, 0.0, 0.0], np.float64)
            ball.state.rvw[2] = np.array([0.0, 0.0, 0.0], np.float64)

    def strike(self, **kwargs) -> None:
        """Set cue stick parameters

        This is merely an alias for :meth:`pooltool.objects.cue.datatypes.Cue.set_state`

        Args:
            kwargs: **kwargs
                Cue stick parameters.

        See Also:
            :meth:`pooltool.objects.cue.datatypes.Cue.set_state`
        """
        self.cue.set_state(**kwargs)
        assert self.cue.cue_ball_id in self.balls

    def get_system_energy(self) -> float:
        """Calculate the energy of the system in Joules"""
        energy = 0
        for ball in self.balls.values():
            energy += ptmath.get_ball_energy(
                ball.state.rvw, ball.params.R, ball.params.m
            )

        return energy

    def randomize_positions(
        self, ball_ids: Optional[List[str]] = None, niter=100
    ) -> bool:
        """Randomize ball positions on the table--ensure no overlap

        This "algorithm" initializes a random state, and checks that all the balls are
        non-overlapping. If any are, a new state is initialized and the process is
        repeated. This is an inefficient algorithm, in case that needs to be said.

        Args:
            ball_ids:
                Only these balls will be randomized.
            niter:
                The number of iterations tried until the algorithm gives up.

        Returns:
            bool: True if all balls are non-overlapping. Returns False otherwise.
        """

        if ball_ids is None:
            ball_ids = list(self.balls.keys())

        for _ in range(niter):
            for ball_id in ball_ids:
                ball = self.balls[ball_id]
                R = ball.params.R
                ball.state.rvw[0] = [
                    np.random.uniform(R, self.table.w - R),
                    np.random.uniform(R, self.table.l - R),
                    R,
                ]

            if not self.is_balls_overlapping():
                return True

        return False

    def is_balls_overlapping(self) -> bool:
        """Determines if any balls are overlapping.

        Returns:
            bool: True if any balls overlap, False otherwise.
        """
        for ball1 in self.balls.values():
            for ball2 in self.balls.values():
                if ball1 is ball2:
                    continue

                assert (
                    ball1.params.R == ball2.params.R
                ), "Balls are assumed to be equal radii"

                if ptmath.is_overlapping(
                    ball1.state.rvw, ball2.state.rvw, ball1.params.R, ball2.params.R
                ):
                    return True

        return False

    def copy(self) -> System:
        """Creates a deep-`ish` copy of the system.

        This method generates a copy of the system with a level of deep copying that is
        contingent on the mutability of the objects within the system. Immutable
        objects, frozen data structures, and read-only numpy arrays
        (``array.flags["WRITEABLE"] = False``) remain shared between the original and the
        copied system.

        TLDR For all intents and purposes, mutating the system copy will not impact the
        original system, and vice versa.

        Returns:
            System: A deepcopy of the system.

        Example:
            >>> import pooltool as pt
            >>> system = pt.System.example()
            >>> system_copy = pt.System.example()
            >>> pt.simulate(system, inplace=True)
            >>> system.simulated
            True
            >>> system_copy.simulated
            False
        """
        return System(
            cue=self.cue.copy(),
            table=self.table.copy(),
            balls={k: v.copy() for k, v in self.balls.items()},
            t=self.t,
            events=[event.copy() for event in self.events],
        )

    def save(self, path: Pathish, drop_continuized_history: bool = False) -> None:
        """Save a System to file in a serialized format.

        Supported file extensions:

        (1) ``.json``
        (2) ``.msgpack``

        Args:
            path:
                Either a ``pathlib.Path`` object or a string. The extension should match the
                supported filetypes mentioned above.
            drop_continuized_history:
                If True, :attr:`pooltool.objects.ball.datatypes.Ball.history_cts` is
                wiped before the save operation, which can save a lot of disk space and
                increase save/load speed. If loading (deserializing) at a later time,
                the ``history_cts`` for each ball can be easily regenerated (see
                Examples).

        Example:

            An example of saving to, and loading from, JSON:

            >>> import pooltool as pt
            >>> system = pt.System.example()
            >>> system.save("case1.json")
            >>> loaded_system = pt.System.load("case1.json")
            >>> assert system == loaded_system

            You can also save `simulated` systems:

            >>> pt.simulate(system, inplace=True)
            >>> system.save("case2.json")

            Simulated systems contain the events of the shot, so they're larger:

                $ du -sh case1.json case2.json
                 12K	case1.json
                 68K	case2.json

        Example:

            JSON may be human readable, but MSGPACK is faster:

            >>> import pooltool as pt
            >>> system = pt.System.example()
            >>> pt.simulate(system, inplace=True)
            >>> print("saving:")
            >>> %timeit system.save("readable.json")
            >>> %timeit system.save("fast.msgpack")
            >>> print("loading:")
            >>> %timeit pt.System.load("readable.json")
            >>> %timeit pt.System.load("fast.msgpack")
            saving:
            5.4 ms ± 470 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
            725 µs ± 55.8 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
            loading:
            3.16 ms ± 38.3 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
            1.9 ms ± 15.2 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)

        Example:

            If the system has been continuized (see
            :func:`pooltool.evolution.continuize.continuize`), disk space and save/load
            times can be decreased by using ``drop_continuized_history``:

            >>> import pooltool as pt
            >>> system = pt.System.example()
            >>> # simulate and continuize the results
            >>> pt.simulate(system, continuous=True, inplace=True)
            >>> print("saving")
            >>> %timeit system.save("no_drop.json")
            >>> %timeit system.save("drop.json", drop_continuized_history=True)
            >>> print("loading")
            >>> %timeit pt.System.load("no_drop.json")
            >>> %timeit pt.System.load("drop.json")
            saving
            36 ms ± 803 µs per loop (mean ± std. dev. of 7 runs, 10 loops each)
            7.59 ms ± 342 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
            loading
            18.3 ms ± 1.15 ms per loop (mean ± std. dev. of 7 runs, 100 loops each)
            3.14 ms ± 30.3 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)

                $ du -sh drop.json no_drop.json
                 68K	drop.json
                584K	no_drop.json

            However, the loaded system is no longer continuized. If you need it to
            be, call :func:`pooltool.evolution.continuize.continuize`:

            >>> loaded_system = pt.System.load("drop.json")
            >>> assert loaded_system != system
            >>> pt.continuize(loaded_system, inplace=True)
            >>> assert loaded_system == system

        See Also:
            Load systems with :meth:`load`.
        """
        if drop_continuized_history:
            # We're dropping the continuized histories. To avoid losing them in `self`,
            # we make a copy.
            copy = self.copy()

            for ball in copy.balls.values():
                ball.history_cts = BallHistory()

            conversion.unstructure_to(copy, path)
            return

        conversion.unstructure_to(self, path)

    @classmethod
    def load(cls, path: Pathish) -> System:
        """Load a System from a file in a serialized format.

        Supported file extensions:

        (1) ``.json``
        (2) ``.msgpack``

        Args:
            path:
                Either a ``pathlib.Path`` object or a string representing the file path. The
                extension should match the supported filetypes mentioned above.

        Returns:
            System: The deserialized System object loaded from the file.

        Raises:
            AssertionError: If the file specified by `path` does not exist.
            ValueError: If the file extension is not supported.

        Examples:

        Please refer to the examples in :meth:`save`.

        See Also:
            Save systems with :meth:`save`.
        """
        return conversion.structure_from(path, cls)

    @classmethod
    def example(cls) -> System:
        """A simple example system

        This system features 2 balls (IDs "1" and "cue") on a pocket table. The cue
        stick parameters are set to pocket the "1" ball in the top-left pocket.

        Example:

            The system can be constructed and introspected like so:

            >>> import pooltool as pt
            >>> system = pt.System.example()
            >>> system.balls["cue"].xyz
            array([0.4953  , 0.9906  , 0.028575])
            >>> system.balls["1"].xyz
            array([0.4953  , 1.4859  , 0.028575])
            >>> system.cue
            <Cue object at 0x7f7a2641ce40>
             ├── V0    : 1.5
             ├── phi   : 95.07668213305062
             ├── a     : 0.0
             ├── b     : -0.3
             └── theta : 0.0

            It can be simulated and visualized:

            >>> pt.simulate(system, inplace=True)
            >>> pt.show(system)
        """
        system = cls(
            cue=Cue.default(),
            table=(table := Table.default()),
            balls={
                "cue": Ball.create("cue", xy=(table.w / 2, table.l / 2)),
                "1": Ball.create("1", xy=(table.w / 2, 3 / 4 * table.l)),
            },
        )
        system.set_ballset(BallSet("pooltool_pocket"))
        system.cue.set_state(V0=1.5, b=-0.3, a=-0.3, phi=94.0)
        return system


@define
class MultiSystem:
    """A storage for System objects

    Houses a collection of systems, for example, shots taken sequentially in
    a game.

    Attributes:
        multisystem:
            A list of System objects (`default` = ``[]``)

    Example:

        This example illustrates the basics of multisystems.

        First, make a system and evolve it.

        >>> import pooltool as pt
        >>> import numpy as np
        >>> system = pt.System.example()
        >>> system.strike(phi=90)
        >>> pt.simulate(system, inplace=True)

        Now add it to a multisystem.

        >>> multisystem = pt.MultiSystem()
        >>> multisystem.append(system)

        Now copy the system, reset it's history, strike it differently, simulate it, and
        add it to the mulisystem:

        >>> next_system = multisystem[-1].copy()
        >>> next_system.strike(phi=0)
        >>> pt.simulate(next_system, inplace=True)
        >>> multisystem.append(next_system)

        The multisystem has a length,

        >>> len(multisystem)
        2

        supports basic indexing,

        >>> multisystem[0].t
        6.017032496778012

        and can be iterated through:

        >>> for shot in multisystem: print(len(shot.events))
        15
        10

        Now visualize the multisystem:

        >>> pt.show(multisystem, title="Press 'n' for next, 'p' for previous")
    """

    multisystem: List[System] = field(factory=list)
    active_index: Optional[int] = field(default=None, init=False)

    def __len__(self) -> int:
        return len(self.multisystem)

    def __getitem__(self, idx: int) -> System:
        return self.multisystem[idx]

    def __iter__(self) -> Iterator[System]:
        for system in self.multisystem:
            yield system

    @property
    def active(self) -> System:
        assert self.active_index is not None
        return self.multisystem[self.active_index]

    @property
    def empty(self) -> bool:
        return not bool(len(self))

    @property
    def max_index(self):
        return len(self) - 1

    def reset(self) -> None:
        self.active_index = None
        self.multisystem = []

    def append(self, system: System) -> None:
        """Append a system to the multisystem

        This appends ``system`` to :attr:`multisystem`.
        """
        if self.empty:
            self.active_index = 0

        self.multisystem.append(system)

    def extend(self, systems: List[System]) -> None:
        if self.empty:
            self.active_index = 0

        self.multisystem.extend(systems)

    def set_active(self, i) -> None:
        if self.active_index is not None:
            table = self.active.table
            self.active_index = i
            self.active.table = table
        else:
            self.active_index = i

        if i < 0:
            i = len(self) - 1

        self.active_index = i

    def save(self, path: Pathish) -> None:
        """Save the multisystem to file in a serialized format.

        Supported file extensions:

        (1) ``.json``
        (2) ``.msgpack``

        Args:
            path:
                Either a ``pathlib.Path`` object or a string. The extension should match the
                supported filetypes mentioned above.

        See Also:
            - To load a multisystem, see :meth:`load`.
            - To save/load single systems, see :meth:`System.save` and :meth:`System.load`
        """
        conversion.unstructure_to(self, path)

    @classmethod
    def load(cls, path: Pathish) -> MultiSystem:
        """Load a multisystem from a file in a serialized format.

        Supported file extensions:

        (1) ``.json``
        (2) ``.msgpack``

        Args:
            path:
                Either a pathlib.Path object or a string representing the file path. The
                extension should match the supported filetypes mentioned above.

        Returns:
            MultiSystem: The deserialized MultiSystem object loaded from the file.

        See Also:
            - To save a multisystem, see :meth:`save`.
            - To save/load single systems, see :meth:`System.save` and :meth:`System.load`
        """
        return conversion.structure_from(path, cls)


multisystem = MultiSystem()
