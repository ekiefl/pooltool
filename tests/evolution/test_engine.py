import attrs
import pytest

from pooltool.evolution.engine import SimulationEngine
from pooltool.physics.dimensionality import Dim
from pooltool.physics.resolve.resolver import Resolver


def _patch_resolver_dims(resolver: Resolver, dim_value: Dim) -> None:
    """Set every resolver strategy's dim to dim_value, in place."""
    for field in attrs.fields(type(resolver)):
        strategy = getattr(resolver, field.name)
        if hasattr(strategy, "dim"):
            strategy.dim = dim_value


@pytest.fixture
def engine_3d() -> SimulationEngine:
    """A SimulationEngine constructed with every resolver strategy patched to Dim.THREE."""
    resolver = SimulationEngine().resolver
    _patch_resolver_dims(resolver, Dim.THREE)
    return SimulationEngine(resolver=resolver, is_3d=True)


def test_default_engine_constructs():
    engine = SimulationEngine()
    assert engine.is_3d is False


def test_3d_engine_constructs(engine_3d: SimulationEngine):
    assert engine_3d.is_3d is True
    assert engine_3d.detector.is_3d is True


def test_3d_engine_with_all_2d_strategies_raises():
    with pytest.raises(ValueError, match="incompatible with is_3d=True"):
        SimulationEngine(is_3d=True)


def test_validation_error_identifies_offending_strategy():
    with pytest.raises(ValueError, match=r"Resolver\."):
        SimulationEngine(is_3d=True)


def test_strategy_missing_dim_raises():
    @attrs.define
    class DummyBallBall:
        pass

    resolver = SimulationEngine().resolver
    resolver.ball_ball = DummyBallBall()  # type: ignore

    with pytest.raises(AttributeError, match="missing required 'dim'"):
        SimulationEngine(resolver=resolver)


def test_3d_engine_rejects_one_dim_two_strategy(engine_3d: SimulationEngine):
    """Reverting one strategy to Dim.TWO causes validation to raise, naming it."""
    engine_3d.resolver.ball_ball.dim = Dim.TWO

    with pytest.raises(ValueError, match=r"ball_ball.*incompatible with is_3d=True"):
        SimulationEngine(resolver=engine_3d.resolver, is_3d=True)


def test_dim_both_strategy_accepted_in_2d():
    resolver = SimulationEngine().resolver
    resolver.ball_ball.dim = Dim.BOTH
    SimulationEngine(resolver=resolver, is_3d=False)


def test_dim_both_strategy_accepted_in_3d(engine_3d: SimulationEngine):
    engine_3d.resolver.ball_ball.dim = Dim.BOTH
    SimulationEngine(resolver=engine_3d.resolver, is_3d=True)


def test_ball_table_exempt_from_dim_validation():
    """Ball-table resolver strategies don't carry a `dim` attribute. The
    validator skips this field in either mode via SKIP_DIMENSION."""
    resolver = SimulationEngine().resolver

    assert not hasattr(resolver.ball_table, "dim")

    SimulationEngine(resolver=resolver, is_3d=False)


def test_detector_is_not_constructor_passable():
    """``detector`` is init=False on SimulationEngine."""
    with pytest.raises(TypeError):
        SimulationEngine(detector="anything")  # type: ignore[call-arg]
