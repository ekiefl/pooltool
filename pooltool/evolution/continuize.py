import pooltool.physics.evolve as evolve
from pooltool.events import filter_ball
from pooltool.objects.ball.datatypes import BallHistory, BallState
from pooltool.system.datatypes import System


def continuize(system: System, dt: float = 0.01, inplace: bool = False) -> System:
    """Create BallHistory for each ball with many timepoints

    All balls share the same timepoints, and the timepoints are uniformly spaced, except
    for the last timepoint, which occurs at the final event, which is necessarily dt of
    the second last timepoint.

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

        >>> # Continuize a system
        >>> import pooltool as pt
        >>> system = pt.simulate(pt.System.example())
        >>> continuized_system = pt.continuize(system, inplace=False)
        >>> assert not system.continuized
        >>> assert continuized_system.continuized

        The returned system is continuized, but the passed system remains unchanged.

        You can also modify the system in place:

        >>> # Continuize a system in place
        >>> import pooltool as pt
        >>> system = pt.simulate(pt.System.example())
        >>> continuized_system = pt.continuize(system, inplace=True)
        >>> assert system.continuized
        >>> assert continuized_system.continuized
        >>> assert system is continuized_system

        Notice that the returned system _is_ the continuized system. Therefore, there is
        no point catching the return object when inplace is True:

        >>> # Simulate a system in place
        >>> import pooltool as pt
        >>> system = pt.simulate(pt.System.example())
        >>> assert not system.continuized
        >>> pt.continuize(system, inplace=True)
        >>> assert system.continuized

    Notes:
    The old continuize did not have uniform and equally spaced time points. That
    implementation can be found with

    `git checkout 7b2f7440f7d9ad18cba65c9e4862ee6bdc620631`

    (Look for pooltool.system.datatypes.continuize_heterogeneous)
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
                for agent in events[count].agents:
                    if agent.matches(ball):
                        state = agent.final.state.copy()  # type: ignore
                        break
                else:
                    raise ValueError("No agents in event match ball")

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
