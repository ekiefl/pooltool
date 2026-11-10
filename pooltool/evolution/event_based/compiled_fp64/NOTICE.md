# Numerical source notices

The compiled FP64 implementation adapts Pooltool's Apache-2.0 event detector,
event loop, and selected stock 2D resolvers for array-based execution. See
the distribution's LICENSE.txt. The prediction and resolution modules reuse
Pooltool's numeric primitives. The contact module adapts the planar cushion
positioning and Stronge impulse code from Pooltool's
`physics/resolve/ball_cushion` and `physics/resolve/stronge_compliant.py`.

The scalar root iteration in `contact.py` adapts the k=1 TOMS748 implementation
in SciPy 1.18.1, `scipy/optimize/_zeros_py.py`. It replaces callable residuals
with fixed numeric arguments for the two Stronge equations. The SciPy BSD
3-Clause license and copyright notice are reproduced in SCIPY-LICENSE.txt.
