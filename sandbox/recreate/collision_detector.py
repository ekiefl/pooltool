"""Collision detector for analyzing ball trajectories and identifying collisions.

This module provides functionality to detect ball-ball collisions from trajectory
data without relying on the physics engine. It's designed to work with both
simulated and experimental trajectories.
"""

from typing import Dict, List, Tuple

import attrs
import numpy as np
from numpy.typing import NDArray
from trajectory import ShotTrajectoryData

import pooltool as pt


@attrs.define
class CollisionEvent:
    """Represents a detected collision between two balls."""

    ball1: str
    ball2: str
    time: float
    position1: Tuple[float, float]
    position2: Tuple[float, float]
    velocity1_before: Tuple[float, float]
    velocity2_before: Tuple[float, float]
    velocity1_after: Tuple[float, float]
    velocity2_after: Tuple[float, float]


class CollisionDetector:
    """Detects ball-ball collisions from trajectory data.

    This detector analyzes ball trajectories to identify potential collisions
    based on relative distances and velocity changes, without requiring
    access to the underlying physics engine.
    """

    def __init__(
        self,
        shot_data: ShotTrajectoryData,
        distance_threshold: float = 0.001,  # 1mm tolerance
        velocity_change_threshold: float = 0.05,
    ):  # 5% change
        """Initialize the collision detector.

        Parameters
        ----------
        shot_data : ShotTrajectoryData
            The trajectory data to analyze
        distance_threshold : float, optional
            Tolerance for ball-ball distance compared to expected 2*radius
        velocity_change_threshold : float, optional
            Minimum relative velocity change to consider a collision
        """
        self.shot_data = shot_data
        self.ball_radius = shot_data.radius
        self.expected_collision_distance = 2 * self.ball_radius
        self.distance_threshold = distance_threshold
        self.velocity_change_threshold = velocity_change_threshold
        self.ball_ids = list(shot_data.balls.keys())

    def _calculate_relative_distances(self) -> Dict[Tuple[str, str], NDArray]:
        """Calculate pairwise distances between all balls over time.

        Returns
        -------
        Dict[Tuple[str, str], NDArray]
            Dictionary mapping ball ID pairs to arrays of distances over time
        """
        distances = {}

        # We need to ensure all trajectories have the same time points
        # (This should already be the case, but it's good to verify)
        reference_times = None
        for ball_id, trajectory in self.shot_data.balls.items():
            if reference_times is None:
                reference_times = trajectory.t
            elif not np.array_equal(reference_times, trajectory.t):
                raise ValueError("All ball trajectories must have the same time points")

        # Calculate distances between each pair of balls
        for i, ball1_id in enumerate(self.ball_ids):
            ball1 = self.shot_data.balls[ball1_id]

            for j, ball2_id in enumerate(self.ball_ids[i + 1 :], i + 1):
                ball2 = self.shot_data.balls[ball2_id]

                # Calculate distance at each time point
                dx = ball2.x - ball1.x
                dy = ball2.y - ball1.y
                distance = np.sqrt(dx**2 + dy**2)

                distances[(ball1_id, ball2_id)] = distance

        return distances

    def _calculate_relative_velocities(self) -> Dict[Tuple[str, str], NDArray]:
        """Calculate pairwise relative velocities between balls over time.

        Returns
        -------
        Dict[Tuple[str, str], NDArray]
            Dictionary mapping ball ID pairs to arrays of relative velocities over time
        """
        velocities = {}

        for i, ball1_id in enumerate(self.ball_ids):
            ball1 = self.shot_data.balls[ball1_id]

            # Calculate ball velocities (use central difference)
            vx1 = np.gradient(ball1.x, ball1.t)
            vy1 = np.gradient(ball1.y, ball1.t)

            for j, ball2_id in enumerate(self.ball_ids[i + 1 :], i + 1):
                ball2 = self.shot_data.balls[ball2_id]

                # Calculate ball velocities
                vx2 = np.gradient(ball2.x, ball2.t)
                vy2 = np.gradient(ball2.y, ball2.t)

                # Calculate relative velocity magnitude
                # v_rel = |v2 - v1|
                dvx = vx2 - vx1
                dvy = vy2 - vy1
                rel_velocity = np.sqrt(dvx**2 + dvy**2)

                velocities[(ball1_id, ball2_id)] = rel_velocity

        return velocities

    def _detect_potential_collisions(
        self,
        distances: Dict[Tuple[str, str], NDArray],
        velocities: Dict[Tuple[str, str], NDArray],
    ) -> List[Tuple[str, str, int]]:
        """Identify time indices where potential collisions occur.

        Parameters
        ----------
        distances : Dict[Tuple[str, str], NDArray]
            Dictionary of distances between ball pairs
        velocities : Dict[Tuple[str, str], NDArray]
            Dictionary of relative velocities between ball pairs

        Returns
        -------
        List[Tuple[str, str, int]]
            List of (ball1_id, ball2_id, time_index) tuples for potential collisions
        """
        potential_collisions = []

        # Minimum time between consecutive collisions of the same ball pair (seconds)
        min_collision_separation = 0.25

        for (ball1_id, ball2_id), distance_array in distances.items():
            # Check if balls are close to the expected collision distance
            distance_close = (
                np.abs(distance_array - self.expected_collision_distance)
                < self.distance_threshold
            )

            # Skip if no potential collisions by distance
            if not np.any(distance_close):
                continue

            # Get relative velocity for this pair
            rel_velocity = velocities[(ball1_id, ball2_id)]

            # Check velocity changes (which could indicate a collision)
            # Calculate percentage change in velocity
            vel_change_percent = np.abs(np.diff(rel_velocity) / rel_velocity[:-1])

            # Add padding to make same size as other arrays
            vel_change_percent = np.append(vel_change_percent, 0)

            # Find where both distance is close to 2R and velocity changes significantly
            potential_indices = np.where(
                distance_close & (vel_change_percent > self.velocity_change_threshold)
            )[0]

            # Group by time proximity to avoid detecting the same collision multiple times
            if len(potential_indices) > 0:
                # Get the ball trajectory to access time values
                ball_traj = self.shot_data.balls[ball1_id]
                collision_times = ball_traj.t[potential_indices]

                # Group collision candidates by time proximity
                time_based_groups = []
                current_group = [0]  # Start with first index

                for i in range(1, len(collision_times)):
                    # If this time point is close to the previous one, add to current group
                    if (
                        collision_times[i] - collision_times[current_group[0]]
                        < min_collision_separation
                    ):
                        current_group.append(i)
                    else:
                        # Start a new group
                        time_based_groups.append(current_group)
                        current_group = [i]

                # Add the last group if it's not empty
                if current_group:
                    time_based_groups.append(current_group)

                # For each time-based group, pick the best collision point
                for group in time_based_groups:
                    group_indices = [potential_indices[i] for i in group]

                    # Calculate distance error for each index in the group
                    # This is how close the distance is to the expected collision distance (2R)
                    distance_errors = np.abs(
                        distance_array[group_indices] - self.expected_collision_distance
                    )

                    # Choose the index with minimum distance error (closest to exact 2R)
                    best_idx = group_indices[np.argmin(distance_errors)]
                    potential_collisions.append((ball1_id, ball2_id, best_idx))

        return potential_collisions

    def _create_collision_events(
        self, potential_collisions: List[Tuple[str, str, int]]
    ) -> List[CollisionEvent]:
        """Create detailed collision events from potential collision indices.

        Parameters
        ----------
        potential_collisions : List[Tuple[str, str, int]]
            List of potential collisions as (ball1_id, ball2_id, time_index)

        Returns
        -------
        List[CollisionEvent]
            List of detailed collision events
        """
        events = []

        for ball1_id, ball2_id, idx in potential_collisions:
            ball1 = self.shot_data.balls[ball1_id]
            ball2 = self.shot_data.balls[ball2_id]

            # Use central difference for calculating velocities
            # For "before" velocities, use the preceding point
            if idx > 0:
                dt_before = ball1.t[idx] - ball1.t[idx - 1]
                vx1_before = (ball1.x[idx] - ball1.x[idx - 1]) / dt_before
                vy1_before = (ball1.y[idx] - ball1.y[idx - 1]) / dt_before
                vx2_before = (ball2.x[idx] - ball2.x[idx - 1]) / dt_before
                vy2_before = (ball2.y[idx] - ball2.y[idx - 1]) / dt_before
            else:
                # If at first index, use forward difference
                dt_before = ball1.t[1] - ball1.t[0]
                vx1_before = (ball1.x[1] - ball1.x[0]) / dt_before
                vy1_before = (ball1.y[1] - ball1.y[0]) / dt_before
                vx2_before = (ball2.x[1] - ball2.x[0]) / dt_before
                vy2_before = (ball2.y[1] - ball2.y[0]) / dt_before

            # For "after" velocities, use the succeeding point
            if idx < len(ball1.t) - 1:
                dt_after = ball1.t[idx + 1] - ball1.t[idx]
                vx1_after = (ball1.x[idx + 1] - ball1.x[idx]) / dt_after
                vy1_after = (ball1.y[idx + 1] - ball1.y[idx]) / dt_after
                vx2_after = (ball2.x[idx + 1] - ball2.x[idx]) / dt_after
                vy2_after = (ball2.y[idx + 1] - ball2.y[idx]) / dt_after
            else:
                # If at last index, use backward difference
                dt_after = ball1.t[-1] - ball1.t[-2]
                vx1_after = (ball1.x[-1] - ball1.x[-2]) / dt_after
                vy1_after = (ball1.y[-1] - ball1.y[-2]) / dt_after
                vx2_after = (ball2.x[-1] - ball2.x[-2]) / dt_after
                vy2_after = (ball2.y[-1] - ball2.y[-2]) / dt_after

            # Create collision event
            event = CollisionEvent(
                ball1=ball1_id,
                ball2=ball2_id,
                time=ball1.t[idx],
                position1=(ball1.x[idx], ball1.y[idx]),
                position2=(ball2.x[idx], ball2.y[idx]),
                velocity1_before=(vx1_before, vy1_before),
                velocity2_before=(vx2_before, vy2_before),
                velocity1_after=(vx1_after, vy1_after),
                velocity2_after=(vx2_after, vy2_after),
            )

            events.append(event)

        # Sort events by time
        events.sort(key=lambda e: e.time)

        return events

    def detect_collisions(self) -> List[CollisionEvent]:
        """Detect all ball-ball collisions in the shot data.

        Returns
        -------
        List[CollisionEvent]
            List of detected collision events, sorted by time
        """
        # Calculate pairwise distances and velocities
        distances = self._calculate_relative_distances()
        velocities = self._calculate_relative_velocities()

        # Identify potential collisions
        potential_collisions = self._detect_potential_collisions(distances, velocities)

        # Create detailed collision events
        collision_events = self._create_collision_events(potential_collisions)

        return collision_events


if __name__ == "__main__":
    import os
    from pathlib import Path

    from plotting import plot_trajectories, visualize_collision

    # Load the shot data
    base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    systems = [pt.System.load(base_dir / f"shot{i}.msgpack") for i in range(1, 12)]
    noise_level: float = 0.002

    # Generate clean and noisy trajectories
    trajs_clean = [ShotTrajectoryData.from_simulated(system) for system in systems]
    trajs_noisy = [
        ShotTrajectoryData.from_simulated(
            system,
            noise_level=noise_level,
            random_seed=42 + i,  # Different seed for each trajectory
        )
        for i, system in enumerate(systems)
    ]

    for traj in trajs_clean[4:]:
        # Create collision detector
        detector = CollisionDetector(
            shot_data=traj, distance_threshold=0.02, velocity_change_threshold=0.1
        )

        # Detect collisions
        collisions = detector.detect_collisions()

        print(f"Detected {len(collisions)} ball-ball collisions:")
        for i, collision in enumerate(collisions):
            print(
                f"Collision {i+1}: Ball {collision.ball1} and Ball {collision.ball2} at t={collision.time:.3f}s"
            )

        plot_trajectories(traj)

        # Visualize each collision
        for collision in collisions:
            visualize_collision(traj, collision, time_window=0.2)

        print("----------")

    # Compare with expected collisions from clean trajectory
    # clean_traj = trajs_clean[-5]  # Corresponding clean trajectory
    # clean_detector = CollisionDetector(
    #    shot_data=clean_traj,
    #    distance_threshold=0.02,  # Smaller tolerance for clean data
    #    velocity_change_threshold=0.05
    # )
    #
    # clean_collisions = clean_detector.detect_collisions()
    #
    # print("\nGround truth collisions (from clean data):")
    # for i, collision in enumerate(clean_collisions):
    #    print(f"Collision {i+1}: Ball {collision.ball1} and Ball {collision.ball2} at t={collision.time:.3f}s")
