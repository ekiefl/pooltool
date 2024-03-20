from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

import attrs

from pooltool.layouts import snooker_color_locs
from pooltool.utils.strenum import StrEnum, auto


class BallGroup(StrEnum):
    REDS = auto()
    COLORS = auto()

    @property
    def balls(self) -> Tuple[str, ...]:
        """Return the ball IDs associated to a BallGroup"""
        return _group_to_balls_dict[self]

    @classmethod
    def get(cls, balls: Tuple[str, ...]) -> BallGroup:
        if balls in _group_to_balls_dict:
            return _balls_to_group_dict[balls]

        if all(ball in _group_to_balls_dict[cls.COLORS] for ball in balls):
            return cls.COLORS

        if all(ball in _group_to_balls_dict[cls.REDS] for ball in balls):
            return cls.REDS

        raise ValueError(f"Cannot match {balls} to a BallGroup")


_group_to_balls_dict: Dict[BallGroup, Tuple[str, ...]] = {
    BallGroup.REDS: tuple(f"red_{i:02d}" for i in range(1, 16)),
    BallGroup.COLORS: ("yellow", "green", "brown", "blue", "pink", "black"),
}

_balls_to_group_dict: Dict[Tuple[str, ...], BallGroup] = {
    v: k for k, v in _group_to_balls_dict.items()
}


@attrs.define
class BallInfo:
    id: str
    color: bool
    order: int
    points: int
    respot: Optional[Tuple[float, float]] = attrs.field(default=None, init=False)

    def __attrs_post_init__(self):
        if self.id == "red":
            return

        assert isinstance((loc := snooker_color_locs[self.id].relative_to), tuple)
        self.respot = loc


ball_infos_dict: Dict[str, BallInfo] = {
    "white": BallInfo("white", False, -1, 4),
    "red": BallInfo("red", False, -1, 1),
    "yellow": BallInfo("yellow", True, 0, 2),
    "green": BallInfo("green", True, 1, 3),
    "brown": BallInfo("brown", True, 2, 4),
    "blue": BallInfo("blue", True, 3, 5),
    "pink": BallInfo("pink", True, 4, 6),
    "black": BallInfo("black", True, 5, 7),
}


def _match_ball_id_to_key(ball_id: str) -> str:
    return "red" if ball_id.startswith("red_") else ball_id


def ball_info(ball_id: str) -> BallInfo:
    return ball_infos_dict[_match_ball_id_to_key(ball_id)]


def ball_infos(ball_ids: Optional[Iterable[str]] = None) -> Dict[str, BallInfo]:
    if ball_ids is None:
        return ball_infos_dict.copy()

    return {ball_id: ball_info(ball_id) for ball_id in ball_ids}
