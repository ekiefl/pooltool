#! /usr/bin/env python

from __future__ import annotations

from typing import Dict, Iterator, List, Optional

import numpy as np
from attrs import define, field

import pooltool.math as math
import pooltool.physics.utils as physics_utils
from pooltool.error import ConfigError
from pooltool.events import Event
from pooltool.objects.ball.datatypes import Ball, BallHistory
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.potting import PottingConfig
from pooltool.serialize import conversion
from pooltool.serialize.serializers import Pathish

Balls = Dict[str, Ball]


@define
class System:
    cue: Cue
    table: Table
    balls: Balls

    t: float = field(default=0)
    events: List[Event] = field(factory=list)

    @property
    def continuized(self):
        return all(not ball.history_cts.empty for ball in self.balls.values())

    @property
    def simulated(self):
        return bool(len(self.events))

    def set_meta(self, meta):
        """Define any meta data for the shot"""
        raise NotImplementedError()

    def update_history(self, event: Event):
        """Updates the history for all balls"""
        self.t = event.time

        for ball in self.balls.values():
            ball.state.t = event.time
            ball.history.add(ball.state)

        self.events.append(event)

    def reset_history(self):
        """Remove all events, histories, and reset time"""

        self.t = 0

        for ball in self.balls.values():
            ball.history = BallHistory()
            ball.history_cts = BallHistory()
            ball.state.t = 0

        self.events = []

    def reset_balls(self):
        """Reset balls to their initial states"""
        for ball in self.balls.values():
            if not ball.history.empty:
                ball.state = ball.history[0].copy()

    def aim_at_pos(self, pos):
        """Set phi to aim at a 3D position

        Parameters
        ==========
        pos : array-like
            A length-3 iterable specifying the x, y, z coordinates of the position to be
            aimed at
        """

        assert self.cue.cue_ball_id in self.balls

        cueing_ball = self.balls[self.cue.cue_ball_id]

        direction = math.angle(
            math.unit_vector(np.array(pos) - cueing_ball.state.rvw[0])
        )
        self.cue.set_state(phi=direction * 180 / np.pi)

    def aim_at_ball(self, ball_id: str, cut: Optional[float] = None):
        """Set phi to aim directly at a ball

        Parameters
        ==========
        ball : pooltool.objects.ball.Ball
            A ball
        cut : float, None
            The cut angle in degrees, within [-89, 89]
        """

        assert self.cue.cue_ball_id in self.balls

        cueing_ball = self.balls[self.cue.cue_ball_id]
        object_ball = self.balls[ball_id]

        self.aim_at_pos(object_ball.state.rvw[0])

        if cut is None:
            return

        assert -89 < cut < 89, "Cut must be less than 89 and more than -89"

        # Ok a cut angle has been requested. Unfortunately, there exists no analytical
        # function phi(cut), at least as far as I have been able to calculate. Instead,
        # it is a nasty transcendental equation that must be solved. The gaol is to make
        # its value 0. To do this, I sweep from 0 to the max possible angle with 100
        # values and find where the equation flips from positive to negative. The dphi
        # that makes the equation lies somewhere between those two values, so then I do
        # a new parameter sweep between the value that was positive and the value that
        # was negative. Then I rinse and repeat this a total of 5 times.

        left = True if cut < 0 else False
        cut = np.abs(cut) * np.pi / 180
        R = object_ball.params.R
        d = math.norm3d(object_ball.state.rvw[0] - cueing_ball.state.rvw[0])

        lower_bound = 0
        upper_bound = np.pi / 2 - np.arccos((2 * R) / d)

        for _ in range(5):
            dphis = np.linspace(lower_bound, upper_bound, 100)
            transcendental = (
                np.arctan(
                    2 * R * np.sin(cut - dphis) / (d - 2 * R * np.cos(cut - dphis))
                )
                - dphis
            )
            for i in range(len(transcendental)):
                if transcendental[i] < 0:
                    lower_bound = dphis[i - 1] if i > 0 else 0
                    upper_bound = dphis[i]
                    dphi = dphis[i]
                    break
            else:
                raise ConfigError(
                    "System.aim_at_ball :: Wow this should never happen. The algorithm "
                    "that finds the cut angle needs to be looked at again, because "
                    "the transcendental equation could not be solved."
                )

        self.cue.phi = (self.cue.phi + 180 / np.pi * (dphi if left else -dphi)) % 360

    def aim_for_pocket(
        self,
        ball_id: str,
        pocket_id: str,
        config: PottingConfig = PottingConfig.default(),
    ):
        """Set phi to pot a given ball into a given pocket"""
        assert self.cue.cue_ball_id in self.balls

        self.cue.set_state(
            phi=config.calculate_angle(
                self.balls[self.cue.cue_ball_id],
                self.balls[ball_id],
                self.table.pockets[pocket_id],
            )
        )

    def aim_for_best_pocket(
        self, ball_id: str, config: PottingConfig = PottingConfig.default()
    ):
        """Set phi to pot a given ball into the best/easiest pocket"""
        assert self.cue.cue_ball_id in self.balls

        cue_ball = self.balls[self.cue.cue_ball_id]
        object_ball = self.balls[ball_id]
        pockets = list(self.table.pockets.values())

        self.aim_for_pocket(
            ball_id=ball_id,
            pocket_id=config.choose_pocket(cue_ball, object_ball, pockets).id,
            config=config,
        )

    def strike(self, **state_kwargs) -> None:
        """Set cue stick parameters

        Just a wrapper for self.cue.set_state

        state_kwargs: **kwargs
            Pass state parameters to be updated for the cue strike. Any parameters
            accepted by Cue.set_state are permissible.
        """
        self.cue.set_state(**state_kwargs)
        assert self.cue.cue_ball_id in self.balls

    def get_system_energy(self):
        energy = 0
        for ball in self.balls.values():
            energy += physics_utils.get_ball_energy(
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
            True if all balls are non-overlapping. Returns False otherwise.
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

    def is_balls_overlapping(self):
        for ball1 in self.balls.values():
            for ball2 in self.balls.values():
                if ball1 is ball2:
                    continue

                assert (
                    ball1.params.R == ball2.params.R
                ), "Balls are assumed to be equal radii"

                if physics_utils.is_overlapping(
                    ball1.state.rvw, ball2.state.rvw, ball1.params.R, ball2.params.R
                ):
                    return True

        return False

    def copy(self) -> System:
        """Make deepcopy of the system"""
        return System(
            cue=self.cue.copy(),
            table=self.table.copy(),
            balls={k: v.copy() for k, v in self.balls.items()},
            t=self.t,
            events=[event.copy() for event in self.events],
        )

    def save(self, path: Pathish, drop_continuized_history: bool = False):
        """Save a System in a serialized format (e.g. json, msgpack)

        Args:
            drop_continuized_history:
                If True, the `history_cts` attribute is not saved, which can save a lot
                of disk space. If deserializing at a later time, these `history_cts`
                attributes can be regenerated with a `shot.continuize()` call.
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
        return conversion.structure_from(path, cls)

    @classmethod
    def example(cls) -> System:
        system = cls(
            cue=Cue.default(),
            table=(table := Table.default()),
            balls={
                "cue": Ball.create("cue", xy=(table.w / 2, table.l / 2)),
                "1": Ball.create("1", xy=(table.w / 2, 3 / 4 * table.l)),
            },
        )
        system.aim_for_best_pocket("1")
        system.cue.set_state(V0=1.5, b=-0.3)
        return system


@define
class MultiSystem:
    multisystem: List[System] = field(factory=list)

    active_index: Optional[int] = field(default=None)

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
        if self.empty:
            self.active_index = 0

        self.multisystem.append(system)

    def extend(self, systems: List[System]) -> None:
        if self.empty:
            self.active_index = 0

        self.multisystem.extend(systems)

    def set_active(self, i) -> None:
        """Change the active system in the collection

        Parameters
        ==========
        i : int
            The integer index of the shot you would like to make active. Negative
            indexing is supported, e.g. set_active(-1) sets the last system in the
            collection as active
        """
        if self.active_index is not None:
            table = self.active.table
            self.active_index = i
            self.active.table = table
        else:
            self.active_index = i

        if i < 0:
            i = len(self) - 1

        self.active_index = i

    def save(self, path: Pathish):
        """Save a MultiSystem in a serialized format (e.g. json, msgpack)"""
        conversion.unstructure_to(self, path)

    @classmethod
    def load(cls, path: Pathish) -> MultiSystem:
        return conversion.structure_from(path, cls)


multisystem = MultiSystem()
