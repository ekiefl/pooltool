import attrs
import numpy as np

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


def airborne_pocket_collision():
    ball = pt.Ball.create("cue")
    scale = 0.18
    ball.state.rvw = np.array(
        [
            [0.8, 0.2, 1.228575],
            [1.8 * scale, -1.8 * scale, 1.5],
            [0, 0, 0],
        ]
    )
    ball.state.s = pt.constants.airborne

    other = pt.Ball.create("1")
    scale = 0.27
    other.state.rvw = np.array(
        [
            [0.8, 0.2, 1],
            [1.8 * scale, -1.8 * scale, 1.5],
            [0, 0, 0],
        ]
    )
    other.state.s = pt.constants.airborne

    another = pt.Ball.create("2")
    scale = 0.11
    another.state.rvw = np.array(
        [
            [0.8, 0.2, 0.8],
            [1.8 * scale, -1.8 * scale, 1.5],
            [0, 0, 0],
        ]
    )
    another.state.s = pt.constants.airborne

    fast1 = pt.Ball.create("3")
    scale = 2
    fast1.state.rvw = np.array(
        [
            [0.3, 0.7, fast1.params.R * 7 / 5],
            [1.8 * scale, -1.8 * scale, 0.6],
            [0, 0, 0],
        ]
    )
    fast1.state.s = pt.constants.airborne

    fast2 = pt.Ball.create("4")
    scale = 2
    fast2.state.rvw = np.array(
        [
            [0.8, 0.2, fast2.params.R * 7 / 5],
            [1.8 * scale, -1.8 * scale, -2.0],
            [0, 0, 0],
        ]
    )
    fast2.state.s = pt.constants.airborne

    vertical = pt.Ball.create("5")
    vertical.state.rvw = np.array(
        [
            [1, -0.05, 0.75],
            [0, 0, 0],
            [0, 0, 0],
        ]
    )
    vertical.state.s = pt.constants.airborne

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=pt.Table.default(),
        balls=(ball, other, another, fast1, fast2, vertical),
    )
    shot.set_ballset(pt.objects.BallSet("pooltool_pocket"))

    return shot


def drop_on_cushion():
    table = pt.Table.default()

    # ball = pt.Ball.create("cue", xy=(table.w-0.01, table.l/4))
    # ball.state.rvw[0, 2] = 0.2
    # ball.state.rvw[1, 2] = 0.5
    # ball.state.s = pt.constants.airborne

    other = pt.Ball.create("other", xy=(table.w - 0.1, table.l / 4 + 0.1))
    other.state.rvw[0, 2] = 0.3
    other.state.rvw[1, 0] = 0.4
    other.state.s = pt.constants.airborne

    shot = pt.System(
        cue=pt.Cue(cue_ball_id="other"),
        table=table,
        balls=(other,),
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
    "airborne_pocket_collision": airborne_pocket_collision,
    "drop_on_cushion": drop_on_cushion,
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
