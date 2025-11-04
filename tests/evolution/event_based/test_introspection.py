import tempfile
from pathlib import Path

import pooltool as pt
from pooltool.evolution.event_based.introspection import (
    SimulationSnapshotSequence,
    simulate_with_snapshots,
)
from pooltool.evolution.event_based.simulate import simulate


def test_simulate_with_snapshots_equivalence_with_simulate():
    """Tests that `simulates_with_snapshots` returns same thing as `simulate`."""
    system = pt.System.example()
    result, _ = simulate_with_snapshots(system)
    assert result == simulate(system)


def test_snapshot_sequence_roundtrip():
    system = pt.System.example()

    with tempfile.TemporaryDirectory() as tmpdir:
        _, seq = simulate_with_snapshots(system)
        output = Path(tmpdir) / "seq.json"
        seq.save(output)
        assert seq == SimulationSnapshotSequence.load(output)


def test_selected_event_in_all_possible_events():
    system = pt.System.example()
    _, seq = simulate_with_snapshots(system)

    for step in range(len(seq) - 1):
        snapshot = seq[step]
        all_events = snapshot.get_prospective_events()
        first_event = all_events[0]

        assert snapshot.event.event_type == first_event.event_type
        assert snapshot.event.time == first_event.time


def test_pre_evolve_equals_snapshot_system():
    """pre_evolve_system should return the same system as stored in snapshot."""
    system = pt.System.example()
    _, seq = simulate_with_snapshots(system)

    for step in range(len(seq)):
        snapshot = seq[step]
        pre_evolve = snapshot.pre_evolve_system()

        assert pre_evolve == snapshot.system
        assert pre_evolve is not snapshot.system


def test_post_evolve_advances_time():
    """post_evolve_system should advance time to the selected event."""
    system = pt.System.example()
    _, seq = simulate_with_snapshots(system)

    for step in range(len(seq)):
        snapshot = seq[step]
        event = snapshot.event
        post_evolve = snapshot.post_evolve_system(event)

        assert post_evolve.t == event.time


def test_post_resolve_of_n_equals_pre_evolve_of_n_plus_1():
    """post_resolve_system of step n should equal pre_evolve_system of step n+1."""
    system = pt.System.example()
    _, seq = simulate_with_snapshots(system)

    for step in range(len(seq) - 1):
        current_snapshot = seq[step]
        next_snapshot = seq[step + 1]

        post_resolve = current_snapshot.post_resolve_system(
            current_snapshot.event
        )
        pre_evolve_next = next_snapshot.pre_evolve_system()

        assert post_resolve == pre_evolve_next


def test_system_state_progression():
    """Test the full progression: pre_evolve -> post_evolve -> post_resolve."""
    system = pt.System.example()
    _, seq = simulate_with_snapshots(system)

    for step in range(len(seq)):
        snapshot = seq[step]
        event = snapshot.event

        pre_evolve = snapshot.pre_evolve_system()
        post_evolve = snapshot.post_evolve_system(event)
        post_resolve = snapshot.post_resolve_system(event)

        assert pre_evolve.t <= post_evolve.t
        assert post_evolve.t == event.time
        assert post_resolve.t == event.time

        assert pre_evolve is not post_evolve
        assert post_evolve is not post_resolve
