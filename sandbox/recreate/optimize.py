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


def parameter_sweep(
    ref_traj: ShotTrajectoryData,
    ref_anchors: dict[str, list[Anchor]],
    ref_data: list[TrajectoryDatum],
    param_name: str,
    param_values: NDArray[np.float64],
    fixed_params: dict[str, float],
    time_cutoff: float,
    alpha: float = 1.0,
    plot: bool = True,
) -> tuple[float, list[float]]:
    """
    Perform a parameter sweep to find the optimal value for a given parameter.

    Parameters
    ----------
    ref_traj : ShotTrajectoryData
        Reference trajectory data
    ref_anchors : dict[str, list[Anchor]]
        Reference anchor points
    ref_data : list[TrajectoryDatum]
        Reference trajectory data points
    param_name : str
        Name of the parameter to sweep
    param_values : NDArray[np.float64]
        Array of parameter values to try
    fixed_params : dict[str, float]
        Dictionary of parameters to keep fixed during the sweep
    time_cutoff : float
        Time cutoff for the simulation
    alpha : float, default=1.0
        Weight for direction vs magnitude in loss calculation
    plot : bool, default=True
        Whether to plot the loss curve

    Returns
    -------
    tuple[float, list[float]]
        Optimal parameter value and list of losses for all parameter values
    """
    num_datapoints = sum(1 for datum in ref_data if datum.time <= time_cutoff)
    losses = []

    for param_value in param_values:
        trial = initialize_system_from_trajectory(ref_traj)

        # Set all parameters
        params = {**fixed_params, param_name: param_value}
        trial.cue.set_state(**params)

        pt.simulate(trial, inplace=True, t_final=time_cutoff)
        trial_anchors = get_corresponding_anchors(trial, ref_anchors)
        trial_data = build_traj_data_from_anchors(trial_anchors)

        loss = calculate_vector_loss(
            ref_data[:num_datapoints],
            trial_data[:num_datapoints],
            alpha=alpha,
        )
        losses.append(loss)

    optimal_value = param_values[np.argmin(losses)]

    if plot:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 6))
        plt.plot(param_values, losses)
        plt.xlabel(param_name)
        plt.ylabel("Loss")
        plt.title(f"Parameter sweep for {param_name}")
        plt.axvline(
            x=optimal_value,
            color="r",
            linestyle="--",
            label=f"Optimal {param_name} = {optimal_value:.4f}",
        )
        plt.legend()
        plt.grid(True)
        plt.show()

    return optimal_value, losses


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

    # First sweep for phi
    phi_low, phi_high = PARAMETER_BOUNDS["phi"]
    phis = np.linspace(phi_low, phi_high, num_phi)
    phi_estimate, _ = parameter_sweep(
        ref_traj=ref_traj,
        ref_anchors=ref_anchors,
        ref_data=ref_data,
        param_name="phi",
        param_values=phis,
        fixed_params={"V0": 1.0},
        time_cutoff=time_cutoff,
        alpha=1.0,
        plot=True,
    )

    # Then sweep for V0 using the estimated phi
    V0_low, V0_high = PARAMETER_BOUNDS["V0"]
    V0s = np.linspace(V0_low, V0_high, num_V0)
    V0_estimate, _ = parameter_sweep(
        ref_traj=ref_traj,
        ref_anchors=ref_anchors,
        ref_data=ref_data,
        param_name="V0",
        param_values=V0s,
        fixed_params={"phi": phi_estimate},
        time_cutoff=time_cutoff,
        alpha=0.0,
        plot=True,
    )

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

    phi_init, V0_init = estimate_phi_and_V0(
        reference_traj,
        reference_anchors,
        reference_data,
        events=1,
        num_phi=360,
        num_V0=100,
    )

    trial = initialize_system_from_trajectory(reference_traj)
    trial.cue.set_state(phi=phi_init, V0=V0_init)
    pt.simulate(trial, inplace=True)
    pt.show(trial)
