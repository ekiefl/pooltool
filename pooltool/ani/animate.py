#! /usr/bin/env python

import pooltool as pt
import pooltool.ani as ani
import pooltool.games as games
import pooltool.ani.environment as environment

from pooltool.error import TableConfigError, ConfigError
from pooltool.system import SystemCollection
from pooltool.objects.cue import Cue
from pooltool.objects.ball import Ball
from pooltool.objects.table import table_types
from pooltool.games.nine_ball import NineBall
from pooltool.games.eight_ball import EightBall

from pooltool.ani.hud import HUD
from pooltool.ani.menu import Menus, GenericMenu
from pooltool.ani.modes import *
from pooltool.ani.mouse import Mouse
from pooltool.ani.camera import PlayerCam

import gc
import copy
import gltf
import simplepbr

from panda3d.core import *
from direct.showbase.ShowBase import ShowBase

__all__ = [
    'ShotViewer',
    'Play',
]


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


class Interface(ShowBase, ModeManager, HUD):
    is_game = None
    def __init__(self, shot=None, monitor=False):
        if self.is_game is None:
            raise Exception(f"'{self.__class__.__name__}' must set 'is_game' attribute")

        self.stdout = pt.terminal.Run()

        super().__init__(self)
        HUD.__init__(self)
        base.setBackgroundColor(0.04, 0.04, 0.04)
        simplepbr.init(enable_shadows=ani.settings['graphics']['shadows'], max_lights=13)

        if not ani.settings['graphics']['shader']:
            render.set_shader_off()

        globalClock.setMode(ClockObject.MLimited)
        globalClock.setFrameRate(ani.settings['graphics']['fps'])

        self.shots = SystemCollection()

        self.tasks = {}
        self.disableMouse()
        self.mouse = Mouse()
        self.player_cam = PlayerCam()

        ModeManager.__init__(self)

        self.scene = None

        self.frame = 0
        self.add_task(self.increment_frame, 'increment_frame')

        if monitor:
            self.add_task(self.monitor, 'monitor')


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
        for shot in self.shots:
            shot.table.remove_nodes()
            for ball in shot.balls.values():
                ball.teardown()

        self.environment.unload_room()
        self.environment.unload_lights()
        self.destroy_hud()

        if len(self.shots):
            self.shots.clear_animation()
            self.shots.clear()

        self.player_cam.focus = None
        self.player_cam.has_focus = False

        gc.collect()


    def init_system_nodes(self):
        self.init_scene()
        self.shots.active.table.render()
        self.init_environment()

        # Render the balls of the active shot
        for ball in self.shots.active.balls.values():
            if not ball.rendered:
                ball.render()

        self.shots.active.cue.render()

        R = max([ball.R for ball in self.shots.active.balls.values()])
        self.player_cam.create_focus(
            parent = self.shots.active.table.get_node('cloth'),
            pos = (self.shots.active.table.w/2, self.shots.active.table.l/2, R)
        )


    def init_scene(self):
        self.scene = render.attachNewNode('scene')


    def init_environment(self):
        if ani.settings['graphics']['physical_based_rendering']:
            room_path = pt.utils.panda_path(ani.model_dir / 'room/room_pbr.glb')
            floor_path = pt.utils.panda_path(ani.model_dir / 'room/floor_pbr.glb')
        else:
            room_path = pt.utils.panda_path(ani.model_dir / 'room/room.glb')
            floor_path = pt.utils.panda_path(ani.model_dir / 'room/floor.glb')

        self.environment = environment.Environment(self.shots.active.table)
        if ani.settings['graphics']['room']:
            self.environment.load_room(room_path)
        if ani.settings['graphics']['floor']:
            self.environment.load_floor(floor_path)
        if ani.settings['graphics']['lights']:
            self.environment.load_lights()


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

        self.shots.active.cue.init_collision_handling(self.collision_handler)
        for ball in self.shots.active.balls.values():
            ball.init_collision(self.shots.active.cue)


    def monitor(self, task):
        self.stdout.warning('', header=f"Frame {self.frame}", lc='green', nl_before=1, nl_after=0)
        self.stdout.info('Mode', self.mode)
        self.stdout.info('Tasks', list(self.tasks.keys()))
        self.stdout.info('Memory', pt.utils.get_total_memory_usage())
        self.stdout.info('Actions', [k for k in self.keymap if self.keymap[k]])
        self.stdout.info('Keymap', self.keymap)
        self.stdout.info('Frame', self.frame)

        return task.cont


    def increment_frame(self, task):
        self.frame += 1
        return task.cont


    def init_help_page(self):
        self.help_hint = OnscreenText(
            text = "Press 'h' to toggle help",
            pos = (-1.55, 0.93),
            scale = ani.menu_text_scale*0.9,
            fg = (1,1,1,1),
            align = TextNode.ALeft,
            parent = aspect2d,
        )
        self.help_hint.show()

        self.help_node = aspect2d.attachNewNode('help')

        def add_instruction(pos, msg, title=False):
            text = OnscreenText(
                text = msg,
                style = 1,
                fg = (1, 1, 1, 1),
                parent = base.a2dTopLeft,
                align = TextNode.ALeft,
                pos = (-1.45 if not title else -1.55, 0.85-pos),
                scale = ani.menu_text_scale if title else 0.7*ani.menu_text_scale,
            )
            text.reparentTo(self.help_node)

        h = lambda x: 0.06*x
        add_instruction(h(1), "Camera controls", True)
        add_instruction(h(2), "Rotate - [mouse]")
        add_instruction(h(3), "Pan - [hold v]")
        add_instruction(h(4), "Zoom - [hold left-click]")

        add_instruction(h(6), "Aim controls", True)
        add_instruction(h(7), "Enter aim mode - [a]")
        add_instruction(h(8), "Apply english - [hold e]")
        add_instruction(h(9), "Elevate cue - [hold b]")
        add_instruction(h(10), "Precise aiming - [hold f]")
        add_instruction(h(11), "Raise head - [hold t]")

        add_instruction(h(13), "Shot controls", True)
        add_instruction(h(14), "Stroke - [hold s] (move mouse down then up)")
        add_instruction(h(15), "Take next shot - [a]")
        add_instruction(h(16), "Undo shot - [z]")
        add_instruction(h(17), "Replay shot - [r]")
        add_instruction(h(18), "Pause shot - [space]")
        add_instruction(h(19), "Rewind - [hold left-arrow]")
        add_instruction(h(20), "Fast forward - [hold right-arrow]")
        add_instruction(h(21), "Slow down - [down-arrow]")
        add_instruction(h(22), "Speed up - [up-arrow]")

        add_instruction(h(24), "Other controls", True)
        add_instruction(h(25), "Cue different ball - [hold q]\n    (select with mouse, click to confirm)")
        add_instruction(h(27), "Move ball - [hold g]\n    (click once to select ball, move with mouse, then click to confirm move")

        self.help_node.hide()


class ShotViewer(Interface):
    is_game = False

    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        self.create_standby_screen()
        self.create_instructions()
        self.create_title('')

        self.stop()


    def create_title(self, title):
        self.title_node = OnscreenText(
            text = title,
            pos = (-1.55, -0.93),
            scale = ani.menu_text_scale*0.7,
            fg = (1,1,1,1),
            align = TextNode.ALeft,
            parent = aspect2d,
        )
        self.title_node.hide()


    def create_instructions(self):
        self.instructions = OnscreenText(
            text = "Press <escape> to exit",
            pos = (-1.55, 0.93),
            scale = ani.menu_text_scale*0.7,
            fg = (1,1,1,1),
            align = TextNode.ALeft,
            parent = aspect2d,
        )
        self.instructions.hide()


    def create_standby_screen(self):
        self.standby_screen = GenericMenu(frame_color=(0.3,0.3,0.3,1))
        self.standby_screen.add_image(ani.logo_paths['default'], pos=(0,0,0), scale=(0.5, 1, 0.44))

        text = OnscreenText(
            text = 'GUI standing by...',
            style = 1,
            fg = (1, 1, 1, 1),
            parent = self.standby_screen.titleMenu,
            align = TextNode.ALeft,
            pos = (-1.55,0.93),
            scale = 0.8*ani.menu_text_scale,
        )


    def show(self, shot_or_shots=None, title=''):

        if shot_or_shots is None:
            # No passed shots. This is ok if self.shots has already been defined, but will complain
            # otherwise
            if not len(self.shots):
                raise ConfigError("ShotViewer.show :: No shots passed and no shots set.")
        else:
            # Create a new SystemCollection based on type of shot_or_shots
            if issubclass(type(shot_or_shots), System):
                self.shots = SystemCollection()
                self.shots.append(shot_or_shots)
            elif issubclass(type(shot_or_shots), SystemCollection):
                self.shots = shot_or_shots

        if self.shots.active is None:
            self.shots.set_active(0)

        self.standby_screen.hide()
        self.instructions.show()
        self.create_title(title)
        self.title_node.show()
        self.init_help_page()
        self.help_hint.hide()
        self.mouse = Mouse()
        self.init_system_nodes()
        self.init_hud()

        params = dict(
            init_animations = True,
            single_instance = True,
        )
        self.change_mode('shot', enter_kwargs=params)

        self.player_cam.load_state('last_scene', ok_if_not_exists=True)

        self.taskMgr.run()


    def stop(self):
        self.standby_screen.show()
        self.instructions.hide()
        self.title_node.hide()
        base.graphicsEngine.renderFrame()
        base.graphicsEngine.renderFrame()

        self.taskMgr.stop()


    def finalizeExit(self):
        self.stop()


class Play(Interface, Menus):
    is_game = True

    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        Menus.__init__(self)

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
        self.shots = SystemCollection()
        self.shots.append(System())
        self.shots.set_active(-1)

        self.init_help_page()
        self.setup()
        self.init_system_nodes()
        self.init_collisions()
        self.change_mode('aim')


    def close_scene(self):
        Interface.close_scene(self)


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
                l = self.setup_options[ani.options_table_length],
                w = self.setup_options[ani.options_table_width],
                height = self.setup_options[ani.options_table_height],
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
                model_name = self.setup_options[ani.options_table],
            )
        table_type = table_params.pop('type')
        try:
            self.shots.active.table = table_types[table_type](**table_params)
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
            f_c = self.setup_options[ani.options_friction_cushion],
            e_c = self.setup_options[ani.options_restitution_cushion],
        )

        game_class = games.game_classes[self.setup_options[ani.options_game]]
        self.game = game_class()
        self.game.init(self.shots.active.table, ball_kwargs)
        self.game.start()


    def setup_cue(self):
        self.shots.active.cue = Cue(cueing_ball = self.game.set_initial_cueing_ball(self.shots.active.balls))


    def setup_balls(self):
        self.shots.active.balls = self.game.balls


    def start(self):
        self.run()


