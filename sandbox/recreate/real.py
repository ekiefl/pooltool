from __future__ import annotations

import pickle
from pathlib import Path
from typing import Literal

import numpy as np
from trajectory import BallTrajectory, ShotTrajectoryData

_ball_lookup: dict[str, int] = {
    "white": 1,
    "yellow": 2,
    "red": 3,
}


def _infer_cue_ball(raw_shot: dict) -> Literal["white", "yellow"]:
    return (
        "white"
        if len(raw_shot["balls"][1]["x"]) > len(raw_shot["balls"][2]["x"])
        else "yellow"
    )


def load_real_trajectories(
    path: Path,
    dt: float,
    table_dims: tuple[float, float] = (2.84, 1.42),
) -> list[ShotTrajectoryData]:
    with open(path, "rb") as f:
        all_shots = pickle.load(f)

    shots = []
    for raw_shot in all_shots:
        cue_ball = _infer_cue_ball(raw_shot)
        trajectories: dict[str, BallTrajectory] = {}

        for ball_id in _ball_lookup:
            raw_ball = raw_shot["balls"][_ball_lookup[ball_id]]

            x, y, t = raw_ball["x"], raw_ball["y"], raw_ball["t"]

            # Use uniform time step
            t_uniform = np.arange(t[0], t[-1] + dt, dt)
            x_uniform = np.interp(t_uniform, t, x)
            y_uniform = np.interp(t_uniform, t, y)

            # Rotate to match pooltool coordinate system
            x_transformed = y_uniform
            y_transformed = table_dims[0] - x_uniform

            trajectories[ball_id] = BallTrajectory(
                x_transformed, y_transformed, t_uniform
            )

        shot = ShotTrajectoryData(cue_ball, trajectories, table_dims)
        shots.append(shot)

    return shots


if __name__ == "__main__":
    shots = load_real_trajectories(Path("./20221225_2_Match_Ersin_Cemal.pkl"), dt=0.01)
