#! /usr/bin/env python

import pooltool.terminal as terminal

from pooltool.events import *
from pooltool.system import System, SystemHistory, SystemRender
from pooltool.objects import NonObject, DummyBall

import numpy as np

from abc import ABC


class EvolveShot(ABC, System, SystemHistory, SystemRender):
    def __init__(self, cue=None, table=None, balls=None, run=terminal.Run(), progress=terminal.Progress()):
        self.run = run
        self.progress = progress

        System.__init__(self, cue=cue, table=table, balls=balls)
        SystemHistory.__init__(self)
        SystemRender.__init__(self)

        # What kinds of events should be considered?
        self.include = {
            type_ball_ball: True,
            type_ball_cushion: True,
            type_ball_pocket: True,
        }


    def simulate(self, strike=True, name="NA", **kwargs):
        """Run a simulation

        Parameters
        ==========
        t_final : float, None
            The simulation will run until the time is greater than this value. If None, simulation
            is ran until the next event occurs at np.inf

        strike : bool, True
            If True, the cue stick will strike a ball at the start of the simulation. If you already
            struck the cue ball, you should set this to False.

        name : str, 'NA'
            A name for the simulated shot
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

        self.progress_update = progress_update

        self.run.warning('', header=name, lc='green')
        self.run.info('starting energy', f"{np.round(energy_start, 2)}J")

        self.progress.new("Running", progress_total_items=int(energy_start))
        self.evolution_algorithm(**kwargs)
        self.progress.end()

        self.run.info('Finished after', self.progress.t.time_elapsed_precise())


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


    @abstractmethod
    def evolution_algorithm(self):
        pass


class EvolveShotEventBased(EvolveShot):
    def __init__(self, *args, **kwargs):
        EvolveShot.__init__(self, *args, **kwargs)


    def evolution_algorithm(self, t_final=None, continuize=True, dt=0.01):
        """The event-based evolution algorithm"""

        while True:
            event = self.get_next_event()

            if event.time == np.inf:
                self.end_history()
                break

            self.evolve(event.time - self.t)
            if self.include.get(event.event_type, True):
                event.resolve()

            self.update_history(event)

            if (self.num_events % 10) == 0:
                self.progress_update()

            if t_final is not None and self.t >= t_final:
                break

        if continuize:
            self.continuize(dt=dt)


    def get_next_event(self):
        # Start by assuming next event doesn't happen
        event = NonEvent(t = np.inf)

        transition_event = self.get_min_transition_event_time()
        if transition_event.time < event.time:
            event = transition_event

        ball_ball_event = self.get_min_ball_ball_event_time()
        if ball_ball_event.time < event.time:
            event = ball_ball_event

        ball_cushion_event = self.get_min_ball_cushion_event_time()
        if ball_cushion_event.time < event.time:
            event = ball_cushion_event

        ball_pocket_event = self.get_min_ball_pocket_event_time()
        if ball_pocket_event.time < event.time:
            event = ball_pocket_event

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

                if ball1.s == pooltool.pocketed or ball2.s == pooltool.pocketed:
                    continue

                if ball1.s in pooltool.nontranslating and ball2.s in pooltool.nontranslating:
                    continue

                dtau_E = physics.get_ball_ball_collision_time(
                    rvw1=ball1.rvw,
                    rvw2=ball2.rvw,
                    s1=ball1.s,
                    s2=ball2.s,
                    mu1=(ball1.u_s if ball1.s == pooltool.sliding else ball1.u_r),
                    mu2=(ball2.u_s if ball2.s == pooltool.sliding else ball2.u_r),
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


    def get_min_ball_cushion_event_time(self):
        """Returns minimum time until next ball-cushion collision"""

        dtau_E_min = np.inf
        involved_agents = tuple([DummyBall(), NonObject()])

        for ball in self.balls.values():
            if ball.s in pooltool.nontranslating:
                continue

            for cushion in self.table.cushion_segments['linear'].values():
                dtau_E = physics.get_ball_linear_cushion_collision_time(
                    rvw=ball.rvw,
                    s=ball.s,
                    lx=cushion.lx,
                    ly=cushion.ly,
                    l0=cushion.l0,
                    p1=cushion.p1,
                    p2=cushion.p2,
                    mu=(ball.u_s if ball.s == pooltool.sliding else ball.u_r),
                    m=ball.m,
                    g=ball.g,
                    R=ball.R
                )

                if dtau_E < dtau_E_min:
                    involved_agents = (ball, cushion)
                    dtau_E_min = dtau_E

            for cushion in self.table.cushion_segments['circular'].values():
                dtau_E = physics.get_ball_circular_cushion_collision_time(
                    rvw=ball.rvw,
                    s=ball.s,
                    a=cushion.a,
                    b=cushion.b,
                    r=cushion.radius,
                    mu=(ball.u_s if ball.s == pooltool.sliding else ball.u_r),
                    m=ball.m,
                    g=ball.g,
                    R=ball.R
                )

                if dtau_E < dtau_E_min:
                    involved_agents = (ball, cushion)
                    dtau_E_min = dtau_E

        dtau_E = dtau_E_min

        return BallCushionCollision(*involved_agents, t=(self.t + dtau_E))


    def get_min_ball_pocket_event_time(self):
        """Returns minimum time until next ball-pocket collision"""

        dtau_E_min = np.inf
        involved_agents = tuple([DummyBall(), NonObject()])

        for ball in self.balls.values():
            if ball.s in pooltool.nontranslating:
                continue

            for pocket in self.table.pockets.values():
                dtau_E = physics.get_ball_pocket_collision_time(
                    rvw=ball.rvw,
                    s=ball.s,
                    a=pocket.a,
                    b=pocket.b,
                    r=pocket.radius,
                    mu=(ball.u_s if ball.s == pooltool.sliding else ball.u_r),
                    m=ball.m,
                    g=ball.g,
                    R=ball.R
                )

                if dtau_E < dtau_E_min:
                    involved_agents = (ball, pocket)
                    dtau_E_min = dtau_E

        dtau_E = dtau_E_min

        return BallPocketCollision(*involved_agents, t=(self.t + dtau_E))


class EvolveShotDiscreteTime(EvolveShot):
    def __init__(self, *args, **kwargs):
        EvolveShot.__init__(self, *args, **kwargs)


    def evolution_algorithm(self, t_final=None, dt=0.05):
        """The discrete time algorithm"""

        steps = 0
        while True:
            self.evolve(dt)
            self.t += dt

            events = self.detect_events()
            for event in events:
                event.resolve()
                self.update_history(event, update_all=True)

            if (steps % 1000) == 0:
                self.progress_update()

            if t_final is not None and self.t >= t_final:
                break

            if self.get_system_energy() < pooltool.tol:
                break

            steps += 1


    def detect_events(self):
        events = []
        events.extend(self.detect_ball_ball_collisions())
        events.extend(self.detect_ball_cushion_collisions())

        if not len(events):
            events.append(NonEvent(t = self.t))

        return events


    def detect_ball_ball_collisions(self):
        events = []
        for i, ball1 in enumerate(self.balls.values()):
            for j, ball2 in enumerate(self.balls.values()):
                if i >= j:
                    continue

                if ball1.s in pooltool.nontranslating and ball2.s in pooltool.nontranslating:
                    continue

                if physics.is_overlapping(ball1.rvw, ball2.rvw, ball1.R, ball2.R):
                    events.append(BallBallCollision(ball1, ball2, t=self.t))

        return events


    def detect_ball_cushion_collisions(self):
        """FIXME a complete hack that doesn't work for generalized tables"""
        events = []

        for ball in self.balls.values():
            ball_x, ball_y = ball.rvw[0,:2]
            if ball_x <= self.table.L + ball.R:
                events.append(BallCushionCollision(ball, self.table.cushion_segments['L'], t=self.t))
            elif ball_x >= self.table.R - ball.R:
                events.append(BallCushionCollision(ball, self.table.cushion_segments['R'], t=self.t))
            elif ball_y <= self.table.B + ball.R:
                events.append(BallCushionCollision(ball, self.table.cushion_segments['B'], t=self.t))
            elif ball_y >= self.table.T - ball.R:
                events.append(BallCushionCollision(ball, self.table.cushion_segments['T'], t=self.t))

        return events


shot_evolver = {
    'event': EvolveShotEventBased,
    'discrete': EvolveShotDiscreteTime,
}

def get_shot_evolver(algorithm):
    evolver = shot_evolver.get(algorithm)

    if evolver is None:
        raise ValueError(f"'{algorithm}' is not a valid shot evolution algorithm. Please choose from: {list(shot_evolver.keys())}")

    return evolver


