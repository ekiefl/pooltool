"""On-table behaviour of the quadric iteration, and in-jit speed vs the production 2D quartic.

Usage:
    python sandbox/torus_jaw/bench2.py
"""

import sys
import time
from pathlib import Path

import numpy as np
from numba import njit

sys.path.insert(0, str(Path(__file__).parent))
from geometry import (
    FAMILIES,
    JAWS,
    NOSE,
    R_POOL,
    G,
    generate_cases,
    reference_solution,
)
from methods import G_TOL, QUADRIC_MAXIT, detect_quadric, windows

import pooltool.constants as const
from pooltool.evolution.event_based.detect.ball_cushion import (
    ball_vertical_cylinder_collision_time,
)
from pooltool.ptmath.roots import (
    ABS_OR_REL_CUTOFF,
    ATOL,
    RTOL,
    get_real_positive_smallest_root,
    is_real_number,
    quartic,
)

INF = np.inf


@njit(cache=True)
def poly_g(t, p, r, D):
    x = p[0, 0] + p[0, 1] * t + p[0, 2] * t * t
    y = p[1, 0] + p[1, 1] * t + p[1, 2] * t * t
    z = p[2, 0] + p[2, 1] * t + p[2, 2] * t * t
    rho = np.sqrt(x * x + y * y)
    return (rho - r) ** 2 + z * z - D * D


@njit(cache=True)
def quadric_poly(p, r, D, hi):
    """AM-GM enclosing-quadric iteration for a general (3, 3) position polynomial.

    Rows of ``p`` are (constant, linear, quadratic) coefficients of x, y, z in the
    jaw-centered frame. No prefilter and no triangle bound: this isolates the question
    of how the iteration behaves when z is constant.
    """
    x = p[0]
    y = p[1]
    z = p[2]
    rho2 = np.zeros(5)
    z2 = np.zeros(5)
    for i in range(3):
        for j in range(3):
            rho2[i + j] += x[i] * x[j] + y[i] * y[j]
            z2[i + j] += z[i] * z[j]
    t_k = 0.0
    for it in range(QUADRIC_MAXIT):
        xk = x[0] + x[1] * t_k + x[2] * t_k * t_k
        yk = y[0] + y[1] * t_k + y[2] * t_k * t_k
        c = np.sqrt(xk * xk + yk * yk)
        c = max(c, 1e-9)
        k = 1.0 - r / c
        b = k * rho2 + z2
        b[0] += r * r - D * D - r * c
        roots = quartic.solve(b[4], b[3], b[2], b[1], b[0])
        t_next = INF
        for j in range(4):
            root = roots[j]
            if not is_real_number(root, ABS_OR_REL_CUTOFF, RTOL, ATOL):
                continue
            t = root.real
            if t < t_k - 1e-12 or t >= t_next:
                continue
            slope = b[1] + 2 * b[2] * t + 3 * b[3] * t * t + 4 * b[4] * t * t * t
            if slope > 0.0:
                continue
            t_next = t
        if t_next == INF or t_next > hi:
            return INF, it + 1
        if poly_g(t_next, p, r, D) <= G_TOL:
            return t_next, it + 1
        t_k = t_next
    return INF, QUADRIC_MAXIT


@njit(cache=True)
def effective_radius_quartic(p, r_eff):
    """Exact on-table solve: |xy(t)|**2 = r_eff**2, the existing 2D cylinder quartic."""
    x = p[0]
    y = p[1]
    b = np.zeros(5)
    for i in range(3):
        for j in range(3):
            b[i + j] += x[i] * x[j] + y[i] * y[j]
    b[0] -= r_eff * r_eff
    return get_real_positive_smallest_root(
        quartic.solve(b[4], b[3], b[2], b[1], b[0]), ABS_OR_REL_CUTOFF, RTOL, ATOL
    )


def on_table_cases(n, jaw, seed):
    """Rolling/sliding balls near a jaw: z constant, xy quadratic with friction deceleration."""
    rng = np.random.default_rng(seed)
    Z = R_POOL - jaw.h
    s = np.sqrt(jaw.D**2 - Z**2)
    r_eff = jaw.r + s
    out = []
    while len(out) < n:
        d0 = rng.uniform(r_eff + 1e-3, 0.4)
        az = rng.uniform(0, 2 * np.pi)
        X0, Y0 = d0 * np.cos(az), d0 * np.sin(az)
        speed = rng.uniform(0.2, 5.0)
        miss = rng.uniform(-r_eff * 1.2, r_eff * 1.2)
        toward = -np.array([X0, Y0]) / d0
        perp = np.array([-toward[1], toward[0]])
        direction = miss * perp - np.array([X0, Y0])
        direction /= np.linalg.norm(direction)
        v = speed * direction
        if rng.uniform() < 0.5:
            a = -0.01 * G * direction
        else:
            slip = rng.normal(size=2)
            slip /= np.linalg.norm(slip)
            a = -0.2 * G * slip
        p = np.array([[X0, v[0], 0.5 * a[0]], [Y0, v[1], 0.5 * a[1]], [Z, 0.0, 0.0]])
        out.append(p)
    return np.array(out), r_eff


def on_table_study():
    print(
        "=== on-table balls (z constant): quadric iteration vs one-shot effective-radius quartic"
    )
    for jaw in JAWS[:2]:
        ps, r_eff = on_table_cases(3000, jaw, 0)
        hi = 3.0
        t_q = np.empty(len(ps))
        it_q = np.empty(len(ps))
        t_e = np.empty(len(ps))
        for i, p in enumerate(ps):
            t_q[i], it_q[i] = quadric_poly(p, jaw.r, jaw.D, hi)
            t_e[i] = effective_radius_quartic(p, r_eff)
        t_e[t_e > hi] = INF
        hit = np.isfinite(t_e)
        agree = np.isfinite(t_q) == hit
        err = np.abs(t_q[hit & agree] - t_e[hit & agree])
        print(
            f"  {jaw.name}: r_eff = {r_eff:.5f} (vs r + R = {jaw.r + R_POOL:.5f}); {hit.sum()} hits of {len(ps)}"
        )
        print(
            f"    hit/miss disagreements: {(~agree).sum()}, max |dt| on hits: {err.max():.1e}"
        )
        ih = np.bincount(it_q[hit].astype(int))
        im = np.bincount(it_q[~hit].astype(int))
        print(
            f"    quadric solves on hits:   mean {it_q[hit].mean():.2f}  hist "
            + " ".join(f"{i}:{c}" for i, c in enumerate(ih) if c)
        )
        print(
            f"    quadric solves on misses: mean {it_q[~hit].mean():.2f}  hist "
            + " ".join(f"{i}:{c}" for i, c in enumerate(im) if c)
        )
    print()


def make_prod_runner():
    @njit
    def run(rvws, ss, mus, a, b, r, m, g, R, nose_radius, height, out):
        for i in range(rvws.shape[0]):
            out[i] = ball_vertical_cylinder_collision_time(
                rvws[i], ss[i], a, b, r, mus[i], m, g, R, nose_radius, height
            )

    return run


def make_quadric_runner():
    @njit
    def run(cases, out):
        for i in range(cases.shape[0]):
            c = cases[i]
            t, _it = detect_quadric(c[0], c[1], c[2], c[3], c[4], c[5], G, c[6], c[7])
            out[i] = t

    return run


def timeit(fn, args, n, target=0.5):
    fn(*args)
    reps = 1
    while True:
        t0 = time.perf_counter()
        for _ in range(reps):
            fn(*args)
        el = time.perf_counter() - t0
        if el > target:
            return el / (reps * n) * 1e9
        reps *= 2


def speed_study():
    print("=== in-jit cost per call (ns)")
    rng = np.random.default_rng(0)
    n = 6000
    jaw = JAWS[0]
    rvws = np.zeros((n, 3, 3))
    d0 = rng.uniform(0.05, 0.5, n)
    az = rng.uniform(0, 2 * np.pi, n)
    rvws[:, 0, 0] = d0 * np.cos(az)
    rvws[:, 0, 1] = d0 * np.sin(az)
    rvws[:, 0, 2] = R_POOL
    sp = rng.uniform(0.2, 5, n)
    vaz = rng.uniform(0, 2 * np.pi, n)
    rvws[:, 1, 0] = sp * np.cos(vaz)
    rvws[:, 1, 1] = sp * np.sin(vaz)
    rvws[:, 2, :] = rng.normal(size=(n, 3)) * 5
    ss = np.where(rng.uniform(size=n) < 0.5, const.rolling, const.sliding).astype(
        np.int64
    )
    mus = np.where(ss == const.rolling, 0.01, 0.2)
    out = np.empty(n)
    run = make_prod_runner()
    prod = timeit(
        run, (rvws, ss, mus, jaw.r, 0.0, jaw.r, 0.17, G, R_POOL, NOSE, jaw.h, out), n
    )
    print(
        f"  production 2D cylinder quartic (random rolling/sliding states): {prod:7.0f}"
    )

    cases, labels = generate_cases(400, 0)
    fams = np.array([lab[1] for lab in labels])
    qrun = make_quadric_runner()
    nwin = np.array(
        [windows(c[0], c[1], c[2], c[3], c[4], c[5], G, c[6], c[7])[0] for c in cases]
    )
    ref = np.array([reference_solution(c)[0] for c in cases])
    hit = np.isfinite(ref)
    rows = [
        ("all airborne cases", np.ones(len(cases), bool)),
        ("  rejected by window", nwin == 0),
        ("  passed window, miss", (nwin > 0) & ~hit),
        ("  hits", hit),
    ]
    rows += [(f"  hits, family {f}", hit & (fams == f)) for f in FAMILIES]
    for name, sel in rows:
        sub = np.ascontiguousarray(cases[sel])
        ns = timeit(qrun, (sub, np.empty(len(sub))), len(sub))
        print(
            f"  quadric, {name:28s} n={len(sub):5d}: {ns:7.0f}   ({ns / prod:4.1f}x production 2D)"
        )


if __name__ == "__main__":
    on_table_study()
    speed_study()
