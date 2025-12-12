#! /usr/bin/env python
import logging
import math

import attrs
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from numpy.typing import NDArray

import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallParams
from pooltool.objects.table.components import LinearCushionSegment
from pooltool.physics.resolve.ball_cushion.core import CoreBallLCushionCollision
from pooltool.physics.resolve.ball_cushion.han_2005 import Han2005Linear
from pooltool.physics.resolve.ball_cushion.impulse_frictional_inelastic import (
    ImpulseFrictionalInelasticLinear,
)
from pooltool.physics.resolve.ball_cushion.mathavan_2010 import Mathavan2010Linear
from pooltool.physics.resolve.ball_cushion.stronge_compliant import (
    StrongeCompliantLinear,
)

pio.renderers.default = "browser"

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)


def natural_roll_spin_rate(ball_speed: float, R: float):
    return ball_speed / R


def gearing_sidespin(ball_speed: float, R: float, cut_angle: float):
    speed_tangent = ball_speed * math.sin(cut_angle)
    return -speed_tangent / R


def gearing_sidespin_factor(cut_angle: float):
    return math.sin(cut_angle)


def cue_strike_spin_rate(impulse_offset: float, ball_speed: float, R: float):
    """From impulse momentum equations"""
    return 2.5 * ball_speed * impulse_offset / R**2


def cue_strike_spin_rate_factor(impulse_offset: float, R: float) -> float:
    """spin_rate / natural_roll"""
    return 2.5 * impulse_offset / R


def cue_strike_spin_rate_factor_fractional_offset(
    impulse_offset_fraction: float,
) -> float:
    """spin_rate / natural_roll"""
    return 2.5 * impulse_offset_fraction


def cue_strike_spin_rate_factor_percent_english(
    percent_english: float, max_english_radius_fraction=0.5
):
    return cue_strike_spin_rate_factor_fractional_offset(
        (percent_english / 100) * max_english_radius_fraction
    )


@attrs.define(frozen=True)
class BallCushionCollisionExperimentConfig:
    model: CoreBallLCushionCollision
    params: BallParams
    xy_line_of_centers_angle_radians: float = 0.0


@attrs.define
class BallCushionCollisionExperiment:
    config: BallCushionCollisionExperimentConfig

    cushion: LinearCushionSegment = attrs.field(init=False)

    @cushion.default
    def __default_cushion(self):
        length = 2.0
        p1 = ptmath.coordinate_rotation(
            np.array([0.5 * length, 0.0, 0.0]),
            np.pi / 2 + self.config.xy_line_of_centers_angle_radians,
        )
        p2 = -p1
        height = 2.0 * self.config.params.R * 0.635
        p1[2] = height
        p2[2] = height
        cushion = LinearCushionSegment(id="dummy", p1=p1, p2=p2)
        return cushion

    cb_i: Ball = attrs.field(init=False)

    @cb_i.default
    def __default_cb(self):
        cb_i = Ball(id="cue", params=self.config.params)
        contact_position = (self.cushion.p2 + self.cushion.p1) / 2.0
        BallCushionCollisionExperiment.place_ball_next_to_position(
            cb_i,
            contact_position,
            angle_radians=self.config.xy_line_of_centers_angle_radians + math.pi,
        )
        return cb_i

    def setup(
        self,
        cb_speed: float,
        cb_topspin: float = 0.0,
        cb_sidespin: float = 0.0,
        cut_angle: float = 0.0,
    ):
        """
        note that cut_angle is defined with counter-clockwise positive
        """
        logger.debug(
            f"speed={cb_speed}, topspin={cb_topspin}, sidespin={cb_sidespin}, cut_angle={cut_angle} ({math.degrees(cut_angle)} deg)"
        )
        BallCushionCollisionExperiment.setup_ball_motion(
            self.cb_i,
            cb_speed,
            self.config.xy_line_of_centers_angle_radians - cut_angle,
            cb_topspin,
            cb_sidespin,
        )

    def result(self) -> tuple[Ball, LinearCushionSegment]:
        return self.config.model.resolve(self.cb_i, self.cushion, inplace=False)

    @staticmethod
    def place_ball_next_to_position(
        ball: Ball,
        position: NDArray[np.float64],
        separation: float = 0.0,
        angle_radians: float = 0.0,
    ):
        ball.state.rvw[0] = np.array(
            [position[0], position[1], ball.params.R]
        ) + ptmath.coordinate_rotation(
            np.array([separation + ball.params.R, 0.0, 0.0]), angle_radians
        )

    @staticmethod
    def setup_ball_motion(ball: Ball, speed: float, direction, topspin, sidespin):
        ball.state.rvw[1] = ptmath.coordinate_rotation(
            np.array([speed, 0.0, 0.0]), direction
        )
        ball.state.rvw[2] = ptmath.coordinate_rotation(
            np.array([0.0, topspin, sidespin]), direction
        )


def collision_results_versus_cut_angle(
    config: BallCushionCollisionExperimentConfig,
    cut_angles,
    speeds,
    topspin_factors=None,
    sidespin_factors=None,
):
    if topspin_factors is None:
        topspin_factors = [0.0]
    if sidespin_factors is None:
        sidespin_factors = [0.0]

    n_cut_angles = np.size(cut_angles)

    results = {}
    collision_experiment = BallCushionCollisionExperiment(config)

    for speed in speeds:
        natural_roll = natural_roll_spin_rate(speed, collision_experiment.cb_i.params.R)
        for topspin_factor in topspin_factors:
            topspin = topspin_factor * natural_roll
            for sidespin_factor in sidespin_factors:
                sidespin = sidespin_factor * natural_roll
                vel = np.empty((n_cut_angles, 3))
                avel = np.empty((n_cut_angles, 3))
                outgoing_vel = np.empty((n_cut_angles, 3))
                outgoing_avel = np.empty((n_cut_angles, 3))
                rebound_angle = np.empty(n_cut_angles)
                rebound_speed = np.empty(n_cut_angles)
                for i, cut_angle in enumerate(cut_angles):
                    sidespin = sidespin_factor * natural_roll

                    collision_experiment.setup(speed, topspin, sidespin, cut_angle)
                    vel[i] = collision_experiment.cb_i.vel
                    avel[i] = collision_experiment.cb_i.avel

                    cut_angle_check = (
                        -np.atan2(vel[i][1], vel[i][0])
                        + config.xy_line_of_centers_angle_radians
                    ) % (2 * math.pi)
                    assert abs(cut_angle - cut_angle_check) < 1e-2, (
                        f"cut_angle={cut_angle}, cut_angle_check={cut_angle_check}, config.xy_line_of_centers_angle_radians % 2*pi ={config.xy_line_of_centers_angle_radians % (2 * math.pi)}"
                    )

                    cb_f, _ = collision_experiment.result()
                    outgoing_vel[i] = ptmath.coordinate_rotation(
                        cb_f.vel, -config.xy_line_of_centers_angle_radians
                    )
                    outgoing_avel[i] = ptmath.coordinate_rotation(
                        cb_f.avel, -config.xy_line_of_centers_angle_radians
                    )
                    rebound_angle[i] = np.atan(outgoing_vel[i][1] / outgoing_vel[i][0])
                    rebound_speed[i] = ptmath.norm3d(outgoing_vel[i])

                results[(speed, topspin_factor, sidespin_factor)] = (
                    vel,
                    avel,
                    outgoing_vel,
                    outgoing_avel,
                    rebound_angle,
                    rebound_speed,
                )

    return results


N_CUT_ANGLES = 90


def plot_rebound_angle_vs_incident_angle(
    title: str, configs, speeds, topspin_factors=None, sidespin_factors=None
):
    cut_angles = np.linspace(0, np.pi / 2, N_CUT_ANGLES, endpoint=False)
    cut_angles_deg = np.rad2deg(cut_angles)

    fig = go.Figure()

    # Add 1:1 reference line
    fig.add_trace(
        go.Scatter(
            x=cut_angles_deg,
            y=cut_angles_deg,
            mode="lines",
            name="1:1 line (perfect reflection)",
            line=dict(color="gray", width=1, dash="dash"),
            opacity=0.7,
        )
    )

    base_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    for config_idx, config in enumerate(configs):
        results = collision_results_versus_cut_angle(
            config, cut_angles, speeds, topspin_factors, sidespin_factors
        )

        base_color = base_colors[config_idx % len(base_colors)]
        trajectory_idx = 0
        num_trajectories = len(results)

        for (speed, topspin_factor, sidespin_factor), (
            _,
            _,
            _,
            _,
            rebound_angles,
            _,
        ) in results.items():
            label = f"{config.model.model}: speed={speed:.3} m/s"
            if topspin_factors is not None:
                label += f", topspin_factor={topspin_factor:.2}"
            if sidespin_factors is not None:
                label += f", sidespin_factor={sidespin_factor:.2}"
            rebound_angles_deg = np.rad2deg(rebound_angles)

            opacity = 0.4 + 0.6 * trajectory_idx / max(1, num_trajectories - 1)

            fig.add_trace(
                go.Scatter(
                    x=cut_angles_deg,
                    y=rebound_angles_deg,
                    mode="lines",
                    name=label,
                    line=dict(color=base_color, width=2),
                    opacity=opacity,
                )
            )
            trajectory_idx += 1

    fig.update_layout(
        title=title,
        xaxis_title="incident angle (deg)",
        yaxis_title="rebound angle (deg)",
        showlegend=True,
    )

    fig.show(config={"displayModeBar": True})


def plot_rebound_speed_vs_incident_angle(
    title: str, configs, speeds, topspin_factors=None, sidespin_factors=None
):
    cut_angles = np.linspace(0, np.pi / 2, N_CUT_ANGLES, endpoint=False)
    cut_angles_deg = np.rad2deg(cut_angles)

    fig = go.Figure()
    base_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    for config_idx, config in enumerate(configs):
        results = collision_results_versus_cut_angle(
            config, cut_angles, speeds, topspin_factors, sidespin_factors
        )

        base_color = base_colors[config_idx % len(base_colors)]
        trajectory_idx = 0
        num_trajectories = len(results)

        for (speed, topspin_factor, sidespin_factor), (
            _,
            _,
            _,
            _,
            _,
            rebound_speeds,
        ) in results.items():
            label = f"{config.model.model}: speed={speed:.3} m/s"
            if topspin_factors is not None:
                label += f", topspin_factor={topspin_factor:.2}"
            if sidespin_factors is not None:
                label += f", sidespin_factor={sidespin_factor:.2}"

            opacity = 0.4 + 0.6 * trajectory_idx / max(1, num_trajectories - 1)

            fig.add_trace(
                go.Scatter(
                    x=cut_angles_deg,
                    y=rebound_speeds,
                    mode="lines",
                    name=label,
                    line=dict(color=base_color, width=2),
                    opacity=opacity,
                )
            )
            trajectory_idx += 1

    fig.update_layout(
        title=title,
        xaxis_title="incident angle (deg)",
        yaxis_title="rebound speed (m/s)",
        showlegend=True,
    )

    fig.show(config={"displayModeBar": True})


def main():
    models = [
        Han2005Linear(),
        Mathavan2010Linear(),
        ImpulseFrictionalInelasticLinear(),
        StrongeCompliantLinear(),
    ]

    ball_params = BallParams.default()
    configs = [
        BallCushionCollisionExperimentConfig(
            model=model, params=ball_params, xy_line_of_centers_angle_radians=100.0
        )
        for model in models
    ]

    speeds = np.linspace(0.5, 2.5, 5)
    topspins = np.linspace(-2, 2, 5)

    plot_rebound_angle_vs_incident_angle(
        "Stun-Shot Collision At Various Speeds\nRebound Angle vs. Incident Angle",
        configs,
        speeds,
    )

    plot_rebound_angle_vs_incident_angle(
        "Rolling-Ball Collision At Various Speeds\nRebound Angle vs. Incident Angle",
        configs,
        speeds,
        topspin_factors=[1.0],
    )

    plot_rebound_speed_vs_incident_angle(
        "Rolling-Ball Collision At Various Speeds\nRebound Speed vs. Incident Angle",
        configs,
        speeds,
        topspin_factors=[1.0],
    )

    plot_rebound_angle_vs_incident_angle(
        "1.0 m/s Collision At Various Topspins\nRebound Angle vs. Incident Angle",
        configs,
        [1.0],
        topspin_factors=topspins,
    )

    plot_rebound_speed_vs_incident_angle(
        "1.0 m/s Collision At Various Topspins\nRebound Speed vs. Incident Angle",
        configs,
        [1.0],
        topspin_factors=topspins,
    )

    plot_rebound_angle_vs_incident_angle(
        "1.0 m/s Rolling-Ball Collision With Various Sidespin\nRebound Angle vs. Incident Angle",
        configs,
        [1.0],
        topspin_factors=[1.0],
        sidespin_factors=topspins,
    )

    plot_rebound_speed_vs_incident_angle(
        "1.0 m/s Rolling-Ball Collision With Various Sidespin\nRebound Speed vs. Incident Angle",
        configs,
        [1.0],
        topspin_factors=[1.0],
        sidespin_factors=topspins,
    )


if __name__ == "__main__":
    main()
