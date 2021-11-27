#! /usr/bin/env python

import pooltool
import pooltool.ani as ani
import pooltool.utils as utils
import pooltool.games as games
import pooltool.ani.environment as environment

from pooltool.error import TableConfigError, ConfigError
from pooltool.objects.cue import Cue
from pooltool.objects.ball import Ball
from pooltool.objects.table import table_types
from pooltool.games.nine_ball import NineBall
from pooltool.games.eight_ball import EightBall

from pooltool.ani.hud import HUD
from pooltool.ani.menu import Menus
from pooltool.ani.modes import *
from pooltool.ani.mouse import Mouse
from pooltool.ani.camera import PlayerCam

import gc
import copy
import gltf
import simplepbr

from panda3d.core import *
from direct.showbase.ShowBase import ShowBase


class ModeManager(MenuMode, AimMode, StrokeMode, ViewMode, ShotMode, CamLoadMode, CamSaveMode,
                  CalculateMode, PickBallMode, GameOverMode, CallShotMode, BallInHandMode):
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

        super().__init__(self)
        simplepbr.init(enable_shadows=ani.settings['graphics']['shadows'], max_lights=13)

        if not ani.settings['graphics']['shader']:
            render.set_shader_off()

        globalClock.setMode(ClockObject.MLimited)
        globalClock.setFrameRate(ani.settings['graphics']['fps'])

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
        self.environment.unload_room()
        self.environment.unload_lights()
        gc.collect()


    def init_system_nodes(self):
        self.init_scene()
        self.table.render()
        self.init_environment()

        for ball in self.balls.values():
            if not ball.rendered:
                ball.render()

        self.cue.render()

        self.player_cam.create_focus(
            parent = self.table.get_node('cloth'),
            pos = self.balls['cue'].get_node('ball').getPos()
        )


    def init_scene(self):
        self.scene = render.attachNewNode('scene')


    def init_environment(self):
        if ani.settings['graphics']['physical_based_rendering']:
            room_path = utils.panda_path(ani.model_dir / 'room/room_pbr.glb')
            floor_path = utils.panda_path(ani.model_dir / 'room/floor_pbr.glb')
        else:
            room_path = utils.panda_path(ani.model_dir / 'room/room.glb')
            floor_path = utils.panda_path(ani.model_dir / 'room/floor.glb')

        self.environment = environment.Environment(self.table)
        if ani.settings['graphics']['room']:
            self.environment.load_room(room_path)
        if ani.settings['graphics']['floor']:
            self.environment.load_floor(floor_path)
        if ani.settings['graphics']['lights']:
            self.environment.load_lights()


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
        self.init_collisions()
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
        if self.setup_options[ani.options_table] != 'custom':
            table_params = copy.deepcopy(ani.table_config[self.setup_options[ani.options_table]])
            table_params['model_name'] = self.setup_options[ani.options_table]
        else:
            table_params = dict(
                type = self.setup_options[ani.options_table_type],
                table_length = self.setup_options[ani.options_table_length],
                table_width = self.setup_options[ani.options_table_width],
                table_height = self.setup_options[ani.options_table_height],
                lights_height = self.setup_options[ani.options_lights_height],
                cushion_width = self.setup_options[ani.options_cushion_width],
                cushion_height = self.setup_options[ani.options_cushion_height],
                corner_pocket_width = self.setup_options[ani.options_corner_pocket_width],
                corner_pocket_angle = self.setup_options[ani.options_corner_pocket_angle],
                corner_pocket_depth = self.setup_options[ani.options_corner_pocket_depth],
                corner_pocket_radius = self.setup_options[ani.options_corner_pocket_radius],
                corner_jaw_radius = self.setup_options[ani.options_corner_jaw_radius],
                side_pocket_width = self.setup_options[ani.options_side_pocket_width],
                side_pocket_angle = self.setup_options[ani.options_side_pocket_angle],
                side_pocket_depth = self.setup_options[ani.options_side_pocket_depth],
                side_pocket_radius = self.setup_options[ani.options_side_pocket_radius],
                side_jaw_radius = self.setup_options[ani.options_side_jaw_radius],
                model_name = self.setup_options[ani.options_table]
            )
        table_type = table_params.pop('type')
        try:
            self.table = table_types[table_type](**table_params)
        except TypeError as e:
            raise TableConfigError(f"Something went wrong with your table config file. Probably you "
                                   f"provided a parameter in the table config that's unrecognized by "
                                   f"pooltool. Here is the error: {e}")


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


    def init_collisions(self):
        """Setup collision detection for cue stick

        Notes
        =====
        - NOTE this Panda3D collision handler is specifically for determining whether the
          cue stick is intersecting with cushions or balls. All other collisions discussed at
          https://ekiefl.github.io/2020/12/20/pooltool-alg/#2-what-are-events are unrelated
          to this.
        """

        base.cTrav = CollisionTraverser()
        self.collision_handler = CollisionHandlerQueue()
        self.cue.init_collision_handling(self.collision_handler)

        for ball in self.balls.values():
            ball.init_collision(self.cue)


    def start(self):
        self.run()


