import numpy as np

from pooltool.evolution import continuize, simulate
from pooltool.system.datatypes import System
from pooltool.system.render import SystemRender


def _snapshot(system: System) -> dict[str, tuple]:
    return {
        ball_id: (ball.state.rvw.copy(), len(ball.history), ball.history_cts.empty)
        for ball_id, ball in system.balls.items()
    }


def test_resample_leaves_the_system_untouched():
    system = simulate(System.example())
    before = _snapshot(system)

    render = SystemRender.from_system(system)
    render.resample(0.02)
    render.resample(0.01)

    assert not system.continuized
    for ball_id, (rvw, history_length, cts_empty) in before.items():
        ball = system.balls[ball_id]
        assert np.array_equal(ball.state.rvw, rvw)
        assert len(ball.history) == history_length
        assert ball.history_cts.empty == cts_empty


def test_resample_matches_continuize():
    system = simulate(System.example())
    reference = continuize(system, dt=0.01)

    render = SystemRender.from_system(system)
    render.resample(0.01)

    for ball_id, ball_render in render.balls.items():
        expected = reference.balls[ball_id].history_cts
        assert len(ball_render.history) == len(expected)
        assert len(ball_render.quats) == len(expected)
        rvws, _, ts = ball_render.history.vectorize()
        expected_rvws, _, expected_ts = expected.vectorize()
        assert np.array_equal(rvws, expected_rvws)
        assert np.array_equal(ts, expected_ts)


def test_unsimulated_system_gives_empty_histories():
    render = SystemRender.from_system(System.example())
    render.resample(0.01)

    for ball_render in render.balls.values():
        assert ball_render.history.empty
        assert ball_render.quats == []
