import logging
from typing import Optional

import numpy as np

from pooltool import Cue, MultiSystem, ShotViewer, System, Table, simulate
from pooltool.constants import pocketed
from pooltool.error import SimulateError
from pooltool.layouts import get_nine_ball_rack
from pooltool.utils import wiggle


def aim(system: System) -> None:
    lowest_ball = min(
        ball.id
        for ball in system.balls.values()
        if (ball.id != "cue" and ball.state.s != pocketed)
    )

    # Aim to pot the ball, introduce a lot of uncertainty (10 deg)
    system.cue.cue_ball_id = "cue"
    system.aim_for_best_pocket(lowest_ball)
    system.cue.phi = wiggle(system.cue.phi, 10)

    # Choose a random spin
    ang = 2 * np.pi * np.random.rand()
    rad = 0.5 * np.random.rand()
    system.cue.a = rad * np.cos(ang)
    system.cue.b = rad * np.sin(ang)
    system.cue.theta = 8

    # Choose a random cue speed
    system.cue.V0 = np.random.uniform(0.2, 4)


def simulate_game() -> MultiSystem:
    m = MultiSystem()

    system = System(
        cue=Cue.default(),
        table=(table := Table.default()),
        balls=get_nine_ball_rack(table),
    )

    shots = 0
    while True:
        if all(
            ball.state.s == pocketed
            for ball in system.balls.values()
            if ball.id != "cue"
        ):
            break

        if shots > 100:
            break

        aim(system)
        system.strike()

        try:
            simulate(system)
        except SimulateError:
            break

        # Continuize the shot (in case this has an effect)
        system.continuize()

        m.append(system)
        system = system.copy()
        system.reset_history()

        if system.balls["cue"].state.s == pocketed:
            # The cue ball is pocketed. Place somewhere on table
            system.randomize_positions(["cue"])
            system.balls["cue"].state.rvw[0, 2]

        shots += 1

    print(f"Game composed of {shots} shots")
    return m


def has_drift(multisystem: MultiSystem) -> bool:
    for system in multisystem:
        for ball in system.balls.values():
            for state in ball.history:
                if state.s == pocketed:
                    continue

                if state.rvw[0, 2] != ball.params.R:
                    return True

            for state in ball.history_cts:
                if state.s == pocketed:
                    continue

                if state.rvw[0, 2] != ball.params.R:
                    return True

    return False


if __name__ == "__main__":
    assert not any(has_drift(simulate_game()) for _ in range(30))
