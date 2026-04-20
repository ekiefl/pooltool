import math

import attrs
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallParams
from pooltool.physics.resolve.ball_ball.core import BallBallCollisionStrategy

pio.renderers.default = "browser"


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
class BallBallCollisionExperimentConfig:
    model: BallBallCollisionStrategy
    params: BallParams
    xy_line_of_centers_angle_radians: float = 0.0


@attrs.define
class BallBallCollisionExperiment:
    config: BallBallCollisionExperimentConfig

    ob_i: Ball = attrs.field(init=False)

    @ob_i.default
    def __default_ob(self):
        ob_i = Ball(id="object", params=self.config.params)
        ob_i.state.rvw[0] = np.array([0, 0, self.config.params.R])
        return ob_i

    cb_i: Ball = attrs.field(init=False)

    @cb_i.default
    def __default_cb(self):
        cb_i = Ball(id="cue", params=self.config.params)
        BallBallCollisionExperiment.place_ball_next_to(
            cb_i, self.ob_i, self.config.xy_line_of_centers_angle_radians + math.pi
        )
        return cb_i

    def setup(
        self,
        cb_speed: float,
        cb_topspin: float = 0.0,
        cb_sidespin: float = 0.0,
        cut_angle: float = 0.0,
    ):
        BallBallCollisionExperiment.setup_ball_motion(
            self.cb_i,
            cb_speed,
            self.config.xy_line_of_centers_angle_radians - cut_angle,
            cb_topspin,
            cb_sidespin,
        )

    def result(self):
        return self.config.model.resolve(self.cb_i, self.ob_i, inplace=False)

    @staticmethod
    def place_ball_next_to(
        ball: Ball, other_ball: Ball, angle: float, separation: float = 0.0
    ):
        ball.state.rvw[0] = other_ball.xyz + ptmath.coordinate_rotation(
            np.array([other_ball.params.R + separation + ball.params.R, 0, 0]), angle
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
    config: BallBallCollisionExperimentConfig,
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
    collision_experiment = BallBallCollisionExperiment(config)

    for speed in speeds:
        natural_roll = natural_roll_spin_rate(speed, collision_experiment.cb_i.params.R)
        for topspin_factor in topspin_factors:
            topspin = topspin_factor * natural_roll
            for sidespin_factor in sidespin_factors:
                sidespin = sidespin_factor * natural_roll
                vel = np.empty((n_cut_angles, 3))
                avel = np.empty((n_cut_angles, 3))
                induced_vel = np.empty((n_cut_angles, 3))
                induced_avel = np.empty((n_cut_angles, 3))
                throw_angles = np.empty(n_cut_angles)
                for i, cut_angle in enumerate(cut_angles):
                    collision_experiment.setup(speed, topspin, sidespin, cut_angle)
                    vel[i] = collision_experiment.cb_i.vel
                    avel[i] = collision_experiment.cb_i.avel

                    cb_f, ob_f = collision_experiment.result()

                    induced_vel[i] = ptmath.coordinate_rotation(
                        ob_f.vel, -config.xy_line_of_centers_angle_radians
                    )
                    induced_avel[i] = ptmath.coordinate_rotation(
                        ob_f.avel, -config.xy_line_of_centers_angle_radians
                    )
                    throw_angles[i] = -np.atan2(induced_vel[i, 1], induced_vel[i, 0])

                results[(speed, topspin_factor, sidespin_factor)] = (
                    vel,
                    avel,
                    induced_vel,
                    induced_avel,
                    throw_angles,
                )

    return results


def collision_results_versus_sidespin(
    config: BallBallCollisionExperimentConfig,
    sidespin_factors,
    speeds,
    topspin_factors=None,
    cut_angles=None,
):
    if topspin_factors is None:
        topspin_factors = [0.0]
    if cut_angles is None:
        cut_angles = [0.0]

    n_sidespins = np.size(sidespin_factors)

    results = {}
    collision_experiment = BallBallCollisionExperiment(config)

    for speed in speeds:
        natural_roll = natural_roll_spin_rate(speed, collision_experiment.cb_i.params.R)
        for topspin_factor in topspin_factors:
            topspin = topspin_factor * natural_roll
            for cut_angle in cut_angles:
                vel = np.empty((n_sidespins, 3))
                avel = np.empty((n_sidespins, 3))
                induced_vel = np.empty((n_sidespins, 3))
                induced_avel = np.empty((n_sidespins, 3))
                throw_angles = np.empty(n_sidespins)
                for i, sidespin_factor in enumerate(sidespin_factors):
                    sidespin = sidespin_factor * natural_roll
                    collision_experiment.setup(speed, topspin, sidespin, cut_angle)
                    vel[i] = collision_experiment.cb_i.vel
                    avel[i] = collision_experiment.cb_i.avel

                    cb_f, ob_f = collision_experiment.result()

                    induced_vel[i] = ptmath.coordinate_rotation(
                        ob_f.vel, -config.xy_line_of_centers_angle_radians
                    )
                    induced_avel[i] = ptmath.coordinate_rotation(
                        ob_f.avel, -config.xy_line_of_centers_angle_radians
                    )
                    throw_angles[i] = -np.atan2(induced_vel[i, 1], induced_vel[i, 0])

                results[(speed, topspin_factor, cut_angle)] = (
                    vel,
                    avel,
                    induced_vel,
                    induced_avel,
                    throw_angles,
                )

    return results


def plot_throw_vs_cut_angle(
    title: str, config, speeds, topspin_factors=None, sidespin_factors=None
):
    cut_angles = np.linspace(0, np.pi / 2, 90 * 2, endpoint=False)
    cut_angles_deg = np.rad2deg(cut_angles)

    results = collision_results_versus_cut_angle(
        config, cut_angles, speeds, topspin_factors, sidespin_factors
    )

    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title="cut angle (deg)",
        yaxis_title="throw angle (deg)",
        showlegend=True,
    )

    for (speed, topspin_factor, sidespin_factor), (
        _,
        _,
        _,
        _,
        throw_angles,
    ) in results.items():
        label = f"speed={speed:.3} m/s"
        if topspin_factors is not None:
            label += f", topspin_factor={topspin_factor}"
        if sidespin_factors is not None:
            label += f", sidespin_factor={sidespin_factor}"
        fig.add_trace(
            go.Scatter(
                x=cut_angles_deg,
                y=np.rad2deg(throw_angles),
                mode="lines",
                name=label,
            )
        )

    fig.show(config={"displayModeBar": True})


def plot_throw_vs_sidespin_factor(
    title: str, config, speeds, topspin_factors=None, cut_angles=None
):
    sidespin_factors = np.linspace(-1.25, 1.25, 125 * 2)

    results = collision_results_versus_sidespin(
        config, sidespin_factors, speeds, topspin_factors, cut_angles
    )

    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title="sidespin / natural roll",
        yaxis_title="throw angle (deg)",
        showlegend=True,
    )

    for (speed, topspin_factor, cut_angle), (
        _,
        _,
        _,
        _,
        throw_angles,
    ) in results.items():
        label = f"speed={speed:.3} m/s"
        if topspin_factors is not None:
            label += f", topspin_factor={topspin_factor}"
        if cut_angles is not None:
            cut_angle_deg = math.degrees(cut_angle)
            label += f", cut_angle={cut_angle_deg:.3} deg"
        fig.add_trace(
            go.Scatter(
                x=sidespin_factors,
                y=np.rad2deg(throw_angles),
                mode="lines",
                name=label,
            )
        )

    fig.show(config={"displayModeBar": True})


def plot_throw_vs_percent_sidespin(
    title: str,
    config,
    speeds,
    topspin_factors=None,
    cut_angles=None,
    min_sidespin_percentage=-100,
    max_sidespin_percentage=100,
    max_english_radius_fraction=0.5,
):
    sidespin_percentages = np.linspace(
        min_sidespin_percentage, max_sidespin_percentage, 100 * 2
    )
    sidespin_factors = np.array(
        [
            cue_strike_spin_rate_factor_percent_english(
                sidespin_percentage, max_english_radius_fraction
            )
            for sidespin_percentage in sidespin_percentages
        ]
    )

    results = collision_results_versus_sidespin(
        config, sidespin_factors, speeds, topspin_factors, cut_angles
    )

    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title="sidespin (% of max)",
        yaxis_title="throw angle (deg)",
        showlegend=True,
    )

    for (speed, topspin_factor, cut_angle), (
        _,
        _,
        _,
        _,
        throw_angles,
    ) in results.items():
        label = f"speed={speed:.3} m/s"
        if topspin_factors is not None:
            label += f", topspin_factor={topspin_factor}"
        if cut_angles is not None:
            cut_angle_deg = math.degrees(cut_angle)
            label += f", cut_angle={cut_angle_deg:.3} deg"
        fig.add_trace(
            go.Scatter(
                x=sidespin_percentages,
                y=np.rad2deg(throw_angles),
                mode="lines",
                name=label,
            )
        )

    fig.show(config={"displayModeBar": True})


def plot_sidespin_transfer_percentage_vs_percent_sidespin(
    title: str,
    config,
    speeds,
    topspin_factors=None,
    cut_angles=None,
    min_sidespin_percentage=-100,
    max_sidespin_percentage=100,
    max_english_radius_fraction=0.5,
):
    sidespin_percentages = np.linspace(
        min_sidespin_percentage, max_sidespin_percentage, 100 * 2
    )
    sidespin_factors = np.array(
        [
            cue_strike_spin_rate_factor_percent_english(
                sidespin_percentage, max_english_radius_fraction
            )
            for sidespin_percentage in sidespin_percentages
        ]
    )

    results = collision_results_versus_sidespin(
        config, sidespin_factors, speeds, topspin_factors, cut_angles
    )

    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title="sidespin (% of max)",
        yaxis_title="sidespin transfer (%)",
        showlegend=True,
    )

    for (speed, topspin_factor, cut_angle), (
        _,
        avels,
        _,
        induced_avels,
        _,
    ) in results.items():
        label = f"speed={speed:.3} m/s"
        if topspin_factors is not None:
            label += f", topspin_factor={topspin_factor}"
        if cut_angles is not None:
            cut_angle_deg = math.degrees(cut_angle)
            label += f", cut_angle={cut_angle_deg:.3} deg"
        sidespin_transfer_percentage = (
            np.divide(-induced_avels[:, 2], avels[:, 2]) * 100
        )
        fig.add_trace(
            go.Scatter(
                x=sidespin_percentages,
                y=sidespin_transfer_percentage,
                mode="lines",
                name=label,
            )
        )

    fig.show(config={"displayModeBar": True})


def plot_sidespin_transfer_effectiveness_vs_percent_sidespin(
    title: str,
    config,
    speeds,
    topspin_factors=None,
    cut_angles=None,
    min_sidespin_percentage=-100,
    max_sidespin_percentage=100,
    max_english_radius_fraction=0.5,
):
    sidespin_percentages = np.linspace(
        min_sidespin_percentage, max_sidespin_percentage, 100 * 2
    )
    sidespin_factors = np.array(
        [
            cue_strike_spin_rate_factor_percent_english(
                sidespin_percentage, max_english_radius_fraction
            )
            for sidespin_percentage in sidespin_percentages
        ]
    )

    results = collision_results_versus_sidespin(
        config, sidespin_factors, speeds, topspin_factors, cut_angles
    )

    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title="sidespin (% of max)",
        yaxis_title="spin transfer effectiveness (%)",
        showlegend=True,
    )

    for (speed, topspin_factor, cut_angle), (
        _,
        _,
        induced_vels,
        induced_avels,
        _,
    ) in results.items():
        label = f"speed={speed:.3} m/s"
        if topspin_factors is not None:
            label += f", topspin_factor={topspin_factor}"
        if cut_angles is not None:
            cut_angle_deg = math.degrees(cut_angle)
            label += f", cut_angle={cut_angle_deg:.3} deg"
        sidespin_transfer_effectiveness = 100 * np.array(
            [
                -induced_avels[i, 2]
                / natural_roll_spin_rate(
                    ptmath.norm3d(induced_vels[i]), config.params.R
                )
                for i in range(len(induced_vels))
            ]
        )
        fig.add_trace(
            go.Scatter(
                x=sidespin_percentages,
                y=sidespin_transfer_effectiveness,
                mode="lines",
                name=label,
            )
        )

    fig.show(config={"displayModeBar": True})
