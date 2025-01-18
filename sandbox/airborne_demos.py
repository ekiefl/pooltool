import attrs

import pooltool as pt


def drop():
    ball = pt.Ball.create("cue", xy=(0.5, 0.5))
    ball.state.rvw[0, 2] = 0.3
    ball.state.rvw[1, 0] = 0.5
    ball.state.s = pt.constants.airborne

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball,),
    )

    return shot


def impulse_into():
    ball = pt.Ball.create("cue", xy=(0.5, 0.5))
    ball.state.rvw[1, 2] = -5.0
    ball.state.rvw[1, 1] = 0.5
    ball.state.s = pt.constants.airborne

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball,),
    )

    return shot


def simul():
    ball = pt.Ball.create("cue", xy=(0.5, 0.5))
    ball.state.rvw[0, 2] = 0.3
    ball.state.s = pt.constants.airborne
    ball.params = attrs.evolve(ball.params, g=9.81 / 6)

    other = pt.Ball.create("other", xy=(0.4, 0.5))
    other.state.rvw[0, 2] = 0.3
    other.state.rvw[2, 0] = 20
    other.state.s = pt.constants.airborne

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball, other),
    )

    return shot


def bounce_over():
    ball = pt.Ball.create("cue", xy=(0.7, 0.5))
    ball.state.rvw[1, 2] = -5.0
    ball.state.rvw[1, 1] = 0
    ball.state.rvw[1, 0] = 2
    ball.state.s = pt.constants.airborne

    other = pt.Ball.create("other", xy=(0.7, 0.42))
    other.state.rvw[1, 0] = 3.2
    other.state.s = pt.constants.sliding

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball, other),
    )

    return shot


def cushion_lift():
    ball = pt.Ball.create("cue", xy=(0.2, 0.5))
    ball.state.rvw[1, 0] = 3.5
    ball.state.s = pt.constants.sliding

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball,),
    )

    return shot


def slip():
    ball = pt.Ball.create("cue", xy=(0.5, 0.5))
    ball.state.rvw[0, 2] = 0.3
    ball.state.rvw[1, 1] = 1.0
    ball.state.rvw[2, 0] = 100.0
    ball.state.s = pt.constants.airborne

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball,),
    )

    return shot


def friction_test():
    ball = pt.Ball.create("cue")
    ball.state.rvw[0, :] = [0.8, 0.125, 0.20955 + ball.params.R]
    ball.state.rvw[1, :] = [0, 0.0637, 0]
    ball.state.rvw[2, :] = [58.11, 0, 0]
    ball.state.s = pt.constants.airborne

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball,),
    )

    return shot


def airborne_circular_cushion():
    ball = pt.Ball.create("cue", xy=(0.2, 0.5))
    scale = 1.3
    ball.state.rvw[0, 2] = 0.5
    ball.state.rvw[1, 0] = 2.5 * scale
    ball.state.rvw[1, 1] = 1.8 * scale
    ball.state.s = pt.constants.airborne

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball,),
    )

    return shot


_map = {
    "drop": drop,
    "simul": simul,
    "impulse_into": impulse_into,
    "bounce_over": bounce_over,
    "cushion_lift": cushion_lift,
    "friction_test": friction_test,
    "slip": slip,
    "airborne_circular_cushion": airborne_circular_cushion,
}


def main(name: str):
    shot = _map[name]()
    pt.simulate(shot, inplace=True)
    pt.show(shot)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("Series of airborne test demos.")
    ap.add_argument("--name", choices=list(_map.keys()) + ["all"])
    args = ap.parse_args()

    if args.name == "all":
        for name in _map:
            print(f"Running {name}...")
            main(name)
    else:
        main(args.name)
