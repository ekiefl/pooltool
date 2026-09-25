from __future__ import annotations

from direct.interval.IntervalGlobal import Parallel, Sequence, Wait
from panda3d.direct import HideInterval, ShowInterval

import pooltool.ani.tasks as tasks
from pooltool.ani.environment import Environment
from pooltool.ani.hud import hud
from pooltool.ani.playback import PlaybackState, ShotPlayback
from pooltool.objects.ball.render import BallRender
from pooltool.objects.cue.render import CueRender, StrokeRecording
from pooltool.objects.table.render import TableRender
from pooltool.system.datatypes import MultiSystem, multisystem
from pooltool.system.render import SystemRender
from pooltool.utils.strenum import StrEnum, auto


class SceneComponents(StrEnum):
    TABLE = auto()
    CUE = auto()
    BALLS = auto()
    ENVIRONMENT = auto()


PARALLEL_TRAILING_BUFFER = 0.5
"""Seconds of downtime after the balls settle when several systems play together."""

PARALLEL_INACTIVE_ALPHA = 0.3
"""Opacity of the balls of a system playing alongside the active one."""

TICK_TASK = "shot_playback_tick"

RENDER_DT = 0.01
"""Simulation seconds between render samples at unit playback speed."""


class SceneController:
    """Owns which systems are rendered and the playback of their shot animation

    The systems rendered are drawn from ``multisystem`` and kept in ``systems``, keyed
    by their index in it. One of them, ``active``, owns the table and the environment
    and is drawn at full opacity. Any others play alongside it at reduced opacity,
    which is parallel mode.

    While a playback exists, the visibility of each cue is a function of the playback
    time: hidden except while its stroke plays. Modes show and hide the cue only
    when there is no playback.

    The stroke a player traced for a shot is kept in ``strokes``, keyed like
    ``systems``, so it outlives the cue render it was traced on and replays after
    switching shots.
    """

    def __init__(self, multisystem: MultiSystem) -> None:
        self.multisystem = multisystem
        self.systems: dict[int, SystemRender] = {}
        self.strokes: dict[int, StrokeRecording] = {}
        self.active: int = 0
        self.environment: Environment = Environment()
        self.playback: ShotPlayback | None = None
        self.playback_speed: float = 1

    @property
    def system(self) -> SystemRender:
        return self.systems[self.active]

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
        return len(self.systems) > 1

    def attach_system(self, index: int) -> None:
        """Make the system at ``index`` in ``multisystem`` the only one rendered"""
        self.systems = {index: SystemRender.from_system(self.multisystem[index])}
        self.active = index

    def record_stroke(self, stroke: StrokeRecording) -> None:
        """Keep ``stroke`` as the stroke of the active shot"""
        self.strokes[self.multisystem.active_index] = stroke

    def reset_animation(self) -> None:
        """Set objects to initial states and remove the animation"""
        if self.playback is None:
            return

        self.playback.destroy()
        self.playback = None

    def render_table(self) -> None:
        self.system.table.render()

    def render_balls(self) -> None:
        for ball in self.system.balls.values():
            ball.render()
            ball.reset_angular_integration()

    def render_cue(self) -> None:
        self.system.cue.render()

    def unrender_table(self) -> None:
        self.system.table.remove_nodes()

    def unrender_balls(self) -> None:
        for ball in self.system.balls.values():
            ball.remove_nodes()

    def unrender_cue(self) -> None:
        self.system.cue.remove_nodes()

    def buildup(self, components: list[SceneComponents] | None = None) -> None:
        components = list(SceneComponents) if components is None else components
        self.playback_speed = 1

        if SceneComponents.TABLE in components:
            self.render_table()
        if SceneComponents.BALLS in components:
            self.render_balls()
        if SceneComponents.CUE in components:
            self.render_cue()
        if SceneComponents.ENVIRONMENT in components:
            self.environment.init(self.system.table._table)

        tasks.add(self._tick_task, TICK_TASK)

    def _tick_task(self, task):
        if self.playback is not None:
            self.playback.tick()
        return task.cont

    def teardown(self, components: list[SceneComponents] | None = None) -> None:
        """Stop the animation, leave parallel mode, and remove the components' nodes"""
        components = list(SceneComponents) if components is None else components
        self.reset_animation()
        tasks.remove(TICK_TASK)
        self._unrender_inactive_systems()

        if SceneComponents.TABLE in components:
            self.unrender_table()
        if SceneComponents.BALLS in components:
            self.unrender_balls()
        if SceneComponents.CUE in components:
            self.unrender_cue()
        if SceneComponents.ENVIRONMENT in components:
            self.environment.teardown()

    def switch_rendered_system(self, multisystem_idx: int) -> None:
        """Convenience method for switching which system in ``multisystem`` is rendered."""
        components_to_refresh = [SceneComponents.CUE, SceneComponents.BALLS]
        self.teardown(components_to_refresh)
        self.multisystem.set_active(multisystem_idx)
        self.attach_system(self.multisystem.active_index)
        self.buildup(components_to_refresh)

    def change_speed(self, factor: float) -> None:
        """Rebuild the animation at a new speed, keeping its time and entering loop mode"""
        self.playback_speed *= factor
        self.rebuild_animation()

        assert self.playback is not None
        self.playback.loop = True

    def enter_parallel_mode(self) -> None:
        """Render every eligible system in ``multisystem`` and play them together

        A system is eligible if it is simulated, or if it is the newest one, which in
        the game is the shot not yet taken. Playback keeps its time and state, and
        loops.
        """
        if self.is_parallel_mode:
            return

        for idx, system in enumerate(self.multisystem):
            if idx == self.active:
                continue
            if not system.simulated and idx != self.multisystem.max_index:
                continue

            system_render = SystemRender.from_system(system)
            for ball in system_render.balls.values():
                ball.render()
            system_render.cue.render()
            self.systems[idx] = system_render

        self._update_opacities()
        self.rebuild_animation()

        assert self.playback is not None
        self.playback.loop = True

    def exit_parallel_mode(self) -> None:
        """Remove every system but the active one and rebuild its animation"""
        if not self.is_parallel_mode:
            return

        self._unrender_inactive_systems()
        self._update_opacities()
        self.rebuild_animation()

    def set_parallel_active(self, index: int) -> None:
        """Bring the rendered system at ``index`` to full opacity"""
        assert index in self.systems
        self.active = index
        self._update_opacities()

    def _unrender_inactive_systems(self) -> None:
        for idx in list(self.systems):
            if idx == self.active:
                continue
            system_render = self.systems.pop(idx)
            for ball in system_render.balls.values():
                ball.remove_nodes()
            system_render.cue.remove_nodes()

    def _update_opacities(self) -> None:
        for idx, system_render in self.systems.items():
            if idx == self.active:
                for ball in system_render.balls.values():
                    ball.set_alpha(1.0)
                system_render.cue.show_node("cue_stick_model")
            else:
                for ball in system_render.balls.values():
                    ball.set_alpha(PARALLEL_INACTIVE_ALPHA)
                system_render.cue.hide_node("cue_stick_model")

    def switch_to_shot(self, shot_index: int) -> None:
        """Switch to a different system in the system collection

        Outside parallel mode the shot's animation is built and played in loop mode,
        paused if the animation being left was not playing.
        """
        self.multisystem.set_active(shot_index)

        if self.is_parallel_mode:
            self.set_parallel_active(shot_index)
            return

        state = PlaybackState.STOPPED if self.playback is None else self.playback.state
        self.reset_animation()

        self.switch_rendered_system(self.multisystem.active_index)
        system_cue = self.multisystem.active.cue
        hud.update_cue(
            system_cue, self.multisystem.active.balls[system_cue.cue_ball_id]
        )

        # Changing to a different shot is considered advanced maneuvering, so we enter
        # loop mode
        self.build_shot_animation()

        assert self.playback is not None
        self.playback.loop = True
        self.playback.play()

        if state is not PlaybackState.PLAYING:
            self.playback.pause()

    def rebuild_animation(self) -> None:
        """Rebuild the shot animation, keeping the current time, state, and loop mode"""
        playback = self.playback
        if playback is None:
            self.build_shot_animation()
            return

        t, state, loop = playback.t, playback.state, playback.loop
        self.reset_animation()
        self.build_shot_animation()

        assert self.playback is not None
        self.playback.loop = loop

        if state is PlaybackState.PLAYING:
            self.playback.play()
        elif state is PlaybackState.PAUSED:
            self.playback.play()
            self.playback.pause()

        self.playback.seek(t)

    def build_shot_animation(
        self,
        animate_stroke: bool = True,
        trailing_buffer: float = 0.0,
    ) -> None:
        """Build the shot animation over the rendered systems

        Every system's stroke is in the tree, delayed so that all strikes land at
        t=0, and its balls hold their initial state until then. Each cue is hidden
        except while its stroke plays. The playback starts stopped, in single-pass
        mode. In parallel mode the trailing buffer is ``PARALLEL_TRAILING_BUFFER``.

        Args:
            animate_stroke:
                If False, no strokes are built and the cues stay hidden.
            trailing_buffer:
                Seconds of downtime appended after the balls come to rest.
        """
        if self.is_parallel_mode:
            trailing_buffer = PARALLEL_TRAILING_BUFFER

        strokes: dict[int, Sequence] = {}
        for idx, system_render in self.systems.items():
            if not system_render.cue.rendered:
                system_render.cue.render()

            system_render.cue.hide()

            if not animate_stroke:
                strokes[idx] = Sequence()
                continue

            cue_stick = system_render.cue.get_node("cue_stick")
            stroke = self.strokes.get(idx, StrokeRecording())
            strokes[idx] = Sequence(
                ShowInterval(cue_stick),
                system_render.cue.get_stroke_sequence(stroke),
                HideInterval(cue_stick),
            )

        hold = max(stroke.get_duration() for stroke in strokes.values())
        stroke_animation = Parallel(
            *(
                Sequence(Wait(hold - stroke.get_duration()), stroke)
                for stroke in strokes.values()
            )
        )

        # This takes ~90% of this method's execution time
        ball_animations = Parallel()
        for system_render in self.systems.values():
            system_render.resample(RENDER_DT * self.playback_speed)
            for ball in system_render.balls.values():
                if not ball.rendered:
                    ball.render()

                ball_animation = ball.get_playback_sequence(self.playback_speed, hold)
                if len(ball_animation) > 0:
                    ball_animations.append(ball_animation)

        self.playback = ShotPlayback.from_parts(
            stroke_animation,
            ball_animations,
            trailing_buffer=trailing_buffer,
            loop=False,
            speed=self.playback_speed,
            events={idx: self.multisystem[idx].events for idx in self.systems},
        )


visual = SceneController(multisystem)
