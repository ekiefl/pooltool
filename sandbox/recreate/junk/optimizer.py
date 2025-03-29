from __future__ import annotations

from pathlib import Path
from typing import Literal

import attrs
import numpy as np
import optuna
from numpy.typing import NDArray
from optuna.samplers import RandomSampler
from trajectory import ShotTrajectoryData

import pooltool as pt

# optuna.logging.set_verbosity(optuna.logging.WARNING)

PARAMETER_BOUNDS: dict[str, tuple[float, float]] = {
    "V0": (0.2, 4),
    "dphi": (-2, 2),
    "a": (-0.5, 0.5),
    "b": (-0.5, 0.5),
    "e_c": (0.85, 0.98),
    "u_s": (0.1, 0.212),
    "u_r": (0.005, 0.01),
    "f_c": (0.1, 0.25),
}


@attrs.define
class PhysicsParameters:
    u_s: float
    u_r: float
    e_c: float
    f_c: float


@attrs.define
class ShotParameters:
    V0: float
    dphi: float
    a: float
    b: float

    def phi(self, base_phi: float) -> float:
        return (base_phi + self.dphi) % 360


@attrs.define
class InitializationParameters:
    white_pos: NDArray[np.float64]
    yellow_pos: NDArray[np.float64]
    red_pos: NDArray[np.float64]
    cue: Literal["white", "yellow"]
    phi: float


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
    system.cue.phi = init_params.phi
    system.balls["white"].state.rvw[0] = init_params.white_pos
    system.balls["yellow"].state.rvw[0] = init_params.yellow_pos
    system.balls["red"].state.rvw[0] = init_params.red_pos
    return system


def _guess_phi(trajectory: ShotTrajectoryData, integration_time: float = 0.1) -> float:
    cue = trajectory.balls[trajectory.cue]
    pos = cue.get_positions(np.array([0, integration_time]))
    vector = pos[1] - pos[0]
    phi_rad = np.arctan2(vector[1], vector[0])
    phi_deg = (np.degrees(phi_rad) + 360) % 360
    assert 0 <= phi_deg <= 360
    return phi_deg


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
        phi=_guess_phi(trajectory),
    )
    return build_system(params)


def compute_mse(
    sim_array: NDArray[np.float64], real_array: NDArray[np.float64]
) -> float:
    squared_diffs = np.sum((sim_array - real_array) ** 2, axis=2)
    mse = np.mean(squared_diffs)
    return mse


def _get_collision_indices(shot: pt.System) -> list[int]:
    included_types = {
        pt.EventType.BALL_BALL,
        pt.EventType.BALL_LINEAR_CUSHION,
        pt.EventType.BALL_CIRCULAR_CUSHION,
        pt.EventType.SLIDING_ROLLING,
    }
    collision_indices = []
    for idx, event in enumerate(shot.events):
        if idx == 0 or idx == (len(shot.events) - 1):
            collision_indices.append(idx)
        elif event.event_type in included_types:
            collision_indices.append(idx)
    return collision_indices


def _get_simulated_ball_trajs(
    system: pt.System, collision_indices: list[int]
) -> tuple[
    NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]
]:
    white_history = system.balls["white"].history.vectorize()
    white_traj = white_history[0][collision_indices, 0, :2]  # type: ignore

    yellow_history = system.balls["yellow"].history.vectorize()
    yellow_traj = yellow_history[0][collision_indices, 0, :2]  # type: ignore

    red_history = system.balls["red"].history.vectorize()
    red_traj = red_history[0][collision_indices, 0, :2]  # type: ignore

    timepoints = white_history[2][collision_indices]  # type: ignore

    return white_traj, yellow_traj, red_traj, timepoints


# ----- INNER STUDY: Optimize shot parameters given fixed physics parameters ----- #
def optimize_shot_for_physics(
    real_trajectory: ShotTrajectoryData,
    physics_params: PhysicsParameters,
    n_trials: int = 200,
    n_jobs: int = 1,
    time_weight: float = 1.0,
) -> tuple[float, pt.System]:
    """
    For a given shot trajectory and fixed physics parameters,
    run an inner study to optimize shot parameters and return the best loss.
    """
    system_base = initialize_system_from_trajectory(real_trajectory)

    def run_trial(shot_params: ShotParameters) -> float:
        trial_system = system_base.copy()
        for ball in trial_system.balls.values():
            ball.params = attrs.evolve(ball.params, **attrs.asdict(physics_params))
        trial_system.cue.set_state(
            V0=shot_params.V0,
            phi=(system_base.cue.phi + shot_params.dphi) % 360,
            a=shot_params.a,
            b=shot_params.b,
        )
        pt.simulate(trial_system, inplace=True)

        collision_indices = _get_collision_indices(trial_system)
        white_traj, yellow_traj, red_traj, timepoints = _get_simulated_ball_trajs(
            trial_system, collision_indices
        )
        sim_array = np.stack((white_traj, yellow_traj, red_traj), axis=1)

        white_real_traj = real_trajectory.balls["white"].get_positions(timepoints)
        yellow_real_traj = real_trajectory.balls["yellow"].get_positions(timepoints)
        red_real_traj = real_trajectory.balls["red"].get_positions(timepoints)
        real_array = np.stack(
            (white_real_traj, yellow_real_traj, red_real_traj), axis=1
        )

        mse = compute_mse(sim_array, real_array)
        tf_sim = timepoints[-1]
        tf_real = real_trajectory.balls[real_trajectory.cue].t[-1]
        time_loss = (np.abs(tf_sim - tf_real) / tf_real) ** 2
        total_loss = mse + time_weight * time_loss
        return total_loss

    def inner_objective(trial: optuna.Trial) -> float:
        V0 = trial.suggest_float("V0", *PARAMETER_BOUNDS["V0"])
        dphi = trial.suggest_float("dphi", *PARAMETER_BOUNDS["dphi"])
        a = trial.suggest_float("a", *PARAMETER_BOUNDS["a"])
        b = trial.suggest_float("b", *PARAMETER_BOUNDS["b"])
        shot_params = ShotParameters(V0=V0, dphi=dphi, a=a, b=b)
        return run_trial(shot_params)

    def exploit_gamma(x: int) -> int:
        # Default is 0.1
        return min(int(np.ceil(0.05 * x)), 10)

    sampler = RandomSampler()
    # sampler = TPESampler(n_startup_trials=500, gamma=exploit_gamma, n_ei_candidates=24)

    study_inner = optuna.create_study(sampler=sampler, direction="minimize")
    study_inner.optimize(inner_objective, n_trials=n_trials, n_jobs=n_jobs)
    best_loss = study_inner.best_trial.value

    # Extract the best shot parameters from the inner study.
    best_shot_params = ShotParameters(
        V0=study_inner.best_trial.params["V0"],
        dphi=study_inner.best_trial.params["dphi"],
        a=study_inner.best_trial.params["a"],
        b=study_inner.best_trial.params["b"],
    )

    # Re-simulate the system using the best shot parameters.
    best_system = system_base.copy()
    for ball in best_system.balls.values():
        ball.params = attrs.evolve(ball.params, **attrs.asdict(physics_params))
    best_system.cue.set_state(
        V0=best_shot_params.V0,
        phi=(system_base.cue.phi + best_shot_params.dphi) % 360,
        a=best_shot_params.a,
        b=best_shot_params.b,
    )
    pt.simulate(best_system, inplace=True)

    return float(best_loss), best_system


def print_trial_callback(study: optuna.Study, trial: optuna.trial.FrozenTrial) -> None:
    print(
        f"Trial {trial.number} finished: Loss = {trial.value:.4f}, Parameters = {trial.params}"
    )


def print_best_callback(study: optuna.Study, trial: optuna.trial.FrozenTrial) -> None:
    best_trial = study.best_trial
    print(
        f"Current best trial: #{best_trial.number} with loss {best_trial.value:.4f} and parameters: {best_trial.params}"
    )


# ----- OUTER STUDY: Tune physics parameters using aggregated loss over several shots ----- #
def optimize_physics(
    real_shots: list[ShotTrajectoryData],
    n_trials: int = 50,
    n_jobs: int = 1,
    inner_trials: int = 200,
    time_weight: float = 1.0,
) -> tuple[PhysicsParameters, float]:
    """
    Outer study that tunes physics parameters. For each candidate physics parameter set,
    it runs an inner study (for each shot in real_shots) to determine the best shot parameters.
    The total loss (sum over all shots) is returned as the objective value.
    """

    def outer_objective(trial: optuna.Trial) -> float:
        # Physics parameters (hyperparameters)
        e_c = trial.suggest_float("e_c", *PARAMETER_BOUNDS["e_c"])
        u_s = trial.suggest_float("u_s", *PARAMETER_BOUNDS["u_s"])
        u_r = trial.suggest_float("u_r", *PARAMETER_BOUNDS["u_r"])
        f_c = trial.suggest_float("f_c", *PARAMETER_BOUNDS["f_c"])
        physics_params = PhysicsParameters(u_s=u_s, u_r=u_r, e_c=e_c, f_c=f_c)

        total_loss = 0.0
        # Evaluate this candidate physics parameter set on all provided shots.
        for shot in real_shots:
            shot_loss, _ = optimize_shot_for_physics(
                shot,
                physics_params,
                n_trials=inner_trials,
                n_jobs=1,
                time_weight=time_weight,
            )
            total_loss += shot_loss
        return total_loss

    study_outer = optuna.create_study(direction="minimize")
    study_outer.optimize(
        outer_objective,
        n_trials=n_trials,
        n_jobs=n_jobs,
        gc_after_trial=True,
        show_progress_bar=True,
        callbacks=[print_best_callback],
    )
    best_params = study_outer.best_trial.params
    best_loss = study_outer.best_trial.value
    physics_params_best = PhysicsParameters(
        u_s=best_params["u_s"],
        u_r=best_params["u_r"],
        e_c=best_params["e_c"],
        f_c=best_params["f_c"],
    )
    return physics_params_best, best_loss


if __name__ == "__main__":
    # Use argparse to allow a choice between hyperparameter tuning (outer study)
    # and fixed physics parameters with inner shot optimization.
    import argparse

    from viewer import BilliardDataViewer

    parser = argparse.ArgumentParser(
        description="Optimize billiard shot parameters using either hyperparameter tuning or fixed physics parameters."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["hyper", "single"],
        required=True,
        help="Select 'hyper' to tune physics parameters (outer study) or 'single' to use fixed physics parameters for shot optimization.",
    )
    args = parser.parse_args()

    dt = 0.01
    path = Path("./20221225_2_Match_Ersin_Cemal.msgpack")
    real_shots_all = pt.serialize.conversion.structure_from(
        path, list[ShotTrajectoryData]
    )
    # Use the first 10 shots for the study.

    if args.mode == "hyper":
        real_shots = real_shots_all[:10]
        best_physics, total_loss = optimize_physics(
            real_shots, n_trials=50, n_jobs=1, inner_trials=200, time_weight=1.0
        )
        print("Best physics parameters:", best_physics)
        print("Total loss over all shots:", total_loss)
    elif args.mode == "single":
        real_shots = real_shots_all[:1]
        physics_params = PhysicsParameters(
            u_s=0.17003445300732106,
            u_r=0.006498878670246954,
            e_c=0.9546870235795885,
            f_c=0.22609860002341078,
        )
        print("Using fixed physics parameters:", physics_params)
        simulated_shots = []
        for real_shot in real_shots:
            _, best_simulation = optimize_shot_for_physics(
                real_shot, physics_params, n_trials=200, n_jobs=1, time_weight=1.0
            )
            pt.continuize(best_simulation, inplace=True)
            sim_traj_data = ShotTrajectoryData.from_simulated(best_simulation)
            simulated_shots.append(sim_traj_data)

        viewer = BilliardDataViewer(real_shots, simulated_shots)
        viewer.master.mainloop()
