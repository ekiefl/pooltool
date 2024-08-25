#! /usr/bin/env python

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.camera import cam
from pooltool.ani.globals import Global
from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.evolution import simulate
from pooltool.system.datatypes import System, multisystem


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

        tasks.add(
            self.run_simulation,
            "run_simulation",
            extraArgs=[multisystem.active],
            taskChain="simulation",
            appendTask=True,
        )

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
                Mode.shot, enter_kwargs=dict(build_animations=True)
            )
        elif self.keymap[Action.zoom]:
            cam.zoom_via_mouse()
        elif self.keymap[Action.move]:
            cam.move_fixation_via_mouse()
        else:
            if task.time < ani.rotate_downtime:
                # This catch helps prevent the shot follow through from moving the
                # camera, which is annoying and no one would want. So instead of
                # rotating the camera, we just touch the mouse so there is not a big
                # jump the next time the camera is truly rotated
                mouse.touch()
            else:
                cam.rotate_via_mouse()

            if task.time > 0.25:
                self.shot_sim_overlay.show()

        return task.cont

    def run_simulation(self, system: System, task):
        """Run a pool simulation"""

        simulate(
            system,
            continuous=True,
            inplace=True,
        )

        tasks.remove("run_simulation")

        return task.done
