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
    PARALLEL = auto()


class SystemController:
    def __init__(self) -> None:
        self.system: SystemRender
        self.stroke_animation: Sequence = Sequence()
        self.ball_animations: Parallel = Parallel()
        self.shot_animation: Sequence = Sequence()
        self.paused: bool = True
        self.playback_speed: float = 1
        self.playback_mode: PlaybackMode = PlaybackMode.SINGLE
        self.parallel_systems: Dict[int, SystemRender] = {}
        self.is_parallel_mode: bool = False

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
        # Store parallel mode state before teardown
        was_in_parallel_mode = self.is_parallel_mode

        if hasattr(self, "system"):
            # Exit parallel mode if active to avoid issues during transition
            if self.is_parallel_mode:
                self.exit_parallel_mode()
            self.teardown()

        self.system = SystemRender.from_system(system)

        # If we were in parallel mode before, re-enter it
        if was_in_parallel_mode:
            self.setup_parallel_mode()

    def reset_animation(self, reset_pause: bool = True) -> None:
        """Set objects to initial states, pause, and remove animations"""
        if not self.is_parallel_mode:
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
        paused. The animation is never finished if it's playing in a loop or in parallel mode.
        """
        # Never consider animation finished in LOOP mode or in parallel mode
        if self.playback_mode == PlaybackMode.LOOP or self.is_parallel_mode:
            return False

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

        # In parallel mode, always use LOOP behavior
        if self.playback_mode == PlaybackMode.LOOP or self.is_parallel_mode:
            self.shot_animation.loop()
        elif self.playback_mode == PlaybackMode.SINGLE:
            self.shot_animation.start()
        else:
            raise NotImplementedError()

        self.paused = False

    def restart_animation(self) -> None:
        """Set the animation to t=0"""
        # If animation is completed (in final state), clear it before setting time. This
        # avoids stdout warnings from Panda3D like:
        # :interval(warning): CLerpNodePathInterval::priv_step() called for LerpPosQuatInterval-1 in state final.
        if not self.shot_animation.isPlaying() and not self.paused:
            self.shot_animation.clearToInitial()

        self.shot_animation.set_t(0)

    def restart_ball_animations(self) -> None:
        # If animation is completed (in final state), clear it before setting time. This
        # avoids stdout warnings from Panda3D like:
        # :interval(warning): CLerpNodePathInterval::priv_step() called for LerpPosQuatInterval-1 in state final.
        if not self.ball_animations.isPlaying() and not self.paused:
            self.ball_animations.clearToInitial()

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

        # Handle speed change differently based on mode
        if self.is_parallel_mode:
            # Update all systems in parallel mode
            for idx, sys_render in self.parallel_systems.items():
                system = multisystem[idx]
                if system.simulated:
                    continuize(system, dt=0.01 * self.playback_speed, inplace=True)

            # Rebuild parallel animations with new speed
            self._build_parallel_animations(multisystem.active_index)
        else:
            # Just update the active system
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

    def setup_parallel_mode(self) -> None:
        """Setup all systems for parallel visualization with synchronized animations"""
        if self.is_parallel_mode:
            return

        # First, clear any existing animations
        self.reset_animation(reset_pause=True)

        self.is_parallel_mode = True
        self.parallel_systems = {}

        # Store current system
        current_index = multisystem.active_index

        # Create SystemRender for each system in multisystem
        for idx, system in enumerate(multisystem):
            # Skip if system doesn't have events (unsimulated)
            if len(system.events) == 0 and idx != len(multisystem) - 1:
                continue

            # If this is the active system, we already have it
            if idx == current_index:
                self.parallel_systems[idx] = self.system
                continue

            # Create SystemRender for this system
            if system.simulated and not system.continuized:
                continuize(system, inplace=True)

            sys_render = SystemRender.from_system(system)
            self.parallel_systems[idx] = sys_render

        # Build animations for all systems
        self._build_parallel_animations(current_index)

    def _build_parallel_animations(self, active_index: int) -> None:
        """Build synchronized animations for parallel visualization"""
        if not self.is_parallel_mode:
            return

        # First, render all systems with appropriate opacity
        for idx, sys_render in self.parallel_systems.items():
            if idx == active_index:
                # Set active system to full opacity
                for ball in sys_render.balls.values():
                    if not ball.rendered:
                        ball.render()
                    ball.set_alpha(1.0)
            else:
                # Render with reduced opacity
                for ball_id, ball in sys_render.balls.items():
                    if not ball.rendered:
                        ball.render()
                    ball.set_alpha(0.3)

                # Hide cue for non-active systems
                sys_render.cue.hide_nodes()

        # Now build animations for all systems and combine them
        all_ball_animations = Parallel()
        longest_duration = 0

        # First, build all ball animations and find the longest duration
        for idx, sys_render in self.parallel_systems.items():
            # For each ball in this system
            for ball_id, ball in sys_render.balls.items():
                # Set quaternions for animation
                ball.set_quats(ball._ball.history_cts)

                # Get ball animation
                ball_animation = ball.get_playback_sequence(
                    playback_speed=self.playback_speed
                )
                if len(ball_animation) > 0:
                    all_ball_animations.append(ball_animation)

                    # Check if this animation is longer than current max
                    if ball_animation.getDuration() > longest_duration:
                        longest_duration = ball_animation.getDuration()

        # Now, build stroke animation only for active system
        active_sys = self.parallel_systems[active_index]
        stroke_animation = Sequence(
            ShowInterval(active_sys.cue.get_node("cue_stick")),
            active_sys.cue.get_stroke_sequence(),
            HideInterval(active_sys.cue.get_node("cue_stick")),
        )

        # Combine stroke animation with all ball animations
        self.stroke_animation = stroke_animation
        self.ball_animations = all_ball_animations
        self.shot_animation = Sequence(
            Func(self.restart_ball_animations),
            stroke_animation,
            all_ball_animations,
            Wait(0.5),  # Add a small buffer at the end
        )

    def _render_parallel_systems(self, active_index: int) -> None:
        """Update opacity for all rendered systems"""
        if not self.is_parallel_mode:
            return

        # Update opacity for all systems
        for idx, sys_render in self.parallel_systems.items():
            if idx == active_index:
                # Set active system to full opacity
                for ball in sys_render.balls.values():
                    ball.set_alpha(1.0)
                sys_render.cue.show_nodes()
            else:
                # Set non-active systems to reduced opacity
                for ball in sys_render.balls.values():
                    ball.set_alpha(0.3)
                sys_render.cue.hide_nodes()

    def exit_parallel_mode(self) -> None:
        """Exit parallel visualization mode"""
        if not self.is_parallel_mode:
            return

        # Store animation state
        was_playing = not self.paused
        current_time = 0
        if len(self.shot_animation) > 0:
            current_time = self.shot_animation.get_t()

        # Pause the animation to prevent errors during transition
        self.pause_animation()

        # Clear the animation before removing nodes
        self.reset_animation(reset_pause=True)

        # Remove all non-active systems
        active_idx = multisystem.active_index
        for idx, sys_render in self.parallel_systems.items():
            if idx != active_idx:
                for ball in sys_render.balls.values():
                    ball.remove_nodes()
                sys_render.cue.remove_nodes()

        # Keep reference to active system
        active_system = self.parallel_systems.get(active_idx)
        self.system = active_system  # Ensure system is still set properly

        # Reset state
        self.parallel_systems = {}
        self.is_parallel_mode = False

        # Rebuild animation for the active system only
        self.build_shot_animation()

        # Restore animation state
        if was_playing:
            self.animate(PlaybackMode.LOOP)
            # Try to restore animation time position if possible
            if current_time > 0 and current_time <= self.shot_animation.getDuration():
                self.shot_animation.set_t(current_time)

    def update_parallel_active(self, new_index: int) -> None:
        """Update which system is active in parallel mode"""
        if not self.is_parallel_mode:
            return

        # Update system opacities
        self._render_parallel_systems(new_index)

        # We don't need to rebuild animations since we're just changing opacities
        # The animations should continue playing from where they were

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

        if not self.system.cue.rendered:
            self.system.cue.render()

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
