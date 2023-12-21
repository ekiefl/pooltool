from __future__ import annotations

import random
from typing import Any, Dict

import attrs
import numpy as np
from numpy.typing import NDArray

import pooltool as pt
from pooltool.ai.image_representation import PygameRenderer
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.system.datatypes import System

ObservationDict = Dict[str, Any]

BALL_DIM = 2


@attrs.define
class State:
    system: System
    game: Ruleset


class Spaces:
    def __init__(self, observation, action, reward) -> None:
        """gym.spaces instances"""
        self.observation = observation
        self.action = action
        self.reward = reward


@attrs.define
class BaseLightZeroEnv(State):
    spaces: Spaces

    def observation(self) -> ObservationDict:
        return dict(
            observation=self.observation_array(),
            action_mask=None,
            to_play=-1,
        )

    def observation_array(self):
        raise NotImplementedError("Inheriting classes must define this")

    def scale_action(self, action: NDArray[np.float32]) -> NDArray[np.float32]:
        """Scale the action from [-1, 1] to the given range [low, high]"""
        low = self.spaces.action.low  # type: ignore
        high = self.spaces.action.high  # type: ignore
        assert np.all(action >= -1) and np.all(action <= 1), f"{action=}"
        scaled_action = low + (0.5 * (action + 1.0) * (high - low))
        return np.clip(scaled_action, low, high)

    def set_action(self, scaled_action: NDArray[np.float32]) -> None:
        """Set the cue parameters from an action array"""
        self.system.cue.set_state(
            V0=scaled_action[0],
            phi=pt.aim.at_ball(self.system, "object", cut=scaled_action[1]),
        )

    def simulate(self) -> None:
        """Simulate the system"""
        pt.simulate(self.system, inplace=True, max_events=200)
        self.game.process_shot(self.system)
        self.game.advance(self.system)

    def seed(self, seed_value: int) -> None:
        random.seed(seed_value)
        np.random.seed(seed_value)


@attrs.define
class LightZeroEnv(BaseLightZeroEnv):
    def _slice(self, ball_idx: int) -> slice:
        return slice(ball_idx * BALL_DIM, (ball_idx + 1) * BALL_DIM)

    def _null_obs(self) -> NDArray[np.float32]:
        return np.empty(len(self.system.balls) * BALL_DIM, dtype=np.float32)

    def observation_array(self) -> NDArray[np.float32]:
        """Return the system state as a 1D array of ball coordinates"""
        obs = self._null_obs()
        for ball_idx, ball_id in enumerate(self.system.balls.keys()):
            obs[self._slice(ball_idx)] = self.system.balls[ball_id].state.rvw[
                0, :BALL_DIM
            ]

        return obs

    def set_observation(self, obs: NDArray[np.float32]) -> None:
        """Set the system state from an observation array"""
        for ball_idx, ball_id in enumerate(self.system.balls.keys()):
            self.system.balls[ball_id].state.rvw[0, :BALL_DIM] = obs[
                self._slice(ball_idx)
            ]

    @staticmethod
    def get_obs_space(balls: Dict[str, pt.Ball], table: pt.Table) -> Any:
        table_length = table.l
        table_width = table.l
        ball_radius = balls["cue"].params.R

        xmin, ymin = ball_radius, ball_radius
        xmax, ymax = table_width - ball_radius, table_length - ball_radius

        from gym import spaces

        return spaces.Box(
            low=np.array([xmin, ymin] * len(balls), dtype=np.float32),
            high=np.array([xmax, ymax] * len(balls), dtype=np.float32),
            shape=(BALL_DIM * len(balls),),
            dtype=np.float32,
        )


@attrs.define
class LightZeroImageEnv(BaseLightZeroEnv):
    renderer: PygameRenderer

    def observation_array(self) -> NDArray[np.uint8]:
        """Return the system state as an image array"""
        return self.renderer.observation()

    @staticmethod
    def get_obs_space(renderer: PygameRenderer) -> Any:
        from gym import spaces

        channels = 1 if renderer.render_config.grayscale else 3

        return spaces.Box(
            low=0,
            high=255,
            shape=(channels, renderer.height, renderer.width),
            dtype=np.uint8,
        )
