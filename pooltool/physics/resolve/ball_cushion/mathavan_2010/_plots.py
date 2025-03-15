"""Plotting utilities for the Mathavan 2010 cushion collision model.

This module exists only to visually inspect the Mathavan model and compare the results
to the figures in the Mathavan paper.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator

from pooltool.physics.resolve.ball_cushion.mathavan_2010.model import solve_paper


@dataclass
class _BallParameters:
    """Parameters used in paper"""

    mass: float = 0.1406  # kg
    radius: float = 0.02625  # m
    h: float = 0.03675
    restitution: float = 0.98  # coefficient of restitution
    table_friction: float = 0.212  # sliding friction coefficient between ball and table
    cushion_friction: float = (
        0.14  # sliding friction coefficient between ball and cushion
    )


@dataclass
class _SpinConfig:
    k_values: List[float]  # Spin multipliers
    labels: List[str]  # Labels for plot legend
    colors: List[str]  # Colors for plot lines


@dataclass
class _SubplotConfig:
    ax: Axes  # Matplotlib axes object
    title: str  # Plot title
    ylabel: str  # Y-axis label
    data: np.ndarray  # Plot data
    spin_config: _SpinConfig  # Spin configuration


def _calculate_rebound_values(
    vx: float, vy: float, with_sidespin: bool = False
) -> Tuple[float, float]:
    """Calculate rebound speed and angle from velocity components"""
    v_rebound = np.sqrt(vx**2 + vy**2)

    if with_sidespin and vx < 0:
        rebound_angle = 180 - np.degrees(np.arctan2(abs(vy), abs(vx)))
    else:
        rebound_angle = np.degrees(np.arctan2(abs(vy), abs(vx)))

    return v_rebound, rebound_angle


def _run_simulations(
    k_values: List[float],
    incident_angles: np.ndarray,
    initial_speed: float,
    ball_params: _BallParameters,
    with_sidespin: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    """Run Mathavan model simulations for different k values and incident angles.

    Args:
        k_values: Array of k values for topspin/sidespin scaling factors
        incident_angles: Array of incident angles in radians
        initial_speed: Initial velocity magnitude (m/s)
        ball_params: Physical parameters of the ball
        with_sidespin: If True, use k values for sidespin with rolling topspin.
            If False, use k values for topspin with no sidespin. Defaults to False.

    Returns:
        A tuple containing arrays of (rebound_speeds, rebound_angles)
    """
    # Initialize result arrays
    rebound_speeds = np.zeros((len(k_values), len(incident_angles)))
    rebound_angles = np.zeros((len(k_values), len(incident_angles)))

    # Extract ball parameters
    M = ball_params.mass
    R = ball_params.radius
    h = ball_params.h
    ee = ball_params.restitution
    mu_s = ball_params.table_friction
    mu_w = ball_params.cushion_friction
    V_0 = initial_speed

    # Run simulations for each k value and incident angle
    for k_idx, k in enumerate(k_values):
        for angle_idx, alpha in enumerate(incident_angles):
            # Set spin parameters based on simulation type
            if with_sidespin:
                omega0T = V_0 / R  # Rolling topspin
                omega0S = k * V_0 / R  # Variable sidespin
            else:
                omega0T = k * V_0 / R  # Variable topspin
                omega0S = 0.0  # No sidespin

            # Run simulation and get final velocities
            vx, vy, _, _, _ = solve_paper(
                M, R, h, ee, mu_s, mu_w, V_0, alpha, omega0S, omega0T
            )

            v_rebound, rebound_angle = _calculate_rebound_values(vx, vy, with_sidespin)
            rebound_speeds[k_idx, angle_idx] = v_rebound
            rebound_angles[k_idx, angle_idx] = rebound_angle

    return rebound_speeds, rebound_angles


def _setup_subplot(config: _SubplotConfig, x_data: np.ndarray) -> None:
    ax = config.ax
    spin_config = config.spin_config

    for k_idx, k in enumerate(spin_config.k_values):
        ax.plot(
            x_data,
            config.data[k_idx],
            color=spin_config.colors[k_idx],
            label=spin_config.labels[k_idx],
            linewidth=1.5,
        )

    ax.set_title(config.title)
    ax.set_xlabel("Incident Angle (degrees)")
    ax.set_ylabel(config.ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_xlim(0, 90)
    ax.xaxis.set_major_locator(MultipleLocator(10))


def _generate_model_behavior_plots(
    ball_params: Optional[_BallParameters] = None,
    initial_speed: float = 1.0,
    angle_count: int = 50,
    figsize: Tuple[float, float] = (12, 10),
) -> Tuple[Figure, np.ndarray]:
    """Generate visualization plots demonstrating the Mathavan model behavior.

    Creates plots showing model behavior under various conditions of incident angles,
    topspin, and sidespin. The result is a 2x2 grid of plots showing:
    - Topspin: Incident Angle vs. Rebound Speed
    - Topspin: Incident Angle vs. Rebound Angle
    - Sidespin: Incident Angle vs. Rebound Speed
    - Sidespin: Incident Angle vs. Rebound Angle

    Args:
        ball_params: Physical parameters of the ball. If None, uses default parameters.
            Defaults to None.
        initial_speed: Initial velocity magnitude (m/s). Defaults to 1.0.
        angle_count: Number of incident angles to sample between 0.1 and 89.9 degrees.
            Defaults to 50.
        figsize: Figure size in inches. Defaults to (12, 10).

    Returns:
        A tuple containing (figure, axes)
    """
    if ball_params is None:
        ball_params = _BallParameters()

    incident_angles = np.radians(np.linspace(0.1, 89.9, angle_count))
    incident_angles_deg = np.degrees(incident_angles)

    topspin_config = _SpinConfig(
        k_values=[-1, 0, 1, 2],
        labels=["k = -1", "k = 0", "k = 1", "k = 2"],
        colors=["blue", "green", "red", "purple"],
    )

    sidespin_config = _SpinConfig(
        k_values=[-2, -1, 0, 1, 2],
        labels=["k = -2", "k = -1", "k = 0", "k = 1", "k = 2"],
        colors=["brown", "blue", "green", "red", "purple"],
    )

    rebound_speeds, rebound_angles = _run_simulations(
        topspin_config.k_values,
        incident_angles,
        initial_speed,
        ball_params,
        with_sidespin=False,
    )

    sidespin_rebound_speeds, sidespin_rebound_angles = _run_simulations(
        sidespin_config.k_values,
        incident_angles,
        initial_speed,
        ball_params,
        with_sidespin=True,
    )

    fig, axes = plt.subplots(2, 2, figsize=figsize)

    subplot_configs = [
        _SubplotConfig(
            ax=axes[0, 0],
            title="(a) Topspin: Incident Angle vs. Rebound Speed",
            ylabel="Rebound Speed (m/s)",
            data=rebound_speeds,
            spin_config=topspin_config,
        ),
        _SubplotConfig(
            ax=axes[0, 1],
            title="(b) Topspin: Incident Angle vs. Rebound Angle",
            ylabel="Rebound Angle (degrees)",
            data=rebound_angles,
            spin_config=topspin_config,
        ),
        _SubplotConfig(
            ax=axes[1, 0],
            title="(c) Sidespin: Incident Angle vs. Rebound Speed",
            ylabel="Rebound Speed (m/s)",
            data=sidespin_rebound_speeds,
            spin_config=sidespin_config,
        ),
        _SubplotConfig(
            ax=axes[1, 1],
            title="(d) Sidespin: Incident Angle vs. Rebound Angle",
            ylabel="Rebound Angle (degrees)",
            data=sidespin_rebound_angles,
            spin_config=sidespin_config,
        ),
    ]

    for config in subplot_configs:
        _setup_subplot(config, incident_angles_deg)

    plt.tight_layout()
    return fig, axes


if __name__ == "__main__":
    fig, _ = _generate_model_behavior_plots()
    plt.show()
