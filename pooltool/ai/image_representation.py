from __future__ import annotations

from typing import Callable, Tuple

import attrs
import numba
import numpy as np
import pygame
from pygame.surface import Surface
from pygame.time import Clock

import pooltool.constants as const
from pooltool.ai.datatypes import State
from pooltool.objects.table.datatypes import Table

Color = Tuple[int, int, int]

GRAYSCALE_CONVERSION_WEIGHTS = np.array([0.299, 0.587, 0.114], dtype=np.float64)


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
class RenderConfig:
    grayscale: bool = attrs.field()
    cushion_color: Color = attrs.field()
    ball_color: Callable[[str, State], Color]


class PygameRenderer:
    def __init__(self, coordinates: CoordinateManager, render_config: RenderConfig):
        self.coordinates: CoordinateManager = coordinates
        self.render_config: RenderConfig = render_config

        self.screen: Surface
        self.clock: Clock
        self.state: State

    @property
    def width(self) -> int:
        return self.coordinates.width

    @property
    def height(self) -> int:
        return self.coordinates.height

    def init(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()

    def set_state(self, state: State) -> None:
        self.state = state

    def render(self) -> None:
        self.screen.fill((0, 0, 0))

        for ball in self.state.system.balls.values():
            if ball.state.s == const.pocketed:
                continue

            x, y, _ = ball.state.rvw[0]
            radius = ball.params.R

            ball_color = self.render_config.ball_color(ball.id, self.state)
            if self.render_config.grayscale:
                ball_color = to_grayscale(ball_color)

            pygame.draw.circle(
                surface=self.screen,
                color=ball_color,
                center=self.coordinates.coords_to_px(x, y),
                radius=self.coordinates.scale_dist(radius),
            )

        cushion_color = self.render_config.cushion_color
        if self.render_config.grayscale:
            cushion_color = to_grayscale(cushion_color)

        for cushion in self.state.system.table.cushion_segments.linear.values():
            pygame.draw.line(
                surface=self.screen,
                color=cushion_color,
                start_pos=self.coordinates.coords_to_px(*cushion.p1[:2]),
                end_pos=self.coordinates.coords_to_px(*cushion.p2[:2]),
                width=1,
            )

        pygame.display.flip()

    def observation(self) -> np.ndarray:
        raw_data = pygame.surfarray.array3d(self.screen)
        if self.render_config.grayscale:
            return array_to_grayscale(raw_data, GRAYSCALE_CONVERSION_WEIGHTS)
        else:
            return np.transpose(raw_data, (1, 0, 2))

    def display_frame(self) -> None:
        """Display the current frame in a window"""
        self.render()

        # Display until exited
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            self.clock.tick(60)

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

        sy = px_y / (screen_y_max - screen_y_min)
        sx = px_x / (screen_x_max - screen_x_min)

        offset_y = table_y_min - screen_y_min
        offset_x = table_x_min - screen_x_min

        def coords_to_px(x: float, y: float) -> Tuple[float, float]:
            return sx * (x + offset_x), sy * (y + offset_y)

        def scale_dist(d: float) -> float:
            return d * max(sy, sx)

        return CoordinateManager(px_x, px_y, coords_to_px, scale_dist)


if __name__ == "__main__":
    import pooltool as pt
    from pooltool.ai.datatypes import State

    system = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=(table := pt.Table.default()),
        balls=pt.get_nine_ball_rack(table),
    )
    system.strike(V0=8, phi=pt.aim.at_ball(system, "1"))
    pt.simulate(system, inplace=True)
    game = pt.get_ruleset(pt.GameType.NINEBALL)()

    def color_map(ball_id, _):
        if ball_id == "cue":
            return (255, 255, 255)  # Cue ball is white
        elif ball_id == "1":
            return (255, 255, 0)  # 1-ball is yellow
        elif ball_id == "2":
            return (0, 0, 255)  # 2-ball is blue
        elif ball_id == "3":
            return (255, 0, 0)  # 3-ball is red
        elif ball_id == "4":
            return (128, 0, 128)  # 4-ball is purple
        elif ball_id == "5":
            return (255, 165, 0)  # 5-ball is orange
        elif ball_id == "6":
            return (0, 128, 0)  # 6-ball is green
        elif ball_id == "7":
            return (128, 0, 0)  # 7-ball is burgundy
        elif ball_id == "8":
            return (0, 0, 0)  # 8-ball is black
        elif ball_id == "9":
            return (204, 204, 0)  # 9-ball is a blackened yellow
        else:
            return (255, 128, 128)  # Default color

    config = RenderConfig(
        grayscale=True,
        cushion_color=(255, 255, 255),
        ball_color=color_map,
    )

    renderer = PygameRenderer.build(system.table, 300, config)
    renderer.init()
    renderer.set_state(State(system, game))

    for i in range(len(system.events)):
        for ball in system.balls.values():
            ball.state = ball.history[i]
        renderer.display_frame()

    renderer.close()
