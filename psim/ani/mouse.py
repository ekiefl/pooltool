#! /usr/bin/env python

import psim.ani.utils as autils

import numpy as np

from panda3d.core import ClockObject
from pandac.PandaModules import WindowProperties


class Mouse(ClockObject):
    def __init__(self):
        ClockObject.__init__(self)

        self.mouse = base.mouseWatcherNode
        self.tracking = False


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


    def track(self):
        if not self.tracking and self.mouse.hasMouse():
            self.last_x, self.last_y = self.get_xy()
            self.last_t = self.getFrameTime()
            self.tracking = True


    def get_x(self, update=True):
        x = self.mouse.getMouseX()

        if update:
            self.last_x = x
            self.last_t = self.getFrameTime()

        return x


    def get_y(self, update=True):
        y = self.mouse.getMouseY()

        if update:
            self.last_y = y
            self.last_t = self.getFrameTime()

        return y


    def get_xy(self, update=True):
        x, y = self.get_x(update=False), self.get_y(update=False)

        if update:
            self.last_x = x
            self.last_y = y
            self.last_t = self.getFrameTime()

        return x, y


    def get_dx(self, update=True):
        last_x  = self.last_x
        return self.get_x(update=update) - last_x


    def get_dy(self, update=True):
        last_y  = self.last_y
        return self.get_y(update=update) - last_y


    def get_vel_x(self, update=True):
        dt = self.getFrameTime() - self.last_t

        if not dt:
            return np.inf

        return self.get_dx(update=update)/dt


    def get_vel_y(self, update=True):
        dt = self.getFrameTime() - self.last_t

        if not dt:
            return np.inf

        return self.get_dy(update=update)/dt



