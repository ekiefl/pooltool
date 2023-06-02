import pooltool.constants as constants
import pooltool.events.resolve as resolve
from pooltool.events.datatypes import Agent, Event, EventType
from pooltool.objects import Ball, Cue


def test_resolve_stick_ball_rolling():
    """Tests that a sweetspot hit 7/5*R leads to rolling state

    Since the stick-ball interaction is quite unrealistic, I had to modulate things so
    the amount of spin applied seemed somewhat more realistic. Enter
    `constants.english_fraction`. Due to this factor, the required top spin for a
    rolling state is actually 7/5*R/english_fraction.
    """

    # Create the cue and set state to requirement for rolling outgoing ball state
    cue = Cue.default()
    cue.set_state(b=0.4 / constants.english_fraction)

    # Create the ball
    ball = Ball.create("test", xy=(0.2, 0.2))

    event = Event(
        EventType.STICK_BALL,
        agents=(
            Agent.from_object(cue),
            Agent.from_object(ball),
        ),
        time=0,
    )

    # Resolve the event and test for rolling state
    resolve.resolve_stick_ball(event)
    ball_state = event.agents[1].get_final().state
    assert ball_state.s == constants.rolling
