#! /usr/bin/env python

from __future__ import annotations

from typing import Optional

from attrs import define, evolve, field, fields_dict


@define(frozen=True)
class CueSpecs:
    # TODO add snooker cue if needed
    brand: str = field(default="Predator")
    M: float = field(default=0.567)  # 20oz
    length: float = field(default=1.4732)  # 58in
    tip_radius: float = field(default=0.007)  # 14mm tip
    butt_radius: float = field(default=0.02)

    @staticmethod
    def default() -> CueSpecs:
        return CueSpecs()


@define
class Cue:
    id: str = field(default="cue_stick")

    V0: float = field(default=2.0)
    phi: float = field(default=0.0)
    theta: float = field(default=0.0)
    a: float = field(default=0.0)
    b: float = field(default=0.25)
    cue_ball_id: str = field(default="cue")

    specs: CueSpecs = field(factory=CueSpecs.default)

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

    def copy(self) -> Cue:
        """Create a deep-ish copy

        `specs` is shared between self and the copy, but that's ok because it's frozen
        and has no mutable attributes
        """
        return evolve(self)

    def reset_state(self):
        """Reset V0, phi, theta, a and b to their defaults"""
        field_defaults = {
            fname: field.default
            for fname, field in fields_dict(self.__class__).items()
            if fname in ("V0", "phi", "theta", "a", "b")
        }
        self.set_state(**field_defaults)

    def set_state(
        self, V0=None, phi=None, theta=None, a=None, b=None, cue_ball_id=None
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
        if cue_ball_id is not None:
            self.cue_ball_id = cue_ball_id

    @classmethod
    def default(cls) -> Cue:
        return Cue()
