from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from direct.interval.IntervalGlobal import Func, Parallel, Sequence, Wait
from panda3d.direct import HideInterval, ShowInterval

from pooltool.objects.ball.render import BallRender
from pooltool.objects.cue.render import CueRender
from pooltool.objects.table.render import TableRender
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum, auto


@dataclass
class SystemRender:
    balls: Dict[str, BallRender]
    table: TableRender
    cue: CueRender

    @staticmethod
    def from_system(system: System) -> SystemRender:
        return SystemRender(
            balls={ball_id: BallRender(ball) for ball_id, ball in system.balls.items()},
            table=TableRender(system.table),
            cue=CueRender(system.cue),
        )


class PlaybackMode(StrEnum):
    LOOP = auto()
    SINGLE = auto()


class SystemController:
    def __init__(self) -> None:
        self.system: SystemRender
        self.stroke_animation: Sequence = Sequence()
        self.ball_animations: Parallel = Parallel()
        self.shot_animation: Sequence = Sequence()
        self.paused: bool = False

    @property
    def table(self):
        return self.system.table

    @property
    def balls(self):
        return self.system.balls

    @property
    def cue(self):
        return self.system.cue

    def attach_system(self, system: System) -> None:
        """Teardown existing system, attach and attach new system"""
        if hasattr(self, "system"):
            self.teardown()
        self.system = SystemRender.from_system(system)

    def reset_animation(self) -> None:
        """Set objects to initial states, pause, and remove animations"""
        self.playback_speed: float = 1

        self.shot_animation.clearToInitial()
        self.stroke_animation.clearToInitial()
        self.ball_animations.clearToInitial()

        self.stroke_animation = Sequence()
        self.ball_animations = Parallel()
        self.shot_animation = Sequence()

    @property
    def animation_finished(self):
        """Returns whether or not the animation is finished

        Returns true if the animation has stopped and it's not because the game has been
        paused. The animation is never finished if it's playing in a loop.
        """
        return not self.shot_animation.isPlaying() and not self.paused

    def buildup(self) -> None:
        """Render all object nodes"""
        self.system.table.render()
        for ball in self.system.balls.values():
            ball.render()
        self.system.cue.render()

    def teardown(self) -> None:
        """Stop animations and remove all nodes"""
        self.reset_animation()

        for ball in self.system.balls.values():
            ball.remove_nodes()

        self.system.table.remove_nodes()
        self.system.cue.remove_nodes()

    def start_animation(self, playback_mode: PlaybackMode) -> None:
        assert len(self.shot_animation), "Must populate shot_animation"

        if playback_mode == PlaybackMode.SINGLE:
            self.shot_animation.start()
        elif playback_mode == PlaybackMode.LOOP:
            self.shot_animation.loop()

    def restart_animation(self) -> None:
        self.shot_animation.set_t(0)

    def restart_ball_animations(self) -> None:
        self.ball_animations.set_t(0)

    def toggle_pause(self) -> None:
        if self.shot_animation.isPlaying():
            self.pause_animation()
        else:
            self.resume_animation()

    def offset_time(self, dt) -> None:
        old_t = self.shot_animation.get_t()
        new_t = max(0, min(old_t + dt, self.shot_animation.duration))
        self.shot_animation.set_t(new_t)

    def pause_animation(self) -> None:
        self.shot_animation.pause()

    def resume_animation(self) -> None:
        self.shot_animation.resume()

    def build_shot_animation(
        self,
        animate_stroke: bool = True,
        trailing_buffer: float = 0,
        leading_buffer: float = 0,
    ) -> None:
        """From the SystemRender, build the shot animation"""

        # This takes ~90% of this method's execution time
        self.ball_animations = Parallel()
        for ball in self.system.balls.values():
            if not ball.rendered:
                ball.render()

            self.ball_animations.append(
                ball.get_playback_sequence(playback_speed=self.playback_speed)
            )

        if not animate_stroke:
            # Early return, skipping stroke trajectory
            self.system.cue.hide_nodes()
            self.stroke_animation = Sequence
            self.shot_animation = Sequence(
                Func(self.restart_ball_animations),
                self.ball_animations,
                Wait(trailing_buffer),
            )
            return

        self.stroke_animation = Sequence(
            ShowInterval(self.system.cue.get_node("cue_stick")),
            self.system.cue.get_stroke_sequence(),
            HideInterval(self.system.cue.get_node("cue_stick")),
        )
        self.shot_animation = Sequence(
            Func(self.restart_ball_animations),
            self.stroke_animation,
            self.ball_animations,
            Wait(trailing_buffer),
        )


visual = SystemController()
