# %% [markdown]
# # The 30 Degree Rule
#
# The 30 degree rule states that the cue ball, when colliding with a ball over a wide range of cut angles, will be deflected roughly 30 degrees from it's initial course after the collision. In this sense, it is more of a *rule of thumb* used by pool players to improve their game, rather than a truism of pool physics.
#
# In this example, we will setup simulations that test the 30 degree rule and some of the physics equations defined by [Dr. Dave Billiards](https://drdavebilliards.com/).
#
# ## Assumptions
#
# We will use the default pooltool physics, which assume perfectly elastic and frictionless ball-ball collisions. Read more [here](https://ekiefl.github.io/2020/04/24/pooltool-theory/#section-ii-ball-ball-interactions).
#
# ## Definitions
#
# **The rule, stated in full:***
#
# > The 30° rule states that for a rolling-CB shot, over a wide range of cut angles, between a 1/4-ball hit (49 degree cut) and 3/4-ball hit (14 degree cut), the CB will deflect or carom off by very close to 30° (the “natural angle“) from its original direction after hitting the OB. If you want to be more precise, the angle is a little more (about 34°) closer to a 1/2-ball hit and a little less (about 27°) closer to a 1/4-ball or 3/4-ball hit.
#
# *(source: https://billiards.colostate.edu/faq/30-90-rules/30-degree-rule/)*
#
# **Ball-hit fraction and cut angle**
#
# - Ball-hit fraction, $f$, describes the fraction of overlap between the cue ball and object ball, projected in the direction of the aiming line.
# - Cut angle, $\phi$, refers to the angle that the cue ball glances the object ball, where $0$ refers to a full ball hit (straight on), and $90$ refers to the lower bound of the thinnest hit possible.
#
# These two are visualized in this diagram, where $f = \text{ball overlap} / (2R)$:
#
# <img src="assets/30_degree_rule/diagram1.png" width="500px" />
#
# *(source: https://billiards.colostate.edu/technical_proofs/new/TP_A-23.pdf)*
#
# Establishing the relationship between these quantities is important, since the 30 degree rule makes reference to both cut angle *and* ball-hit fraction. One can calculate the ball-hit fraction from cut angle with the following equation:
#
# $$
# f(\phi) = 1 - \sin{\phi}
# $$

# %% [markdown]
# # Visualizing a single collision
#
# To start, we'll need to create a billiards system. That means defining a table, a cue stick, and a collection of balls.
#
# We'll start with a table. Since we don't want collisions with cushions to interfere with our trajectory, let's make an unrealistically large $5\text{m} \times 5\text{m}$  table.

# %%
import pooltool as pt

table_specs = pt.objects.BilliardTableSpecs(l=5, w=5)
table = pt.Table.from_table_specs(table_specs)

# %% [markdown]
# Next, we'll create two balls.

# %%
cue_ball = pt.Ball.create("cue", xy=(2.5, 2.0))
obj_ball = pt.Ball.create("obj", xy=(2.5, 3.0))

# %% [markdown]
# Next, we'll need a cue stick.

# %%
cue = pt.Cue(cue_ball_id="cue")

# %% [markdown]
# Finally, we'll need to wrap these objects up into a system. We'll call this our system *template*, with the intention of reusing it for many different shots.

# %%
system_template = pt.System(
    table=table,
    cue=cue,
    balls={"cue": cue_ball, "obj": obj_ball},
)

# %% [markdown]
# Let's set up a shot by aiming at the object ball with a cut angle of 30 degrees. There is a small clash in terminology here, because in pooltool, `phi` is an angle defined with respect to the table, not the cut angle:
#
# <img src="https://ekiefl.github.io/images/pooltool/pooltool-theory/table_coordinates.jpg" width="130px" />
#
# So in the function call below, `pt.aim.at_ball(system, "obj", cut=30)` returns the angle `phi` that the cue ball should be directed at such that a cut angle of 30 degrees with the object ball is achieved.

# %%
# Creates a deep copy of the template
system = system_template.copy()

phi = pt.aim.at_ball(system, "obj", cut=30)
system.cue.set_state(V0=3, phi=phi, b=0.2)

# %% [markdown]
# Now, we simulate the shot and "continuize" it so that we have coordinate data in $10\text{ms}$ timestep intervals.

# %%
pt.simulate(system, inplace=True)
pt.continuize(system, dt=0.01, inplace=True)

print(f"System simulated: {system.simulated}")

# %% [markdown]
# If you have a graphics card, you can immediately visualize this shot in 3D with
#
# ```python
# gui = pt.ShotViewer()
# gui.show(system)
# ```
#
# Since that can't be embedded into the documentation, we'll instead plot the trajectory of the cue ball by accessing it's historical states.

# %%
import plotly.express as px
import plotly.io as pio
pio.renderers.default = "sphinx_gallery"

cue_ball = system.balls["cue"]
history = cue_ball.history_cts
type(history)

# %% [markdown]
# You can read about the `BallHistory` state 

# %%
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio

import pooltool as pt
import pooltool.constants as constants

pio.renderers.default = "sphinx_gallery"


# %%
def _assert_cue_rolling_at_impact(system: pt.System) -> None:
    event = pt.events.filter_type(system.events, pt.EventType.BALL_BALL)[0]
    for agent in event.agents:
        if agent.id != "cue":
            continue
        assert agent.initial.state.s == constants.rolling, "Cue ball isn't rolling!"


# %%
def get_deflection_system(cut: float, V0: float = 2, b: float = 0.2) -> pt.System:
    ballset = pt.objects.get_ballset("pooltool_pocket")
    cue_ball = pt.Ball.create("cue", xy=(50, 50), ballset=ballset)
    obj_ball = pt.Ball.create("2", xy=(49, 50), ballset=ballset)
    cue = pt.Cue(cue_ball_id="cue")
    table = pt.Table.from_table_specs(
        specs=pt.objects.BilliardTableSpecs(
            l=100,
            w=100,
        )
    )
    system = pt.System(
        cue=cue,
        table=table,
        balls={"cue": cue_ball, "2": obj_ball},
    )
    system.strike(V0=V0, phi=pt.aim.at_ball(system, "2", cut=cut), b=b)

    # Evolve the shot
    _ = pt.simulate(system, inplace=True)

    # The cue ball must be rolling at impact
    _assert_cue_rolling_at_impact(system)

    return system


# %%
def get_deflection_angle(cut: float, V0: float = 2, b: float = 0.2) -> float:
    system = get_deflection_system(cut=cut, V0=V0, b=b)

    # Get the ball-ball collision
    collision = pt.events.filter_type(system.events, pt.EventType.BALL_BALL)[0]

    # Get the velocity of the cue right before impact
    for agent in collision.agents:
        if agent.id == "cue":
            break
    cue_velocity_pre_collision = agent.initial.state.rvw[1]

    # Get event when object ball transitions from sliding to rolling
    sliding_to_rolling = pt.events.filter_events(
        system.events,
        pt.events.by_time(collision.time, after=True),
        pt.events.by_ball("cue"),
        pt.events.by_type(pt.EventType.SLIDING_ROLLING),
    )[0]

    # Get the velocity of the cue after it is done sliding
    cue_velocity_post_slide = sliding_to_rolling.agents[0].final.state.rvw[1]

    return np.rad2deg(
        np.arccos(
            np.dot(
                pt.ptmath.unit_vector(cue_velocity_pre_collision),
                pt.ptmath.unit_vector(cue_velocity_post_slide),
            )
        )
    )

# %%

# %%
