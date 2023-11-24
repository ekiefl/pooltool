from __future__ import annotations

from typing import Any, Dict, List, Protocol, Tuple, Union

import attrs
import pandas as pd

from pooltool.game.ruleset.datatypes import ShotInfo


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

    @property
    def players(self) -> List[str]:
        return list(set(self.data["player"]))  # type: ignore

    def __attrs_post_init__(self):
        for field in FIELDS:
            self.data[field] = []

    def add(self, shot_result: ShotResult) -> None:
        for field in FIELDS:
            self.data[field].append(getattr(shot_result, field))

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.data)

    def summary(self) -> pd.DataFrame:
        summary_data: Dict[str, Any] = {
            "player": [],
            "metric": [],
            "score": [],
        }

        frame = self.to_frame()

        for fn in FUNCTIONS:
            for player in self.players:
                summary_data["player"].append(player)
                summary_data["metric"].append(fn.__name__)
                summary_data["score"].append(fn(frame, player))

        return pd.DataFrame(summary_data)

    def plot_summary(self):
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        df = self.summary()
        pivot_df = df.pivot(index="metric", columns="player", values="score")

        colors = {
            self.players[0]: "#1f77b4",
            self.players[1]: "#ff7f0e",
        }

        fig = make_subplots(rows=1, cols=len(FUNCTIONS), subplot_titles=pivot_df.index)

        for i, metric in enumerate(pivot_df.index, start=1):
            for player in pivot_df.columns:
                fig.add_trace(
                    go.Bar(
                        x=[player],
                        y=[pivot_df.loc[metric, player]],
                        name=player,
                        marker_color=colors[player],
                    ),
                    row=1,
                    col=i,
                )

        fig.update_layout(
            title_text="Comparison of Player Metrics",
            showlegend=False,
            barmode="group",
            height=400,
            width=900,
        )

        fig.show()


class PlayerMetric(Protocol):
    def __call__(self, frame: pd.DataFrame, player: str) -> float:
        ...


def shots_taken(frame: pd.DataFrame, player: str) -> float:
    return frame.query(f"player == '{player}'").shape[0]


def games_played(frame: pd.DataFrame, player: str) -> float:
    return frame.query("game_over == True").shape[0]


def fraction_legal(frame: pd.DataFrame, player: str) -> float:
    return frame.query(f"player == '{player}'").pipe(
        lambda x: x.legal.sum() / x.shape[0]
    )


def fraction_won(frame: pd.DataFrame, player: str) -> float:
    games = frame.query("game_over == True")
    return games.query(f"player == '{player}'").shape[0] / games.shape[0]


def average_turn_length(frame: pd.DataFrame, player: str) -> float:
    turn_array = frame.query(f"player == '{player}'").turn_over.values.astype(int)

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


FUNCTIONS: Tuple[PlayerMetric, ...] = (
    shots_taken,
    fraction_legal,
    average_turn_length,
    fraction_won,
    games_played,
)
