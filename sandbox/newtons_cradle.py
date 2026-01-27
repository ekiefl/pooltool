import argparse

import numpy as np

import pooltool as pt
from pooltool.layouts import BallPos, Jump, ball_cluster_blueprint, generate_layout


def main():
    parser = argparse.ArgumentParser(
        description="Simulate an imperfect Newton's cradle. WARNING: if angle-variation "
        "is low and n-balls is high, the event count will skyrocket.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--n-balls", type=int, default=4, help="Number of balls")
    parser.add_argument(
        "--angle-variation", type=float, default=0.3, help="Max angle offset (degrees)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    table = pt.Table.default()
    ball_params = pt.BallParams.default()

    jump_sequence = [
        (
            Jump.ANGLE(90 + rng.uniform(-args.angle_variation, args.angle_variation)),
            {str(i + 2)},
        )
        for i in range(args.n_balls - 1)
    ]

    blueprint = ball_cluster_blueprint(
        seed=BallPos([], (0.5, 0.4), {"1"}),
        jump_sequence=jump_sequence,
    )

    cue = BallPos([], (0.5, 0.1), {"cue"})
    blueprint.append(cue)

    balls = generate_layout(
        blueprint,
        table,
        ballset=pt.objects.BallSet("pooltool_pocket"),
        ball_params=ball_params,
        spacing_factor=0,
    )

    system = pt.System(
        balls=balls,
        table=table,
        cue=pt.Cue.default(),
    )

    system.strike(V0=2, phi=pt.aim.at_ball(system, "1", cut=0))
    pt.simulate(system, inplace=True)
    print(len(system.events))
    pt.show(system)


if __name__ == "__main__":
    main()
