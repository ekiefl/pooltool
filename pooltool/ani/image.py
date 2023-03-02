from pathlib import Path
from typing import Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
from panda3d.core import ClockObject, FrameBufferProperties, GraphicsOutput, Texture
from PIL import Image

from pooltool.ani.animate import Interface, ShowBaseConfig
from pooltool.ani.camera import CameraState, cam
from pooltool.ani.globals import Global
from pooltool.ani.hud import HUDElement, hud
from pooltool.error import ConfigError
from pooltool.system.datatypes import System, multisystem
from pooltool.system.render import visual
from pooltool.utils.strenum import StrEnum, auto


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
        multisystem.reset()
        multisystem.append(shot)

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
        camera_state: Optional[CameraState] = None,
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
        visual.cue.hide_nodes()

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
        for ball in visual.balls.values():
            ball.set_quats(ball._ball.history_cts)

        frames = int(shot.events[-1].time * fps) + 1

        for frame in range(frames):
            for ball in visual.balls.values():
                ball.set_render_state_from_history(ball._ball.history_cts, frame)

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
