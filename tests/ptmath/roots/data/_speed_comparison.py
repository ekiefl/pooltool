import subprocess
import time
from pathlib import Path

import numpy as np
from _quartic_ctypes import solve as solve_c
from _quartic_ctypes import solve_many as solve_many_c

from pooltool.ptmath.roots._quartic_numba import solve as solve_numba
from pooltool.ptmath.roots._quartic_numba import solve_many as solve_many_numba


def time_solve_many(
    solve_fn,
    coeffs: np.ndarray,
    n_runs: int = 100,
    warmup: int = 3,
) -> tuple[float, float]:
    for _ in range(warmup):
        solve_fn(coeffs)

    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        solve_fn(coeffs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return np.mean(times), np.std(times)


def time_solve(solve_fn, n_runs: int = 10000, warmup=100) -> tuple[float, float]:
    rng = np.random.default_rng(seed=42)
    for _ in range(warmup):
        coeffs = rng.uniform(-10, 10, size=5)
        a, b, c, d, e = coeffs
        solve_fn(a, b, c, d, e)

    times = []
    for _ in range(n_runs):
        coeffs = rng.uniform(-10, 10, size=5)
        a, b, c, d, e = coeffs

        start = time.perf_counter()
        solve_fn(a, b, c, d, e)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return np.mean(times), np.std(times)


def main():
    sizes = [10, 100, 1000, 10000]
    rng = np.random.default_rng(seed=42)
    for size in sizes:
        coeffs_list = []
        for _ in range(size):
            coeffs = rng.uniform(-10, 10, size=5)
            coeffs[0] = rng.choice([rng.uniform(0.1, 10), rng.uniform(-10, -0.1)])
            coeffs_list.append(coeffs)

        coeffs = np.array(coeffs_list)

        print(f"Batch size: {size} equations")
        c_mean, c_std = time_solve_many(solve_many_c, coeffs)
        print(f"C (ctypes):  {c_mean * 1000:8.4f} ms ± {c_std * 1000:6.4f} ms")
        numba_mean, numba_std = time_solve_many(solve_many_numba, coeffs)
        print(
            f"Numba:       {numba_mean * 1000:8.4f} ms ± {numba_std * 1000:6.4f} ms\n"
        )

    n_polys = 10000
    print(f"Single roots: {n_polys} polynomials")
    c_mean, c_std = time_solve(solve_c, n_polys)
    print(f"C (ctypes):  {c_mean * 1e6:8.4f} μs ± {c_std * 1e6:6.4f} μs")
    numba_mean, numba_std = time_solve(solve_numba, n_polys)
    print(f"Numba:       {numba_mean * 1e6:8.4f} μs ± {numba_std * 1e6:6.4f} μs")

    benchmark_path = Path(__file__).parent / "_1010_source_code" / "benchmark"
    result = subprocess.run([str(benchmark_path)], capture_output=True, text=True)
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
