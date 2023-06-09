import pytest

import pooltool.constants as const
from pooltool.events import ball_ball_collision, ball_pocket_collision
from pooltool.evolution.event_based.simulate import get_next_event
from pooltool.evolution.event_based.test_data import TEST_DIR, prep_shot
from pooltool.math.roots import QuarticSolver
from pooltool.system import System


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
    tolerance from 1e-12 to 1e-9. However, I am no longer hopeful of developing a robust
    analytic quartic solver, which despite having a closed-form solution, is far less
    numerically stable than numerical methods.
    """
    shot = prep_shot(TEST_DIR / "case1.msgpack", 0)

    next_event = get_next_event(shot, solver)

    expected = ball_ball_collision(
        shot.balls["1"], shot.balls["cue"], 0.048943195217641386
    )
    assert next_event.agents == expected.agents
    assert next_event.time == pytest.approx(expected.time, rel=1e-3)


@pytest.mark.parametrize("solver", [QuarticSolver.NUMERIC, QuarticSolver.ANALYTIC])
def test_case2(solver: QuarticSolver):
    """
    In this shot, the next event should be:

        <Event object at 0x7fc1a3164a80>
         ├── type   : ball_pocket
         ├── time   : 0.089330336
         └── agents : ['8', 'lc']

    However, I am no longer hopeful of developing a robust analytic quartic solver,
    which despite having a closed-form solution, is far less numerically stable than
    numerical methods.
    """
    shot = System.load(TEST_DIR / "case2.msgpack")

    next_event = get_next_event(shot, solver)
    expected = ball_pocket_collision(
        shot.balls["8"], shot.table.pockets["lc"], 0.08933033587481054
    )

    if solver == QuarticSolver.NUMERIC:
        assert next_event == expected
    elif solver == QuarticSolver.ANALYTIC:
        assert next_event != expected
