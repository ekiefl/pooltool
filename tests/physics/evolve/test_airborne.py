import numpy as np

from pooltool.physics.evolve import evolve_airborne_state


def test_xy_velocity_conserved():
    """Test that the x- and y-components of the velocity remain unchanged as time evolves."""
    r0 = np.array([0.0, 0.0, 0.0], dtype=np.float64)
    v0 = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    w0 = np.array([0.1, 0.2, 0.3], dtype=np.float64)
    rvw0 = np.array([r0, v0, w0], dtype=np.float64)

    g = 9.81
    t = 1.0

    rvw = evolve_airborne_state(rvw0.copy(), g, t)

    # Check if vx and vy are unchanged
    np.testing.assert_almost_equal(
        rvw[1, 0], v0[0], err_msg="X velocity changed unexpectedly."
    )
    np.testing.assert_almost_equal(
        rvw[1, 1], v0[1], err_msg="Y velocity changed unexpectedly."
    )


def test_angular_velocity_conserved():
    """Test that the angular velocity (w) is conserved and remains unchanged as time evolves."""
    r0 = np.array([0.0, 0.0, 0.0], dtype=np.float64)
    v0 = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    w0 = np.array([0.1, 0.2, 0.3], dtype=np.float64)
    rvw0 = np.array([r0, v0, w0], dtype=np.float64)

    g = 9.81
    t = 2.0

    rvw = evolve_airborne_state(rvw0.copy(), g, t)

    # Check if angular velocity is unchanged
    np.testing.assert_array_almost_equal(
        rvw[2], w0, err_msg="Angular velocity changed unexpectedly."
    )


def test_xy_displacement_linear():
    """Test that the xy-displacement changes linearly with time.

    This assumes there is no air friction.

    Equations:
        r_x(t) = r_x(0) + v_x(0)*t
        r_y(t) = r_y(0) + v_y(0)*t
    """
    r0 = np.array([0.0, 0.0, 10.0], dtype=np.float64)
    v0 = np.array([3.0, 4.0, 5.0], dtype=np.float64)
    w0 = np.array([0.1, 0.2, 0.3], dtype=np.float64)
    rvw0 = np.array([r0, v0, w0], dtype=np.float64)

    g = 9.81

    for t in [0.0, 1.0, 2.0, 3.0]:
        rvw = evolve_airborne_state(rvw0.copy(), g, t)
        expected_x = r0[0] + v0[0] * t
        expected_y = r0[1] + v0[1] * t
        np.testing.assert_almost_equal(
            rvw[0, 0], expected_x, err_msg="X displacement not linear in time."
        )
        np.testing.assert_almost_equal(
            rvw[0, 1], expected_y, err_msg="Y displacement not linear in time."
        )


def test_gravity_direction():
    """Test that gravity affects the motion in the z-direction only.

    Equations:
        v_z(t) = v_z(0) - g*t
        r_z(t) = r_z(0) + v_z(0)*t - (1/2)*g*t^2
    """
    r0 = np.array([0.0, 0.0, 10.0], dtype=np.float64)
    v0 = np.array([3.0, 4.0, 5.0], dtype=np.float64)
    w0 = np.array([0.1, 0.2, 0.3], dtype=np.float64)
    rvw = np.array([r0, v0, w0], dtype=np.float64)

    g = 9.81
    t = 1.0

    rvw_t = evolve_airborne_state(rvw.copy(), g, t)
    expected_z = r0[2] + v0[2] * t - 0.5 * g * t**2
    expected_vz = v0[2] - g * t

    np.testing.assert_almost_equal(
        rvw_t[0, 2],
        expected_z,
        err_msg="Z displacement does not match gravity equation.",
    )
    np.testing.assert_almost_equal(
        rvw_t[1, 2], expected_vz, err_msg="Z velocity does not match gravity equation."
    )


def test_z_displacement_parabolic():
    """Test that z-displacement is parabolic.

    Equations:
        z(t) = z(0) + v_z(0)*t - (g/2)*t^2
    """
    r0 = np.array([0.0, 0.0, 10.0], dtype=np.float64)
    v0 = np.array([3.0, 4.0, 5.0], dtype=np.float64)
    w0 = np.array([0.1, 0.2, 0.3], dtype=np.float64)
    rvw = np.array([r0, v0, w0], dtype=np.float64)

    g = 9.81
    times = np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float64)
    z_values = []

    for t in times:
        rvw_t = evolve_airborne_state(rvw.copy(), g, t)
        z_values.append(rvw_t[0, 2])

    z_values = np.array(z_values)
    # Fit a quadratic to the computed z values
    coeffs = np.polyfit(times, z_values, 2)
    # The true quadratic form is: z(t) = z0 + v0_z t - (g/2)*t^2
    # Coefficients from polyfit are in order: a*t^2 + b*t + c
    # We know a should be -g/2, b should be v0_z, and c should be z0.

    np.testing.assert_almost_equal(
        coeffs[0],
        -g / 2,
        decimal=5,
        err_msg="Quadratic coefficient a does not match -g/2.",
    )
    np.testing.assert_almost_equal(
        coeffs[1],
        v0[2],
        decimal=5,
        err_msg="Quadratic coefficient b does not match initial v_z.",
    )
    np.testing.assert_almost_equal(
        coeffs[2],
        r0[2],
        decimal=5,
        err_msg="Quadratic coefficient c does not match initial z.",
    )
