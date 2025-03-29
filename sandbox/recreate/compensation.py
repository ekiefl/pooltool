import numpy as np


def compensate_V0(
    base_V0: float, a: float, b: float, ball_mass: float, cue_mass: float
) -> float:
    """
    Compensate the cue velocity (V0) for off-center hits to maintain consistent ball speed.

    When striking a ball off-center (a,b ≠ 0,0), the outgoing ball velocity decreases.
    This function calculates the adjusted V0 needed to maintain the same outgoing
    ball velocity as a center hit.

    The compensation formula is:
    V0_compensated = base_V0 * (1 + [5/(2(1 + m/M))] * (a² + b²))

    Args:
        base_V0: The cue velocity for center hit (a=0, b=0)
        a: Horizontal offset from ball center (-1 to 1)
        b: Vertical offset from ball center (-1 to 1)

    Returns:
        The compensated V0 value to use for the off-center hit
    """
    distance_squared = a**2 + b**2
    coefficient = 5 / (2 * (1 + ball_mass / cue_mass))
    compensation_factor = 1 + coefficient * distance_squared

    return base_V0 * compensation_factor


def get_base_V0(
    V0: float, a: float, b: float, ball_mass: float, cue_mass: float
) -> float:
    """
    Calculate the base V0 (center hit velocity) given an actual V0 and offset parameters.

    This is the inverse of compensate_V0_for_offset. When we have a known V0 at some
    offset (a,b), this function calculates what the equivalent center hit V0 would be.

    The formula is derived from the compensation formula:
    base_V0 = V0 / (1 + [5/(2(1 + m/M))] * (a² + b²))

    Args:
        V0: The actual cue velocity used with the given offset
        a: Horizontal offset from ball center (-1 to 1)
        b: Vertical offset from ball center (-1 to 1)

    Returns:
        The equivalent base V0 for a center hit (a=0, b=0)
    """
    distance_squared = a**2 + b**2
    coefficient = 5 / (2 * (1 + ball_mass / cue_mass))
    compensation_factor = 1 + coefficient * distance_squared

    return V0 / compensation_factor


def compensate_phi(
    phi_intended: float, a: float, ball_mass: float, end_mass: float
) -> float:
    """
    Calculate the input phi angle needed to achieve a desired outgoing direction when using
    a horizontal offset (a).

    Due to squirt/deflection effects, when using a non-zero 'a' offset, the ball direction
    deviates from the cue direction. This function calculates the adjusted input phi needed
    to achieve the intended outgoing direction.

    The formula is:
    phi_input = phi_intended + 180/π * arctan2((5/2 * a * √(1-a²)), (1 + m_b/m_e + 5/2 * (1-a²)))

    Args:
        phi_intended: The desired outgoing direction angle in degrees
        a: Horizontal offset from ball center (-1 to 1)

    Returns:
        The adjusted input phi angle in degrees
    """
    numerator = 5 / 2 * a * np.sqrt(1 - a**2)
    denominator = 1 + ball_mass / end_mass + 5 / 2 * (1 - a**2)

    squirt_angle = 180 / np.pi * np.arctan2(numerator, denominator)
    phi_input = phi_intended + squirt_angle

    return phi_input % 360


def get_base_phi(
    phi_input: float, a: float, ball_mass: float, end_mass: float
) -> float:
    """
    Calculate the intended outgoing phi angle from an input phi and horizontal offset (a).

    This is the inverse of compensate_phi_for_offset. When we have a known input phi at some
    horizontal offset (a), this function calculates what the resulting outgoing direction will be.

    Args:
        phi_input: The input phi angle in degrees
        a: Horizontal offset from ball center (-1 to 1)

    Returns:
        The resulting outgoing phi angle in degrees
    """
    numerator = 5 / 2 * a * np.sqrt(1 - a**2)
    denominator = 1 + ball_mass / end_mass + 5 / 2 * (1 - a**2)

    squirt_angle = 180 / np.pi * np.arctan2(numerator, denominator)
    phi_intended = phi_input - squirt_angle

    return phi_intended % 360
