"""
Collision Detection Script

This script detects collisions in ball trajectories by analyzing:
1. Direction changes (detecting sudden angle changes)
2. Proximity between balls and cushions
3. Velocity changes
"""

from typing import Tuple

import matplotlib.pyplot as plt

import pooltool as pt
from sandbox.recreate.trajectory import ShotTrajectoryData


def plot_trajectories(
    traj: ShotTrajectoryData,
    plot_size: Tuple[int, int] = (12, 10),
    padding: float = 0.1,
    line_width: float = 1.5,
    show_plot: bool = True,
) -> None:
    """Plot ball trajectories.

    Args:
        traj: Shot trajectory data containing all ball trajectories
        plot_size: Figure size (width, height) in inches
        padding: Padding around table boundary (meters)
        line_width: Width of trajectory lines
        dpi: DPI for saving the figure
        show_plot: Whether to display the plot interactively
    """
    # Create a figure for the trajectory plot
    fig, ax = plt.subplots(figsize=plot_size)

    # Set up the table boundary
    table_l, table_w = traj.table_dims

    # Configure plot limits and style
    ax.set_xlim(0 - padding, table_w + padding)
    ax.set_ylim(0 - padding, table_l + padding)
    ax.set_aspect("equal")

    # Add table outline for reference
    table_outline = plt.Rectangle(
        (0, 0),
        table_w,
        table_l,
        fill=False,
        edgecolor="brown",
        linewidth=2,
    )
    ax.add_patch(table_outline)

    # Add axes labels and grid
    ax.grid(True, linestyle="--", alpha=0.7)
    ax.set_xlabel("X position (width, m)")
    ax.set_ylabel("Y position (length, m)")
    ax.set_title("Ball Trajectories")

    # Map ball IDs to their actual colors
    color_map = {
        "white": "silver",  # Use silver instead of white for better visibility
        "yellow": "gold",
        "red": "red",
    }

    # Plot all trajectories
    for ball_id, ball_traj in traj.balls.items():
        color = color_map.get(ball_id, "blue")
        ax.plot(
            ball_traj.x, ball_traj.y, color=color, label=ball_id, linewidth=line_width
        )

    # Add legend
    ax.legend(loc="upper right")

    plt.tight_layout()

    if show_plot:
        plt.show()


def main():
    """Main function to load, analyze and visualize ball collisions."""
    # Load systems
    systems = [pt.System.load(f"shot{i}.msgpack") for i in range(1, 9)]

    noise_level: float = 0.005

    # Create trajectories without noise
    trajs_clean = [ShotTrajectoryData.from_simulated(system) for system in systems]

    # Create trajectories with noise to simulate experimental data
    trajs_noisy = [
        ShotTrajectoryData.from_simulated(
            system,
            noise_level=noise_level,
            random_seed=42 + i,  # Different seed for each trajectory
        )
        for i, system in enumerate(systems)
    ]

    print("\n=== Analysis with exp data ===")
    trajs_exp = pt.serialize.conversion.structure_from(
        "./20221225_2_Match_Ersin_Cemal.msgpack", list[ShotTrajectoryData]
    )
    for traj in trajs_exp:
        collisions_clean = plot_trajectories(
            traj=traj,
        )


if __name__ == "__main__":
    main()
