#! /usr/bin/env python

from pooltool.ani.modes import Mode, action

class CamSaveMode(Mode):
    keymap = {
        action.quit: False,
        action.cam_save: True,
    }


    def enter(self):
        self.mouse.show()
        self.mouse.absolute()
        self.mouse.track()

        self.task_action('escape', action.quit, True)
        self.task_action('k', action.cam_save, True)
        self.task_action('k-up', action.cam_save, False)

        self.add_task(self.cam_save_task, 'cam_save_task')


    def exit(self):
        self.remove_task('cam_save_task')
        self.mouse.touch()


    def cam_save_task(self, task):
        if not self.keymap[action.cam_save]:
            enter_kwargs = dict(load_prev_cam = True) if self.last_mode == 'aim' else {}
            self.change_mode(self.last_mode, enter_kwargs=enter_kwargs)

        return task.cont
