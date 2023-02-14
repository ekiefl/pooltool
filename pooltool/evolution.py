#! /usr/bin/env python

from abc import ABC, abstractmethod

import numpy as np

import pooltool.constants as c
import pooltool.physics as physics
import pooltool.terminal as terminal
import pooltool.utils as utils
from pooltool.error import SimulateError
from pooltool.events import (
    EventType,
    ball_ball_collision,
    ball_cushion_collision,
    ball_pocket_collision,
    get_next_transition_event,
    null_event,
)
from pooltool.objects import NullObject


class EvolveShot(ABC):
    def __init__(self, run=terminal.Run(), progress=terminal.Progress()):
        self.run = run
        self.progress = progress

        # What kinds of events should be considered?
        self.include = {
            EventType.BALL_BALL: True,
            EventType.BALL_CUSHION: True,
            EventType.BALL_POCKET: True,
        }

    def simulate(self, name="NA", quiet=False, raise_simulate_error=False, **kwargs):
        """Run a simulation

        Parameters
        ==========
        t_final : float, None
            The simulation will run until the time is greater than this value. If None,
            simulation is ran until the next event occurs at np.inf
        raise_simulate_error : bool, False
            If true, a SimulateError is raised upon failure, so it may be caught and
            handled. This is to avoid errors when simulating shots in the GUI.

        name : str, 'NA'
            A name for the simulated shot
        """

        self.reset_history()
        self.update_history(null_event(time=0))

        if not quiet:

            def progress_update():
                """Convenience function for updating progress"""
                msg = f"SIM TIME {self.t:.6f}s | EVENTS {len(self.events)}"
                self.progress.update(msg)

            self.run.warning("", header=name, lc="green")
            self.progress.new("Running")
        else:

            def progress_update():
                pass

        self.progress_update = progress_update

        try:
            self.evolution_algorithm(**kwargs)
        except:
            raise SimulateError()

        if not quiet:
            self.progress.end()
            self.run.info("Finished after", self.progress.t.time_elapsed_precise())

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

    @abstractmethod
    def evolution_algorithm(self):
        pass


class EvolveShotEventBased(EvolveShot):
    def __init__(self, *args, **kwargs):
        EvolveShot.__init__(self, *args, **kwargs)

    def evolution_algorithm(self, t_final=None, continuize=False, dt=None):
        """The event-based evolution algorithm"""

        if dt is None:
            dt = 0.01

        while True:
            event = self.get_next_event()

            if event.time == np.inf:
                self.update_history(null_event(time=self.t + c.tol))
                break

            self.evolve(event.time - self.t)
            if self.include.get(event.event_type, True):
                event.resolve()

            self.update_history(event)

            if (len(self.events) % 30) == 0:
                self.progress_update()

            if t_final is not None and self.t >= t_final:
                break

        if continuize:
            self.continuize(dt=dt)

    def get_next_event(self):
        # Start by assuming next event doesn't happen
        event = null_event(time=np.inf)

        transition_event = self.get_min_transition_event_time()
        if transition_event.time < event.time:
            event = transition_event

        ball_ball_event = self.get_min_ball_ball_event_time()
        if ball_ball_event.time < event.time:
            event = ball_ball_event

        ball_linear_cushion_event = self.get_min_ball_linear_cushion_event_time()
        if ball_linear_cushion_event.time < event.time:
            event = ball_linear_cushion_event

        ball_circular_cushion_event = self.get_min_ball_circular_cushion_event_time()
        if ball_circular_cushion_event.time < event.time:
            event = ball_circular_cushion_event

        ball_pocket_event = self.get_min_ball_pocket_event_time()
        if ball_pocket_event.time < event.time:
            event = ball_pocket_event

        return event

    def get_min_transition_event_time(self):
        """Returns minimum time until next ball transition event"""

        event = null_event(time=np.inf)

        for ball in self.balls.values():
            trans_event = get_next_transition_event(ball)
            if trans_event.time <= event.time:
                event = trans_event

        return event

    def get_min_ball_ball_event_time(self):
        """Returns minimum time until next ball-ball collision"""
        dtau_E = np.inf
        ball_ids = []
        collision_coeffs = []

        for i, ball1 in enumerate(self.balls.values()):
            for j, ball2 in enumerate(self.balls.values()):
                if i >= j:
                    continue

                if ball1.state.s == c.pocketed or ball2.state.s == c.pocketed:
                    continue

                if (
                    ball1.state.s in c.nontranslating
                    and ball2.state.s in c.nontranslating
                ):
                    continue

                collision_coeffs.append(
                    physics.get_ball_ball_collision_coeffs_fast(
                        rvw1=ball1.state.rvw,
                        rvw2=ball2.state.rvw,
                        s1=ball1.state.s,
                        s2=ball2.state.s,
                        mu1=(
                            ball1.params.u_s
                            if ball1.state.s == c.sliding
                            else ball1.params.u_r
                        ),
                        mu2=(
                            ball2.params.u_s
                            if ball2.state.s == c.sliding
                            else ball2.params.u_r
                        ),
                        m1=ball1.params.m,
                        m2=ball2.params.m,
                        g1=ball1.params.g,
                        g2=ball2.params.g,
                        R=ball1.params.R,
                    )
                )

                ball_ids.append((ball1.id, ball2.id))

        if not len(collision_coeffs):
            # There are no collisions to test for
            return ball_ball_collision(NullObject(), NullObject(), self.t + dtau_E)

        dtau_E, index = utils.min_real_root(p=np.array(collision_coeffs), tol=c.tol)

        ball1_id, ball2_id = ball_ids[index]
        ball1, ball2 = self.balls[ball1_id], self.balls[ball2_id]

        return ball_ball_collision(ball1, ball2, self.t + dtau_E)

    def get_min_ball_circular_cushion_event_time(self):
        dtau_E = np.inf
        agent_ids = []
        collision_coeffs = []

        for ball in self.balls.values():
            if ball.state.s in c.nontranslating:
                continue

            for cushion in self.table.cushion_segments["circular"].values():
                collision_coeffs.append(
                    physics.get_ball_circular_cushion_collision_coeffs_fast(
                        rvw=ball.state.rvw,
                        s=ball.state.s,
                        a=cushion.a,
                        b=cushion.b,
                        r=cushion.radius,
                        mu=(
                            ball.params.u_s
                            if ball.state.s == c.sliding
                            else ball.params.u_r
                        ),
                        m=ball.params.m,
                        g=ball.params.g,
                        R=ball.params.R,
                    )
                )

                agent_ids.append((ball.id, cushion.id))

        if not len(collision_coeffs):
            # There are no collisions to test for
            return ball_cushion_collision(NullObject(), NullObject(), self.t + dtau_E)

        dtau_E, index = utils.min_real_root(p=np.array(collision_coeffs), tol=c.tol)

        ball_id, cushion_id = agent_ids[index]
        ball, cushion = (
            self.balls[ball_id],
            self.table.cushion_segments["circular"][cushion_id],
        )

        return ball_cushion_collision(ball, cushion, self.t + dtau_E)

    def get_min_ball_linear_cushion_event_time(self):
        dtau_E_min = np.inf
        involved_agents = tuple([NullObject(), NullObject()])

        for ball in self.balls.values():
            if ball.state.s in c.nontranslating:
                continue

            for cushion in self.table.cushion_segments["linear"].values():
                dtau_E = physics.get_ball_linear_cushion_collision_time_fast(
                    rvw=ball.state.rvw,
                    s=ball.state.s,
                    lx=cushion.lx,
                    ly=cushion.ly,
                    l0=cushion.l0,
                    p1=cushion.p1,
                    p2=cushion.p2,
                    direction=cushion.direction.value,
                    mu=(
                        ball.params.u_s
                        if ball.state.s == c.sliding
                        else ball.params.u_r
                    ),
                    m=ball.params.m,
                    g=ball.params.g,
                    R=ball.params.R,
                )

                if dtau_E < dtau_E_min:
                    involved_agents = (ball, cushion)
                    dtau_E_min = dtau_E

        dtau_E = dtau_E_min

        return ball_cushion_collision(*involved_agents, self.t + dtau_E)

    def get_min_ball_pocket_event_time(self):
        """Returns minimum time until next ball-pocket collision"""
        dtau_E = np.inf
        agent_ids = []
        collision_coeffs = []

        for ball in self.balls.values():
            if ball.state.s in c.nontranslating:
                continue

            for pocket in self.table.pockets.values():
                collision_coeffs.append(
                    physics.get_ball_pocket_collision_coeffs_fast(
                        rvw=ball.state.rvw,
                        s=ball.state.s,
                        a=pocket.a,
                        b=pocket.b,
                        r=pocket.radius,
                        mu=(
                            ball.params.u_s
                            if ball.state.s == c.sliding
                            else ball.params.u_r
                        ),
                        m=ball.params.m,
                        g=ball.params.g,
                        R=ball.params.R,
                    )
                )

                agent_ids.append((ball.id, pocket.id))

        if not len(collision_coeffs):
            # There are no collisions to test for
            return ball_pocket_collision(NullObject(), NullObject(), self.t + dtau_E)

        dtau_E, index = utils.min_real_root(p=np.array(collision_coeffs), tol=c.tol)

        ball_id, pocket_id = agent_ids[index]
        ball, pocket = self.balls[ball_id], self.table.pockets[pocket_id]

        return ball_pocket_collision(ball, pocket, self.t + dtau_E)


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
                resolve_event(event)
                self.update_history(event)

            if (steps % 1000) == 0:
                self.progress_update()

            if t_final is not None and self.t >= t_final:
                break

            if self.get_system_energy() < c.tol:
                break

            steps += 1

    def detect_events(self):
        events = []
        events.extend(self.detect_ball_ball_collisions())
        events.extend(self.detect_ball_cushion_collisions())

        if not len(events):
            events.append(null_event(time=self.t))

        return events

    def detect_ball_ball_collisions(self):
        events = []
        for i, ball1 in enumerate(self.balls.values()):
            for j, ball2 in enumerate(self.balls.values()):
                if i >= j:
                    continue

                if ball1.s in c.nontranslating and ball2.s in c.nontranslating:
                    continue

                if physics.is_overlapping(
                    ball1.state.rvw, ball2.state.rvw, ball1.params.R, ball2.params.R
                ):
                    events.append(ball_ball_collision(ball1, ball2, self.t))

        return events

    def detect_ball_cushion_collisions(self):
        """FIXME a complete hack that doesn't work for generalized tables"""
        events = []

        for ball in self.balls.values():
            ball_x, ball_y = ball.state.rvw[0, :2]
            if ball_x <= self.table.L + ball.params.R:
                events.append(
                    ball_cushion_collision(
                        ball, self.table.cushion_segments["L"], self.t
                    )
                )
            elif ball_x >= self.table.R - ball.params.R:
                events.append(
                    ball_cushion_collision(
                        ball, self.table.cushion_segments["R"], self.t
                    )
                )
            elif ball_y <= self.table.B + ball.params.R:
                events.append(
                    ball_cushion_collision(
                        ball, self.table.cushion_segments["B"], self.t
                    )
                )
            elif ball_y >= self.table.T - ball.params.R:
                events.append(
                    ball_cushion_collision(
                        ball, self.table.cushion_segments["T"], self.t
                    )
                )

        return events


shot_evolver = {
    "event": EvolveShotEventBased,
    "discrete": EvolveShotDiscreteTime,
}


def get_shot_evolver(algorithm):
    evolver = shot_evolver.get(algorithm)

    if evolver is None:
        raise ValueError(
            f"'{algorithm}' is not a valid shot evolution algorithm. Please choose "
            f"from: {list(shot_evolver.keys())}"
        )

    return evolver
