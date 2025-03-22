from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

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


def plot_linear_fits(
    traj: ShotTrajectoryData,
    fits: Dict[str, List[Any]],
    plot_size: Tuple[int, int] = (12, 10),
) -> None:
    """Plot the linear fits of ball trajectories.

    Args:
        traj: Shot trajectory data
        fits: Linear segment fits from fit_all_trajectories
        plot_size: Figure size (width, height) in inches
    """
    fig, ax = plt.subplots(figsize=plot_size)

    # Set up the plot
    table_l, table_w = traj.table_dims
    padding = 0.1

    # Configure plot limits
    ax.set_xlim(0 - padding, table_w + padding)
    ax.set_ylim(0 - padding, table_l + padding)
    ax.set_aspect("equal")

    # Add table outline
    table_outline = plt.Rectangle(
        (0, 0), table_w, table_l, fill=False, edgecolor="brown", linewidth=2
    )
    ax.add_patch(table_outline)

    # Basic plot styling
    ax.grid(True, linestyle="--", alpha=0.7)
    ax.set_xlabel("X position (m)")
    ax.set_ylabel("Y position (m)")
    ax.set_title("Linear Segment Fits of Ball Trajectories")

    # Base colors for different balls
    base_color_map = {
        "white": ["darkgray", "dimgray"],
        "yellow": ["gold", "orange"],
        "red": ["red", "darkred"],
        # Default colors for any other balls
        "_default": ["royalblue", "navy"],
    }

    # Plot actual trajectories with a single transparent line
    for ball_id, ball_traj in traj.balls.items():
        # Choose color based on ball type but make it transparent
        base_color = base_color_map.get(ball_id, base_color_map["_default"])[0]
        ax.plot(
            ball_traj.x,
            ball_traj.y,
            color=base_color,
            alpha=0.3,
            linewidth=1.5,
            linestyle="-",
            label=f"{ball_id} (actual)",
        )

    # Plot all linear fits with alternating colors
    for ball_id, ball_segments in fits.items():
        # Get alternating colors for this ball
        colors = base_color_map.get(ball_id, base_color_map["_default"])

        # No need to add ball ID to legend again, it's added with actual trajectory

        # Plot each linear fit with alternating colors
        for i, segment in enumerate(ball_segments):
            # Alternate colors for consecutive segments
            color = colors[i % len(colors)]

            # Create line points from the linear fit equation
            t_vals = np.linspace(segment.t_start, segment.t_end, 100)

            # Calculate points using velocity vector
            # p = p0 + v*t
            start_x, start_y = segment.start_pos
            vx, vy = segment.velocity

            # Calculate points along the fitted line
            x_fit = start_x + vx * (t_vals - segment.t_start)
            y_fit = start_y + vy * (t_vals - segment.t_start)

            # Plot the actual linear fit
            ax.plot(
                x_fit,
                y_fit,
                color=color,
                linewidth=2,
                label=f"{ball_id} fit {i+1}"
                if i < 2
                else "",  # Only label first two segments to avoid cluttering
            )

            # Mark segment endpoints
            ax.plot(
                segment.start_pos[0],
                segment.start_pos[1],
                "o",
                color=color,
                markersize=6,
            )
            ax.plot(
                segment.end_pos[0], segment.end_pos[1], "s", color=color, markersize=6
            )

    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    unique_labels = dict(zip(labels, handles))
    ax.legend(unique_labels.values(), unique_labels.keys(), loc="upper right")

    plt.tight_layout()
    plt.show()


def visualize_collision(
    shot_data: ShotTrajectoryData,
    collision: Any,  # Using Any to avoid circular import
    time_window: float = 0.1,
) -> None:
    """Visualize a collision event using matplotlib.

    Parameters
    ----------
    shot_data : ShotTrajectoryData
        The shot trajectory data
    collision : Any (CollisionEvent)
        The collision event to visualize with attributes:
        ball1, ball2, time, position1, position2, velocity1_before,
        velocity2_before, velocity1_after, velocity2_after
    time_window : float, optional
        Time window around the collision to show (seconds)
    """
    collision_time = collision.time
    ball1_id = collision.ball1
    ball2_id = collision.ball2

    # Get ball trajectories
    ball1 = shot_data.balls[ball1_id]
    ball2 = shot_data.balls[ball2_id]

    # Find time window indices
    start_time = max(0, collision_time - time_window)
    end_time = collision_time + time_window

    time_mask1 = (ball1.t >= start_time) & (ball1.t <= end_time)
    time_mask2 = (ball2.t >= start_time) & (ball2.t <= end_time)

    # Set up the figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Map ball IDs to their actual colors, same as in plot_trajectories
    color_map = {
        "white": "silver",  # Use silver instead of white for better visibility
        "yellow": "gold",
        "red": "red",
    }

    # Get colors for each ball
    color1 = color_map.get(ball1_id, "blue")
    color2 = color_map.get(ball2_id, "green")

    # Plot trajectories with proper colors
    ax.plot(
        ball1.x[time_mask1],
        ball1.y[time_mask1],
        color=color1,
        linewidth=1.5,
        label=f"Ball {ball1_id}",
    )
    ax.plot(
        ball2.x[time_mask2],
        ball2.y[time_mask2],
        color=color2,
        linewidth=1.5,
        label=f"Ball {ball2_id}",
    )

    # Mark collision point
    ax.scatter(
        *collision.position1,
        color=color1,
        s=100,
        marker="o",
        edgecolors="black",
        zorder=10,
    )
    ax.scatter(
        *collision.position2,
        color=color2,
        s=100,
        marker="o",
        edgecolors="black",
        zorder=10,
    )

    # Draw ball at collision time with actual size
    ball_radius = shot_data.radius

    circle1 = plt.Circle(
        collision.position1, ball_radius, fill=True, alpha=0.3, color=color1
    )
    circle2 = plt.Circle(
        collision.position2, ball_radius, fill=True, alpha=0.3, color=color2
    )

    ax.add_patch(circle1)
    ax.add_patch(circle2)

    # Add table outline for reference
    table_l, table_w = shot_data.table_dims
    padding = 0.1

    # Configure plot limits
    ax.set_xlim(0 - padding, table_w + padding)
    ax.set_ylim(0 - padding, table_l + padding)

    # Add table outline
    table_outline = plt.Rectangle(
        (0, 0), table_w, table_l, fill=False, edgecolor="brown", linewidth=2
    )
    ax.add_patch(table_outline)

    # Add velocity vectors
    scale = 0.1  # Scale factor for velocity arrows

    # Before collision velocity
    ax.arrow(
        collision.position1[0],
        collision.position1[1],
        scale * collision.velocity1_before[0],
        scale * collision.velocity1_before[1],
        color=color1,
        width=0.005,
        head_width=0.02,
        head_length=0.03,
        length_includes_head=True,
        label="Before",
    )

    ax.arrow(
        collision.position2[0],
        collision.position2[1],
        scale * collision.velocity2_before[0],
        scale * collision.velocity2_before[1],
        color=color2,
        width=0.005,
        head_width=0.02,
        head_length=0.03,
        length_includes_head=True,
    )

    # After collision velocity
    ax.arrow(
        collision.position1[0],
        collision.position1[1],
        scale * collision.velocity1_after[0],
        scale * collision.velocity1_after[1],
        color=color1,
        width=0.005,
        head_width=0.02,
        head_length=0.03,
        length_includes_head=True,
        alpha=0.5,
        linestyle="dashed",
        label="After",
    )

    ax.arrow(
        collision.position2[0],
        collision.position2[1],
        scale * collision.velocity2_after[0],
        scale * collision.velocity2_after[1],
        color=color2,
        width=0.005,
        head_width=0.02,
        head_length=0.03,
        length_includes_head=True,
        alpha=0.5,
        linestyle="dashed",
    )

    # Set axis properties
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.7)
    ax.set_title(f"Ball-Ball Collision at t={collision_time:.3f}s")
    ax.set_xlabel("X position (m)")
    ax.set_ylabel("Y position (m)")

    # Handle legend with duplicates removed
    handles, labels = ax.get_legend_handles_labels()
    unique_labels = dict(zip(labels, handles))
    ax.legend(unique_labels.values(), unique_labels.keys(), loc="upper right")

    plt.tight_layout()
    plt.show()
