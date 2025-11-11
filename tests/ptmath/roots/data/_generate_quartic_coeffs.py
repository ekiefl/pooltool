from pathlib import Path

import numpy as np
import typer
from mpmath import mp


def generate_diabolical_roots(n: int, rng: np.random.Generator):
    roots_list = []
    case_labels = []

    for _ in range(n):
        case = rng.integers(0, 6)
        case_labels.append(case)

        if case == 0:
            exp1 = rng.uniform(2, 15)
            exp2 = rng.uniform(0, exp1 - 2)
            exp3 = rng.uniform(-2, exp2)
            exp4 = rng.uniform(-4, exp3)
            roots = np.array([10**exp1, 10**exp2, 10**exp3, 10**exp4])
            if rng.random() > 0.5:
                roots *= rng.choice([-1, 1], size=4)

        elif case == 1:
            base = rng.uniform(0.1, 1000)
            spacing = rng.uniform(1e-4, 1e-1) * base
            roots = np.array(
                [base, base + spacing, base + 2 * spacing, base + 3 * spacing]
            )

        elif case == 2:
            exp_large = rng.uniform(10, 50)
            exp_small = rng.uniform(-5, 2)
            r_large = 10**exp_large
            r_small = 10**exp_small
            roots = np.array([r_large, r_large * 0.99, r_small, r_small * 0.5])

        elif case == 3:
            base = rng.uniform(1, 1000)
            roots = np.array([base, base, base * 1.001, base * 0.999])

        elif case == 4:
            base = rng.uniform(100, 10000)
            roots = np.array([base, base, base, base + rng.uniform(1e-10, 1e-4) * base])

        else:
            exp_huge = rng.uniform(30, 100)
            exp_med = rng.uniform(10, 20)
            exp_small = rng.uniform(-5, 5)
            roots = np.array(
                [10**exp_huge, 10**exp_med, 10**exp_small, 10 ** (exp_small - 2)]
            )

        roots_list.append(roots)

    return roots_list, case_labels


def generate_complex_roots(n: int, rng: np.random.Generator):
    roots_list = []

    for i in range(n):
        if i % 2 == 0:
            roots = rng.uniform(0, 10, size=4)
        else:
            real1 = rng.uniform(0, 10)
            real2 = rng.uniform(0, 10)
            imag = rng.uniform(0, 1)
            roots = np.array(
                [
                    complex(real1, imag),
                    complex(real1, -imag),
                    complex(real2, 0),
                    complex(real2, 0),
                ],
                dtype=complex,
            )

        roots_list.append(roots)

    return roots_list


def roots_to_coefficients(roots):
    x1, x2, x3, x4 = roots

    c4 = 1.0
    c3 = -(x1 + x2 + x3 + x4)
    c2 = x1 * x2 + (x1 + x2) * (x3 + x4) + x3 * x4
    c1 = -(x1 * x2 * (x3 + x4) + x3 * x4 * (x1 + x2))
    c0 = x1 * x2 * x3 * x4

    return np.array([c0, c1, c2, c3, c4])


def roots_to_coefficients_exact(roots):
    mp.dps = 100

    x1, x2, x3, x4 = [mp.mpc(r) for r in roots]

    c4 = mp.mpf(1.0)
    c3 = -(x1 + x2 + x3 + x4)
    c2 = x1 * x2 + (x1 + x2) * (x3 + x4) + x3 * x4
    c1 = -(x1 * x2 * (x3 + x4) + x3 * x4 * (x1 + x2))
    c0 = x1 * x2 * x3 * x4

    return np.array(
        [
            complex(c0).real,
            complex(c1).real,
            complex(c2).real,
            complex(c3).real,
            float(c4),
        ]
    )


def main(
    n: int,
    output_file: Path = Path("coefficients.npy"),
    diabolical: bool = False,
):
    rng = np.random.default_rng(seed=42)

    if diabolical:
        roots_list, case_labels = generate_diabolical_roots(n, rng)
        coefficients = np.array(
            [roots_to_coefficients_exact(roots) for roots in roots_list]
        )
        print(
            f"Generated {n} diabolical quartic coefficient arrays and saved to {output_file}"
        )

        case_file = output_file.with_name(output_file.stem + ".cases.npy")
        np.save(case_file, np.array(case_labels))
        print(f"Saved case labels to {case_file}")

        roots_file = output_file.with_name(output_file.stem + ".roots.npy")
        roots_array = np.array(roots_list)
        np.save(roots_file, roots_array)
        print(f"Saved true roots to {roots_file}")
    else:
        roots_list = []
        for _ in range(n):
            roots = rng.uniform(-10, 10, size=4)
            roots_list.append(roots)

        coefficients = np.array(
            [roots_to_coefficients_exact(roots) for roots in roots_list]
        )
        roots_file = output_file.with_name(output_file.stem + ".roots.npy")
        roots_array = np.array(roots_list)
        np.save(roots_file, roots_array)
        print(f"Saved true roots to {roots_file}")

        print(f"Generated {n} quartic coefficient arrays and saved to {output_file}")

    np.save(output_file, coefficients)


if __name__ == "__main__":
    typer.run(main)
