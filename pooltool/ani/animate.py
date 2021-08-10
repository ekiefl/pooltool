#! /usr/bin/env python

import pooltool
import pooltool.ani as ani
import pooltool.utils as utils
import pooltool.games as games

from pooltool.objects.cue import Cue
from pooltool.objects.ball import Ball
from pooltool.objects.table import Table
from pooltool.games.nine_ball import NineBall
from pooltool.games.eight_ball import EightBall

from pooltool.ani.hud import HUD
from pooltool.ani.menu import Menus
from pooltool.ani.modes import *
from pooltool.ani.mouse import Mouse
from pooltool.ani.camera import PlayerCam

import gc

from panda3d.core import *
from direct.showbase.ShowBase import ShowBase


class ModeManager(MenuMode, AimMode, StrokeMode, ViewMode, ShotMode, CamLoadMode, CamSaveMode, CalculateMode,
                  PickBallMode, GameOverMode, CallShotMode, BallInHandMode):
    def __init__(self):
        # Init every Mode class
        self.modes = modes
        for mode in modes.values():
            mode.__init__(self)

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

        # Teardown operations for the old mode
        self.last_mode = self.mode
        self.end_mode(**exit_kwargs)

        # Build up operations for the new mode
        self.mode = mode
        self.keymap = self.modes[mode].keymap
        self.modes[mode].enter(self, **enter_kwargs)


    def end_mode(self, **kwargs):
        # Stop watching actions related to mode
        self.ignoreAll()

        if self.mode is not None:
            self.modes[self.mode].exit(self, **kwargs)
            self.reset_action_states()

        self.mode = None


    def reset_action_states(self):
        for key in self.keymap:
            self.keymap[key] = self.action_state_defaults[self.mode][key]


class Interface(ShowBase, ModeManager):
    is_game = None
    def __init__(self, shot=None):
        if self.is_game is None:
            raise Exception(f"'{self.__class__.__name__}' must set 'is_game' attribute")

        ShowBase.__init__(self)

        self.shot = None
        self.balls = None
        self.table = None
        self.cue = None
        if shot:
            self.set_shot(shot)

        self.tasks = {}
        self.disableMouse()
        self.mouse = Mouse()
        self.player_cam = PlayerCam()

        ModeManager.__init__(self)

        self.scene = None
        self.add_task(self.monitor, 'monitor')
        self.frame = 0


    def set_shot(self, shot):
        self.shot = shot
        self.balls = self.shot.balls
        self.table = self.shot.table
        self.cue = self.shot.cue


    def add_task(self, *args, **kwargs):
        task = taskMgr.add(*args, **kwargs)
        self.tasks[task.name] = task


    def add_task_later(self, *args, **kwargs):
        task = taskMgr.doMethodLater(*args, **kwargs)
        self.tasks[task.name] = task


    def remove_task(self, name):
        taskMgr.remove(name)
        del self.tasks[name]


    def close_scene(self):
        for ball in self.balls.values():
            ball.remove_nodes()
        self.table.remove_nodes()
        gc.collect()


    def init_system_nodes(self):
        self.init_scene()
        self.table.render()

        for ball in self.balls.values():
            if not ball.rendered:
                ball.render()

        self.cue.render()
        self.cue.init_focus(self.cueing_ball)

        self.player_cam.create_focus(
            parent = self.table.get_node('cloth'),
            pos = self.balls['cue'].get_node('ball').getPos()
        )


    def init_scene(self):
        self.scene = render.attachNewNode('scene')


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


class ShotViewer(Interface):
    is_game = False

    def __init__(self, shot=None):
        Interface.__init__(self, shot=shot)
        self.stop()
        self.is_game = False


    def start(self):
        if not self.win:
            self.openMainWindow()

        self.mouse = Mouse()
        self.init_system_nodes()
        params = dict(
            init_animations = True,
            single_instance = True,
        )
        self.change_mode('shot', enter_kwargs=params)

        self.taskMgr.run()


    def stop(self):
        if self.win:
            self.closeWindow(self.win)
        self.taskMgr.stop()


    def finalizeExit(self):
        self.stop()


class Play(Interface, Menus, HUD):
    is_game = True

    def __init__(self, *args, **kwargs):
        Interface.__init__(self, shot=None)
        Menus.__init__(self)
        HUD.__init__(self)

        self.change_mode('menu')

        # This task chain allows simulations to be run in parallel to the game processes
        taskMgr.setupTaskChain(
            'simulation',
            numThreads = 1,
            tickClock = None,
            threadPriority = None,
            frameBudget = None,
            frameSync = None,
            timeslicePriority = None
        )


    def go(self):
        self.setup()
        self.init_system_nodes()
        self.change_mode('aim')


    def close_scene(self):
        Interface.close_scene(self)
        self.destroy_hud()


    def setup(self):
        self.setup_options = self.get_menu_options()

        self.setup_table()
        self.setup_game()
        self.setup_balls()
        self.setup_cue()

        self.init_hud()


    def setup_table(self):
        self.table = Table(
            w = self.setup_options[ani.options_table_width],
            l = self.setup_options[ani.options_table_length],
            cushion_height = self.setup_options[ani.options_cushion_height_frac]*self.setup_options[ani.options_ball_diameter],
        )


    def setup_game(self):
        """Setup the game class from pooltool.games

        Notes
        =====
        - For reasons of bad design, ball kwargs are defined in this method
        """

        ball_kwargs = dict(
            R = self.setup_options[ani.options_ball_diameter]/2,
            u_s = self.setup_options[ani.options_friction_slide],
            u_r = self.setup_options[ani.options_friction_roll],
            u_sp = self.setup_options[ani.options_friction_spin],
        )

        game_class = games.game_classes[self.setup_options[ani.options_game]]
        self.game = game_class()
        self.game.init(self.table, ball_kwargs)
        self.game.start()


    def setup_cue(self):
        self.cue = Cue()


    def setup_balls(self):
        self.balls = self.game.layout.get_balls_dict()
        self.cueing_ball = self.game.set_initial_cueing_ball(self.balls)


    def start(self):
        self.run()


