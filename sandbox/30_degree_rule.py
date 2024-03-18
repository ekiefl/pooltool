import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

import pooltool as pt
import pooltool.constants as constants


def plot_ball_trajectory(ball: pt.Ball, fig: go.Figure = go.Figure()) -> go.Figure:
    """
    Plot the trajectory of the ball on a plane using the displacement vector (rvw[0]) with Plotly.

    Args:
        ball (Ball): The ball history object containing the ball states.
    """
    ball_history = ball.history_cts
    # Extract the x and y components of the displacement vector from each BallState
    x_coords = [state.rvw[0][0] for state in ball_history.states]
    y_coords = [state.rvw[0][1] for state in ball_history.states]

    # Create the plot
    fig.add_trace(
        go.Scatter(x=x_coords, y=y_coords, mode="lines+markers", name="Trajectory")
    )

    # Update plot layout
    fig.update_layout(
        title="Ball Trajectory",
        xaxis_title="X Position",
        yaxis_title="Y Position",
        showlegend=True,
        width=1000,
        height=1000,
    )

    return fig


def get_deflection_system(cut: float, V0: float = 2, b: float = 0.2) -> pt.System:
    ballset = pt.get_ballset("pooltool_pocket")
    cue_ball = pt.Ball.create("cue", xy=(98, 50), ballset=ballset)
    obj_ball = pt.Ball.create("2", xy=(97, 50), ballset=ballset)
    cue = pt.Cue(cue_ball_id="cue")
    table = pt.Table.from_table_specs(
        specs=pt.BilliardTableSpecs(
            l=100,
            w=100,
        )
    )  # Use a very large table to make sure the cue ball eventually is rolling
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


def _assert_cue_rolling_at_impact(system: pt.System) -> None:
    event = pt.filter_type(system.events, pt.EventType.BALL_BALL)[0]
    for agent in event.agents:
        if agent.id != "cue":
            continue
        assert agent.initial.state.s == constants.rolling, "Cue ball isn't rolling!"


def get_deflection_angle(cut: float, V0: float = 2, b: float = 0.2) -> float:
    system = get_deflection_system(cut=cut, V0=V0, b=b)

    # Get the ball-ball collision
    collision = pt.filter_type(system.events, pt.EventType.BALL_BALL)[0]

    # Get the velocity of the cue right before impact
    for agent in collision.agents:
        if agent.id == "cue":
            break
    cue_velocity_pre_collision = agent.initial.state.rvw[1]

    # Get event when object ball transitions from sliding to rolling
    sliding_to_rolling = pt.filter_events(
        system.events,
        pt.by_time(collision.time, after=True),
        pt.by_ball("cue"),
        pt.by_type(pt.EventType.SLIDING_ROLLING),
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
