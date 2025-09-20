from __future__ import annotations

from attrs import define

from pooltool.evolution.continuous import continuize
from pooltool.objects.ball.render import BallRender
from pooltool.objects.cue.render import CueRender
from pooltool.objects.table.render import TableRender
from pooltool.system.datatypes import System


@define
class SystemRender:
    balls: dict[str, BallRender]
    table: TableRender
    cue: CueRender

    @staticmethod
    def from_system(system: System) -> SystemRender:
        if system.simulated and not system.continuized:
            continuize(system, inplace=True)

        return SystemRender(
            balls={ball_id: BallRender(ball) for ball_id, ball in system.balls.items()},
            table=TableRender(system.table),
            cue=CueRender(system.cue),
        )
