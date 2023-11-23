from __future__ import annotations

from typing import Dict, List, Union

import attrs
import pandas as pd

from pooltool.game.ruleset.datatypes import ShotInfo
from pooltool.ptmath import get_constant_value_blocks


@attrs.define
class ShotResult:
    player: str
    legal: bool
    turn_over: bool
    game_over: bool
    winner: str

    @classmethod
    def from_shot_info(cls, shot_info: ShotInfo) -> ShotResult:
        return cls(
            player=shot_info.player.name,
            legal=shot_info.legal,
            turn_over=shot_info.turn_over,
            game_over=shot_info.game_over,
            winner=shot_info.winner.name if shot_info.winner is not None else "",
        )


FIELDS: List[str] = list(attrs.fields_dict(ShotResult).keys())


@attrs.define
class ResultAccumulator:
    data: Dict[str, Union[List[str], List[bool]]] = attrs.field(
        init=False, factory=dict
    )
    fields: List[str] = attrs.field(init=False, default=FIELDS)

    def __attrs_post_init__(self):
        for field in FIELDS:
            self.data[field] = []

    def add(self, shot_result: ShotResult) -> None:
        for field in FIELDS:
            self.data[field].append(getattr(shot_result, field))

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.data)

    def fraction_legal(self, player: str) -> float:
        return (
            self.to_frame()
            .query(f"player == '{player}'")
            .pipe(lambda x: x.legal.sum() / x.shape[0])
        )

    def average_turn_length(self, player: str) -> float:
        turn_array = (
            self.to_frame().query(f"player == '{player}'").turn_over.values.astype(int)
        )

        turn_lengths: List[int] = []
        turn_length = 0
        for turn in turn_array:
            turn_length += 1
            if turn == 1:
                turn_lengths.append(turn_length)
                turn_length = 0

        if turn_length > 0:
            turn_lengths.append(turn_length)

        return sum(turn_lengths) / len(turn_lengths)
