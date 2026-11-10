"""Differential checks against Pooltool's unchanged reference backend."""

import os

import numpy as np
import pytest

import pooltool as pt
import pooltool.constants as const
from pooltool.error import SimulateError
from pooltool.events import EventType
from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based.compiled_fp64 import adapter
from pooltool.physics.resolve.resolver import default_resolver_3d
from sandbox.compiled_fp64_workloads import (
    additional_cases,
    compare,
    degenerate_quartic,
    engine,
    moving,
    purpose_cases,
    seeded_cases,
    sparse,
    straight,
)

_PURPOSE_CASES = purpose_cases()


@pytest.mark.parametrize(
    ("name", "shot"), _PURPOSE_CASES.items(), ids=list(_PURPOSE_CASES)
)
def test_native_histories(name, shot):
    reference = pt.simulate(shot, engine=engine(), continuous=True, dt=0.02)
    compiled = pt.simulate(
        shot, engine=engine(), backend="compiled_fp64", continuous=True, dt=0.02
    )
    compare(reference, compiled)
    assert not shot.simulated, name
    if name == "tie":
        rails = [
            event
            for event in compiled.events
            if event.event_type == EventType.BALL_LINEAR_CUSHION
        ]
        assert rails[0].time == rails[1].time
        assert rails[0].ids != rails[1].ids
    if name == "cluster":
        assert any(
            event.event_type == EventType.BALL_CIRCULAR_CUSHION
            for event in compiled.events
        )
    if name == "separating":
        assert all(event.event_type != EventType.BALL_BALL for event in compiled.events)


@pytest.mark.parametrize(
    "limits", [{"t_final": 0.06}, {"max_events": 1}, {"t_final": 0.5, "max_events": 2}]
)
def test_requested_limits(limits):
    shot = sparse(speed=2.0, heading=12)
    compare(
        pt.simulate(shot, engine=engine(), **limits),
        pt.simulate(shot, engine=engine(), backend="compiled_fp64", **limits),
    )


def test_simultaneous_requested_limits():
    shot = sparse(speed=2.0, heading=12)
    cap_time = pt.simulate(shot, engine=engine()).events[3].time
    reference = pt.simulate(shot, engine=engine(), t_final=cap_time, max_events=1)
    compiled = pt.simulate(
        shot, engine=engine(), t_final=cap_time, max_events=1, backend="compiled_fp64"
    )
    compare(reference, compiled)
    assert len(compiled.events) == 6
    assert all(event.event_type == EventType.NONE for event in compiled.events[-2:])


def test_already_sliding_and_pocketed():
    shot = moving()
    cue = shot.balls["cue"]
    cue.state.s = const.sliding
    cue.state.rvw[2] = [0.0, 3.0, -14.0]
    pocket = next(iter(shot.table.pockets.values()))
    ball = pt.Ball.create("gone", xy=(pocket.center[0], pocket.center[1]))
    ball.state.rvw[0, 2] = -pocket.depth
    ball.state.s = const.pocketed
    pocket.add(ball.id)
    shot.balls[ball.id] = ball
    compare(
        pt.simulate(shot, engine=engine(), continuous=True),
        pt.simulate(shot, engine=engine(), backend="compiled_fp64", continuous=True),
    )


def test_copy_inplace_reload_and_request_isolation(tmp_path):
    shot = straight()
    stock = pt.simulate(shot, engine=engine(), continuous=True)
    first = pt.simulate(shot, engine=engine(), backend="compiled_fp64", continuous=True)
    alternate = sparse(speed=0.65, heading=137, side=-0.24)
    assert (
        pt.simulate(alternate, engine=engine(), backend="compiled_fp64", inplace=True)
        is alternate
    )
    assert alternate.simulated and not alternate.continuized

    path = tmp_path / "compiled.msgpack"
    first.save(path)
    compare(stock, pt.System.load(path))
    first.balls["cue"].state.rvw[0, 0] += 1
    first.table.pockets[next(iter(first.table.pockets))].add("mutation")

    second = pt.simulate(
        shot, engine=engine(), backend="compiled_fp64", continuous=True
    )
    compare(stock, second)
    assert not shot.simulated
    assert not np.shares_memory(
        shot.balls["cue"].state.rvw, second.balls["cue"].state.rvw
    )


@pytest.mark.parametrize("invalid", ("airborne", "3d", "include", "clock", "backend"))
def test_unsupported_input_preserves_inplace_state(invalid):
    shot = straight()
    kwargs = {"engine": engine(), "backend": "compiled_fp64"}
    if invalid == "airborne":
        shot.balls["cue"].state.s = const.airborne
        shot.balls["cue"].state.rvw[0, 2] += 0.02
    elif invalid == "3d":
        kwargs["engine"] = SimulationEngine(is_3d=True, resolver=default_resolver_3d())
    elif invalid == "include":
        kwargs["include"] = set()
    elif invalid == "clock":
        shot.balls["cue"].state.t = -0.5
    else:
        kwargs["backend"] = "unknown"
    original = shot.copy()
    with pytest.raises(ValueError):
        pt.simulate(shot, inplace=True, **kwargs)
    assert shot == original


def test_internal_capacity_failure_does_not_commit(monkeypatch):
    shot = straight()
    original = shot.copy()
    monkeypatch.setattr(adapter, "_MAX_HISTORY_EVENTS", 1)
    with pytest.raises(SimulateError, match="exceeded 1 retained events"):
        pt.simulate(shot, engine=engine(), backend="compiled_fp64", inplace=True)
    assert shot == original


def test_degenerate_stock_root_is_an_explicit_failure():
    shot = degenerate_quartic()
    original = shot.copy()
    with pytest.raises(ValueError, match="Leading coefficient a is zero"):
        pt.simulate(shot, engine=engine())
    with pytest.raises(SimulateError, match="Leading coefficient a is zero"):
        pt.simulate(shot, engine=engine(), backend="compiled_fp64", inplace=True)
    assert shot == original


@pytest.mark.skipif(
    os.getenv("POOLTOOL_EXTENDED_FP64") != "1",
    reason="set POOLTOOL_EXTENDED_FP64=1 for the longer compiled differential",
)
def test_extended_differential():
    failures = []
    for name, shot in [*additional_cases(), *seeded_cases()]:
        try:
            compare(
                pt.simulate(shot, engine=engine(), continuous=True, dt=0.025),
                pt.simulate(
                    shot,
                    engine=engine(),
                    backend="compiled_fp64",
                    continuous=True,
                    dt=0.025,
                ),
            )
        except (AssertionError, ArithmeticError, SimulateError, ValueError) as error:
            failures.append(f"{name}: {type(error).__name__}: {error}")
    assert not failures, "\n".join(failures)
