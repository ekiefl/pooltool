from pathlib import Path
from typing import List, Optional, Tuple, Union

import attrs
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
from panda3d.core import ClockObject, FrameBufferProperties, GraphicsOutput, Texture
from PIL import Image

from pooltool.ani.animate import Interface, ShowBaseConfig
from pooltool.ani.camera import CameraState, cam, camera_states
from pooltool.ani.globals import Global
from pooltool.ani.hud import HUDElement, hud
from pooltool.system.datatypes import System, multisystem
from pooltool.system.render import visual
from pooltool.utils.strenum import StrEnum, auto

DEFAULT_FBP = FrameBufferProperties()
DEFAULT_FBP.setRgbColor(True)
DEFAULT_FBP.setRgbaBits(8, 8, 8, 0)
DEFAULT_FBP.setDepthBits(24)

DEFAULT_SHOWBASE_CONFIG = ShowBaseConfig(
    window_type="offscreen",
    monitor=False,
    fb_prop=DEFAULT_FBP,
)


class ImageExt(StrEnum):
    PNG = auto()
    JPG = auto()


def _resize_window(size):
    """Changes window size when provided the dimensions (x, y) in pixels"""
    Global.base.win.setSize(*[int(dim) for dim in size])


def _init_system_collection(shot):
    """Reset the multisystem and add the shot of interest"""
    multisystem.reset()
    multisystem.append(shot)


@attrs.define
class ImageExport:
    save_dir: Union[str, Path] = attrs.field(converter=Path)
    ext: ImageExt = attrs.field(converter=ImageExt)
    prefix: str = attrs.field(default="shot")
    image_count: int = attrs.field(default=0)
    paths: List[Path] = attrs.field(factory=list)

    def __attrs_post_init__(self):
        if not self.save_dir.exists():
            self.save_dir.mkdir(parents=True)

    def save(self, img: NDArray[np.uint8]) -> Path:
        """Save an image"""
        path = self._get_filepath()
        assert not path.exists()

        plt.imsave(path, img)

        # Increment
        self.image_count += 1
        self.paths.append(path)

        return path

    def _get_filepath(self) -> Path:
        stem = f"{self.prefix}_{self.image_count:06d}"
        name = f"{stem}.{self.ext}"
        return Path(self.save_dir) / name


class ImageSaver(Interface):
    """An interface for saving shots as series of images"""

    def __init__(self, config: ShowBaseConfig = DEFAULT_SHOWBASE_CONFIG):
        Interface.__init__(self, config=config)

        # Create and setup the image texture
        self.tex = Texture()
        Global.base.win.addRenderTexture(
            self.tex, GraphicsOutput.RTMCopyRam, GraphicsOutput.RTPColor
        )

        # Aim to render 1000 FPS so the clock doesn't sleep between frames
        Global.clock.setMode(ClockObject.MLimited)
        Global.clock.setFrameRate(1000)

    def get_image_array(self) -> NDArray[np.uint8]:
        """Return array of current image texture"""
        assert self.tex.hasRamImage()

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
        camera_state: CameraState = camera_states["7_foot_offcenter"],
        prefix: str = "shot",
        size: Tuple[int, int] = (230, 144),
        fmt: str = "jpg",
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
            prefix:
                The image filenames will be prefixed with this string. By default, the
                prefix is "shot".
            size:
                The number of pixels in x and y. If x:y != 1.6, the aspect ratio will
                look distorted.
            fmt:
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
        exporter = ImageExport(
            save_dir=save_dir,
            ext=fmt,
            prefix=prefix,
        )

        shot.continuize(dt=1 / fps)

        _init_system_collection(shot)
        _resize_window(size)

        self.create_scene()

        # We don't want the cue in this
        visual.cue.hide_nodes()

        cam.load_state(camera_state)

        if show_hud:
            hud.init()
            hud.elements[HUDElement.help_text].help_hint.hide()
            hud.update_cue(shot.cue)
        else:
            hud.destroy()

        # Set quaternions for each ball
        for ball in visual.balls.values():
            ball.set_quats(ball._ball.history_cts)

        frames = int(shot.events[-1].time * fps) + 1

        for frame in range(frames):
            for ball in visual.balls.values():
                ball.set_render_state_from_history(ball._ball.history_cts, frame)

            Global.task_mgr.step()
            exporter.save(self.get_image_array())

        if not make_gif:
            return

        imgs = (
            Image.open(fp)
            for fp in (
                self._get_filepath(save_dir, prefix, frame, img_format)
                for frame in range(frames)
            )
        )

        img = next(imgs)

        img.save(
            fp=f"{save_dir}/{prefix}.gif",
            format="GIF",
            append_images=imgs,
            save_all=True,
            duration=(1 / fps) * 1e3,
            loop=0,  # loop infinitely
        )
