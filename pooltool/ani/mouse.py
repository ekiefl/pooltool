#! /usr/bin/env python

import pooltool.ani.utils as autils

import numpy as np

from panda3d.core import ClockObject
from pandac.PandaModules import WindowProperties


class Mouse(ClockObject):
    def __init__(self):
        ClockObject.__init__(self)

        self.mouse = base.mouseWatcherNode
        self.tracking = False


    def __enter__(self):
        if not self.tracking:
            raise Exception("Mouse :: self.tracking is False")
        return self


    def __exit__(self, *args):
        self.touch()


    @staticmethod
    def hide():
        props = WindowProperties()
        props.setCursorHidden(True)
        base.win.requestProperties(props)


    @staticmethod
    def show():
        props = WindowProperties()
        props.setCursorHidden(False)
        base.win.requestProperties(props)

    @staticmethod
    def absolute():
        props = WindowProperties()
        props.setMouseMode(WindowProperties.M_absolute)
        base.win.requestProperties(props)


    @staticmethod
    def relative():
        props = WindowProperties()
        props.setMouseMode(WindowProperties.M_relative)
        base.win.requestProperties(props)


    def touch(self):
        self.last_x, self.last_y = self.get_xy()
        self.last_t = self.getRealTime() - self.getDt()


    def track(self):
        if not self.tracking and self.mouse.hasMouse():
            self.tracking = True
            self.touch()


    def get_x(self):
        return self.mouse.getMouseX()


    def get_y(self):
        return self.mouse.getMouseY()


    def get_xy(self):
        return self.get_x(), self.get_y()


    def get_dx(self):
        return self.get_x() - self.last_x


    def get_dy(self):
        return self.get_y() - self.last_y


    def get_vel_x(self):
        dt = self.get_dt()

        if not dt:
            return np.inf

        return self.get_dx()/dt


    def get_vel_y(self):
        dt = self.get_dt()

        if not dt:
            return np.inf

        return self.get_dy()/dt


    def get_dt(self):
        return self.getRealTime() - self.last_t


