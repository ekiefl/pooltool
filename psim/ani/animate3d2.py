#! /usr/bin/env python

import psim.ani as ani
import psim.ani.utils as autils
import psim.ani.action as action

from psim.ani import model_paths
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


class AnimateShot(ShowBase, MenuHandler, Handler, Tasks):
    def __init__(self, *args, **kwargs):
        ShowBase.__init__(self)
        MenuHandler.__init__(self)
        Handler.__init__(self)
        Tasks.__init__(self)

        self.tasks = {}
        self.disableMouse()
        self.mouse = Mouse()
        self.cam = CustomCamera()

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
        self.cue_stick.removeNode()
        self.ball1.removeNode()
        self.ball2.removeNode()
        self.table.removeNode()
        self.scene.removeNode()
        del self.scene
        gc.collect()


    def go(self):
        self.change_mode('aim')
        self.init_game_nodes()


    def init_game_nodes(self):
        self.init_scene()
        self.init_table()
        self.init_cue_stick()


    def init_table(self):
        w, l, h = 40, 80, 0

        self.table = NodePath()

        self.table = self.scene.attachNewNode(autils.make_rectangle(
            x1=0, y1=0, z1=0, x2=w, y2=l, z2=0, name='table'
        ))

        self.table.setPos(0, 0, 0)
        table_tex = loader.loadTexture(model_paths['blue_cloth'])

        self.table.setTexture(table_tex)


    def init_cue_stick(self):
        cue_stick_model = loader.loadModel(model_paths['cylinder'])
        cue_stick_tex = loader.loadTexture(model_paths['red_cloth'])
        cue_stick_model.setTexture(cue_stick_tex)
        cue_stick_model.setTexScale(TextureStage.getDefault(), 0.01, 0.01)

        cue_stick_model.setScale(0.02)
        cue_stick_model.setSz(0.8)

        bounds = cue_stick_model.getTightBounds()
        h = abs(bounds[0][2] - bounds[1][2])

        self.cue_stick = self.scene.attachNewNode('cue_stick')
        cue_stick_model.reparentTo(self.cue_stick)
        cue_stick_model.setPos(0, 0, h/2 + 1 + 0.2)

        self.cue_stick.setP(90)
        self.cue_stick.setH(90)

        self.cue_stick.reparentTo(self.cue_stick_focus)


    def init_scene(self):
        self.scene = render.attachNewNode('scene')

        self.ball1 = loader.loadModel('smiley.egg')
        self.ball1.reparentTo(self.scene)
        self.ball1.setPos(12,12,0.9)
        self.ball1.setScale(1)

        self.ball2 = loader.loadModel('smiley.egg')
        self.ball2.reparentTo(self.scene)
        self.ball2.setPos(30,70,0.9)
        self.ball2.setScale(1)

        self.cam.create_focus(pos=self.ball1.getPos())

        self.cue_stick_focus = self.scene.attachNewNode("cue_stick_focus")
        self.cue_stick_focus.setPos(self.ball1.getPos())


    def start(self):
        self.run()
