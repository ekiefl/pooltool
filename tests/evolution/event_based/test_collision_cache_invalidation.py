from math import sqrt
from random import Random

import pytest

import pooltool as pt
import pooltool.constants as const
from pooltool.events import (
    Event,
    EventType,
    ball_ball_collision,
    ball_pocket_collision,
    null_event,
    rolling_stationary_transition,
    stick_ball_collision,
)
from pooltool.events.utils import event_type_to_ball_indices
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.serialize import conversion


def _original_invalidate(cache: CollisionCache, event: Event) -> None:
    """The per-entry lookup and generator used before this optimization."""
    invalid_ball_ids = cache._get_invalid_ball_ids(event)
    for event_type, event_times in cache.times.items():
        keys_to_delete = []
        for key in event_times:
            ball_indices = event_type_to_ball_indices.get(event_type, ())
            if any(key[idx] in invalid_ball_ids for idx in ball_indices):
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del event_times[key]


def _ordered(cache: CollisionCache):
    return [(kind, list(entries.items())) for kind, entries in cache.times.items()]


def test_public_cache_mutation_copy_and_serialization(tmp_path):
    cache = CollisionCache.create()
    entries = {("a", "b"): 1.0, ("b", "a"): 2.0, ("b", "b"): 3.0}
    cache.times[EventType.BALL_LINEAR_CUSHION] = entries
    cache.times[EventType.BALL_BALL] = {("a", "b"): 4.0}
    cache.times[EventType.NONE] = {("a",): 5.0}
    # A caller can modify a category after the cache has been created.
    entries[("a", "a")] = 6.0
    original = _ordered(cache)
    copied = cache.copy()
    path = tmp_path / "cache.json"
    conversion.unstructure_to(cache, path)
    reopened = conversion.structure_from(path, CollisionCache)

    event = rolling_stationary_transition(pt.Ball.create("a"), 0.5)
    expected = [
        (EventType.BALL_LINEAR_CUSHION, [(("b", "a"), 2.0), (("b", "b"), 3.0)]),
        (EventType.BALL_BALL, []),
        (EventType.NONE, [(("a",), 5.0)]),
    ]
    for restored in (copied, reopened):
        assert _ordered(restored) == original
        restored.invalidate(event)
        restored.invalidate(event)
        assert _ordered(restored) == expected
    assert _ordered(cache) == original

    cache.invalidate(event)
    assert cache.times[EventType.BALL_LINEAR_CUSHION] is entries
    assert _ordered(cache) == expected
    empty = CollisionCache.create()
    empty.invalidate(event)
    assert empty.size == 0


def test_seeded_cache_matches_original_in_full_order(monkeypatch):
    rng = Random(473)
    a, b = pt.Ball.create("a"), pt.Ball.create("b")
    table = pt.Table.default()
    events = (
        rolling_stationary_transition(a, 0.5),
        ball_ball_collision(a, b, 0.5),
        stick_ball_collision(pt.Cue(id="b", cue_ball_id="a"), a, 0.5),
        ball_pocket_collision(a, next(iter(table.pockets.values())), 0.5),
    )
    # Include both a category with no mapping and one with a present, empty
    # mapping. A synthetic three-slot mapping exercises the generic path.
    monkeypatch.setitem(event_type_to_ball_indices, EventType.BALL_TABLE, set())
    monkeypatch.setitem(event_type_to_ball_indices, EventType.BALL_OFF_TABLE, {0, 2, 3})
    kinds = list(EventType)
    identifiers = ("a", "b", "c", "d", "e")
    for _ in range(48):
        rng.shuffle(kinds)
        cache = CollisionCache(
            {
                kind: {
                    tuple(rng.choices(identifiers, k=4)): rng.random()
                    for _ in range(rng.randrange(30))
                }
                for kind in kinds
            }
        )
        expected = cache.copy()
        for event in rng.sample(events, len(events)):
            _original_invalidate(expected, event)
            cache.invalidate(event)
            assert _ordered(cache) == _ordered(expected)


@pytest.mark.parametrize("kind", [EventType.BALL_LINEAR_CUSHION, EventType.BALL_BALL])
def test_malformed_key_still_raises_before_deleting_from_its_category(kind):
    a = pt.Ball.create("a")
    event = rolling_stationary_transition(a, 0.5)
    cache = CollisionCache({kind: {("a", "b"): 1.0, (): 2.0}})
    expected = cache.copy()
    for candidate, invalidate in (
        (expected, _original_invalidate),
        (cache, CollisionCache.invalidate),
    ):
        with pytest.raises(IndexError):
            invalidate(candidate, event)
    assert _ordered(cache) == _ordered(expected)
    with pytest.raises(KeyError):
        cache.invalidate(null_event(time=0.5))


def _cushion_tie():
    table = pt.Table.default()
    balls = [
        pt.Ball.create(ball_id, xy=(x * table.w, 0.2 * table.l))
        for ball_id, x in (("cue", 0.25), ("target", 0.65))
    ]
    for ball in balls:
        ball.state.s = const.rolling
        ball.state.rvw[1, 1] = -1.0
        ball.state.rvw[2, 0] = 1.0 / ball.params.R
    cue = pt.Cue.default()
    cue.set_state(V0=0)
    return pt.System(cue=cue, table=table, balls=balls)


def _cluster():
    table = pt.Table.default()
    cue_ball = pt.Ball.create("cue", xy=(table.w / 2, table.l / 4))
    spacing = 2.004 * cue_ball.params.R
    balls = [cue_ball]
    for row in range(3):
        for column in range(row + 1):
            x = table.w / 2 + (column - row / 2) * spacing
            y = table.l * 0.64 + row * spacing * sqrt(3) / 2
            balls.append(pt.Ball.create(f"{row}-{column}", xy=(x, y)))
    cue = pt.Cue.default()
    cue.set_state(V0=3.2, phi=90.05)
    return pt.System(cue=cue, table=table, balls=balls)


@pytest.mark.parametrize(
    "make_shot",
    [pt.System.example, _cushion_tie, _cluster],
    ids=["pot", "tie", "cluster"],
)
def test_complete_shot_matches_original_exactly(make_shot, monkeypatch, tmp_path):
    shot = make_shot()
    changed = pt.simulate(shot, continuous=True, dt=0.01)
    with monkeypatch.context() as patch:
        patch.setattr(CollisionCache, "invalidate", _original_invalidate)
        reference = pt.simulate(shot, continuous=True, dt=0.01)

    # Includes ordered events, agent snapshots, pockets, and every sparse and
    # continuous ball state. The bookkeeping change requires exact equality.
    changed_path, reference_path = (
        tmp_path / "changed.msgpack",
        tmp_path / "base.msgpack",
    )
    changed.save(changed_path)
    reference.save(reference_path)
    assert changed_path.read_bytes() == reference_path.read_bytes()
    assert changed.continuized

    if make_shot is _cushion_tie:
        rail = [
            e for e in changed.events if e.event_type == EventType.BALL_LINEAR_CUSHION
        ]
        assert rail[0].ids[0] != rail[1].ids[0]
        assert rail[0].time == rail[1].time
    elif make_shot is _cluster:
        assert sum(e.event_type == EventType.BALL_BALL for e in changed.events) >= 6
    else:
        assert any(e.event_type == EventType.BALL_POCKET for e in changed.events)
