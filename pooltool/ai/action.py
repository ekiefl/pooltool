from __future__ import annotations

import attrs

from pooltool.objects.cue.datatypes import Cue


@attrs.define
class Action:
    V0: float
    phi: float
    theta: float
    a: float
    b: float

    def apply(self, cue: Cue) -> None:
        cue.V0 = self.V0
        cue.phi = self.phi
        cue.theta = self.theta
        cue.a = self.a
        cue.b = self.b

    @classmethod
    def from_cue(cls, cue: Cue) -> Action:
        return cls(
            cue.V0,
            cue.phi,
            cue.theta,
            cue.a,
            cue.b,
        )
