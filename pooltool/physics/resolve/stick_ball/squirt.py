import numpy as np


def get_squirt_angle(m_b: float, m_e: float, a: float, throttle: float) -> float:
    """Calculate the squirt angle

    Derivation here: https://billiards.colostate.edu/technical_proofs/new/TP_A-31.pdf

    Notational discrepenacy: in pooltool, `a` (normalized by `R`) controls sidespin
    (negative is right-spin, positive is left spin), whereas `b` controls top spin
    (positive) and back spin (negative). In the derivation above, `b` (unnormalized) is
    used to describe the amount of sidespin applied. In this function, the pooltool
    notation is used.

    Args:
        *args:
            See https://billiards.colostate.edu/technical_proofs/new/TP_A-31.pdf.
        throttle:
            Scale the calculated squirt by this factor. Set to 0.0 to turn off squirt.

    Returns:
        float:
            The amount of squirt deflection in radians. Negative deflection is to the
            right and positive deflection is to the left.
    """
    m_r = m_b / m_e

    A = 1 - a**2

    numerator = 5 / 2 * a * np.sqrt(A)
    denominator = 1 + m_r + 5 / 2 * A

    return -throttle * np.arctan2(numerator, denominator)
