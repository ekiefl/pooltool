from __future__ import annotations

from typing import Literal, Optional, cast

import attrs
import numpy as np
from numpy.typing import NDArray

import pooltool as pt


@attrs.define
class ShotTrajectoryData:
    cue: Literal["white", "yellow"]
    balls: dict[str, BallTrajectory]
    table_dims: tuple[float, float] = (2.84, 1.42)
    radius: float = 0.0615 / 2

    @classmethod
    def from_simulated(
        cls,
        shot: pt.System,
        noise_level: float = 0.0,
        random_seed: Optional[int] = None,
    ) -> ShotTrajectoryData:
        """Create trajectory data from a simulated shot, with optional noise.

        Args:
            shot: A simulated shot system with continuized history
            noise_level: Standard deviation of Gaussian noise to add to positions (in meters)
            random_seed: Optional seed for reproducible noise generation

        Returns:
            A new ShotTrajectoryData instance
        """
        assert shot.continuized

        # Set random seed if provided
        if random_seed is not None:
            np.random.seed(random_seed)

        cue = cast(Literal["white", "yellow"], shot.cue.cue_ball_id)
        table_dims = shot.table.l, shot.table.w
        radius = shot.balls[cue].params.R

        trajs = {}
        for ball in shot.balls.values():
            # Create trajectory without noise first
            traj = BallTrajectory.from_ball(ball)

            # Add noise if requested
            if noise_level > 0:
                # Add Gaussian noise to x and y coordinates
                x_noise = np.random.normal(0, noise_level, size=len(traj.x))
                y_noise = np.random.normal(0, noise_level, size=len(traj.y))

                # Apply noise
                traj.x = traj.x + x_noise
                traj.y = traj.y + y_noise

            trajs[ball.id] = traj

        return cls(cue, trajs, table_dims, radius)

    def lengthen(self, t_new: float) -> None:
        """Lengthen all ball trajectories to the specified time.

        Args:
            t_new: The new end time for the trajectories.
                If a trajectory already extends past t_new, it is left unchanged.
        """
        for ball_traj in self.balls.values():
            ball_traj.lengthen(t_new)


@attrs.define
class BallTrajectory:
    x: NDArray[np.float64]
    y: NDArray[np.float64]
    t: NDArray[np.float64]

    @property
    def dt(self) -> float:
        return self.t[1] - self.t[0]

    def __attrs_post_init__(self) -> None:
        assert len(self.x) == len(self.y) == len(self.t)
        dt = self.dt
        for diff in np.diff(self.t):
            assert np.isclose(dt, diff)

    def get_positions(self, ts: NDArray[np.float64]) -> NDArray[np.float64]:
        """For array of times, return coordinates corresponding to closest matching time."""
        indices = np.clip(
            np.rint((ts - self.t[0]) / self.dt).astype(int), 0, len(self.t) - 1
        )
        return np.stack((self.x[indices], self.y[indices]), axis=1)

    def lengthen(self, t_new: float) -> None:
        """Lengthen the trajectory to the specified time.

        Args:
            t_new: The new end time for the trajectory.
                If the trajectory already extends past t_new, it is left unchanged.
        """
        if t_new <= self.t[-1]:
            return

        dt = self.dt
        num_new_steps = int(np.ceil((t_new - self.t[-1]) / dt))

        new_t = np.array([self.t[-1] + dt * (i + 1) for i in range(num_new_steps)])

        new_x = np.full(num_new_steps, self.x[-1])
        new_y = np.full(num_new_steps, self.y[-1])

        self.t = np.concatenate([self.t, new_t])
        self.x = np.concatenate([self.x, new_x])
        self.y = np.concatenate([self.y, new_y])

    @classmethod
    def from_ball(cls, ball: pt.Ball) -> BallTrajectory:
        rvw, _, t = ball.history_cts.vectorize()  # type: ignore
        dt = t[1] - t[0]
        t[-1] = t[-2] + dt  # last value is not dt after second last. fix that
        return cls(rvw[:, 0, 0], rvw[:, 0, 1], t)
