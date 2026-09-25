from __future__ import annotations

from attrs import define

from pooltool.evolution.continuous import continuize_ball
from pooltool.objects.ball.datatypes import BallHistory
from pooltool.objects.ball.render import BallRender
from pooltool.objects.cue.render import CueRender
from pooltool.objects.table.render import TableRender
from pooltool.system.datatypes import System


@define
class SystemRender:
    """The rendered counterparts of a system's objects

    The histories the balls are animated from are derived from the system by
    :meth:`resample` and kept on the ball renders. Nothing here writes to the system.
    """

    system: System
    balls: dict[str, BallRender]
    table: TableRender
    cue: CueRender

    @staticmethod
    def from_system(system: System) -> SystemRender:
        return SystemRender(
            system=system,
            balls={ball_id: BallRender(ball) for ball_id, ball in system.balls.items()},
            table=TableRender(system.table),
            cue=CueRender(system.cue),
        )

    def resample(self, dt: float) -> None:
        """Derive each ball's render history from the system, one state every ``dt``

        An unsimulated system leaves every ball with an empty history.
        """
        for ball_id, ball_render in self.balls.items():
            if self.system.simulated:
                history = continuize_ball(
                    self.system.balls[ball_id], self.system.events, dt
                )
            else:
                history = BallHistory()
            ball_render.set_history(history)
