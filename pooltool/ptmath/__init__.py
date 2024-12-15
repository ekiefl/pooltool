"""Math functions"""

import pooltool.ptmath.roots as roots
from pooltool.ptmath.utils import (
    angle_between_vectors,
    are_points_on_same_side,
    convert_2D_to_3D,
    coordinate_rotation,
    cross,
    find_intersection_2D,
    is_overlapping,
    norm2d,
    norm3d,
    norm3d_squared,
    point_on_line_closest_to_point,
    projected_angle,
    solve_transcendental,
    unit_vector,
    unit_vector_slow,
    wiggle,
)

__all__ = [
    "roots",
    "projected_angle",
    "angle_between_vectors",
    "coordinate_rotation",
    "cross",
    "norm3d",
    "norm3d_squared",
    "solve_transcendental",
    "convert_2D_to_3D",
    "norm2d",
    "point_on_line_closest_to_point",
    "find_intersection_2D",
    "are_points_on_same_side",
    "unit_vector",
    "unit_vector_slow",
    "wiggle",
    "is_overlapping",
]
