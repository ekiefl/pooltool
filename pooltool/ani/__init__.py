#! /usr/bin/env python

from __future__ import annotations

import shutil
import traceback
from pathlib import Path

import attrs
from panda3d.core import loadPrcFile

import pooltool as pt
from pooltool.serialize import conversion
from pooltool.terminal import Run
from pooltool.user_config import CONFIG_DIR
from pooltool.utils import panda_path

run = Run()

loadPrcFile(panda_path(Path(pt.__file__).parent / "config" / "config_panda3d.prc"))

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
class GraphicsConfig:
    room: bool
    floor: bool
    table: bool
    shadows: bool
    shader: bool
    lights: bool
    max_lights: int
    physical_based_rendering: bool
    debug: bool
    fps: int
    fps_inactive: int
    hud: bool


@attrs.define
class GameplayConfig:
    cue_collision: int


@attrs.define
class Config:
    graphics: GraphicsConfig
    gameplay: GameplayConfig

    @classmethod
    def default(cls) -> Config:
        return cls(
            GraphicsConfig(
                room=False,
                floor=False,
                table=False,
                shadows=False,
                shader=False,
                lights=False,
                max_lights=13,
                physical_based_rendering=False,
                debug=False,
                fps=45,
                fps_inactive=5,
                hud=False,
            ),
            GameplayConfig(
                cue_collision=True,
            ),
        )

    @classmethod
    def load(cls, path: Path) -> Config:
        return conversion.structure_from(path, Config)

    def save(self, path: Path) -> None:
        conversion.unstructure_to(settings, path)


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
