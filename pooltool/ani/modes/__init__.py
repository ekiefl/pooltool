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

        self.add_task(self.quit_task, 'quit_task')
        self.add_task(self.cam_save_watch, 'cam_save_watch')
        self.add_task(self.cam_load_watch, 'cam_load_watch')


    def quit_task(self, task):
        if self.keymap.get(action.quit):
            self.keymap[action.quit] = False
            self.close_scene()
            self.change_mode('menu')

        return task.cont


    def cam_save_watch(self, task):
        if self.keymap.get(action.cam_save) and self.mode != 'cam_save':
            self.change_mode('cam_save')

        return task.cont


    def cam_load_watch(self, task):
        if self.keymap.get(action.cam_load) and self.mode != 'cam_load':
            self.change_mode('cam_load')

        return task.cont


    @abstractmethod
    def enter(self):
        pass


    @abstractmethod
    def exit(self):
        pass


from pooltool.ani.modes.aim import AimMode
from pooltool.ani.modes.menu import MenuMode
from pooltool.ani.modes.shot import ShotMode
from pooltool.ani.modes.view import ViewMode
from pooltool.ani.modes.stroke import StrokeMode
from pooltool.ani.modes.cam_save import CamSaveMode
from pooltool.ani.modes.cam_load import CamLoadMode
from pooltool.ani.modes.pick_ball import PickBallMode
from pooltool.ani.modes.calculate import CalculateMode
