#! /usr/bin/env python

import tempfile
from pathlib import Path

from direct.interval.IntervalGlobal import Func, Parallel, Sequence, Wait
from panda3d.direct import HideInterval, ShowInterval

import pooltool.ani as ani
import pooltool.constants as c
import pooltool.physics as physics
import pooltool.utils as utils
from pooltool.error import ConfigError, SimulateError
from pooltool.events import Event, Events, EventType, null_event
from pooltool.evolution import EvolveShotEventBased
from pooltool.objects.ball import Ball, BallHistory
from pooltool.objects.cue import cue_from_dict
from pooltool.utils.strenum import StrEnum, auto


class SystemHistory(object):
    def __init__(self):
        self.t = None
        self.events = Events()
        self.continuized = False

    def init_history(self):
        """Add an initializing null_event"""
        event = null_event(time=0)
        for ball in self.balls.values():
            ball.update_history(event)

        self.events.append(event)

    def end_history(self):
        """Add a final null_event that timestamps the final state of each ball"""

        event = null_event(time=self.t + c.tol)
        for ball in self.balls.values():
            ball.update_history(event)

        self.events.append(event)

    def reset_history(self):
        """Remove all events, histories, and reset timer"""

        self.t = 0
        self.continuized = False

        for ball in self.balls.values():
            ball.history = BallHistory()
            ball.history_cts = BallHistory()
            ball.events.reset()
            ball.t = 0

        self.events.reset()

    def set_from_history(self, i):
        """Set the ball states according to a history index"""
        for ball in self.balls.values():
            ball.set_from_history(i)

    def update_history(self, event, update_all=False):
        """Updates the history for agents of an event

        Parameters
        ==========
        event : class with base events.Event
            An event
        update_all : bool, False
            By default, this method updates only the histories of balls that are agents
            of the event. However, if update_all is True, each ball's history will be
            updated.
        """
        self.t = event.time

        if update_all:
            for ball in self.balls.values():
                ball.update_history(event)
        else:
            for agent in event.agents:
                if isinstance(agent, Ball):
                    agent.update_history(event)

        self.events.append(event)

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
            cts_history = BallHistory()
            rvw, s = ball.history.rvw[0], ball.history.s[0]
            cts_history.add(rvw, s, 0)

            # Get all events that the ball is involved in, even the null_event events that
            # mark the start and end times
            events = self.events.filter_ball(ball, keep_nonevent=True)

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
                        rvw, s = events[event_counter].final_states[0]
                    elif events[event_counter].event_type.is_collision():
                        if ball == events[event_counter].agents[0]:
                            rvw, s = events[event_counter].final_states[0]
                        else:
                            rvw, s = events[event_counter].final_states[1]
                    else:
                        raise NotImplementedError(
                            f"Can't handle {events[event_counter]}"
                        )

                    # Since this event occurs between two timestamps, we won't be
                    # evolving a full dt. Instead, we evolve this much:
                    evolve_time = elapsed + dt - events[event_counter].time

                # Whether it was the hard path or the easy path, the ball state is
                # properly defined and we know how much we need to simulate.
                rvw, s = physics.evolve_ball_motion(
                    state=s,
                    rvw=rvw,
                    R=ball.params.R,
                    m=ball.m,
                    u_s=ball.u_s,
                    u_sp=ball.u_sp,
                    u_r=ball.u_r,
                    g=ball.g,
                    t=evolve_time,
                )

                cts_history.add(rvw, s, elapsed + dt)
                elapsed += dt

            # Attach the newly created history to the ball
            ball.history_cts = cts_history

        self.continuized = True


class PlaybackMode(StrEnum):
    LOOP = auto()
    SINGLE = auto()


class SystemRender(object):
    def __init__(self):
        self.reset_animation()

    def init_shot_animation(
        self, animate_stroke=True, trailing_buffer=0, leading_buffer=0
    ):
        if not len(self.events):
            try:
                self.simulate(raise_simulate_error=True)
            except SimulateError:
                pass

        if not self.continuized:
            # playback speed / fps * 2.0 is basically the sweetspot for creating smooth
            # interpolations that capture motion. Any more is wasted computation and any
            # less and the interpolation starts to look bad.
            if self.playback_speed > 0.99:
                self.continuize(
                    dt=self.playback_speed / ani.settings["graphics"]["fps"] * 2.5
                )
            else:
                self.continuize(
                    dt=self.playback_speed / ani.settings["graphics"]["fps"] * 1.5
                )

        if self.ball_animations is None:
            # This takes ~90% of this method's execution time
            self.ball_animations = Parallel()
            for ball in self.balls.values():
                if not ball.render_obj.rendered:
                    ball.render_obj.render(ball)
                ball.render_obj.set_playback_sequence(
                    ball, playback_speed=self.playback_speed
                )
                self.ball_animations.append(ball.render_obj.playback_sequence)

        if self.user_stroke and animate_stroke:
            # There exists a stroke trajectory, and animating the stroke has been
            # requested
            self.cue.render_obj.set_stroke_sequence()
            self.stroke_animation = Sequence(
                ShowInterval(self.cue.render_obj.get_node("cue_stick")),
                self.cue.render_obj.stroke_sequence,
                HideInterval(self.cue.render_obj.get_node("cue_stick")),
            )
            self.shot_animation = Sequence(
                Func(self.restart_ball_animations),
                self.stroke_animation,
                self.ball_animations,
                Wait(trailing_buffer),
            )
        else:
            self.cue.render_obj.hide_nodes()
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

    def clear_animation(self):
        if self.shot_animation is not None:
            self.shot_animation.clearToInitial()
            self.shot_animation = None
            self.ball_animations = None
            self.stroke_animation = None

        for ball in self.balls.values():
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

    def reset_animation(self):
        self.shot_animation = None
        self.ball_animations = None
        self.stroke_animation = None
        self.user_stroke = False
        self.playback_speed = 1

    def teardown(self):
        self.clear_animation()
        for ball in self.balls.values():
            ball.remove_nodes()
        self.cue.render_obj.remove_nodes()

    def buildup(self):
        self.clear_animation()
        for ball in self.balls.values():
            ball.render_obj.render(ball)
            ball.reset_angular_integration()
        self.cue.render_obj.render()
        self.cue.render_obj.init_focus(self.cue.cueing_ball)


class System(SystemHistory, SystemRender, EvolveShotEventBased):
    def __init__(self, path=None, cue=None, table=None, balls=None, d=None):
        SystemHistory.__init__(self)
        SystemRender.__init__(self)
        EvolveShotEventBased.__init__(self)

        # FIXME use classmethods/staticmethods for path and d routes
        if path and (cue or table or balls):
            raise ConfigError(
                "System :: if path provided, cue, table, and balls must be None"
            )
        if d and (cue or table or balls):
            raise ConfigError(
                "System :: if d provided, cue, table, and balls must be None"
            )
        if d and path:
            raise ConfigError(
                "System :: Preload a system with either `d` or `path`, not both"
            )

        if path:
            path = Path(path)
            self.load(path)
        elif d:
            self.load_from_dict(d)
        else:
            self.cue = cue
            self.table = table
            self.balls = balls
            self.t = None
            self.meta = None

    def set_cue(self, cue):
        self.cue = cue

    def set_table(self, table):
        self.table = table

    def set_balls(self, balls):
        self.balls = balls

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

    def get_system_energy(self):
        energy = 0
        for ball in self.balls.values():
            energy += physics.get_ball_energy(ball.state.rvw, ball.params.R, ball.m)

        return energy

    def reset_balls(self):
        """Reset balls to their initial states, i.e. ball.history.*[0]"""
        for ball in self.balls.values():
            try:
                ball.set_from_history(0)
            except IndexError:
                pass

    def is_balls_overlapping(self):
        for ball1 in self.balls.values():
            for ball2 in self.balls.values():
                if ball1 is ball2:
                    continue

                if physics.is_overlapping(ball1.rvw, ball2.rvw, ball1.R, ball2.R):
                    return True

        return False

    def set_system_state(self):
        raise NotImplementedError(
            "set_system_state FIXME. What should this take as input?"
        )

    def as_dict(self):
        d = {}

        if self.balls:
            d["balls"] = {}
            for ball in self.balls.values():
                d["balls"][ball.id] = ball.as_dict()

        if self.cue:
            d["cue"] = self.cue.as_dict()

        if self.table:
            d["table"] = self.table.as_dict()

        d["events"] = self.events.as_dict()
        d["meta"] = self.meta

        return d

    def from_dict(self, d):
        """Return balls, table, cue, events, and meta objects from dictionary"""
        if "balls" in d:
            balls = {}
            for ball_id, ball_dict in d["balls"].items():
                balls[ball_id] = ball_from_dict(ball_dict)
        else:
            balls = None

        if "cue" in d:
            cue = cue_from_dict(d["cue"])
            if balls and cue.cueing_ball_id in balls:
                cue.set_state(cueing_ball=balls[cue.cueing_ball_id])
        else:
            cue = None

        if "table" in d:
            table = table_from_dict(d["table"])
        else:
            table = None

        events = Events()
        for event_dict in d["events"]:
            event = Event.from_dict(event_dict)

            # The agents of this event are NullObjects, since they came from a pickleable
            # dictionary.  We attempt to change that by associating the proper agents
            # based on object IDs. So if the NullObject agent has an id 'cue', We replace
            # this agent with a proper instantiation of 'cue', i.e. balls['cue']
            if event.event_type == EventType.BALL_BALL:
                agent1, agent2 = event.agents
                event.agents = [balls[agent1.id], balls[agent2.id]]

            elif event.event_type == EventType.BALL_CUSHION:
                agent1, agent2 = event.agents
                if agent2.id.endswith("edge"):
                    cushion = table.cushion_segments["linear"][agent2.id.split("_")[0]]
                else:
                    cushion = table.cushion_segments["circular"][agent2.id]
                event.agents = [balls[agent1.id], cushion]

            elif event.event_type == EventType.BALL_POCKET:
                agent1, agent2 = event.agents
                event.agents = [balls[agent1.id], table.pockets[agent2.id]]

            elif event.event_type == EventType.STICK_BALL:
                agent1, agent2 = event.agents
                event.agents = [cue, balls[agent2.id]]

            elif event.event_type.is_transition():
                agent = event.agents[0]
                event.agents = [balls[agent.id]]

            events.append(event)

        meta = d["meta"]

        return balls, table, cue, events, meta

    def save(self, path, set_to_initial=True):
        """Save the system state as a pickle

        Parameters
        ==========
        set_to_initial : bool, True
            Prior to saving, this method sets the ball states the initial states in the
            history.  However, this can be prevented by setting this to False, causing
            the ball states to be saved as is.
        """
        if set_to_initial:
            self.reset_balls()
        utils.save_pickle(self.as_dict(), path)

    def load(self, path):
        """Load a pickle-stored system state"""
        self.balls, self.table, self.cue, self.events, self.meta = self.from_dict(
            utils.load_pickle(path)
        )

    def load_from_dict(self, d):
        """Load a dictionary-stored system state"""
        self.balls, self.table, self.cue, self.events, self.meta = self.from_dict(d)

    def copy(self, set_to_initial=True):
        """Make a fresh copy of this system state

        Parameters
        ==========
        set_to_initial : bool, True
            Prior to copying, this method sets the ball states the initial states in the
            history.  However, this can be prevented by setting this to False, causing
            the ball states to be copied as is.
        """
        with tempfile.NamedTemporaryFile(delete=True) as temp:
            self.save(temp.name, set_to_initial=set_to_initial)
            balls, table, cue, events, meta = self.from_dict(
                utils.load_pickle(temp.name)
            )

        system = self.__class__(balls=balls, table=table, cue=cue)
        system.events = events
        system.meta = meta
        return system


class SystemCollectionRender(object):
    def __init__(self):
        self.active = None
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

    def set_animation(self):
        if self.parallel:
            self.shot_animation = Parallel()

            # `max_dur` is the shot duration of the longest shot in the collection. All
            # shots beside this one will have a buffer appended where the balls stay in
            # their final state until the last shot finishes.
            max_dur = max([shot.events[-1].time for shot in self])

            # FIXME `leading_buffer` should be utilized here to sync up all shots that
            # have cue trajectories such that the ball animations all start at the
            # moment of the stick-ball collision
            pass

            for shot in self:
                shot_dur = shot.events[-1].time
                shot.init_shot_animation(
                    trailing_buffer=max_dur - shot_dur,
                    leading_buffer=0,
                )
                self.shot_animation.append(shot.shot_animation)
        else:
            if not self.active:
                raise ConfigError(
                    "SystemCollectionRender.set_animation :: self.active not set"
                )
            self.active.init_shot_animation()
            self.shot_animation = self.active.shot_animation

    def start_animation(self, playback_mode: PlaybackMode):
        if playback_mode == PlaybackMode.SINGLE:
            self.shot_animation.start()
        elif playback_mode == PlaybackMode.LOOP:
            self.shot_animation.loop()

    def skip_stroke(self):
        stroke = self.active.stroke_animation
        if stroke is not None:
            self.shot_animation.set_t(stroke.get_duration())

    def restart_animation(self):
        self.shot_animation.set_t(0)

    def clear_animation(self):
        if self.parallel:
            for shot in self:
                shot.clear_animation()
        else:
            self.active.clear_animation()

        if self.shot_animation is not None:
            self.shot_animation.clearToInitial()
            self.shot_animation.pause()
            self.shot_animation = None

    def toggle_parallel(self):
        self.clear_animation()

        if self.parallel:
            for shot in self:
                shot.teardown()
            self.active.buildup()
            self.parallel = False
            self.set_animation()
        else:
            self.active.teardown()
            for shot in self:
                shot.buildup()
            self.parallel = True
            self.set_animation()

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

    def slow_down(self):
        self.change_speed(0.5)

    def speed_up(self):
        self.change_speed(2.0)

    def change_speed(self, factor):
        # FIXME This messes up the syncing of shots when self.parallel is True. One
        # clear issue is that trailing_buffer times do not respect self.playback_speed.
        self.playback_speed *= factor
        for shot in self:
            shot.playback_speed *= factor
            shot.continuized = False

        curr_time = self.shot_animation.get_t()
        self.clear_animation()
        self.set_animation()
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

    def highlight_system(self, i):
        for system in self:
            for ball in system.balls.values():
                ball.set_alpha(1 / len(self))

        for ball in self[i].balls.values():
            ball.set_alpha(1.0)


class SystemCollection(utils.ListLike, SystemCollectionRender):
    def __init__(self, path=None):
        utils.ListLike.__init__(self)

        if path:
            self.load(Path(path))

        SystemCollectionRender.__init__(self)

        self.active: System = None
        self.active_index = None

    def append(self, system):
        if len(self):
            # In order to append a system, the table must be damn-near identical to
            # existing systems in this collection. Otherwise we raise an error
            if system.table.as_dict() != self[0].table.as_dict():
                raise ConfigError(
                    f"Cannot append System '{system}', which has a different table "
                    f"than the rest of the SystemCollection"
                )

        utils.ListLike.append(self, system)

    def append_copy_of_active(
        self, state="current", reset_history=True, as_active=False
    ):
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
        assert state in {"initial", "final", "current"}

        set_to_initial = False if state == "current" else True
        new = self.active.copy(set_to_initial=set_to_initial)

        if state == "initial":
            new.set_from_history(0)
        elif state == "final":
            new.set_from_history(-1)

        if reset_history:
            new.reset_history()

        self.append(new)

        if as_active:
            self.set_active(-1)

    def set_active(self, i):
        """Change the active system in the collection

        Parameters
        ==========
        i : int
            The integer index of the shot you would like to make active. Negative
            indexing is supported, e.g. set_active(-1) sets the last system in the
            collection as active
        """
        if self.active is not None:
            table = self.active.table
            self.active = self[i]
            self.active.table = table
        else:
            self.active = self[i]

        if i < 0:
            i = len(self) - 1

        self.active_index = i

    def as_pickleable_object(self):
        return [system.as_dict() for system in self]

    def save(self, path):
        for system in self:
            system.reset_balls()
        utils.save_pickle(self.as_pickleable_object(), path)

    def load(self, path):
        obj = utils.load_pickle(path)
        for system_dict in obj:
            self.append(System(d=system_dict))

    def clear(self):
        self.active = None
        self._list = []
