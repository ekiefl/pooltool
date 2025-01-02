from __future__ import annotations

from typing import Any, Dict, Mapping, Type

from cattrs.gen import make_dict_unstructure_fn

from pooltool.physics.resolve.ball_ball import (
    BallBallCollisionStrategy,
    ball_ball_models,
)
from pooltool.physics.resolve.ball_ball.friction import (
    BallBallFrictionStrategy,
    ball_ball_friction_models,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionCollisionStrategy,
    BallLCushionCollisionStrategy,
    ball_ccushion_models,
    ball_lcushion_models,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketStrategy,
    ball_pocket_models,
)
from pooltool.physics.resolve.stick_ball import (
    StickBallCollisionStrategy,
    stick_ball_models,
)
from pooltool.physics.resolve.transition import (
    BallTransitionStrategy,
    ball_transition_models,
)
from pooltool.serialize import conversion
from pooltool.serialize.serializers import SerializeFormat

_model_map: Mapping[Any, Mapping[Any, Type]] = {
    BallBallCollisionStrategy: ball_ball_models,
    BallLCushionCollisionStrategy: ball_lcushion_models,
    BallCCushionCollisionStrategy: ball_ccushion_models,
    BallPocketStrategy: ball_pocket_models,
    StickBallCollisionStrategy: stick_ball_models,
    BallTransitionStrategy: ball_transition_models,
    BallBallFrictionStrategy: ball_ball_friction_models,
}


def _disambiguate_model_structuring(v: Dict[str, Any], t: Type) -> Any:
    return conversion[SerializeFormat.YAML].structure(v, _model_map[t][v["model"]])


def register_serialize_hooks():
    conversion.register_structure_hook_func(
        check_func=lambda t: t in _model_map, func=_disambiguate_model_structuring
    )

    for models in _model_map.values():
        for model_cls in models.values():
            # Unstructure init=False attrs fields
            conversion.register_unstructure_hook(
                model_cls,
                make_dict_unstructure_fn(
                    model_cls,
                    conversion[SerializeFormat.YAML],
                    _cattrs_include_init_false=True,
                ),
                which=(SerializeFormat.YAML,),
            )
