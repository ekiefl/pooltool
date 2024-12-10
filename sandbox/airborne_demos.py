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
    ball.state.s = pt.constants.sliding

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
    ball.state.rvw[1, 0] = 2
    ball.state.s = pt.constants.sliding

    other = pt.Ball.create("other", xy=(0.7, 0.42))
    other.state.rvw[1, 0] = 1.8
    other.state.s = pt.constants.sliding

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball, other),
    )

    return shot


def cushion_lift():
    ball = pt.Ball.create("cue", xy=(0.7, 0.5))
    ball.state.rvw[1, 0] = 4
    ball.state.s = pt.constants.sliding

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
}


def main(args):
    shot = _map[args.name]()
    pt.simulate(shot, inplace=True)
    pt.show(shot)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("Series of airborne test demos.")
    ap.add_argument("--name", choices=_map.keys())
    args = ap.parse_args()
    main(args)
