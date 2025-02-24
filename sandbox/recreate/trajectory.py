from __future__ import annotations

from typing import Literal, cast

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
    def from_simulated(cls, shot: pt.System, dt: float) -> ShotTrajectoryData:
        assert shot.continuized

        cue = cast(Literal["white", "yellow"], shot.cue.cue_ball_id)
        table_dims = shot.table.l, shot.table.w
        radius = shot.balls[cue].params.R

        trajs = {}
        for ball in shot.balls.values():
            trajs[ball.id] = BallTrajectory.from_ball(ball)

        return cls(cue, trajs, table_dims, radius)


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

    @classmethod
    def from_ball(cls, ball: pt.Ball) -> BallTrajectory:
        rvw, _, t = ball.history_cts.vectorize()  # type: ignore
        dt = t[1] - t[0]
        t[-1] = t[-2] + dt # last value is not dt after second last. fix that
        return cls(rvw[:, 0, 0], rvw[:, 0, 1], t)
