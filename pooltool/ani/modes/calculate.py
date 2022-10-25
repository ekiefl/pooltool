#! /usr/bin/env python

import numpy as np

import pooltool as pt
import pooltool.ani as ani
from pooltool.ani.action import Action
from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import mouse


class CalculateMode(BaseMode):
    name = Mode.calculate
    keymap = {
        Action.move: False,
        Action.quit: False,
        Action.zoom: False,
        Action.show_help: False,
    }

    def enter(self):
        mouse.hide()
        mouse.relative()
        mouse.track()

        self.shot_sim_overlay = GenericMenu(
            title="Calculating shot...",
            frame_color=(0, 0, 0, 0.4),
            title_pos=(0, 0, -0.2),
        )

        self.add_task(self.run_simulation, "run_simulation", taskChain="simulation")

        self.task_action("escape", Action.quit, True)
        self.task_action("mouse1", Action.zoom, True)
        self.task_action("mouse1-up", Action.zoom, False)
        self.task_action("a", Action.aim, True)
        self.task_action("v", Action.move, True)
        self.task_action("v-up", Action.move, False)
        self.task_action("h", Action.show_help, True)

        self.add_task(self.calculate_view_task, "calculate_view_task")

    def exit(self):
        self.remove_task("calculate_view_task")
        self.shot_sim_overlay.hide()

    def calculate_view_task(self, task):
        if not self.has_task("run_simulation"):
            # simulation calculation is finished
            self.change_mode(Mode.shot, enter_kwargs=dict(init_animations=True))
        elif self.keymap[Action.zoom]:
            self.zoom_camera_calculate()
        elif self.keymap[Action.move]:
            self.move_camera_calculate()
        else:
            if task.time > ani.rotate_downtime:
                # Prevents shot follow through from moving camera
                self.rotate_camera_calculate()
            else:
                # Update mouse positions so there is not a big jump
                mouse.touch()

            if task.time > 0.25:
                self.shot_sim_overlay.show()

        return task.cont

    def run_simulation(self, task):
        """Run a pool simulation"""
        self.shots.active.simulate(continuize=False, quiet=False)
        self.game.process_shot(self.shots.active)

        self.remove_task("run_simulation")

        return task.done

    def zoom_camera_calculate(self):
        with mouse:
            s = -mouse.get_dy() * ani.zoom_sensitivity

        self.player_cam.node.setPos(
            pt.autils.multiply_cw(self.player_cam.node.getPos(), 1 - s)
        )

    def move_camera_calculate(self):
        with mouse:
            dxp, dyp = mouse.get_dx(), mouse.get_dy()

        h = self.player_cam.focus.getH() * np.pi / 180 + np.pi / 2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        self.player_cam.focus.setX(
            self.player_cam.focus.getX() + dx * ani.move_sensitivity
        )
        self.player_cam.focus.setY(
            self.player_cam.focus.getY() + dy * ani.move_sensitivity
        )

    def rotate_camera_calculate(self):
        fx, fy = ani.rotate_sensitivity_x, ani.rotate_sensitivity_y

        with mouse:
            alpha_x = self.player_cam.focus.getH() - fx * mouse.get_dx()
            alpha_y = max(
                min(0, self.player_cam.focus.getR() + fy * mouse.get_dy()), -90
            )

        self.player_cam.focus.setH(alpha_x)  # Move view laterally
        self.player_cam.focus.setR(alpha_y)  # Move view vertically
