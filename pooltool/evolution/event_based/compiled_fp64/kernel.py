"""Bounded compiled event loop and retained FP64 history for planar simulations."""

import math

import numpy as np
from numba import njit

from pooltool import constants as const
from pooltool import ptmath
from pooltool.evolution.event_based.compiled_fp64.contact import resolve_cushion
from pooltool.evolution.event_based.compiled_fp64.prediction import (
    ball_ball_time,
    circular_time,
    linear_time,
    pocket_time,
    transition_time,
)
from pooltool.evolution.event_based.compiled_fp64.resolution import (
    final_motion,
    resolve_ball_pair,
    resolve_cue,
    resolve_transition,
)
from pooltool.physics.evolve import evolve_ball_motion

STICK, TRANSITION, PAIR, CIRCULAR, LINEAR, POCKET = range(6)
MORE, COMPLETE, EVENT_LIMIT, TIME_LIMIT, OVERFLOW, INVALID_TIME, INVALID_CONTACT = (
    range(7)
)

# Category precedence and stable order from the stock planar EventDetector.
TIERS = (1, 2, 4, 4, 4, 2)
CATEGORY_ORDER = (STICK, TRANSITION, LINEAR, CIRCULAR, POCKET, PAIR)


@njit(cache=True)
def _energy(rvw, params):
    radius, mass, gravity = params[0], params[1], params[5]
    linear = mass * ptmath.norm3d(rvw[1]) ** 2 / 2
    rotational = (2 / 5 * mass * radius**2) * ptmath.norm3d(rvw[2]) ** 2 / 2
    potential = mass * gravity * (rvw[0, 2] - radius)
    return linear + rotational + potential


@njit(cache=True)
def _event_energy(slot, rvw, params, jobs, strike):
    kind, a, b = jobs[slot]
    if kind == STICK:
        return strike[0] ** 2
    if kind == PAIR:
        m1, m2 = params[a, 1], params[b, 1]
        return (
            0.5 * (m1 * m2 / (m1 + m2)) * ptmath.squared_norm3d(rvw[a, 1] - rvw[b, 1])
        )
    return _energy(rvw[a], params[a])


@njit(cache=True)
def _select(rvw, params, jobs, strike, ranks, times, winners):
    """Choose the stable minimum in each bucket, then apply cross-bucket priority."""
    winners[:] = -1
    for slot in range(len(jobs)):
        kind = jobs[slot, 0]
        incumbent = winners[kind]
        if (
            incumbent < 0
            or times[slot] < times[incumbent]
            or (times[slot] == times[incumbent] and ranks[slot] < ranks[incumbent])
        ):
            winners[kind] = slot

    best = -1
    for kind in CATEGORY_ORDER:
        slot = winners[kind]
        if slot < 0 or times[slot] == math.inf:
            continue
        if best < 0 or times[slot] < times[best]:
            best = slot
        elif times[slot] == times[best]:
            tier, best_tier = TIERS[kind], TIERS[jobs[best, 0]]
            if tier < best_tier or (
                tier == best_tier
                and _event_energy(slot, rvw, params, jobs, strike)
                > _event_energy(best, rvw, params, jobs, strike)
            ):
                best = slot
    return best


@njit(cache=True)
def _evolve(rvw, states, params, dt):
    for a in range(len(states)):
        if states[a] == const.stationary or states[a] == const.pocketed:
            continue
        p = params[a]
        value, _ = evolve_ball_motion(
            states[a], rvw[a], p[0], p[1], p[2], p[3], p[4], p[5], dt
        )
        # The simulation preserves the old label until the resolver updates it.
        rvw[a, :, :] = value


@njit(cache=True)
def _next_stick_time(clock, cue_ball, rvw, states, params, strike):
    if clock != 0 or states[cue_ball] == const.pocketed or strike[0] <= 0:
        return math.inf
    for a in range(len(states)):
        if states[a] != const.pocketed and _energy(rvw[a], params[a]) > 0.0:
            return math.inf
    return 0.0


@njit(cache=True)
def _valid_height(rvw, state, radius):
    return state == const.pocketed or (state != const.airborne and rvw[0, 2] == radius)


@njit(cache=True, nogil=True)
def run_chunk(
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
    cache_epoch,
    times,
    ranks,
    transition_end,
    transition_origin,
    cache_sequence,
    h_rvw,
    h_states,
    h_time,
    h_event,
    h_pre,
    h_pre_states,
    count,
    max_events,
    max_time,
    chunk_events,
):
    """Advance a chunk, retaining numeric rows for normal Pooltool snapshots.

    Row zero is the initial snapshot. Later rows hold all post-event states and
    the pre-event state of each participating ball. Cached survivor times are
    absolute. The adapter materializes terminal null snapshots.
    """
    linear, circular, pockets = geometry
    winners = np.empty(6, dtype=np.int64)
    clock = h_time[count]
    for _ in range(chunk_events):
        for slot in range(len(jobs)):
            kind, a, b = jobs[slot]
            epoch = generations[a]
            if kind == PAIR:
                epoch = max(epoch, generations[b])
            if cache_epoch[slot] == epoch:
                continue
            cache_epoch[slot] = epoch
            # Transition replacement keeps key order. Collision invalidation
            # re-inserts the affected keys after all surviving entries.
            ranks[slot] = a if kind == TRANSITION else cache_sequence
            cache_sequence += 1
            if kind == STICK:
                dt = _next_stick_time(clock, a, rvw, states, params, strike)
            elif kind == TRANSITION:
                dt, end = transition_time(rvw[a], states[a], params[a])
                transition_end[a] = end
                if end != states[a] and not math.isfinite(dt):
                    return INVALID_TIME, count, clock, cache_sequence, slot, 0
            elif kind == PAIR:
                dt = ball_ball_time(
                    rvw[a], rvw[b], states[a], states[b], params[a], params[b]
                )
            elif kind == CIRCULAR:
                dt = circular_time(rvw[a], states[a], params[a], circular[b])
            elif kind == LINEAR:
                dt = linear_time(rvw[a], states[a], params[a], linear[b])
            else:
                dt = pocket_time(rvw[a], states[a], params[a], pockets[b])
            if math.isnan(dt) or dt < 0:
                return INVALID_TIME, count, clock, cache_sequence, slot, 0
            deadline = (transition_origin[a] if kind == TRANSITION else clock) + dt
            if math.isfinite(dt) and not math.isfinite(deadline):
                return INVALID_TIME, count, clock, cache_sequence, slot, 0
            times[slot] = deadline

        slot = _select(rvw, params, jobs, strike, ranks, times, winners)
        if slot < 0:
            return COMPLETE, count, clock, cache_sequence, -1, 0
        t = times[slot]
        if not math.isfinite(t) or t < clock:
            return INVALID_TIME, count, clock, cache_sequence, slot, 0
        row = count + 1
        if row >= len(h_time):
            return OVERFLOW, count, clock, cache_sequence, slot, 0

        dt = t - clock
        evolved_time = clock + dt
        _evolve(rvw, states, params, dt)
        kind, a, b = jobs[slot]
        h_pre[row, 0], h_pre_states[row, 0] = rvw[a], states[a]
        detail = 0
        if kind == STICK:
            resolve_cue(rvw[a], params[a], strike, cue_specs)
            states[a] = final_motion(rvw[a], params[a, 0])
        elif kind == TRANSITION:
            end = transition_end[a]
            if not resolve_transition(rvw[a], states[a], end):
                detail = 1
            states[a] = end
        elif kind == PAIR:
            h_pre[row, 1], h_pre_states[row, 1] = rvw[b], states[b]
            ok, left_state, right_state = resolve_ball_pair(
                rvw[a], rvw[b], states[a], states[b], params[a], params[b], friction
            )
            if not ok:
                detail = 2
            states[a], states[b] = left_state, right_state
            generations[b], transition_origin[b] = row, t
        elif kind == POCKET:
            rvw[a, :, :] = 0
            rvw[a, 0, 0], rvw[a, 0, 1], rvw[a, 0, 2] = (
                pockets[b, 0],
                pockets[b, 1],
                -pockets[b, 3],
            )
            states[a] = const.pocketed
        else:
            if kind == LINEAR:
                contact = resolve_cushion(rvw[a], params[a], linear[b], True, omega[0])
            else:
                contact = resolve_cushion(
                    rvw[a], params[a], circular[b], False, omega[1]
                )
            if contact != 0:
                detail = 10 + contact
            states[a] = final_motion(rvw[a], params[a, 0])
        if (
            detail
            or not np.all(np.isfinite(rvw))
            or not _valid_height(rvw[a], states[a], params[a, 0])
            or (kind == PAIR and not _valid_height(rvw[b], states[b], params[b, 0]))
        ):
            return INVALID_CONTACT, count, clock, cache_sequence, slot, detail

        generations[a] = row
        # Canonical transition snapshots retain the evolved pre-event time;
        # the other resolvers stamp their selected time before taking snapshots.
        transition_origin[a] = evolved_time if kind == TRANSITION else t
        count, clock = row, t
        h_event[row], h_time[row] = slot, t
        h_rvw[row], h_states[row] = rvw, states
        if t >= max_time:
            return TIME_LIMIT, count, clock, cache_sequence, -1, 0
        # Stock checks its preincrement event counter against the requested cap.
        if max_events > 0 and count - 1 > max_events:
            return EVENT_LIMIT, count, clock, cache_sequence, -1, 0
    return MORE, count, clock, cache_sequence, -1, 0
