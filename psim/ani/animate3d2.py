#! /usr/bin/env python

import psim.ani as ani
import psim.ani.utils as autils
import psim.ani.action as action

from psim.ani import model_paths
from psim.ani.menu import MenuHandler
from psim.ani.tasks import Tasks
from psim.ani.mouse import Mouse

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
                    action.pause: False,
                    action.quit: False,
                },
            }
        }

        self.mode = None
        self.keymap = None


    def update_key_map(self, action_name, action_state):
        self.keymap[action_name] = action_state


    def watch_action(self, keystroke, action_name, action_state):
        self.accept(keystroke, self.update_key_map, [action_name, action_state])


    def change_mode(self, mode):
        assert mode in self.modes

        # Tear down operations for the current mode
        if self.mode is not None:
            self.modes[self.mode]['exit']()

        # Build up operations for the new mode
        self.modes[mode]['enter']()

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

        # Stop watching actions related to mode
        self.ignoreAll()


    def aim_enter(self):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.watch_action('escape', action.quit, True)
        self.watch_action('f', action.fine_control, True)
        self.watch_action('f-up', action.fine_control, False)

        self.add_task(self.aim_task, 'aim_task')
        self.add_task(self.should_quit_task, 'should_quit_task')


    def aim_exit(self):
        self.remove_task('aim_task')
        self.remove_task('should_quit_task')

        # Stop watching actions related to mode
        self.ignoreAll()


class AnimateShot(ShowBase, MenuHandler, Handler, Tasks):
    def __init__(self, *args, **kwargs):
        ShowBase.__init__(self)
        MenuHandler.__init__(self)
        Handler.__init__(self)
        Tasks.__init__(self)

        self.tasks = {}
        self.disableMouse()
        self.mouse = Mouse()

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


    def update_camera(self):
        if self.keymap[action.fine_control]:
            fx, fy = 2, 0
        else:
            fx, fy = 10, 3

        alpha_x = self.dummy.getH() - fx * self.mouse.get_dx()
        alpha_y = max(min(0, self.dummy.getR() + fy * self.mouse.get_dy()), -45)

        self.dummy.setH(alpha_x) # Move view laterally
        self.dummy.setR(alpha_y) # Move view vertically


    def close_scene(self):
        self.cue.removeNode()
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
        self.init_cue()


    def init_table(self):
        w, l, h = 40, 80, 0

        self.table = NodePath()

        self.table = render.attachNewNode(autils.make_rectangle(
            x1=0, y1=0, z1=0, x2=w, y2=l, z2=0, name='table'
        ))

        self.table.setPos(0, 0, 0)
        table_tex = loader.loadTexture(model_paths['blue_cloth'])
        table_tex.setWrapU(Texture.WM_repeat)
        table_tex.setWrapV(Texture.WM_repeat)

        self.table.setTexture(table_tex)


    def init_cue(self):
        w, l, h = 20, 1, 0

        self.cue = NodePath()

        self.cue = render.attachNewNode(autils.make_rectangle(
            x1=0, y1=0, z1=0, x2=w, y2=l, z2=0, name='table'
        ))

        table_tex = loader.loadTexture(model_paths['red_cloth'])
        table_tex.setWrapU(Texture.WM_repeat)
        table_tex.setWrapV(Texture.WM_repeat)

        self.cue.setTexture(table_tex)

        self.cue.reparentTo(self.dummy)
        self.cue.setPos(2, -0.5, 0)


    def init_scene(self):
        self.scene = render.attachNewNode('scene')

        self.ball1 = loader.loadModel(model_paths['sphere2'])
        self.ball1.reparentTo(self.scene)
        self.ball1.setPos(12,12,0.9)
        self.ball1.setScale(1)

        self.ball2 = loader.loadModel(model_paths['sphere2'])
        self.ball2.reparentTo(self.scene)
        self.ball2.setPos(30,70,0.9)
        self.ball2.setScale(1)

        self.dummy = self.scene.attachNewNode("dummyNode")
        self.dummy.setPos(self.ball1.getPos())

        self.camera.reparentTo(self.dummy)
        self.camera.setPos(50, 0, 0)
        self.camera.lookAt(self.ball1)


    def start(self):
        self.run()
