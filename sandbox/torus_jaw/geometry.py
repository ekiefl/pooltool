"""Case generation and a high-precision reference solver for airborne ball vs torus jaw.

All quantities are in a jaw-centered frame: the jaw nose circle has radius ``r`` and lies
in the plane Z = 0, the ball center must stay a distance ``D = R + nose_radius`` from it.
The ball is airborne, so X and Y are linear in t and Z is a downward parabola.
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq, minimize_scalar

G = 9.81
R_POOL = 0.028575
R_SNOOKER = 0.02625
NOSE = 0.001

FAMILIES = ("aimed", "drop", "departing", "random", "graze", "axis")


@dataclass(frozen=True)
class Jaw:
    name: str
    r: float
    h: float
    D: float


JAWS = (
    Jaw("pool_corner", 0.02095, 0.037, R_POOL + NOSE),
    Jaw("pool_side", 0.00795, 0.037, R_POOL + NOSE),
    Jaw("snooker_corner", 0.1016, 0.037, R_SNOOKER + NOSE),
)


def g_of_t(t, c):
    X0, Y0, Z0, vx, vy, vz, r, D = c
    X = X0 + vx * t
    Y = Y0 + vy * t
    Z = Z0 + vz * t - 0.5 * G * t * t
    rho = np.hypot(X, Y)
    return (rho - r) ** 2 + Z**2 - D**2


def _accept(c, jaw, R):
    z_table = R - jaw.h
    return c[2] >= z_table - 1e-12 and g_of_t(0.0, c) > 1e-10


def _gen_aimed(rng, jaw, R):
    d0 = rng.uniform(0.05, 0.5)
    az = rng.uniform(0, 2 * np.pi)
    X0, Y0 = d0 * np.cos(az), d0 * np.sin(az)
    Z0 = rng.uniform(R - jaw.h, 0.12)
    speed = rng.uniform(0.3, 5.0)
    miss = rng.uniform(-(jaw.r + jaw.D + 0.03), jaw.r + jaw.D + 0.03)
    toward = -np.array([X0, Y0]) / d0
    perp = np.array([-toward[1], toward[0]])
    target = np.array([0.0, 0.0]) + miss * perp
    direction = target - np.array([X0, Y0])
    direction /= np.linalg.norm(direction)
    vx, vy = speed * direction
    vz = rng.uniform(-2.0, 2.0)
    return np.array([X0, Y0, Z0, vx, vy, vz, jaw.r, jaw.D])


def _gen_drop(rng, jaw, R):
    rho0 = rng.uniform(0, jaw.r + jaw.D)
    az = rng.uniform(0, 2 * np.pi)
    X0, Y0 = rho0 * np.cos(az), rho0 * np.sin(az)
    Z0 = rng.uniform(jaw.D + 0.005, 0.2)
    speed = rng.uniform(0, 1.0)
    vaz = rng.uniform(0, 2 * np.pi)
    vx, vy = speed * np.cos(vaz), speed * np.sin(vaz)
    vz = rng.uniform(-1.0, 0.5)
    return np.array([X0, Y0, Z0, vx, vy, vz, jaw.r, jaw.D])


def _gen_departing(rng, jaw, R):
    """Ball a spacer off the torus surface, moving away along the true outward normal side."""
    spacer = 1e-4
    az = rng.uniform(0, 2 * np.pi)
    polar = rng.uniform(0, 2 * np.pi)
    nose_point = np.array([jaw.r * np.cos(az), jaw.r * np.sin(az), 0.0])
    normal = np.array(
        [np.cos(polar) * np.cos(az), np.cos(polar) * np.sin(az), np.sin(polar)]
    )
    P = nose_point + (jaw.D + spacer) * normal
    rho = np.hypot(P[0], P[1])
    if rho < 1e-6:
        return None
    nose_point = np.array([jaw.r * P[0] / rho, jaw.r * P[1] / rho, 0.0])
    normal = P - nose_point
    normal /= np.linalg.norm(normal)
    P = nose_point + (jaw.D + spacer) * normal
    if P[2] < R - jaw.h:
        return None
    speed = rng.uniform(0.2, 4.0)
    v = rng.normal(size=3)
    v /= np.linalg.norm(v)
    if np.dot(v, normal) < 0:
        v = v - 2 * np.dot(v, normal) * normal
    v *= speed
    return np.array([P[0], P[1], P[2], v[0], v[1], v[2], jaw.r, jaw.D])


def _gen_random(rng, jaw, R):
    X0, Y0 = rng.uniform(-0.2, 0.2, size=2)
    Z0 = rng.uniform(R - jaw.h, 0.15)
    vx, vy = rng.uniform(-4, 4, size=2)
    vz = rng.uniform(-3, 3)
    return np.array([X0, Y0, Z0, vx, vy, vz, jaw.r, jaw.D])


def _gen_graze(rng, jaw, R):
    """Trajectory tangent to the torus at a surface point, offset by a tiny signed gap."""
    az = rng.uniform(0, 2 * np.pi)
    polar = rng.uniform(0, 2 * np.pi)
    nose_point = np.array([jaw.r * np.cos(az), jaw.r * np.sin(az), 0.0])
    normal = np.array(
        [np.cos(polar) * np.cos(az), np.cos(polar) * np.sin(az), np.sin(polar)]
    )
    gap = rng.choice([-1, 1]) * 10 ** rng.uniform(-7, -3)
    P = nose_point + (jaw.D + gap) * normal
    if P[2] < R - jaw.h + 1e-3:
        return None
    v = rng.normal(size=3)
    v -= np.dot(v, normal) * normal
    v /= np.linalg.norm(v)
    v *= rng.uniform(0.2, 4.0)
    tau = rng.uniform(0.005, 0.15)
    vz0 = v[2] + G * tau
    Z0 = P[2] - v[2] * tau - 0.5 * G * tau * tau
    X0 = P[0] - v[0] * tau
    Y0 = P[1] - v[1] * tau
    return np.array([X0, Y0, Z0, v[0], v[1], vz0, jaw.r, jaw.D])


def _gen_axis(rng, jaw, R):
    """Ball descending almost exactly along the jaw axis, where the radial bound is loosest."""
    rho0 = 10 ** rng.uniform(-7, -3)
    az = rng.uniform(0, 2 * np.pi)
    X0, Y0 = rho0 * np.cos(az), rho0 * np.sin(az)
    Z0 = rng.uniform(jaw.D + 0.005, 0.2)
    speed = 10 ** rng.uniform(-4, -1)
    vaz = rng.uniform(0, 2 * np.pi)
    vx, vy = speed * np.cos(vaz), speed * np.sin(vaz)
    vz = rng.uniform(-1.0, 0.5)
    return np.array([X0, Y0, Z0, vx, vy, vz, jaw.r, jaw.D])


GENERATORS = {
    "aimed": _gen_aimed,
    "drop": _gen_drop,
    "departing": _gen_departing,
    "random": _gen_random,
    "graze": _gen_graze,
    "axis": _gen_axis,
}


def generate_cases(n_per_family: int, seed: int = 0):
    rng = np.random.default_rng(seed)
    cases = []
    labels = []
    for jaw in JAWS:
        R = R_SNOOKER if "snooker" in jaw.name else R_POOL
        for fam in FAMILIES:
            gen = GENERATORS[fam]
            count = 0
            while count < n_per_family:
                c = gen(rng, jaw, R)
                if c is not None and _accept(c, jaw, R):
                    cases.append(c)
                    labels.append((jaw.name, fam))
                    count += 1
    return np.array(cases), labels


def horizon(c):
    """Time after which the ball is permanently below the torus band."""
    Z0, vz, D = c[2], c[5], c[7]
    return (vz + np.sqrt(vz**2 + 2 * G * (Z0 + D + 0.05))) / G


def reference_solution(c, dt: float = 1e-5):
    """First entry time into the torus, or inf, plus the closest distance to the nose circle.

    Dense sampling to ``dt`` followed by brentq on sign changes and Brent minimization on
    shallow local minima so that grazes are not missed.
    """
    T = horizon(c)
    n = int(np.ceil(T / dt)) + 1
    ts = np.linspace(0.0, T, n)
    gs = g_of_t(ts, c)
    D = c[7]
    d_min = np.sqrt(max(gs.min() + D * D, 0.0))

    f = lambda t: g_of_t(t, c)
    neg = gs <= 0
    crossings = np.flatnonzero((~neg[:-1]) & neg[1:])
    first_cross = np.inf
    if crossings.size:
        i = crossings[0]
        first_cross = brentq(f, ts[i], ts[i + 1], xtol=1e-15, rtol=1e-15, maxiter=200)

    interior = np.arange(1, n - 1)
    is_min = (gs[interior] < gs[interior - 1]) & (gs[interior] <= gs[interior + 1])
    shallow = interior[is_min & (gs[interior] > 0) & (gs[interior] < 1e-4)]
    for i in shallow:
        if ts[i] > first_cross:
            break
        res = minimize_scalar(
            f, bounds=(ts[i - 1], ts[i + 1]), method="bounded", options={"xatol": 1e-15}
        )
        if res.fun < 0:
            t_root = brentq(f, ts[i - 1], res.x, xtol=1e-15, rtol=1e-15, maxiter=200)
            first_cross = min(first_cross, t_root)
            d_min = min(d_min, np.sqrt(max(res.fun + D * D, 0.0)))
    return first_cross, d_min


def reference_octic(c):
    """Independent cross-check: solve the degree-8 polynomial in numpy and polish."""
    X0, Y0, Z0, vx, vy, vz, r, D = c
    rho2 = np.array([X0 * X0 + Y0 * Y0, 2 * (X0 * vx + Y0 * vy), vx * vx + vy * vy])
    Zc = np.array([Z0, vz, -0.5 * G])
    Z2 = np.convolve(Zc, Zc)
    q = Z2.copy()
    q[:3] += rho2
    q[0] += r * r - D * D
    octic = np.convolve(q, q)
    octic[:3] -= 4 * r * r * rho2
    roots = np.roots(octic[::-1])
    best = np.inf
    for root in roots:
        if abs(root.imag) > 1e-6:
            continue
        t = root.real
        for _ in range(5):
            X = X0 + vx * t
            Y = Y0 + vy * t
            Z = Z0 + vz * t - 0.5 * G * t * t
            rho = np.hypot(X, Y)
            gval = (rho - r) ** 2 + Z * Z - D * D
            drho = (X * vx + Y * vy) / rho if rho > 0 else 0.0
            dg = 2 * (rho - r) * drho + 2 * Z * (vz - G * t)
            if dg == 0:
                break
            t -= gval / dg
        if t <= 0:
            continue
        if abs(g_of_t(t, c)) > 1e-10:
            continue
        X = X0 + vx * t
        Y = Y0 + vy * t
        Z = Z0 + vz * t - 0.5 * G * t * t
        rho = np.hypot(X, Y)
        drho = (X * vx + Y * vy) / rho if rho > 0 else 0.0
        dg = 2 * (rho - r) * drho + 2 * Z * (vz - G * t)
        if dg > 1e-9:
            continue
        best = min(best, t)
    return best
