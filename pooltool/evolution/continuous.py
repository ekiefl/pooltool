"""Module for building a time-dense system trajectory and interpolating ball states

For an explanation, see :func:`continuize` and :func:`interpolate_ball_states`
"""

from collections.abc import Sequence

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.physics.evolve as evolve
from pooltool.objects.ball.datatypes import Ball, BallHistory, BallState
from pooltool.system.datatypes import System


def continuize(system: System, dt: float = 0.01, inplace: bool = False) -> System:
    """Create a ``BallHistory`` for each ball with many timepoints

    When pooltool simulates a shot, it evolves the system using an `event-based shot
    evolution algorithm
    <https://ekiefl.github.io/2020/12/20/pooltool-alg/#continuous-event-based-evolution>`_.
    This means pooltool only timestamps the ball states during events--not between
    events. This makes simulation fast, but provides insufficient trajectory information
    if you wanted to visualize or plot ball trajectories over time.

    *Continuizing* the shot means tracking the ball states with higher temporal
    resolution, so that the ball trajectories between events can be recapitulated. It's
    a misnomer because the states are still tracked over discrete time steps ``dt``
    seconds apart. *i.e.* not continuous.

    This function calculates the "continous" timestamps for each ball and stores them in
    :attr:`pooltool.objects.Ball.history_cts` (the event-based timestamps are preserved,
    and are stored in :attr:`pooltool.objects.Ball.history`)

    The continous timepoints are shared between all balls and are uniformly spaced
    (except for the last timepoint, which occurs at the final event, which necessarily
    occurs less than ``dt`` after the second last timepoint).

    Args:
        dt:
            This is the spacing between each timepoint. 0.01 looks visually accurate at
            60fps at a playback speed of 1. Function runtime is inversely proportional
            to dt.
        inplace:
            By default, a copy of the passed system is continuized and returned. This
            leaves the passed system unmodified. If inplace is set to True, the passed
            system is modified in place, meaning no copy is made and the returned system
            is the passed system. For a more practical distinction, see Examples below.

    Examples:
        Standard usage:

        >>> import pooltool as pt
        >>> system = pt.simulate(pt.System.example())

        The system has been simulated, so their ``history`` attributes are populated:

        >>> len(system.balls["cue"].history)
        14
        >>> system.balls["cue"].history[0]
        BallState(rvw=array([[0.4953  , 0.9906  , 0.028575],
               [0.      , 0.      , 0.      ],
               [0.      , 0.      , 0.      ]]), s=0, t=0.0)
        >>> system.balls["cue"].history[-1]
        BallState(rvw=array([[0.7464286761774921, 1.247940272192023 , 0.028575          ],
               [0.                , 0.                , 0.                ],
               [0.                , 0.                , 0.                ]]), s=0, t=5.193035203405666)

        However, the system has not been continuized, so their ``history_cts`` attributes are empty:

        >>> len(system.balls["cue"].history_cts)
        0

        After continuizing, the continuous ball histories are populated with many timestamps:

        >>> continuized_system = pt.continuize(system, inplace=False)
        >>> continuized_system.continuized
        True
        >>> len(continuized_system.balls["cue"].history_cts)
        523

        You can also modify the system in place:

        >>> import pooltool as pt
        >>> system = pt.simulate(pt.System.example())
        >>> continuized_system = pt.continuize(system, inplace=True)
        >>> assert system.continuized
        >>> assert continuized_system.continuized
        >>> assert system is continuized_system

        Notice that the returned system *is* the continuized system. Therefore, there is
        no point catching the return object when inplace is True:

        >>> import pooltool as pt
        >>> system = pt.simulate(pt.System.example())
        >>> assert not system.continuized
        >>> pt.continuize(system, inplace=True)
        >>> assert system.continuized

    See Also:
        - :attr:`pooltool.objects.Ball.history_cts`
        - :func:`pooltool.evolution.simulate`
    """
    if not inplace:
        system = system.copy()

    for ball in system.balls.values():
        ball.history_cts = continuize_ball(ball, dt)

    return system


def continuize_ball(ball: Ball, dt: float) -> BallHistory:
    """Build a ball's time-dense history from its event-based history

    This is the per-ball work of :func:`continuize`. The ball is not modified.

    Args:
        ball:
            A ball whose :attr:`pooltool.objects.Ball.history` spans the shot.
        dt:
            Simulation seconds between timestamps.

    Returns:
        A history holding the ball's initial state, a state every ``dt`` seconds, and
        its final state, which is within ``dt`` of the last timestamp.
    """
    params = ball.params
    rvws, ss, ts = ball.history.vectorize()
    return BallHistory.from_vectorization(
        _continuize_states(
            rvws,
            ss,
            ts,
            params.R,
            params.m,
            params.u_s,
            params.u_sp,
            params.u_r,
            params.g,
            dt,
        )
    )


@jit(nopython=True, cache=const.use_numba_cache)
def _continuize_states(
    rvws: NDArray[np.float64],
    ss: NDArray[np.float64],
    ts: NDArray[np.float64],
    R: float,
    m: float,
    u_s: float,
    u_sp: float,
    u_r: float,
    g: float,
    dt: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Evolve an event-based history onto a uniform time grid

    Each timestamp is evolved from the last event state at or before it. Motion state
    transitions are events, so a ball's motion state never changes between an event
    state and the timestamps evolved from it. The grid starts at the first state's
    time and steps by ``dt``; the final event state is appended after it.
    """
    num_events = len(ts)
    num_uniform = int((ts[-1] - ts[0]) // dt) + 1
    num_states = num_uniform + 1

    out_rvws = np.empty((num_states, 3, 3))
    out_ss = np.empty(num_states)
    out_ts = np.empty(num_states)

    out_rvws[0] = rvws[0]
    out_ss[0] = ss[0]
    out_ts[0] = ts[0]

    ref = 0
    for n in range(1, num_uniform):
        t = ts[0] + n * dt
        while ref + 1 < num_events and ts[ref + 1] <= t:
            ref += 1
        rvw, s = evolve.evolve_ball_motion(
            int(ss[ref]), rvws[ref], R, m, u_s, u_sp, u_r, g, t - ts[ref]
        )
        out_rvws[n] = rvw
        out_ss[n] = s
        out_ts[n] = t

    out_rvws[-1] = rvws[-1]
    out_ss[-1] = ss[-1]
    out_ts[-1] = ts[-1]

    return out_rvws, out_ss, out_ts


def interpolate_ball_states(
    ball: Ball,
    timestamps: NDArray[np.float64] | Sequence[float],
    *,
    extrapolate: bool = False,
) -> list[BallState]:
    """Calculate exact ball states at arbitrary timestamps.

    This function calculates the precise ball states at arbitrary timestamps by evolving
    the ball from the nearest preceding event state using the same physics model as the
    simulation. It provides physically accurate positions, velocities, and angular velocities
    according to the ball's motion equations.

    Args:
        ball:
            The Ball object containing the history and physical parameters.
        timestamps:
            A sequence or numpy array of timestamps at which to calculate ball states.
            Should be in ascending order and within the history's time range.
        extrapolate:
            If True, timestamps outside the history's time range will use the nearest boundary
            state (initial or final). If False (default), a ValueError is raised for timestamps
            outside the range.

    Returns:
        A list of BallState objects corresponding to the given timestamps.

    Raises:
        ValueError:
            If history is empty or if timestamps are out of range and extrapolate is False.

    Examples:
        >>> import pooltool as pt
        >>> import numpy as np
        >>> system = pt.simulate(pt.System.example())
        >>> ball = system.balls["cue"]
        >>> # Get ball states at specific timestamps
        >>> timestamps = np.array([0.5, 1.0, 1.5])
        >>> states = pt.interpolate_ball_states(ball, timestamps)
        >>> # Use the states
        >>> states[0].rvw[0]  # Position at t=0.5
        array([x, y, z])
    """
    history = ball.history
    params = ball.params

    if history.empty:
        raise ValueError("Cannot interpolate from empty history")

    if not isinstance(timestamps, np.ndarray):
        timestamps = np.array(timestamps, dtype=np.float64)

    if not np.all(np.diff(timestamps) >= 0):
        raise ValueError("Timestamps must be in ascending order")

    min_time = history[0].t
    max_time = history[-1].t

    if not extrapolate and (timestamps[0] < min_time or timestamps[-1] > max_time):
        raise ValueError(
            f"Timestamps must be within history time range ({min_time}, {max_time})"
        )

    result_states = []
    history_array = history.states
    history_len = len(history_array)

    idx = 0

    for t in timestamps:
        if t < min_time:
            result_states.append(history_array[0].copy())
            continue
        elif t > max_time:
            result_states.append(history_array[-1].copy())
            continue

        # Find the nearest preceding state in history
        while idx < history_len - 1 and history_array[idx + 1].t <= t:
            idx += 1

        # Go back one step if we've advanced too far
        if history_array[idx].t > t and idx > 0:
            idx -= 1

        # Get the reference state to evolve from
        ref_state = history_array[idx]

        if abs(ref_state.t - t) < 1e-10:
            # The timestamp exactly matches a history state, use it directly
            result_states.append(ref_state.copy())
            continue

        evolve_time = t - ref_state.t
        rvw, s = evolve.evolve_ball_motion(
            state=ref_state.s,
            rvw=ref_state.rvw,
            R=params.R,
            m=params.m,
            u_s=params.u_s,
            u_sp=params.u_sp,
            u_r=params.u_r,
            g=params.g,
            t=evolve_time,
        )

        result_states.append(BallState(rvw=rvw, s=s, t=t))

    return result_states
