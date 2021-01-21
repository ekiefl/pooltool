#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.physics as physics
import psim.terminal as terminal
import psim.configurations as configurations

from psim.events import *

import copy
import numpy as np


class ShotHistory(utils.Garbage):
    """Track the states of balls over time"""

    def __init__(self, balls=None, progress=terminal.Progress(), run=terminal.Run()):
        self.run = run
        self.progress = progress

        if balls is None:
            self.balls = {}

        self.reset_history()


    def reset_history(self):
        self.vectorized = False

        self.history = {
            'balls': {},
            'index': [],
            'time': [],
            'event': [],
        }

        self.n = -1
        self.time = 0

        self.touch_history()


    def get_time_history(self):
        """Returns 1D array if self.vectorized, otherwise a list"""
        return self.history['time']


    def _get_ball_var_history(self, ball_id, key):
        return self.history['balls'][ball_id][key]


    def get_ball_state_history(self, ball_id):
        """Returns 1D array if self.vectorized, otherwise a list"""
        return self._get_ball_var_history(ball_id, 's')


    def get_ball_rvw_history(self, ball_id):
        """Returns 3D array if self.vectorized, otherwise a list of 2D arrays"""
        return self._get_ball_var_history(ball_id, 'rvw')


    def get_ball_euler_history(self, ball_id):
        """Returns 3D array if self.vectorized, otherwise a list of 2D arrays"""
        return self._get_ball_var_history(ball_id, 'euler')


    def get_ball_quat_history(self, ball_id):
        """Returns 3D array if self.vectorized, otherwise a list of 2D arrays"""
        return self._get_ball_var_history(ball_id, 'quat')


    def get_event_history_for_ball(self, ball_id):
        return [event
                for event in self.history['event']
                if ball_id in event.agents]


    def touch_history(self):
        """Initializes ball trajectories if they haven't been initialized"""

        for ball_id in self.balls:
            if ball_id not in self.history['balls']:
                self.init_ball_history(ball_id)


    def init_ball_history(self, ball_id):
        """Adds a new ball to the trajectory. Adds nans if self.n > 0"""

        if ball_id not in self.balls:
            raise ValueError(f"ShotHistory.init_ball_history :: {ball_id} not in self.balls")

        self.history['balls'][ball_id] = {
            's': [np.nan] * self.n,
            'rvw': [np.nan * np.ones((4,3))] * self.n,
            'euler': [np.nan * np.ones((4,3))] * self.n,
            'quat': [np.nan * np.ones((4,4))] * self.n,
        }


    def timestamp(self, dt):
        # update time
        self.n += 1
        self.time += dt

        # log time
        self.history['time'].append(self.time)
        self.history['index'].append(self.n)

        # log event
        self.history['event'].append(None)

        # log ball states
        for ball_id, ball in self.balls.items():
            self.history['balls'][ball_id]['s'].append(ball.s)
            self.history['balls'][ball_id]['rvw'].append(ball.rvw)


    def continuize(self, dt=0.05):
        old_n = self.n
        old_history = self.history
        self.reset_history()

        self.progress.new("Continuizing shot history", progress_total_items=old_n)

        # Set and log balls to the initial state
        self.set_table_state_via_history(index=0, history=old_history)
        self.timestamp(0)

        dt_prime = dt
        for index, event in zip(old_history['index'], old_history['event']):

            self.progress.update(f"Done event {index} / {old_n}")
            self.progress.increment()

            if not isinstance(event, Event):
                continue

            if event.dtau_E == np.inf:
                break

            # Evolve in steps of dt up to the event
            event_time = 0
            while event_time < (event.dtau_E - dt_prime):
                self.evolve(dt_prime, log=False)
                self.timestamp(dt)
                event_time += dt_prime

                dt_prime = dt

            dt_prime = dt - (event.dtau_E - event_time)
            # Set and log balls to the resolved state of the event
            self.set_table_state_via_history(index=index, history=old_history)

        self.vectorize_history()
        self.progress.end()


    def set_table_state_via_history(self, index, history=None):
        if history is None:
            history = self.history

        for ball_id, ball in self.balls.items():
            ball.set(
                history['balls'][ball_id]['rvw'][index],
                history['balls'][ball_id]['s'][index],
            )


    def vectorize_history(self):
        """Convert all list objects in self.history to array objects

        Notes
        =====
        - Should be done once the history has been already built and
          will not be further appended to.
        - self.history['event'] cannot be vectorized because its
          elements are Event objects
        """

        self.history['index'] = np.array(self.history['index'])
        self.history['time'] = np.array(self.history['time'])
        for ball in self.history['balls']:
            self.history['balls'][ball]['s'] = np.array(self.history['balls'][ball]['s'])
            self.history['balls'][ball]['rvw'] = np.array(self.history['balls'][ball]['rvw'])
            self.history['balls'][ball]['euler'] = np.array(self.history['balls'][ball]['euler'])
            self.history['balls'][ball]['quat'] = np.array(self.history['balls'][ball]['quat'])

        self.vectorized = True


    def calculate_euler_angles(self):
        for ball_id in self.balls:
            angle_integrations = self.history['balls'][ball_id]['rvw'][:, 3, :]
            euler_angles = utils.as_euler_angle(angle_integrations)
            self.history['balls'][ball_id]['euler'] = euler_angles


    def calculate_quaternions(self):
        for ball_id in self.balls:
            angle_integrations = self.history['balls'][ball_id]['rvw'][:, 3, :]
            quaternions = utils.as_quaternion(angle_integrations)
            self.history['balls'][ball_id]['quat'] = quaternions


class Shot(object):
    def __init__(self, cue=None, table=None, balls=None):
        self.cue = cue
        self.table = table
        self.balls = balls


    def set_cue(self, cue):
        self.cue = cue


    def set_table(self, table):
        self.table = table


    def set_balls(self, balls):
        self.balls = balls


    def get_system_energy(self):
        energy = 0
        for name, ball in self.balls.items():
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


class SimulateShot(Shot, ShotHistory):
    def __init__(self, cue=None, table=None, balls=None):

        Shot.__init__(self, cue=cue, table=table, balls=balls)
        ShotHistory.__init__(self, balls=self.balls)

        self.events = Events()


    def simulate(self, time=None, name='NA'):
        self.touch_history()

        energy_start = self.get_system_energy()

        def progress_update():
            """Convenience function for updating progress"""
            energy = self.get_system_energy()
            num_stationary = len([_ for _ in self.balls.values() if _.s == 0])
            msg = f"ENERGY {np.round(energy, 2)}J | STATIONARY {num_stationary} | EVENTS {self.n}"
            self.progress.update(msg)
            self.progress.increment(increment_to=int(energy_start - energy))

        self.run.warning('', header='Pre-run info', lc='green')
        self.run.info('name', name)
        self.run.info('num balls', len(self.balls))
        self.run.info('table dimensions', f"{self.table.l}m x {self.table.w}m")
        self.run.info('starting energy', f"{np.round(energy_start, 2)}J")
        self.run.info('float precision', psim.tol, nl_after=1)

        self.progress.new(f"Running", progress_total_items=int(energy_start))

        event = NonEvent(t=0)
        self.events.add(event)

        self.timestamp(0)

        while event.time < np.inf:
            event = self.get_next_event()
            self.events.add(event)

            self.evolve(dt=(event.time - self.time))
            event.resolve()

            if (self.n % 5) == 0:
                progress_update()

            if time is not None and self.time >= time:
                break

        self.progress.end()

        self.run.warning('', header='Post-run info', lc='green')
        self.run.info('Finished after', self.progress.t.time_elapsed())
        self.run.info('Number of events', len(self.events.events), nl_after=1)

        print(self.events)


    def evolve(self, dt, log=True):
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
            ball.set(rvw, s, t=(self.time + dt))

        if log:
            self.timestamp(dt)


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
        involved_balls = tuple([None, None])

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

        return BallBallCollision(*involved_balls, t=(self.time + dtau_E))


    def get_min_ball_rail_event_time(self):
        """Returns minimum time until next ball-rail collision"""

        dtau_E_min = np.inf
        involved_agents = ([None, None])

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

        return BallCushionCollision(*involved_agents, t=(self.time + dtau_E))




