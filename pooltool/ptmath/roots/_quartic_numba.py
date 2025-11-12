"""1:1 exact translation of the "1010" quartic root-finding algorithm.

The original implementation is written in C, and was converted into numba by Claude
Code. The 1:1 correspondence has been tested to floating point precision on a test of
100,000 difficult to determine quartics.

Solve speed:

* Numba (this implementation): ~200ms / 100k quartics
* C (original implementation): ~120ms / 100k quartics

References:
    @article{10.1145/3386241,
        author = {Orellana, Alberto Giacomo and Michele, Cristiano De},
        title = {Algorithm 1010: Boosting Efficiency in Solving Quartic Equations with No Compromise in Accuracy},
        year = {2020},
        issue_date = {June 2020},
        publisher = {Association for Computing Machinery},
        address = {New York, NY, USA},
        volume = {46},
        number = {2},
        issn = {0098-3500},
        url = {https://doi.org/10.1145/3386241},
        doi = {10.1145/3386241},
        abstract = {Aiming to provide a very accurate, efficient, and robust quartic
        equation solver for physical applications, we have proposed an algorithm that
        builds on the previous works of P. Strobach and S. L. Shmakov. It is based on
        the decomposition of the quartic polynomial into two quadratics, whose
        coefficients are first accurately estimated by handling carefully numerical
        errors and afterward refined through the use of the Newton-Raphson method. Our
        algorithm is very accurate in comparison with other state-of-the-art solvers
        that can be found in the literature, but (most importantly) it turns out to be
        very efficient according to our timing tests. A crucial issue for us is the
        robustness of the algorithm, i.e., its ability to cope with the detrimental
        effect of round-off errors, no matter what set of quartic coefficients is
        provided in a practical application. In this respect, we extensively tested our
        algorithm in comparison to other quartic equation solvers both by considering
        specific extreme cases and by carrying out a statistical analysis over a very
        large set of quartics. Our algorithm has also been heavily tested in a physical
        application, i.e., simulations of hard cylinders, where it proved its absolute
        reliability as well as its efficiency.},
        journal = {ACM Trans. Math. Softw.},
        month = may,
        articleno = {20},
        numpages = {28},
        keywords = {Newton-Raphson scheme, Quartic equation, factorization into quadratics, numerical solver design, performance}
    }
"""

import math

import numpy as np
from numba import float64, jit, njit
from numpy.typing import NDArray

import pooltool.constants as const

cubic_rescal_fact = 3.488062113727083e102
quart_rescal_fact = 7.156344627944542e76
macheps = 2.2204460492503131e-16


@njit(float64(float64, float64))
def oqs_max2(a, b):
    if a >= b:
        return a
    else:
        return b


@njit(float64(float64, float64, float64))
def oqs_max3(a, b, c):
    t = oqs_max2(a, b)
    return oqs_max2(t, c)


@jit(nopython=True, cache=const.use_numba_cache)
def oqs_solve_cubic_analytic_depressed_handle_inf(b, c):
    PI2 = math.pi / 2.0
    TWOPI = 2.0 * math.pi
    Q = -b / 3.0
    R = 0.5 * c
    if R == 0:
        if b <= 0:
            sol = math.sqrt(-b)
        else:
            sol = 0.0
        return sol

    if abs(Q) < abs(R):
        QR = Q / R
        QRSQ = QR * QR
        KK = 1.0 - Q * QRSQ
    else:
        RQ = R / Q
        KK = math.copysign(1.0, Q) * (RQ * RQ / Q - 1.0)

    if KK < 0.0:
        sqrtQ = math.sqrt(Q)
        theta = math.acos((R / abs(Q)) / sqrtQ)
        if theta < PI2:
            sol = -2.0 * sqrtQ * math.cos(theta / 3.0)
        else:
            sol = -2.0 * sqrtQ * math.cos((theta + TWOPI) / 3.0)
    else:
        if abs(Q) < abs(R):
            A = -math.copysign(1.0, R) * math.pow(
                abs(R) * (1.0 + math.sqrt(KK)), 1.0 / 3.0
            )
        else:
            A = -math.copysign(1.0, R) * math.pow(
                abs(R) + math.sqrt(abs(Q)) * abs(Q) * math.sqrt(KK), 1.0 / 3.0
            )
        if A == 0.0:
            B = 0.0
        else:
            B = Q / A
        sol = A + B
    return sol


@jit(nopython=True, cache=const.use_numba_cache)
def oqs_solve_cubic_analytic_depressed(b, c):
    Q = -b / 3.0
    R = 0.5 * c
    if abs(Q) > 1e102 or abs(R) > 1e154:
        sol = oqs_solve_cubic_analytic_depressed_handle_inf(b, c)
        return sol
    Q3 = Q * Q * Q
    R2 = R * R
    if R2 < Q3:
        theta = math.acos(R / math.sqrt(Q3))
        sqrtQ = -2.0 * math.sqrt(Q)
        if theta < math.pi / 2:
            sol = sqrtQ * math.cos(theta / 3.0)
        else:
            sol = sqrtQ * math.cos((theta + 2.0 * math.pi) / 3.0)
    else:
        A = -math.copysign(1.0, R) * math.pow(abs(R) + math.sqrt(R2 - Q3), 1.0 / 3.0)
        if A == 0.0:
            B = 0.0
        else:
            B = Q / A
        sol = A + B
    return sol


@jit(nopython=True, cache=const.use_numba_cache)
def oqs_calc_phi0(a, b, c, d, scaled):
    diskr = 9 * a * a - 24 * b
    if diskr > 0.0:
        diskr = math.sqrt(diskr)
        if a > 0.0:
            s = -2 * b / (3 * a + diskr)
        else:
            s = -2 * b / (3 * a - diskr)
    else:
        s = -a / 4

    aq = a + 4 * s
    bq = b + 3 * s * (a + 2 * s)
    cq = c + s * (2 * b + s * (3 * a + 4 * s))
    dq = d + s * (c + s * (b + s * (a + s)))
    gg = bq * bq / 9
    hh = aq * cq

    g = hh - 4 * dq - 3 * gg
    h = (8 * dq + hh - 2 * gg) * bq / 3 - cq * cq - dq * aq * aq
    rmax = oqs_solve_cubic_analytic_depressed(g, h)
    if math.isnan(rmax) or math.isinf(rmax):
        rmax = oqs_solve_cubic_analytic_depressed_handle_inf(g, h)
        if (math.isnan(rmax) or math.isinf(rmax)) and scaled:
            rfact = cubic_rescal_fact
            rfactsq = rfact * rfact
            ggss = gg / rfactsq
            hhss = hh / rfactsq
            dqss = dq / rfactsq
            aqs = aq / rfact
            bqs = bq / rfact
            cqs = cq / rfact
            ggss = bqs * bqs / 9.0
            hhss = aqs * cqs
            g = hhss - 4.0 * dqss - 3.0 * ggss
            h = (
                (8.0 * dqss + hhss - 2.0 * ggss) * bqs / 3
                - cqs * (cqs / rfact)
                - (dq / rfact) * aqs * aqs
            )
            rmax = oqs_solve_cubic_analytic_depressed(g, h)
            if math.isnan(rmax) or math.isinf(rmax):
                rmax = oqs_solve_cubic_analytic_depressed_handle_inf(g, h)
            rmax *= rfact

    x = rmax
    xsq = x * x
    xxx = x * xsq
    gx = g * x
    f = x * (xsq + g) + h
    if abs(xxx) > abs(gx):
        maxtt = abs(xxx)
    else:
        maxtt = abs(gx)
    if abs(h) > maxtt:
        maxtt = abs(h)

    if abs(f) > macheps * maxtt:
        for iter in range(8):
            df = 3.0 * xsq + g
            if df == 0:
                break
            xold = x
            x += -f / df
            fold = f
            xsq = x * x
            f = x * (xsq + g) + h
            if f == 0:
                break

            if abs(f) >= abs(fold):
                x = xold
                break
    phi0 = x
    return phi0


@jit(nopython=True, cache=const.use_numba_cache)
def oqs_calc_err_ldlt(b, c, d, d2, l1, l2, l3):
    if b == 0:
        sum = abs(d2 + l1 * l1 + 2.0 * l3)
    else:
        sum = abs(((d2 + l1 * l1 + 2.0 * l3) - b) / b)
    if c == 0:
        sum += abs(2.0 * d2 * l2 + 2.0 * l1 * l3)
    else:
        sum += abs(((2.0 * d2 * l2 + 2.0 * l1 * l3) - c) / c)
    if d == 0:
        sum += abs(d2 * l2 * l2 + l3 * l3)
    else:
        sum += abs(((d2 * l2 * l2 + l3 * l3) - d) / d)
    return sum


@jit(nopython=True, cache=const.use_numba_cache)
def oqs_calc_err_abcd_cmplx(a, b, c, d, aq, bq, cq, dq):
    if d == 0:
        sum = abs(bq * dq)
    else:
        sum = abs((bq * dq - d) / d)
    if c == 0:
        sum += abs(bq * cq + aq * dq)
    else:
        sum += abs(((bq * cq + aq * dq) - c) / c)
    if b == 0:
        sum += abs(bq + aq * cq + dq)
    else:
        sum += abs(((bq + aq * cq + dq) - b) / b)
    if a == 0:
        sum += abs(aq + cq)
    else:
        sum += abs(((aq + cq) - a) / a)
    return sum


@jit(nopython=True, cache=const.use_numba_cache)
def oqs_calc_err_abcd(a, b, c, d, aq, bq, cq, dq):
    if d == 0:
        sum = abs(bq * dq)
    else:
        sum = abs((bq * dq - d) / d)
    if c == 0:
        sum += abs(bq * cq + aq * dq)
    else:
        sum += abs(((bq * cq + aq * dq) - c) / c)
    if b == 0:
        sum += abs(bq + aq * cq + dq)
    else:
        sum += abs(((bq + aq * cq + dq) - b) / b)
    if a == 0:
        sum += abs(aq + cq)
    else:
        sum += abs(((aq + cq) - a) / a)
    return sum


@jit(nopython=True, cache=const.use_numba_cache)
def oqs_calc_err_abc(a, b, c, aq, bq, cq, dq):
    if c == 0:
        sum = abs(bq * cq + aq * dq)
    else:
        sum = abs(((bq * cq + aq * dq) - c) / c)
    if b == 0:
        sum += abs(bq + aq * cq + dq)
    else:
        sum += abs(((bq + aq * cq + dq) - b) / b)
    if a == 0:
        sum += abs(aq + cq)
    else:
        sum += abs(((aq + cq) - a) / a)
    return sum


@jit(nopython=True, cache=const.use_numba_cache)
def oqs_NRabcd(a, b, c, d, AQ, BQ, CQ, DQ):
    x0, x1, x2, x3 = AQ, BQ, CQ, DQ

    fvec0 = x1 * x3 - d
    fvec1 = x1 * x2 + x0 * x3 - c
    fvec2 = x1 + x0 * x2 + x3 - b
    fvec3 = x0 + x2 - a

    if d == 0:
        errf = abs(fvec0)
    else:
        errf = abs(fvec0 / d)
    if c == 0:
        errf += abs(fvec1)
    else:
        errf += abs(fvec1 / c)
    if b == 0:
        errf += abs(fvec2)
    else:
        errf += abs(fvec2 / b)
    if a == 0:
        errf += abs(fvec3)
    else:
        errf += abs(fvec3 / a)

    for iter in range(8):
        x02 = x0 - x2
        det = x1 * x1 + x1 * (-x2 * x02 - 2.0 * x3) + x3 * (x0 * x02 + x3)
        if det == 0.0:
            break

        J00 = x02
        J01 = x3 - x1
        J02 = x1 * x2 - x0 * x3
        J03 = -x1 * J01 - x0 * J02
        J10 = x0 * J00 + J01
        J11 = -x1 * J00
        J12 = -x1 * J01
        J13 = -x1 * J02
        J20 = -J00
        J21 = -J01
        J22 = -J02
        J23 = J02 * x2 + J01 * x3
        J30 = -x2 * J00 - J01
        J31 = J00 * x3
        J32 = x3 * J01
        J33 = x3 * J02

        dx0 = J00 * fvec0 + J01 * fvec1 + J02 * fvec2 + J03 * fvec3
        dx1 = J10 * fvec0 + J11 * fvec1 + J12 * fvec2 + J13 * fvec3
        dx2 = J20 * fvec0 + J21 * fvec1 + J22 * fvec2 + J23 * fvec3
        dx3 = J30 * fvec0 + J31 * fvec1 + J32 * fvec2 + J33 * fvec3

        xold0, xold1, xold2, xold3 = x0, x1, x2, x3

        x0 += -dx0 / det
        x1 += -dx1 / det
        x2 += -dx2 / det
        x3 += -dx3 / det

        fvec0 = x1 * x3 - d
        fvec1 = x1 * x2 + x0 * x3 - c
        fvec2 = x1 + x0 * x2 + x3 - b
        fvec3 = x0 + x2 - a

        errfold = errf
        if d == 0:
            errf = abs(fvec0)
        else:
            errf = abs(fvec0 / d)
        if c == 0:
            errf += abs(fvec1)
        else:
            errf += abs(fvec1 / c)
        if b == 0:
            errf += abs(fvec2)
        else:
            errf += abs(fvec2 / b)
        if a == 0:
            errf += abs(fvec3)
        else:
            errf += abs(fvec3 / a)

        if errf == 0:
            break
        if errf >= errfold:
            x0, x1, x2, x3 = xold0, xold1, xold2, xold3
            break

    return x0, x1, x2, x3


@jit(nopython=True, cache=const.use_numba_cache)
def oqs_solve_quadratic(a, b):
    diskr = a * a - 4 * b
    if diskr >= 0.0:
        if a >= 0.0:
            div = -a - math.sqrt(diskr)
        else:
            div = -a + math.sqrt(diskr)

        zmax = div / 2

        if zmax == 0.0:
            zmin = 0.0
        else:
            zmin = b / zmax

        root0 = zmax + 0.0j
        root1 = zmin + 0.0j
    else:
        sqrtd = math.sqrt(-diskr)
        root0 = -a / 2 + sqrtd / 2 * 1j
        root1 = -a / 2 - sqrtd / 2 * 1j
    return (root0, root1)


@jit(nopython=True, cache=const.use_numba_cache)
def solve_many(ps: NDArray[np.float64]) -> NDArray[np.complex128]:
    num_eqn = ps.shape[0]
    roots = np.zeros((num_eqn, 4), dtype=np.complex128)

    for i in range(num_eqn):
        p = ps[i, :]
        roots[i, :] = solve(p[0], p[1], p[2], p[3], p[4])

    return roots


@jit(nopython=True, cache=const.use_numba_cache)
def solve(a: float, b: float, c: float, d: float, e: float) -> NDArray[np.complex128]:
    """Solve quartic equation.

    Args:
        coeff: Array [a, b, c, d, e] representing at^4 + bt^3 + ct^2 + dt + e = 0

    Returns:
        Array of 4 complex roots
    """
    roots = np.zeros(4, dtype=np.complex128)

    if a == 0.0:
        return roots

    a_p = b / a
    b_p = c / a
    c_p = d / a
    d_p = e / a
    phi0 = oqs_calc_phi0(a_p, b_p, c_p, d_p, 0)

    rfact = 1.0
    if math.isnan(phi0) or math.isinf(phi0):
        rfact = quart_rescal_fact
        a_p /= rfact
        rfactsq = rfact * rfact
        b_p /= rfactsq
        c_p /= rfactsq * rfact
        d_p /= rfactsq * rfactsq
        phi0 = oqs_calc_phi0(a_p, b_p, c_p, d_p, 1)

    l1 = a_p / 2
    l3 = b_p / 6 + phi0 / 2
    del2 = c_p - a_p * l3
    nsol = 0
    bl311 = 2.0 * b_p / 3.0 - phi0 - l1 * l1
    dml3l3 = d_p - l3 * l3

    d2m_0, d2m_1, d2m_2 = 0.0, 0.0, 0.0
    l2m_0, l2m_1, l2m_2 = 0.0, 0.0, 0.0
    res_0, res_1, res_2 = 0.0, 0.0, 0.0

    if bl311 != 0.0:
        d2m_0 = bl311
        l2m_0 = del2 / (2.0 * d2m_0)
        res_0 = oqs_calc_err_ldlt(b_p, c_p, d_p, d2m_0, l1, l2m_0, l3)
        nsol = 1
    if del2 != 0:
        if nsol == 0:
            l2m_0 = 2 * dml3l3 / del2
            if l2m_0 != 0:
                d2m_0 = del2 / (2 * l2m_0)
                res_0 = oqs_calc_err_ldlt(b_p, c_p, d_p, d2m_0, l1, l2m_0, l3)
                nsol = 1
        elif nsol == 1:
            l2m_1 = 2 * dml3l3 / del2
            if l2m_1 != 0:
                d2m_1 = del2 / (2 * l2m_1)
                res_1 = oqs_calc_err_ldlt(b_p, c_p, d_p, d2m_1, l1, l2m_1, l3)
                nsol = 2

        if nsol == 1:
            d2m_1 = bl311
            l2m_1 = 2.0 * dml3l3 / del2
            res_1 = oqs_calc_err_ldlt(b_p, c_p, d_p, d2m_1, l1, l2m_1, l3)
            nsol = 2
        elif nsol == 2:
            d2m_2 = bl311
            l2m_2 = 2.0 * dml3l3 / del2
            res_2 = oqs_calc_err_ldlt(b_p, c_p, d_p, d2m_2, l1, l2m_2, l3)
            nsol = 3

    if nsol == 0:
        l2 = 0.0
        d2 = 0.0
    elif nsol == 1:
        d2 = d2m_0
        l2 = l2m_0
    elif nsol == 2:
        if res_0 <= res_1:
            d2 = d2m_0
            l2 = l2m_0
        else:
            d2 = d2m_1
            l2 = l2m_1
    else:
        if res_0 <= res_1 and res_0 <= res_2:
            d2 = d2m_0
            l2 = l2m_0
        elif res_1 <= res_2:
            d2 = d2m_1
            l2 = l2m_1
        else:
            d2 = d2m_2
            l2 = l2m_2

    whichcase = 0
    realcase_0 = -1
    realcase_1 = -1
    aq = 0.0
    bq = 0.0
    cq = 0.0
    dq = 0.0
    aq1 = 0.0
    bq1 = 0.0
    cq1 = 0.0
    dq1 = 0.0
    acx = 0.0 + 0.0j
    bcx = 0.0 + 0.0j
    ccx = 0.0 + 0.0j
    dcx = 0.0 + 0.0j
    acx1 = 0.0 + 0.0j
    bcx1 = 0.0 + 0.0j
    ccx1 = 0.0 + 0.0j
    dcx1 = 0.0 + 0.0j
    err0 = 0.0
    err1 = 0.0

    if d2 < 0.0:
        gamma = math.sqrt(-d2)
        aq = l1 + gamma
        bq = l3 + gamma * l2

        cq = l1 - gamma
        dq = l3 - gamma * l2
        if abs(dq) < abs(bq):
            dq = d_p / bq
        elif abs(dq) > abs(bq):
            bq = d_p / dq
        if abs(aq) < abs(cq):
            aqv_0, aqv_1, aqv_2 = 0.0, 0.0, 0.0
            errv_0, errv_1, errv_2 = 0.0, 0.0, 0.0
            nsol = 0
            if dq != 0:
                aqv_0 = (c_p - bq * cq) / dq
                errv_0 = oqs_calc_err_abc(a_p, b_p, c_p, aqv_0, bq, cq, dq)
                nsol = 1
            if cq != 0:
                if nsol == 0:
                    aqv_0 = (b_p - dq - bq) / cq
                    errv_0 = oqs_calc_err_abc(a_p, b_p, c_p, aqv_0, bq, cq, dq)
                    nsol = 1
                else:
                    aqv_1 = (b_p - dq - bq) / cq
                    errv_1 = oqs_calc_err_abc(a_p, b_p, c_p, aqv_1, bq, cq, dq)
                    nsol = 2
            if nsol == 0:
                aqv_0 = a_p - cq
                errv_0 = oqs_calc_err_abc(a_p, b_p, c_p, aqv_0, bq, cq, dq)
                aq = aqv_0
            elif nsol == 1:
                aqv_1 = a_p - cq
                errv_1 = oqs_calc_err_abc(a_p, b_p, c_p, aqv_1, bq, cq, dq)
                if errv_0 <= errv_1:
                    aq = aqv_0
                else:
                    aq = aqv_1
            else:
                aqv_2 = a_p - cq
                errv_2 = oqs_calc_err_abc(a_p, b_p, c_p, aqv_2, bq, cq, dq)
                if errv_0 <= errv_1 and errv_0 <= errv_2:
                    aq = aqv_0
                elif errv_1 <= errv_2:
                    aq = aqv_1
                else:
                    aq = aqv_2
        else:
            cqv_0, cqv_1, cqv_2 = 0.0, 0.0, 0.0
            errv_0, errv_1, errv_2 = 0.0, 0.0, 0.0
            nsol = 0
            if bq != 0:
                cqv_0 = (c_p - aq * dq) / bq
                errv_0 = oqs_calc_err_abc(a_p, b_p, c_p, aq, bq, cqv_0, dq)
                nsol = 1
            if aq != 0:
                if nsol == 0:
                    cqv_0 = (b_p - bq - dq) / aq
                    errv_0 = oqs_calc_err_abc(a_p, b_p, c_p, aq, bq, cqv_0, dq)
                    nsol = 1
                else:
                    cqv_1 = (b_p - bq - dq) / aq
                    errv_1 = oqs_calc_err_abc(a_p, b_p, c_p, aq, bq, cqv_1, dq)
                    nsol = 2
            if nsol == 0:
                cqv_0 = a_p - aq
                errv_0 = oqs_calc_err_abc(a_p, b_p, c_p, aq, bq, cqv_0, dq)
                cq = cqv_0
            elif nsol == 1:
                cqv_1 = a_p - aq
                errv_1 = oqs_calc_err_abc(a_p, b_p, c_p, aq, bq, cqv_1, dq)
                if errv_0 <= errv_1:
                    cq = cqv_0
                else:
                    cq = cqv_1
            else:
                cqv_2 = a_p - aq
                errv_2 = oqs_calc_err_abc(a_p, b_p, c_p, aq, bq, cqv_2, dq)
                if errv_0 <= errv_1 and errv_0 <= errv_2:
                    cq = cqv_0
                elif errv_1 <= errv_2:
                    cq = cqv_1
                else:
                    cq = cqv_2
        realcase_0 = 1
    elif d2 > 0:
        gamma = math.sqrt(d2)
        acx = complex(l1, gamma)
        bcx = complex(l3, gamma * l2)
        ccx = acx.conjugate()
        dcx = bcx.conjugate()
        realcase_0 = 0
    else:
        realcase_0 = -1

    if realcase_0 == -1 or (
        abs(d2) <= macheps * oqs_max3(abs(2.0 * b_p / 3.0), abs(phi0), l1 * l1)
    ):
        d3 = d_p - l3 * l3
        if realcase_0 == 1:
            err0 = oqs_calc_err_abcd(a_p, b_p, c_p, d_p, aq, bq, cq, dq)
        elif realcase_0 == 0:
            err0 = oqs_calc_err_abcd_cmplx(a_p, b_p, c_p, d_p, acx, bcx, ccx, dcx)
        if d3 <= 0:
            realcase_1 = 1
            aq1 = l1
            bq1 = l3 + math.sqrt(-d3)
            cq1 = l1
            dq1 = l3 - math.sqrt(-d3)
            if abs(dq1) < abs(bq1):
                dq1 = d_p / bq1
            elif abs(dq1) > abs(bq1):
                bq1 = d_p / dq1
            err1 = oqs_calc_err_abcd(a_p, b_p, c_p, d_p, aq1, bq1, cq1, dq1)
        else:
            realcase_1 = 0
            acx1 = complex(l1, 0.0)
            bcx1 = complex(l3, math.sqrt(d3))
            ccx1 = complex(l1, 0.0)
            dcx1 = bcx1.conjugate()
            err1 = oqs_calc_err_abcd_cmplx(a_p, b_p, c_p, d_p, acx1, bcx1, ccx1, dcx1)
        if realcase_0 == -1 or err1 < err0:
            whichcase = 1
            if realcase_1 == 1:
                aq = aq1
                bq = bq1
                cq = cq1
                dq = dq1
            else:
                acx = acx1
                bcx = bcx1
                ccx = ccx1
                dcx = dcx1

    if (whichcase == 0 and realcase_0 == 1) or (whichcase == 1 and realcase_1 == 1):
        aq, bq, cq, dq = oqs_NRabcd(a_p, b_p, c_p, d_p, aq, bq, cq, dq)
        roots[0], roots[1] = oqs_solve_quadratic(aq, bq)
        roots[2], roots[3] = oqs_solve_quadratic(cq, dq)
    else:
        if whichcase == 0:
            cdiskr = acx * acx / 4 - bcx
            zx1 = -acx / 2 + np.sqrt(cdiskr)
            zx2 = -acx / 2 - np.sqrt(cdiskr)
            if abs(zx1) > abs(zx2):
                zxmax = zx1
            else:
                zxmax = zx2
            zxmin = bcx / zxmax
            roots[0] = zxmin
            roots[1] = zxmin.conjugate()
            roots[2] = zxmax
            roots[3] = zxmax.conjugate()
        else:
            cdiskr = np.sqrt(acx * acx - 4.0 * bcx)
            zx1 = -0.5 * (acx + cdiskr)
            zx2 = -0.5 * (acx - cdiskr)
            if abs(zx1) > abs(zx2):
                zxmax = zx1
            else:
                zxmax = zx2
            zxmin = bcx / zxmax
            roots[0] = zxmax
            roots[1] = zxmin
            cdiskr = np.sqrt(ccx * ccx - 4.0 * dcx)
            zx1 = -0.5 * (ccx + cdiskr)
            zx2 = -0.5 * (ccx - cdiskr)
            if abs(zx1) > abs(zx2):
                zxmax = zx1
            else:
                zxmax = zx2
            zxmin = dcx / zxmax
            roots[2] = zxmax
            roots[3] = zxmin

    if rfact != 1.0:
        for k in range(4):
            roots[k] *= rfact

    return roots
