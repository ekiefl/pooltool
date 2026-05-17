import attrs
import pytest

from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based.detect import EventDetector
from pooltool.physics.dimensionality import Dim
from pooltool.physics.resolve.resolver import Resolver


def _patch_all_dims(
    resolver: Resolver,
    detector: EventDetector,
    dim_value: Dim,
) -> None:
    """Set every strategy's dim to dim_value, in place."""
    for bundle in (resolver, detector):
        for field in attrs.fields(type(bundle)):
            strategy = getattr(bundle, field.name)
            if hasattr(strategy, "dim"):
                strategy.dim = dim_value


@pytest.fixture
def engine_3d() -> SimulationEngine:
    """A SimulationEngine constructed with every strategy patched to Dim.THREE."""
    resolver = SimulationEngine().resolver
    detector = SimulationEngine().detector
    _patch_all_dims(resolver, detector, Dim.THREE)
    return SimulationEngine(resolver=resolver, detector=detector, is_3d=True)


def test_default_engine_constructs():
    engine = SimulationEngine()
    assert engine.is_3d is False


def test_3d_engine_constructs(engine_3d: SimulationEngine):
    assert engine_3d.is_3d is True


def test_3d_engine_with_all_2d_strategies_raises():
    with pytest.raises(ValueError, match="incompatible with is_3d=True"):
        SimulationEngine(is_3d=True)


def test_validation_error_identifies_offending_strategy():
    with pytest.raises(ValueError, match=r"Resolver\.|EventDetector\."):
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
        SimulationEngine(
            resolver=engine_3d.resolver,
            detector=engine_3d.detector,
            is_3d=True,
        )


def test_dim_both_strategy_accepted_in_2d():
    resolver = SimulationEngine().resolver
    resolver.ball_ball.dim = Dim.BOTH
    SimulationEngine(resolver=resolver, is_3d=False)


def test_dim_both_strategy_accepted_in_3d(engine_3d: SimulationEngine):
    engine_3d.resolver.ball_ball.dim = Dim.BOTH
    SimulationEngine(
        resolver=engine_3d.resolver,
        detector=engine_3d.detector,
        is_3d=True,
    )
