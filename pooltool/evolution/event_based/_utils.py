from __future__ import annotations

from pooltool.physics.utils import get_ball_energy
from pooltool.system.datatypes import System


def _system_has_energy(system: System) -> bool:
    """Return True if any ball in the system has kinetic energy.

    Cue energy (e.g. ``system.cue.V0 > 0``) does not count.
    """
    return any(
        bool(
            get_ball_energy(
                ball.state.rvw,
                ball.params.R,
                ball.params.m,
            )
        )
        for ball in system.balls.values()
    )
