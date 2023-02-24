"""Two balls, a cue, and a table"""
import numpy as np

import pooltool as pt


def rand_pos(table):
    params = pt.BallParams()
    return (
        np.random.uniform(params.R, table.w - params.R),
        np.random.uniform(params.R, table.l - params.R),
    )


# Create a 2-ball system (randomly placed balls)
table = pt.Table.pocket_table()
shot = pt.System(
    table=table,
    cue=pt.Cue(),
    balls={
        "cue": pt.Ball.create("cue", xy=rand_pos(table)),
        "1": pt.Ball.create("1", xy=rand_pos(table)),
    },
)

# The balls are not in motion, so there is no energy in the system. Let's change that...
assert shot.get_system_energy() == 0

# Let's set the cue-stick parameters. Let's strike the cue ball with a strike of 1.5m/s
# (V0), with bottom english (b), a bit of left spin (a), and a level cue (theta)
shot.cue.set_state(
    cue_ball_id="cue",
    V0=1.5,
    b=-0.1,
    a=0.2,
    theta=0,
)

# The direction of the shot (phi) is still the default of 0
assert shot.cue.phi == 0

# So let's Aim at the 1-ball, with a 30 degree cut to the left
shot.aim_for_best_pocket(ball_id="1")

# Now the direction is set!
assert shot.cue.phi != 0

# The energy of the system is still zero though, because we haven't struck the cue ball,
# we've only set the parameters that we would like to use.
assert shot.get_system_energy() == 0

# Let's strike the cue ball, giving the system some initial energy
shot.strike()
assert shot.get_system_energy() > 0

# The shot hasn't been simulated yet, so time is t=0
assert shot.t == 0

# Let's simulate the shot
pt.simulate(shot)

# The shot has been simulated. Here are the series of events that took place:
print(shot.events)

# We can visualize the shot like so (press r to replay):
interface = pt.ShotViewer()
interface.show(shot)
