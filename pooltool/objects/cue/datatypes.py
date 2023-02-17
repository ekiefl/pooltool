#! /usr/bin/env python

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

import pooltool.events as events
import pooltool.utils as utils
from pooltool.error import ConfigError


@dataclass(frozen=True)
class CueSpecs:
    brand: str = field(default="Predator")
    M: float = field(default=0.567)  # 20oz
    length: float = field(default=1.4732)  # 58in
    tip_radius: float = field(default=0.007)  # 14mm tip
    butt_radius: float = field(default=0.02)

    @staticmethod
    def default() -> CueSpecs:
        return CueSpecs()


@dataclass
class Cue:
    id: str = field(default="cue_stick")

    V0: float = field(default=2.0)
    phi: float = field(default=0.0)
    theta: float = field(default=0.0)
    a: float = field(default=0.0)
    b: float = field(default=0.25)
    cueing_ball: Optional[Any] = field(default=None)

    specs: CueSpecs = field(default_factory=CueSpecs.default)

    def reset_state(self):
        """Reset V0, phi, theta, a and b to their defaults"""
        field_defaults = {
            fname: field.default
            for fname, field in self.__dataclass_fields__.items()
            if fname in ("V0", "phi", "theta", "a", "b")
        }
        self.set_state(**field_defaults)

    def set_state(
        self, V0=None, phi=None, theta=None, a=None, b=None, cueing_ball=None
    ):
        """Set the cueing parameters

        Notes
        =====
        - If any parameters are None, they will be left untouched--they will not be set
          to None
        """

        if V0 is not None:
            self.V0 = V0
        if phi is not None:
            self.phi = phi
        if theta is not None:
            self.theta = theta
        if a is not None:
            self.a = a
        if b is not None:
            self.b = b
        if cueing_ball is not None:
            self.cueing_ball = cueing_ball

    def strike(self, t=None, **state_kwargs):
        """Strike the cue ball

        Parameters
        ==========
        t : float, None
            The time that the collision occurs at

        state_kwargs: **kwargs
            Pass state parameters to be updated before the cue strike. Any parameters
            accepted by Cue.set_state are permissible.
        """
        self.set_state(**state_kwargs)

        assert self.cueing_ball

        event = events.stick_ball_collision(self, self.cueing_ball, t)
        event.resolve()

        return event

    def aim_at_pos(self, pos):
        """Set phi to aim at a 3D position

        Parameters
        ==========
        pos : array-like
            A length-3 iterable specifying the x, y, z coordinates of the position to be
            aimed at
        """

        assert self.cueing_ball

        direction = utils.angle_fast(
            utils.unit_vector_fast(np.array(pos) - self.cueing_ball.state.rvw[0])
        )
        self.set_state(phi=direction * 180 / np.pi)

    def aim_at_ball(self, ball, cut=None):
        """Set phi to aim directly at a ball

        Parameters
        ==========
        ball : pooltool.objects.ball.Ball
            A ball
        cut : float, None
            The cut angle in degrees, within [-89, 89]
        """

        assert self.cueing_ball

        self.aim_at_pos(ball.state.rvw[0])

        if cut is None:
            return

        if cut > 89 or cut < -89:
            raise ConfigError(
                "Cue.aim_at_ball :: cut must be less than 89 and more than -89"
            )

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
        R = ball.params.R
        d = np.linalg.norm(ball.state.rvw[0] - self.cueing_ball.state.rvw[0])

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
                    "Cue.aim_at_ball :: Wow this should never happen. The algorithm "
                    "that finds the cut angle needs to be looked at again, because "
                    "the transcendental equation could not be solved."
                )

        self.phi = (self.phi + 180 / np.pi * (dphi if left else -dphi)) % 360

    def __repr__(self):
        lines = [
            f"<{self.__class__.__name__} object at {hex(id(self))}>",
            f" ├── V0    : {self.V0}",
            f" ├── phi   : {self.phi}",
            f" ├── a     : {self.a}",
            f" ├── b     : {self.b}",
            f" └── theta : {self.theta}",
        ]

        return "\n".join(lines) + "\n"
