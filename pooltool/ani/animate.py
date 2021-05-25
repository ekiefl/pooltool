#! /usr/bin/env python

import pooltool

from pooltool.objects.cue import Cue
from pooltool.objects.ball import Ball
from pooltool.objects.table import Table

from pooltool.ani.menu import MenuManager
from pooltool.ani.modes import *
from pooltool.ani.tasks import Tasks
from pooltool.ani.mouse import Mouse
from pooltool.ani.camera import CustomCamera

import gc

from panda3d.core import *
from direct.showbase.ShowBase import ShowBase


class Handler(MenuMode, AimMode, StrokeMode, ViewMode, ShotMode):
    def __init__(self):
        # Init every Mode class
        MenuMode.__init__(self)
        AimMode.__init__(self)
        StrokeMode.__init__(self)
        ViewMode.__init__(self)
        ShotMode.__init__(self)

        self.modes = {
            'menu': MenuMode,
            'aim': AimMode,
            'stroke': StrokeMode,
            'view': ViewMode,
            'shot': ShotMode,
        }

        # Store the above as default states
        self.action_state_defaults = {}
        for mode in self.modes:
            self.action_state_defaults[mode] = {}
            for a, default_state in self.modes[mode].keymap.items():
                self.action_state_defaults[mode][a] = default_state

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



class Interface(ShowBase, MenuManager, Handler, Tasks):
    def __init__(self, *args, **kwargs):
        ShowBase.__init__(self)
        MenuManager.__init__(self)
        Handler.__init__(self)
        Tasks.__init__(self)

        self.tasks = {}
        self.balls = {}
        self.disableMouse()
        self.mouse = Mouse()
        self.cam = CustomCamera()
        self.table = None
        self.cue_stick = Cue()

        self.change_mode('menu')

        self.scene = None
        self.add_task(self.monitor, 'monitor')

        taskMgr.setupTaskChain('simulation', numThreads = 1, tickClock = None,
                               threadPriority = None, frameBudget = None,
                               frameSync = None, timeslicePriority = None)


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
        self.table = Table(l=2.840*2/3, w=1.420*2/3)
        self.table.render()


    def init_cue_stick(self):
        self.cue_stick.render()
        self.cue_stick.init_focus(self.balls['cue'])


    def init_scene(self):
        self.scene = render.attachNewNode('scene')


    def init_balls(self):
        ball_kwargs = dict(
            u_s=0.14,
            u_r=0.007,
            u_sp=0.022,
        )
        self.balls['r'] = Ball('r', **ball_kwargs)
        self.balls['y'] = Ball('y', **ball_kwargs)
        self.balls['cue'] = Ball('cue', **ball_kwargs)

        self.balls['cue'].rvw[0] = [self.table.center[0] + 0.2, self.table.l/4, pooltool.R]
        self.balls['r'].rvw[0] = [self.table.center[0], self.table.l*3/4, pooltool.R]
        self.balls['y'].rvw[0] = [self.table.center[0], self.table.l/4, pooltool.R]

        #self.balls['cue'] = Ball('cue')
        #R = self.balls['cue'].R
        #self.balls['cue'].rvw[0] = [self.table.center[0], self.table.B+0.33, R]

        #self.balls['1'] = Ball('1')
        #self.balls['1'].rvw[0] = [self.table.center[0], self.table.B+1.4, R]

        #self.balls['2'] = Ball('2')
        #self.balls['2'].rvw[0] = [self.table.center[0], self.table.T-0.3, R]

        #self.balls['3'] = Ball('3')
        #self.balls['3'].rvw[0] = [self.table.center[0] + self.table.w/6, self.table.B+1.89, R]

        #self.balls['4'] = Ball('4')
        #self.balls['4'].rvw[0] = [self.table.center[0] + self.table.w/6, self.table.B+0.2, R]

        #self.balls['5'] = Ball('5')
        #self.balls['5'].rvw[0] = [self.table.center[0] - self.table.w/6, self.table.B+0.2, R]

        #self.balls['6'] = Ball('6')
        #self.balls['6'].rvw[0] = [self.table.center[0], self.table.T-0.03, R]

        #self.balls['7'] = Ball('7')
        #self.balls['7'].rvw[0] = [self.table.center[0] - self.table.w/5, self.table.B+1.89, R]

        #self.balls['8'] = Ball('8')
        #self.balls['8'].rvw[0] = [self.table.center[0]+0.3, self.table.T-0.03, R]

        #self.balls['10'] = Ball('10')
        #self.balls['10'].rvw[0] = [self.table.center[0] - self.table.w/5, self.table.T-0.2, R]

        for ball in self.balls.values():
            ball.render()


    def start(self):
        self.run()
