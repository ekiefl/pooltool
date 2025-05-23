# cython: language_level=3
import numpy as np
from itertools import combinations

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.events import (
    Event,
    EventType,
    ball_ball_collision,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    ball_pocket_collision,
    null_event,
)
from pooltool.evolution.event_based.cache import CollisionCache, TransitionCache
from pooltool.evolution.event_based import solve
from pooltool.ptmath.roots.quartic import QuarticSolver, solve_quartics

def get_next_event(shot, transition_cache=None, collision_cache=None, quartic_solver=QuarticSolver.HYBRID):
    event = null_event(time=np.inf)
    if transition_cache is None:
        transition_cache = TransitionCache.create(shot)
    if collision_cache is None:
        collision_cache = CollisionCache.create(shot)

    transition_event = transition_cache.get_next()
    if transition_event.time < event.time:
        event = transition_event

    ball_ball_event = get_next_ball_ball_collision(
        shot, collision_cache=collision_cache, solver=quartic_solver
    )
    if ball_ball_event.time < event.time:
        event = ball_ball_event

    ball_circular_cushion_event = get_next_ball_circular_cushion_event(
        shot, collision_cache=collision_cache, solver=quartic_solver
    )
    if ball_circular_cushion_event.time < event.time:
        event = ball_circular_cushion_event

    ball_linear_cushion_event = get_next_ball_linear_cushion_collision(
        shot, collision_cache=collision_cache
    )
    if ball_linear_cushion_event.time < event.time:
        event = ball_linear_cushion_event

    ball_pocket_event = get_next_ball_pocket_collision(
        shot, collision_cache=collision_cache, solver=quartic_solver
    )
    if ball_pocket_event.time < event.time:
        event = ball_pocket_event

    return event

def get_next_ball_ball_collision(shot, collision_cache, solver=QuarticSolver.HYBRID):
    cache = collision_cache.times.setdefault(EventType.BALL_BALL, {})
    possible = getattr(collision_cache, '_possible_pairs', None)
    if possible and EventType.BALL_BALL in possible:
        candidates = possible[EventType.BALL_BALL]
    else:
        candidates = [(b1.id, b2.id) for b1, b2 in combinations(shot.balls.values(), 2)]

    ball_pairs = []
    collision_coeffs = []
    for ball_pair in candidates:
        if ball_pair in cache:
            continue
        ball1 = shot.balls[ball_pair[0]]
        ball2 = shot.balls[ball_pair[1]]
        b1s, b1p = ball1.state, ball1.params
        b2s, b2p = ball2.state, ball2.params

        if b1s.s == const.pocketed or b2s.s == const.pocketed:
            cache[ball_pair] = np.inf
        elif b1s.s in const.nontranslating and b2s.s in const.nontranslating:
            cache[ball_pair] = np.inf
        elif ptmath.norm3d(b1s.rvw[0] - b2s.rvw[0]) < b1p.R + b2p.R:
            cache[ball_pair] = np.inf
        else:
            ball_pairs.append(ball_pair)
            collision_coeffs.append(
                solve.ball_ball_collision_coeffs(
                    rvw1=b1s.rvw,
                    rvw2=b2s.rvw,
                    s1=b1s.s,
                    s2=b2s.s,
                    mu1=(b1p.u_s if b1s.s == const.sliding else b1p.u_r),
                    mu2=(b2p.u_s if b2s.s == const.sliding else b2p.u_r),
                    m1=b1p.m,
                    m2=b2p.m,
                    g1=b1p.g,
                    g2=b2p.g,
                    R=b1p.R,
                )
            )

    if collision_coeffs:
        roots = solve_quartics(ps=np.array(collision_coeffs), solver=solver)
        for root, ball_pair in zip(roots, ball_pairs):
            cache[ball_pair] = shot.t + root

    ball_pair = min(cache, key=lambda k: cache[k])
    return ball_ball_collision(
        ball1=shot.balls[ball_pair[0]],
        ball2=shot.balls[ball_pair[1]],
        time=cache[ball_pair],
    )

def get_next_ball_circular_cushion_event(shot, collision_cache, solver=QuarticSolver.HYBRID):
    if not shot.table.has_circular_cushions:
        return null_event(np.inf)

    cache = collision_cache.times.setdefault(EventType.BALL_CIRCULAR_CUSHION, {})
    possible = getattr(collision_cache, '_possible_pairs', None)
    if possible and EventType.BALL_CIRCULAR_CUSHION in possible:
        candidates = possible[EventType.BALL_CIRCULAR_CUSHION]
    else:
        candidates = [
            (b.id, c.id)
            for b in shot.balls.values()
            for c in shot.table.cushion_segments.circular.values()
        ]

    ball_cushion_pairs = []
    collision_coeffs = []
    for obj_ids in candidates:
        if obj_ids in cache:
            continue
        ball = shot.balls[obj_ids[0]]
        state, params = ball.state, ball.params
        if state.s in const.nontranslating:
            cache[obj_ids] = np.inf
            continue
        ball_cushion_pairs.append(obj_ids)
        segment = shot.table.cushion_segments.circular[obj_ids[1]]
        collision_coeffs.append(
            solve.ball_circular_cushion_collision_coeffs(
                rvw=state.rvw,
                s=state.s,
                a=segment.a,
                b=segment.b,
                r=segment.radius,
                mu=(params.u_s if state.s == const.sliding else params.u_r),
                m=params.m,
                g=params.g,
                R=params.R,
            )
        )

    if collision_coeffs:
        roots = solve_quartics(ps=np.array(collision_coeffs), solver=solver)
        for root, ball_cushion_pair in zip(roots, ball_cushion_pairs):
            cache[ball_cushion_pair] = shot.t + root

    ball_id, cushion_id = min(cache, key=lambda k: cache[k])
    return ball_circular_cushion_collision(
        ball=shot.balls[ball_id],
        cushion=shot.table.cushion_segments.circular[cushion_id],
        time=cache[(ball_id, cushion_id)],
    )

def get_next_ball_linear_cushion_collision(shot, collision_cache):
    if not shot.table.has_linear_cushions:
        return null_event(np.inf)

    cache = collision_cache.times.setdefault(EventType.BALL_LINEAR_CUSHION, {})
    possible = getattr(collision_cache, '_possible_pairs', None)
    if possible and EventType.BALL_LINEAR_CUSHION in possible:
        candidates = possible[EventType.BALL_LINEAR_CUSHION]
    else:
        candidates = [
            (b.id, c.id)
            for b in shot.balls.values()
            for c in shot.table.cushion_segments.linear.values()
        ]

    for obj_ids in candidates:
        if obj_ids in cache:
            continue
        ball = shot.balls[obj_ids[0]]
        state, params = ball.state, ball.params
        if state.s in const.nontranslating:
            cache[obj_ids] = np.inf
            continue
        cushion = shot.table.cushion_segments.linear[obj_ids[1]]
        dtau_E = solve.ball_linear_cushion_collision_time(
            rvw=state.rvw,
            s=state.s,
            lx=cushion.lx,
            ly=cushion.ly,
            l0=cushion.l0,
            p1=cushion.p1,
            p2=cushion.p2,
            direction=cushion.direction,
            mu=(params.u_s if state.s == const.sliding else params.u_r),
            m=params.m,
            g=params.g,
            R=params.R,
        )
        cache[obj_ids] = shot.t + dtau_E

    obj_ids = min(cache, key=lambda k: cache[k])
    return ball_linear_cushion_collision(
        ball=shot.balls[obj_ids[0]],
        cushion=shot.table.cushion_segments.linear[obj_ids[1]],
        time=cache[obj_ids],
    )

def get_next_ball_pocket_collision(shot, collision_cache, solver=QuarticSolver.HYBRID):
    if not shot.table.has_pockets:
        return null_event(np.inf)

    cache = collision_cache.times.setdefault(EventType.BALL_POCKET, {})
    possible = getattr(collision_cache, '_possible_pairs', None)
    if possible and EventType.BALL_POCKET in possible:
        candidates = possible[EventType.BALL_POCKET]
    else:
        candidates = [
            (b.id, p.id)
            for b in shot.balls.values()
            for p in shot.table.pockets.values()
        ]

    ball_pocket_pairs = []
    collision_coeffs = []
    for obj_ids in candidates:
        if obj_ids in cache:
            continue
        ball = shot.balls[obj_ids[0]]
        state, params = ball.state, ball.params
        if state.s in const.nontranslating:
            cache[obj_ids] = np.inf
            continue
        pocket = shot.table.pockets[obj_ids[1]]
        ball_pocket_pairs.append(obj_ids)
        collision_coeffs.append(
            solve.ball_pocket_collision_coeffs(
                rvw=state.rvw,
                s=state.s,
                a=pocket.a,
                b=pocket.b,
                r=pocket.radius,
                mu=(params.u_s if state.s == const.sliding else params.u_r),
                m=params.m,
                g=params.g,
                R=params.R,
            )
        )

    if collision_coeffs:
        roots = solve_quartics(ps=np.array(collision_coeffs), solver=solver)
        for root, ball_pocket_pair in zip(roots, ball_pocket_pairs):
            cache[ball_pocket_pair] = shot.t + root

    ball_id, pocket_id = min(cache, key=lambda k: cache[k])
    return ball_pocket_collision(
        ball=shot.balls[ball_id],
        pocket=shot.table.pockets[pocket_id],
        time=cache[(ball_id, pocket_id)],
    )