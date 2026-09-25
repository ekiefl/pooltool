from collections.abc import Callable, Iterator

import pytest
from direct.interval.IntervalGlobal import Parallel, Sequence, Wait, ivalMgr
from panda3d.core import ClockObject

from pooltool.ani.playback import PlaybackState, ShotPlayback

DT = 0.1
DURATION = 1.0


@pytest.fixture
def advance() -> Iterator[Callable[[int], None]]:
    """Advance the interval manager by frames of ``DT`` seconds."""
    clock = ClockObject.get_global_clock()
    mode = clock.get_mode()
    clock.set_mode(ClockObject.M_non_real_time)
    clock.set_dt(DT)

    def _advance(frames: int) -> None:
        for _ in range(frames):
            clock.tick()
            ivalMgr.step()

    yield _advance

    clock.set_mode(mode)


def _playback(loop: bool = False) -> ShotPlayback:
    return ShotPlayback(Sequence(Wait(DURATION)), 0.0, loop)


def _bring_to(
    state: PlaybackState, advance: Callable[[int], None], loop: bool = False
) -> ShotPlayback:
    playback = _playback(loop)
    if state is PlaybackState.STOPPED:
        return playback
    playback.play()
    if state is PlaybackState.PAUSED:
        advance(2)
        playback.pause()
    elif state is PlaybackState.FINISHED:
        advance(20)
    else:
        advance(2)
    assert playback.state is state
    return playback


def test_starts_stopped_at_zero():
    playback = _playback()
    assert playback.state is PlaybackState.STOPPED
    assert playback.t == 0.0
    assert playback.duration == DURATION
    assert not playback.finished


def test_play_advances_and_finishes(advance):
    playback = _playback()
    playback.play()
    assert playback.state is PlaybackState.PLAYING
    advance(5)
    assert playback.t == pytest.approx(0.5)
    advance(10)
    assert playback.finished
    assert playback.state is PlaybackState.FINISHED


def test_looping_playback_never_finishes(advance):
    playback = _playback(loop=True)
    playback.play()
    advance(25)
    assert playback.state is PlaybackState.PLAYING
    assert 0.0 <= playback.t < DURATION


def test_pause_freezes_time_and_resume_continues(advance):
    playback = _playback()
    playback.play()
    advance(3)
    playback.pause()
    t = playback.t
    advance(3)
    assert playback.t == t
    playback.resume()
    advance(2)
    assert playback.t == pytest.approx(t + 2 * DT)


@pytest.mark.parametrize(
    "start, op, expected",
    [
        (PlaybackState.STOPPED, "play", PlaybackState.PLAYING),
        (PlaybackState.PLAYING, "play", PlaybackState.PLAYING),
        (PlaybackState.PAUSED, "play", PlaybackState.PLAYING),
        (PlaybackState.FINISHED, "play", PlaybackState.PLAYING),
        (PlaybackState.STOPPED, "pause", PlaybackState.STOPPED),
        (PlaybackState.PLAYING, "pause", PlaybackState.PAUSED),
        (PlaybackState.PAUSED, "pause", PlaybackState.PAUSED),
        (PlaybackState.FINISHED, "pause", PlaybackState.FINISHED),
        (PlaybackState.STOPPED, "resume", PlaybackState.STOPPED),
        (PlaybackState.PLAYING, "resume", PlaybackState.PLAYING),
        (PlaybackState.PAUSED, "resume", PlaybackState.PLAYING),
        (PlaybackState.FINISHED, "resume", PlaybackState.FINISHED),
        (PlaybackState.STOPPED, "stop", PlaybackState.STOPPED),
        (PlaybackState.PLAYING, "stop", PlaybackState.STOPPED),
        (PlaybackState.PAUSED, "stop", PlaybackState.STOPPED),
        (PlaybackState.FINISHED, "stop", PlaybackState.STOPPED),
        (PlaybackState.STOPPED, "restart", PlaybackState.STOPPED),
        (PlaybackState.PLAYING, "restart", PlaybackState.PLAYING),
        (PlaybackState.PAUSED, "restart", PlaybackState.PAUSED),
        (PlaybackState.FINISHED, "restart", PlaybackState.PLAYING),
        (PlaybackState.STOPPED, "seek", PlaybackState.STOPPED),
        (PlaybackState.PLAYING, "seek", PlaybackState.PLAYING),
        (PlaybackState.PAUSED, "seek", PlaybackState.PAUSED),
        (PlaybackState.FINISHED, "seek", PlaybackState.PAUSED),
        (PlaybackState.STOPPED, "step", PlaybackState.STOPPED),
        (PlaybackState.PLAYING, "step", PlaybackState.PLAYING),
        (PlaybackState.PAUSED, "step", PlaybackState.PAUSED),
        (PlaybackState.FINISHED, "step", PlaybackState.PAUSED),
    ],
)
def test_state_table(advance, start, op, expected):
    playback = _bring_to(start, advance)
    if op == "seek":
        playback.seek(0.5)
    elif op == "step":
        playback.step(-0.3)
    else:
        getattr(playback, op)()
    assert playback.state is expected


@pytest.mark.parametrize(
    "start", [PlaybackState.STOPPED, PlaybackState.PAUSED, PlaybackState.FINISHED]
)
def test_seek_moves_time_when_not_playing(advance, start):
    playback = _bring_to(start, advance)
    playback.seek(0.5)
    assert playback.t == pytest.approx(0.5)
    playback.step(0.2)
    assert playback.t == pytest.approx(0.7)


def test_seek_clamps_to_tree(advance):
    playback = _bring_to(PlaybackState.PAUSED, advance)
    playback.seek(-1.0)
    assert playback.t == 0.0
    playback.seek(5.0)
    assert playback.t == DURATION


def test_step_is_ignored_while_playing(advance):
    playback = _bring_to(PlaybackState.PLAYING, advance)
    t = playback.t
    playback.step(0.5)
    assert playback.t == t


def test_restart_moves_to_start(advance):
    for start in (PlaybackState.PLAYING, PlaybackState.PAUSED, PlaybackState.FINISHED):
        playback = _bring_to(start, advance)
        playback.restart()
        assert playback.t == 0.0


def test_play_from_stopped_starts_at_seeked_time(advance):
    playback = _playback()
    playback.seek(0.5)
    playback.play()
    advance(1)
    assert playback.t == pytest.approx(0.5 + DT)


def test_play_after_finished_starts_over(advance):
    playback = _bring_to(PlaybackState.FINISHED, advance)
    playback.play()
    advance(1)
    assert playback.t == pytest.approx(DT)


def test_changing_loop_while_playing_keeps_time(advance):
    playback = _bring_to(PlaybackState.PLAYING, advance)
    t = playback.t
    playback.loop = True
    assert playback.state is PlaybackState.PLAYING
    assert playback.t == pytest.approx(t)
    advance(20)
    assert playback.state is PlaybackState.PLAYING


def test_destroy_returns_to_stopped(advance):
    playback = _bring_to(PlaybackState.PLAYING, advance)
    playback.destroy()
    assert playback.state is PlaybackState.STOPPED


def test_from_parts_lays_out_stroke_then_balls_then_buffer():
    stroke = Sequence(Wait(0.3))
    balls = Parallel(Sequence(Wait(1.0)), Sequence(Wait(2.0)))
    playback = ShotPlayback.from_parts(stroke, balls, trailing_buffer=0.5, loop=True)
    assert playback.stroke_duration == pytest.approx(0.3)
    assert playback.duration == pytest.approx(0.3 + 2.0 + 0.5)
    assert playback.loop
