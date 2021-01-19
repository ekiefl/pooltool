#! /usr/bin/env python

import psim.ani as ani
import psim.ani.utils as autils
import psim.ani.action as action

from psim.ani import model_paths
from psim.objects import Ball, Table, Cue
from psim.ani.menu import MenuHandler
from psim.ani.tasks import Tasks
from psim.ani.mouse import Mouse
from psim.ani.camera import CustomCamera

import gc

from panda3d.core import *
from direct.showbase import DirectObject
from direct.showbase.ShowBase import ShowBase


class Handler(DirectObject.DirectObject):
    def __init__(self):

        self.modes = {
            'menu': {
                'enter': self.menu_enter,
                'exit': self.menu_exit,
                'keymap': {
                    action.exit: False,
                }
            },
            'aim': {
                'enter': self.aim_enter,
                'exit': self.aim_exit,
                'keymap': {
                    action.fine_control: False,
                    action.quit: False,
                    action.shoot: False,
                    action.view: False,
                    action.zoom: False,
                },
            },
            'view': {
                'enter': self.view_enter,
                'exit': self.view_exit,
                'keymap': {
                    action.aim: False,
                    action.fine_control: False,
                    action.move: True,
                    action.quit: False,
                    action.zoom: False,
                },
            },
        }

        # Store the above as default states
        self.action_state_defaults = {}
        for mode in self.modes:
            self.action_state_defaults[mode] = {}
            for a, default_state in self.modes[mode]['keymap'].items():
                self.action_state_defaults[mode][a] = default_state

        self.mode = None
        self.keymap = None


    def update_key_map(self, action_name, action_state):
        self.keymap[action_name] = action_state


    def watch_action(self, keystroke, action_name, action_state):
        self.accept(keystroke, self.update_key_map, [action_name, action_state])


    def change_mode(self, mode):
        assert mode in self.modes

        # Stop watching actions related to mode
        self.ignoreAll()

        # Tear down operations for the current mode
        if self.mode is not None:
            self.modes[self.mode]['exit']()

        # Build up operations for the new mode
        self.modes[mode]['enter']()

        if self.mode is not None:
            self.reset_action_states()

        self.mode = mode
        self.keymap = self.modes[mode]['keymap']


    def menu_enter(self):
        self.mouse.show()
        self.mouse.absolute()
        self.show_menu('main')

        self.watch_action('escape', action.exit, True)
        self.watch_action('escape-up', action.exit, False)

        self.add_task(self.menu_task, 'menu_task')


    def menu_exit(self):
        self.hide_menus()
        self.remove_task('menu_task')


    def aim_enter(self):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.cue_stick.show_nodes()

        self.cam.load_state('aim', ok_if_not_exists=True)

        self.watch_action('escape', action.quit, True)
        self.watch_action('f', action.fine_control, True)
        self.watch_action('f-up', action.fine_control, False)
        self.watch_action('mouse1', action.zoom, True)
        self.watch_action('mouse1-up', action.zoom, False)
        self.watch_action('s', action.shoot, True)
        self.watch_action('s-up', action.shoot, False)
        self.watch_action('v', action.view, True)

        self.add_task(self.aim_task, 'aim_task')
        self.add_task(self.quit_task, 'quit_task')


    def aim_exit(self):
        self.remove_task('aim_task')
        self.remove_task('quit_task')

        self.cue_stick.hide_nodes()

        self.cam.store_state('aim', overwrite=True)


    def view_enter(self):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.watch_action('escape', action.quit, True)
        self.watch_action('mouse1', action.zoom, True)
        self.watch_action('mouse1-up', action.zoom, False)
        self.watch_action('a', action.aim, True)
        self.watch_action('v', action.move, True)
        self.watch_action('v-up', action.move, False)

        self.add_task(self.view_task, 'view_task')
        self.add_task(self.quit_task, 'quit_task')


    def view_exit(self):
        self.remove_task('view_task')
        self.remove_task('quit_task')


    def reset_action_states(self):
        for key in self.keymap:
            self.keymap[key] = self.action_state_defaults[self.mode][key]


class InteractiveVisualization(ShowBase, MenuHandler, Handler, Tasks):
    def __init__(self, *args, **kwargs):
        ShowBase.__init__(self)
        MenuHandler.__init__(self)
        Handler.__init__(self)
        Tasks.__init__(self)

        self.tasks = {}
        self.balls = {}
        self.disableMouse()
        self.mouse = Mouse()
        self.cam = CustomCamera()
        self.table = Table()
        self.cue_stick = Cue()

        self.change_mode('menu')

        self.scene = None
        self.add_task(self.monitor, 'monitor')


    def add_task(self, *args, **kwargs):
        task = taskMgr.add(*args, **kwargs)
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
            pos = self.balls['cue'].get_node('sphere').getPos()
        )


    def init_table(self):
        self.table.render()


    def init_cue_stick(self):
        self.cue_stick.render()
        self.cue_stick.init_focus(self.balls['cue'])


    def init_scene(self):
        self.scene = render.attachNewNode('scene')


    def init_balls(self):

        self.balls['cue'] = Ball('cue')
        R = self.balls['cue'].R
        self.balls['cue'].rvw[0] = [self.table.center[0], self.table.B+0.33, R]

        self.balls['1'] = Ball('1')
        self.balls['1'].rvw[0] = [self.table.center[0], self.table.B+1.4, R]

        self.balls['2'] = Ball('2')
        self.balls['2'].rvw[0] = [self.table.center[0], self.table.T-0.3, R]

        self.balls['3'] = Ball('3')
        self.balls['3'].rvw[0] = [self.table.center[0] + self.table.w/6, self.table.B+1.89, R]

        self.balls['4'] = Ball('4')
        self.balls['4'].rvw[0] = [self.table.center[0] + self.table.w/6, self.table.B+0.2, R]

        self.balls['5'] = Ball('5')
        self.balls['5'].rvw[0] = [self.table.center[0] - self.table.w/6, self.table.B+0.2, R]

        self.balls['6'] = Ball('6')
        self.balls['6'].rvw[0] = [self.table.center[0], self.table.T-0.03, R]

        self.balls['7'] = Ball('7')
        self.balls['7'].rvw[0] = [self.table.center[0] - self.table.w/5, self.table.B+1.89, R]

        self.balls['8'] = Ball('8')
        self.balls['8'].rvw[0] = [self.table.center[0]+0.3, self.table.T-0.03, R]

        self.balls['10'] = Ball('10')
        self.balls['10'].rvw[0] = [self.table.center[0] - self.table.w/5, self.table.T-0.2, R]

        for ball in self.balls.values():
            ball.render()


    def start(self):
        self.run()
