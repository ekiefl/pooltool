#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.physics as physics
import psim.terminal as terminal
import psim.configurations as configurations

from psim.events import *
from psim.objects import NonObject, DummyBall, BallHistory

from panda3d.direct import HideInterval, ShowInterval
from direct.interval.IntervalGlobal import *

import copy
import numpy as np


class System(object):
    def __init__(self, cue=None, table=None, balls=None):
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



class SystemHistory(Events):
    balls = None

    def __init__(self):
        self.t = None
        self.num_events = 0

        if self.balls is None:
            raise NotImplementedError("Child classes of SystemHistory must have self.balls defined")

        Events.__init__(self)


    def init_history(self):
        """Add an initializing NonEvent"""

        self.num_events += 1

        event = NonEvent(t=0)
        for ball in self.balls.values():
            ball.update_history(event)

        self.add_event(event)


    def end_history(self):
        """Add a final NonEvent that timestamps the final state of each ball"""

        self.num_events += 1

        event = NonEvent(t=self.t)
        for ball in self.balls.values():
            ball.update_history(event)

        self.add_event(event)


    def reset_history(self):
        """Remove all events, histories, and reset timer"""

        self.t = 0
        for ball in self.balls.values():
            ball.history.reset_history()
            ball.reset_events()
            ball.set_time(0)

        self.reset_events()


    def update_history(self, event):
        self.t = event.time
        self.num_events += 1

        for agent in event.agents:
            if agent.object_type == 'ball':
                agent.update_history(event)

        self.add_event(event)


    def vectorize_trajectories(self):
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
        - FIXME This is a very inefficient function that could be radically speeded up if
          physics.evolve_ball_motion and/or its functions had vectorized operations for arrays of time values.
        """

        for ball in self.balls.values():
            # Create a new history
            cts_history = BallHistory()

            for n in range(ball.num_events - 1):
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

                cts_history.add(rvw, s, next_event.time - psim.tol)
                cts_history.add(ball.history.rvw[n+1], ball.history.s[n+1], next_event.time)

            # Attach the newly created history to the ball, overwriting the existing history
            ball.attach_history(cts_history)


class ShotRender(object):
    def __init__(self):
        self.shot_animation = None
        self.ball_animations = None
        self.stroke_animation = None
        self.playback_speed = 1


    def init_shot_animation(self):

        self.ball_animations = Parallel()
        for ball in self.balls.values():
            ball.set_playback_sequence(playback_speed=self.playback_speed)
            self.ball_animations.append(ball.playback_sequence)

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


    def loop_animation(self):
        if self.shot_animation is None:
            raise Exception("First call ShotRender.init_shot_animation()")

        self.shot_animation.loop()


    def restart_animation(self):
        self.shot_animation.set_t(0)


    def restart_ball_animations(self):
        self.ball_animations.set_t(0)


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


    def finish_animation(self):
        self.shot_animation.finish()


    def slow_down(self):
        self.playback_speed *= 0.5
        self.shot_animation.setPlayRate(0.5*self.shot_animation.getPlayRate())


    def speed_up(self):
        self.playback_speed *= 2.0
        self.shot_animation.setPlayRate(2.0*self.shot_animation.getPlayRate())


    def exit_ops(self):
        self.finish_animation()
        self.ball_animations.finish()

        self.cue.reset_state()
        self.cue.set_render_state_as_object_state()
        self.cue.update_focus()

        for ball in self.balls.values():
            ball.reset_angular_integration()




class SimulateShot(System, SystemHistory, ShotRender):
    def __init__(self, cue=None, table=None, balls=None, progress=terminal.Progress(), run=terminal.Run()):
        self.run = run
        self.progress = progress

        System.__init__(self, cue=cue, table=table, balls=balls)
        SystemHistory.__init__(self)
        ShotRender.__init__(self)


    def simulate(self, t_final=None, strike=True, name='NA'):
        """Run a simulation

        Parameters
        ==========
        t_final : float
            The simulation will run until the time is greater than this value. If None, simulation
            is ran until the next even occurs at np.inf

        strike : bool, True
            If True, the cue stick will strike a ball at the start of the simulation. If you already
            struck the cue ball, you should set this to False.
        """

        self.reset_history()
        self.init_history()

        if strike:
            event = self.cue.strike(t = self.t)
            self.update_history(event)

        energy_start = self.get_system_energy()

        def progress_update():
            """Convenience function for updating progress"""
            energy = self.get_system_energy()
            num_stationary = len([_ for _ in self.balls.values() if _.s == 0])
            msg = f"ENERGY {np.round(energy, 2)}J | STATIONARY {num_stationary} | EVENTS {self.num_events}"
            self.progress.update(msg)
            self.progress.increment(increment_to=int(energy_start - energy))

        self.run.warning('', header=name, lc='green')
        self.run.info('starting energy', f"{np.round(energy_start, 2)}J")

        self.progress.new(f"Running", progress_total_items=int(energy_start))

        while True:
            event = self.get_next_event()

            if event.time == np.inf:
                self.end_history()
                break

            self.evolve(event.time - self.t)
            event.resolve()

            self.update_history(event)

            if (self.num_events % 10) == 0:
                progress_update()

            if t_final is not None and self.t >= t_final:
                break

        self.progress.end()

        self.run.info('Finished after', self.progress.t.time_elapsed_precise())
        self.run.info('Number of events', len(self.events), nl_after=1)

        self.continuize()
        self.vectorize_trajectories()
        self.balls['cue'].set_playback_sequence()



    def evolve(self, dt):
        """Evolves current ball an amount of time dt

        FIXME This is very inefficent. each ball should store its natural trajectory thereby avoid a
        call to the clunky evolve_ball_motion. It could even be a partial function so parameters don't
        continuously need to be passed
        """

        for ball_id, ball in self.balls.items():
            rvw, s = physics.evolve_ball_motion(
                state=ball.s,
                rvw=ball.rvw,
                R=ball.R,
                m=ball.m,
                u_s=ball.u_s,
                u_sp=ball.u_sp,
                u_r=ball.u_r,
                g=ball.g,
                t=dt,
            )
            ball.set(rvw, s, t=(self.t + dt))


    def get_next_event(self):
        # Start by assuming next event doesn't happen
        event = NonEvent(t = np.inf)

        transition_event = self.get_min_transition_event_time()
        if transition_event.time < event.time:
            event = transition_event

        ball_ball_event = self.get_min_ball_ball_event_time()
        if ball_ball_event.time < event.time:
            event = ball_ball_event

        ball_cushion_event = self.get_min_ball_rail_event_time()
        if ball_cushion_event.time < event.time:
            event = ball_cushion_event

        return event


    def get_min_transition_event_time(self):
        """Returns minimum time until next ball transition event"""

        event = NonEvent(t = np.inf)

        for ball in self.balls.values():
            if ball.next_transition_event.time <= event.time:
                event = ball.next_transition_event

        return event


    def get_min_ball_ball_event_time(self):
        """Returns minimum time until next ball-ball collision"""

        dtau_E_min = np.inf
        involved_balls = tuple([DummyBall(), DummyBall()])

        for i, ball1 in enumerate(self.balls.values()):
            for j, ball2 in enumerate(self.balls.values()):
                if i >= j:
                    continue

                if ball1.s == psim.stationary and ball2.s == psim.stationary:
                    continue

                dtau_E = physics.get_ball_ball_collision_time(
                    rvw1=ball1.rvw,
                    rvw2=ball2.rvw,
                    s1=ball1.s,
                    s2=ball2.s,
                    mu1=(ball1.u_s if ball1.s == psim.sliding else ball1.u_r),
                    mu2=(ball2.u_s if ball2.s == psim.sliding else ball2.u_r),
                    m1=ball1.m,
                    m2=ball2.m,
                    g1=ball1.g,
                    g2=ball2.g,
                    R=ball1.R
                )

                if dtau_E < dtau_E_min:
                    involved_balls = (ball1, ball2)
                    dtau_E_min = dtau_E

        dtau_E = dtau_E_min

        return BallBallCollision(*involved_balls, t=(self.t + dtau_E))


    def get_min_ball_rail_event_time(self):
        """Returns minimum time until next ball-rail collision"""

        dtau_E_min = np.inf
        involved_agents = tuple([DummyBall(), NonObject()])

        for ball in self.balls.values():
            if ball.s == psim.stationary:
                continue

            for rail in self.table.rails.values():
                dtau_E = physics.get_ball_rail_collision_time(
                    rvw=ball.rvw,
                    s=ball.s,
                    lx=rail.lx,
                    ly=rail.ly,
                    l0=rail.l0,
                    mu=(ball.u_s if ball.s == psim.sliding else ball.u_r),
                    m=ball.m,
                    g=ball.g,
                    R=ball.R
                )

                if dtau_E < dtau_E_min:
                    involved_agents = (ball, rail)
                    dtau_E_min = dtau_E

        dtau_E = dtau_E_min

        return BallCushionCollision(*involved_agents, t=(self.t + dtau_E))


