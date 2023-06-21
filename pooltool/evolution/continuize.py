import pooltool.physics as physics
from pooltool.events import filter_ball
from pooltool.objects.ball.datatypes import BallHistory, BallState
from pooltool.system.datatypes import System


def continuize(system: System, dt: float = 0.01) -> None:
    """Create BallHistory for each ball with many timepoints

    All balls share the same timepoints, and the timepoints are uniformly spaced, except
    for the last timepoint, which occurs within <dt of the second last timepoint.

    The old continuize did not have uniform and equally spaced time points. That
    implementation can be found with

        git checkout 7b2f7440f7d9ad18cba65c9e4862ee6bdc620631

    (Look for pooltool.system.datatypes.continuize_heterogeneous)

    FIXME This is a very inefficient function, and could be
    radically sped up if physics.evolve_ball_motion and/or its functions had
    vectorized operations for arrays of time values.
    """

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
                        state = agent.get_final().state
                        break
                else:
                    raise ValueError("No agents in event match ball")

                rvw, s = state.rvw, state.s

                # Since this event occurs between two timestamps, we won't be
                # evolving a full dt. Instead, we evolve this much:
                evolve_time = elapsed + dt - events[count].time

            # Whether it was the hard path or the easy path, the ball state is
            # properly defined and we know how much we need to simulate.
            rvw, s = physics.evolve_ball_motion(
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
