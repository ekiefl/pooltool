#! /usr/bin/env python

import gc

import gltf  # FIXME at first glance this does nothing?
import simplepbr
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    ClockObject,
    GraphicsOutput,
    TextNode,
    Texture,
    WindowProperties,
)

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
import pooltool.games as games
import pooltool.terminal as terminal
import pooltool.utils as utils
from pooltool.ani.camera import player_cam
from pooltool.ani.environment import environment
from pooltool.ani.globals import Global, require_showbase
from pooltool.ani.hud import HUDElement, hud
from pooltool.ani.menu import GenericMenu, menus
from pooltool.ani.modes import Mode, ModeManager, all_modes
from pooltool.ani.mouse import mouse
from pooltool.error import ConfigError
from pooltool.objects.cue import Cue, cue_avoid
from pooltool.objects.table import table_types
from pooltool.system import System, SystemCollection


@require_showbase
def boop(frames=1):
    """Advance/render a number of frames"""
    for _ in range(frames):
        Global.base.graphicsEngine.renderFrame()


def showbase_kwargs():
    """Returns parameters that should be passed to the Showbase constructor"""
    window_type = "offscreen" if ani.settings["graphics"]["offscreen"] else None
    return dict(
        windowType=window_type,
    )


class Interface(ShowBase):
    def __init__(self, shot=None, monitor=False):
        super().__init__(self, **showbase_kwargs())

        # Background doesn't apply if ran after simplepbr.init(). See
        # https://discourse.panda3d.org/t/cant-change-base-background-after-simplepbr-init/28945
        Global.base.setBackgroundColor(0.04, 0.04, 0.04)

        simplepbr.init(
            enable_shadows=ani.settings["graphics"]["shadows"], max_lights=13
        )

        if not ani.settings["graphics"]["offscreen"]:
            mouse.init()

        player_cam.init()

        if not ani.settings["graphics"]["shader"]:
            Global.render.set_shader_off()

        Global.clock.setMode(ClockObject.MLimited)
        Global.clock.setFrameRate(ani.settings["graphics"]["fps"])

        Global.register_shots(SystemCollection())
        Global.register_mode_mgr(ModeManager(all_modes))
        Global.mode_mgr.init_modes()

        self.frame = 0
        tasks.add(self.increment_frame, "increment_frame")

        if monitor:
            tasks.add(self.monitor, "monitor")

        self.listen_constant_events()
        self.stdout = terminal.Run()

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
        requested_width = Global.base.win.getXSize()
        requested_height = Global.base.win.getYSize()

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

        is_window_active = Global.base.win.get_properties().foreground
        if not is_window_active and Global.mode_mgr.mode != Mode.purgatory:
            Global.mode_mgr.change_mode(Mode.purgatory)

    def listen_constant_events(self):
        """Listen for events that are mode independent"""
        tasks.register_event("window-event", self.handle_window_event)
        tasks.register_event("close-scene", self.close_scene)
        tasks.register_event("toggle-help", hud.toggle_help)

    def close_scene(self):
        for shot in Global.shots:
            shot.table.remove_nodes()
            for ball in shot.balls.values():
                ball.teardown()

        environment.unload_room()
        environment.unload_lights()

        hud.destroy()

        if len(Global.shots):
            Global.shots.clear_animation()
            Global.shots.clear()

        player_cam.focus = None
        player_cam.has_focus = False

        gc.collect()

    def init_system_nodes(self):
        Global.render.attachNewNode("scene")
        Global.shots.active.table.render()
        environment.init(Global.shots.active.table)

        # Render the balls of the active shot
        for ball in Global.shots.active.balls.values():
            if not ball.rendered:
                ball.render()

        Global.shots.active.cue.render()

        R = max([ball.R for ball in Global.shots.active.balls.values()])
        player_cam.create_focus(
            parent=Global.shots.active.table.get_node("cloth"),
            pos=(Global.shots.active.table.w / 2, Global.shots.active.table.l / 2, R),
        )

    def monitor(self, task):
        if Global.mode_mgr.mode == Mode.purgatory or Global.mode_mgr.mode is None:
            return task.cont

        keymap = Global.mode_mgr.get_keymap()
        self.stdout.warning(
            "", header=f"Frame {self.frame}", lc="green", nl_before=1, nl_after=0
        )
        self.stdout.info("Mode", Global.mode_mgr.mode)
        self.stdout.info("Last", Global.mode_mgr.last_mode)
        self.stdout.info("Tasks", [task.name for task in Global.task_mgr.getAllTasks()])
        self.stdout.info("Memory", utils.get_total_memory_usage())
        self.stdout.info("Actions", [k for k in keymap if keymap[k]])
        self.stdout.info("Keymap", Global.mode_mgr.get_keymap())
        self.stdout.info("Frame", self.frame)

        return task.cont

    def increment_frame(self, task):
        self.frame += 1
        return task.cont

    def start(self):
        Global.task_mgr.run()


class ShotViewer(Interface):
    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        self.create_standby_screen()
        self.create_title("")

        # Set ShotMode to view only. This prevents giving cue stick control to the user
        # and dictates that esc key closes scene rather than going to a menu
        Global.mode_mgr.modes[Mode.shot].view_only = True

        self.stop()

    def show(self, shot_or_shots=None, title=""):
        if shot_or_shots is None:
            if not len(Global.shots):
                raise ConfigError(
                    "ShotViewer.show :: No shots passed and no shots set."
                )
        else:
            if issubclass(type(shot_or_shots), System):
                Global.register_shots(SystemCollection())
                Global.shots.append(shot_or_shots)
            elif issubclass(type(shot_or_shots), SystemCollection):
                Global.register_shots(shot_or_shots)

        if Global.shots.active is None:
            Global.shots.set_active(0)

        self.init_system_nodes()

        player_cam.load_state("last_scene", ok_if_not_exists=True)

        self.standby_screen.hide()
        self.create_title(title)
        self.title_node.show()

        if ani.settings["graphics"]["hud"]:
            hud.init()
            hud.elements[HUDElement.help_text].help_hint.hide()

        params = dict(
            init_animations=True,
        )
        Global.mode_mgr.update_event_baseline()
        Global.mode_mgr.change_mode(Mode.shot, enter_kwargs=params)
        Global.task_mgr.run()

    def listen_constant_events(self):
        """Listen for events that are mode independent"""
        Interface.listen_constant_events(self)
        tasks.register_event("stop", self.stop)

    def create_title(self, title):
        self.title_node = OnscreenText(
            text=title,
            pos=(-1.55, -0.93),
            scale=ani.menu_text_scale * 0.7,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            parent=Global.aspect2d,
        )
        self.title_node.hide()

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

    def stop(self):
        """Display the standby screen and halt the main loop"""

        self.standby_screen.show()
        self.title_node.hide()

        # Advance a couple of frames to render changes
        boop(2)

        # Stop the main loop
        Global.task_mgr.stop()

    def finalizeExit(self):
        """Override ShowBase.finalizeExit to prevent sys.exit call

        See:
        https://docs.panda3d.org/1.10/python/reference/direct.showbase.ShowBase#direct.showbase.ShowBase.ShowBase.finalizeExit
        """
        self.stop()


class ShotSaver(Interface):
    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)
        self.init_texture()

        # Set ShotMode to view only. This prevents giving cue stick control to the user
        # and dictates that esc key closes scene rather than going to a menu
        Global.mode_mgr.modes[Mode.shot].view_only = True

    def init_texture(self):
        self.tex = Texture()

        Global.base.win.addRenderTexture(
            self.tex, GraphicsOutput.RTMCopyRam, GraphicsOutput.RTPColor
        )

    def show(self, shot):
        Global.register_shots(SystemCollection())
        Global.shots.append(shot)

        if Global.shots.active is None:
            Global.shots.set_active(0)

        self.init_system_nodes()
        player_cam.load_state("last_scene", ok_if_not_exists=True)

        params = dict(
            init_animations=True,
        )
        Global.mode_mgr.update_event_baseline()
        Global.mode_mgr.change_mode(Mode.shot, enter_kwargs=params)
        Global.task_mgr.run()


class Play(Interface):
    def __init__(self, *args, **kwargs):
        Interface.__init__(self, *args, **kwargs)

        # FIXME can this be added to MenuMode.enter? It produces a lot of events that
        # end up being part of the baseline due to the update_event_baseline call below.
        # To see, enter debugger after this command check
        # Global.base.messenger.get_events()
        menus.populate()

        # This task chain allows simulations to be run in parallel to the game processes
        Global.task_mgr.setupTaskChain(
            "simulation",
            numThreads=1,
            tickClock=None,
            threadPriority=None,
            frameBudget=None,
            frameSync=None,
            timeslicePriority=None,
        )

        Global.mode_mgr.update_event_baseline()
        Global.mode_mgr.change_mode(Mode.menu)

    def listen_constant_events(self):
        """Listen for events that are mode independent"""
        Interface.listen_constant_events(self)
        tasks.register_event("go", self.go)

    def go(self):
        menus.hide_all()

        Global.register_shots(SystemCollection())
        Global.shots.append(System())
        Global.shots.set_active(-1)

        self.setup()
        self.init_system_nodes()

        cue_avoid.init_collisions()

        Global.mode_mgr.change_mode(Mode.aim)

    def setup(self):
        self.setup_options = menus.get_options()

        self.setup_table()
        self.setup_game()
        self.setup_balls()
        self.setup_cue()

        if ani.settings["graphics"]["hud"]:
            hud.init()

    def setup_table(self):
        selected_table = self.setup_options["table_type"]
        table_config = ani.load_config("tables")
        table_params = table_config[selected_table]
        table_params["model_name"] = selected_table
        table_type = table_params.pop("type")
        Global.shots.active.table = table_types[table_type](**table_params)

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

        # FIXME use what use to be self.setup_options[ani.options_game] to determine the
        # game type, instead of hardcoding ani.options_sandbox
        game_class = games.game_classes[ani.options_sandbox]

        # Register the game under the Global namespace
        Global.game = game_class()
        Global.game.init(Global.shots.active.table, ball_kwargs)
        Global.game.start()

    def setup_cue(self):
        Global.shots.active.cue = Cue(
            cueing_ball=Global.game.set_initial_cueing_ball(Global.shots.active.balls)
        )

    def setup_balls(self):
        Global.shots.active.balls = Global.game.balls
