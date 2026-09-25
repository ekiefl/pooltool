import numpy as np
import pytest

from pooltool.error import StrokeError
from pooltool.objects.cue.render import StrokeRecording

POSITIONS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.15, 0.1, 0.05, 0.0, -0.02]


def _recording(seconds: float = 0.6) -> StrokeRecording:
    return StrokeRecording(POSITIONS, list(np.linspace(0, seconds, len(POSITIONS))))


def test_key_times_are_the_backswing_start_apex_and_strike():
    stroke = _recording()
    backstroke, apex, strike = stroke.key_times()
    assert backstroke == 0.0
    assert apex == stroke.times[4]
    assert strike == stroke.times[-1]


def test_empty_recording_has_zero_key_times_and_is_not_a_shot():
    stroke = StrokeRecording()
    assert stroke.key_times() == (0.0, 0.0, 0.0)
    assert not stroke.is_shot()


def test_is_shot_needs_a_backswing_of_at_least_a_few_tenths_of_a_second():
    assert _recording(0.6).is_shot()
    assert not _recording(0.2).is_shot()
    assert not StrokeRecording([-0.01] * 10, list(np.linspace(0, 1, 10))).is_shot()


def test_V0_averages_the_speed_over_the_window_before_the_strike():
    stroke = _recording()
    assert stroke.V0() == pytest.approx(0.05 / 0.1)


def test_V0_refuses_a_strike_right_after_the_apex():
    with pytest.raises(StrokeError, match="edge case"):
        _recording(0.1).V0()


def test_trimmed_keeps_the_seconds_before_the_strike():
    stroke = _recording(2.0)
    trimmed = stroke.trimmed(1.0)
    assert trimmed.times[0] == pytest.approx(1.0, abs=0.15)
    assert trimmed.times[-1] == stroke.times[-1]
    assert len(trimmed.positions) == len(trimmed.times)


def test_trimmed_returns_a_short_recording_untouched():
    stroke = _recording(0.6)
    assert stroke.trimmed(1.0) is stroke
