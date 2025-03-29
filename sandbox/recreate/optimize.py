from __future__ import annotations

from typing import Literal

import attrs
import numpy as np
from numpy.typing import NDArray
from trajectory import ShotTrajectoryData

import pooltool as pt
from sandbox.recreate.loss import calculate_vector_loss
from sandbox.recreate.trajectory import (
    Anchor,
    TrajectoryDatum,
    build_anchors_from_simulation,
    build_traj_data_from_anchors,
    get_corresponding_anchors,
)

PARAMETER_BOUNDS: dict[str, tuple[float, float]] = {
    "V0": (0.2, 6),
    "phi": (0, 360),
    "theta": (0, 8),
    "a": (-0.5, 0.5),
    "b": (-0.5, 0.5),
}


@attrs.define
class ShotParameters:
    V0: float
    phi_raw: float
    theta: float
    a: float
    b: float

    def phi(self) -> float:
        return (self.phi_raw) % 360


def compensate_V0_for_offset(base_V0: float, a: float, b: float) -> float:
    """
    Compensate the cue velocity (V0) for off-center hits to maintain consistent ball speed.

    When striking a ball off-center (a,b ≠ 0,0), the outgoing ball velocity decreases.
    This function calculates the adjusted V0 needed to maintain the same outgoing
    ball velocity as a center hit.

    The compensation formula is:
    V0_compensated = base_V0 * (1 + [5/(2(1 + m/M))] * (a² + b²))

    Args:
        base_V0: The cue velocity for center hit (a=0, b=0)
        a: Horizontal offset from ball center (-1 to 1)
        b: Vertical offset from ball center (-1 to 1)

    Returns:
        The compensated V0 value to use for the off-center hit
    """
    system = template()
    ball_mass = system.balls[system.cue.cue_ball_id].params.m
    cue_mass = system.cue.specs.M

    distance_squared = a**2 + b**2
    coefficient = 5 / (2 * (1 + ball_mass / cue_mass))
    compensation_factor = 1 + coefficient * distance_squared

    return base_V0 * compensation_factor


@attrs.define
class InitializationParameters:
    white_pos: NDArray[np.float64]
    yellow_pos: NDArray[np.float64]
    red_pos: NDArray[np.float64]
    cue: Literal["white", "yellow"]


def template() -> pt.System:
    table = pt.Table.from_game_type(pt.GameType.THREECUSHION)
    return pt.System(
        table=table,
        cue=pt.Cue(cue_ball_id="white"),
        balls=pt.layouts.get_rack(pt.GameType.THREECUSHION, table),
    )


def build_system(init_params: InitializationParameters) -> pt.System:
    system = template()
    system.cue.cue_ball_id = init_params.cue
    system.cue.a = 0.0
    system.cue.b = 0.0
    system.balls["white"].state.rvw[0] = init_params.white_pos
    system.balls["yellow"].state.rvw[0] = init_params.yellow_pos
    system.balls["red"].state.rvw[0] = init_params.red_pos
    return system


def initialize_system_from_trajectory(trajectory: ShotTrajectoryData) -> pt.System:
    params = InitializationParameters(
        white_pos=np.array(
            [
                trajectory.balls["white"].x[0],
                trajectory.balls["white"].y[0],
                trajectory.radius,
            ]
        ),
        yellow_pos=np.array(
            [
                trajectory.balls["yellow"].x[0],
                trajectory.balls["yellow"].y[0],
                trajectory.radius,
            ]
        ),
        red_pos=np.array(
            [
                trajectory.balls["red"].x[0],
                trajectory.balls["red"].y[0],
                trajectory.radius,
            ]
        ),
        cue=trajectory.cue,
    )
    return build_system(params)


def estimate_phi_and_V0(
    ref_traj: ShotTrajectoryData,
    ref_anchors: dict[str, list[Anchor]],
    ref_data: list[TrajectoryDatum],
    events: int = 1,
    num_phi: int = 1080,
    num_V0: int = 30,
) -> tuple[float, float]:
    times = sorted(set([datum.time for datum in ref_data]))
    time_cutoff = times[events - 1]
    num_datapoints = sum(1 for datum in ref_data if datum.time <= time_cutoff)

    phi_losses = []
    phi_low, phi_high = PARAMETER_BOUNDS["phi"]
    phis = np.linspace(phi_low, phi_high, num_phi)

    for phi in phis:
        trial = initialize_system_from_trajectory(ref_traj)
        trial.cue.set_state(phi=phi, V0=1.0)
        pt.simulate(trial, inplace=True)
        trial_anchors = get_corresponding_anchors(trial, ref_anchors)
        trial_data = build_traj_data_from_anchors(trial_anchors)

        loss = calculate_vector_loss(
            ref_data[:num_datapoints],
            trial_data[:num_datapoints],
            alpha=1,
        )
        phi_losses.append(loss)

    phi_estimate = phis[np.argmin(phi_losses)]

    import matplotlib.pyplot as plt

    plt.plot(phis, phi_losses)
    plt.show()

    V0_losses = []
    V0_low, V0_high = PARAMETER_BOUNDS["V0"]
    V0s = np.linspace(V0_low, V0_high, num_V0)

    for V0 in V0s:
        trial = initialize_system_from_trajectory(ref_traj)
        trial.cue.set_state(V0=V0, phi=phi_estimate)
        pt.simulate(trial, inplace=True, t_final=time_cutoff)
        trial_anchors = get_corresponding_anchors(trial, ref_anchors)
        trial_data = build_traj_data_from_anchors(trial_anchors)

        loss = calculate_vector_loss(
            ref_data[:num_datapoints],
            trial_data[:num_datapoints],
            alpha=0.0,
        )
        V0_losses.append(loss)

    V0_estimate = V0s[np.argmin(V0_losses)]

    import matplotlib.pyplot as plt

    plt.plot(V0s, V0_losses)
    plt.show()

    return phi_estimate, V0_estimate


if __name__ == "__main__":
    reference = pt.System.load("shot1.msgpack")
    reference_traj = ShotTrajectoryData.from_simulated(reference)
    reference_anchors = build_anchors_from_simulation(reference)
    reference_data = build_traj_data_from_anchors(reference_anchors)

    test = reference.copy()
    test.reset_balls()
    test.reset_history()
    pt.simulate(test, inplace=True)

    phi, V0 = estimate_phi_and_V0(
        reference_traj,
        reference_anchors,
        reference_data,
        events=1,
        num_phi=360,
        num_V0=100,
    )
    trial = initialize_system_from_trajectory(reference_traj)
    trial.cue.set_state(phi=phi, V0=V0)
    pt.simulate(trial, inplace=True)
    pt.show(trial)
