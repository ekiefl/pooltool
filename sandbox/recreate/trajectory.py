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


@attrs.define
class Anchor:
    id: str
    t: float
    x: float
    y: float


@attrs.define
class TrajectoryDatum:
    id: str
    time: float
    pos: NDArray[np.float64]
    vec: NDArray[np.float64]

    @property
    def unit(self) -> NDArray[np.float64]:
        return self.vec / self.norm

    @property
    def norm(self) -> float:
        return pt.ptmath.norm2d(self.vec)

    @classmethod
    def from_anchors(cls, start_anchor: Anchor, end_anchor: Anchor) -> TrajectoryDatum:
        assert start_anchor.id == end_anchor.id
        return cls(
            end_anchor.id,
            end_anchor.t,
            np.array([end_anchor.x, end_anchor.y]),
            np.array([end_anchor.x - start_anchor.x, end_anchor.y - start_anchor.y]),
        )


def build_anchors_from_simulation(
    system: pt.System,
) -> dict[str, list[Anchor]]:
    anchors: dict[str, list[Anchor]] = {}
    for ball in system.balls.values():
        ball_anchors: list[Anchor] = []

        ball_events = pt.events.filter_events(
            system.events,
            pt.events.by_ball(ball.id, keep_nonevent=True),
            pt.events.by_type(
                [
                    pt.EventType.BALL_BALL,
                    pt.EventType.BALL_LINEAR_CUSHION,
                    pt.EventType.BALL_CIRCULAR_CUSHION,
                    pt.EventType.NONE,
                ]
            ),
        )

        event_indices = [
            idx for idx, event in enumerate(system.events) if event in ball_events
        ]

        for i in range(len(event_indices) - 1):
            state = ball.history[event_indices[i]]
            next_state = ball.history[event_indices[i + 1]]

            mid_point = (next_state.t + state.t) / 2
            mid_state = pt.interpolate_ball_states(ball, [mid_point])[0]

            point = Anchor(ball.id, state.t, state.rvw[0, 0], state.rvw[0, 1])
            mid_point = Anchor(
                ball.id, mid_state.t, mid_state.rvw[0, 0], mid_state.rvw[0, 1]
            )

            ball_anchors.append(point)
            ball_anchors.append(mid_point)

        # Add final state
        final_state = ball.history[-1]
        ball_anchors.append(
            Anchor(
                ball.id,
                final_state.t,
                final_state.rvw[0, 0],
                final_state.rvw[0, 1],
            )
        )

        anchors[ball.id] = ball_anchors

    return anchors


def build_traj_data_from_anchors(
    anchors: dict[str, list[Anchor]],
) -> list[TrajectoryDatum]:
    traj_data: list[TrajectoryDatum] = []

    for ball_anchors in anchors.values():
        for i in range(1, len(ball_anchors)):
            traj_datum = TrajectoryDatum.from_anchors(
                ball_anchors[i - 1],
                ball_anchors[i],
            )
            traj_data.append(traj_datum)

    return sorted(traj_data, key=lambda v: (v.time, v.id))


def get_corresponding_anchors(
    system: pt.System,
    template_anchors: dict[str, list[Anchor]],
) -> dict[str, list[Anchor]]:
    anchors: dict[str, list[Anchor]] = {}

    for ball_id, template_ball_anchors in template_anchors.items():
        ball_anchors: list[Anchor] = []

        times = np.array([anchor.t for anchor in template_ball_anchors])
        states = pt.interpolate_ball_states(
            system.balls[ball_id], times, extrapolate=True
        )

        for state in states:
            anchor = Anchor(ball_id, state.t, state.rvw[0, 0], state.rvw[0, 1])
            ball_anchors.append(anchor)

        anchors[ball_id] = ball_anchors

    return anchors


if __name__ == "__main__":
    pass
