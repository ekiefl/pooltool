# Quartic root test data

This directory contains ground truth datasets and reference implementations for testing quartic equation solvers.

## Data files

### Standard test cases

- **`quartic_coeffs.npy`** - 1000 quartic polynomial coefficients with uniformly distributed roots
- **`quartic_coeffs.roots.npy`** - Ground truth roots (computed with mpmath at 100 decimal places)

### Pathological test cases

- **`hard_quartic_coeffs.npy`** - 1000 numerically challenging quartic coefficients
- **`hard_quartic_coeffs.roots.npy`** - Ground truth roots for pathological cases
- **`hard_quartic_coeffs.cases.npy`** - Case labels (0-5) indicating which pathological scenario:
  - Case 0: Widely separated roots
  - Case 1: Closely spaced roots
  - Case 2: Mixed scales with clusters
  - Case 3: Near-repeated roots
  - Case 4: Triple root plus small perturbation
  - Case 5: Extreme scale separation

### Algorithm 1010 reference

- **`1010_reference_coeffs.npy`** - 1000 quartic coefficients for verification against the source code implementation of Algorithm 1010
- **`1010_reference_coeffs.roots.npy`** - Roots computed by the reference implementation

## Regenerating data

From this directory, run:

```bash
# Standard test cases
python _generate_quartic_coeffs.py 1000 --output-file quartic_coeffs.npy

# Pathological test cases
python _generate_quartic_coeffs.py 1000 --output-file hard_quartic_coeffs.npy --diabolical

# Algorithm 1010 reference (requires compiled C library, see below)
python _generate_c_reference.py --n 1000 --output-file 1010_reference_coeffs.npy
```

Seeds are fixed for reproducibility.

## Algorithm 1010 C implementation

`_1010_source_code/` contains the reference C implementation supplied in the publication "*Algorithm 1010: Boosting Efficiency in Solving Quartic Equations with No Compromise in Accuracy*". The `Makefile` has been modified, but all other code has been left untouched.

### Compiling

From this directory:

```bash
cd _1010_source_code
make
```

This builds `libquartic.so` using the provided Makefile.

To clean build artifacts:

```bash
make clean
```

### Using via ctypes

The **`_quartic_ctypes.py`** wrapper provides Python access:

```python
from _quartic_ctypes import solve, solve_many
import numpy as np

# Single equation: at^4 + bt^3 + ct^2 + dt + e = 0
roots = solve(a=1, b=-10, c=35, d=-50, e=24)

# Batch solving
coeffs = np.array([[1, -10, 35, -50, 24]], dtype=np.float64)
roots = solve_many(coeffs)
```

## Speed Comparison

Run the benchmark:

```bash
python _speed_test.py
```

This compares the C implementation (via ctypes) against the production numba implementation across different batch sizes. 
