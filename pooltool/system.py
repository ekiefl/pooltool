#! /usr/bin/env python

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from direct.interval.IntervalGlobal import Func, Parallel, Sequence, Wait
from panda3d.direct import HideInterval, ShowInterval

import pooltool.ani as ani
import pooltool.physics as physics
import pooltool.utils as utils
from pooltool.error import ConfigError, SimulateError
from pooltool.events import Event, EventType, filter_ball
from pooltool.objects.ball import Ball, BallHistory, BallState
from pooltool.objects.cue import Cue, cue_from_dict
from pooltool.objects.table import Table
from pooltool.utils.strenum import StrEnum, auto


class PlaybackMode(StrEnum):
    LOOP = auto()
    SINGLE = auto()


class SystemRender:
    def __init__(self):
        self.reset_animation()

    def reset_animation(self):
        self.shot_animation = None
        self.ball_animations = None
        self.stroke_animation = None
        self.user_stroke = False
        self.playback_speed = 1

    def init_shot_animation(
        self, shot, animate_stroke=True, trailing_buffer=0, leading_buffer=0
    ):
        if not shot.continuized:
            # playback speed / fps * 2.0 is basically the sweetspot for creating smooth
            # interpolations that capture motion. Any more is wasted computation and any
            # less and the interpolation starts to look bad.
            if self.playback_speed > 0.99:
                shot.continuize(
                    dt=self.playback_speed / ani.settings["graphics"]["fps"] * 2.5
                )
            else:
                shot.continuize(
                    dt=self.playback_speed / ani.settings["graphics"]["fps"] * 1.5
                )

        if self.ball_animations is None:
            # This takes ~90% of this method's execution time
            self.ball_animations = Parallel()
            for ball in shot.balls.values():
                if not ball.render_obj.rendered:
                    ball.render_obj.render(ball)
                ball.render_obj.set_playback_sequence(
                    ball, playback_speed=self.playback_speed
                )
                self.ball_animations.append(ball.render_obj.playback_sequence)

        if self.user_stroke and animate_stroke:
            # There exists a stroke trajectory, and animating the stroke has been
            # requested
            shot.cue.render_obj.set_stroke_sequence()
            self.stroke_animation = Sequence(
                ShowInterval(shot.cue.render_obj.get_node("cue_stick")),
                shot.cue.render_obj.stroke_sequence,
                HideInterval(shot.cue.render_obj.get_node("cue_stick")),
            )
            self.shot_animation = Sequence(
                Func(self.restart_ball_animations),
                self.stroke_animation,
                self.ball_animations,
                Wait(trailing_buffer),
            )
        else:
            shot.cue.render_obj.hide_nodes()
            self.stroke_animation = None
            self.shot_animation = Sequence(
                Func(self.restart_ball_animations),
                self.ball_animations,
                Wait(trailing_buffer),
            )

    def start_animation(self, playback_mode: PlaybackMode):
        if self.shot_animation is None:
            raise Exception("First call SystemRender.init_shot_animation()")

        if playback_mode == PlaybackMode.SINGLE:
            self.shot_animation.start()
        elif playback_mode == PlaybackMode.LOOP:
            self.shot_animation.loop()

    def restart_animation(self):
        self.shot_animation.set_t(0)

    def restart_ball_animations(self):
        self.ball_animations.set_t(0)

    def clear_animation(self, shot):
        if self.shot_animation is not None:
            self.shot_animation.clearToInitial()
            self.shot_animation = None
            self.ball_animations = None
            self.stroke_animation = None

        for ball in shot.balls.values():
            if ball.render_obj.playback_sequence is not None:
                ball.render_obj.playback_sequence.pause()
                ball.render_obj.playback_sequence = None

    def toggle_pause(self):
        if self.shot_animation.isPlaying():
            self.pause_animation()
        else:
            self.resume_animation()

    def offset_time(self, dt):
        old_t = self.shot_animation.get_t()
        new_t = max(0, min(old_t + dt, self.shot_animation.duration))
        self.shot_animation.set_t(new_t)

    def pause_animation(self):
        self.shot_animation.pause()

    def resume_animation(self):
        self.shot_animation.resume()

    def teardown(self, shot):
        self.clear_animation(shot)
        for ball in shot.balls.values():
            ball.render_obj.remove_nodes()
        shot.cue.render_obj.remove_nodes()

    def buildup(self, shot):
        self.clear_animation(shot)
        for ball in shot.balls.values():
            ball.render_obj.render(ball)
            ball.render_obj.reset_angular_integration()
        shot.cue.render_obj.render()
        shot.cue.render_obj.init_focus(shot.cue.cueing_ball)


class MultiSystemRender:
    def __init__(self):
        self.shot_animation = None
        self.playback_speed = 1.0
        self.parallel = False
        self.paused = False

    @property
    def animation_finished(self):
        """Returns whether or not the animation is finished

        Returns true if the animation has stopped and it's not because the game has been
        paused. The animation is never finished if it's playing in a loop.
        """

        if not self.shot_animation.isPlaying() and not self.paused:
            return True
        else:
            return False

    def set_animation(self, multisystem):
        if self.parallel:
            self.shot_animation = Parallel()

            # `max_dur` is the shot duration of the longest shot in the collection. All
            # shots beside this one will have a buffer appended where the balls stay in
            # their final state until the last shot finishes.
            max_dur = max([shot.events[-1].time for shot in multisystem])

            # FIXME `leading_buffer` should be utilized here to sync up all shots that
            # have cue trajectories such that the ball animations all start at the
            # moment of the stick-ball collision
            pass

            for shot in multisystem:
                shot_dur = shot.events[-1].time
                shot.render_obj.init_shot_animation(
                    shot,
                    trailing_buffer=max_dur - shot_dur,
                    leading_buffer=0,
                )
                self.shot_animation.append(shot.render_obj.shot_animation)
        else:
            if not multisystem.active:
                raise ConfigError(
                    "MultiSystemRender.set_animation :: multisystem.active not set"
                )
            multisystem.active.render_obj.init_shot_animation(multisystem.active)
            self.shot_animation = multisystem.active.render_obj.shot_animation

    def start_animation(self, playback_mode: PlaybackMode):
        if playback_mode == PlaybackMode.SINGLE:
            self.shot_animation.start()
        elif playback_mode == PlaybackMode.LOOP:
            self.shot_animation.loop()

    def skip_stroke(self, multisystem):
        stroke = multisystem.active.render_obj.stroke_animation
        if stroke is not None:
            self.shot_animation.set_t(stroke.get_duration())

    def restart_animation(self):
        self.shot_animation.set_t(0)

    def clear_animation(self, multisystem):
        if self.parallel:
            for shot in multisystem:
                shot.render_obj.clear_animation(shot)
        else:
            multisystem.active.render_obj.clear_animation(multisystem.active)

        if self.shot_animation is not None:
            self.shot_animation.clearToInitial()
            self.shot_animation.pause()
            self.shot_animation = None

    def toggle_parallel(self, multisystem):
        self.clear_animation(multisystem)

        if self.parallel:
            for shot in multisystem:
                shot.render_obj.teardown(shot)
            multisystem.active.render_obj.buildup(multisystem.active)
            self.parallel = False
            self.set_animation(multisystem)
        else:
            multisystem.active.render_obj.teardown(multisystem.active)
            for shot in multisystem:
                shot.render_obj.buildup(shot)
            self.parallel = True
            self.set_animation(multisystem)

        if not self.paused:
            self.start_animation(PlaybackMode.LOOP)

    def toggle_pause(self):
        if self.shot_animation.isPlaying():
            self.pause_animation()
        else:
            self.resume_animation()

    def pause_animation(self):
        self.paused = True
        self.shot_animation.pause()

    def resume_animation(self):
        self.paused = False
        self.shot_animation.resume()

    def slow_down(self, multisystem):
        self.change_speed(0.5, multisystem)

    def speed_up(self, multisystem):
        self.change_speed(2.0, multisystem)

    def change_speed(self, factor, multisystem):
        # FIXME This messes up the syncing of shots when self.parallel is True. One
        # clear issue is that trailing_buffer times do not respect self.playback_speed.
        self.playback_speed *= factor
        for shot in multisystem:
            shot.render_obj.playback_speed *= factor

            # Reset the continuous ball history
            for ball in shot.balls.values():
                ball.history_cts = BallHistory()

        curr_time = self.shot_animation.get_t()
        self.clear_animation(multisystem)
        self.set_animation(multisystem)
        self.shot_animation.setPlayRate(factor * self.shot_animation.getPlayRate())

        if not self.paused:
            self.start_animation(PlaybackMode.LOOP)

        self.shot_animation.set_t(curr_time / factor)

    def rewind(self):
        self.offset_time(-ani.rewind_dt)

    def fast_forward(self):
        self.offset_time(ani.fast_forward_dt)

    def offset_time(self, dt):
        old_t = self.shot_animation.get_t()
        new_t = max(0, min(old_t + dt, self.shot_animation.duration))
        self.shot_animation.set_t(new_t)

    def highlight_system(self, i, multisystem):
        for system in multisystem:
            for ball in system.balls.values():
                ball.render_obj.set_alpha(1 / len(multisystem))

        for ball in multisystem[i].balls.values():
            ball.render_obj.set_alpha(1.0)


@dataclass
class System:
    cue: Cue
    table: Table
    balls: Dict[str, Ball]

    t: float = field(default=0)
    events: List[Event] = field(default_factory=list)
    meta: Any = field(default=None)

    render_obj: SystemRender = field(init=False)

    def __post_init__(self):
        self.render_obj = SystemRender()

    @property
    def continuized(self):
        return all(not ball.history_cts.empty for ball in self.balls.values())

    def set_meta(self, meta):
        """Define any meta data for the shot

        This method provides the opportunity to associate information to the system. If
        the system is saved or copied, this information will be retained under the
        attribute `meta`.

        Parameters
        ==========
        meta : pickleable object
             Any information can be stored, so long as it is pickleable.
        """

        if not utils.is_pickleable(meta):
            raise ConfigError("System.set_meta :: Cannot set unpickleable object")

        self.meta = meta

    def update_history(self, event: Event):
        """Updates the history for all balls"""
        self.t = event.time

        for ball in self.balls.values():
            ball.state.t = event.time
            ball.history.add(ball.state)

        self.events.append(event)

    def reset_history(self):
        """Remove all events, histories, and reset timer"""

        self.t = 0

        for ball in self.balls.values():
            ball.history = BallHistory()
            ball.history_cts = BallHistory()
            ball.t = 0

        self.events = []

    def continuize(self, dt=0.01):
        """Create BallHistory for each ball with many timepoints

        Notes
        =====
        - All balls share the same timepoints.
        - All timepoints are uniformly spaced.
        - FIXME There exists no timepoint for the final state of the system (t_f). The
          time difference between t_f and the last timepoint is less than dt. This could
          be improved by providing an optional like `include_final`, or perhaps the
          default behavior could be to add one more timepoint that is dt away from the
          current implementation's last time point, and set the ball state to the final
          state.  This latter idea achieves both uniformly spaced timepoints and
          physical accuracy (the system ends in a 0 energy state, rather than an
          _almost_ 0 energy state)
        - FIXME This is a very inefficient function that could be radically sped up if
          physics.evolve_ball_motion and/or its functions had vectorized operations for
          arrays of time values.
        - The old implementation of continuize can be found by looking at code before
          the "save_movie" branch was merged into main
        """

        # This is the exact number of timepoints that the ball histories will contain
        num_timestamps = int(self.events[-1].time // dt) + 1

        for ball in self.balls.values():
            # Create a new history and add the zeroth event
            history = BallHistory()
            history.add(ball.history[0])

            rvw, s = ball.history[0].rvw, ball.history[0].s

            # Get all events that the ball is involved in, even the null_event events
            # that mark the start and end times
            events = filter_ball(self.events, ball, keep_nonevent=True)

            # Tracks which event is currently being handled
            event_counter = 0

            # The elapsed simulation time (as of the last timepoint)
            elapsed = 0

            for n in range(num_timestamps):
                if n == (num_timestamps - 1):
                    # We made it to the end. the difference between the final time and
                    # the elapsed time should be < dt
                    assert events[-1].time - elapsed < dt
                    break

                if events[event_counter + 1].time - elapsed > dt:
                    # This is the easy case. There is no upcoming event so we simply
                    # evolve the state an amount dt
                    evolve_time = dt

                else:
                    # The next event (and perhaps an arbitrary number of subsequent
                    # events) occurs before the next timestamp. Find the last event
                    # between the current timestamp and the next timestamp. This will be
                    # used as a launching point to simulate the ball state to the next
                    # timestamp

                    while True:
                        event_counter += 1

                        if events[event_counter + 1].time - elapsed > dt:
                            # OK, we found the last event between the current timestamp
                            # and the next timestamp. It is events[event_counter].
                            break

                    # We need to get the ball's outgoing state from the event. We'll
                    # evolve the system from this state.
                    if events[event_counter].event_type.is_transition():
                        state = events[event_counter].final_states[0]
                    elif events[event_counter].event_type.is_collision():
                        if ball == events[event_counter].agents[0]:
                            state = events[event_counter].final_states[0]
                        else:
                            state = events[event_counter].final_states[1]
                    else:
                        raise NotImplementedError(
                            f"Can't handle {events[event_counter]}"
                        )
                    rvw, s = state.rvw, state.s

                    # Since this event occurs between two timestamps, we won't be
                    # evolving a full dt. Instead, we evolve this much:
                    evolve_time = elapsed + dt - events[event_counter].time

                # Whether it was the hard path or the easy path, the ball state is
                # properly defined and we know how much we need to simulate.
                rvw, s = physics.evolve_ball_motion(
                    state=s,
                    rvw=rvw,
                    R=ball.params.R,
                    m=ball.params.m,
                    u_s=ball.params.u_s,
                    u_sp=ball.params.u_sp,
                    u_r=ball.params.u_r,
                    g=ball.params.g,
                    t=evolve_time,
                )

                history.add(BallState(rvw, s, elapsed + dt))
                elapsed += dt

            # Attach the newly created history to the ball
            ball.history_cts = history

    def evolve(self, dt):
        """Evolves current ball an amount of time dt

        FIXME This is very inefficent. each ball should store its natural trajectory
        thereby avoid a call to the clunky evolve_ball_motion. It could even be a
        partial function so parameters don't continuously need to be passed
        """

        for ball_id, ball in self.balls.items():
            rvw, s = physics.evolve_ball_motion(
                state=ball.state.s,
                rvw=ball.state.rvw,
                R=ball.params.R,
                m=ball.params.m,
                u_s=ball.params.u_s,
                u_sp=ball.params.u_sp,
                u_r=ball.params.u_r,
                g=ball.params.g,
                t=dt,
            )
            ball.state.set(rvw, s=s, t=(self.t + dt))

    def get_system_energy(self):
        energy = 0
        for ball in self.balls.values():
            energy += physics.get_ball_energy(
                ball.state.rvw, ball.params.R, ball.params.m
            )

        return energy

    def reset_balls(self):
        """Reset balls to their initial states"""
        for ball in self.balls.values():
            if not ball.history.empty:
                ball.state = ball.history[0].copy()

    def is_balls_overlapping(self):
        for ball1 in self.balls.values():
            for ball2 in self.balls.values():
                if ball1 is ball2:
                    continue

                if physics.is_overlapping(
                    ball1.state.rvw, ball2.state.rvw, ball1.params.R, ball2.params.R
                ):
                    return True

        return False

    def copy(self, set_to_initial=True):
        """Make a fresh copy of this system state

        Parameters
        ==========
        set_to_initial : bool, True
            Prior to copying, this method sets the ball states the initial states in the
            history.  However, this can be prevented by setting this to False, causing
            the ball states to be copied as is.
        """
        raise NotImplementedError()


@dataclass
class MultiSystem:
    _multisystem: List[System] = field(default_factory=list)

    active_index: Optional[int] = field(init=False, default=None)
    render_obj: MultiSystemRender = field(init=False)

    def __post_init__(self) -> None:
        self.render_obj = MultiSystemRender()

    def __len__(self) -> int:
        return len(self._multisystem)

    def __getitem__(self, idx: int) -> System:
        return self._multisystem[idx]

    @property
    def active(self) -> System:
        assert self.active_index is not None
        return self._multisystem[self.active_index]

    @property
    def empty(self) -> bool:
        return not bool(len(self))

    def append(self, system: System) -> None:
        if self.empty:
            self.active_index = 0

        self._multisystem.append(system)

    def append_copy_of_active(
        self, state="current", reset_history=True, as_active=False
    ) -> None:
        """Append a copy of the active System

        Parameters
        ==========
        state : str, 'current'
            Must be any of {'initial', 'final', 'current'}. The copy state will be set
            according to this value. If 'initial', the system state will be set
            according to the active system's state at t=0, e.g.
            balls['cue'].history.rvw[0]. If 'final', the system will be set to the final
            state of the active system, e.g. balls['cue'].history.rvw[-1]. If 'current',
            the system will be set to the current state of the active system, e.g.
            balls['cue'].rvw

        reset_history : bool, True
            If True, the history of the copy state will be reset (erased and
            reinitialized).

        as_active : bool, False
            If True, the newly appended System will be set as the active state
        """
        raise NotImplementedError()
        assert state in {"initial", "final", "current"}

        set_to_initial = False if state == "current" else True
        new = self.active.copy(set_to_initial=set_to_initial)

        idx = 0 if state == "initial" else -1
        for ball in new.balls.values():
            ball.state = ball.history[idx].copy()

        if reset_history:
            new.reset_history()

        self.append(new)

        if as_active:
            self.set_active(-1)

    def set_active(self, i) -> None:
        """Change the active system in the collection

        Parameters
        ==========
        i : int
            The integer index of the shot you would like to make active. Negative
            indexing is supported, e.g. set_active(-1) sets the last system in the
            collection as active
        """
        if self.active_index is not None:
            table = self.active.table
            self.active_index = i
            self.active.table = table
        else:
            self.active_index = i

        if i < 0:
            i = len(self) - 1

        self.active_index = i
