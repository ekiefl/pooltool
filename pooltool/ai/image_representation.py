from __future__ import annotations

import os
from typing import Callable, List, Protocol, Tuple

import attrs
import matplotlib.pyplot as plt
import numba
import numpy as np
import pygame
from numpy.typing import NDArray
from pygame.surface import Surface
from pygame.time import Clock

import pooltool.constants as const
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.objects.table.datatypes import Table
from pooltool.system.datatypes import System

Color = Tuple[int, int, int]
WHITE: Color = (255, 255, 255)
GRAYSCALE_CONVERSION_WEIGHTS = np.array([0.299, 0.587, 0.114], dtype=np.float64)


class StateLike(Protocol):
    system: System
    game: Ruleset


def to_grayscale(color: Color) -> Color:
    """Convert a color to grayscale."""
    grayscale_intensity = int(np.dot(np.array(color), GRAYSCALE_CONVERSION_WEIGHTS))
    return (grayscale_intensity, grayscale_intensity, grayscale_intensity)


@numba.jit(nopython=True, cache=True)
def array_to_grayscale(raw_data, weights):
    """Convert image array to grayscale."""
    height, width, _ = raw_data.shape
    grayscale_data = np.empty((height, width), dtype=np.uint8)

    for i in range(height):
        for j in range(width):
            grayscale_data[i, j] = int(
                raw_data[i, j, 0] * weights[0]
                + raw_data[i, j, 1] * weights[1]
                + raw_data[i, j, 2] * weights[2]
            )

    return grayscale_data


@attrs.define
class RenderPlane:
    ball_ids: List[str] = attrs.field(factory=list)
    cushion_ids: List[str] = attrs.field(factory=list)


@attrs.define
class RenderConfig:
    planes: List[RenderPlane]


class PygameRenderer:
    def __init__(
        self,
        coordinates: CoordinateManager,
        render_config: RenderConfig,
    ):
        self.coordinates: CoordinateManager = coordinates
        self.render_config: RenderConfig = render_config

        self.screen: Surface
        self.clock: Clock
        self.state: StateLike

    def init(self) -> None:
        # For off-screen rendering
        os.environ["SDL_DRIVER"] = "dummy"

        self.screen = pygame.Surface((self.coordinates.width, self.coordinates.height))
        self.clock = pygame.time.Clock()

        pygame.init()

    def set_state(self, state: StateLike) -> None:
        self.state = state

    def draw_all(self) -> None:
        all_balls = list(self.state.system.balls.keys())
        all_cushions = list(self.state.system.table.cushion_segments.linear.keys())

        self.draw_plane(
            RenderPlane(
                ball_ids=all_balls,
                cushion_ids=all_cushions,
            )
        )

    def draw_plane(self, plane: RenderPlane) -> None:
        self.screen.fill((0, 0, 0))

        for ball_id in plane.ball_ids:
            ball = self.state.system.balls.get(ball_id)

            if ball is None:
                continue

            if ball.state.s == const.pocketed:
                continue

            x, y, _ = ball.state.rvw[0]
            radius = ball.params.R

            coords = self.coordinates.coords_to_px(x, y)

            pygame.draw.circle(
                surface=self.screen,
                color=WHITE,
                center=coords,
                radius=self.coordinates.scale_dist(radius),
            )

        for cushion_id in plane.cushion_ids:
            cushion = self.state.system.table.cushion_segments.linear.get(cushion_id)

            if cushion is None:
                continue

            pygame.draw.line(
                surface=self.screen,
                color=WHITE,
                start_pos=self.coordinates.coords_to_px(*cushion.p1[:2]),
                end_pos=self.coordinates.coords_to_px(*cushion.p2[:2]),
                width=1,
            )

    def screen_as_array(self) -> NDArray[np.float32]:
        """Return the current screen as an array"""
        array = array_to_grayscale(
            pygame.surfarray.array3d(self.screen),
            GRAYSCALE_CONVERSION_WEIGHTS,
        )

        # H, W, C
        array = array.transpose((1, 0))

        # Convert to float and normalize to [0, 1]
        array = array.astype(np.float32) / 255.0

        return array

    def observation(self) -> NDArray[np.float32]:
        """Return the current screen as an array"""
        array = np.zeros(
            (
                self.coordinates.height,
                self.coordinates.width,
                len(self.render_config.planes),
            ),
            dtype=np.float32,
        )

        for plane_idx, plane in enumerate(self.render_config.planes):
            self.draw_plane(plane)
            array[..., plane_idx] = self.screen_as_array()

        return array

    def display_observation(self, observation: NDArray[np.float32]):
        observation = self.observation()
        channels = observation.shape[-1]

        ncols = int(np.ceil(np.sqrt(channels)))
        nrows = int(np.ceil(channels / ncols))

        _, axes = plt.subplots(nrows, ncols, figsize=(12, 8), facecolor="gray")

        plt.tight_layout()

        for i in range(channels):
            row, col = divmod(i, ncols)
            ax = axes[row, col]
            ax.imshow(observation[:, :, i], cmap="gray")
            ax.axis("off")
            ax.set_title(f"Channel {i+1}")

        for j in range(channels, nrows * ncols):
            axes.flat[j].axis("off")

        plt.show()

    def close(self) -> None:
        pygame.quit()

    @classmethod
    def build(
        cls, table: Table, px: int, render_config: RenderConfig
    ) -> PygameRenderer:
        return cls(CoordinateManager.build(table, px), render_config)


@attrs.define
class CoordinateManager:
    width: int
    height: int
    coords_to_px: Callable[[float, float], Tuple[float, float]]
    scale_dist: Callable[[float], float]

    @classmethod
    def build(cls, table: Table, px: int) -> CoordinateManager:
        assert px % 2 == 0, "px should be even for symmetric table representation"

        xs = []
        ys = []

        for cushion in table.cushion_segments.linear.values():
            xs.append(cushion.p1[0])
            xs.append(cushion.p2[0])
            ys.append(cushion.p1[1])
            ys.append(cushion.p2[1])

        screen_x_min, screen_x_max = min(xs), max(xs)
        screen_y_min, screen_y_max = min(ys), max(ys)

        table_x_min = table.cushion_segments.linear["3"].p1[0]
        table_y_min = table.cushion_segments.linear["18"].p1[1]

        assert screen_y_max - screen_y_min > screen_x_max - screen_x_min, "Assume y > x"

        px_y = px
        px_x = px // ((screen_y_max - screen_y_min) / (screen_x_max - screen_x_min))
        if (px_y % 2) > 0:
            px_x += 1

        sy = (px_y-1) / (screen_y_max - screen_y_min)
        sx = (px_x-1) / (screen_x_max - screen_x_min)

        offset_y = table_y_min - screen_y_min
        offset_x = table_x_min - screen_x_min

        def coords_to_px(x: float, y: float) -> Tuple[float, float]:
            return sx * (x + offset_x), sy * (y + offset_y)

        def scale_dist(d: float) -> float:
            return max(1.0, d * max(sy, sx))

        return CoordinateManager(int(px_x), int(px_y), coords_to_px, scale_dist)


if __name__ == "__main__":
    import pooltool as pt
    from pooltool.ai.datatypes import State

    game_type = pt.GameType.SUMTOTHREE

    game = pt.get_ruleset(game_type)()
    game.players = [
        pt.Player("Player"),
    ]
    table = pt.Table.from_game_type(game_type)
    balls = pt.get_rack(
        game_type=game_type,
        table=table,
        params=None,
        ballset=None,
        spacing_factor=1e-3,
    )
    cue = pt.Cue(cue_ball_id=game.shot_constraints.cueball(balls))
    system = pt.System(table=table, balls=balls, cue=cue)
    system.strike(V0=4, phi=89.9)
    pt.simulate(system, inplace=True)

    config = RenderConfig(
        planes=[
            RenderPlane(ball_ids=["cue"]),
            RenderPlane(ball_ids=["object"]),
            RenderPlane(ball_ids=["cue", "object"]),
            RenderPlane(cushion_ids=["3", "12", "9", "18"]),
        ],
    )

    renderer = PygameRenderer.build(system.table, 400, config)

    renderer.init()
    renderer.set_state(State(system, game))

    for i in range(len(system.events)):
        for ball in system.balls.values():
            ball.state = ball.history[i]
        renderer.display_observation(renderer.observation())
        break

    renderer.close()
