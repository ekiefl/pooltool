#! /usr/bin/env python

from __future__ import annotations

from typing import Counter

import pooltool.constants as const
from pooltool.ruleset.datatypes import (
    BallInHandOptions,
    Ruleset,
    ShotConstraints,
    ShotInfo,
)
from pooltool.ruleset.utils import get_pocketed_ball_ids_during_shot, respot
from pooltool.system.datatypes import System


class _SandBox(Ruleset):
    def build_shot_info(self, shot: System) -> ShotInfo:
        return ShotInfo(
            player=self.active_player,
            legal=True,
            reason="",
            turn_over=False,
            game_over=False,
            winner=None,
            score=Counter(),
        )

    def initial_shot_constraints(self) -> ShotConstraints:
        return ShotConstraints(
            ball_in_hand=BallInHandOptions.ANYWHERE,
            movable=None,
            cueable=None,
            hittable=tuple(),
            call_shot=False,
        )

    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        return self.initial_shot_constraints()

    def respot_balls(self, shot: System):
        """No balls respotted in this variant of 8-ball"""
        for ball_id, ball in shot.balls.items():
            if ball_id == shot.cue.cue_ball_id and ball.state.s == const.pocketed:
                respot(
                    shot,
                    ball_id,
                    shot.table.w / 2,
                    shot.table.l * 1 / 4,
                )

    def process_shot(self, shot: System):
        """Override process_shot to add log messages"""
        super().process_shot(shot)

        ball_ids = get_pocketed_ball_ids_during_shot(shot)
        if len(ball_ids):
            self.log.add_msg(
                f"Ball(s) potted: {', '.join(ball_ids)}", sentiment="neutral"
            )

    def copy(self) -> _SandBox:
        raise NotImplementedError("SandBox copy needs to be implemented")
