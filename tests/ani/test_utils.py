import numpy as np
import pytest
from panda3d.core import Quat, Vec4

import pooltool.ani.utils as autils


def test_as_quaternion_starts_at_the_identity_and_stays_there_without_spin():
    w = np.zeros((5, 3))
    t = np.arange(5) * 0.1

    quats = autils.as_quaternion(w, t)

    assert quats.shape == (5, 4)
    assert np.array_equal(quats, np.tile([1.0, 0.0, 0.0, 0.0], (5, 1)))


def test_as_quaternion_accumulates_a_constant_spin_about_z():
    rate = np.pi
    w = np.tile([0.0, 0.0, rate], (11, 1))
    t = np.linspace(0.0, 1.0, 11)

    quats = autils.as_quaternion(w, t)

    half_angles = 0.5 * rate * t
    expected = np.column_stack(
        [np.cos(half_angles), np.zeros(11), np.zeros(11), np.sin(half_angles)]
    )
    assert quats == pytest.approx(expected)
    assert np.linalg.norm(quats, axis=1) == pytest.approx(np.ones(11))


def _reference_as_quaternion(w: np.ndarray, t: np.ndarray) -> np.ndarray:
    """The original implementation of ``as_quaternion``, kept here as a reference

    Before the jitted kernel, ``as_quaternion`` built one infinitesimal rotation per
    step as a numpy row, wrapped each row in a Panda3D ``Quat``, and accumulated the
    orientation with Panda3D's ``Quat`` multiplication, one object at a time. This
    reproduces that computation so the kernel can be checked against it.
    """
    w_norm = np.linalg.norm(w, axis=1)
    w_unit = np.divide(
        w, w_norm[:, None], out=np.zeros_like(w), where=w_norm[:, None] != 0
    )

    theta = w_norm[1:] * np.diff(t)
    dQ = np.hstack(
        [np.cos(theta / 2)[:, None], w_unit[1:] * np.sin(theta / 2)[:, None]]
    )
    dQ = np.vstack([np.array([1.0, 0.0, 0.0, 0.0]), dQ])

    dquats = []
    for row in dQ:
        quat = Quat(Vec4(*row))
        quat.normalize()
        dquats.append(quat)

    quats = [dquats[0]]
    for i in range(1, len(dquats)):
        quats.append(quats[i - 1] * dquats[i])

    return np.array([list(quat) for quat in quats])


def test_as_quaternion_matches_the_original_implementation():
    """Prove the jitted kernel is equivalent to the Panda3D ``Quat`` accumulation

    The kernel replaced a per-step loop over Panda3D ``Quat`` objects with an explicit
    Hamilton product. Panda3D's ``Quat`` multiplication applies its operands in the
    opposite order to the textbook product, so this test exists to pin the kernel to
    the original's results, including that operand order, on trajectories with
    arbitrary spin axes, uneven timesteps, and stretches of zero spin.
    """
    rng = np.random.default_rng(7)
    num = 400
    w = rng.normal(scale=30.0, size=(num, 3))
    w[100:150] = 0.0
    t = np.concatenate([[0.0], np.cumsum(rng.uniform(0.005, 0.02, size=num - 1))])

    quats = autils.as_quaternion(w, t)
    reference = _reference_as_quaternion(w, t)

    assert quats == pytest.approx(reference, abs=1e-5)
