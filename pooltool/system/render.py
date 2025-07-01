from __future__ import annotations

from attrs import define
from direct.interval.IntervalGlobal import Func, Parallel, Sequence, Wait
from panda3d.direct import HideInterval, ShowInterval

from pooltool.ani.globals import Global
from pooltool.evolution.continuous import continuize
from pooltool.objects.ball.render import BallRender
from pooltool.objects.cue.render import CueRender
from pooltool.objects.table.render import TableRender
from pooltool.system.datatypes import System, multisystem
from pooltool.utils.strenum import StrEnum, auto


class PlaybackMode(StrEnum):
    LOOP = auto()
    SINGLE = auto()
    PARALLEL = auto()


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


@define
class ParallelModeManager:
    """Manages parallel visualization of multiple systems."""

    parallel_systems: dict[int, SystemRender]
    is_active: bool = False

    @classmethod
    def create(cls) -> ParallelModeManager:
        return cls(parallel_systems={}, is_active=False)

    def setup(self, controller: SystemController, current_system: SystemRender) -> None:
        if self.is_active:
            return

        controller.reset_animation(force_pause=True)

        self.is_active = True
        self.parallel_systems = {}

        current_index = multisystem.active_index
        assert current_index is not None

        # Create the SystemRender objects for each eligible system in multisystem.
        for idx, system in enumerate(multisystem):
            if not system.simulated and idx != multisystem.max_index:
                continue

            if idx == current_index:
                self.parallel_systems[idx] = current_system
                continue

            if system.simulated and not system.continuized:
                continuize(system, inplace=True)

            self.parallel_systems[idx] = SystemRender.from_system(system)

        self._build_animations(controller, current_index)

    def exit(self, controller: SystemController) -> SystemRender | None:
        """Exit parallel mode and return the active system."""
        if not self.is_active:
            return None

        was_playing = not controller.paused

        # Clear animation before removing nodes.
        controller.reset_animation(force_pause=True)

        active_idx = multisystem.active_index
        assert active_idx is not None, "Unknown control flow"

        # Remove all non-active systems
        for idx, sys_render in self.parallel_systems.items():
            if idx != active_idx:
                for ball in sys_render.balls.values():
                    ball.remove_nodes()
                sys_render.cue.remove_nodes()

        active_system = self.parallel_systems[active_idx]

        self.parallel_systems = {}
        self.is_active = False

        # Rebuild animation for active system only.
        controller.build_shot_animation()

        if was_playing:
            controller.animate(PlaybackMode.LOOP)

        return active_system

    def update_active_system(self, new_index: int) -> None:
        """Update which system is active in parallel mode"""
        if not self.is_active:
            return

        self._update_system_opacities(new_index)

    def _build_animations(
        self, controller: SystemController, active_index: int
    ) -> None:
        """Build synchronized animations for parallel visualization."""
        if not self.is_active:
            return

        # Render cues and balls from all systems.
        for system_render in self.parallel_systems.values():
            for ball in system_render.balls.values():
                if not ball.rendered:
                    ball.render()
                    ball.set_alpha(0.3)
            if not system_render.cue.rendered:
                system_render.cue.render()

        self._update_system_opacities(active_index)

        # Build all ball animations
        all_ball_animations = Parallel()
        for system_render in self.parallel_systems.values():
            for ball in system_render.balls.values():
                # Set quaternions for animation.
                ball.set_quats(ball._ball.history_cts)

                ball_animation = ball.get_playback_sequence(
                    playback_speed=controller.playback_speed
                )
                if len(ball_animation) > 0:
                    all_ball_animations.append(ball_animation)

        # Build stroke animation only for active system
        active_system_render = self.parallel_systems[active_index]
        stroke_animation = Sequence(
            ShowInterval(active_system_render.cue.get_node("cue_stick")),
            active_system_render.cue.get_stroke_sequence(),
            HideInterval(active_system_render.cue.get_node("cue_stick")),
        )

        # Combine stroke animation with all ball animations.
        controller.stroke_animation = stroke_animation
        controller.ball_animations = all_ball_animations
        controller.shot_animation = Sequence(
            Func(controller.restart_ball_animations),
            stroke_animation,
            all_ball_animations,
            Wait(duration=0.5),  # Add a small downtime buffer at the end.
        )

    def _update_system_opacities(self, active_index: int) -> None:
        """Update opacity for all rendered systems"""
        if not self.is_active:
            return

        for idx, system_render in self.parallel_systems.items():
            if idx == active_index:
                for ball in system_render.balls.values():
                    ball.set_alpha(1.0)
                system_render.cue.show_nodes()
            else:
                for ball in system_render.balls.values():
                    ball.set_alpha(0.3)
                system_render.cue.hide_nodes()

    def rebuild_animations_for_speed_change(
        self, controller: SystemController, active_index: int, new_speed: float
    ) -> None:
        """Rebuilds animations with new playback speed."""
        if not self.is_active:
            return

        for idx in self.parallel_systems:
            system = multisystem[idx]
            if system.simulated:
                continuize(system, dt=0.01 * new_speed, inplace=True)

        self._build_animations(controller, active_index)


class SystemController:
    def __init__(self) -> None:
        self.system: SystemRender
        self.stroke_animation: Sequence = Sequence()
        self.ball_animations: Parallel = Parallel()
        self.shot_animation: Sequence = Sequence()
        self.paused: bool = True
        self.playback_speed: float = 1
        self.playback_mode: PlaybackMode = PlaybackMode.SINGLE
        self.parallel_manager: ParallelModeManager = ParallelModeManager.create()

    @property
    def table(self) -> TableRender:
        return self.system.table

    @property
    def balls(self) -> dict[str, BallRender]:
        return self.system.balls

    @property
    def cue(self) -> CueRender:
        return self.system.cue

    @property
    def is_parallel_mode(self) -> bool:
        return self.parallel_manager.is_active

    def attach_system(self, system: System) -> None:
        """Teardown existing system and attach new system"""
        was_in_parallel_mode = self.parallel_manager.is_active

        if hasattr(self, "system"):
            # Exit parallel mode if active to avoid issues during transition
            if self.parallel_manager.is_active:
                returned_system = self.parallel_manager.exit(self)
                if returned_system:
                    self.system = returned_system
            self.teardown()

        self.system = SystemRender.from_system(system)

        if was_in_parallel_mode:
            self.parallel_manager.setup(self, self.system)

    def reset_animation(self, force_pause: bool = True) -> None:
        """Set objects to initial states, pause, and remove animations

        Args:
            force_pause:
                If True, self.paused is set to True, otherwise its state is left
                unaffected.
        """
        if not self.parallel_manager.is_active:
            self.playback_mode = PlaybackMode.SINGLE

        if force_pause:
            self.paused = True

        self.shot_animation.clearToInitial()
        self.stroke_animation.clearToInitial()
        self.ball_animations.clearToInitial()

        self.stroke_animation = Sequence()
        self.ball_animations = Parallel()
        self.shot_animation = Sequence()

    @property
    def animation_finished(self):
        """Returns whether or not the animation is finished.

        Returns:
            True if the animation has stopped and is in the final state of its sequence.
            A paused animation returns False. The animation is never finished if it's
            playing in a loop or in parallel mode.
        """
        # Never consider animation finished in LOOP mode or in parallel mode
        if self.playback_mode == PlaybackMode.LOOP or self.parallel_manager.is_active:
            return False

        return not self.shot_animation.isPlaying() and not self.paused

    def buildup(self) -> None:
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
        """Sets the playback mode."""
        self.playback_mode = mode

    def animate(self, mode: PlaybackMode | None = None):
        """Starts the animation."""

        assert len(self.shot_animation), "Must populate shot_animation"

        if mode is not None:
            self.playback(mode)

        # In parallel mode, always use LOOP behavior
        if self.playback_mode == PlaybackMode.LOOP or self.parallel_manager.is_active:
            self.shot_animation.loop()
        elif self.playback_mode == PlaybackMode.SINGLE:
            self.shot_animation.start()
        else:
            raise NotImplementedError()

        self.paused = False

    def restart_animation(self) -> None:
        """Sets the animation to t=0.

        This is the full shot animation, including stroke.
        """
        # If animation is completed (in final state), clear it before setting time. This
        # avoids stdout warnings from Panda3D like:
        # :interval(warning): CLerpNodePathInterval::priv_step() called for LerpPosQuatInterval-1 in state final.
        if not self.shot_animation.isPlaying() and not self.paused:
            self.shot_animation.clearToInitial()

        self.shot_animation.set_t(0)

    def restart_ball_animations(self) -> None:
        """Sets the ball animations to t=0."""
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
        was_paused = self.paused

        self.reset_animation(force_pause=False)
        self.playback_speed *= factor

        if self.parallel_manager.is_active:
            assert multisystem.active_index is not None
            self.parallel_manager.rebuild_animations_for_speed_change(
                self, multisystem.active_index, self.playback_speed
            )
        else:
            continuize(multisystem.active, dt=0.01 * self.playback_speed, inplace=True)
            self.build_shot_animation()

        self.shot_animation.setPlayRate(factor * self.shot_animation.getPlayRate())

        self.animate(PlaybackMode.LOOP)

        if was_paused:
            self.pause_animation()

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
        self.parallel_manager.setup(self, self.system)

    def exit_parallel_mode(self) -> None:
        """Exit parallel visualization mode"""
        returned_system = self.parallel_manager.exit(self)
        if returned_system:
            self.system = returned_system

    def update_parallel_active(self, new_index: int) -> None:
        """Update which system is active in parallel mode"""
        self.parallel_manager.update_active_system(new_index)

    def build_shot_animation(
        self,
        animate_stroke: bool = True,
        trailing_buffer: float = 0.0,
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
            self.stroke_animation = Sequence()
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
