import tkinter as tk
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import mplcursors
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from trajectory import ShotTrajectoryData

import pooltool as pt


class BilliardDataViewer:
    def __init__(
        self,
        real_shots: List[ShotTrajectoryData],
        simulated_shots: List[ShotTrajectoryData],
    ) -> None:
        """
        Initialize the BilliardDataViewer.

        Args:
            master: The parent tkinter window.
            real_shots: A list of real shot trajectories.
            simulated_shots: A list of simulated shot trajectories.
        """
        self.master = tk.Tk()
        self.master.title("Billiard Shot Viewer - Real vs Simulated")
        self.real_shots = real_shots
        self.simulated_shots = simulated_shots

        # Determine table dimensions from the first real shot or use default.
        self.table_width: float = real_shots[0].table_dims[0] if real_shots else 2.84

        self._init_ui()
        self._populate_shot_list()

        if self.real_shots:
            self.shot_listbox.selection_set(0)
            self._update_plot()

    def _init_ui(self) -> None:
        """Initialize UI components and event bindings."""
        # Frame for shot selection.
        self.listbox_frame = tk.Frame(self.master)
        self.listbox_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Listbox for selecting shots.
        self.shot_listbox = tk.Listbox(
            self.listbox_frame, selectmode=tk.BROWSE, height=20, width=30
        )
        self.shot_listbox.pack(side=tk.LEFT, fill=tk.Y)

        # Vertical scrollbar for the listbox.
        self.scrollbar = tk.Scrollbar(self.listbox_frame, orient=tk.VERTICAL)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.shot_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.shot_listbox.yview)

        self.shot_listbox.bind("<<ListboxSelect>>", self._on_shot_select)

        # Create the matplotlib figure and axes.
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self._setup_axes()

        # Embed the figure in the Tk window.
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Enable interactive cursor functionality.
        self.cursor = mplcursors.cursor(self.ax, hover=True)
        self.fig.canvas.mpl_connect("button_press_event", self._on_canvas_click)

    def _populate_shot_list(self) -> None:
        """Populate the shot listbox with shot descriptions."""
        self.shot_listbox.delete(0, tk.END)
        for i, shot in enumerate(self.real_shots):
            display_text = f"Shot {i}: Cue ball - {shot.cue}"
            self.shot_listbox.insert(tk.END, display_text)

    def _setup_axes(self) -> None:
        """Configure the plot axes."""
        self.ax.set_xlim(0, self.table_width)
        self.ax.set_ylim(0, self.table_width / 2)
        self.ax.set_xticks(np.linspace(0, self.table_width, 9))
        self.ax.set_yticks(np.linspace(0, self.table_width / 2, 5))
        self.ax.set_xticklabels([])
        self.ax.set_yticklabels([])
        self.ax.grid(True, linestyle="--", alpha=0.6)
        self.ax.set_facecolor("lightblue")

    def _on_shot_select(self, event: tk.Event) -> None:
        """Handle selection changes in the shot listbox."""
        self._update_plot()

    def _update_plot(self) -> None:
        """Update the plot to display the selected real and simulated shot."""
        selection = self.shot_listbox.curselection()
        if not selection:
            return

        shot_index = selection[-1]
        real_shot = self.real_shots[shot_index]
        sim_shot = self.simulated_shots[shot_index]

        self.ax.clear()
        self._setup_axes()
        self.ax.set_title(
            f"Shot {shot_index} - Real vs Simulated (Cue: {real_shot.cue})"
        )

        # Plot real trajectories as solid lines.
        for ball_id, traj in real_shot.balls.items():
            # Convert stored coordinates to original: x = table_width - stored_y, y = stored_x.
            plot_x = self.table_width - traj.y
            plot_y = traj.x
            self.ax.plot(
                plot_x,
                plot_y,
                color=ball_id,
                label=f"Real {ball_id}",
                linestyle="-",
            )
            initial_x = self.table_width - traj.y[0]
            initial_y = traj.x[0]
            circle = plt.Circle(
                (initial_x, initial_y),
                real_shot.radius,
                facecolor=ball_id,
                edgecolor="black",
                linewidth=1.5,
                fill=True,
                alpha=0.5,
            )
            self.ax.add_patch(circle)

        # Plot simulated trajectories as dashed lines.
        for ball_id, traj in sim_shot.balls.items():
            sim_plot_x = self.table_width - traj.y
            sim_plot_y = traj.x
            self.ax.plot(
                sim_plot_x,
                sim_plot_y,
                color=ball_id,
                label=f"Simulated {ball_id}",
                linestyle="--",
            )

        self.canvas.draw()

    def _on_canvas_click(self, event) -> None:
        """Deselect the shot list when clicking on the canvas."""
        if event.inaxes == self.ax:
            self.shot_listbox.selection_clear(0, tk.END)
            self._update_plot()
