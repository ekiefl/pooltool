"""Airborne ball versus circular cushion (torus) contact detection.

The detector is checked against two independent references. The first is brute
force: dense sampling of the distance function followed by Brent refinement, with
shallow local minima refined separately so that grazes are not missed. The second
is exact: the contact condition squared is a degree-eight polynomial in time, whose
roots ``np.roots`` finds all at once. Cases span three jaw geometries (two spindle
tori from pool tables, one ring torus from snooker) and several trajectory
families, including grazes down to sub-micron depth and drops along the axis.
"""

from typing import Any, cast

import numpy as np
import pytest
from scipy.optimize import brentq, minimize_scalar

from pooltool.evolution.event_based.detect.torus import (
    arc_intervals,
    parabola_torus_contact_time,
    torus_contact_windows,
    torus_residual,
)

G = 9.81
POOL_R = 0.028575
SNOOKER_R = 0.02625
NOSE = 0.001
TABLE_Z = POOL_R - 0.037
FULL_RING = 2 * np.pi

JAWS = {
    "pool_corner": (0.02095, POOL_R + NOSE),
    "pool_side": (0.00795, POOL_R + NOSE),
    "snooker_corner": (0.1016, SNOOKER_R + NOSE),
}


def _residual(t, p0, v, r, D) -> float:
    return torus_residual(t, p0[0], p0[1], p0[2], v[0], v[1], v[2], G, r, D)


def _residual_array(ts, p0, v, r, D):
    X = p0[0] + v[0] * ts
    Y = p0[1] + v[1] * ts
    Z = p0[2] + v[2] * ts - 0.5 * G * ts * ts
    return (np.hypot(X, Y) - r) ** 2 + Z**2 - D**2


def _root(f, a: float, b: float) -> float:
    return cast(float, brentq(f, a, b, xtol=1e-15, maxiter=200))


def _reference_contact(p0, v, r, D, dt=1e-5) -> float:
    horizon = (v[2] + np.sqrt(v[2] ** 2 + 2 * G * (p0[2] + D + 0.05))) / G
    ts = np.linspace(0.0, horizon, int(np.ceil(horizon / dt)) + 1)
    gs = _residual_array(ts, p0, v, r, D)

    def f(t):
        return _residual(t, p0, v, r, D)

    negative = gs <= 0
    crossings = np.flatnonzero(~negative[:-1] & negative[1:])
    first = np.inf
    if crossings.size:
        i = crossings[0]
        first = _root(f, ts[i], ts[i + 1])

    interior = np.arange(1, len(ts) - 1)
    is_min = (gs[interior] < gs[interior - 1]) & (gs[interior] <= gs[interior + 1])
    shallow = interior[is_min & (gs[interior] > 0) & (gs[interior] < 1e-4)]
    for i in shallow:
        if ts[i] > first:
            break
        res: Any = minimize_scalar(
            f, bounds=(ts[i - 1], ts[i + 1]), method="bounded", options={"xatol": 1e-15}
        )
        if res.fun < 0:
            first = min(first, _root(f, ts[i - 1], float(res.x)))
    return first


def _residual_slope(t, p0, v, r, D) -> float:
    X = p0[0] + v[0] * t
    Y = p0[1] + v[1] * t
    Z = p0[2] + v[2] * t - 0.5 * G * t * t
    rho = np.hypot(X, Y)
    return 2 * (rho - r) * (X * v[0] + Y * v[1]) / rho + 2 * Z * (v[2] - G * t)


def _octic_contact(p0, v, r, D) -> float:
    """First approaching root of the squared contact condition, a degree-eight polynomial.

    Squaring ``rho**2 + z**2 + r**2 - D**2 == 2 r rho`` removes the square root in
    ``rho`` at the cost of spurious roots satisfying the equation with ``-2 r rho``,
    which lie inside the spindle of a pool jaw. Each real root is polished by Newton
    on the true residual and kept only if the residual vanishes there and the ball is
    not moving away.
    """
    rho2 = np.polynomial.Polynomial(
        [
            p0[0] ** 2 + p0[1] ** 2,
            2 * (p0[0] * v[0] + p0[1] * v[1]),
            v[0] ** 2 + v[1] ** 2,
        ]
    )
    z = np.polynomial.Polynomial([p0[2], v[2], -0.5 * G])
    bracket = rho2 + z * z + (r * r - D * D)
    octic = bracket * bracket - 4 * r * r * rho2

    best = np.inf
    for root in octic.roots():
        if abs(root.imag) > 1e-6:
            continue
        t = root.real
        for _ in range(4):
            slope = _residual_slope(t, p0, v, r, D)
            if slope == 0.0:
                break
            t -= _residual(t, p0, v, r, D) / slope
        if t < 0.0 or t >= best:
            continue
        if abs(_residual(t, p0, v, r, D)) > 1e-10:
            continue
        if _residual_slope(t, p0, v, r, D) > 1e-9:
            continue
        best = t
    return best


def _surface_point_and_normal(rng, r, D, gap):
    azimuth = rng.uniform(0, 2 * np.pi)
    polar = rng.uniform(0, 2 * np.pi)
    nose_point = np.array([r * np.cos(azimuth), r * np.sin(azimuth), 0.0])
    normal = np.array(
        [
            np.cos(polar) * np.cos(azimuth),
            np.cos(polar) * np.sin(azimuth),
            np.sin(polar),
        ]
    )
    point = nose_point + (D + gap) * normal
    return point, normal


def _aimed(rng, r, D):
    d0 = rng.uniform(0.05, 0.5)
    azimuth = rng.uniform(0, 2 * np.pi)
    start = d0 * np.array([np.cos(azimuth), np.sin(azimuth)])
    miss = rng.uniform(-(r + D + 0.03), r + D + 0.03)
    toward = -start / d0
    perp = np.array([-toward[1], toward[0]])
    direction = miss * perp - start
    direction /= np.linalg.norm(direction)
    v_xy = rng.uniform(0.3, 5.0) * direction
    p0 = np.array([start[0], start[1], rng.uniform(TABLE_Z, 0.12)])
    v = np.array([v_xy[0], v_xy[1], rng.uniform(-2.0, 2.0)])
    return p0, v


def _drop(rng, r, D):
    rho0 = rng.uniform(0, r + D)
    azimuth = rng.uniform(0, 2 * np.pi)
    speed = rng.uniform(0, 1.0)
    heading = rng.uniform(0, 2 * np.pi)
    p0 = np.array(
        [rho0 * np.cos(azimuth), rho0 * np.sin(azimuth), rng.uniform(D + 0.005, 0.2)]
    )
    v = np.array(
        [speed * np.cos(heading), speed * np.sin(heading), rng.uniform(-1.0, 0.5)]
    )
    return p0, v


def _departing(rng, r, D):
    point, _ = _surface_point_and_normal(rng, r, D, 1e-4)
    rho = np.hypot(point[0], point[1])
    if rho < 1e-6:
        return None
    nose_point = np.array([r * point[0] / rho, r * point[1] / rho, 0.0])
    normal = point - nose_point
    normal /= np.linalg.norm(normal)
    point = nose_point + (D + 1e-4) * normal
    v = rng.normal(size=3)
    v /= np.linalg.norm(v)
    if np.dot(v, normal) < 0:
        v = v - 2 * np.dot(v, normal) * normal
    return point, rng.uniform(0.2, 4.0) * v


def _graze(rng, r, D):
    gap = rng.choice([-1, 1]) * 10 ** rng.uniform(-7, -3)
    point, normal = _surface_point_and_normal(rng, r, D, gap)
    if point[2] < TABLE_Z + 1e-3:
        return None
    v = rng.normal(size=3)
    v -= np.dot(v, normal) * normal
    v /= np.linalg.norm(v)
    v *= rng.uniform(0.2, 4.0)
    tau = rng.uniform(0.005, 0.15)
    p0 = np.array(
        [
            point[0] - v[0] * tau,
            point[1] - v[1] * tau,
            point[2] - v[2] * tau - 0.5 * G * tau**2,
        ]
    )
    return p0, np.array([v[0], v[1], v[2] + G * tau])


def _axis(rng, _r, D):
    rho0 = 10 ** rng.uniform(-7, -3)
    azimuth = rng.uniform(0, 2 * np.pi)
    speed = 10 ** rng.uniform(-4, -1)
    heading = rng.uniform(0, 2 * np.pi)
    p0 = np.array(
        [rho0 * np.cos(azimuth), rho0 * np.sin(azimuth), rng.uniform(D + 0.005, 0.2)]
    )
    v = np.array(
        [speed * np.cos(heading), speed * np.sin(heading), rng.uniform(-1.0, 0.5)]
    )
    return p0, v


FAMILIES = (_aimed, _drop, _departing, _graze, _axis)


def _cases(rng, family, r, D, count):
    out = []
    while len(out) < count:
        case = family(rng, r, D)
        if case is None:
            continue
        p0, v = case
        if p0[2] >= TABLE_Z and _residual(0.0, p0, v, r, D) > 1e-10:
            out.append((p0, v))
    return out


@pytest.mark.parametrize("jaw", list(JAWS))
def test_matches_brute_force_reference(jaw):
    r, D = JAWS[jaw]
    rng = np.random.default_rng(0)
    hits = 0
    for family in FAMILIES:
        for p0, v in _cases(rng, family, r, D, 120):
            expected = _reference_contact(p0, v, r, D)
            actual = parabola_torus_contact_time(p0, v, G, r, D)
            assert np.isfinite(actual) == np.isfinite(expected), (
                family.__name__,
                p0,
                v,
            )
            if np.isfinite(expected):
                assert actual == pytest.approx(expected, abs=1e-9), (
                    family.__name__,
                    p0,
                    v,
                )
                hits += 1
    assert hits > 150


@pytest.mark.parametrize("jaw", list(JAWS))
def test_matches_octic_reference(jaw):
    r, D = JAWS[jaw]
    rng = np.random.default_rng(3)
    hits = 0
    for family in FAMILIES:
        for p0, v in _cases(rng, family, r, D, 120):
            expected = _octic_contact(p0, v, r, D)
            actual = parabola_torus_contact_time(p0, v, G, r, D)
            assert np.isfinite(actual) == np.isfinite(expected), (
                family.__name__,
                p0,
                v,
            )
            if np.isfinite(expected):
                assert actual == pytest.approx(expected, abs=1e-9), (
                    family.__name__,
                    p0,
                    v,
                )
                hits += 1
    assert hits > 150


def test_detected_contact_is_on_the_surface_and_approaching():
    r, D = JAWS["pool_corner"]
    rng = np.random.default_rng(1)
    for p0, v in _cases(rng, _aimed, r, D, 200):
        t = parabola_torus_contact_time(p0, v, G, r, D)
        if not np.isfinite(t):
            continue
        assert _residual(t, p0, v, r, D) == pytest.approx(0.0, abs=1e-12)
        assert _residual(t - 1e-7, p0, v, r, D) > 0


def test_penetrating_graze_is_detected():
    """A trajectory tangent to the outer face but one micron inside it still registers."""
    r, D = JAWS["pool_corner"]
    rng = np.random.default_rng(2)
    found = 0
    for _ in range(50):
        azimuth = rng.uniform(0, 2 * np.pi)
        polar = rng.uniform(-0.28, 0.5 * np.pi)
        nose_point = np.array([r * np.cos(azimuth), r * np.sin(azimuth), 0.0])
        normal = np.array(
            [
                np.cos(polar) * np.cos(azimuth),
                np.cos(polar) * np.sin(azimuth),
                np.sin(polar),
            ]
        )
        point = nose_point + (D - 1e-6) * normal
        v = rng.normal(size=3)
        v -= np.dot(v, normal) * normal
        v *= 2.0 / np.linalg.norm(v)
        tau = 0.03
        p0 = point - v * tau - np.array([0.0, 0.0, 0.5 * G * tau**2])
        v = v + np.array([0.0, 0.0, G * tau])
        t = parabola_torus_contact_time(p0, v, G, r, D)
        assert np.isfinite(t)
        assert t <= tau + 1e-9
        found += 1
    assert found == 50


def test_receding_ball_inside_window_is_not_detected():
    r, D = JAWS["pool_corner"]
    p0 = np.array([r + D + 1e-6, 0.0, 0.0])
    assert parabola_torus_contact_time(p0, np.array([1.0, 0.0, 0.0]), G, r, D) == np.inf
    approaching = parabola_torus_contact_time(p0, np.array([-1.0, 0.0, 0.0]), G, r, D)
    assert approaching == pytest.approx(1e-6, rel=1e-3)


def test_no_window_means_no_contact():
    r, D = JAWS["pool_corner"]
    p0 = np.array([0.3, 0.0, 0.0])
    v = np.array([0.0, 1.0, 0.0])
    count = torus_contact_windows(p0[0], p0[1], p0[2], v[0], v[1], v[2], G, r, D)[0]
    assert count == 0
    assert parabola_torus_contact_time(p0, v, G, r, D) == np.inf


def test_ball_above_the_band_gets_two_windows():
    """Rising through the band and falling back through it are separate intervals."""
    r, D = JAWS["pool_corner"]
    p0 = np.array([r + 0.5 * D, 0.0, -0.5 * D])
    v = np.array([0.0, 0.0, 3.0])
    count, lo0, hi0, lo1, hi1 = torus_contact_windows(
        p0[0], p0[1], p0[2], v[0], v[1], v[2], G, r, D
    )
    assert count == 2
    assert lo0 == 0.0 and hi0 < lo1 < hi1


def test_arc_intervals_narrow_wedge_is_one_bounded_interval():
    """Along ``y = 1`` the azimuth is between 45 and 90 degrees for ``x`` in [0, 1]."""
    count, lo, hi, _, _ = arc_intervals(-3.0, 1.0, 1.0, 0.0, np.pi / 4, np.pi / 4)
    assert count == 1
    assert lo == pytest.approx(3.0)
    assert hi == pytest.approx(4.0)


def test_arc_intervals_wide_arc_is_everything_but_the_gap():
    count, lo, hi, _, _ = arc_intervals(-3.0, 1.0, 1.0, 0.0, np.pi / 2, 1.5 * np.pi)
    assert count == 1
    assert lo == -np.inf
    assert hi == pytest.approx(3.0)

    count, lo0, hi0, lo1, hi1 = arc_intervals(
        -3.0, 1.0, 1.0, 0.0, np.pi / 2, 1.75 * np.pi
    )
    assert count == 2
    assert lo0 == -np.inf
    assert hi0 == pytest.approx(3.0)
    assert lo1 == pytest.approx(4.0)
    assert hi1 == np.inf


def test_arc_intervals_full_ring_is_unbounded():
    count, lo, hi, _, _ = arc_intervals(0.3, -0.2, 1.0, 2.0, 1.0, FULL_RING)
    assert count == 1
    assert lo == -np.inf
    assert hi == np.inf


def test_arc_intervals_path_missing_the_wedge_is_empty():
    count = arc_intervals(-3.0, -1.0, 1.0, 0.0, np.pi / 4, np.pi / 4)[0]
    assert count == 0
