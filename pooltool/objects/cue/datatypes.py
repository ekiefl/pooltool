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
    ball_id: Optional[str] = field(default=None)

    specs: CueSpecs = field(default_factory=CueSpecs.default)

    def reset_state(self):
        """Reset V0, phi, theta, a and b to their defaults"""
        field_defaults = {
            fname: field.default
            for fname, field in self.__dataclass_fields__.items()
            if fname in ("V0", "phi", "theta", "a", "b")
        }
        self.set_state(**field_defaults)

    def set_state(self, V0=None, phi=None, theta=None, a=None, b=None, ball_id=None):
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
        if ball_id is not None:
            self.ball_id = ball_id

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
