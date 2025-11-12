from pathlib import Path

import numpy as np
import typer
from _quartic_ctypes import solve_many


def main(
    n: int = 1000,
    output_file: Path = Path("1010_reference_coeffs.npy"),
):
    rng = np.random.default_rng(seed=137)

    coeffs_list = []
    for _ in range(n):
        coeffs = rng.uniform(-10, 10, size=5)
        coeffs[0] = rng.choice([rng.uniform(0.1, 10), rng.uniform(-10, -0.1)])
        coeffs_list.append(coeffs)

    coeffs = np.array(coeffs_list)
    roots = solve_many(coeffs)

    np.save(output_file, coeffs)
    print(
        f"Generated {n} Algorithm 1010 reference coefficients and saved to {output_file}"
    )

    roots_file = output_file.with_name(output_file.stem + ".roots.npy")
    np.save(roots_file, roots)
    print(f"Saved Algorithm 1010 roots to {roots_file}")


if __name__ == "__main__":
    typer.run(main)
