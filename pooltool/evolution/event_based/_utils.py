from __future__ import annotations

from pooltool.physics.utils import get_ball_energy
from pooltool.system.datatypes import System


def _system_has_energy(system: System) -> bool:
    """Return True if any ball in the system has nonzero mechanical energy.

    Energy includes linear and rotational kinetic energy plus gravitational
    potential energy (with PE=0 defined at the on-table resting height,
    ``z = R``). Cue energy (e.g. ``system.cue.V0 > 0``) does not count.
    """
    return any(
        get_ball_energy(
            ball.state.rvw,
            ball.params.R,
            ball.params.m,
            ball.params.g,
        )
        > 0.0
        for ball in system.balls.values()
    )
