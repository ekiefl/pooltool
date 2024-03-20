"""This script validates the 30-degree rule proposed by Dr. Dave Billiards

For more information about the 30-degree rule, see https://billiards.colostate.edu/faq/30-90-rules/30-degree-rule/
"""

import numpy as np
import pandas as pd
import plotly.express as px

import pooltool as pt
import pooltool.constants as constants


def _assert_cue_rolling_at_impact(system: pt.System) -> None:
    event = pt.events.filter_type(system.events, pt.EventType.BALL_BALL)[0]
    for agent in event.agents:
        if agent.id != "cue":
            continue
        assert agent.initial.state.s == constants.rolling, "Cue ball isn't rolling!"


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


if __name__ == "__main__":
    cut_angles = np.linspace(5, 85, 50)
    V0s = np.arange(0.5, 3, 0.2).round(2)
    deflection_angles_df = pd.DataFrame(
        [
            [
                1 - np.sin(np.deg2rad(cut)),
                get_deflection_angle(cut=cut, V0=V0, b=0.8),
                V0,
            ]
            for cut in cut_angles
            for V0 in V0s
        ],
        columns=["fullness", "deflection_angle", "v0"],
    )
    fig = px.line(
        deflection_angles_df,
        x="fullness",
        y="deflection_angle",
        color="v0",
        title="Deflection angles",
    )
    fig.show()
