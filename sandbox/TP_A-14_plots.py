#! /usr/bin/env python

import math

import numpy as np
from ball_ball_collisions import (
    BallBallCollisionExperimentConfig,
    cue_strike_spin_rate_factor_percent_english,
    plot_throw_vs_cut_angle,
    plot_throw_vs_percent_sidespin,
    plot_throw_vs_sidespin_factor,
)

from pooltool.objects.ball.datatypes import BallParams
from pooltool.physics.resolve.ball_ball.friction import (
    AlciatoreBallBallFriction,
)
from pooltool.physics.resolve.ball_ball.frictional_inelastic import FrictionalInelastic


def technical_proof_A14_plots(config: BallBallCollisionExperimentConfig):
    slow_speed = 0.447
    medium_speed = 1.341
    fast_speed = 3.129
    alciatore_speeds = [slow_speed, medium_speed, fast_speed]

    model_str = config.model.model
    friction_str = config.model.friction.model

    title = f"Natural-Roll Shot Collision at Various Speeds\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(title, config, alciatore_speeds, topspin_factors=[1.0])

    title = f"Stun Shot Collision at Various Speeds\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(title, config, alciatore_speeds)

    title = f"Medium-Speed Shot with Various Amounts of Topspin\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(
        title, config, [medium_speed], topspin_factors=np.linspace(0, 1, 5)
    )

    title = f"Medium-Speed Head-On Collision with Various Amounts of Topspin\nThrow Angle vs. Sidespin\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_sidespin_factor(
        title, config, [medium_speed], topspin_factors=np.linspace(0, 1, 5)
    )

    title = f"Medium-Speed Half-Ball Hit with Various Amounts of Topspin\nThrow Angle vs. Sidespin\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_sidespin_factor(
        title,
        config,
        [medium_speed],
        topspin_factors=np.linspace(0, 1, 5),
        cut_angles=[math.radians(30)],
    )

    title = f"Head-On Collision at Various Speeds\nThrow Angle vs. Percent English\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_percent_sidespin(title, config, alciatore_speeds)

    title = f"Half-Ball Hit at Various Speeds\nThrow Angle vs. Percent English\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_percent_sidespin(
        title, config, alciatore_speeds, cut_angles=[math.radians(30)]
    )

    title = f"Slow-Speed Stun Shot with Various Typical Sidespins\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(
        title, config, [slow_speed], sidespin_factors=[0.0, -1.0, 1.0]
    )

    title = f"Slow-Speed Stun Shot with Various 25% Sidespins\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(
        title,
        config,
        [slow_speed],
        sidespin_factors=[
            0.0,
            -cue_strike_spin_rate_factor_percent_english(25),
            cue_strike_spin_rate_factor_percent_english(25),
        ],
    )
    title = f"Medium-Speed Natural-Roll Shot with Various 25% Sidespins\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(
        title,
        config,
        [medium_speed],
        topspin_factors=[1.0],
        sidespin_factors=[
            0.0,
            -cue_strike_spin_rate_factor_percent_english(25),
            cue_strike_spin_rate_factor_percent_english(25),
        ],
    )

    title = f"Slow-Speed Stun Shot with Various 50% Sidespins\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(
        title,
        config,
        [slow_speed],
        sidespin_factors=[
            0.0,
            -cue_strike_spin_rate_factor_percent_english(50),
            cue_strike_spin_rate_factor_percent_english(50),
        ],
    )
    title = f"Medium-Speed Natural-Roll Shot with Various 50% Sidespins\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(
        title,
        config,
        [medium_speed],
        topspin_factors=[1.0],
        sidespin_factors=[
            0.0,
            -cue_strike_spin_rate_factor_percent_english(50),
            cue_strike_spin_rate_factor_percent_english(50),
        ],
    )

    title = f"Slow-Speed Stun Shot with Various 100% Sidespins\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(
        title,
        config,
        [slow_speed],
        sidespin_factors=[
            0.0,
            -cue_strike_spin_rate_factor_percent_english(100),
            cue_strike_spin_rate_factor_percent_english(100),
        ],
    )
    title = f"Medium-Speed Natural-Roll Shot with Various 100% Sidespins\nThrow Angle vs. Cut Angle\n(model={model_str}, model.friction={friction_str})"
    plot_throw_vs_cut_angle(
        title,
        config,
        [medium_speed],
        topspin_factors=[1.0],
        sidespin_factors=[
            0.0,
            -cue_strike_spin_rate_factor_percent_english(100),
            cue_strike_spin_rate_factor_percent_english(100),
        ],
    )


def main():
    ball_params = BallParams.default()
    alciatore_friction = AlciatoreBallBallFriction(a=9.951e-3, b=0.108, c=1.088)
    # average_friction = AverageBallBallFriction()
    for model in [
        FrictionalInelastic(friction=alciatore_friction),
        # FrictionalMathavan(friction=alciatore_friction),
        # FrictionalInelastic(friction=average_friction),
        # FrictionalMathavan(friction=average_friction),
    ]:
        config = BallBallCollisionExperimentConfig(model=model, params=ball_params)
        technical_proof_A14_plots(config)


if __name__ == "__main__":
    main()
