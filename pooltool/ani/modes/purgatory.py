#! /usr/bin/env python

import pooltool.ani as ani
from pooltool.ani.modes import Mode, action


class PurgatoryMode(Mode):
    """A transitionary mode when the window has become inactive

    Purgatory mode should be enetered when the pooltool window inactive. Opening an app,
    alt-tabbing, clicking outside the window, etc. are all ways to make the pooltool
    window inactive.

    Purgatory mode is exited by clicking on the window. Since it is possible to
    reactivate the window without clicking (e.g. alt-tabbing), this means that
    reactivating the window is not enough to exit purgatory. The click requirement makes
    sure your mouse doesn't get stuck if you alt-tab to pooltool into a mode that uses
    relative mouse (a mouse that doesn't move). You must willfully click on the window
    to re-engage, which actually feels pretty intuitive.

    In purgatory, the window can either be active or inactive. When inactive, a low
    frame rate is engaged. When active, the standard frame rate is used.
    """

    keymap = {
        action.regain_control: False,
    }

    def __init__(self):
        self.is_window_active = None

    def enter(self):
        self.mouse.show()
        self.mouse.absolute()

        self.task_action("mouse1-up", action.regain_control, True)
        self.task_action("mouse1-down", action.regain_control, False)

        self.add_task(self.purgatory_task, "purgatory_task")

    def exit(self):
        self.remove_task("purgatory_task")

        # Set the framerate to pre-purgatory levels
        globalClock.setFrameRate(ani.settings["graphics"]["fps"])

    def purgatory_task(self, task):
        if self.keymap[action.regain_control]:
            self.change_mode(self.last_mode)

        is_window_active = base.win.get_properties().foreground

        if is_window_active is not self.is_window_active:
            # The state of the window has changed. Time to update the FPS

            if is_window_active:
                globalClock.setFrameRate(ani.settings["graphics"]["fps"])
            else:
                globalClock.setFrameRate(ani.settings["graphics"]["fps_inactive"])

            # Update status
            self.is_window_active = is_window_active

        return task.cont
