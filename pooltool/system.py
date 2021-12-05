#! /usr/bin/env python

import pooltool.utils as utils
import pooltool.physics as physics
import pooltool.constants as c

from pooltool.evolution import EvolveShotEventBased
from pooltool.objects.cue import cue_from_dict
from pooltool.objects.ball import ball_from_dict
from pooltool.objects.table import table_from_dict

from pooltool.events import *
from pooltool.objects.ball import BallHistory

from panda3d.direct import HideInterval, ShowInterval
from direct.interval.IntervalGlobal import *


class SystemHistory(object):
    def __init__(self):
        self.t = None
        self.events = Events()
        self.vectorized = False


    def init_history(self):
        """Add an initializing NonEvent"""
        event = NonEvent(t=0)
        for ball in self.balls.values():
            ball.update_history(event)

        self.events.append(event)


    def end_history(self):
        """Add a final NonEvent that timestamps the final state of each ball"""

        event = NonEvent(t=self.t)
        for ball in self.balls.values():
            ball.update_history(event)

        self.events.append(event)


    def reset_history(self):
        """Remove all events, histories, and reset timer"""

        self.t = 0
        for ball in self.balls.values():
            ball.history.reset()
            ball.events.reset()
            ball.set_time(0)

        self.events.reset()


    def update_history(self, event, update_all=False):
        """Updates the history for agents of an event

        Parameters
        ==========
        event : class with base events.Event
            An event
        update_all : bool, False
            By default, this method updates only the histories of balls that are agents of the
            event. However, if update_all is True, each ball's history will be updated.
        """
        self.t = event.time

        if update_all:
            for ball in self.balls.values():
                ball.update_history(event)
        else:
            for agent in event.agents:
                if agent.object_type == 'ball':
                    agent.update_history(event)

        self.events.append(event)


    def vectorize_trajectories(self):
        if not self.vectorized:
            for ball in self.balls.values():
                ball.history.vectorize()


    def continuize(self, dt=0.01):
        """Create BallHistory for each ball with timepoints _inbetween_ events--attach to respective ball

        Notes
        =====
        - This does not create uniform time spacings between shots. For example, all events are
          sandwiched between two time points, one immediately before the event, and one immediately after.
          This ensures that during lerp (linear interpolation) operations, the event is never interpolated
          over with any significant amount of time.
        - FIXME This is a very inefficient function that could be radically sped up if
          physics.evolve_ball_motion and/or its functions had vectorized operations for arrays of time values.
        """

        for ball in self.balls.values():
            # Create a new history
            cts_history = BallHistory()

            # Add t=0
            cts_history.add(ball.history.rvw[0], ball.history.s[0], 0)

            for n in range(len(ball.events) - 1):
                curr_event = ball.events[n]
                next_event = ball.events[n+1]

                dtau_E = next_event.time - curr_event.time
                if not dtau_E:
                    continue

                step = 0
                rvw, s = ball.history.rvw[n], ball.history.s[n]
                while step < dtau_E:
                    rvw, s = physics.evolve_ball_motion(
                        state=s,
                        rvw=rvw,
                        R=ball.R,
                        m=ball.m,
                        u_s=ball.u_s,
                        u_sp=ball.u_sp,
                        u_r=ball.u_r,
                        g=ball.g,
                        t=dt,
                    )

                    cts_history.add(rvw, s, curr_event.time + step)
                    step += dt

                # By this point the history has been populated with equally spaced timesteps `dt`
                # starting from curr_event.time up until--but not including--next_event.time.
                # There still exists a `remainder` of time that is strictly less than `dt`. I evolve
                # the state this additional amount which gives us the state of the system at the
                # time of the next event, yet _before_ the event has been resolved. Then, I add the
                # next event, _after_ the event has been resolved.
                remainder = dtau_E - step
                rvw, s = physics.evolve_ball_motion(
                    state=s,
                    rvw=rvw,
                    R=ball.R,
                    m=ball.m,
                    u_s=ball.u_s,
                    u_sp=ball.u_sp,
                    u_r=ball.u_r,
                    g=ball.g,
                    t=remainder,
                )

                cts_history.add(rvw, s, next_event.time - c.tol)
                cts_history.add(ball.history.rvw[n+1], ball.history.s[n+1], next_event.time)

            # Attach the newly created history to the ball, overwriting the existing history
            ball.attach_history(cts_history)


class SystemRender(object):
    def __init__(self):
        self.shot_animation = None
        self.ball_animations = None
        self.stroke_animation = None
        self.playback_speed = 1


    def init_shot_animation(self):
        self.vectorize_trajectories()

        self.ball_animations = Parallel()
        for ball in self.balls.values():
            ball.set_playback_sequence(playback_speed=self.playback_speed)
            self.ball_animations.append(ball.playback_sequence)

        if len(self.cue.stroke_pos):
            # There exists a stroke trajectory. Create animation sequence
            self.cue.set_stroke_sequence()
            self.stroke_animation = Sequence(
                ShowInterval(self.cue.get_node('cue_stick')),
                self.cue.stroke_sequence,
                HideInterval(self.cue.get_node('cue_stick')),
            )
            self.shot_animation = Sequence(
                self.stroke_animation,
                self.ball_animations,
                Func(self.restart_ball_animations)
            )
        else:
            self.cue.hide_nodes()
            self.stroke_animation = None
            self.shot_animation = Sequence(
                self.ball_animations,
                Func(self.restart_ball_animations)
            )


    def loop_animation(self):
        if self.shot_animation is None:
            raise Exception("First call SystemRender.init_shot_animation()")

        self.shot_animation.loop()


    def restart_animation(self):
        self.shot_animation.set_t(0)


    def restart_ball_animations(self):
        self.ball_animations.set_t(0)


    def clear_animation(self):
        self.shot_animation.clearToInitial()


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


    def slow_down(self):
        self.playback_speed *= 0.5
        self.shot_animation.setPlayRate(0.5*self.shot_animation.getPlayRate())


    def speed_up(self):
        self.playback_speed *= 2.0
        self.shot_animation.setPlayRate(2.0*self.shot_animation.getPlayRate())


class System(SystemHistory, SystemRender, EvolveShotEventBased):
    def __init__(self, cue=None, table=None, balls=None):
        SystemHistory.__init__(self)
        SystemRender.__init__(self)
        EvolveShotEventBased.__init__(self)

        self.cue = cue
        self.table = table
        self.balls = balls

        self.t = None


    def set_cue(self, cue):
        self.cue = cue


    def set_table(self, table):
        self.table = table


    def set_balls(self, balls):
        self.balls = balls


    def get_system_energy(self):
        energy = 0
        for ball in self.balls.values():
            energy += physics.get_ball_energy(ball.rvw, ball.R, ball.m)

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
        raise NotImplementedError("set_system_state FIXME. What should this take as input?")


    def as_dict(self):
        d = {}

        if self.balls:
            d['balls'] = {}
            for ball in self.balls.values():
                d['balls'][ball.id] = ball.as_dict()

        if self.cue:
            d['cue'] = self.cue.as_dict()

        if self.table:
            d['table'] = self.table.as_dict()

        d['events'] = self.events.as_dict()

        return d


    def from_dict(self, d):
        """Return balls, table, cue, and events objects from dictionary"""
        if 'balls' in d:
            balls = {}
            for ball_id, ball_dict in d['balls'].items():
                balls[ball_id] = ball_from_dict(ball_dict)
        else:
            balls = None

        if 'cue' in d:
            cue = cue_from_dict(d['cue'])
            if balls and cue.cueing_ball_id in balls:
                cue.set_state(cueing_ball = balls[cue.cueing_ball_id])
        else:
            cue = None

        if 'table' in d:
            table = table_from_dict(d['table'])
        else:
            table = None

        events = Events()
        for event_dict in d['events']:
            event = event_from_dict(event_dict)

            # The agents of this event are NonObjects, since they came from a pickleable dictionary.
            # We attempt to change that by associating the proper agents based on object IDs. So if
            # the NonObject agent has an id 'cue', We replace this agent with a proper instantiation
            # of 'cue', i.e. balls['cue']
            if event.event_type == type_ball_ball:
                agent1, agent2 = event.agents
                event.agents = (balls[agent1.id], balls[agent2.id])

            elif event.event_type == type_ball_cushion:
                agent1, agent2 = event.agents
                if agent2.id.endswith('edge'):
                    cushion = table.cushion_segments['linear'][agent2.id.split('_')[0]]
                else:
                    cushion = table.cushion_segments['circular'][agent2.id]
                event.agents = (balls[agent1.id], cushion)

            elif event.event_type == type_ball_pocket:
                agent1, agent2 = event.agents
                event.agents = (balls[agent1.id], table.pockets[agent2.id])

            elif event.event_type == type_stick_ball:
                agent1, agent2 = event.agents
                event.agents = (cue, balls[agent2.id])

            elif event.event_class == class_transition:
                agent = event.agents[0]
                event.agents = (balls[agent.id],)

            # The event now has no NonObject agents, so it is not longer 'partial'. For example,
            # event.resolve may not be called
            event.partial = False
            events.append(event)

        return balls, table, cue, events


    def save(self, path):
        """Save the system state as a pickle"""
        self.reset_balls()
        utils.save_pickle(self.as_dict(), path)


    def load(self, path):
        """Load a pickle-stored system state"""
        self.balls, self.table, self.cue, self.events = self.from_dict(utils.load_pickle(path))


    def copy(self):
        """Make a fresh copy of this system state

        Notes
        =====
        - FIXME continuize() does not work on the fresh copy due to Event data not being stored
          in System or Ball. The solution is to call simulate() again on the copy and then continuize()
        """

        filepath = utils.get_temp_file_path()
        self.save(filepath)
        balls, table, cue, events = self.from_dict(utils.load_pickle(filepath))

        system = self.__class__(balls=balls, table=table, cue=cue)
        system.events = events
        return system


