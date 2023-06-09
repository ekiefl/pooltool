import numpy as np
import pytest

import pooltool.math.roots as roots


@pytest.mark.parametrize(
    "solver", [roots.QuarticSolver.NUMERIC, roots.QuarticSolver.ANALYTIC]
)
def test_case1(solver: roots.QuarticSolver):
    coeffs = (
        0.9604000000000001,
        -22.342459712735774,
        131.1430067191817,
        -13.968966072700297,
        0.37215503307938314,
    )

    expected = 0.048943195217641386
    coeffs_array = np.array(coeffs)[np.newaxis, :]
    assert roots.min_real_root(coeffs_array, solver)[0] == pytest.approx(
        expected, rel=1e-4
    )


def test_numerical_instability():
    """Counter-example to the practicality of analytic quartic solver"""
    coeffs = (
        0.0012005000000000002,
        -0.007228544950177155,
        0.01421426213999817,
        -0.010034434880693832,
        0.000788027327965124,
    )

    # This shows a bifurcation in the solution, where low digit precision leads to roots
    # determined by quartic_analytic and high digit precision leads to roots determined
    # by roots_numerical. The high digit precision roots are correct
    for n in [25, 30, 35]:
        print(f"{n} digits: {roots.quartic_truth(*coeffs, n)}")

    coeffs_array = np.array(coeffs)[np.newaxis, :]

    print(f"analytic: {roots.quartic_analytic(coeffs_array)}")
    print(f"numeric: {roots.roots_numerical(coeffs_array)}")
