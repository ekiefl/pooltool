#! /usr/bin/env python

import time

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
from pooltool.ai.action import Action as CueAction
from pooltool.ani.action import Action
from pooltool.ani.camera import cam
from pooltool.ani.globals import Global
from pooltool.ani.hud import hud
from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.evolution import simulate
from pooltool.system.datatypes import multisystem
from pooltool.system.render import visual


def ai_callback(action: CueAction) -> None:
    action.apply(multisystem.active.cue)
    visual.cue.set_render_state_as_object_state()
    hud.update_cue(multisystem.active.cue)
    print(action)


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

        if Global.game.active_player.is_ai:
            overlay_title = f"{Global.game.active_player.name} is thinking..."
            tasks.add(self.simulate_shot, "simulate_shot", taskChain="simulation")
        else:
            overlay_title = "Calculating shot..."
            tasks.add(self.simulate_shot, "simulate_shot", taskChain="simulation")

        self.shot_sim_overlay = GenericMenu(
            title=overlay_title,
            frame_color=(0, 0, 0, 0.4),
            title_pos=(0, 0, -0.2),
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
        if not tasks.has("simulate_shot"):
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

    def simulate_shot(self, task):
        if Global.game.active_player.is_ai:
            ai = Global.game.active_player.ai
            action = ai.decide(multisystem.active, Global.game, callback=ai_callback)
            ai.apply(multisystem.active, action)

            while task.time < 2.5:
                time.sleep(0.1)

        simulate(
            multisystem.active,
            continuous=True,
            inplace=True,
        )

        tasks.remove("simulate_shot")

        return task.done

    def calculate_ai_shot(self, task):
        """Calculate the AI's next move, then simulate"""

        simulate(
            multisystem.active,
            continuous=True,
            inplace=True,
        )

        tasks.remove("simulate_shot")

        return task.done
