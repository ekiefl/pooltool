import math

import numpy as np
import pytest

from pooltool.ptmath.roots.quadratic import solve


def test_solve_standard_quadratic():
    # x^2 - 5x + 6 = 0
    # Solutions: x = 2, x = 3
    u1, u2 = solve(1.0, -5.0, 6.0)
    solutions = sorted([u1, u2], key=lambda z: (z.real, z.imag))
    # First root -> 2.0 + 0.0j
    assert solutions[0].real == 2.0
    assert solutions[0].imag == 0.0
    # Second root -> 3.0 + 0.0j
    assert solutions[1].real == 3.0
    assert solutions[1].imag == 0.0

    # x^2 - x - 2 = 0
    # Solutions: x = -1, x = 2
    u1, u2 = solve(1.0, -1.0, -2.0)
    solutions = sorted([u1, u2], key=lambda z: (z.real, z.imag))
    # First root -> -1.0 + 0.0j
    assert solutions[0].real == -1.0
    assert solutions[0].imag == 0.0
    # Second root -> 2.0 + 0.0j
    assert solutions[1].real == 2.0
    assert solutions[1].imag == 0.0

    # Perfect square: x^2 - 4x + 4 = 0
    # Single repeated solution: x = 2
    u1, u2 = solve(1.0, -4.0, 4.0)
    solutions = sorted([u1, u2], key=lambda z: (z.real, z.imag))
    # Both roots -> 2.0 + 0.0j
    for root in solutions:
        assert root.real == 2.0
        assert root.imag == 0.0

    # Difference of squares: x^2 - 4 = 0
    # Solutions: x = -2, x = 2
    u1, u2 = solve(1.0, 0.0, -4.0)
    solutions = sorted([u1, u2], key=lambda z: (z.real, z.imag))
    # First root -> -2.0 + 0.0j
    assert solutions[0].real == -2.0
    assert solutions[0].imag == 0.0
    # Second root -> 2.0 + 0.0j
    assert solutions[1].real == 2.0
    assert solutions[1].imag == 0.0

    # Complex roots: x^2 + 1 = 0
    # Solutions: x = i, x = -i
    u1, u2 = solve(1.0, 0.0, 1.0)
    solutions = sorted([u1, u2], key=lambda z: (z.real, z.imag))
    # First root -> -i -> (0.0, -1.0)
    assert solutions[0].real == 0.0
    assert solutions[0].imag == -1.0
    # Second root -> i -> (0.0, 1.0)
    assert solutions[1].real == 0.0
    assert solutions[1].imag == 1.0


def test_solve_large_values():
    """Test large coefficients for numerical stability."""

    # Equation: x^2 - 1e7*x + 1 = 0
    # This should give one very large and one very small solution.
    a, b, c = 1.0, -1e7, 1.0
    u1, u2 = solve(a, b, c)
    solutions = sorted([u1, u2])

    # The large root should be close to 1e7, the smaller should be close to 1e-7. We're
    # able to use a very small relative tolerance due to the way the solver avoids
    # catastrophic cancellation.
    assert pytest.approx(solutions[0].real, rel=1e-12) == 1e-7
    assert pytest.approx(solutions[1].real, rel=1e-12) == 1e7

    assert solutions[0].imag == 0.0
    assert solutions[1].imag == 0.0


def test_solve_linear_equation():
    # a=0, b≠0 => linear equation b*t + c = 0 => t=-c/b
    # e.g. 2t + 4 = 0 => t=-2
    r1, r2 = solve(0.0, 2.0, 4.0)
    assert r1.real == -2.0
    assert r1.imag == 0.0
    assert np.isnan(r2)


def test_solve_degenerate_no_solution():
    # a=0, b=0, c≠0 => no solutions
    # e.g. 0*t^2 + 0*t + 5 = 0 => no real solution
    r1, r2 = solve(0.0, 0.0, 5.0)
    assert np.isnan(r1)
    assert np.isnan(r2)


def test_solve_degenerate_infinite_solutions():
    # a=0, b=0, c=0 => infinite solutions
    # e.g. 0*t^2 + 0*t + 0 = 0 => t can be anything
    r1, r2 = solve(0.0, 0.0, 0.0)
    assert np.isnan(r1)
    assert np.isnan(r2)
