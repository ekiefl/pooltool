#! /usr/bin/env python

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.globals import Global
from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse


class PurgatoryMode(BaseMode):
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

    name = Mode.purgatory
    keymap = {
        Action.regain_control: False,
    }

    def __init__(self):
        super().__init__()

        self.is_window_active = None

        self.dim_overlay = GenericMenu(
            title="Click to continue...",
            frame_color=(0, 0, 0, 0.4),
            title_pos=(0, 0, -0.2),
        )
        self.dim_overlay.hide()

    def enter(self):
        mouse.mode(MouseMode.ABSOLUTE)
        self.dim_overlay.show()

        self.register_keymap_event("mouse1-up", Action.regain_control, True)
        self.register_keymap_event("mouse1-down", Action.regain_control, False)

        tasks.add(self.purgatory_task, "purgatory_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self):
        tasks.remove("shared_task")
        tasks.remove("purgatory_task")

        # Set the framerate to pre-purgatory levels
        Global.clock.setFrameRate(ani.settings["graphics"]["fps"])

        self.dim_overlay.hide()

    def purgatory_task(self, task):
        if self.keymap[Action.regain_control]:
            Global.mode_mgr.change_mode(Global.mode_mgr.last_mode)

        is_window_active = Global.base.win.get_properties().foreground

        if is_window_active is not self.is_window_active:
            # The state of the window has changed. Time to update the FPS

            if is_window_active:
                Global.clock.setFrameRate(ani.settings["graphics"]["fps"])
            else:
                Global.clock.setFrameRate(ani.settings["graphics"]["fps_inactive"])

            # Update status
            self.is_window_active = is_window_active

        return task.cont
