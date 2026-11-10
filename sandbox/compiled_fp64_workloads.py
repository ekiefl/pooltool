"""Deterministic native systems and comparison bounds for the FP64 experiment."""

from math import sqrt

import attrs
import numpy as np

import pooltool as pt
import pooltool.constants as const
from pooltool.evolution.engine import SimulationEngine
from pooltool.objects.table.specs import PocketTableSpecs
from pooltool.physics.resolve.resolver import default_resolver

# Absolute software-equivalence bounds fixed before measuring the corpus.
TIME, POSITION, VELOCITY, SPIN = 50e-9, 0.5e-6, 0.5e-6, 0.0001


def engine():
    return SimulationEngine(resolver=default_resolver())


def sparse(*, speed=1.25, heading=14, side=0.1, vertical=0.0, table=None):
    table = pt.Table.default() if table is None else table
    return pt.System(
        table=table,
        balls={"cue": pt.Ball.create("cue", xy=(0.52 * table.w, 0.43 * table.l))},
        cue=pt.Cue(cue_ball_id="cue", V0=speed, phi=heading, a=side, b=vertical),
    )


def cluster(*, speed=3.4, rows=4):
    shot = sparse(speed=speed, heading=90, side=0)
    spacing = 2 * shot.balls["cue"].params.R + 0.001
    shot.balls["cue"].state.rvw[0, :2] = [shot.table.w / 2, shot.table.l * 0.22]
    for row in range(rows):
        for col in range(row + 1):
            ball_id = f"ball-{row}-{col}"
            shot.balls[ball_id] = pt.Ball.create(
                ball_id,
                xy=(
                    shot.table.w / 2 + (col - row / 2) * spacing,
                    0.58 * shot.table.l + row * sqrt(3) * spacing / 2,
                ),
            )
    return shot


def straight(*, scratch=False, speed=1.15):
    table = pt.Table.default()
    cue_xy = (table.w * 0.35, table.l * 0.5)
    shot = pt.System(
        table=table,
        balls={"cue": pt.Ball.create("cue", xy=cue_xy)},
        cue=pt.Cue(cue_ball_id="cue", V0=speed, phi=180),
    )
    if not scratch:
        shot.balls["target"] = pt.Ball.create(
            "target", xy=(table.w * 0.16, table.l * 0.5)
        )
    return shot


def moving(*, tie=False, near=False):
    shot = sparse(speed=0)
    first = shot.balls["cue"]
    first.state.rvw[0, :2] = [0.75 * shot.table.w, 0.31 * shot.table.l]
    first.state.rvw[1, 0] = 1.0
    first.state.rvw[2, 1] = 1.0 / first.params.R
    first.state.s = const.rolling
    if tie or near:
        second = pt.Ball.create("other", xy=(0.25 * shot.table.w, 0.68 * shot.table.l))
        second.state.rvw[1, 0] = -1.0 if tie else -0.9999998
        second.state.rvw[2, 1] = second.state.rvw[1, 0] / second.params.R
        second.state.s = const.rolling
        shot.balls[second.id] = second
    return shot


def spin():
    shot = sparse(speed=0)
    ball = shot.balls["cue"]
    ball.state.s = const.spinning
    ball.state.rvw[2, 2] = 42.0
    return shot


def altered():
    shot = sparse(table=pt.Table.from_table_specs(PocketTableSpecs(l=2.15, w=1.075)))
    shot.balls["cue"] = pt.Ball.create(
        "cue", xy=(0.5, 0.95), R=0.03, m=0.18, u_s=0.16, u_r=0.017, e_c=0.79
    )
    return shot


def grazing():
    shot = straight(speed=1.1)
    shot.balls["target"].state.rvw[0, 1] += 1.98 * shot.balls["cue"].params.R
    return shot


def separating():
    shot = moving()
    ball = shot.balls["cue"]
    velocity = np.array([0.8, 0.6])
    ball.state.rvw[1, :2] = velocity
    ball.state.rvw[2, :2] = [-velocity[1] / ball.params.R, velocity[0] / ball.params.R]
    target = pt.Ball.create(
        "target", xy=tuple(ball.xyz[:2] - 2.01 * ball.params.R * velocity)
    )
    shot.balls[target.id] = target
    return shot


def degenerate_quartic():
    shot = moving()
    ball = shot.balls["cue"]
    target = pt.Ball.create(
        "target", xy=(ball.xyz[0] - 2.01 * ball.params.R, ball.xyz[1])
    )
    shot.balls[target.id] = target
    return shot


def differing_cloth():
    shot = straight(speed=0.75)
    target = shot.balls["target"]
    target.params = attrs.evolve(target.params, u_s=0.22, u_r=0.013, e_b=0.89)
    return shot


def moving_with_clock():
    shot = moving()
    shot.balls["cue"].state.t = 0.001
    return shot


def purpose_cases():
    return {
        "direct": straight(),
        "scratch": straight(scratch=True),
        "cluster": cluster(),
        "rail": sparse(speed=1.5, heading=43, side=-0.12),
        "draw": sparse(vertical=-0.45),
        "follow": sparse(vertical=0.45),
        "rolling": moving(),
        "tie": moving(tie=True),
        "near-tie": moving(near=True),
        "spin": spin(),
        "altered": altered(),
        "grazing": grazing(),
        "separating": separating(),
        "differing-cloth": differing_cloth(),
        "moving-clock": moving_with_clock(),
        "no-energy": sparse(speed=0),
        "existing-example": pt.System.example(),
    }


def additional_cases():
    for heading in (12, 31, 57, 81, 103, 131, 167, 206, 239, 278, 315, 346):
        for speed in (0.38, 1.2):
            yield f"rail-{heading}-{speed}", sparse(speed=speed, heading=heading)
    for speed in (0.44, 0.75, 1.6):
        yield f"direct-{speed}", straight(speed=speed)
        yield f"scratch-{speed}", straight(scratch=True, speed=speed)


def seeded_cases(count=120):
    rng = np.random.default_rng(823875)
    for index in range(count):
        speed = rng.uniform(0.25, 2.0)
        if index % 4:
            shot = sparse(
                speed=speed,
                heading=rng.uniform(0, 360),
                side=rng.uniform(-0.35, 0.35),
                vertical=rng.uniform(-0.38, 0.38),
            )
        else:
            shot = straight(scratch=index % 8 == 0, speed=speed)
        yield f"seeded-{index:03}", shot


def _compare_state(expected, actual):
    assert actual.s == expected.s
    np.testing.assert_allclose(actual.t, expected.t, atol=TIME, rtol=0)
    for row, tolerance in enumerate((POSITION, VELOCITY, SPIN)):
        np.testing.assert_allclose(
            actual.rvw[row], expected.rvw[row], atol=tolerance, rtol=0
        )


def compare(expected, actual):
    """Check the native event sequence, snapshots, histories and pocket state."""
    np.testing.assert_allclose(actual.t, expected.t, atol=TIME, rtol=0)
    assert list(actual.balls) == list(expected.balls)
    assert [(e.event_type, e.ids) for e in actual.events] == [
        (e.event_type, e.ids) for e in expected.events
    ]
    for ref_event, event in zip(expected.events, actual.events):
        np.testing.assert_allclose(event.time, ref_event.time, atol=TIME, rtol=0)
        for ref_agent, agent in zip(ref_event.agents, event.agents):
            assert agent.agent_type == ref_agent.agent_type
            for field in ("initial", "final"):
                ref_snapshot = getattr(ref_agent, field)
                snapshot = getattr(agent, field)
                assert type(snapshot) is type(ref_snapshot)
                if isinstance(ref_snapshot, pt.Ball):
                    _compare_state(ref_snapshot.state, snapshot.state)
                    assert snapshot.params == ref_snapshot.params
                else:
                    assert snapshot == ref_snapshot
    for ball_id, ref_ball in expected.balls.items():
        ball = actual.balls[ball_id]
        _compare_state(ref_ball.state, ball.state)
        for ref_history, history in (
            (ref_ball.history, ball.history),
            (ref_ball.history_cts, ball.history_cts),
        ):
            assert len(history) == len(ref_history)
            for ref_state, state in zip(ref_history, history):
                _compare_state(ref_state, state)
    assert {key: p.contains for key, p in actual.table.pockets.items()} == {
        key: p.contains for key, p in expected.table.pockets.items()
    }
