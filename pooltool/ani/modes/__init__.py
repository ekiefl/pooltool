#! /usr/bin/env python

import pooltool.ani.utils as autils
import pooltool.ani.action as action

import numpy as np

from abc import ABC, abstractmethod

class Mode(ABC):
    keymap = None

    def __init__(self):
        if self.keymap is None:
            raise NotImplementedError("Child classes of Mode must have 'keymap' attribute")


    def quit_task(self, task):
        if self.keymap[action.quit]:
            self.keymap[action.quit] = False
            self.change_mode('menu')
            self.close_scene()

        return task.cont


    @abstractmethod
    def enter(self):
        pass


    @abstractmethod
    def exit(self):
        pass


class CameraMode(Mode):
    def __init__(self):
        Mode.__init__(self)


    def zoom_camera(self):
        with self.mouse:
            s = -self.mouse.get_dy()*0.3

        self.cam.node.setPos(autils.multiply_cw(self.cam.node.getPos(), 1-s))


    def move_camera(self):
        with self.mouse:
            dxp, dyp = self.mouse.get_dx(), self.mouse.get_dy()

        # NOTE This conversion _may_ depend on how I initialized self.cam.focus
        h = self.cam.focus.getH() * np.pi/180 + np.pi/2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        f = 0.6
        self.cam.focus.setX(self.cam.focus.getX() + dx*f)
        self.cam.focus.setY(self.cam.focus.getY() + dy*f)


    def fix_cue_stick_to_camera(self):
        self.cue_stick.get_node('cue_stick_focus').setH(self.cam.focus.getH())


    def rotate_camera(self, cue_stick_too=False):
        if self.keymap[action.fine_control]:
            fx, fy = 2, 0
        else:
            fx, fy = 13, 3

        with self.mouse:
            alpha_x = self.cam.focus.getH() - fx * self.mouse.get_dx()
            alpha_y = max(min(0, self.cam.focus.getR() + fy * self.mouse.get_dy()), -90)

        self.cam.focus.setH(alpha_x) # Move view laterally
        self.cam.focus.setR(alpha_y) # Move view vertically

        if cue_stick_too:
            self.fix_cue_stick_to_camera()


from pooltool.ani.modes.aim import AimMode
from pooltool.ani.modes.menu import MenuMode
from pooltool.ani.modes.shot import ShotMode
from pooltool.ani.modes.view import ViewMode
from pooltool.ani.modes.stroke import StrokeMode

# Instantiate each class to verify integrity
AimMode()
MenuMode()
ShotMode()
ViewMode()
StrokeMode()
