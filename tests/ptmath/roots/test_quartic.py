import numpy as np
import pytest

from pooltool.ptmath.roots import quartic


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_case1(solver: quartic.QuarticSolver):
    coeffs = (
        0.9604000000000001,
        -22.342459712735774,
        131.1430067191817,
        -13.968966072700297,
        0.37215503307938314,
    )

    expected = 0.048943195217641386
    coeffs_array = np.array(coeffs)[np.newaxis, :]
    assert quartic.solve_quartics(coeffs_array, solver)[0] == pytest.approx(
        expected, rel=1e-4
    )


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_quadratic(solver: quartic.QuarticSolver):
    """This test surfaces the fact that quartic solver can't handle quadratic equations :("""
    coeffs_array = np.array((0, 0, 1, 1, 1), dtype=np.float64)[np.newaxis, :]

    with pytest.raises(NotImplementedError):
        quartic.solve_quartics(coeffs_array, solver)


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_cubic(solver: quartic.QuarticSolver):
    """This test surfaces the fact that quartic solver can't handle cubic equations :("""
    coeffs_array = np.array((0, 1, 1, 1, 1), dtype=np.float64)[np.newaxis, :]

    with pytest.raises(NotImplementedError):
        quartic.solve_quartics(coeffs_array, solver)


def test_e_equals_0():
    coeffs = (
        0.9604000000000001,
        -22.342459712735774,
        131.1430067191817,
        -13.968966072700297,
        0,
    )

    expected = np.zeros(4, dtype=np.complex128)
    assert (expected == quartic.solve(*coeffs)).all()
