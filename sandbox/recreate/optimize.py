from __future__ import annotations

from typing import Literal

import attrs
import numpy as np
from numpy.typing import NDArray
from trajectory import ShotTrajectoryData

import pooltool as pt
from sandbox.recreate.compensation import (
    compensate_phi,
    compensate_V0,
)
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

    # Effective parameters that account for impact offsets
    V0_effective: float = None
    phi_effective: float = None

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
    return build_system(init_params=params)


def parameter_sweep(
    ref_traj: ShotTrajectoryData,
    ref_anchors: dict[str, list[Anchor]],
    ref_data: list[TrajectoryDatum],
    param_config: dict,
    fixed_params: dict[str, float],
    time_cutoff: float,
    alpha: float,
    plot: bool,
    compensate: bool,
    ball_mass: float,
    cue_mass: float,
    end_mass: float,
    base_V0: float,
    base_phi: float,
) -> tuple:
    """
    Perform a parameter sweep to find optimal values for parameters.
    Supports both 1D and 2D parameter sweeps.

    Parameters
    ----------
    ref_traj : ShotTrajectoryData
        Reference trajectory data
    ref_anchors : dict[str, list[Anchor]]
        Reference anchor points
    ref_data : list[TrajectoryDatum]
        Reference trajectory data points
    param_config : dict
        Configuration for parameters to sweep.
        For 1D sweep: {"name": "param_name", "values": array_of_values}
        For 2D sweep: {"names": ["param1", "param2"], "values": [array1, array2]}
    fixed_params : dict[str, float]
        Dictionary of parameters to keep fixed during the sweep
    time_cutoff : float
        Time cutoff for the simulation
    alpha : float
        Weight for direction vs magnitude in loss calculation
    plot : bool
        Whether to plot the loss curve
    compensate : bool
        Whether to compensate V0 and phi for off-center hits
    ball_mass : float
        Mass of the ball in kg (for compensation)
    cue_mass : float
        Mass of the cue in kg (for compensation)
    end_mass : float
        Mass of the cue tip in kg (for compensation)
    base_V0 : float
        Base V0 for center hit (required if compensate=True)
    base_phi : float
        Base phi for center hit (required if compensate=True)

    Returns
    -------
    tuple
        For 1D sweep: (optimal_value, losses)
        For 2D sweep: (optimal_value1, optimal_value2, loss_grid)
    """
    num_datapoints = sum(1 for datum in ref_data if datum.time <= time_cutoff)

    # Check if this is a 1D or 2D parameter sweep
    is_2d = "names" in param_config

    if is_2d:
        # 2D parameter sweep
        param_names = param_config["names"]
        param_values1 = param_config["values"][0]
        param_values2 = param_config["values"][1]
        losses = np.zeros((len(param_values1), len(param_values2)))

        for i, val1 in enumerate(param_values1):
            for j, val2 in enumerate(param_values2):
                trial = initialize_system_from_trajectory(ref_traj)

                # Set parameters with compensation if needed
                params = {**fixed_params, param_names[0]: val1, param_names[1]: val2}

                if (
                    compensate
                    and param_names == ["a", "b"]
                    and base_V0 is not None
                    and base_phi is not None
                ):
                    # Apply compensation for off-center hits
                    compensated_V0 = compensate_V0(
                        base_V0, val1, val2, ball_mass, cue_mass
                    )
                    compensated_phi = compensate_phi(
                        base_phi, val1, ball_mass, end_mass
                    )
                    params["V0"] = compensated_V0
                    params["phi"] = compensated_phi

                trial.cue.set_state(**params)

                pt.simulate(trial, inplace=True, t_final=time_cutoff)
                trial_anchors = get_corresponding_anchors(trial, ref_anchors)
                trial_data = build_traj_data_from_anchors(trial_anchors)

                loss = calculate_vector_loss(
                    ref_data[:num_datapoints],
                    trial_data[:num_datapoints],
                    alpha=alpha,
                )
                losses[i, j] = loss

        # Find optimal values
        min_idx = np.unravel_index(np.argmin(losses), losses.shape)
        optimal_val1 = param_values1[min_idx[0]]
        optimal_val2 = param_values2[min_idx[1]]

        if plot:
            import matplotlib.pyplot as plt

            plt.figure(figsize=(10, 8))
            x_mesh, y_mesh = np.meshgrid(param_values1, param_values2)
            plt.pcolormesh(x_mesh, y_mesh, losses.T, cmap="viridis", shading="auto")
            plt.colorbar(label="Loss")
            plt.xlabel(param_names[0])
            plt.ylabel(param_names[1])
            title = f"Loss landscape in {param_names[0]}-{param_names[1]} space"
            if compensate:
                title += " (with compensation)"
            plt.title(title)

            # Mark optimal point
            plt.scatter(optimal_val1, optimal_val2, color="red", s=100, marker="x")
            plt.text(
                optimal_val1,
                optimal_val2,
                f"  Optimal ({param_names[0]}={optimal_val1:.3f}, {param_names[1]}={optimal_val2:.3f})",
                color="white",
                fontsize=10,
            )

            plt.tight_layout()
            plt.show()

        return optimal_val1, optimal_val2, losses

    else:
        # 1D parameter sweep
        param_name = param_config["name"]
        param_values = param_config["values"]
        losses = []

        for param_value in param_values:
            trial = initialize_system_from_trajectory(ref_traj)

            # Set parameters
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
    events: int,
    num_phi: int,
    num_V0: int,
    plot: bool,
    ball_mass: float,
    cue_mass: float,
    end_mass: float,
) -> tuple[float, float]:
    """
    Estimate the optimal phi and V0 parameters for a center hit (a=0, b=0).

    Parameters
    ----------
    ref_traj : ShotTrajectoryData
        Reference trajectory data
    ref_anchors : dict[str, list[Anchor]]
        Reference anchor points
    ref_data : list[TrajectoryDatum]
        Reference trajectory data points
    events : int
        Number of events to consider in the optimization
    num_phi : int
        Number of phi values to try
    num_V0 : int
        Number of V0 values to try
    plot : bool
        Whether to plot the loss curves
    ball_mass : float
        Mass of the ball in kg
    cue_mass : float
        Mass of the cue in kg
    end_mass : float
        Mass of the cue tip in kg

    Returns
    -------
    tuple[float, float]
        Optimal phi and V0 values
    """
    times = sorted(set([datum.time for datum in ref_data]))
    time_cutoff = times[events - 1]

    # First sweep for phi
    phi_low, phi_high = PARAMETER_BOUNDS["phi"]
    phis = np.linspace(phi_low, phi_high, num_phi)
    phi_estimate, _ = parameter_sweep(
        ref_traj=ref_traj,
        ref_anchors=ref_anchors,
        ref_data=ref_data,
        param_config={"name": "phi", "values": phis},
        fixed_params={"V0": 1.0, "a": 0.0, "b": 0.0},
        time_cutoff=time_cutoff,
        alpha=1.0,
        plot=plot,
        compensate=False,
        ball_mass=ball_mass,
        cue_mass=cue_mass,
        end_mass=end_mass,
        base_V0=None,  # not needed without compensation
        base_phi=None,  # not needed without compensation
    )

    # Then sweep for V0 using the estimated phi
    V0_low, V0_high = PARAMETER_BOUNDS["V0"]
    V0s = np.linspace(V0_low, V0_high, num_V0)
    V0_estimate, _ = parameter_sweep(
        ref_traj=ref_traj,
        ref_anchors=ref_anchors,
        ref_data=ref_data,
        param_config={"name": "V0", "values": V0s},
        fixed_params={"phi": phi_estimate, "a": 0.0, "b": 0.0},
        time_cutoff=time_cutoff,
        alpha=0.0,
        plot=plot,
        compensate=False,
        ball_mass=ball_mass,
        cue_mass=cue_mass,
        end_mass=end_mass,
        base_V0=None,  # not needed without compensation
        base_phi=None,  # not needed without compensation
    )

    return phi_estimate, V0_estimate


def estimate_a_and_b(
    ref_traj: ShotTrajectoryData,
    ref_anchors: dict[str, list[Anchor]],
    ref_data: list[TrajectoryDatum],
    base_V0: float,
    base_phi: float,
    events: int,
    num_a: int,
    num_b: int,
    a_range: tuple[float, float],
    b_range: tuple[float, float],
    ball_mass: float,
    cue_mass: float,
    end_mass: float,
    alpha: float,
    plot: bool,
) -> tuple[float, float, NDArray[np.float64]]:
    """
    Estimate optimal a and b parameters while maintaining effective V0 and phi.

    This function sweeps through combinations of a and b values, compensating
    V0 and phi to maintain the same effective outgoing trajectory.

    Parameters
    ----------
    ref_traj : ShotTrajectoryData
        Reference trajectory data
    ref_anchors : dict[str, list[Anchor]]
        Reference anchor points
    ref_data : list[TrajectoryDatum]
        Reference trajectory data points
    base_V0 : float
        Baseline V0 for center hit (a=0, b=0)
    base_phi : float
        Baseline phi for center hit (a=0, b=0)
    events : int
        Number of events to consider in the optimization
    num_a : int
        Number of a values to try
    num_b : int
        Number of b values to try
    a_range : tuple[float, float]
        Range of a values to explore
    b_range : tuple[float, float]
        Range of b values to explore
    ball_mass : float
        Mass of the ball in kg
    cue_mass : float
        Mass of the cue in kg
    end_mass : float
        Mass of the cue tip in kg
    alpha : float
        Weight for direction vs magnitude in loss calculation
    plot : bool
        Whether to plot the results

    Returns
    -------
    tuple[float, float, NDArray[np.float64]]
        Optimal a value, optimal b value, and 2D array of losses
    """
    times = sorted(set([datum.time for datum in ref_data]))
    time_cutoff = times[events - 1]

    # Create ranges for a and b exploration
    a_values = np.linspace(a_range[0], a_range[1], num_a)
    b_values = np.linspace(b_range[0], b_range[1], num_b)

    # Use parameter_sweep with compensation for a/b
    optimal_a, optimal_b, losses = parameter_sweep(
        ref_traj=ref_traj,
        ref_anchors=ref_anchors,
        ref_data=ref_data,
        param_config={"names": ["a", "b"], "values": [a_values, b_values]},
        fixed_params={},  # We'll override V0 and phi with compensation
        time_cutoff=time_cutoff,
        alpha=alpha,
        plot=plot,
        compensate=True,
        ball_mass=ball_mass,
        cue_mass=cue_mass,
        end_mass=end_mass,
        base_V0=base_V0,
        base_phi=base_phi,
    )

    return optimal_a, optimal_b, losses


def iterative_optimize(
    ref_traj: ShotTrajectoryData,
    ref_anchors: dict[str, list[Anchor]],
    ref_data: list[TrajectoryDatum],
    max_events: int,
    search_narrowing_factor: float,
    initial_a_range: tuple[float, float],
    initial_b_range: tuple[float, float],
    num_a: int,
    num_b: int,
    num_phi: int,
    num_V0: int,
    ball_mass: float,
    cue_mass: float,
    end_mass: float,
    plot: bool,
) -> tuple[float, float, float, float]:
    """
    Iteratively optimize shot parameters by fitting to an increasing number of events.

    Parameters
    ----------
    ref_traj : ShotTrajectoryData
        Reference trajectory data
    ref_anchors : dict[str, list[Anchor]]
        Reference anchor points
    ref_data : list[TrajectoryDatum]
        Reference trajectory data points
    max_events : int
        Maximum number of events to include in optimization
    search_narrowing_factor : float
        Factor by which to narrow the search range in each iteration
    initial_a_range : tuple[float, float]
        Initial range for a parameter
    initial_b_range : tuple[float, float]
        Initial range for b parameter
    num_a : int
        Number of a values to explore
    num_b : int
        Number of b values to explore
    num_phi : int
        Number of phi values to explore in initial optimization
    num_V0 : int
        Number of V0 values to explore in initial optimization
    ball_mass : float
        Mass of the ball in kg
    cue_mass : float
        Mass of the cue in kg
    end_mass : float
        Mass of the cue tip in kg
    plot : bool
        Whether to plot the results

    Returns
    -------
    tuple[float, float, float, float]
        Final base_V0, base_phi, optimal_a, optimal_b values
    """
    print("\n--- Initial optimization: V0 and phi with center hit ---")
    # First find optimal V0 and phi with center hit (a=0, b=0)
    base_phi, base_V0 = estimate_phi_and_V0(
        ref_traj=ref_traj,
        ref_anchors=ref_anchors,
        ref_data=ref_data,
        events=1,
        num_phi=num_phi,
        num_V0=num_V0,
        plot=plot,
        ball_mass=ball_mass,
        cue_mass=cue_mass,
        end_mass=end_mass,
    )
    print(f"Initial baseline: V0 = {base_V0:.4f}, phi = {base_phi:.4f}°")

    # Initialize search ranges
    a_range = initial_a_range
    b_range = initial_b_range

    # Current best values
    curr_a = 0.0
    curr_b = 0.0

    # Iteratively optimize with increasing number of events
    for event_idx in range(1, max_events + 1):
        print(f"\n--- Iteration {event_idx}: Optimizing for {event_idx} events ---")

        # Narrow search ranges around current best values
        a_range = (
            max(
                initial_a_range[0],
                curr_a - (a_range[1] - a_range[0]) / 2 * search_narrowing_factor,
            ),
            min(
                initial_a_range[1],
                curr_a + (a_range[1] - a_range[0]) / 2 * search_narrowing_factor,
            ),
        )
        b_range = (
            max(
                initial_b_range[0],
                curr_b - (b_range[1] - b_range[0]) / 2 * search_narrowing_factor,
            ),
            min(
                initial_b_range[1],
                curr_b + (b_range[1] - b_range[0]) / 2 * search_narrowing_factor,
            ),
        )

        print(f"Search ranges: a in {a_range}, b in {b_range}")

        # Optimize a and b for the current number of events
        curr_a, curr_b, _ = estimate_a_and_b(
            ref_traj=ref_traj,
            ref_anchors=ref_anchors,
            ref_data=ref_data,
            base_V0=base_V0,
            base_phi=base_phi,
            events=event_idx,
            num_a=num_a,
            num_b=num_b,
            a_range=a_range,
            b_range=b_range,
            ball_mass=ball_mass,
            cue_mass=cue_mass,
            end_mass=end_mass,
            alpha=0.5,
            plot=plot,
        )

        # Get compensated V0 and phi for optimal a,b
        optimal_V0 = compensate_V0(
            base_V0=base_V0, a=curr_a, b=curr_b, ball_mass=ball_mass, cue_mass=cue_mass
        )
        optimal_phi = compensate_phi(
            phi_intended=base_phi, a=curr_a, ball_mass=ball_mass, end_mass=end_mass
        )

        print(f"Optimal parameters after {event_idx} events:")
        print(f"a = {curr_a:.4f}, b = {curr_b:.4f}")
        print(f"Compensated V0 = {optimal_V0:.4f} (base: {base_V0:.4f})")
        print(f"Compensated phi = {optimal_phi:.4f}° (base: {base_phi:.4f}°)")

    # Calculate final parameters
    final_V0 = compensate_V0(
        base_V0=base_V0, a=curr_a, b=curr_b, ball_mass=ball_mass, cue_mass=cue_mass
    )
    final_phi = compensate_phi(
        phi_intended=base_phi, a=curr_a, ball_mass=ball_mass, end_mass=end_mass
    )

    print("\n--- Final optimal parameters ---")
    print(f"base_V0 = {base_V0:.4f}, base_phi = {base_phi:.4f}°")
    print(f"a = {curr_a:.4f}, b = {curr_b:.4f}")
    print(f"Compensated V0 = {final_V0:.4f}")
    print(f"Compensated phi = {final_phi:.4f}°")

    return base_V0, base_phi, curr_a, curr_b


if __name__ == "__main__":
    reference = pt.System.load("shot1.msgpack")
    reference_traj = ShotTrajectoryData.from_simulated(reference)
    reference_anchors = build_anchors_from_simulation(reference)
    reference_data = build_traj_data_from_anchors(reference_anchors)

    cue_ball_id = reference.cue.cue_ball_id
    ball_mass = reference.balls[cue_ball_id].params.m
    cue_mass = reference.cue.specs.M
    end_mass = reference.cue.specs.end_mass

    print("Using physical parameters:")
    print(f"Ball mass: {ball_mass} kg")
    print(f"Cue mass: {cue_mass} kg")
    print(f"End mass: {end_mass} kg")

    # Example 1: Basic single-step optimization
    print("\n=== Basic optimization example ===")
    # First find optimal V0 and phi with center hit (a=0, b=0)
    base_phi, base_V0 = estimate_phi_and_V0(
        ref_traj=reference_traj,
        ref_anchors=reference_anchors,
        ref_data=reference_data,
        events=1,
        num_phi=360,
        num_V0=100,
        plot=True,
        ball_mass=ball_mass,
        cue_mass=cue_mass,
        end_mass=end_mass,
    )

    # Optimize a and b for first event
    optimal_a, optimal_b, _ = estimate_a_and_b(
        ref_traj=reference_traj,
        ref_anchors=reference_anchors,
        ref_data=reference_data,
        base_V0=base_V0,
        base_phi=base_phi,
        events=1,
        num_a=20,
        num_b=20,
        a_range=(-0.3, 0.3),
        b_range=(-0.3, 0.3),
        ball_mass=ball_mass,
        cue_mass=cue_mass,
        end_mass=end_mass,
        alpha=0.5,
        plot=True,
    )

    # Get compensated V0 and phi for optimal a,b
    optimal_V0 = compensate_V0(
        base_V0=base_V0,
        a=optimal_a,
        b=optimal_b,
        ball_mass=ball_mass,
        cue_mass=cue_mass,
    )
    optimal_phi = compensate_phi(
        phi_intended=base_phi, a=optimal_a, ball_mass=ball_mass, end_mass=end_mass
    )

    print("\nBasic optimization results:")
    print(f"a = {optimal_a:.4f}, b = {optimal_b:.4f}")
    print(f"Compensated V0 = {optimal_V0:.4f} (base: {base_V0:.4f})")
    print(f"Compensated phi = {optimal_phi:.4f}° (base: {base_phi:.4f}°)")

    # Run simulation with optimal parameters
    trial = initialize_system_from_trajectory(reference_traj)
    trial.cue.set_state(V0=optimal_V0, phi=optimal_phi, a=optimal_a, b=optimal_b)
    pt.simulate(trial, inplace=True)

    # Example 2: Iterative optimization
    print("\n\n=== Iterative optimization example ===")
    # Perform iterative optimization
    base_V0, base_phi, optimal_a, optimal_b = iterative_optimize(
        ref_traj=reference_traj,
        ref_anchors=reference_anchors,
        ref_data=reference_data,
        max_events=3,
        search_narrowing_factor=0.7,
        initial_a_range=(-0.3, 0.3),
        initial_b_range=(-0.3, 0.3),
        num_a=20,
        num_b=20,
        num_phi=360,
        num_V0=100,
        ball_mass=ball_mass,
        cue_mass=cue_mass,
        end_mass=end_mass,
        plot=True,
    )

    # Calculate final parameters with compensation
    final_V0 = compensate_V0(
        base_V0=base_V0,
        a=optimal_a,
        b=optimal_b,
        ball_mass=ball_mass,
        cue_mass=cue_mass,
    )
    final_phi = compensate_phi(
        phi_intended=base_phi, a=optimal_a, ball_mass=ball_mass, end_mass=end_mass
    )

    # Run simulation with final optimal parameters
    trial = initialize_system_from_trajectory(reference_traj)
    trial.cue.set_state(V0=final_V0, phi=final_phi, a=optimal_a, b=optimal_b)
    pt.simulate(trial, inplace=True)
    pt.show(trial)
