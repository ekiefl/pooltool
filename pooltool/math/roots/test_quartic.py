import numpy as np
import pytest

import pooltool.math.roots as roots


@pytest.mark.parametrize("solver", [roots.QuarticSolver.OLD, roots.QuarticSolver.NEW])
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
