#! /usr/bin/env python

from ball_ball_collisions import (
    BallBallCollisionExperimentConfig,
    plot_sidespin_transfer_effectiveness_vs_percent_sidespin,
    plot_sidespin_transfer_percentage_vs_percent_sidespin,
)

from pooltool.objects.ball.datatypes import BallParams
from pooltool.physics.resolve.ball_ball.friction import (
    AlciatoreBallBallFriction,
)
from pooltool.physics.resolve.ball_ball.frictional_inelastic import FrictionalInelastic


def technical_proof_A27_plots(config: BallBallCollisionExperimentConfig):
    slow_speed = 0.447
    medium_speed = 1.341
    fast_speed = 3.129
    alciatore_speeds = [slow_speed, medium_speed, fast_speed]

    model_str = config.model.model
    friction_str = config.model.friction.model

    title = f"Medium-Speed Straight-In Stun-Shot at Various Speeds\nSpin Transfer % vs. Percent English\n(model={model_str}, model.friction={friction_str})"
    plot_sidespin_transfer_percentage_vs_percent_sidespin(
        title, config, alciatore_speeds, topspin_factors=[0], min_sidespin_percentage=1
    )

    title = f"Medium-Speed Straight-In Stun-Shot at Various Speeds\nSpin Transfer Effectiveness vs. Percent English\n(model={model_str}, model.friction={friction_str})"
    plot_sidespin_transfer_effectiveness_vs_percent_sidespin(
        title, config, alciatore_speeds, topspin_factors=[0], min_sidespin_percentage=1
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
        config = BallBallCollisionExperimentConfig(
            model=model, params=ball_params, xy_line_of_centers_angle_radians=-234
        )
        technical_proof_A27_plots(config)


if __name__ == "__main__":
    main()
