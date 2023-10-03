#! /usr/bin/env python

import ast
import configparser
from pathlib import Path
from typing import Dict

from panda3d.core import loadPrcFile

import pooltool as pt
from pooltool.utils import panda_path

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
max_elevate = 80
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


def load_config(name):
    config_path = Path(__file__).parent.parent / "config" / name
    config_obj = configparser.ConfigParser()
    config_obj.read(config_path)
    config = {}
    for section in config_obj.sections():
        config[section] = {}
        for k, v in config_obj[section].items():
            try:
                config[section][k] = ast.literal_eval(v)
            except Exception:
                config[section][k] = v
    return config


def save_config(name, config: Dict, overwrite=False):
    config_path = Path(__file__).parent.parent / "config" / name

    if config_path.exists() and not overwrite:
        raise ValueError(
            f"pass overwrite=True to overwrite existing config: '{config_path}'"
        )

    config_obj = configparser.ConfigParser()
    config_obj.read_dict(config)

    with open(config_path, "w") as configfile:
        config_obj.write(configfile)


if (Path(__file__).parent.parent / "config/settings.local").exists():
    settings = load_config("settings.local")
else:
    settings = load_config("settings")
