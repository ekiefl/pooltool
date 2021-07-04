#! /usr/bin/env python

import pooltool
import pooltool.utils as utils
import pooltool.layouts as layouts

from pooltool.objects.cue import Cue
from pooltool.objects.ball import Ball
from pooltool.objects.table import Table

from pooltool.ani.menu import Menus
from pooltool.ani.modes import (
    AimMode,
    CalculateMode,
    ShotMode,
    MenuMode,
    StrokeMode,
    ViewMode,
    CamSaveMode,
    CamLoadMode,
)
from pooltool.ani.mouse import Mouse
from pooltool.ani.camera import CustomCamera

import gc

from panda3d.core import *
from direct.showbase.ShowBase import ShowBase


class ModeManager(MenuMode, AimMode, StrokeMode, ViewMode, ShotMode, CamLoadMode, CamSaveMode, CalculateMode):
    def __init__(self):
        # Init every Mode class
        MenuMode.__init__(self)
        AimMode.__init__(self)
        StrokeMode.__init__(self)
        ViewMode.__init__(self)
        ShotMode.__init__(self)
        CamLoadMode.__init__(self)
        CamSaveMode.__init__(self)
        CalculateMode.__init__(self)

        self.modes = {
            'menu': MenuMode,
            'aim': AimMode,
            'stroke': StrokeMode,
            'view': ViewMode,
            'shot': ShotMode,
            'calculate': CalculateMode,
            'cam_save': CamSaveMode,
            'cam_load': CamLoadMode,
        }

        # Store the above as default states
        self.action_state_defaults = {}
        for mode in self.modes:
            self.action_state_defaults[mode] = {}
            for a, default_state in self.modes[mode].keymap.items():
                self.action_state_defaults[mode][a] = default_state

        self.last_mode = None
        self.mode = None
        self.keymap = None


    def update_keymap(self, action_name, action_state):
        self.keymap[action_name] = action_state


    def task_action(self, keystroke, action_name, action_state):
        """Add action to keymap to be handled by tasks"""

        self.accept(keystroke, self.update_keymap, [action_name, action_state])


    def change_mode(self, mode, exit_kwargs={}, enter_kwargs={}):
        assert mode in self.modes

        self.end_mode(**exit_kwargs)

        # Build up operations for the new mode
        self.last_mode = self.mode
        self.mode = mode
        self.keymap = self.modes[mode].keymap
        self.modes[mode].enter(self, **enter_kwargs)


    def end_mode(self, **kwargs):
        # Stop watching actions related to mode
        self.ignoreAll()

        # Tear down operations for the current mode
        if self.mode is not None:
            self.modes[self.mode].exit(self, **kwargs)
            self.reset_action_states()


    def reset_action_states(self):
        for key in self.keymap:
            self.keymap[key] = self.action_state_defaults[self.mode][key]



class Interface(ShowBase, Menus, ModeManager):
    def __init__(self, *args, **kwargs):
        ShowBase.__init__(self)

        self.tasks = {}
        self.balls = {}
        self.disableMouse()
        self.mouse = Mouse()
        self.cam = CustomCamera()
        self.table = None
        self.cue_stick = Cue()

        Menus.__init__(self)
        ModeManager.__init__(self)

        self.change_mode('menu')

        self.scene = None
        self.add_task(self.monitor, 'monitor')

        taskMgr.setupTaskChain('simulation', numThreads = 1, tickClock = None,
                               threadPriority = None, frameBudget = None,
                               frameSync = None, timeslicePriority = None)

        self.frame = 0


    def add_task(self, *args, **kwargs):
        task = taskMgr.add(*args, **kwargs)
        self.tasks[task.name] = task


    def add_task_later(self, *args, **kwargs):
        task = taskMgr.doMethodLater(*args, **kwargs)
        self.tasks[task.name] = task


    def remove_task(self, name):
        taskMgr.remove(name)
        del self.tasks[name]
        pass


    def close_scene(self):
        self.cue_stick.remove_nodes()
        for ball in self.balls.values():
            ball.remove_nodes()
        self.table.remove_nodes()
        self.scene.removeNode()
        del self.scene
        gc.collect()


    def go(self):
        self.init_game_nodes()
        self.change_mode('aim')


    def init_game_nodes(self):
        self.init_scene()
        self.init_table()
        self.init_balls()
        self.init_cue_stick()

        self.cam.create_focus(
            parent = self.table.get_node('cloth'),
            pos = self.balls['cue'].get_node('ball').getPos()
        )


    def init_table(self):
        self.table = Table()
        self.table.render()


    def init_cue_stick(self):
        self.cue_stick.render()
        self.cue_stick.init_focus(self.balls['cue'])


    def init_scene(self):
        self.scene = render.attachNewNode('scene')


    def init_balls(self):
        ball_kwargs = {}
        diamond = layouts.NineBallRack(**ball_kwargs)
        diamond.center_by_table(self.table)
        self.balls = {x: y for x, y in enumerate(diamond.balls)}

        self.balls['cue'] = Ball('cue', **ball_kwargs)
        self.balls['cue'].rvw[0] = [self.table.center[0] + 0.2, self.table.l/4, pooltool.R]

        for ball in self.balls.values():
            ball.render()


    def monitor(self, task):
        #print(f"Mode: {self.mode}")
        #print(f"Tasks: {list(self.tasks.keys())}")
        #print(f"Memory: {utils.get_total_memory_usage()}")
        #print(f"Actions: {[k for k in self.keymap if self.keymap[k]]}")
        #print(f"Keymap: {self.keymap}")
        #print(f"Frame: {self.frame}")
        #print()
        self.frame += 1

        return task.cont

    def start(self):
        self.run()
