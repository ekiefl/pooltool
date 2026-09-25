"""Playback of a shot's animation.

The animation of a shot is a static Panda3D interval tree built from the ball
histories and the cue stroke. :class:`ShotPlayback` owns that tree and is the only
place that starts, pauses, or seeks it. Everything else asks it for the state.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Mapping

from direct.interval.IntervalGlobal import MetaInterval, Parallel, Sequence, Wait

from pooltool.events.datatypes import Event
from pooltool.utils.strenum import StrEnum, auto


class PlaybackState(StrEnum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    FINISHED = auto()


EventFilter = Callable[[Event], bool]
"""Decides whether a hook fires for an event."""

EventHook = Callable[[Event, int], None]
"""Called with an event and the index of the system it belongs to."""


class ShotPlayback:
    """The interval tree of a shot animation and its playback state.

    ``state`` is the only playback state. A non-looping playback that runs off the end
    of the tree reports ``FINISHED`` the next time its state is read.

    Time is simulation seconds with the cue strike at zero. The stroke, if animated,
    plays in negative time, and ``duration`` runs to the end of the trailing buffer.
    The tree itself runs in seconds of playback, which differ from simulation seconds
    by the playback speed; the conversion never leaves this class.

    Hooks fire from :meth:`tick` for each event whose time is passed while playing.
    Seeking never fires hooks.
    """

    def __init__(
        self,
        tree: Sequence,
        stroke_seconds: float,
        speed: float,
        loop: bool,
        events: Mapping[int, list[Event]],
    ) -> None:
        self._tree = tree
        self._stroke_seconds = stroke_seconds
        self._speed = speed
        self._loop = loop
        self._state = PlaybackState.STOPPED
        self._events = sorted(
            (
                (event.time, event, index)
                for index, evs in events.items()
                for event in evs
            ),
            key=lambda item: item[0],
        )
        self._times = [time for time, _, _ in self._events]
        self._hooks: list[tuple[EventFilter, EventHook]] = []
        self._cursor = 0
        self._last_t = 0.0
        self._mark()

    @classmethod
    def from_parts(
        cls,
        stroke: MetaInterval,
        balls: MetaInterval,
        trailing_buffer: float,
        loop: bool,
        speed: float,
        events: Mapping[int, list[Event]],
    ) -> ShotPlayback:
        """Assemble the root sequence from the stroke and the ball motions.

        The stroke and the balls play together from the root's start, so each ball
        motion is expected to hold its initial state for the stroke's duration.

        Args:
            stroke:
                The cue strokes, in seconds of playback, ending together at the
                strike. May be empty.
            balls:
                The motion of every ball, in seconds of playback.
            trailing_buffer:
                Seconds of playback appended after the balls come to rest.
            loop:
                Whether playback wraps around at the end instead of finishing.
            speed:
                Simulation seconds per second of playback that the ball motions were
                built with.
            events:
                The events of each animated system, keyed by the system's index. Hooks
                fire on these.
        """
        tree = Sequence(Parallel(stroke, balls), Wait(trailing_buffer))
        return cls(tree, stroke.get_duration(), speed, loop, events)

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
            self._start_tree(self._tree.get_t())

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def t(self) -> float:
        """Simulation seconds since the cue strike. Negative during the stroke."""
        return self._to_sim(self._tree.get_t())

    @property
    def start(self) -> float:
        """The time the playback begins at, which is the start of the stroke."""
        return -self._stroke_seconds * self._speed

    @property
    def duration(self) -> float:
        """The time the playback ends at, after the trailing buffer."""
        return self._to_sim(self._tree.get_duration())

    @property
    def finished(self) -> bool:
        return self.state is PlaybackState.FINISHED

    def add_hook(self, when: EventFilter, hook: EventHook) -> None:
        """Call ``hook`` for each event passing ``when`` as playback passes its time."""
        self._hooks.append((when, hook))

    def tick(self) -> None:
        """Fire hooks for the events passed since the last tick. Call once per frame."""
        t = self.t
        if t == self._last_t:
            return
        if t < self._last_t:
            self._cursor = 0
        while self._cursor < len(self._events) and self._times[self._cursor] <= t:
            _, event, index = self._events[self._cursor]
            self._cursor += 1
            for when, hook in self._hooks:
                if when(event):
                    hook(event, index)
        self._last_t = t

    def play(self) -> None:
        """Play from the current time. A finished playback plays again from the start."""
        state = self.state
        if state is PlaybackState.PLAYING:
            return
        if state is PlaybackState.FINISHED:
            self._tree.clearToInitial()
            self._start_tree(0.0)
            return
        self._start_tree(self._tree.get_t())

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
            self._mark()

    def seek(self, t: float) -> None:
        """Move to ``t``, clamped to the playback. A finished playback becomes paused."""
        t = min(max(t, self.start), self.duration)
        if self.state is PlaybackState.FINISHED:
            self._tree.clearToInitial()
            self._state = PlaybackState.PAUSED
        self._tree.set_t(self._to_root(t))
        self._mark()

    def step(self, dt: float) -> None:
        """Move by ``dt`` simulation seconds. Does nothing while playing."""
        if self.state is PlaybackState.PLAYING:
            return
        self.seek(self.t + dt)

    def destroy(self) -> None:
        """Stop and return the animated objects to their initial state."""
        self._tree.pause()
        self._tree.clearToInitial()
        self._state = PlaybackState.STOPPED

    def _to_sim(self, root_t: float) -> float:
        return (root_t - self._stroke_seconds) * self._speed

    def _to_root(self, t: float) -> float:
        return t / self._speed + self._stroke_seconds

    def _mark(self) -> None:
        """Treat every event up to the current time as already passed."""
        self._last_t = self.t
        self._cursor = bisect_right(self._times, self._last_t)

    def _start_tree(self, root_t: float) -> None:
        """Start the tree in the current loop mode, positioned at ``root_t``.

        Panda3D only honors a seek on a paused interval, so the tree is started, paused,
        moved, and resumed.
        """
        if self._loop:
            self._tree.loop()
        else:
            self._tree.start()
        self._tree.pause()
        self._tree.set_t(root_t)
        self._tree.resume()
        self._state = PlaybackState.PLAYING
        self._mark()
