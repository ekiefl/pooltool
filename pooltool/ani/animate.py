#! /usr/bin/env python

import gc

import gltf  # FIXME at first glance this does nothing?
import simplepbr
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    ClockObject,
    CollisionHandlerQueue,
    CollisionTraverser,
    TextNode,
    WindowProperties,
)

import pooltool as pt
import pooltool.ani as ani
import pooltool.ani.environment as environment
import pooltool.games as games
from pooltool.ani.camera import PlayerCam
from pooltool.ani.hud import hud
from pooltool.ani.menu import GenericMenu, Menus
from pooltool.ani.modes import (
    AimMode,
    BallInHandMode,
    CalculateMode,
    CallShotMode,
    CamLoadMode,
    CamSaveMode,
    GameOverMode,
    MenuMode,
    PickBallMode,
    PurgatoryMode,
    ShotMode,
    StrokeMode,
    ViewMode,
    modes,
)
from pooltool.ani.modes.datatypes import Mode
from pooltool.ani.mouse import Mouse
from pooltool.error import ConfigError
from pooltool.objects.cue import Cue
from pooltool.objects.table import table_types
from pooltool.system import System, SystemCollection


class ModeManager(
    MenuMode,
    AimMode,
    StrokeMode,
    ViewMode,
    ShotMode,
    CamLoadMode,
    CamSaveMode,
    CalculateMode,
    PickBallMode,
    GameOverMode,
    CallShotMode,
    BallInHandMode,
    PurgatoryMode,
):
    def __init__(self):
        # Init every Mode class
        self.modes = modes
        for mode_cls in modes.values():
            mode_cls.__init__(self)

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
        assert mode in Mode

        # Teardown operations for the old mode
        self.last_mode = self.mode
        self.end_mode(**exit_kwargs)

        # Build up operations for the new mode
        self.mode = mode
        self.keymap = self.modes[mode].keymap
        self.modes[mode].enter(self, **enter_kwargs)

    def end_mode(self, **kwargs):
        # Stop watching actions related to mode
        self.reset_event_listeners()

        if self.mode is not None:
            self.modes[self.mode].exit(self, **kwargs)
            self.reset_action_states()

        self.mode = None

    def reset_event_listeners(self):
        """Stop watching for events related to the current mode

        Something a bit clunky is happening here. Since the keystrokes assigned to tasks
        are hardcoded into the `enter` method of each mode, it is not known which event
        listeners belong to the mode, and which are active regardless of mode.
        Consequently, the best strategy (besides refactoring) is to wipe all listeners,
        and then re-instate the global listeners.
        """
        # Stop listening for all actions
        self.ignoreAll()

        # Reinstate the listeners for mode-independent events
        self.listen_constant_events()

    def reset_action_states(self):
        for key in self.keymap:
            self.keymap[key] = self.action_state_defaults[self.mode][key]


class Interface(ShowBase, ModeManager):
    is_game = None

    def __init__(self, shot=None, monitor=False):
        if self.is_game is None:
            raise Exception(f"'{self.__class__.__name__}' must set 'is_game' attribute")

        self.stdout = pt.terminal.Run()

        super().__init__(self)

        # Panda pollutes the global namespace, appease linters
        self.global_clock = __builtins__["globalClock"]
        self.global_render = __builtins__["render"]
        self.aspect2d = __builtins__["aspect2d"]
        self.task_mgr = __builtins__["taskMgr"]
        self.base = __builtins__["base"]

        self.base.setBackgroundColor(0.04, 0.04, 0.04)
        simplepbr.init(
            enable_shadows=ani.settings["graphics"]["shadows"], max_lights=13
        )

        if not ani.settings["graphics"]["shader"]:
            self.global_render.set_shader_off()

        self.global_clock.setMode(ClockObject.MLimited)
        self.global_clock.setFrameRate(ani.settings["graphics"]["fps"])

        self.shots = SystemCollection()

        self.disableMouse()
        self.mouse = Mouse()
        self.player_cam = PlayerCam()

        ModeManager.__init__(self)

        self.scene = None

        self.frame = 0
        self.add_task(self.increment_frame, "increment_frame")

        if monitor:
            self.add_task(self.monitor, "monitor")

    def fix_window_resize(self, win=None):
        """Fix aspect ratio of window upon user resizing

        The user can modify the game window to be whatever size they want. Ideally, they
        would be able to pick arbitrary aspect ratios, however this project has been
        hardcoded to run at a specific aspect ratio, otherwise it looks
        stretched/squished.

        With that in mind, this method is called whenever a change to the window occurs,
        and essentially fixes the aspect ratio. For any given window size chosen by the
        user, this will override their resizing, and resize the window to one with an
        area equal to that requested, but at the required aspect ratio.
        """
        requested_width = self.base.win.getXSize()
        requested_height = self.base.win.getYSize()

        if (
            abs(requested_width / requested_height - ani.aspect_ratio)
            / ani.aspect_ratio
            < 0.05
        ):
            # If they are within 5% of the intended ratio, just let them be.
            return

        requested_area = requested_width * requested_height

        # A = w*h
        # A = r*h*h
        # h = (A/r)^(1/2)
        height = (requested_area / ani.aspect_ratio) ** (1 / 2)
        width = height * ani.aspect_ratio

        properties = WindowProperties()
        properties.setSize(int(width), int(height))
        self.win.requestProperties(properties)

    def handle_window_event(self, win=None):
        self.fix_window_resize(win=win)

        is_window_active = self.base.win.get_properties().foreground
        if not is_window_active and self.mode != Mode.purgatory:
            self.change_mode(Mode.purgatory)

    def listen_constant_events(self):
        """Listen for events that are mode independent"""
        self.accept("window-event", self.handle_window_event)

    def add_task(self, func, name, *args, **kwargs):
        if not self.has_task(name):
            # If the task already exists, don't add it again
            self.task_mgr.add(func, name, *args, **kwargs)

    def add_task_later(self, *args, **kwargs):
        self.task_mgr.doMethodLater(*args, **kwargs)

    def remove_task(self, name):
        self.task_mgr.remove(name)

    def has_task(self, name):
        return self.task_mgr.hasTaskNamed(name)

    def close_scene(self):
        for shot in self.shots:
            shot.table.remove_nodes()
            for ball in shot.balls.values():
                ball.teardown()

        self.environment.unload_room()
        self.environment.unload_lights()

        hud.destroy_hud()
        self.remove_task("update_hud")

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
            parent=self.shots.active.table.get_node("cloth"),
            pos=(self.shots.active.table.w / 2, self.shots.active.table.l / 2, R),
        )

    def init_scene(self):
        self.scene = self.global_render.attachNewNode("scene")

    def init_environment(self):
        if ani.settings["graphics"]["physical_based_rendering"]:
            room_path = pt.utils.panda_path(ani.model_dir / "room/room_pbr.glb")
            floor_path = pt.utils.panda_path(ani.model_dir / "room/floor_pbr.glb")
        else:
            room_path = pt.utils.panda_path(ani.model_dir / "room/room.glb")
            floor_path = pt.utils.panda_path(ani.model_dir / "room/floor.glb")

        self.environment = environment.Environment(self.shots.active.table)
        if ani.settings["graphics"]["room"]:
            self.environment.load_room(room_path)
        if ani.settings["graphics"]["floor"]:
            self.environment.load_floor(floor_path)
        if ani.settings["graphics"]["lights"]:
            self.environment.load_lights()

    def init_collisions(self):
        """Setup collision detection for cue stick

        Notes
        =====
        - NOTE this Panda3D collision handler is specifically for determining whether
          the cue stick is intersecting with cushions or balls. All other collisions
          discussed at
          https://ekiefl.github.io/2020/12/20/pooltool-alg/#2-what-are-events are
          unrelated to this.
        """

        self.base.cTrav = CollisionTraverser()
        self.collision_handler = CollisionHandlerQueue()

        self.shots.active.cue.init_collision_handling(self.collision_handler)
        for ball in self.shots.active.balls.values():
            ball.init_collision(self.shots.active.cue)

    def monitor(self, task):
        self.stdout.warning(
            "", header=f"Frame {self.frame}", lc="green", nl_before=1, nl_after=0
        )
        self.stdout.info("Mode", self.mode)
        self.stdout.info("Last", self.last_mode)
        self.stdout.info("Tasks", [task.name for task in self.task_mgr.getAllTasks()])
        self.stdout.info("Memory", pt.utils.get_total_memory_usage())
        self.stdout.info("Actions", [k for k in self.keymap if self.keymap[k]])
        self.stdout.info("Keymap", self.keymap)
        self.stdout.info("Frame", self.frame)

        return task.cont

    def increment_frame(self, task):
        self.frame += 1
        return task.cont

    def init_help_page(self):
        self.help_hint = OnscreenText(
            text="Press 'h' to toggle help",
            pos=(-1.55, 0.93),
            scale=ani.menu_text_scale * 0.9,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            parent=self.aspect2d,
        )
        self.help_hint.show()

        self.help_node = self.aspect2d.attachNewNode("help")

        def add_instruction(pos, msg, title=False):
            text = OnscreenText(
                text=msg,
                style=1,
                fg=(1, 1, 1, 1),
                parent=self.base.a2dTopLeft,
                align=TextNode.ALeft,
                pos=(-1.45 if not title else -1.55, 0.85 - pos),
                scale=ani.menu_text_scale if title else 0.7 * ani.menu_text_scale,
            )
            text.reparentTo(self.help_node)

        def hrow(x):
            return 0.06 * x

        add_instruction(hrow(1), "Camera controls", True)
        add_instruction(hrow(2), "Rotate - [mouse]")
        add_instruction(hrow(3), "Pan - [hold v + mouse]")
        add_instruction(hrow(4), "Zoom - [hold left-click + mouse]")

        add_instruction(hrow(6), "Aim controls", True)
        add_instruction(hrow(7), "Enter aim mode - [a]")
        add_instruction(hrow(8), "Apply english - [hold e + mouse]")
        add_instruction(hrow(9), "Elevate cue - [hold b + mouse]")
        add_instruction(hrow(10), "Precise aiming - [hold f + mouse]")
        add_instruction(hrow(11), "Raise head - [hold t + mouse]")

        add_instruction(hrow(13), "Shot controls", True)
        add_instruction(hrow(14), "Stroke - [hold s] (move mouse down then up)")
        add_instruction(hrow(15), "Take next shot - [a]")
        add_instruction(hrow(16), "Undo shot - [z]")
        add_instruction(hrow(17), "Replay shot - [r]")
        add_instruction(hrow(18), "Pause shot - [space]")
        add_instruction(hrow(19), "Rewind - [hold left-arrow]")
        add_instruction(hrow(20), "Fast forward - [hold right-arrow]")
        add_instruction(hrow(21), "Slow down - [down-arrow]")
        add_instruction(hrow(22), "Speed up - [up-arrow]")

        add_instruction(hrow(24), "Other controls", True)
        add_instruction(
            hrow(25),
            "Cue different ball - [hold q]\n    (select with mouse, click to confirm)",
        )
        add_instruction(
            hrow(27),
            "Move ball - [hold g]\n    (click once to select ball, move with mouse, "
            "then click to confirm move",
        )

        self.help_node.hide()


class ShotViewer(Interface):
    is_game = False

    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        self.create_standby_screen()
        self.create_instructions()
        self.create_title("")

        self.stop()

    def create_title(self, title):
        self.title_node = OnscreenText(
            text=title,
            pos=(-1.55, -0.93),
            scale=ani.menu_text_scale * 0.7,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            parent=self.aspect2d,
        )
        self.title_node.hide()

    def create_instructions(self):
        self.instructions = OnscreenText(
            text="Press <escape> to exit",
            pos=(-1.55, 0.93),
            scale=ani.menu_text_scale * 0.7,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            parent=self.aspect2d,
        )
        self.instructions.hide()

    def create_standby_screen(self):
        self.standby_screen = GenericMenu(frame_color=(0.3, 0.3, 0.3, 1))
        self.standby_screen.add_image(
            ani.logo_paths["default"], pos=(0, 0, 0), scale=(0.5, 1, 0.44)
        )

        OnscreenText(
            text="GUI standing by...",
            style=1,
            fg=(1, 1, 1, 1),
            parent=self.standby_screen.titleMenu,
            align=TextNode.ALeft,
            pos=(-1.55, 0.93),
            scale=0.8 * ani.menu_text_scale,
        )

    def show(self, shot_or_shots=None, title=""):

        if shot_or_shots is None:
            # No passed shots. This is ok if self.shots has already been defined, but
            # will complain otherwise
            if not len(self.shots):
                raise ConfigError(
                    "ShotViewer.show :: No shots passed and no shots set."
                )
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

        hud_task = hud.init_hud()
        self.add_task(hud_task, "update_hud")

        params = dict(
            init_animations=True,
            single_instance=True,
        )
        self.change_mode(Mode.shot, enter_kwargs=params)

        self.player_cam.load_state("last_scene", ok_if_not_exists=True)

        self.taskMgr.run()

    def stop(self):
        self.standby_screen.show()
        self.instructions.hide()
        self.title_node.hide()
        self.base.graphicsEngine.renderFrame()
        self.base.graphicsEngine.renderFrame()

        self.taskMgr.stop()

    def finalizeExit(self):
        self.stop()


class Play(Interface, Menus):
    is_game = True

    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        Menus.__init__(self)

        self.change_mode(Mode.menu)

        # This task chain allows simulations to be run in parallel to the game processes
        self.task_mgr.setupTaskChain(
            "simulation",
            numThreads=1,
            tickClock=None,
            threadPriority=None,
            frameBudget=None,
            frameSync=None,
            timeslicePriority=None,
        )

    def go(self):
        self.hide_menus()

        self.shots = SystemCollection()
        self.shots.append(System())
        self.shots.set_active(-1)

        self.init_help_page()
        self.setup()
        self.init_system_nodes()
        self.init_collisions()
        self.change_mode(Mode.aim)

    def close_scene(self):
        Interface.close_scene(self)

    def setup(self):
        self.setup_options = self.get_menu_options()

        self.setup_table()
        self.setup_game()
        self.setup_balls()
        self.setup_cue()

        hud.attach_game(self.game)
        hud_task = hud.init_hud()
        self.add_task(hud_task, "update_hud")

    def setup_table(self):
        selected_table = self.setup_options["table_type"]
        table_config = ani.load_config("tables")
        table_params = table_config[selected_table]
        table_params["model_name"] = selected_table
        table_type = table_params.pop("type")
        self.shots.active.table = table_types[table_type](**table_params)

    def setup_game(self):
        """Setup the game class from pooltool.games

        Notes
        =====
        - For reasons of bad design, ball kwargs are defined in this method
        """

        # FIXME
        # ball_kwargs = dict(
        #    R = self.setup_options[ani.options_ball_diameter]/2,
        #    u_s = self.setup_options[ani.options_friction_slide],
        #    u_r = self.setup_options[ani.options_friction_roll],
        #    u_sp = self.setup_options[ani.options_friction_spin],
        #    f_c = self.setup_options[ani.options_friction_cushion],
        #    e_c = self.setup_options[ani.options_restitution_cushion],
        # )

        ball_kwargs = dict(
            R=0.028575,  # ball radius
            u_s=0.2,  # sliding friction
            u_r=0.01,  # rolling friction
            u_sp=10 * 2 / 5 * 0.028575 / 9,  # spinning friction
            f_c=0.2,  # cushion coeffiient of friction
            e_c=0.85,  # cushion coeffiient of restitution
        )

        # FIXME
        # game_class = games.game_classes[self.setup_options[ani.options_game]]
        game_class = games.game_classes[ani.options_sandbox]
        self.game = game_class()
        self.game.init(self.shots.active.table, ball_kwargs)
        self.game.start()

    def setup_cue(self):
        self.shots.active.cue = Cue(
            cueing_ball=self.game.set_initial_cueing_ball(self.shots.active.balls)
        )

    def setup_balls(self):
        self.shots.active.balls = self.game.balls

    def start(self):
        self.run()
