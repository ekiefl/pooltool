"""Candidate airborne ball vs torus jaw detectors, all numba-jitted.

Every detector has the signature ``(X0, Y0, Z0, vx, vy, vz, G, r, D) -> (t, iters)`` in the
jaw-centered frame, returning ``np.inf`` when there is no upcoming contact.
"""

import numpy as np
from numba import njit

from pooltool.evolution.event_based.detect.quartic_coefficients import (
    parabola_circle_distance_2d_quartic_coefficients,
)
from pooltool.evolution.event_based.detect.torus import parabola_torus_contact_time
from pooltool.ptmath.roots import ABS_OR_REL_CUTOFF, ATOL, RTOL, is_real_number, quartic

INF = np.inf
MAXIT = 30
QUADRIC_MAXIT = 80
CONVERGED = 1e-11
G_TOL = 1e-14
C_MIN = 1e-9
RHO_SMALL_FRACTION = 0.1


@njit(cache=True)
def g_and_dg(t, X0, Y0, Z0, vx, vy, vz, G, r, D):
    X = X0 + vx * t
    Y = Y0 + vy * t
    Z = Z0 + vz * t - 0.5 * G * t * t
    rho = np.sqrt(X * X + Y * Y)
    if rho > 0.0:
        drho = (X * vx + Y * vy) / rho
    else:
        drho = 0.0
    gval = (rho - r) ** 2 + Z * Z - D * D
    dg = 2.0 * (rho - r) * drho + 2.0 * Z * (vz - G * t)
    return gval, dg


@njit(cache=True)
def windows(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Certified time windows in which contact is possible.

    Intersection of the bounding vertical cylinder of radius ``r + D`` with the height
    band ``|Z| <= D`` and ``t >= 0``. Returns ``(count, lo0, hi0, lo1, hi1)``.
    """
    alpha = vx * vx + vy * vy
    beta = 2.0 * (X0 * vx + Y0 * vy)
    gamma = X0 * X0 + Y0 * Y0 - (r + D) ** 2

    if alpha < 1e-14:
        if gamma > 0.0:
            return 0, INF, INF, INF, INF
        tc1, tc2 = 0.0, INF
    else:
        disc = beta * beta - 4.0 * alpha * gamma
        if disc < 0.0:
            return 0, INF, INF, INF, INF
        sd = np.sqrt(disc)
        tc1 = (-beta - sd) / (2.0 * alpha)
        tc2 = (-beta + sd) / (2.0 * alpha)

    disc_lo = vz * vz + 2.0 * G * (Z0 + D)
    if disc_lo < 0.0:
        return 0, INF, INF, INF, INF
    sd_lo = np.sqrt(disc_lo)
    tb1 = (vz - sd_lo) / G
    tb2 = (vz + sd_lo) / G

    lo0 = max(tb1, tc1, 0.0)
    hi0 = min(tb2, tc2)
    disc_hi = vz * vz + 2.0 * G * (Z0 - D)
    if disc_hi < 0.0:
        if lo0 < hi0:
            return 1, lo0, hi0, INF, INF
        return 0, INF, INF, INF, INF

    sd_hi = np.sqrt(disc_hi)
    ta1 = (vz - sd_hi) / G
    ta2 = (vz + sd_hi) / G

    n = 0
    w0lo, w0hi, w1lo, w1hi = INF, INF, INF, INF
    lo = max(tb1, tc1, 0.0)
    hi = min(ta1, tc2)
    if lo < hi:
        w0lo, w0hi = lo, hi
        n = 1
    lo = max(ta2, tc1, 0.0)
    hi = min(tb2, tc2)
    if lo < hi:
        if n == 0:
            w0lo, w0hi = lo, hi
        else:
            w1lo, w1hi = lo, hi
        n += 1
    return n, w0lo, w0hi, w1lo, w1hi


@njit(cache=True)
def detect_windows_only(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Cost reference: the prefilter alone, returning the first window start."""
    n, lo0, _hi0, _lo1, _hi1 = windows(X0, Y0, Z0, vx, vy, vz, G, r, D)
    if n == 0:
        return INF, 0
    return lo0, 0


@njit(cache=True)
def _newton_polish(t, X0, Y0, Z0, vx, vy, vz, G, r, D, steps):
    for _ in range(steps):
        gval, dg = g_and_dg(t, X0, Y0, Z0, vx, vy, vz, G, r, D)
        if dg == 0.0:
            break
        t -= gval / dg
    return t


@njit(cache=True)
def detect_octic(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Exact: degree-8 polynomial via companion-matrix eigenvalues, then Newton polish."""
    rho2 = np.array([X0 * X0 + Y0 * Y0, 2.0 * (X0 * vx + Y0 * vy), vx * vx + vy * vy])
    Zc = np.array([Z0, vz, -0.5 * G])
    Z2 = np.zeros(5)
    for i in range(3):
        for j in range(3):
            Z2[i + j] += Zc[i] * Zc[j]
    q = Z2.copy()
    q[0] += rho2[0] + r * r - D * D
    q[1] += rho2[1]
    q[2] += rho2[2]
    octic = np.zeros(9)
    for i in range(5):
        for j in range(5):
            octic[i + j] += q[i] * q[j]
    for i in range(3):
        octic[i] -= 4.0 * r * r * rho2[i]
    desc = np.empty(9, dtype=np.complex128)
    for i in range(9):
        desc[i] = octic[8 - i]
    roots = np.roots(desc)

    best = INF
    for k in range(roots.shape[0]):
        root = roots[k]
        if abs(root.imag) > 1e-6:
            continue
        t = _newton_polish(root.real, X0, Y0, Z0, vx, vy, vz, G, r, D, 4)
        if t <= 0.0 or t >= best:
            continue
        gval, dg = g_and_dg(t, X0, Y0, Z0, vx, vy, vz, G, r, D)
        if abs(gval) > 1e-10 or dg > 1e-9:
            continue
        best = t
    return best, 1


@njit(cache=True)
def _sample_bisect_window(lo, hi, n, X0, Y0, Z0, vx, vy, vz, G, r, D):
    dt = (hi - lo) / n
    g_prev, _ = g_and_dg(lo, X0, Y0, Z0, vx, vy, vz, G, r, D)
    for i in range(1, n + 1):
        t = lo + dt * i
        g_cur, _ = g_and_dg(t, X0, Y0, Z0, vx, vy, vz, G, r, D)
        if g_prev > 0.0 and g_cur <= 0.0:
            a, b = t - dt, t
            for _ in range(25):
                m = 0.5 * (a + b)
                gm, _ = g_and_dg(m, X0, Y0, Z0, vx, vy, vz, G, r, D)
                if gm > 0.0:
                    a = m
                else:
                    b = m
            return _newton_polish(0.5 * (a + b), X0, Y0, Z0, vx, vy, vz, G, r, D, 3)
        g_prev = g_cur
    return INF


@njit(cache=True)
def detect_sample_bisect(X0, Y0, Z0, vx, vy, vz, G, r, D, n):
    """Prefilter, then n uniform samples per window, bisection on the first sign change."""
    cnt, lo0, hi0, lo1, hi1 = windows(X0, Y0, Z0, vx, vy, vz, G, r, D)
    if cnt == 0:
        return INF, 0
    t = _sample_bisect_window(lo0, hi0, n, X0, Y0, Z0, vx, vy, vz, G, r, D)
    if t < INF or cnt == 1:
        return t, n
    return _sample_bisect_window(lo1, hi1, n, X0, Y0, Z0, vx, vy, vz, G, r, D), 2 * n


@njit(cache=True)
def detect_sample_bisect_4(X0, Y0, Z0, vx, vy, vz, G, r, D):
    return detect_sample_bisect(X0, Y0, Z0, vx, vy, vz, G, r, D, 4)


@njit(cache=True)
def detect_sample_bisect_16(X0, Y0, Z0, vx, vy, vz, G, r, D):
    return detect_sample_bisect(X0, Y0, Z0, vx, vy, vz, G, r, D, 16)


@njit(cache=True)
def detect_sample_bisect_64(X0, Y0, Z0, vx, vy, vz, G, r, D):
    return detect_sample_bisect(X0, Y0, Z0, vx, vy, vz, G, r, D, 64)


@njit(cache=True)
def _newton_window(lo, hi, X0, Y0, Z0, vx, vy, vz, G, r, D):
    t = lo
    for it in range(MAXIT):
        gval, dg = g_and_dg(t, X0, Y0, Z0, vx, vy, vz, G, r, D)
        if dg == 0.0:
            return INF, it
        t_new = t - gval / dg
        if abs(t_new - t) < CONVERGED:
            gval, dg = g_and_dg(t_new, X0, Y0, Z0, vx, vy, vz, G, r, D)
            if t_new >= lo and t_new <= hi and abs(gval) < 1e-10 and dg <= 1e-9:
                return t_new, it + 1
            return INF, it + 1
        t = t_new
    return INF, MAXIT


@njit(cache=True)
def detect_newton(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Prefilter, then plain scalar Newton from the window entry time."""
    cnt, lo0, hi0, lo1, hi1 = windows(X0, Y0, Z0, vx, vy, vz, G, r, D)
    if cnt == 0:
        return INF, 0
    t, it = _newton_window(lo0, hi0, X0, Y0, Z0, vx, vy, vz, G, r, D)
    if t < INF or cnt == 1:
        return t, it
    t, it2 = _newton_window(lo1, hi1, X0, Y0, Z0, vx, vy, vz, G, r, D)
    return t, it + it2


@njit(cache=True)
def _first_entry_root(C, roots, t_min, c0, c1, c2, sign):
    """Smallest real root at or after ``t_min`` where the model polynomial is decreasing.

    ``sign`` restricts the model radius ``c0 + c1 t + c2 t**2`` to be non-negative (+1),
    non-positive (-1), or unrestricted (0) at the root.
    """
    best = INF
    for k in range(roots.shape[0]):
        root = roots[k]
        if not is_real_number(root, ABS_OR_REL_CUTOFF, RTOL, ATOL):
            continue
        t = root.real
        if t < t_min - 1e-12 or t >= best:
            continue
        slope = C[1] + 2.0 * C[2] * t + 3.0 * C[3] * t * t + 4.0 * C[4] * t * t * t
        if slope > 0.0:
            continue
        if sign != 0:
            L = c0 + c1 * t + c2 * t * t
            if sign * L < -1e-12:
                continue
        best = t
    return best


@njit(cache=True)
def _tangent_window(lo, hi, X0, Y0, Z0, vx, vy, vz, G, r, D, order, mirror):
    """Meridian-plane iteration: replace rho(t) by its Taylor polynomial about t_k.

    ``order`` 1 is the tangent line, equivalent to projecting the trajectory into the
    vertical plane through the jaw axis at the ball's azimuth. ``order`` 2 is the
    osculating parabola. With ``mirror`` the far half of that plane is modelled too, so
    the torus section is its exact pair of circles at radius ``+r`` and ``-r``. Each
    iterate solves parabola-circle quartics exactly and re-expands at the root found.
    """
    center = np.array([r, 0.0])
    center_m = np.array([-r, 0.0])
    xy = np.empty((2, 3))
    xy[1, 0] = Z0
    xy[1, 1] = vz
    xy[1, 2] = -0.5 * G
    alpha = vx * vx + vy * vy
    beta = 2.0 * (X0 * vx + Y0 * vy)

    t_k = lo
    for it in range(MAXIT):
        X = X0 + vx * t_k
        Y = Y0 + vy * t_k
        rho = np.sqrt(X * X + Y * Y)
        q1 = 2.0 * alpha * t_k + beta
        if rho > 1e-12:
            drho = q1 / (2.0 * rho)
            if order == 2:
                ddrho = (2.0 * alpha * rho - q1 * drho) / (2.0 * rho * rho)
            else:
                ddrho = 0.0
        else:
            drho = np.sqrt(alpha)
            ddrho = 0.0
        c2 = 0.5 * ddrho
        c1 = drho - ddrho * t_k
        c0 = rho - drho * t_k + 0.5 * ddrho * t_k * t_k
        xy[0, 0] = c0
        xy[0, 1] = c1
        xy[0, 2] = c2
        C = parabola_circle_distance_2d_quartic_coefficients(xy, center, D)
        roots = quartic.solve(C[4], C[3], C[2], C[1], C[0])
        if mirror:
            t_next = _first_entry_root(C, roots, lo, c0, c1, c2, 1)
            Cm = parabola_circle_distance_2d_quartic_coefficients(xy, center_m, D)
            roots_m = quartic.solve(Cm[4], Cm[3], Cm[2], Cm[1], Cm[0])
            t_m = _first_entry_root(Cm, roots_m, lo, c0, c1, c2, -1)
            t_next = min(t_next, t_m)
        else:
            t_next = _first_entry_root(C, roots, lo, c0, c1, c2, 0)
        if t_next == INF:
            return INF, it + 1
        if t_next > hi + 1e-9:
            return INF, it + 1
        if abs(t_next - t_k) < CONVERGED:
            _gval, dg = g_and_dg(t_next, X0, Y0, Z0, vx, vy, vz, G, r, D)
            if dg <= 1e-9:
                return t_next, it + 1
            return INF, it + 1
        t_k = t_next
    return INF, MAXIT


@njit(cache=True)
def _tangent(X0, Y0, Z0, vx, vy, vz, G, r, D, order, mirror):
    cnt, lo0, hi0, lo1, hi1 = windows(X0, Y0, Z0, vx, vy, vz, G, r, D)
    if cnt == 0:
        return INF, 0
    t, it = _tangent_window(lo0, hi0, X0, Y0, Z0, vx, vy, vz, G, r, D, order, mirror)
    if t < INF or cnt == 1:
        return t, it
    t, it2 = _tangent_window(lo1, hi1, X0, Y0, Z0, vx, vy, vz, G, r, D, order, mirror)
    return t, it + it2


@njit(cache=True)
def detect_tangent(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Prefilter, then tangent-cylinder (first-order meridian) quartic iteration."""
    return _tangent(X0, Y0, Z0, vx, vy, vz, G, r, D, 1, False)


@njit(cache=True)
def detect_osculating(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Prefilter, then osculating-parabola (second-order meridian) quartic iteration."""
    return _tangent(X0, Y0, Z0, vx, vy, vz, G, r, D, 2, False)


@njit(cache=True)
def detect_meridian(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Prefilter, then projection into the meridian plane with both torus circles."""
    return _tangent(X0, Y0, Z0, vx, vy, vz, G, r, D, 1, True)


@njit(cache=True)
def detect_meridian_osc(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Meridian projection with both circles and a second-order radial model."""
    return _tangent(X0, Y0, Z0, vx, vy, vz, G, r, D, 2, True)


@njit(cache=True)
def _first_entry_root_poly(b0, b1, b2, b3, b4, t_min, t_max):
    """First real root of the quartic in ``[t_min, t_max]`` where it is non-increasing."""
    roots = quartic.solve(b4, b3, b2, b1, b0)
    best = INF
    for j in range(4):
        root = roots[j]
        if not is_real_number(root, ABS_OR_REL_CUTOFF, RTOL, ATOL):
            continue
        t = root.real
        if t < t_min - 1e-12 or t > t_max + 1e-12 or t >= best:
            continue
        slope = b1 + 2.0 * b2 * t + 3.0 * b3 * t * t + 4.0 * b4 * t * t * t
        if slope > 0.0:
            continue
        best = t
    return best


@njit(cache=True)
def _eval_poly(b0, b1, b2, b3, b4, t):
    return b0 + t * (b1 + t * (b2 + t * (b3 + t * b4)))


@njit(cache=True)
def _quadric_window(lo, hi, X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Enclosing-quadric iteration.

    ``g = P(t) - 2 r rho`` with ``P`` quartic, so any polynomial upper bound ``U >= rho``
    gives a quartic ``P - 2 r U`` that is a global lower bound on ``g``. Its first
    non-increasing root at or after ``t_k`` is never later than the true first root, so
    stepping to it is monotone and no root is a certificate of no contact.

    Two bounds are used. ``rho <= (rho**2 + c**2) / (2 c)`` (tight on the parallel
    ``rho = c``, an enclosing spheroid or hyperboloid of revolution) with ``c`` the
    radius at ``t_k`` converges quadratically except when ``c`` is tiny, so near the
    axis it is combined with the triangle-inequality bound ``rho <= m + sqrt(alpha)
    |t - t_m|`` (``m`` the horizontal miss distance, ``t_m`` its time), whose slack is
    at most ``m``. Both are valid lower bounds on the contact time, so the later one is
    taken.
    """
    alpha = vx * vx + vy * vy
    beta = 2.0 * (X0 * vx + Y0 * vy)
    gamma = X0 * X0 + Y0 * Y0
    z0 = Z0 * Z0
    z1 = 2.0 * Z0 * vz
    z2 = vz * vz - G * Z0
    z3 = -G * vz
    z4 = 0.25 * G * G
    p0 = gamma + z0 + r * r - D * D
    p1 = beta + z1
    p2 = alpha + z2
    rho_small = RHO_SMALL_FRACTION * (r + D)

    if alpha < 1e-14:
        sa = 0.0
        t_m = -INF
        m = np.sqrt(gamma)
    else:
        sa = np.sqrt(alpha)
        t_m = -beta / (2.0 * alpha)
        m2 = gamma - beta * beta / (4.0 * alpha)
        m = np.sqrt(m2) if m2 > 0.0 else 0.0

    t_k = lo
    for it in range(QUADRIC_MAXIT):
        X = X0 + vx * t_k
        Y = Y0 + vy * t_k
        c = np.sqrt(X * X + Y * Y)
        c = max(c, C_MIN)
        k = 1.0 - r / c
        t_next = _first_entry_root_poly(
            z0 + k * gamma + r * r - D * D - r * c,
            z1 + k * beta,
            z2 + k * alpha,
            z3,
            z4,
            t_k,
            INF,
        )
        if t_next == INF or t_next > hi + 1e-9:
            return INF, it + 1

        if c < rho_small:
            if t_k >= t_m:
                b0 = p0 - 2.0 * r * (m - sa * t_m)
                b1 = p1 - 2.0 * r * sa
                if _eval_poly(b0, b1, p2, z3, z4, t_k) >= 0.0:
                    cand = _first_entry_root_poly(b0, b1, p2, z3, z4, t_k, INF)
                    if cand == INF or cand > hi + 1e-9:
                        return INF, it + 1
                    t_next = max(t_next, cand)
            else:
                b0 = p0 - 2.0 * r * (m + sa * t_m)
                b1 = p1 + 2.0 * r * sa
                if _eval_poly(b0, b1, p2, z3, z4, t_k) >= 0.0:
                    cand = _first_entry_root_poly(b0, b1, p2, z3, z4, t_k, t_m)
                    if cand == INF:
                        if t_m > hi + 1e-9:
                            return INF, it + 1
                        cand = t_m
                    t_next = max(t_next, cand)

        gval, _dg = g_and_dg(t_next, X0, Y0, Z0, vx, vy, vz, G, r, D)
        if gval <= G_TOL:
            return t_next, it + 1
        t_k = t_next
    return INF, QUADRIC_MAXIT


@njit(cache=True)
def detect_quadric(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Prefilter, then enclosing-quadric quartic iteration with a rigorous certificate."""
    cnt, lo0, hi0, lo1, hi1 = windows(X0, Y0, Z0, vx, vy, vz, G, r, D)
    if cnt == 0:
        return INF, 0
    t, it = _quadric_window(lo0, hi0, X0, Y0, Z0, vx, vy, vz, G, r, D)
    if t < INF or cnt == 1:
        return t, it
    t, it2 = _quadric_window(lo1, hi1, X0, Y0, Z0, vx, vy, vz, G, r, D)
    return t, it + it2


@njit(cache=True)
def detect_quadric_nowindow(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """Enclosing-quadric iteration from t = 0 with no prefilter, to price the window."""
    return _quadric_window(0.0, INF, X0, Y0, Z0, vx, vy, vz, G, r, D)


@njit(cache=True)
def detect_production(X0, Y0, Z0, vx, vy, vz, G, r, D):
    """The detector shipped in pooltool, for benchmarking against the candidates."""
    t = parabola_torus_contact_time(
        np.array([X0, Y0, Z0]), np.array([vx, vy, vz]), G, r, D
    )
    return t, 0


METHODS = {
    "windows_only": detect_windows_only,
    "octic": detect_octic,
    "sample_bisect_4": detect_sample_bisect_4,
    "sample_bisect_16": detect_sample_bisect_16,
    "sample_bisect_64": detect_sample_bisect_64,
    "newton": detect_newton,
    "tangent": detect_tangent,
    "osculating": detect_osculating,
    "meridian": detect_meridian,
    "meridian_osc": detect_meridian_osc,
    "quadric": detect_quadric,
    "quadric_nowindow": detect_quadric_nowindow,
    "production": detect_production,
}
