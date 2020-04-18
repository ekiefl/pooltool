#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.physics as physics

from psim.objects import Ball, Table, Cue

import numpy as np
import pandas as pd


class Event(object):
    def __init__(self, event_type, ids, tau):
        self.event_type = event_type
        self.ids = ids
        self.tau = tau

    def __repr__(self):
        return f"type: {self.event_type}; involved: {self.ids}; tau: {self.tau}"


class ShotSimulation(object):
    def __init__(self, g=None):
        self.g = g or psim.g

        self.t = []


    def evolve(self, t):
        for ball_id in self.balls:
            ball = self.balls[ball_id]
            rvw, s = physics.evolve_ball_motion(
                state=ball.s,
                rvw=ball.rvw,
                R=ball.R,
                m=ball.m,
                u_s=self.table.u_s,
                u_sp=self.table.u_sp,
                u_r=self.table.u_r,
                g=self.g,
                t=t,
            )
            ball.s = s
            ball.rvw = rvw
            ball.store(rvw, s)

        self.t.append(t)


    def resolve(self, event):
        if event.event_type == 'ball-ball':
            ball_id1, ball_id2 = event.ids

            rvw1 = self.balls[ball_id1].rvw
            rvw2 = self.balls[ball_id2].rvw

            rvw1, rvw2 = physics.resolve_ball_ball_collision(rvw1, rvw2)
            s1, s2 = psim.sliding, psim.sliding

            self.balls[ball_id1].rvw = rvw1
            self.balls[ball_id2].rvw = rvw2
            self.balls[ball_id1].s = s1
            self.balls[ball_id2].s = s2

            self.balls[ball_id1].store(rvw1, s1)
            self.balls[ball_id2].store(rvw2, s2)


    def get_next_event(self):
        tau_min = np.inf
        ids_min = tuple()
        event_type = None

        tau, ids = self.get_min_motion_event_time()
        if tau < tau_min:
            tau_min = tau
            event_type = 'motion'
            ids_min = ids

        tau, ids = self.get_min_ball_ball_event_time()
        if tau < tau_min:
            tau_min = tau
            event_type = 'ball-ball'
            ids_min = ids

        return Event(event_type, ids_min, tau_min)


    def get_min_motion_event_time(self):
        """Returns minimum until next ball motion transition"""

        tau_min = np.inf
        ball_id = None

        for ball in self.balls.values():
            if ball.s == psim.stationary:
                continue
            elif ball.s == psim.rolling:
                tau = physics.get_roll_time(ball.rvw, self.table.u_r, self.g)
            elif ball.s == psim.sliding:
                tau = physics.get_slide_time(ball.rvw, ball.R, self.table.u_s, self.g)
            elif ball.s == psim.spinning:
                tau = physics.get_spin_time(ball.rvw, ball.R, self.table.u_sp, self.g)

            if tau < tau_min:
                tau_min = tau
                ball_id = ball.id

        return tau_min, ball_id


    def get_min_ball_ball_event_time(self):
        """Returns minimum time until next ball-ball collision"""

        tau_min = np.inf
        ball_ids = (None, None)

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


    def get_time_array(self):
        return np.array(self.t)


    def print_ball_states(self):
        for ball in self.balls:
            print(f"ball: {ball}; state: {self.balls[ball].s}")


    def setup_test(self, setup='masse'):
        # Make a table, cue, and balls
        self.table = Table()
        self.cue = Cue(brand='Predator')
        self.balls = {}

        self.balls['cue'] = Ball('cue')
        self.balls['cue'].rvw[0] = [self.table.center[0], self.table.B+0.33, 0]

        self.balls['8'] = Ball('8')
        self.balls['8'].rvw[0] = [self.table.center[0], 1.6, 0]

        if setup == 'masse':
            self.cue.strike(
                ball = self.balls['cue'],
                V0 = 2.8,
                phi = 80.746,
                theta = 80,
                a = 0.2,
                b = 0.0,
            )
        elif setup == 'slight_masse':
            self.cue.strike(
                ball = self.balls['cue'],
                V0 = 0.5,
                phi = 100,
                theta = 20,
                a = -0.4,
                b = 0.0,
            )
        elif setup == 'straight_shot':
            self.cue.strike(
                ball = self.balls['cue'],
                V0 = 1,
                phi = 89,
                sweet_spot=True
            )


