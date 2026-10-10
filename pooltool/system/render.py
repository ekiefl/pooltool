from __future__ import annotations

from attrs import define

import pooltool.ani.off_table as off_table
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

    def place_balls_initially(self) -> None:
        """Put each rendered ball at the start of its render history, if it has one"""
        for ball_render in self.balls.values():
            if not ball_render.history.empty:
                ball_render.set_render_state_from_history(0)

    def pose_cue(self) -> None:
        """Point the cue at its ball as the system's cue state describes

        The cue is placed at the ball's rendered position, so place the balls first.
        """
        if not self.cue.has_focus:
            self.cue.init_focus(self.balls[self.system.cue.cue_ball_id])
        self.cue.set_render_state_as_object_state()

    def resample(self, dt: float) -> None:
        """Derive each ball's render history from the system, one state every ``dt``

        A ball that left the table during the shot has its frozen off-table states
        replaced by the animated tail of :mod:`pooltool.ani.off_table`. An unsimulated
        system leaves every ball with an empty history.
        """
        box = self.table.bounding_box()
        for ball_id, ball_render in self.balls.items():
            if not self.system.simulated:
                ball_render.set_history(BallHistory(), box, None)
                continue

            ball = self.system.balls[ball_id]
            history = continuize_ball(ball, dt)
            crossing = off_table.crossing_event(self.system, ball_id)
            left_table_at = None
            if crossing is not None:
                history = off_table.with_tail(
                    history, off_table.exit_state(crossing), ball.params, box, dt
                )
                left_table_at = crossing.time
            ball_render.set_history(history, box, left_table_at)
