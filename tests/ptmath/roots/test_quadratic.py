import math

import pytest

from pooltool.ptmath.roots.quadratic import solve


def test_solve_standard_quadratic():
    # x^2 - 5x + 6 = 0
    # Solutions: x = 2 or x = 3
    u1, u2 = solve(1.0, -5.0, 6.0)
    solutions = sorted([u1, u2])
    assert pytest.approx(solutions[0]) == 2.0
    assert pytest.approx(solutions[1]) == 3.0

    # x^2 - x - 2 = 0
    # Solutions: x = 2, x = -1
    u1, u2 = solve(1.0, -1.0, -2.0)
    solutions = sorted([u1, u2])
    assert pytest.approx(solutions[0]) == -1.0
    assert pytest.approx(solutions[1]) == 2.0

    # Perfect square: x^2 - 4x + 4 = 0
    # Single repeated solution: x = 2
    u1, u2 = solve(1.0, -4.0, 4.0)
    solutions = sorted([u1, u2])
    assert pytest.approx(solutions[0]) == 2.0
    assert pytest.approx(solutions[1]) == 2.0

    # Difference of squares: x^2 - 4 = 0
    # Solutions: x = 2, x = -2
    u1, u2 = solve(1.0, 0.0, -4.0)
    solutions = sorted([u1, u2])
    assert pytest.approx(solutions[0], 0.0001) == -2.0
    assert pytest.approx(solutions[1], 0.0001) == 2.0


def test_solve_negative_discriminant():
    # Equation with negative discriminant: x^2 + x + 1 = 0 Solutions are complex, but
    # since we are taking the square root directly, we get nan.

    u1, u2 = solve(1.0, 1.0, 1.0)
    assert math.isnan(u1)
    assert math.isnan(u2)


def test_solve_large_values():
    """Test large coefficients for numerical stability."""

    # Equation: x^2 - 1e7*x + 1 = 0
    # This should give one very large and one very small solution.
    a, b, c = 1.0, -1e7, 1.0
    u1, u2 = solve(a, b, c)
    solutions = sorted([u1, u2])

    # The large root should be close to 1e7, the smaller should be close to 1e-7. The
    # required relative tolerance required to pass this test is pretty large (1e-2).
    assert pytest.approx(solutions[0], rel=1e-2) == 1e-7
    assert pytest.approx(solutions[1], rel=1e-2) == 1e7
