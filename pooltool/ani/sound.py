"""Sound effects for shot playback.

Collision events from a simulated system are turned into a Panda3D interval sequence
that fires a sound at each event's playback time, with volume scaled by how hard the
impact was.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import ClassVar

import numpy as np
from direct.interval.FunctionInterval import FunctionInterval
from direct.interval.IntervalGlobal import Sequence, Wait
from panda3d.core import AudioSound

import pooltool.ptmath as ptmath
from pooltool.ani.constants import sound_dir
from pooltool.ani.globals import Global
from pooltool.config import settings
from pooltool.events.datatypes import Event, EventType
from pooltool.utils import panda_path

FIRE_TOLERANCE: float = 0.15
"""Maximum lag (in animation seconds) between an event's scheduled time and the
animation clock for its sound to fire. Seeking across a sound's scheduled time by more
than this skips the sound rather than playing it late."""

MIN_VOLUME: float = 0.02

PLAY_RATE_JITTER: float = 0.06


class Effect:
    """A pool of identical sounds so overlapping impacts don't cut each other off.

    Panda3D restarts an ``AudioSound`` when ``play`` is called on it while it is
    already playing. A break shot has many collisions within milliseconds of each
    other, so each effect keeps several voices and round-robins through them.
    """

    def __init__(self, name: str, voices: int) -> None:
        path = panda_path(sound_dir / f"{name}.ogg")
        self.voices: list[AudioSound] = [
            Global.loader.loadSfx(path) for _ in range(voices)
        ]
        self._next: int = 0

    def play(self, volume: float, play_rate: float) -> None:
        voice = self.voices[self._next]
        self._next = (self._next + 1) % len(self.voices)
        voice.stop()
        voice.setVolume(volume)
        voice.setPlayRate(play_rate)
        voice.play()


class EffectBank:
    """Lazily loads each effect the first time it is requested."""

    voices: ClassVar[dict[str, int]] = {
        "ballcollision": 8,
        "cushion": 6,
        "pot": 4,
        "cue": 2,
    }

    def __init__(self) -> None:
        self._effects: dict[str, Effect] = {}

    def get(self, name: str) -> Effect:
        if name not in self._effects:
            self._effects[name] = Effect(name, self.voices[name])
        return self._effects[name]


bank = EffectBank()

_EFFECT_NAMES: dict[EventType, str] = {
    EventType.STICK_BALL: "cue",
    EventType.BALL_BALL: "ballcollision",
    EventType.BALL_LINEAR_CUSHION: "cushion",
    EventType.BALL_CIRCULAR_CUSHION: "cushion",
    EventType.BALL_POCKET: "pot",
    EventType.BALL_TABLE: "cushion",
}

_REFERENCE_SPEEDS: dict[EventType, float] = {
    EventType.STICK_BALL: 5.0,
    EventType.BALL_BALL: 3.0,
    EventType.BALL_LINEAR_CUSHION: 3.0,
    EventType.BALL_CIRCULAR_CUSHION: 3.0,
    EventType.BALL_POCKET: 2.0,
    EventType.BALL_TABLE: 1.0,
}
"""Impact speed (m/s) at which each event type reaches full volume."""


def is_audible(event: Event) -> bool:
    return event.event_type in _EFFECT_NAMES


def impact_speed(event: Event) -> float:
    """The speed at which the event's agents come together.

    For collisions with a surface this is the ball's velocity component along the
    contact normal, so a glancing cushion hit is quieter than a square one. For
    ball-ball collisions it is the relative speed along the line of centers.

    Raises:
        ValueError: If the event type has no associated sound.
    """
    event_type = event.event_type

    if event_type == EventType.STICK_BALL:
        ball = event.get_ball(event.ids[1], initial=False)
        return ptmath.norm3d(ball.state.rvw[1])

    if event_type == EventType.BALL_BALL:
        ball1 = event.get_ball(event.ids[0])
        ball2 = event.get_ball(event.ids[1])
        normal = ptmath.unit_vector(ball2.state.rvw[0] - ball1.state.rvw[0])
        return abs(float(np.dot(ball1.state.rvw[1] - ball2.state.rvw[1], normal)))

    if event_type in (EventType.BALL_LINEAR_CUSHION, EventType.BALL_CIRCULAR_CUSHION):
        ball = event.get_ball(event.ids[0])
        cushion = event.get_cushion(event.ids[1])
        normal = cushion.get_normal_xy(ball.state.rvw[0])
        return abs(float(np.dot(ball.state.rvw[1], normal)))

    if event_type == EventType.BALL_POCKET:
        ball = event.get_ball(event.ids[0])
        return ptmath.norm3d(ball.state.rvw[1])

    if event_type == EventType.BALL_TABLE:
        ball = event.get_ball(event.ids[0])
        return abs(float(ball.state.rvw[1][2]))

    raise ValueError(f"No sound is associated with event type {event_type}")


def volume(event: Event) -> float:
    """Volume in [0, 1], before the user's master volume is applied."""
    return min(1.0, impact_speed(event) / _REFERENCE_SPEEDS[event.event_type])


_muted: bool = False


@contextmanager
def muted() -> Generator[None, None, None]:
    """Suppress all sound effects within the block.

    Use this around a seek that is expected to pass over scheduled sounds, such as
    rebuilding the animation at a new speed and jumping back to the current time.
    """
    global _muted
    _muted = True
    try:
        yield
    finally:
        _muted = False


def _fire(effect: Effect, level: float, scheduled: float, clock: Callable[[], float]):
    if _muted or clock() - scheduled > FIRE_TOLERANCE:
        return

    master = settings.audio.volume
    play_rate = 1.0 + random.uniform(-PLAY_RATE_JITTER, PLAY_RATE_JITTER)
    effect.play(level * master, play_rate)


def build_sequence(
    events: list[Event], playback_speed: float, clock: Callable[[], float]
) -> Sequence:
    """Build a sequence that plays each audible event's sound at its playback time.

    Args:
        events:
            The system's events. Event times are in simulation seconds, with the
            cue strike at zero.
        playback_speed:
            The factor by which simulation time is compressed in the animation. Must
            match the speed the ball animations were built with.
        clock:
            Returns the current animation time in the same time base as the returned
            sequence, i.e. seconds since the cue strike, at playback speed. Used to
            suppress sounds whose scheduled time is seeked past rather than played
            through.
    """
    sequence = Sequence()
    elapsed = 0.0

    for event in events:
        if not is_audible(event):
            continue

        level = volume(event)
        if level < MIN_VOLUME:
            continue

        scheduled = event.time / playback_speed
        sequence.append(Wait(scheduled - elapsed))
        sequence.append(
            FunctionInterval(
                _fire,
                extraArgs=[
                    bank.get(_EFFECT_NAMES[event.event_type]),
                    level,
                    scheduled,
                    clock,
                ],
            )
        )
        elapsed = scheduled

    return sequence
