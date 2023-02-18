#! /usr/bin/env python

import gc
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

import gltf  # FIXME at first glance this does nothing?
import matplotlib.pyplot as plt
import numpy as np
import simplepbr
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    ClockObject,
    FrameBufferProperties,
    GraphicsOutput,
    GraphicsWindow,
    TextNode,
    Texture,
    WindowProperties,
)
from PIL import Image

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
import pooltool.games as games
import pooltool.terminal as terminal
import pooltool.utils as utils
from pooltool.ani.camera import CameraState, cam
from pooltool.ani.collision import cue_avoid
from pooltool.ani.environment import environment
from pooltool.ani.globals import Global, require_showbase
from pooltool.ani.hud import HUDElement, hud
from pooltool.ani.menu import GenericMenu, menus
from pooltool.ani.modes import Mode, ModeManager, all_modes
from pooltool.ani.mouse import mouse
from pooltool.error import ConfigError
from pooltool.objects.ball.datatypes import BallParams
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.system.datatypes import MultiSystem, System
from pooltool.system.render import PlaybackMode, visual
from pooltool.utils.strenum import StrEnum, auto


@dataclass
class ShowBaseConfig:
    window_type: Optional[str] = None
    window_size: Optional[Tuple[int, int]] = None
    fb_prop: Optional[FrameBufferProperties] = None
    monitor: bool = False

    @classmethod
    def default(cls):
        return cls(
            window_type="onscreen",
            window_size=None,
            fb_prop=None,
            monitor=False,
        )


@require_showbase
def boop(frames=1):
    """Advance/render a number of frames"""
    for _ in range(frames):
        Global.base.graphicsEngine.renderFrame()


@require_showbase
def window_resize(win=None):
    """Maintain aspect ratio when user resizes window

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

    diff = abs(requested_width / requested_height - ani.aspect_ratio)
    if diff / ani.aspect_ratio < 0.05:
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
    Global.base.win.requestProperties(properties)

    is_window_active = Global.base.win.get_properties().foreground
    if not is_window_active and Global.mode_mgr.mode != Mode.purgatory:
        Global.mode_mgr.change_mode(Mode.purgatory)


class Interface(ShowBase):
    def __init__(self, config: ShowBaseConfig):
        super().__init__(self, windowType=config.window_type)

        self.openMainWindow(fbprops=config.fb_prop, size=config.window_size)

        # Background doesn't apply if ran after simplepbr.init(). See
        # https://discourse.panda3d.org/t/cant-change-base-background-after-simplepbr-init/28945
        Global.base.setBackgroundColor(0.04, 0.04, 0.04)

        simplepbr.init(
            enable_shadows=ani.settings["graphics"]["shadows"], max_lights=13
        )

        if isinstance(self.win, GraphicsWindow):
            mouse.init()

        cam.init()

        if not ani.settings["graphics"]["shader"]:
            Global.render.set_shader_off()

        Global.clock.setMode(ClockObject.MLimited)
        Global.clock.setFrameRate(ani.settings["graphics"]["fps"])

        Global.register_mode_mgr(ModeManager(all_modes))
        Global.mode_mgr.init_modes()

        self.frame = 0
        tasks.add(self.increment_frame, "increment_frame")

        if config.monitor:
            tasks.add(self.monitor, "monitor")

        self.listen_constant_events()
        self.stdout = terminal.Run()

    def listen_constant_events(self):
        """Listen for events that are mode independent"""
        tasks.register_event("window-event", window_resize)
        tasks.register_event("close-scene", self.close_scene)
        tasks.register_event("toggle-help", hud.toggle_help)

    def close_scene(self):
        for shot in Global.multisystem:
            shot.table.render_obj.remove_nodes()
            for ball in shot.balls.values():
                ball.render_obj.teardown()

        environment.unload_room()
        environment.unload_lights()

        hud.destroy()

        if len(Global.multisystem):
            Global.multisystem.render_obj.clear_animation(Global.multisystem)
            Global.multisystem.active_index = None
            Global.multisystem._multisystem = []

        cam.fixation = None
        cam.fixation_object = None
        cam.fixated = False

        gc.collect()

    def create_scene(self):
        """Create a scene from Global.multisystem"""
        Global.render.attachNewNode("scene")

        visual.attach_system(Global.system)
        visual.buildup()

        environment.init(Global.system.table)

        R = max([ball.params.R for ball in Global.system.balls.values()])
        cam.fixate(
            pos=(Global.system.table.w / 2, Global.system.table.l / 2, R),
            node=visual.table.get_node("table"),
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

    def finalizeExit(self):
        """Override ShowBase.finalizeExit to potentially prevent sys.exit call

        See:
        https://docs.panda3d.org/1.10/python/reference/direct.showbase.ShowBase#direct.showbase.ShowBase.ShowBase.finalizeExit
        """
        self.stop()

    def stop(self):
        """Called when window exited. Subclasses can avoid by overwriting this method"""
        sys.exit()


class ShotViewer(Interface):
    """An interface for viewing shots from within a python script"""

    def __init__(self, config=ShowBaseConfig.default()):
        Interface.__init__(self, config=config)
        self.create_standby_screen()
        self.create_title("")

        # Set ShotMode to view only. This prevents giving cue stick control to the user
        # and dictates that esc key closes scene rather than going to a menu
        Global.mode_mgr.modes[Mode.shot].view_only = True

        self.stop()

    def show(self, shot_or_shots=None, title=""):
        if shot_or_shots is None:
            if not len(Global.multisystem):
                raise ConfigError(
                    "ShotViewer.show :: No shots passed and no shots set."
                )
        else:
            if issubclass(type(shot_or_shots), System):
                Global.register_multisystem(MultiSystem())
                Global.multisystem.append(shot_or_shots)
            elif issubclass(type(shot_or_shots), MultiSystem):
                Global.register_multisystem(shot_or_shots)

        if Global.system is None:
            Global.multisystem.set_active(0)

        self.create_scene()

        cam.load_saved_state("last_scene", ok_if_not_exists=True)

        self.standby_screen.hide()
        self.create_title(title)
        self.title_node.show()

        if ani.settings["graphics"]["hud"]:
            hud.init()
            hud.elements[HUDElement.help_text].help_hint.hide()

        params = dict(
            init_animations=True,
            playback_mode=PlaybackMode.LOOP,
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


class ImageFormat(StrEnum):
    PNG = auto()
    JPG = auto()


class ImageSaver(Interface):
    """An interface for saving shots as series of images"""

    def __init__(self, config=None):
        if config is None:
            config = ShowBaseConfig(
                window_type="offscreen",
                monitor=False,
                fb_prop=self.frame_buffer_properties(),
            )

        Interface.__init__(self, config=config)
        self.init_image_texture()

        Global.clock.setMode(ClockObject.MLimited)
        Global.clock.setFrameRate(1000)

    def init_image_texture(self):
        self.tex = Texture()

        Global.base.win.addRenderTexture(
            self.tex, GraphicsOutput.RTMCopyRam, GraphicsOutput.RTPColor
        )

    def make_save_dir(self, save_dir: Union[str, Path]):
        save_dir = Path(save_dir)

        if save_dir.exists():
            raise ConfigError(f"'{self.save_dir}' exists")

        save_dir.mkdir()
        return save_dir

    def _get_filepath(self, save_dir, file_prefix, frame, img_format):
        return f"{save_dir}/{file_prefix}_{frame:06d}.{img_format}"

    def _resize_window(self, size):
        """Changes window size when provided the dimensions (x, y) in pixels"""
        Global.base.win.setSize(*[int(dim) for dim in size])

    def _init_system_collection(self, shot):
        """Create system collection holding the shot. Register to Global"""
        Global.register_multisystem(MultiSystem())
        Global.multisystem.append(shot)
        if Global.system is None:
            Global.multisystem.set_active(0)

    def get_image_array(self):
        """Return array of current image texture, or None if texture has no RAM image"""
        if not self.tex.hasRamImage():
            return None

        array = np.frombuffer(self.tex.getRamImage(), dtype=np.uint8)
        array.shape = (
            self.tex.getYSize(),
            self.tex.getXSize(),
            self.tex.getNumComponents(),
        )

        # This flips things rightside up and orders RGB correctly
        return array[::-1, :, ::-1]

    def save(
        self,
        shot: System,
        save_dir: Union[str, Path],
        camera_state: CameraState = Optional[None],
        file_prefix: str = "shot",
        size: Tuple[int, int] = (230, 144),
        img_format: ImageFormat = ImageFormat.JPG,
        show_hud: bool = False,
        fps: float = 30.0,
        make_gif: bool = False,
    ):
        """Save a shot as a series of images

        Args:
            shot:
                The shot you would like visualized. It should already by simulated. It
                is OK if you have continuized the shot (you can check with
                shot.continuized), but the continuization will be overwritten to match
                the `fps` chosen in this method.
            save_dir:
                The directory that you would like to save the shots in. It must not
                already exist.
            camera_state:
                A camera state specifying the camera's view of the table.
            file_prefix:
                The image filenames will be prefixed with this string. By default, the
                prefix is "shot".
            size:
                The number of pixels in x and y. If x:y != 1.6, the aspect ratio will
                look distorted.
            img_format:
                The image format, e.g. "jpg".
            show_hud:
                If True, the HUD will appear in the images.
            fps:
                This is the rate (in frames per second) that an image of the shot is
                taken.
            make_gif:
                If True, a GIF will be created in addition to the image files. The GIF
                should play in realtime, however in practice this is only the case for
                low res and low fps GIFs.
        """
        shot.continuize(dt=1 / fps)

        self._init_system_collection(shot)
        self._resize_window(size)
        self.create_scene()

        # We don't want the cue in this
        shot.cue.render_obj.hide_nodes()

        if camera_state is not None:
            cam.load_state(camera_state)

        if show_hud:
            hud.init()
            hud.elements[HUDElement.help_text].help_hint.hide()
            hud.update_cue(shot.cue)
        else:
            hud.destroy()

        save_dir = self.make_save_dir(save_dir)

        # Set quaternions for each ball
        for ball in Global.system.balls.values():
            ball.render_obj.set_quats(ball.history_cts)

        frames = int(shot.events[-1].time * fps) + 1

        for frame in range(frames):
            for ball in Global.system.balls.values():
                ball.render_obj.set_render_state_from_history(ball.history_cts, frame)

            Global.task_mgr.step()

            plt.imsave(
                self._get_filepath(save_dir, file_prefix, frame, img_format),
                self.get_image_array(),
            )

        if not make_gif:
            return

        imgs = (
            Image.open(fp)
            for fp in (
                self._get_filepath(save_dir, file_prefix, frame, img_format)
                for frame in range(frames)
            )
        )

        img = next(imgs)

        img.save(
            fp=f"{save_dir}/{file_prefix}.gif",
            format="GIF",
            append_images=imgs,
            save_all=True,
            duration=(1 / fps) * 1e3,
            loop=0,  # loop infinitely
        )

    @staticmethod
    def frame_buffer_properties():
        fb_prop = FrameBufferProperties()
        fb_prop.setRgbColor(True)
        fb_prop.setRgbaBits(8, 8, 8, 0)
        fb_prop.setDepthBits(24)

        return fb_prop


class Game(Interface):
    def __init__(self, config=ShowBaseConfig.default()):
        Interface.__init__(self, config=config)

        # FIXME can this be added to MenuMode.enter? It produces a lot of events that
        # end up being part of the baseline due to the update_event_baseline call below.
        # To see, enter debugger after this command check
        # Global.base.messenger.get_events()
        menus.populate()

        # This task chain allows simulations to be run in parallel to the game processes
        Global.task_mgr.setupTaskChain("simulation", numThreads=1)

        tasks.register_event("enter-game", self.enter_game)

        Global.mode_mgr.update_event_baseline()
        Global.mode_mgr.change_mode(Mode.menu)

    def enter_game(self):
        """Close the menu, setup the visualization, and start the game"""
        menus.hide_all()
        self.create_system()
        self.create_scene()
        cue_avoid.init_collisions()

        if ani.settings["graphics"]["hud"]:
            hud.init()

        Global.mode_mgr.change_mode(Mode.aim)

    def create_system(self):
        """Create the Global.multisystem and game objects

        FIXME this and its calls (setup_*) should probably be a method of some
        MenuOptions class. Since this depends strictly on the menu options, it should
        not belong in this class.
        """
        self.setup_options = menus.get_options()

        game = self.setup_game()

        table = self.setup_table()
        balls = self.setup_balls(table, game.rack)
        cue = self.setup_cue(balls, game)
        shot = System(table=table, balls=balls, cue=cue)

        shots = MultiSystem()
        shots.append(shot)
        shots.set_active(-1)

        game.start(shot)

        Global.register_multisystem(shots)
        Global.game = game

    def start(self):
        Global.task_mgr.run()

    def setup_table(self):
        return Table.default()

    @staticmethod
    def setup_game():
        """Setup the game class from pooltool.games"""
        game = games.game_classes[ani.options_sandbox]()
        game.init()
        return game

    @staticmethod
    def setup_cue(balls, game):
        return Cue(cueing_ball=game.set_initial_cueing_ball(balls))

    @staticmethod
    def setup_balls(table, rack):
        # FIXME Using default BallParams
        return rack(table, ordered=True, params=BallParams()).get_balls_dict()
