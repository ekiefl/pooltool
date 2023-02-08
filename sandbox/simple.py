"""Two balls, a cue, and a table"""
import numpy as np
import pooltool as pt

# Create a system
from pooltool.constants import table_length, table_width, R
cx, cy = np.random.uniform(0, table_width - 2*R), np.random.uniform(0, table_length - 2*R)
bx, by = np.random.uniform(0, table_width - 2*R), np.random.uniform(0, table_length - 2*R)
shot = pt.System(
    table=pt.PocketTable(model_name="7_foot"),
    cue=pt.Cue(),
    balls={
        "cue": pt.Ball("cue", xyz=[cx, cy]),
        "1": pt.Ball("1", xyz=[bx, by]),
    },
)

# Let's make sure the balls are not overlapping:
assert not shot.is_balls_overlapping()

# The balls are not in motion, so there is no energy in the system. Let's change that...
assert shot.get_system_energy() == 0

# Let's set the cue-stick parameters. Let's strike the cue ball with a strike of 1.5m/s
# (V0), with bottom english (b), a bit of left spin (a), and a level cue (theta)
shot.cue.set_state(
    cueing_ball=shot.balls["cue"],
    V0=1.5,
    b=-0.1,
    a=0.2,
    theta=0,
)

# The direction of the shot (phi) is still the default of 0
assert shot.cue.phi == 0

# So let's Aim at the 1-ball, with a 30 degree cut to the left
target_ball = shot.balls['1']
shot.cue.aim_to_pot(target_ball, shot.table.pockets.values())

# Now the direction is set!
assert shot.cue.phi != 0

# The energy of the system is still zero though, because we haven't struck the cue ball,
# we've only set the parameters that we would like to use.
assert shot.get_system_energy() == 0

# Let's strike the cue ball, giving the system some initial energy
shot.cue.strike()
assert shot.get_system_energy() > 0

# The shot hasn't been simulated yet, so time doesn't exist
assert shot.t is None

# Let's simulate the shot
shot.simulate()

# The shot has been simulated. Here are the series of events that took place:
print(shot.events)

# We can visualize the shot like so (press r to replay):
interface = pt.ShotViewer()
interface.show(shot)

# Oh no! it's a scratch. Try avoiding the scratch by modifying the cue ball's spin in
# the code above
