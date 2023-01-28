#! /usr/bin/env python

import numpy as np

import pooltool as pt
import pooltool.ani as ani
import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.camera import camera
from pooltool.ani.globals import Global
from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.error import SimulateError


class CalculateMode(BaseMode):
    name = Mode.calculate
    keymap = {
        Action.move: False,
        Action.quit: False,
        Action.zoom: False,
        Action.show_help: False,
    }

    def enter(self):
        mouse.mode(MouseMode.RELATIVE)

        self.shot_sim_overlay = GenericMenu(
            title="Calculating shot...",
            frame_color=(0, 0, 0, 0.4),
            title_pos=(0, 0, -0.2),
        )

        tasks.add(self.run_simulation, "run_simulation", taskChain="simulation")

        self.register_keymap_event("escape", Action.quit, True)
        self.register_keymap_event("mouse1", Action.zoom, True)
        self.register_keymap_event("mouse1-up", Action.zoom, False)
        self.register_keymap_event("a", Action.aim, True)
        self.register_keymap_event("v", Action.move, True)
        self.register_keymap_event("v-up", Action.move, False)
        self.register_keymap_event("h", Action.show_help, True)

        tasks.add(self.calculate_view_task, "calculate_view_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self):
        tasks.remove("calculate_view_task")
        tasks.remove("shared_task")

        self.shot_sim_overlay.hide()

    def calculate_view_task(self, task):
        if not tasks.has("run_simulation"):
            # simulation calculation is finished
            Global.mode_mgr.change_mode(
                Mode.shot, enter_kwargs=dict(init_animations=True)
            )
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

        try:
            Global.shots.active.simulate(
                continuize=False, quiet=False, raise_simulate_error=True
            )
        except SimulateError:
            # Failed to simulate shot. Return to aim mode. Not ideal but better than a
            # runtime error
            Global.mode_mgr.change_mode(Mode.aim)

        Global.game.process_shot(Global.shots.active)

        tasks.remove("run_simulation")

        return task.done

    def zoom_camera_calculate(self):
        with mouse:
            s = -mouse.get_dy() * ani.zoom_sensitivity

        camera.node.setPos(pt.autils.multiply_cw(camera.node.getPos(), 1 - s))

    def move_camera_calculate(self):
        with mouse:
            dxp, dyp = mouse.get_dx(), mouse.get_dy()

        h = camera.focus.getH() * np.pi / 180 + np.pi / 2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        camera.focus.setX(camera.focus.getX() + dx * ani.move_sensitivity)
        camera.focus.setY(camera.focus.getY() + dy * ani.move_sensitivity)

    def rotate_camera_calculate(self):
        fx, fy = ani.rotate_sensitivity_x, ani.rotate_sensitivity_y

        with mouse:
            alpha_x = camera.focus.getH() - fx * mouse.get_dx()
            alpha_y = max(min(0, camera.focus.getR() + fy * mouse.get_dy()), -90)

        camera.focus.setH(alpha_x)  # Move view laterally
        camera.focus.setR(alpha_y)  # Move view vertically
