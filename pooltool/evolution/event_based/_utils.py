from __future__ import annotations

import pooltool.constants as const
from pooltool.physics.utils import get_ball_energy
from pooltool.system.datatypes import System


def _system_has_energy(system: System) -> bool:
    """Return True if any ball in play has nonzero mechanical energy.

    Energy includes linear and rotational kinetic energy plus gravitational
    potential energy (with PE=0 defined at the on-table resting height,
    ``z = R``). Cue energy (e.g. ``system.cue.V0 > 0``) does not count. Pocketed and
    off-table balls are ignored: they sit at fixed heights that are not the resting
    height, yet take part in no further physics.
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
        if ball.state.s not in const.out_of_play
    )
