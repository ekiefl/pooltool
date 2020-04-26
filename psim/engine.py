#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.physics as physics
import psim.terminal as terminal

from psim.objects import (
    Ball,
    Table,
    Cue,
)

import numpy as np

np.random.seed(100)


class Event(object):
    def __init__(self, event_type, agents, tau):
        self.agents = agents
        self.tau = tau
        self.event_type = event_type

    def __repr__(self):
        lines = [
            f'<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>',
            f' ├── event_type : {self.event_type}',
            f' ├── tau        : {self.tau}',
            f' └── agents     : {self.agents}',
        ]

        return '\n' + '\n'.join(lines)


class ShotHistory(object):
    """Track the states of balls over time"""

    def __init__(self, progress=terminal.Progress(), run=terminal.Run()):
        self.run = run
        self.progress = progress

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


    def get_ball_state_history(self, ball_id):
        """Returns 1D array if self.vectorized, otherwise a list"""
        return self.history['balls'][ball_id]['s']


    def get_ball_rvw_history(self, ball_id):
        """Returns 3D array if self.vectorized, otherwise a list of 2D arrays"""
        return self.history['balls'][ball_id]['rvw']


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
        }


    def timestamp(self, dt, event=None):
        # update time
        self.n += 1
        self.time += dt

        # log time
        self.history['time'].append(self.time)
        self.history['index'].append(self.n)

        # log event
        self.history['event'].append(event)

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

            if event.tau == np.inf:
                break

            # Evolve in steps of dt up to the event
            event_time = 0
            while event_time < (event.tau - dt_prime):
                self.evolve(dt_prime)
                event_time += dt_prime

                dt_prime = dt

            dt_prime = dt - (event.tau - event_time)
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

        self.vectorized = True


    def convert_to_euler_angles(self, inplace=False):
        pass


    def plot_history(self, ball_id, full=False):
        """Primitive plotting for use during development"""

        import pandas as pd
        import matplotlib.pyplot as plt

        def add_plot(fig, num, x, y):
            if np.max(np.abs(df[y])) < 0.000000001:
                df[y] = 0

            ax = fig.add_subplot(num)
            for name, group in groups:
                ax.plot(group[x], group[y], marker="o", linestyle="", label=name, ms=1.4)
            ax.set_ylabel(y)
            ax.set_xlabel(x)
            ax.legend()

        s = np.array(self.history['balls'][ball_id]['s'])
        rvw = np.array(self.history['balls'][ball_id]['rvw'])
        t = np.array(self.history['time'])

        df = pd.DataFrame({
            'rx': rvw[:, 0, 0], 'ry': rvw[:, 0, 1], 'rz': rvw[:, 0, 2],
            'vx': rvw[:, 1, 0], 'vy': rvw[:, 1, 1], 'vz': rvw[:, 1, 2],
            'wx': rvw[:, 2, 0], 'wy': rvw[:, 2, 1], 'wz': rvw[:, 2, 2],
            '|v|': np.sqrt(rvw[:, 1, 2]**2 + rvw[:, 1, 1]**2 + rvw[:, 1, 0]**2),
            '|w|': np.sqrt(rvw[:, 2, 2]**2 + rvw[:, 2, 1]**2 + rvw[:, 2, 0]**2),
            'time': t,
            'state': s,
        })
        df['time'] = df['time'].astype(float)

        groups = df.groupby('state')

        fig = plt.figure(figsize=(10, 10))
        plt.title(f"ball ID: {ball_id}")
        add_plot(fig, 331, 'time', 'rx')
        add_plot(fig, 332, 'time', 'ry')
        add_plot(fig, 333, 'time', 'rz')
        add_plot(fig, 334, 'time', 'vx')
        add_plot(fig, 335, 'time', 'vy')
        add_plot(fig, 336, 'time', 'vz')
        add_plot(fig, 337, 'time', 'wx')
        add_plot(fig, 338, 'time', 'wy')
        add_plot(fig, 339, 'time', 'wz')
        plt.tight_layout()
        plt.show()

        if full:
            fig = plt.figure(figsize=(6, 5))
            add_plot(fig, 111, 'time', '|v|')
            plt.title(f"ball ID: {ball_id}")
            plt.tight_layout()
            plt.show()

            fig = plt.figure(figsize=(6, 5))
            add_plot(fig, 111, 'time', '|w|')
            plt.title(f"ball ID: {ball_id}")
            plt.tight_layout()
            plt.show()


class ShotSimulation(ShotHistory):
    def __init__(self, g=None):
        self.g = g or psim.g

        self.cue = None
        self.table = None

        ShotHistory.__init__(self)


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


    def simulate(self, name='NA'):
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
        event = Event(event_type=None, agents=tuple(), tau=0)

        self.timestamp(0, event)
        while event.tau < np.inf:
            event = self.get_next_event()
            self.evolve(dt=event.tau, event=event)

            if (self.n % 5) == 0:
                progress_update()

        self.vectorize_history()

        self.progress.end()

        self.run.warning('', header='Post-run info', lc='green')
        self.run.info('Finished after', self.progress.t.time_elapsed(), nl_after=1)


    def set_cue(self, cue):
        self.cue = cue


    def set_table(self, table):
        self.table = table


    def set_balls(self, balls):
        self.balls = balls


    def evolve(self, dt, log=True, event=None):
        for ball_id, ball in self.balls.items():
            rvw, s = physics.evolve_ball_motion(
                state=ball.s,
                rvw=ball.rvw,
                R=ball.R,
                m=ball.m,
                u_s=self.table.u_s,
                u_sp=self.table.u_sp,
                u_r=self.table.u_r,
                g=self.g,
                t=dt,
            )
            ball.set(rvw, s)

        if event is not None:
            self.resolve(event)

        if log:
            self.timestamp(dt, event=event)


    def resolve(self, event):
        if event.event_type == 'ball-ball':
            ball_id1, ball_id2 = event.agents

            rvw1 = self.balls[ball_id1].rvw
            rvw2 = self.balls[ball_id2].rvw

            rvw1, rvw2 = physics.resolve_ball_ball_collision(rvw1, rvw2)
            s1, s2 = psim.sliding, psim.sliding

            self.balls[ball_id1].set(rvw1, s1)
            self.balls[ball_id2].set(rvw2, s2)

        elif event.event_type == 'ball-rail':
            ball_id, rail_id = event.agents

            rvw = self.balls[ball_id].rvw
            normal = self.table.rails[rail_id].normal

            rvw = physics.resolve_ball_rail_collision(rvw, normal)
            s = psim.sliding

            self.balls[ball_id].set(rvw, s)


    def get_next_event(self):
        tau_min = np.inf
        agents = tuple()
        event_type = None

        tau, ids, e = self.get_min_motion_event_time()
        if tau < tau_min:
            tau_min = tau
            event_type = e
            agents = ids

        tau, ids = self.get_min_ball_ball_event_time()
        if tau < tau_min:
            tau_min = tau
            event_type = 'ball-ball'
            agents = ids

        tau, ids = self.get_min_ball_rail_event_time()
        if tau < tau_min:
            tau_min = tau
            event_type = 'ball-rail'
            agents = ids

        return Event(event_type, agents, tau_min)


    def get_min_motion_event_time(self):
        """Returns minimum until next ball motion transition"""

        tau_min = np.inf
        ball_id = None
        event_type_min = None

        for ball in self.balls.values():
            if ball.s == psim.stationary:
                continue
            elif ball.s == psim.rolling:
                tau = physics.get_roll_time(ball.rvw, self.table.u_r, self.g)
                event_type = 'end-roll'
            elif ball.s == psim.sliding:
                tau = physics.get_slide_time(ball.rvw, ball.R, self.table.u_s, self.g)
                event_type = 'end-slide'
            elif ball.s == psim.spinning:
                tau = physics.get_spin_time(ball.rvw, ball.R, self.table.u_sp, self.g)
                event_type = 'end-spin'

            if tau < tau_min:
                tau_min = tau
                ball_id = ball.id
                event_type_min = event_type

        return tau_min, (ball_id, ), event_type_min


    def get_min_ball_ball_event_time(self):
        """Returns minimum time until next ball-ball collision"""

        tau_min = np.inf
        ball_ids = tuple()

        for i, ball1 in enumerate(self.balls.values()):
            for j, ball2 in enumerate(self.balls.values()):
                if i >= j:
                    continue

                if ball1.s == psim.stationary and ball2.s == psim.stationary:
                    continue

                tau = physics.get_ball_ball_collision_time(
                    rvw1=ball1.rvw,
                    rvw2=ball2.rvw,
                    s1=ball1.s,
                    s2=ball2.s,
                    mu1=(self.table.u_s if ball1.s == psim.sliding else self.table.u_r),
                    mu2=(self.table.u_s if ball2.s == psim.sliding else self.table.u_r),
                    m1=ball1.m,
                    m2=ball2.m,
                    g=self.g,
                    R=ball1.R
                )

                if tau < tau_min:
                    ball_ids = (ball1.id, ball2.id)
                    tau_min = tau

        return tau_min, ball_ids


    def get_min_ball_rail_event_time(self):
        """Returns minimum time until next ball-rail collision"""

        tau_min = np.inf
        agent_ids = (None, None)

        for ball in self.balls.values():
            if ball.s == psim.stationary:
                continue

            for rail in self.table.rails.values():
                tau = physics.get_ball_rail_collision_time(
                    rvw=ball.rvw,
                    s=ball.s,
                    lx=rail.lx,
                    ly=rail.ly,
                    l0=rail.l0,
                    mu=(self.table.u_s if ball.s == psim.sliding else self.table.u_r),
                    m=ball.m,
                    g=self.g,
                    R=ball.R
                )

                if tau < tau_min:
                    agent_ids = (ball.id, rail.id)
                    tau_min = tau

        return tau_min, agent_ids


    def print_ball_states(self):
        for ball in self.balls.values():
            print(ball)


    def setup_test(self, setup='masse'):
        # Make a table, cue, and balls
        self.cue = Cue(brand='Predator')
        self.balls = {}

        if setup == 'masse':
            self.table = Table()
            self.balls['cue'] = Ball('cue')
            self.balls['cue'].rvw[0] = [self.table.center[0], self.table.B+0.33, 0]

            self.balls['8'] = Ball('8')
            self.balls['8'].rvw[0] = [self.table.center[0], 1.6, 0]

            self.balls['3'] = Ball('3')
            self.balls['3'].rvw[0] = [self.table.center[0]*0.70, 1.6, 0]

            self.cue.strike(
                ball = self.balls['cue'],
                V0 = 2.9,
                phi = 80.746,
                theta = 80,
                a = 0.2,
                b = 0.0,
            )
        elif setup == 'stat_mech':
            self.table = Table(l=2.5, w=2.5)

            self.balls['cue'] = Ball('cue')
            self.balls['cue'].rvw[0] = [
                self.table.w - 0.2,
                0.2,
                0
            ]

            for i in range(1,40):
                self.balls[i] = Ball(i)
                R = self.balls[i].R

                self.balls[i].rvw[0] = [
                    (self.table.w/2)*np.random.rand() + R,
                    (self.table.l - 2*R)*np.random.rand() + R,
                    0
                ]

                while self.is_balls_overlapping():
                    self.balls[i] = Ball(i)
                    self.balls[i].rvw[0] = [
                        (self.table.w/2)*np.random.rand() + R,
                        (self.table.l - 2*R)*np.random.rand() + R,
                        0
                    ]

            self.cue.strike(
                ball = self.balls['cue'],
                V0 = 10.9,
                phi = 81,
                theta = 20,
                a = 0.01,
                b = 0.0,
            )
        elif setup == 'straight_shot':
            self.table = Table()
            self.balls['cue'] = Ball('cue')
            self.balls['cue'].rvw[0] = [self.table.center[0], self.table.B+0.33, 0]

            self.balls['7'] = Ball('7')
            self.balls['7'].rvw[0] = [self.table.center[0] - self.table.w/5, self.table.B+1.89, 0]

            self.balls['9'] = Ball('9')
            self.balls['9'].rvw[0] = [self.table.center[0] - self.table.w/5, self.table.T-0.1, 0]

            self.balls['2'] = Ball('2')
            self.balls['2'].rvw[0] = [self.table.center[0], self.table.T-0.3, 0]

            self.balls['3'] = Ball('3')
            self.balls['3'].rvw[0] = [self.table.center[0] + self.table.w/6, self.table.B+1.89, 0]

            self.balls['8'] = Ball('8')
            self.balls['8'].rvw[0] = [self.table.center[0], self.table.B+1.66, 0]

            self.cue.strike(
                ball = self.balls['cue'],
                V0 = 2.50001,
                phi = 91.999999157,
                a = -0.3,
                b = 0.4,
                theta = 0,
            )

        self.touch_history()

