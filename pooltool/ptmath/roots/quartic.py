from pooltool.ptmath.roots._quartic_numba import solve as _solve_numba
from pooltool.ptmath.roots._quartic_numba import solve_many as _solve_many_numba

solve_many = _solve_many_numba
solve = _solve_numba
