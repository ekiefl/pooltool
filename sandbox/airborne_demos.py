import attrs

import pooltool as pt


def drop():
    ball = pt.Ball.create("cue", xy=(0.5, 0.5))
    ball.state.rvw[0, 2] = 0.3
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


_map = {
    "drop": drop,
    "simul": simul,
    "impulse_into": impulse_into,
    "slip": slip,
}


def main(args):
    shot = _map[args.name]()
    pt.simulate(shot, inplace=True)
    pt.show(shot)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("Series of airborne test demos.")
    ap.add_argument("--name")
    args = ap.parse_args()
    main(args)
