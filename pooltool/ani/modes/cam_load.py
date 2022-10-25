#! /usr/bin/env python

from direct.gui.DirectGui import DGG

from pooltool.ani.action import Action
from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import mouse


class CamLoadMode(BaseMode):
    name = Mode.cam_load
    keymap = {
        Action.quit: False,
        Action.cam_load: True,
    }

    def enter(self):
        if self.last_mode == Mode.aim:
            # FIXME Justification for this lie?
            self.last_mode = Mode.view

        mouse.show()
        mouse.absolute()
        mouse.track()
        self.selection = None

        self.task_action("escape", Action.quit, True)
        self.task_action("2", Action.cam_load, True)
        self.task_action("2-up", Action.cam_load, False)

        self.render_camera_load_buttons()
        self.add_task(self.cam_load_task, "cam_load_task")

    def render_camera_load_buttons(self):
        self.cam_load_slots = GenericMenu(
            title="Release key with moused hovered over desired save slot",
            frame_color=(0, 0, 0, 0.2),
            title_pos=(0, 0, 0.45),
        )

        pos = -1.2
        for slot in range(1, 10):
            exists = True if f"save_{slot}" in self.player_cam.states else False
            button = self.cam_load_slots.add_button(
                text=(f"{slot}", f"{slot}", "load" if exists else "empty", f"{slot}"),
                command=lambda: None,
                scale=0.1,
                text_scale=0.6,
                frameSize=(-1.2, 1.2, -1.2, 1.2),
                frameColor=(0.3, 0.6, 0.6, 1.0) if exists else (0.8, 0.8, 0.8, 1.0),
            )
            button.setPos((pos, 0, 0.25))
            button.bind(DGG.WITHIN, self.update_load_selection, extraArgs=[slot])
            button.bind(DGG.WITHOUT, self.update_load_selection, extraArgs=[None])
            pos += 0.3

        self.cam_load_slots.show()

    def update_load_selection(self, state, coords):
        self.selection = state

    def exit(self):
        if self.selection:
            self.player_cam.load_state(
                name=f"save_{self.selection}", ok_if_not_exists=True
            )

        self.remove_task("cam_load_task")
        mouse.touch()
        self.cam_load_slots.hide()

    def cam_load_task(self, task):
        if not self.keymap[Action.cam_load]:
            enter_kwargs = (
                dict(load_prev_cam=True) if self.last_mode == Mode.aim else dict()
            )
            self.change_mode(self.last_mode, enter_kwargs=enter_kwargs)

        return task.cont
