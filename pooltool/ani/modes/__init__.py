#! /usr/bin/env python

import pooltool.ani.action as action

from abc import ABC, abstractmethod

class Mode(ABC):
    keymap = None

    def __init__(self):
        if self.keymap is None:
            raise NotImplementedError("Child classes of Mode must have 'keymap' attribute")


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

# Instantiate each class to verify integrity
AimMode()
MenuMode()
ShotMode()
ViewMode()
StrokeMode()
