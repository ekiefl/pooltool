from pooltool.ptmath.roots._quartic_numba import solve as solve_numba
from pooltool.ptmath.roots._quartic_numba import solve_many as solve_many_numba

solve = solve_numba
solve_many = solve_many_numba

__all__ = [
    "solve",
    "solve_many",
]
