#! /usr/bin/env python

import ast
import pooltool
import configparser
import pooltool.utils as utils

from pooltool.error import ConfigError, TableConfigError

from pathlib import Path
from panda3d.core import *

loadPrcFile(utils.panda_path(Path(pooltool.__file__).parent / 'config' / 'config_panda3d.prc'))

menu_text_scale = 0.07
menu_text_scale_small = 0.04
zoom_sensitivity = 0.3
min_player_cam = 2
max_english = 6/10
elevate_sensitivity = 13
english_sensitivity = 0.1
rotate_sensitivity_x = 19
rotate_sensitivity_y = 5
rotate_fine_sensitivity_x = 2
rotate_fine_sensitivity_y = 0
move_sensitivity = 0.6
stroke_sensitivity = 0.4
max_stroke_speed = 7 # m/s
backstroke_fraction = 0.5 # max backstroke length, as fraction of cue stick length
max_elevate = 80 # max masse angle
rotate_downtime = 0.3 # number of seconds that camera rotation is disabled when shot is being calculated
rewind_dt = 0.02
fast_forward_dt = 0.02

options_game = 'Game'
options_8_ball = '8-ball'
options_9_ball = '9-ball'
options_sandbox = 'Sandbox'
options_table = 'Table'
options_ball_diameter = 'Ball diameter'
options_friction_slide = 'Coeff. sliding friction'
options_friction_roll = 'Coeff. rolling friction'
options_friction_spin = 'Coeff. spinning friction'

options_table_type = 'Table type'
options_table_length = 'Play surface length'
options_table_width = 'Play surface width'
options_table_height = 'Table height'
options_lights_height = 'Light height'
options_cushion_width = 'Cushion width'
options_cushion_height = 'Cushion height'
options_corner_pocket_width = 'Pocket width (corner)'
options_corner_pocket_angle = 'Pocket opening angle (corner)'
options_corner_pocket_depth = 'Pocket depth (corner)'
options_corner_pocket_radius = 'Pocket radius (corner)'
options_corner_jaw_radius = 'Jaw radius (corner)'
options_side_pocket_width = 'Pocket width (side)'
options_side_pocket_angle = 'Pocket opening angle (side)'
options_side_pocket_depth = 'Pocket depth (side)'
options_side_pocket_radius = 'Pocket radius (side)'
options_side_jaw_radius = 'Jaw radius (side)'

ball_highlight = {
    'ball_offset': 0.12,
    'ball_amplitude': 0.03,
    'ball_frequency': 4,
    'ball_factor': 1.3,
    'shadow_alpha_offset': 0.27,
    'shadow_alpha_amplitude': 0.07,
    'shadow_scale_offset': 2.2,
    'shadow_scale_amplitude': 0.4,
}

model_dir = Path(pooltool.__file__).parent / 'models'

logo_dir = Path(pooltool.__file__).parent / 'logo'
logo_paths = {
    'default': utils.panda_path(logo_dir / 'logo.png'),
    'small': utils.panda_path(logo_dir / 'logo_small.png'),
    'smaller': utils.panda_path(logo_dir / 'logo_smaller.png'),
    'pt': utils.panda_path(logo_dir / 'logo_pt.png'),
    'pt_smaller': utils.panda_path(logo_dir / 'logo_pt_smaller.png'),
}


def load_config(name, exception_type=Exception, exception_msg="Something went wrong. Here is what we know: {}"):
    config_path = Path(__file__).parent.parent / 'config' / name
    config_obj = configparser.ConfigParser()
    try:
        config_obj.read(config_path)
    except Exception as e:
        raise exception_type(f"Something went wrong with your table config file. Here is the reported issue: {e}")
    config = {}
    for section in config_obj.sections():
        config[section] = {}
        for k, v in config_obj[section].items():
            try:
                config[section][k] = ast.literal_eval(v)
            except:
                config[section][k] = v
    return config

table_config = load_config('tables', TableConfigError)
settings = load_config('settings', ConfigError)


