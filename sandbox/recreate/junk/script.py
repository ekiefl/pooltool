"""
Collision Detection Script

This script detects collisions in ball trajectories by analyzing:
1. Direction changes (detecting sudden angle changes)
2. Proximity between balls and cushions
3. Velocity changes
"""

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from numpy.typing import NDArray
from scipy import stats

import pooltool as pt
from sandbox.recreate.plotting import plot_linear_fits
from sandbox.recreate.trajectory import BallTrajectory, ShotTrajectoryData


@dataclass
class LinearFit:
    """Linear fit of ball trajectory segment."""

    t_start: float  # Start time of window
    t_end: float  # End time of window
    window_size: float  # Actual window size (t_end - t_start)
    start_idx: int  # Start index in trajectory
    end_idx: int  # End index in trajectory
    start_pos: NDArray[np.float64]  # [x, y] of starting point
    end_pos: NDArray[np.float64]  # [x, y] of ending point
    r_squared: float  # R² value of the fit
    velocity: NDArray[np.float64]  # 2D velocity vector [vx, vy]


def fit_linear_segments(
    ball_traj: BallTrajectory,
    segment_length,
) -> List[LinearFit]:
    """Fit linear segments to ball trajectory based on path length thresholds.

    Args:
        ball_traj: Ball trajectory data
        segment_length: Minimum path length (meters) for a segment,
                               automatically adjusts window size based on ball speed

    Returns:
        List of LinearFit objects representing each segment
        with continuous segments (end_idx of segment n = start_idx of segment n+1)
    """
    t = ball_traj.t
    x = ball_traj.x
    y = ball_traj.y

    segments = []

    current_idx = 0

    while current_idx < len(t) - 1:
        t_start = t[current_idx]
        start_pos = np.array([x[current_idx], y[current_idx]])

        # Start with a minimum window size to ensure at least 2 points
        end_idx = current_idx + 1  # Minimum 2 points (current + 1 more)
        path_length = 0.0

        # Keep expanding the window until we reach the threshold or end of trajectory
        while end_idx < len(t) - 1:
            end_pos = np.array([x[end_idx], y[end_idx]])
            path_length = np.linalg.norm(end_pos - start_pos)

            # If we've reached the threshold, stop expanding
            if path_length >= segment_length:
                break

            # Otherwise, expand the window
            end_idx += 1

        # Extract segment indices
        indices = np.arange(current_idx, end_idx + 1)
        start_idx = indices[0]

        # Make sure this segment has advanced (avoid infinite loops)
        if start_idx == end_idx:
            current_idx += 1
            continue

        # Update position data
        start_pos = np.array([x[start_idx], y[start_idx]])
        end_pos = np.array([x[end_idx], y[end_idx]])

        # Get actual window time size
        actual_window_size = t[end_idx] - t[start_idx]

        # Extract segment data for regression
        t_segment = t[indices]
        x_segment = x[indices]
        y_segment = y[indices]

        # Calculate direction vector using linear regression
        slope_x, _, r_value_x, _, _ = stats.linregress(t_segment, x_segment)
        slope_y, _, r_value_y, _, _ = stats.linregress(t_segment, y_segment)

        segments.append(
            LinearFit(
                t_start=t_start,
                t_end=t[end_idx],
                window_size=actual_window_size,
                start_idx=start_idx,
                end_idx=end_idx,
                start_pos=start_pos,
                end_pos=end_pos,
                r_squared=(r_value_x**2 + r_value_y**2) / 2,
                velocity=np.array([slope_x, slope_y]),
            )
        )

        # Start the next segment from the end index of this segment
        # This ensures continuity between segments
        current_idx = end_idx

    return segments


def fit_all_trajectories(
    traj: ShotTrajectoryData,
    segment_length,
) -> Dict[str, List[LinearFit]]:
    """Fit linear segments to all ball trajectories in a shot.

    Args:
        traj: Shot trajectory data containing all ball trajectories
        segment_length: Minimum path length (meters) for a segment,
                               automatically adjusts window size based on ball speed

    Returns:
        Dictionary mapping ball IDs to their list of LinearFit objects
    """
    results = {}

    for ball_id, ball_traj in traj.balls.items():
        results[ball_id] = fit_linear_segments(ball_traj, segment_length)

    return results


@dataclass
class BallBallCollision:
    ball1: str
    ball2: str
    time: float
    position1: tuple[float, float]
    position2: tuple[float, float]


def main():
    """Main function to load, analyze and visualize ball collisions."""
    # Load systems
    systems = [pt.System.load(f"shot{i}.msgpack") for i in range(1, 12)]

    noise_level: float = 0.002

    # trajs_clean = [ShotTrajectoryData.from_simulated(system) for system in systems]
    trajs_noisy = [
        ShotTrajectoryData.from_simulated(
            system,
            noise_level=noise_level,
            random_seed=42 + i,  # Different seed for each trajectory
        )
        for i, system in enumerate(systems)
    ]
    # trajs_exp = pt.serialize.conversion.structure_from(
    #    "./20221225_2_Match_Ersin_Cemal.msgpack",
    #    list[ShotTrajectoryData],
    # )

    print("\n=== Analysis with experimental data ===")
    for traj in trajs_noisy[-5:]:
        fits = fit_all_trajectories(traj, segment_length=0.05)
        import ipdb

        ipdb.set_trace()
        plot_linear_fits(traj, fits)


if __name__ == "__main__":
    main()
