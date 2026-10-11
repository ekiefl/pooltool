"""Render-only continuation of a ball that has left the table.

The simulation freezes an off-table ball where it crossed the table boundary. For
display, the ball instead keeps flying, lands on the rail top or the floor, bounces,
skids to a halt, and fades out. This module builds that tail as ball history states
with ordinary motion-state labels, so the animation machinery treats it like any other
motion. Nothing here feeds back into the simulation.

The tail is a fixed-step integration on the render grid rather than a piecewise
analytic solution. It is short, it fades, and nothing depends on its accuracy. The table
is treated as a box (see :class:`~pooltool.ani.table_box.TableBox`). A ball that has
left the table only ever moves away from it, so the box's sides are never struck; only
its top and the floor around it are.
"""

from math import sqrt

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.ani.table_box import TableBox
from pooltool.events.datatypes import Event, EventType
from pooltool.objects.ball.datatypes import Ball, BallHistory, BallParams, BallState
from pooltool.system.datatypes import System

TAIL_DURATION = 1.0
"""Seconds the ball is animated for after crossing the table boundary.

The ball is halted at the end of the tail.
"""

FADE_START = 0.5
"""Seconds after crossing the table boundary that the ball begins to fade out.

The fade lasts until ``TAIL_DURATION``, when the ball is invisible.
"""

RESTITUTION = 0.5
"""Ratio of outgoing to incoming vertical speed at a bounce."""

RAIL_BOUNCE_SPEED_RETENTION = 0.95
"""Fraction of horizontal speed kept through a bounce on the rail top."""

FLOOR_BOUNCE_SPEED_RETENTION = 0.7
"""Fraction of horizontal speed kept through a bounce on the floor."""

RAIL_FRICTION = 0.05
"""Friction coefficient decelerating a ball that has settled onto the rail top."""

FLOOR_FRICTION = 0.1
"""Friction coefficient decelerating a ball that has settled onto the floor."""

MIN_BOUNCE_HEIGHT = 0.005
"""Bounces lower than this settle the ball onto the surface it struck."""


def crossing_event(system: System, ball_id: str) -> Event | None:
    """The event in which the ball left the table, if it did during this shot"""
    for event in system.events:
        if (
            event.event_type == EventType.BALL_OFF_TABLE
            and event.agents[0].id == ball_id
        ):
            return event
    return None


def exit_state(crossing: Event) -> BallState:
    """The ball's state at the instant it crossed the table boundary, before freezing

    The event records the ball as it was before resolution, so the state carries the
    exit velocity that the frozen state in the ball's history has discarded.
    """
    ball = crossing.agents[0].initial
    assert isinstance(ball, Ball)
    return ball.state


def with_tail(
    history: BallHistory,
    exit: BallState,
    params: BallParams,
    box: TableBox,
    dt: float,
) -> BallHistory:
    """Replace the frozen off-table states of a render history with the animated tail

    ``history`` is the ball's continuized history. Its states from the crossing onward
    are frozen where the ball left the table. They are replaced by the exit state and
    ``TAIL_DURATION`` seconds of tail sampled every ``dt`` after it.
    """
    R = params.R
    ss = history.ss
    k = int(np.argmax(ss == const.off_table))
    assert ss[k] == const.off_table

    r = exit.rvw[0].copy()
    if box.contains(r[0], r[1]) and r[2] - R < box.top:
        r[2] = box.top + R

    n = round(TAIL_DURATION / dt)
    tail_rvws, tail_ss = _tail(
        r,
        exit.rvw[1],
        exit.rvw[2],
        R,
        params.g,
        box.x_min,
        box.x_max,
        box.y_min,
        box.y_max,
        box.top,
        box.floor,
        dt,
        n,
    )

    exit_rvw = np.array([r, exit.rvw[1], exit.rvw[2]])
    rvws = np.concatenate([history.rvws[:k], exit_rvw[None], tail_rvws])
    ss = np.concatenate([ss[:k], [const.airborne], tail_ss])
    ts = np.concatenate([history.ts[:k], [exit.t], exit.t + dt * np.arange(1, n + 1)])
    return BallHistory.from_vectorization((rvws, ss, ts))


@jit(nopython=True, cache=const.use_numba_cache)
def _over_rail(
    x: float, y: float, x_min: float, x_max: float, y_min: float, y_max: float
) -> bool:
    return x_min <= x <= x_max and y_min <= y <= y_max


@jit(nopython=True, cache=const.use_numba_cache)
def _tail(
    r0: NDArray[np.float64],
    v0: NDArray[np.float64],
    w0: NDArray[np.float64],
    R: float,
    g: float,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    top: float,
    floor: float,
    dt: float,
    n: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Step the off-table trajectory ``n`` times by ``dt``, returning each state

    The ball falls under gravity until its bottom dips below the surface beneath it,
    where it is snapped to the surface and bounced. A bounce too low to matter settles
    the ball, which then decelerates under the friction of the surface it is on,
    taking off again if it runs off the rail edge. The last state is halted.
    """
    rvws = np.empty((n, 3, 3))
    ss = np.empty(n)

    r = r0.copy()
    v = v0.copy()
    w = w0.copy()
    settled = False

    for i in range(n):
        if settled:
            on_rail = _over_rail(r[0], r[1], x_min, x_max, y_min, y_max)
            friction = RAIL_FRICTION if on_rail else FLOOR_FRICTION
            speed = sqrt(v[0] * v[0] + v[1] * v[1])
            decel = friction * g * dt
            if speed <= decel:
                v[0] = 0.0
                v[1] = 0.0
            else:
                v[0] -= decel * v[0] / speed
                v[1] -= decel * v[1] / speed
            r += v * dt
            if on_rail and not _over_rail(r[0], r[1], x_min, x_max, y_min, y_max):
                settled = False
        else:
            v[2] -= g * dt
            r += v * dt
            on_rail = _over_rail(r[0], r[1], x_min, x_max, y_min, y_max)
            surface = top if on_rail else floor
            if r[2] - R < surface:
                r[2] = surface + R
                vz = -RESTITUTION * v[2]
                retention = (
                    RAIL_BOUNCE_SPEED_RETENTION
                    if on_rail
                    else FLOOR_BOUNCE_SPEED_RETENTION
                )
                v[0] *= retention
                v[1] *= retention
                if vz * vz / (2.0 * g) < MIN_BOUNCE_HEIGHT:
                    v[2] = 0.0
                    settled = True
                else:
                    v[2] = vz

        if settled:
            w[0] = -v[1] / R
            w[1] = v[0] / R
            w[2] = 0.0
            s = const.stationary if v[0] == 0.0 and v[1] == 0.0 else const.rolling
        else:
            s = const.airborne

        rvws[i, 0] = r
        rvws[i, 1] = v
        rvws[i, 2] = w
        ss[i] = s

    rvws[n - 1, 1] = 0.0
    rvws[n - 1, 2] = 0.0
    ss[n - 1] = const.stationary
    return rvws, ss
