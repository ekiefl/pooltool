from __future__ import annotations

import importlib
import sys
from functools import partial
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import attrs
import numpy as np
import torch
from ding.config import compile_config
from ding.envs import create_env_manager, get_vec_env_setting, to_ndarray
from ding.policy import create_policy
from ding.utils import set_pkg_seed
from gym import spaces
from lzero.mcts.utils import prepare_observation
from lzero.worker import MuZeroEvaluator

from pooltool.ai import aim
from pooltool.ai.action import Action
from pooltool.ai.datatypes import LightZeroEnv, ObservationDict, Spaces, State
from pooltool.events.datatypes import EventType
from pooltool.events.filter import filter_type
from pooltool.game.datatypes import GameType
from pooltool.game.layouts import get_rack
from pooltool.game.ruleset import get_ruleset
from pooltool.game.ruleset.datatypes import Player, Ruleset
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.system.datatypes import System

SUPPORTED_GAMETYPES = {
    GameType.SUMTOTHREE,
}


def calc_reward(state: State) -> float:
    """Calculate the reward

    A point is scored when both:

        (1) The player contacts the object ball with the cue ball
        (2) The sum of contacted rails by either balls is 3

    This reward is designed to offer a small reward for contacting the object ball, and
    a larger reward for scoring a point.
    """
    if not state.game.shot_info.turn_over:
        return 1.0

    if len(filter_type(state.system.events, EventType.BALL_BALL)):
        return 0.1

    return 0.0


def single_player_env(random_pos: bool = False) -> LightZeroEnv:
    """Create a 1 player environment (for training, evaluation, etc)"""
    gametype = GameType.SUMTOTHREE
    game = get_ruleset(gametype)(
        players=[Player("Player 1")],
        win_condition=-1,  # type: ignore
    )
    system = System(
        cue=Cue.default(),
        table=(table := Table.from_game_type(gametype)),
        balls=get_rack(gametype, table),
    )

    if random_pos:
        get_pos = lambda table, ball: (
            (table.w - 2 * ball.params.R) * np.random.rand() + ball.params.R,
            (table.l - 2 * ball.params.R) * np.random.rand() + ball.params.R,
            ball.params.R,
        )
        system.balls["cue"].state.rvw[0] = get_pos(system.table, system.balls["cue"])
        system.balls["object"].state.rvw[0] = get_pos(
            system.table, system.balls["object"]
        )

    return get_env(State(system, game))


def get_env(state: State) -> LightZeroEnv:
    """Create a SumToThree environment from a State"""
    return LightZeroEnv(
        system=state.system,
        game=state.game,
        spaces=Spaces(
            observation=LightZeroEnv.get_obs_space(
                state.system.balls,
                state.system.table,
            ),
            action=spaces.Box(
                low=np.array([0.5, -70], dtype=np.float32),
                high=np.array([3, +70], dtype=np.float32),
                shape=(2,),
                dtype=np.float32,
            ),
            reward=spaces.Box(
                low=0.0,
                high=1.0,
                shape=(1,),
                dtype=np.float32,
            ),
        ),
    )


def _config_from_model_path(model_path: Path) -> Tuple[dict, dict]:
    config_path = model_path.parent.parent / "formatted_total_config.py"
    assert config_path.exists()

    sys.path.append(str(config_path.parent))
    config_module = importlib.import_module("formatted_total_config")
    return config_module.main_config, config_module.create_config


@attrs.define
class ActionInference:
    evaluator: MuZeroEvaluator

    def forward_ready_observation(
        self, observation: ObservationDict
    ) -> Tuple[Any, Any, Any]:
        obs = [observation["observation"]]
        obs = to_ndarray(obs)
        obs = prepare_observation(obs, self.evaluator.policy_config.model.model_type)
        obs = torch.from_numpy(obs).to(self.evaluator.policy_config.device).float()

        action_mask = [observation["action_mask"]]
        to_play = [np.array(observation["to_play"], dtype=np.int64)]

        return obs, action_mask, to_play

    def infer(self, observation: ObservationDict):
        obs = self.forward_ready_observation(observation)
        policy_output = self.evaluator._policy.forward(*obs)
        return policy_output[0]["action"]

    @classmethod
    def from_model_path(cls, model_path: Path) -> ActionInference:
        cfg, create_cfg = _config_from_model_path(model_path)

        # Otherwise the environment isn't registered
        create_cfg.policy.import_names = cfg.policy.import_names

        # We just need a single evaluator
        cfg.env.evaluator_env_num = 1
        cfg.env.n_evaluator_episode = 1

        # If cuda is available and was used for training, use it
        cfg.policy.device = (
            "cuda" if cfg.policy.cuda and torch.cuda.is_available() else "cpu"
        )

        cfg = compile_config(
            cfg, env=None, auto=True, create_cfg=create_cfg, save_cfg=False
        )

        env_fn, _, evaluator_env_cfg = get_vec_env_setting(cfg.env)
        evaluator_env = create_env_manager(
            cfg.env.manager, [partial(env_fn, cfg=c) for c in evaluator_env_cfg]
        )

        evaluator_env.seed(cfg.seed, dynamic_seed=False)
        set_pkg_seed(cfg.seed, use_cuda=cfg.policy.cuda)

        policy = create_policy(cfg.policy, enable_field=["learn", "eval"])
        policy.eval_mode.load_state_dict(
            torch.load(model_path, map_location=cfg.policy.device)
        )

        policy_config = cfg.policy

        return cls(
            MuZeroEvaluator(
                eval_freq=cfg.policy.eval_freq,
                n_evaluator_episode=cfg.env.n_evaluator_episode,
                stop_value=cfg.env.stop_value,
                env=evaluator_env,
                policy=policy.eval_mode,
                exp_name=cfg.exp_name,
                policy_config=policy_config,
            )
        )


@attrs.define
class SumToThreeAI:
    model: ActionInference = attrs.field()

    def decide(
        self,
        system: System,
        game: Ruleset,
        callback: Optional[Callable[[Action], None]] = None,
    ) -> Action:
        env = get_env(State(system, game))

        phi = aim.at_ball(env.system, "object")
        if callback is not None:
            callback(Action(1, phi, 0, 0, 0))

        action = self.model.infer(env.observation())
        V0, cut_angle = env.scale_action(action)
        phi = aim.at_ball(env.system, "object", cut=cut_angle)

        return Action(
            V0=V0,
            phi=phi,
            theta=0,
            a=0,
            b=0.2,
        )

    def apply(self, system: System, action: Action) -> None:
        action.apply(system.cue)

    @classmethod
    def load(cls, path: Path) -> SumToThreeAI:
        return cls(ActionInference.from_model_path(path))
