import numpy as np
import pytest

from pooltool import ptmath
from pooltool.constants import sliding, stationary
from pooltool.objects import (
    Ball,
    BallParams,
    CircularCushionSegment,
    LinearCushionSegment,
    PocketTableSpecs,
)
from pooltool.physics.resolve.ball_cushion import (
    BallLCushionModel,
    ball_ccushion_models,
    ball_lcushion_models,
)
from pooltool.physics.resolve.ball_cushion.core import (
    CoreBallCCushionCollision,
    CoreBallLCushionCollision,
)
from pooltool.physics.resolve.models import BallCCushionModel


@pytest.fixture
def cushion_yaxis():
    h = PocketTableSpecs().cushion_height

    return LinearCushionSegment(
        "cushion",
        p1=np.array([0, -1, h], dtype=np.float64),
        p2=np.array([0, +1, h], dtype=np.float64),
    )


@pytest.fixture
def cushion_circular():
    h = PocketTableSpecs().cushion_height

    return CircularCushionSegment(
        "pocket_cushion",
        center=np.array([0.0, 0.0, h], dtype=np.float64),
        radius=0.01,
    )


@pytest.mark.parametrize(
    "model_name",
    [
        BallLCushionModel.UNREALISTIC,
        BallLCushionModel.HAN_2005,
        BallLCushionModel.IMPULSE_FRICTIONAL_INELASTIC,
        BallLCushionModel.MATHAVAN_2010,
        BallLCushionModel.STRONGE_COMPLIANT,
    ],
)
@pytest.mark.parametrize("theta", np.linspace(1, 89, 10))
def test_energy(
    cushion_yaxis: LinearCushionSegment, model_name: BallLCushionModel, theta: float
) -> None:
    """Test that ball-linear cushion interactions do not increase energy"""
    R = BallParams.default().R
    pos = [-R, 0, R]

    rads = np.radians(theta)
    vel = [np.cos(rads), np.sin(rads), 0]

    # Ball hitting left-side of cushion
    ball = Ball("cue")
    ball.state.rvw[0] = pos
    ball.state.rvw[1] = vel
    ball.state.s = sliding

    initial_energy = ptmath.get_ball_energy(
        ball.state.rvw,
        ball.params.R,
        ball.params.m,
    )

    # Resolve physics
    model = ball_lcushion_models[model_name]()
    ball_after, _ = model.resolve(ball=ball, cushion=cushion_yaxis, inplace=False)

    final_energy = ptmath.get_ball_energy(
        ball_after.state.rvw,
        ball_after.params.R,
        ball_after.params.m,
    )

    assert np.isclose(initial_energy, final_energy) or final_energy <= initial_energy, (
        "energy must not increase during collisions"
    )


@pytest.mark.parametrize(
    "model_name",
    [
        BallLCushionModel.UNREALISTIC,
        BallLCushionModel.HAN_2005,
        BallLCushionModel.IMPULSE_FRICTIONAL_INELASTIC,
        BallLCushionModel.MATHAVAN_2010,
        BallLCushionModel.STRONGE_COMPLIANT,
    ],
)
@pytest.mark.parametrize("theta", np.linspace(-89, 89, 20))
def test_symmetry(
    cushion_yaxis: LinearCushionSegment, model_name: BallLCushionModel, theta: float
) -> None:
    """Test that ball-linear cushion interactions are symmetric"""
    R = BallParams.default().R
    pos = [-R, 0, R]

    rads = np.radians(theta)
    vel = [np.cos(rads), np.sin(rads), 0]

    # Ball hitting left-side of cushion
    ball = Ball("cue")
    ball.state.rvw[0] = pos
    ball.state.rvw[1] = vel
    ball.state.s = sliding

    # Ball hitting left-side of cushion with opposite y-vel
    other = ball.copy()
    other.state.rvw[1, 1] = -ball.state.rvw[1, 1]

    # Positions are same
    assert np.array_equal(ball.state.rvw[0], other.state.rvw[0])

    # X-velocities are the same
    assert ball.state.rvw[1, 0] == other.state.rvw[1, 0]

    # Y-velocities are the reflected
    assert ball.state.rvw[1, 1] == -other.state.rvw[1, 1]

    # Resolve physics
    model = ball_lcushion_models[model_name]()
    ball_after, _ = model.resolve(ball=ball, cushion=cushion_yaxis, inplace=False)
    other_after, _ = model.resolve(ball=other, cushion=cushion_yaxis, inplace=False)

    # The velocities have been updated
    assert not np.array_equal(ball.state.rvw[1], ball_after.state.rvw[1])
    assert not np.array_equal(other.state.rvw[1], other_after.state.rvw[1])

    # X-velocties are negative and the same
    assert ball_after.state.rvw[1, 0] < 0
    assert other_after.state.rvw[1, 0] < 0
    assert np.isclose(ball_after.state.rvw[1, 0], other_after.state.rvw[1, 0])

    # Y-velocities are reflected
    assert np.isclose(ball_after.state.rvw[1, 1], -other_after.state.rvw[1, 1])


def _get_linear_spacer() -> float:
    class _Probe(CoreBallLCushionCollision):
        def solve(self, ball, cushion):
            return ball, cushion

    probe = _Probe()
    R = BallParams.default().R
    h = PocketTableSpecs().cushion_height
    cushion = LinearCushionSegment(
        "probe",
        p1=np.array([0, -1, h], dtype=np.float64),
        p2=np.array([0, +1, h], dtype=np.float64),
    )
    ball = Ball("probe")
    ball.state.rvw[0] = [-R, 0, R]
    ball.state.rvw[1] = [1.0, 0.0, 0.0]
    ball.state.s = sliding

    probe.make_kiss(ball, cushion)
    pos_after = ball.state.rvw[0]

    c = ptmath.point_on_line_closest_to_point(cushion.p1, cushion.p2, pos_after)
    c[2] = pos_after[2]
    return ptmath.norm3d(pos_after - c) - R


def _get_circular_spacer() -> float:
    class _Probe(CoreBallCCushionCollision):
        def solve(self, ball, cushion):
            return ball, cushion

    probe = _Probe()
    R = BallParams.default().R
    h = PocketTableSpecs().cushion_height
    cushion = CircularCushionSegment(
        "probe",
        center=np.array([0.0, 0.0, h], dtype=np.float64),
        radius=0.01,
    )
    ball = Ball("probe")
    dist = R + cushion.radius
    ball.state.rvw[0] = [dist, 0.0, R]
    ball.state.rvw[1] = [-1.0, 0.0, 0.0]
    ball.state.s = sliding

    probe.make_kiss(ball, cushion)
    c = np.array([cushion.center[0], cushion.center[1], ball.state.rvw[0, 2]])
    return ptmath.norm3d(ball.state.rvw[0] - c) - R - cushion.radius


@pytest.mark.parametrize("theta", [15, 30, 45, 60, 75])
def test_make_kiss_displacement_along_velocity_linear(
    cushion_yaxis: LinearCushionSegment, theta: float
) -> None:
    R = BallParams.default().R
    rads = np.radians(theta)
    vel = np.array([np.cos(rads), np.sin(rads), 0.0])

    ball = Ball("cue")
    ball.state.rvw[0] = [-R, 0, R]
    ball.state.rvw[1] = vel
    ball.state.s = sliding

    pos_before = ball.state.rvw[0].copy()

    model = ball_lcushion_models[BallLCushionModel.MATHAVAN_2010]()
    model.make_kiss(ball, cushion_yaxis)

    displacement = ball.state.rvw[0] - pos_before
    cross = np.cross(displacement, vel)
    assert np.allclose(cross, 0, atol=1e-10), (
        f"Displacement {displacement} is not parallel to velocity {vel}"
    )


@pytest.mark.parametrize("theta", [15, 30, 45, 60, 75])
def test_make_kiss_displacement_along_velocity_circular(
    cushion_circular: CircularCushionSegment, theta: float
) -> None:
    R = BallParams.default().R
    dist = R + cushion_circular.radius
    rads = np.radians(theta)

    ball = Ball("cue")
    ball.state.rvw[0] = [dist * np.cos(rads), dist * np.sin(rads), R]
    vel_dir = (
        np.array([cushion_circular.center[0], cushion_circular.center[1], R])
        - ball.state.rvw[0]
    )
    vel_dir[2] = 0.0
    vel_dir = vel_dir / np.linalg.norm(vel_dir)
    perp = np.array([-vel_dir[1], vel_dir[0], 0.0])
    vel = vel_dir + 0.3 * perp
    vel = vel / np.linalg.norm(vel)

    ball.state.rvw[1] = vel
    ball.state.s = sliding

    pos_before = ball.state.rvw[0].copy()

    model = ball_ccushion_models[BallCCushionModel.MATHAVAN_2010]()
    model.make_kiss(ball, cushion_circular)

    displacement = ball.state.rvw[0] - pos_before
    cross = np.cross(displacement, vel)
    assert np.allclose(cross, 0, atol=1e-10), (
        f"Displacement {displacement} is not parallel to velocity {vel}"
    )


@pytest.mark.parametrize("offset", [-1e-7, 0, 1e-7])
def test_make_kiss_separation_linear(
    cushion_yaxis: LinearCushionSegment, offset: float
) -> None:
    R = BallParams.default().R
    spacer = _get_linear_spacer()

    ball = Ball("cue")
    ball.state.rvw[0] = [-(R + offset), 0, R]
    ball.state.rvw[1] = [1.0, 0.0, 0.0]
    ball.state.s = sliding

    model = ball_lcushion_models[BallLCushionModel.MATHAVAN_2010]()
    model.make_kiss(ball, cushion_yaxis)

    c = ptmath.point_on_line_closest_to_point(
        cushion_yaxis.p1, cushion_yaxis.p2, ball.state.rvw[0]
    )
    c[2] = ball.state.rvw[0, 2]
    dist = ptmath.norm3d(ball.state.rvw[0] - c)

    assert dist == pytest.approx(R + spacer, abs=1e-12)


def test_make_kiss_separation_circular(
    cushion_circular: CircularCushionSegment,
) -> None:
    R = BallParams.default().R
    spacer = _get_circular_spacer()
    target_dist = R + cushion_circular.radius

    ball = Ball("cue")
    ball.state.rvw[0] = [target_dist, 0.0, R]
    ball.state.rvw[1] = [-1.0, 0.0, 0.0]
    ball.state.s = sliding

    model = ball_ccushion_models[BallCCushionModel.MATHAVAN_2010]()
    model.make_kiss(ball, cushion_circular)

    c = np.array(
        [cushion_circular.center[0], cushion_circular.center[1], ball.state.rvw[0, 2]]
    )
    dist = ptmath.norm3d(ball.state.rvw[0] - c)

    assert dist == pytest.approx(R + cushion_circular.radius + spacer, abs=1e-12)


def test_make_kiss_nontranslating_linear(
    cushion_yaxis: LinearCushionSegment,
) -> None:
    R = BallParams.default().R
    spacer = _get_linear_spacer()

    ball = Ball("cue")
    ball.state.rvw[0] = [-(R - 1e-7), 0, R]
    ball.state.rvw[1] = [0.0, 0.0, 0.0]
    ball.state.s = stationary

    pos_before = ball.state.rvw[0].copy()

    model = ball_lcushion_models[BallLCushionModel.MATHAVAN_2010]()
    model.make_kiss(ball, cushion_yaxis)

    c = ptmath.point_on_line_closest_to_point(
        cushion_yaxis.p1, cushion_yaxis.p2, ball.state.rvw[0]
    )
    c[2] = ball.state.rvw[0, 2]
    dist = ptmath.norm3d(ball.state.rvw[0] - c)
    assert dist == pytest.approx(R + spacer, abs=1e-12)

    displacement = ball.state.rvw[0] - pos_before
    normal = cushion_yaxis.get_normal_xy(ball.state.rvw[0])
    disp_norm = displacement / np.linalg.norm(displacement)
    assert np.allclose(np.abs(np.dot(disp_norm, normal)), 1.0, atol=1e-10)


def test_make_kiss_nontranslating_circular(
    cushion_circular: CircularCushionSegment,
) -> None:
    R = BallParams.default().R
    spacer = _get_circular_spacer()
    target_dist = R + cushion_circular.radius

    ball = Ball("cue")
    ball.state.rvw[0] = [target_dist - 1e-7, 0.0, R]
    ball.state.rvw[1] = [0.0, 0.0, 0.0]
    ball.state.s = stationary

    pos_before = ball.state.rvw[0].copy()

    model = ball_ccushion_models[BallCCushionModel.MATHAVAN_2010]()
    model.make_kiss(ball, cushion_circular)

    c = np.array(
        [cushion_circular.center[0], cushion_circular.center[1], ball.state.rvw[0, 2]]
    )
    dist = ptmath.norm3d(ball.state.rvw[0] - c)
    assert dist == pytest.approx(R + cushion_circular.radius + spacer, abs=1e-12)

    displacement = ball.state.rvw[0] - pos_before
    normal = cushion_circular.get_normal_xy(ball.state.rvw[0])
    disp_norm = displacement / np.linalg.norm(displacement)
    assert np.allclose(np.abs(np.dot(disp_norm, normal)), 1.0, atol=1e-10)


def test_make_kiss_fallback_boundary_linear(
    cushion_yaxis: LinearCushionSegment,
) -> None:
    """Test both sides of the fallback boundary for linear cushions.

    For a ball at [-R, 0, R] with unit velocity at grazing angle phi from the
    cushion surface, the velocity-based displacement is spacer / sin(phi).
    The fallback triggers when this exceeds 5 * spacer, i.e. sin(phi) < 1/5.
    """
    R = BallParams.default().R
    spacer = _get_linear_spacer()
    model = ball_lcushion_models[BallLCushionModel.MATHAVAN_2010]()

    phi = np.degrees(np.arcsin(0.2))
    dphi = 1.0

    # phi: just above boundary → velocity-based (displacement parallel to velocity)
    ball = Ball("cue")
    rads = np.radians(phi + dphi)
    vel = np.array([np.sin(rads), np.cos(rads), 0.0])
    ball.state.rvw[0] = [-R, 0, R]
    ball.state.rvw[1] = vel
    ball.state.s = sliding
    pos_before = ball.state.rvw[0].copy()
    model.make_kiss(ball, cushion_yaxis)
    displacement = ball.state.rvw[0] - pos_before
    cross = np.cross(displacement, vel)
    assert np.allclose(cross, 0, atol=1e-10)

    c = ptmath.point_on_line_closest_to_point(
        cushion_yaxis.p1, cushion_yaxis.p2, ball.state.rvw[0]
    )
    c[2] = ball.state.rvw[0, 2]
    assert ptmath.norm3d(ball.state.rvw[0] - c) == pytest.approx(R + spacer, abs=1e-12)

    # phi - dphi: just below boundary → fallback (displacement along normal)
    ball = Ball("cue")
    rads = np.radians(phi - dphi)
    vel = np.array([np.sin(rads), np.cos(rads), 0.0])
    ball.state.rvw[0] = [-R, 0, R]
    ball.state.rvw[1] = vel
    ball.state.s = sliding
    pos_before = ball.state.rvw[0].copy()
    model.make_kiss(ball, cushion_yaxis)
    displacement = ball.state.rvw[0] - pos_before
    normal = cushion_yaxis.get_normal_xy(ball.state.rvw[0])
    disp_norm = displacement / np.linalg.norm(displacement)
    assert np.allclose(np.abs(np.dot(disp_norm, normal)), 1.0, atol=1e-10)

    c = ptmath.point_on_line_closest_to_point(
        cushion_yaxis.p1, cushion_yaxis.p2, ball.state.rvw[0]
    )
    c[2] = ball.state.rvw[0, 2]
    assert ptmath.norm3d(ball.state.rvw[0] - c) == pytest.approx(R + spacer, abs=1e-12)


def test_make_kiss_fallback_boundary_circular(
    cushion_circular: CircularCushionSegment,
) -> None:
    """Test both sides of the fallback boundary for circular cushions.

    For a ball at [dist, 0, R] with unit velocity at grazing angle phi from the
    cushion tangent, the velocity-based displacement is approximately
    spacer / sin(phi). The fallback triggers when this exceeds 5 * spacer.
    """
    R = BallParams.default().R
    spacer = _get_circular_spacer()
    dist = R + cushion_circular.radius
    model = ball_ccushion_models[BallCCushionModel.MATHAVAN_2010]()

    phi = np.degrees(np.arcsin(0.2))
    dphi = 1.0

    # phi: just above boundary → velocity-based (displacement parallel to velocity)
    ball = Ball("cue")
    rads = np.radians(phi + dphi)
    vel = np.array([-np.sin(rads), np.cos(rads), 0.0])
    ball.state.rvw[0] = [dist, 0.0, R]
    ball.state.rvw[1] = vel
    ball.state.s = sliding
    pos_before = ball.state.rvw[0].copy()
    model.make_kiss(ball, cushion_circular)
    displacement = ball.state.rvw[0] - pos_before
    cross = np.cross(displacement, vel)
    assert np.allclose(cross, 0, atol=1e-10)

    c = np.array(
        [cushion_circular.center[0], cushion_circular.center[1], ball.state.rvw[0, 2]]
    )
    assert ptmath.norm3d(ball.state.rvw[0] - c) == pytest.approx(
        R + cushion_circular.radius + spacer, abs=1e-12
    )

    # phi - dphi: just below boundary → fallback (displacement along radial)
    ball = Ball("cue")
    rads = np.radians(phi - dphi)
    vel = np.array([-np.sin(rads), np.cos(rads), 0.0])
    ball.state.rvw[0] = [dist, 0.0, R]
    ball.state.rvw[1] = vel
    ball.state.s = sliding
    pos_before = ball.state.rvw[0].copy()
    model.make_kiss(ball, cushion_circular)
    displacement = ball.state.rvw[0] - pos_before
    normal = cushion_circular.get_normal_xy(ball.state.rvw[0])
    disp_norm = displacement / np.linalg.norm(displacement)
    assert np.allclose(np.abs(np.dot(disp_norm, normal)), 1.0, atol=1e-10)

    c = np.array(
        [cushion_circular.center[0], cushion_circular.center[1], ball.state.rvw[0, 2]]
    )
    assert ptmath.norm3d(ball.state.rvw[0] - c) == pytest.approx(
        R + cushion_circular.radius + spacer, abs=1e-12
    )
