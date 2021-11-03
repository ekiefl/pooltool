#! /usr/bin/env python

import pooltool.ani.utils as autils
import pooltool.ani.action as action

import re
import numpy as np

from abc import ABC, abstractmethod
from pathlib import Path
from inspect import isclass
from pkgutil import iter_modules
from importlib import import_module


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


# https://julienharbulot.com/python-dynamical-import.html
package_dir = str(Path(__file__).resolve().parent)
for (_, module_name, _) in iter_modules([package_dir]):
    module = import_module(f"{__name__}.{module_name}")
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)

        if isclass(attribute):
            globals()[attribute_name] = attribute

get_mode_name = lambda mode: re.sub(r'(?<!^)(?=[A-Z])', '_', mode.__name__[:-4]).lower()
modes = {get_mode_name(cls): cls for cls in Mode.__subclasses__()}
