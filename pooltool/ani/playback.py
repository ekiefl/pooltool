"""Playback of a shot's animation.

The animation of a shot is a static Panda3D interval tree built from the ball
histories and the cue stroke. :class:`ShotPlayback` owns that tree and is the only
place that starts, pauses, or seeks it. Everything else asks it for the state.
"""

from __future__ import annotations

from direct.interval.IntervalGlobal import Func, MetaInterval, Parallel, Sequence, Wait

from pooltool.utils.strenum import StrEnum, auto


class PlaybackState(StrEnum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    FINISHED = auto()


def _reset_to_start(interval: MetaInterval) -> Func:
    """An instant interval that returns ``interval`` to its start when passed"""

    def reset() -> None:
        interval.clearToInitial()
        interval.set_t(0)

    return Func(reset)


class ShotPlayback:
    """The interval tree of a shot animation and its playback state.

    ``state`` is the only playback state. A non-looping playback that runs off the end
    of the tree reports ``FINISHED`` the next time its state is read.

    Time is measured in seconds into the root sequence. The stroke, if animated, plays
    first, so the balls start moving at ``stroke_duration``.
    """

    def __init__(self, tree: Sequence, stroke_duration: float, loop: bool) -> None:
        self._tree = tree
        self._stroke_duration = stroke_duration
        self._loop = loop
        self._state = PlaybackState.STOPPED

    @classmethod
    def from_parts(
        cls, stroke: Sequence, balls: Parallel, trailing_buffer: float, loop: bool
    ) -> ShotPlayback:
        """Assemble the root sequence from the stroke and the ball motions.

        The ball motions are reset to their start each time the root passes zero, so a
        looping playback shows the balls at rest while the stroke replays.

        Args:
            stroke:
                The cue stroke. May be empty, in which case the balls start at zero.
            balls:
                The motion of every ball, played together after the stroke.
            trailing_buffer:
                Seconds of downtime appended after the balls come to rest.
            loop:
                Whether playback wraps around at the end instead of finishing.
        """
        tree = Sequence(
            _reset_to_start(balls),
            stroke,
            balls,
            Wait(trailing_buffer),
        )
        return cls(tree, stroke.get_duration(), loop)

    @property
    def state(self) -> PlaybackState:
        if self._state is PlaybackState.PLAYING and not self._tree.isPlaying():
            self._state = PlaybackState.FINISHED
        return self._state

    @property
    def loop(self) -> bool:
        return self._loop

    @loop.setter
    def loop(self, value: bool) -> None:
        if value == self._loop:
            return
        self._loop = value
        if self.state is PlaybackState.PLAYING:
            self._start_tree(self.t)

    @property
    def t(self) -> float:
        """Seconds into the root sequence"""
        return self._tree.get_t()

    @property
    def duration(self) -> float:
        return self._tree.get_duration()

    @property
    def stroke_duration(self) -> float:
        return self._stroke_duration

    @property
    def finished(self) -> bool:
        return self.state is PlaybackState.FINISHED

    def play(self) -> None:
        """Play from the current time. A finished playback plays again from the start."""
        state = self.state
        if state is PlaybackState.PLAYING:
            return
        if state is PlaybackState.FINISHED:
            self._tree.clearToInitial()
            self._start_tree(0.0)
            return
        self._start_tree(self.t)

    def pause(self) -> None:
        if self.state is PlaybackState.PLAYING:
            self._tree.pause()
            self._state = PlaybackState.PAUSED

    def resume(self) -> None:
        if self.state is PlaybackState.PAUSED:
            self.play()

    def stop(self) -> None:
        """Stop without moving the animation."""
        if self.state is PlaybackState.STOPPED:
            return
        self._tree.pause()
        self._state = PlaybackState.STOPPED

    def restart(self) -> None:
        """Move to the start, playing again if finished."""
        if self.state is PlaybackState.FINISHED:
            self._tree.clearToInitial()
            self._start_tree(0.0)
        else:
            self._tree.set_t(0.0)

    def seek(self, t: float) -> None:
        """Move to ``t`` seconds, clamped to the tree. A finished playback becomes paused."""
        t = min(max(t, 0.0), self.duration)
        if self.state is PlaybackState.FINISHED:
            self._tree.clearToInitial()
            self._state = PlaybackState.PAUSED
        self._tree.set_t(t)

    def step(self, dt: float) -> None:
        """Move by ``dt`` seconds. Does nothing while playing."""
        if self.state is PlaybackState.PLAYING:
            return
        self.seek(self.t + dt)

    def destroy(self) -> None:
        """Stop and return the animated objects to their initial state."""
        self._tree.pause()
        self._tree.clearToInitial()
        self._state = PlaybackState.STOPPED

    def _start_tree(self, t: float) -> None:
        """Start the tree in the current loop mode, positioned at ``t``.

        Panda3D only honors a seek on a paused interval, so the tree is started, paused,
        moved, and resumed.
        """
        if self._loop:
            self._tree.loop()
        else:
            self._tree.start()
        self._tree.pause()
        self._tree.set_t(t)
        self._tree.resume()
        self._state = PlaybackState.PLAYING
