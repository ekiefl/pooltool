#! /usr/bin/env python

from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes import Mode, action
from direct.gui.DirectGui import *

class CamSaveMode(Mode):
    keymap = {
        action.quit: False,
        action.cam_save: True,
    }


    def enter(self):
        self.mouse.show()
        self.mouse.absolute()
        self.mouse.track()
        self.selection = None

        self.task_action('escape', action.quit, True)
        self.task_action('1', action.cam_save, True)
        self.task_action('1-up', action.cam_save, False)

        self.render_camera_save_buttons()
        self.add_task(self.cam_save_task, 'cam_save_task')


    def render_camera_save_buttons(self):
        self.cam_save_slots = GenericMenu(
            title = "Release key with moused hovered over desired save slot",
            frame_color = (0,0,0,0.2),
            title_pos = (0,0,0.45),
        )

        pos = -1.2
        for slot in range(1, 10):
            exists = True if f'save_{slot}' in self.player_cam.states else False
            button = self.cam_save_slots.add_button(
                text = (f'{slot}', f'{slot}', 'replace' if exists else 'write', f'{slot}'),
                command = lambda: None,
                scale = 0.1,
                text_scale = 0.6,
                frameSize = (-1.2, 1.2, -1.2, 1.2),
                frameColor = (0.3, 0.6, 0.6, 1.0) if exists else (0.8, 0.8, 0.8, 1.0),
            )
            button.setPos((pos, 0, 0.25))
            button.bind(DGG.WITHIN, self.update_save_selection, extraArgs=[slot])
            button.bind(DGG.WITHOUT, self.update_save_selection, extraArgs=[None])
            pos += 0.3

        self.cam_save_slots.show()


    def update_save_selection(self, state, coords):
        self.selection = state


    def exit(self):
        if self.selection:
            self.player_cam.store_state(name=f'save_{self.selection}', overwrite=True)

        self.remove_task('cam_save_task')
        self.mouse.touch()
        self.cam_save_slots.hide()
        del self.selection


    def cam_save_task(self, task):
        if not self.keymap[action.cam_save]:
            enter_kwargs = dict(load_prev_cam = True) if self.last_mode == 'aim' else {}
            self.change_mode(self.last_mode, enter_kwargs=enter_kwargs)

        return task.cont
