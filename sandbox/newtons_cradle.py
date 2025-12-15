import pooltool as pt
from pooltool.evolution.event_based.introspection import simulate_with_snapshots

table = pt.Table.default()
ball_radius = pt.BallParams.default().R

balls = [
    pt.Ball.create(
        str(i + 1),
        xy=(0.5 * table.w, 0.4 * table.l + 2 * i * ball_radius),
        ballset=pt.objects.BallSet("pooltool_pocket"),
    )
    for i in range(3)
]

balls.append(
    pt.Ball.create(
        "cue",
        xy=(0.5 * table.w, 0.1 * table.l),
        ballset=pt.objects.BallSet("pooltool_pocket"),
    )
)

system = pt.System(
    balls=balls,
    table=table,
    cue=pt.Cue.default(),
)

engine = pt.physics.PhysicsEngine()
system.strike(V0=2, phi=pt.aim.at_ball(system, "1", cut=0))
system, snapshots = simulate_with_snapshots(system)
