# Solve Polynomials of up to the fourth degree.
# Algorithms by Ferrari, Tartaglia, Cardano, et al. (16th century Italy)

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const


def analytic(coeffs: NDArray[np.float64]) -> NDArray[np.complex128]:
    ans = solve_poly(coeffs.astype(np.complex128))
    if len(ans) != 4:
        print(ans.shape)
    return ans


def solve_poly(coeffs: NDArray[np.complex128]) -> NDArray[np.complex128]:
    if not len(coeffs):
        return np.empty(0, dtype=np.complex128)

    if coeffs[0] == 0:
        return np.zeros(1, dtype=np.complex128)

    if coeffs[-1] == 0:
        return solve_poly(coeffs[:-1])

    return solve_normalized_poly(coeffs[:-1] / coeffs[-1])


def solve_normalized_poly(coeffs: NDArray[np.complex128]) -> NDArray[np.complex128]:
    degree = len(coeffs)
    shift = -coeffs[-1] / degree

    n = coeffs.shape[0]
    new_coeffs = np.zeros(n + 1, dtype=coeffs.dtype)
    new_coeffs[:n] = coeffs
    new_coeffs[n] = 1.0

    shifted_coeffs = get_shifted_coeffs(shift, new_coeffs)[: degree - 1]
    depressed_solution = solve_depressed_poly(shifted_coeffs)

    return depressed_solution + shift


def get_shifted_coeffs(shift, coeffs: NDArray[np.complex128]) -> NDArray[np.complex128]:
    n = len(coeffs)
    result = np.zeros(n, dtype=np.complex128)

    for j in range(n):
        binomial_seq = get_binomial_sequence(j)
        coeff = coeffs[j]
        x = 1.0
        for i, b in enumerate(binomial_seq):
            result[len(binomial_seq) - 1 - i] += coeff * b * x
            x *= shift

    return result


def get_binomial_sequence(n: int) -> NDArray[np.complex128]:
    seq = np.zeros(n + 1, dtype=np.complex128)
    seq[0] = 1

    for i in range(n):
        seq[i + 1] = 1
        for j in range(i, 0, -1):
            seq[j] += seq[j - 1]

    return seq


def solve_depressed_poly(coeffs: NDArray[np.complex128]) -> NDArray[np.complex128]:
    if not len(coeffs):
        # Poly is: x + 0 = 0
        return np.zeros(1, dtype=np.complex128)
    if coeffs[0] == 0:
        return solve_depressed_poly(coeffs[1:])
    if len(coeffs) == 1:
        # Quadratic
        return sqrts(-coeffs[0])
    if len(coeffs) == 2:
        return solve_depressed_cubic(coeffs[0], coeffs[1])
    if len(coeffs) == 3:
        return solve_depressed_quartic(coeffs[0], coeffs[1], coeffs[2])
    raise ValueError("unsupported polynomial degree")


def solve_depressed_quartic(e, d, c):
    if d == 0:
        tmp = solve_poly(np.array([e, c, 1], dtype=np.complex128))
        soln = np.empty(len(tmp) * 2, dtype=np.complex128)
        i = 0
        for tmp_root in tmp:
            r1, r2 = sqrts(tmp_root)
            soln[i] = r1
            soln[i + 1] = r2
            i += 2
        return soln

    p = (
        solve_poly(np.array([-d * d, c * c - 4 * e, 2 * c, 1], dtype=np.complex128))[0]
        ** 0.5
    )

    return np.concatenate(
        (
            solve_poly(np.array([c + p * p - d / p, 2 * p, 2], dtype=np.complex128)),
            solve_poly(np.array([c + p * p + d / p, -2 * p, 2], dtype=np.complex128)),
        )
    )


def sqrts(x: complex):
    s = x**0.5
    return np.array([-s, s], dtype=np.complex128)


# Based on http://en.wikipedia.org/wiki/Cubic_equation#Cardano.27s_method
def solve_depressed_cubic(q, p):
    third_root_unity = np.exp(np.pi / 3j)

    if p == 0:
        r = -(q ** (1 / 3.0))
    else:
        u = solve_poly(np.array([-p * p * p / 27, q, 1], dtype=np.complex128))[0] ** (
            1 / 3.0
        )
        r = u - p / 3 / u

    return np.array(
        [r, r * third_root_unity, r * third_root_unity**2], dtype=np.complex128
    )


if __name__ == "__main__":
    from pooltool.math.roots import quartic

    coeffs = np.array(
        [
            0.9604000000000001,
            -22.342459712735774,
            131.1430067191817,
            -13.968966072700297,
            0.37215503307938314,
        ]
    )
    coeffs = np.random.rand(5)
    revcoeffs = coeffs[::-1]
    ccoeffs = coeffs.astype(np.complex128)

    quartic.analytic(coeffs)
    quartic.numeric(ccoeffs)
    analytic(revcoeffs)

    # for _ in range(100000):
    #    coeffs = np.random.rand(5)
    #    ans = analytic(coeffs)
