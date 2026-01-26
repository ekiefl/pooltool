import matplotlib.pyplot as plt
import numpy as np
import scipy as sp

from pooltool.physics.resolve.stronge_compliant import (
    collision_duration,
    compression_duration,
    f_per_m_n,
    f_per_m_t_intermediate_angle_of_incidence,
    f_per_m_t_stick,
    frequency_n,
    frequency_t,
    slip_time_for_initial_stick,
    slip_time_for_stick,
    stick_time_for_initial_slip,
    u_t_dot_initial_slip,
    u_t_initial_slip,
    v_t_initial_slip,
    v_t_stick,
)

v_n_0 = -3.0
beta_t = 3.5
beta_n = 1.0
beta_t_by_beta_n = beta_t / beta_n
mu = 0.2
e_n = 0.85
k_n = 1
eta_squared = beta_t_by_beta_n / 1.7**2
m = 0.170097

omega_n = frequency_n(beta_n, k_n, m)
omega_t = frequency_t(omega_n, beta_t_by_beta_n, eta_squared)
t_c = compression_duration(omega_n)
t_f = collision_duration(t_c, e_n)

print(f"omega_t / omega_n = {omega_t / omega_n}")


def initial_stick(interp):
    v_t_0 = v_n_0 * mu * sp.interpolate.interp1d([0, 1], [0, eta_squared])(interp)
    v_t_0_by_v_n_0 = v_t_0 / v_n_0

    t_slip = slip_time_for_initial_stick(
        v_t_0_by_v_n_0, omega_t, omega_n, mu, e_n, eta_squared, t_c, t_f
    )

    print(f"t_slip / t_c = {t_slip / t_c}")

    ts = np.linspace(0, t_f, 100)
    force_factor = beta_n / (omega_n * -v_n_0)
    f_per_m_ns = np.array(
        [f_per_m_n(t, t_c, v_n_0, beta_n, omega_n, e_n) * force_factor for t in ts]
    )
    f_per_m_t_sticks = np.array(
        [
            f_per_m_t_stick(t, beta_t, omega_t, v_t_0, 0, 0) * force_factor / mu
            for t in ts
        ]
    )

    fig = plt.figure(1)
    ax = fig.add_subplot()
    ax.set(xlabel="non-dimensional time", ylabel="non-dimensional force")
    ax.plot(ts / t_c, f_per_m_ns, label="f_per_m_n")
    ax.plot(ts / t_c, -f_per_m_ns, label="-f_per_m_n", linestyle="dashed")
    ax.plot(ts / t_c, f_per_m_t_sticks, label="f_per_m_t_sticks")
    ax.grid()
    ax.legend()
    plt.show()


def initial_slip(interp):
    print(f"interp={interp}")

    assert v_n_0 < 0
    v_t_0 = (
        v_n_0
        * mu
        * sp.interpolate.interp1d(
            [0, 1], [eta_squared, (1 + e_n) * beta_t_by_beta_n - eta_squared / e_n]
        )(interp)
    )
    assert v_t_0 < 0

    v_t_0_by_v_n_0 = v_t_0 / v_n_0

    ts = np.linspace(0, t_f, 500)

    print(
        f"calculating stick_time_for_initial_slip(\n"
        f"\tv_t_0_by_v_n_0={v_t_0_by_v_n_0},\n"
        f"\tbeta_t_by_beta_n={beta_t_by_beta_n},\n"
        f"\tmu={mu},\n"
        f"\te_n={e_n},\n"
        f"\teta_squared={eta_squared},\n"
        f"\tt_c={t_c}\n"
        ")"
    )

    t_stick = stick_time_for_initial_slip(
        v_t_0_by_v_n_0, beta_t_by_beta_n, mu, e_n, eta_squared, t_c
    )
    print(f"t_stick / t_c = {t_stick / t_c}")
    u_t_slip_to_stick = u_t_initial_slip(
        t_stick, t_c, v_n_0, mu, eta_squared, omega_n, e_n
    )
    print(f"u_t_slip_to_stick={u_t_slip_to_stick}")
    v_t_slip_to_stick = v_t_initial_slip(
        t_stick, t_c, v_t_0, v_n_0, mu, beta_t_by_beta_n, omega_n, e_n
    )
    print(f"v_t_slip_to_stick={v_t_slip_to_stick}")

    t_slip = slip_time_for_stick(
        v_t_0,
        v_n_0,
        beta_t_by_beta_n,
        omega_t,
        omega_n,
        mu,
        e_n,
        eta_squared,
        t_c,
        t_f,
        t_stick,
        u_t_slip_to_stick,
        v_t_slip_to_stick,
    )
    print(f"t_slip / t_c = {t_slip / t_c}")

    u_t_dot = np.array(
        [
            u_t_dot_initial_slip(t, t_c, v_n_0, mu, eta_squared, omega_n, e_n)
            if t < t_stick
            else -v_t_stick(t, omega_t, v_t_slip_to_stick, u_t_slip_to_stick, t_stick)
            for t in ts
        ]
    )
    v_t = np.array(
        [
            v_t_initial_slip(t, t_c, v_t_0, v_n_0, mu, beta_t_by_beta_n, omega_n, e_n)
            if t < t_stick
            else v_t_stick(t, omega_t, v_t_slip_to_stick, u_t_slip_to_stick, t_stick)
            for t in ts
        ]
    )

    force_factor = beta_n / (omega_n * v_n_0)

    f_per_m_ns = np.array(
        [f_per_m_n(t, t_c, v_n_0, beta_n, omega_n, e_n) * force_factor for t in ts]
    )
    f_per_m_t_sticks = np.array(
        [
            f_per_m_t_stick(
                t, beta_t, omega_t, v_t_slip_to_stick, u_t_slip_to_stick, t_stick
            )
            * force_factor
            / mu
            for t in ts
        ]
    )
    f_per_m_t = np.array(
        [
            f_per_m_t_intermediate_angle_of_incidence(
                t,
                t_c,
                v_n_0,
                beta_t,
                beta_n,
                omega_t,
                omega_n,
                mu,
                e_n,
                v_t_slip_to_stick,
                u_t_slip_to_stick,
                t_stick,
                t_slip,
            )
            * force_factor
            / mu
            for t in ts
        ]
    )

    fig = plt.figure(1)
    ax = fig.add_subplot()
    ax.set(xlabel="non-dimensional time", ylabel="non-dimensional force")
    ax.plot(ts / t_c, f_per_m_ns, label="f_per_m_n")
    ax.plot(ts / t_c, -f_per_m_ns, label="-f_per_m_n", linestyle="dashed")
    ax.plot(ts / t_c, f_per_m_t_sticks, label="f_per_m_t_stick", linestyle="dashed")
    ax.plot(ts / t_c, f_per_m_t, label="f_per_m_t")
    ax.legend()
    ax.grid()

    fig = plt.figure(2)
    ax = fig.add_subplot()
    ax.set(xlabel="non-dimensional time", ylabel="velocity")
    ax.plot(ts / t_c, v_t, label="v_t")
    ax.plot(ts / t_c, -u_t_dot, label="-u_t_dot")
    ax.legend()
    ax.grid()

    plt.show()


if __name__ == "__main__":
    for x in np.linspace(0.01, 0.99, 5):
        initial_stick(x)
    for x in np.linspace(0.01, 0.99, 5):
        initial_slip(x)
