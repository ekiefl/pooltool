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

    def quit_task(self, task):
        if self.keymap.get(action.quit):
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


from pooltool.ani.modes.aim import AimMode
from pooltool.ani.modes.menu import MenuMode
from pooltool.ani.modes.shot import ShotMode
from pooltool.ani.modes.view import ViewMode
from pooltool.ani.modes.stroke import StrokeMode
from pooltool.ani.modes.calculate import CalculateMode
