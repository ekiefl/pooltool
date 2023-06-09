import pytest

from pooltool.events import ball_ball_collision
from pooltool.evolution.event_based.simulate import get_next_event
from pooltool.evolution.event_based.test_data import TEST_DIR, prep_shot
from pooltool.math.roots import QuarticSolver


@pytest.mark.parametrize("solver", [QuarticSolver.NUMERIC, QuarticSolver.ANALYTIC])
def test_case1(solver: QuarticSolver):
    """
    In this shot, the next event should be:

        <Event object at 0x7fe42a948b80>
         ├── type   : ball_ball
         ├── time   : 0.048943195
         └── agents : ['1', 'cue']

    Added this event because it was the cause of a failed collision when using the
    analytic quartic root solver. The collision was retained by lowering the imaginary
    tolerance from 1e-12 to 1e-9.
    """
    case1 = prep_shot(TEST_DIR / "case1.msgpack", 0)

    next_event = get_next_event(case1, solver)

    expected = ball_ball_collision(
        case1.balls["1"], case1.balls["cue"], 0.048943195217641386
    )
    assert next_event.agents == expected.agents
    assert next_event.time == pytest.approx(expected.time, rel=1e-3)
