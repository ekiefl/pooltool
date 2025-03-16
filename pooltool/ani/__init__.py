#! /usr/bin/env python

from __future__ import annotations

import shutil
import traceback
from pathlib import Path

import attrs
from panda3d.core import loadPrcFileData

import pooltool as pt
from pooltool.config.user import CONFIG_DIR
from pooltool.game.datatypes import GameType
from pooltool.serialize import conversion
from pooltool.terminal import Run
from pooltool.utils import panda_path

run = Run()

# This is hard-coded. Change it and everything looks bad
aspect_ratio = 1.6

menu_text_scale = 0.07
menu_text_scale_small = 0.04
zoom_sensitivity = 0.3
min_camera = 2
max_english = 6 / 10
power_sensitivity = 2
elevate_sensitivity = 13
english_sensitivity = 0.1
rotate_sensitivity_x = 19
rotate_sensitivity_y = 5
rotate_fine_sensitivity_x = 2
rotate_fine_sensitivity_y = 0
move_sensitivity = 0.6
stroke_sensitivity = 0.4
min_stroke_speed = 0.05  # m/s
max_stroke_speed = 7  # m/s
# max backstroke length, as fraction of cue stick length
backstroke_fraction = 0.5
# max masse angle
max_elevate = 89.9
# number of seconds that camera rotation is disabled when shot is being calculated
rotate_downtime = 0.3

ball_highlight = {
    "ball_offset": 0.12,
    "ball_amplitude": 0.03,
    "ball_frequency": 4,
    "ball_factor": 1.3,
    "shadow_alpha_offset": 0.27,
    "shadow_alpha_amplitude": 0.07,
    "shadow_scale_offset": 2.2,
    "shadow_scale_amplitude": 0.4,
}

model_dir: Path = Path(pt.__file__).parent / "models"

logo_dir = Path(pt.__file__).parent / "logo"
logo_paths = {
    "default": panda_path(logo_dir / "logo.png"),
    "small": panda_path(logo_dir / "logo_small.png"),
    "smaller": panda_path(logo_dir / "logo_smaller.png"),
    "pt": panda_path(logo_dir / "logo_pt.png"),
    "pt_smaller": panda_path(logo_dir / "logo_pt_smaller.png"),
}


@attrs.define
class PandaConfig:
    show_frame_rate: bool = True
    window_width: int = 1400
    sync_video: bool = False
    gl_check_errors: bool = False
    gl_version_major: int = 3
    gl_version_minor: int = 2

    @property
    def window_height(self) -> int:
        return int(self.window_width / aspect_ratio)

    def apply_settings(self) -> None:
        """Apply Panda3D configuration settings at runtime."""
        loadPrcFileData(
            "", f"show-frame-rate-meter {'#t' if self.show_frame_rate else '#f'}"
        )
        loadPrcFileData("", f"win-size {self.window_width} {self.window_height}")
        loadPrcFileData("", "fullscreen #f")  # hard-coded, fullscreen broken
        loadPrcFileData("", f"sync-video {'#t' if self.sync_video else '#f'}")
        loadPrcFileData("", f"gl-check-errors {'#t' if self.gl_check_errors else '#f'}")
        loadPrcFileData(
            "", f"gl-version {self.gl_version_major} {self.gl_version_minor}"
        )


@attrs.define
class GraphicsConfig:
    room: bool = True
    floor: bool = True
    table: bool = True
    shadows: bool = False
    shader: bool = True
    lights: bool = True
    max_lights: int = 13
    physical_based_rendering: bool = False
    debug: bool = False
    fps: int = 45
    fps_inactive: int = 5
    hud: bool = True


@attrs.define
class GameplayConfig:
    cue_collision: int = True
    game_type: GameType = GameType.NINEBALL


@attrs.define
class Config:
    graphics: GraphicsConfig
    gameplay: GameplayConfig
    panda: PandaConfig

    @classmethod
    def default(cls) -> Config:
        return cls(
            GraphicsConfig(),
            GameplayConfig(),
            PandaConfig(),
        )

    @classmethod
    def load(cls, path: Path) -> Config:
        return conversion.structure_from(path, Config)

    def save(self, path: Path) -> None:
        conversion.unstructure_to(self, path)

    def apply_panda_settings(self) -> None:
        """Apply Panda3D configuration settings."""
        self.panda.apply_settings()


GENERAL_CONFIG = CONFIG_DIR / "general.yaml"
if GENERAL_CONFIG.exists():
    try:
        settings = Config.load(GENERAL_CONFIG)
    except Exception:
        full_traceback = traceback.format_exc()
        dump_path = GENERAL_CONFIG.parent / f".{GENERAL_CONFIG.name}"
        run.info_single(
            f"{GENERAL_CONFIG} is malformed and can't be loaded. It is being "
            f"replaced with a default working version. Your version has been moved to "
            f"{dump_path} if you want to diagnose it. Here is the error:\n{full_traceback}"
        )
        shutil.move(GENERAL_CONFIG, dump_path)
        settings = Config.default()
        settings.save(GENERAL_CONFIG)
else:
    settings = Config.default()
    settings.save(GENERAL_CONFIG)

# Apply Panda3D settings from the config
settings.apply_panda_settings()
