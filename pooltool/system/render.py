from __future__ import annotations

from typing import Dict, Optional

from attrs import define
from direct.interval.IntervalGlobal import Func, Parallel, Sequence, Wait
from panda3d.direct import HideInterval, ShowInterval

from pooltool.ani.globals import Global
from pooltool.evolution.continuize import continuize
from pooltool.objects.ball.render import BallRender
from pooltool.objects.cue.render import CueRender
from pooltool.objects.table.render import TableRender
from pooltool.system.datatypes import System, multisystem
from pooltool.utils.strenum import StrEnum, auto


@define
class SystemRender:
    balls: Dict[str, BallRender]
    table: TableRender
    cue: CueRender

    @staticmethod
    def from_system(system: System) -> SystemRender:
        # If you're making a SystemRender from your system that has already been
        # simulated, you want it continuized
        if system.simulated and not system.continuized:
            continuize(system, inplace=True)

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
        self.paused: bool = True
        self.playback_speed: float = 1
        self.playback_mode: PlaybackMode = PlaybackMode.SINGLE

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
        """Teardown existing system and attach new system"""
        if hasattr(self, "system"):
            self.teardown()
        self.system = SystemRender.from_system(system)

    def reset_animation(self, reset_pause: bool = True) -> None:
        """Set objects to initial states, pause, and remove animations"""
        self.playback_mode = PlaybackMode.SINGLE

        if reset_pause:
            self.paused = True

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
        self.playback_speed = 1

        # FIXME See the FIXME in teardown for an explanation
        if not any(
            child.name == "table" for child in Global.render.find("scene").getChildren()
        ):
            self.system.table.render()

        for ball in self.system.balls.values():
            ball.render()
            ball.reset_angular_integration()
        self.system.cue.render()

    def teardown(self) -> None:
        """Stop animations and remove all nodes"""
        self.reset_animation()

        for ball in self.system.balls.values():
            ball.remove_nodes()

        self.system.cue.remove_nodes()

        # FIXME Table has lingering references that prevent it from being unrendered.
        # And when teardown and buildup are called, the shading gets weird and the balls
        # disappear. I think it has to do with lingering references in environment.py.
        # For now, the fix is to simply not remove the table nodes in `teardown`, and
        # only render them once in `buildup`
        # self.system.table.remove_nodes()

    def playback(self, mode: PlaybackMode) -> None:
        """Set the playback mode (does not affect pause status)"""
        self.playback_mode = mode

    def animate(self, mode: Optional[PlaybackMode] = None):
        """Start the animation"""

        assert len(self.shot_animation), "Must populate shot_animation"

        if mode is not None:
            self.playback(mode)

        if self.playback_mode == PlaybackMode.LOOP:
            self.shot_animation.loop()
        elif self.playback_mode == PlaybackMode.SINGLE:
            self.shot_animation.start()
        else:
            raise NotImplementedError()

        self.paused = False

    def restart_animation(self) -> None:
        """Set the animation to t=0"""
        self.shot_animation.set_t(0)

    def restart_ball_animations(self) -> None:
        self.ball_animations.set_t(0)

    def toggle_pause(self) -> None:
        if self.shot_animation.isPlaying():
            self.pause_animation()
        else:
            self.resume_animation()

    def slow_down(self):
        self.change_speed(0.5)

    def speed_up(self):
        self.change_speed(2.0)

    def change_speed(self, factor):
        curr_time = self.shot_animation.get_t()

        self.reset_animation(reset_pause=False)
        self.playback_speed *= factor

        # Recontinuize to adjust for change in speed
        continuize(multisystem.active, dt=0.01 * self.playback_speed, inplace=True)

        self.build_shot_animation()

        self.shot_animation.setPlayRate(factor * self.shot_animation.getPlayRate())

        if self.paused:
            self.animate(PlaybackMode.LOOP)
            self.pause_animation()
        else:
            self.animate(PlaybackMode.LOOP)

        self.shot_animation.set_t(curr_time / factor)

    def offset_time(self, dt) -> None:
        old_t = self.shot_animation.get_t()
        new_t = max(0, min(old_t + dt, self.shot_animation.duration))
        self.shot_animation.set_t(new_t)

    def pause_animation(self) -> None:
        self.shot_animation.pause()
        self.paused = True

    def resume_animation(self) -> None:
        self.shot_animation.resume()
        self.paused = False

    def advance_to_end_of_stroke(self):
        """Sets shot animation time to immediately after the stroke animation"""
        if not len(self.stroke_animation):
            return

        self.shot_animation.set_t(self.stroke_animation.get_duration())

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
