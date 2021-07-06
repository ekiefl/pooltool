#! /usr/bin/env python

from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes import Mode, action
from direct.gui.DirectGui import *

class CamLoadMode(Mode):
    keymap = {
        action.quit: False,
        action.cam_load: True,
    }


    def enter(self):
        if self.last_mode == 'aim':
            self.last_mode = 'view'
        self.mouse.show()
        self.mouse.absolute()
        self.mouse.track()
        self.selection = None

        self.task_action('escape', action.quit, True)
        self.task_action('2', action.cam_load, True)
        self.task_action('2-up', action.cam_load, False)

        self.render_camera_load_buttons()
        self.add_task(self.cam_load_task, 'cam_load_task')


    def render_camera_load_buttons(self):
        self.cam_load_slots = GenericMenu(
            title = "Release key with moused hovered over desired save slot",
            frame_color = (0,0,0,0.2),
            title_pos = (0,0,0.45),
        )

        pos = -1.2
        for slot in range(1, 10):
            exists = True if f'save_{slot}' in self.player_cam.states else False
            button = self.cam_load_slots.add_button(
                text = (f'{slot}', f'{slot}', 'load' if exists else 'empty', f'{slot}'),
                command = lambda: None,
                scale = 0.1,
                text_scale = 0.6,
                frameSize = (-1.2, 1.2, -1.2, 1.2),
                frameColor = (0.3, 0.6, 0.6, 1.0) if exists else (0.8, 0.8, 0.8, 1.0),
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
            self.player_cam.load_state(name=f'save_{self.selection}', ok_if_not_exists=True)

        self.remove_task('cam_load_task')
        self.mouse.touch()
        self.cam_load_slots.hide()


    def cam_load_task(self, task):
        if not self.keymap[action.cam_load]:
            enter_kwargs = dict(load_prev_cam = True) if self.last_mode == 'aim' else {}
            self.change_mode(self.last_mode, enter_kwargs=enter_kwargs)

        return task.cont
