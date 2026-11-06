from __future__ import annotations

import math
from itertools import combinations, product
from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool import events
from pooltool.error import SimulateError
from pooltool.evolution.continuous import continuize
from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based.detect import EventDetector
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.components import (
    CircularCushionSegment,
    CushionDirection,
    LinearCushionSegment,
    Pocket,
)
from pooltool.objects.table.datatypes import Table
from pooltool.physics.resolve.ball_ball.friction import AlciatoreBallBallFriction
from pooltool.physics.resolve.ball_ball.frictional_inelastic import (
    FrictionalInelastic2D,
)
from pooltool.physics.resolve.ball_cushion.stronge_compliant.model import (
    StrongeCompliantCircular2D,
    StrongeCompliantLinear2D,
)
from pooltool.physics.resolve.ball_pocket import CanonicalBallPocket
from pooltool.physics.resolve.resolver import (
    Resolver,
    _snapshot_final,
    _snapshot_initial,
)
from pooltool.physics.resolve.stick_ball.instantaneous_point import InstantaneousPoint2D
from pooltool.physics.resolve.transition import CanonicalTransition
from pooltool.system.datatypes import System

_CHUNK = 32
_MAX_HISTORY_EVENTS = 4096
_TRANSITIONS = {
    (const.sliding, const.rolling): events.sliding_rolling_transition,
    (const.rolling, const.spinning): events.rolling_spinning_transition,
    (const.rolling, const.stationary): events.rolling_stationary_transition,
    (const.spinning, const.stationary): events.spinning_stationary_transition,
}


def _unsupported(detail: str) -> ValueError:
    return ValueError(f"Unsupported compiled_fp64 input: {detail}")


def _pack_engine(engine: SimulationEngine, cue: Cue):
    if (
        type(engine) is not SimulationEngine
        or engine.is_3d
        or type(engine.detector) is not EventDetector
        or engine.detector.is_3d
        or type(engine.resolver) is not Resolver
    ):
        raise _unsupported("the canonical 2D detector and resolver are required")
    resolver = engine.resolver
    pair = resolver.ball_ball
    linear, circular = resolver.ball_linear_cushion, resolver.ball_circular_cushion
    stick = resolver.stick_ball
    if not (
        type(pair) is FrictionalInelastic2D
        and type(pair.friction) is AlciatoreBallBallFriction
        and type(linear) is StrongeCompliantLinear2D
        and type(circular) is StrongeCompliantCircular2D
        and type(stick) is InstantaneousPoint2D
        and type(resolver.ball_pocket) is CanonicalBallPocket
        and type(resolver.transition) is CanonicalTransition
    ):
        raise _unsupported("the selected resolver strategies are not supported")

    cue_specs = np.array(
        (
            cue.specs.M,
            cue.specs.end_mass,
            stick.english_throttle,
            stick.squirt_throttle,
        ),
        dtype=np.float64,
    )
    strike = np.array((cue.V0, cue.phi, cue.theta, cue.a, cue.b), dtype=np.float64)
    if (
        not np.isfinite(cue_specs).all()
        or np.any(cue_specs[:2] <= 0)
        or np.any(cue_specs[2:] < 0)
        or not np.isfinite(strike).all()
        or cue.V0 < 0
        or cue.a**2 + cue.b**2 >= 1
    ):
        raise _unsupported("invalid cue parameters or strike")

    omega = np.array((linear.omega_ratio, circular.omega_ratio), dtype=np.float64)
    friction = np.array((pair.friction.a, pair.friction.b, pair.friction.c))
    if not (
        np.all((1 < omega) & (omega < 2))
        and np.all(np.isfinite(friction) & (friction >= 0))
    ):
        raise _unsupported("invalid Stronge omega ratio or Alciatore coefficients")
    return strike, cue_specs, friction.astype(np.float64), omega


def _pack_balls(balls: tuple[Ball, ...]):
    rvw = np.empty((len(balls), 3, 3), dtype=np.float64)
    states = np.empty(len(balls), dtype=np.int64)
    params = np.empty((len(balls), 9), dtype=np.float64)
    origins = np.empty(len(balls), dtype=np.float64)
    for i, ball in enumerate(balls):
        p, state = ball.params, ball.state
        if (
            type(ball) is not Ball
            or not isinstance(state.rvw, np.ndarray)
            or state.rvw.shape != (3, 3)
            or state.rvw.dtype != np.float64
            or not np.isfinite(state.rvw).all()
            or not math.isfinite(state.t)
            or state.t < 0
        ):
            raise _unsupported("each ball needs a finite native FP64 state and clock")
        if state.s == const.pocketed:
            if state.rvw[0, 2] > 0 or np.any(state.rvw[1:]):
                raise _unsupported("pocketed balls must have a stationary pocket state")
        elif (
            state.s not in const.on_table
            or state.rvw[0, 2] != p.R
            or state.rvw[1, 2] != 0
        ):
            raise _unsupported(
                "only planar on-table and pocketed ball states are supported"
            )
        rvw[i], states[i], origins[i] = state.rvw, state.s, state.t
        params[i] = p.R, p.m, p.u_s, p.u_sp, p.u_r, p.g, p.e_b, p.e_c, p.f_c

    if (
        not np.isfinite(params).all()
        or np.any(params[:, :6] <= 0)
        or np.any(params[:, 6] < 0)
        or np.any(params[:, 6:8] > 1)
        or np.any(params[:, 7:] <= 0)
        or np.any(params[:, :2] != params[0, :2])
    ):
        raise _unsupported("invalid ball parameters, or different masses or radii")
    return rvw, states, params, origins


def _pack_table(table: Table, radius: float):
    rows = []
    for key, rail in table.cushion_segments.linear.items():
        if (
            type(rail) is not LinearCushionSegment
            or key != rail.id
            or rail.direction
            not in (
                CushionDirection.SIDE1,
                CushionDirection.SIDE2,
                CushionDirection.BOTH,
            )
            or rail.p1.shape != (3,)
            or rail.p2.shape != (3,)
            or rail.p1[2] != rail.p2[2]
            or np.array_equal(rail.p1, rail.p2)
            or rail.nose_radius < 0
            or (radius + rail.nose_radius) ** 2 <= (rail.height - radius) ** 2
        ):
            raise _unsupported("invalid linear cushion geometry")
        rows.append(
            (
                rail.lx,
                rail.ly,
                rail.l0,
                rail.direction,
                rail.nose_radius,
                rail.height,
                *rail.p1,
                *rail.p2,
            )
        )
    linear = np.array(rows, dtype=np.float64).reshape(-1, 12)

    rows = []
    for key, jaw in table.cushion_segments.circular.items():
        if type(jaw) is not CircularCushionSegment or key != jaw.id or jaw.radius <= 0:
            raise _unsupported("invalid circular cushion geometry")
        rows.append((jaw.a, jaw.b, jaw.radius, jaw.height))
    circular = np.array(rows, dtype=np.float64).reshape(-1, 4)

    rows = []
    for key, pocket in table.pockets.items():
        if (
            type(pocket) is not Pocket
            or key != pocket.id
            or pocket.radius <= 0
            or pocket.depth < 0
        ):
            raise _unsupported("invalid pocket geometry")
        rows.append((pocket.a, pocket.b, pocket.radius, pocket.depth))
    pockets = np.array(rows, dtype=np.float64).reshape(-1, 4)
    geometry = (linear, circular, pockets)
    if not all(np.isfinite(values).all() for values in geometry):
        raise _unsupported("table geometry must be finite")
    return geometry


class _History(NamedTuple):
    rvw: NDArray[np.float64]
    states: NDArray[np.int64]
    times: NDArray[np.float64]
    slots: NDArray[np.int64]
    pre: NDArray[np.float64]
    pre_states: NDArray[np.int64]

    @classmethod
    def allocate(cls, rows: int, balls: int) -> _History:
        return cls(
            np.empty((rows, balls, 3, 3)),
            np.empty((rows, balls), dtype=np.int64),
            np.empty(rows),
            np.empty(rows, dtype=np.int64),
            np.empty((rows, 2, 3, 3)),
            np.empty((rows, 2), dtype=np.int64),
        )

    def grow(self, count: int, balls: int) -> _History:
        history = self.allocate(
            min(len(self.times) * 2, _MAX_HISTORY_EVENTS + 1), balls
        )
        for original, extended in zip(self, history, strict=True):
            extended[: count + 1] = original[: count + 1]
        return history


def _restore_history(shot: System, jobs, history: _History, count: int) -> None:
    from pooltool.evolution.event_based.compiled_fp64.kernel import (
        CIRCULAR,
        LINEAR,
        PAIR,
        POCKET,
        STICK,
        TRANSITION,
    )

    balls = tuple(shot.balls.values())
    linear = tuple(shot.table.cushion_segments.linear.values())
    circular = tuple(shot.table.cushion_segments.circular.values())
    pockets = tuple(shot.table.pockets.values())
    shot._update_history(events.null_event(time=0))
    for row in range(1, count + 1):
        kind, a, b = jobs[history.slots[row]]
        time = float(history.times[row])
        prior = float(history.times[row - 1])
        evolved_time = prior + (time - prior)
        ball = balls[a]
        before, after = int(history.pre_states[row, 0]), int(history.states[row, a])
        ball.state = BallState(history.pre[row, 0].copy(), before, evolved_time)
        if kind == STICK:
            event = events.stick_ball_collision(shot.cue, ball, time)
        elif kind == PAIR:
            balls[b].state = BallState(
                history.pre[row, 1].copy(),
                int(history.pre_states[row, 1]),
                evolved_time,
            )
            event = events.ball_ball_collision(ball, balls[b], time)
        elif kind == CIRCULAR:
            event = events.ball_circular_cushion_collision(ball, circular[b], time)
        elif kind == LINEAR:
            event = events.ball_linear_cushion_collision(ball, linear[b], time)
        elif kind == POCKET:
            event = events.ball_pocket_collision(ball, pockets[b], time)
        else:
            assert kind == TRANSITION
            event = _TRANSITIONS[before, after](ball, time)

        _snapshot_initial(shot, event)
        for i, current in enumerate(balls):
            current.state = BallState(
                history.rvw[row, i].copy(),
                int(history.states[row, i]),
                evolved_time if kind == TRANSITION and i == a else time,
            )
        if kind == POCKET:
            pockets[b].add(ball.id)
        _snapshot_final(shot, event)
        shot._update_history(event)


def simulate_compiled(
    shot: System,
    engine: SimulationEngine,
    inplace: bool,
    continuous: bool,
    dt: float | None,
    t_final: float | None,
    include: set[events.EventType],
    max_events: int,
) -> System:
    if (
        type(shot) is not System
        or type(shot.table) is not Table
        or type(shot.cue) is not Cue
    ):
        raise _unsupported("native System, Table, and Cue objects are required")
    if include != set(events.EventType):
        raise _unsupported("custom event inclusion is not supported")
    step = 0.01 if dt is None else dt
    if continuous and (not math.isfinite(step) or step <= 0):
        raise _unsupported("continuous dt must be finite and positive")
    if type(max_events) is not int or (t_final is not None and math.isnan(t_final)):
        raise _unsupported("expected an integer event limit and a non-NaN time limit")
    if shot.cue.cue_ball_id not in shot.balls or any(
        key != ball.id for key, ball in shot.balls.items()
    ):
        raise _unsupported("ball identities and cue ball must match the System")
    strike, cue_specs, friction, omega = _pack_engine(engine, shot.cue)
    rvw, states, params, origins = _pack_balls(tuple(shot.balls.values()))
    geometry = _pack_table(shot.table, float(params[0, 0]))

    from pooltool.evolution.event_based.compiled_fp64.kernel import (
        CIRCULAR,
        COMPLETE,
        EVENT_LIMIT,
        LINEAR,
        MORE,
        OVERFLOW,
        PAIR,
        POCKET,
        STICK,
        TIME_LIMIT,
        TRANSITION,
        run_chunk,
    )

    n = len(states)
    cue = tuple(shot.balls).index(shot.cue.cue_ball_id)
    rows = [(STICK, cue, -1), *((TRANSITION, i, -1) for i in range(n))]
    rows.extend((PAIR, a, b) for a, b in combinations(range(n), 2))
    for kind, components in zip((LINEAR, CIRCULAR, POCKET), geometry, strict=True):
        rows.extend((kind, a, b) for a, b in product(range(n), range(len(components))))
    jobs = np.array(rows, dtype=np.int64)
    history = _History.allocate(min(_CHUNK, _MAX_HISTORY_EVENTS) + 1, n)
    history.rvw[0], history.states[0], history.times[0], history.slots[0] = (
        rvw,
        states,
        0.0,
        -1,
    )
    generations = np.zeros(n, dtype=np.int64)
    epochs = np.full(len(jobs), -1, dtype=np.int64)
    times, ranks = np.empty(len(jobs)), np.empty(len(jobs), dtype=np.int64)
    transition_end = np.empty(n, dtype=np.int64)
    count = sequence = 0
    max_time = math.inf if t_final is None else float(t_final)
    while True:
        if count + 1 == len(history.times) and count < _MAX_HISTORY_EVENTS:
            history = history.grow(count, n)
        chunk = max(1, min(_CHUNK, len(history.times) - count - 1))
        try:
            status, count, clock, sequence, slot, detail = run_chunk(
                rvw,
                states,
                params,
                geometry,
                jobs,
                strike,
                cue_specs,
                friction,
                omega,
                generations,
                epochs,
                times,
                ranks,
                transition_end,
                origins,
                sequence,
                *history,
                count,
                max_events,
                max_time,
                chunk,
            )
        except (ArithmeticError, AssertionError, ValueError) as error:
            raise SimulateError(f"Compiled FP64 numerical failure: {error}") from error
        if status != MORE:
            break
    if status == OVERFLOW:
        raise SimulateError(
            f"Compiled FP64 exceeded {_MAX_HISTORY_EVENTS} retained events"
        )
    if status not in (COMPLETE, TIME_LIMIT, EVENT_LIMIT):
        raise SimulateError(
            f"Compiled FP64 failed after {count} events (status {status}, slot {slot}, detail {detail})"
        )
    if not np.isfinite(rvw).all() or (
        status == COMPLETE and any(int(s) in const.energetic for s in states)
    ):
        raise SimulateError("Compiled FP64 ended with invalid or unresolved motion")

    # Reconstruct and, if requested, interpolate before publishing any changes
    # to the caller. The event loop is not rerun to obtain native snapshots.
    result = System(
        shot.cue.copy(),
        shot.table.copy(),
        {key: ball.copy(drop_history=True) for key, ball in shot.balls.items()},
    )
    result.reset_history()
    _restore_history(result, jobs, history, count)
    if status in (COMPLETE, TIME_LIMIT):
        result._update_history(events.null_event(time=float(clock)))
    if (
        status in (TIME_LIMIT, EVENT_LIMIT)
        and max_events > 0
        and count == max_events + 2
    ):
        result.stop_balls()
        result._update_history(events.null_event(time=float(clock)))
    if continuous:
        continuize(result, dt=step, inplace=True)
    if not inplace:
        return result

    for key, ball in shot.balls.items():
        updated = result.balls[key]
        ball.state, ball.history, ball.history_cts = (
            updated.state,
            updated.history,
            updated.history_cts,
        )
    for key, pocket in shot.table.pockets.items():
        pocket.contains.update(result.table.pockets[key].contains)
    shot.t, shot.events = result.t, result.events
    return shot
