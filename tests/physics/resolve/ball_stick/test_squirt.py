import attrs
import numpy as np

from pooltool.objects.ball.params import BallParams
from pooltool.objects.cue.datatypes import CueSpecs
from pooltool.physics.resolve.stick_ball.squirt import get_squirt_angle


def test_get_squirt_angle():
    # Define ball and cue such that the m_r is 20
    ball_params = BallParams.default()
    cue_specs = attrs.evolve(CueSpecs.default(), end_mass=ball_params.m / 20)

    expected = 1.1993583313332898 * np.pi / 180

    # Left spin yields negative dphi
    answer = get_squirt_angle(ball_params.m, cue_specs.end_mass, 0.2, throttle=1.0)
    assert np.isclose(answer, -expected)

    # Right spin yields positive dphi
    answer = get_squirt_angle(ball_params.m, cue_specs.end_mass, -0.2, throttle=1.0)
    assert np.isclose(answer, expected)

    # Throttle halves the dphi
    answer = get_squirt_angle(ball_params.m, cue_specs.end_mass, -0.2, throttle=0.5)
    assert np.isclose(answer, expected / 2)
