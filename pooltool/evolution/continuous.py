"""Module for building a time-dense system trajectory and interpolating ball states

For an explanation, see :func:`continuize` and :func:`interpolate_ball_states`
"""

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

import pooltool.physics.evolve as evolve
from pooltool.events import filter_ball
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

    # This is the exact number of timepoints that the ball histories will contain
    num_timestamps = int(system.events[-1].time // dt) + 1

    for ball in system.balls.values():
        # Create a new history and add the zeroth event
        history = BallHistory()
        history.add(ball.history[0])

        rvw, s = ball.history[0].rvw, ball.history[0].s

        # Get all events that the ball is involved in, even the null_event events
        # that mark the start and end times
        events = filter_ball(system.events, ball.id, keep_nonevent=True)

        # Tracks which event is currently being handled
        count = 0

        # The elapsed simulation time (as of the last timepoint)
        elapsed = 0.0

        for n in range(num_timestamps):
            if n == (num_timestamps - 1):
                # We made it to the end. the difference between the final time and
                # the elapsed time should be < dt
                assert events[-1].time - elapsed < dt
                break

            if events[count + 1].time - elapsed > dt:
                # This is the easy case. There is no upcoming event so we simply
                # evolve the state an amount dt
                evolve_time = dt

            else:
                # The next event (and perhaps an arbitrary number of subsequent
                # events) occurs before the next timestamp. Find the last event
                # between the current timestamp and the next timestamp. This will be
                # used as a launching point to simulate the ball state to the next
                # timestamp

                while True:
                    count += 1

                    if events[count + 1].time - elapsed > dt:
                        # OK, we found the last event between the current timestamp
                        # and the next timestamp. It is events[count].
                        break

                # We need to get the ball's outgoing state from the event. We'll
                # evolve the system from this state.
                state = events[count].get_ball(ball.id, initial=False).state.copy()

                rvw, s = state.rvw, state.s

                # Since this event occurs between two timestamps, we won't be
                # evolving a full dt. Instead, we evolve this much:
                evolve_time = elapsed + dt - events[count].time

            # Whether it was the hard path or the easy path, the ball state is
            # properly defined and we know how much we need to simulate.
            rvw, s = evolve.evolve_ball_motion(
                state=s,
                rvw=rvw,
                R=ball.params.R,
                m=ball.params.m,
                u_s=ball.params.u_s,
                u_sp=ball.params.u_sp,
                u_r=ball.params.u_r,
                g=ball.params.g,
                t=evolve_time,
            )

            history.add(BallState(rvw, s, elapsed + dt))
            elapsed += dt

        # There is a finale. The final state is missing from the continuous history,
        # whose final state is within dt of the true final state. We add the final
        # state to the continous history even though this breaks the promise of
        # uniformly spaced timestamps
        history.add(ball.history[-1])

        # Attach the newly created history to the ball
        ball.history_cts = history

    return system


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
