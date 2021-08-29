#! /usr/bin/env python
import ast
import pooltool
import configparser

from pathlib import Path
from panda3d.core import *

loadPrcFile(str(Path(pooltool.__file__).parent / 'Config.prc'))

#model_paths = (path for path in (Path(pooltool.__file__).parent.parent / 'models').glob('*') if path.is_file())
#model_paths = {str(path.stem): Filename.fromOsSpecific(str(path.absolute())) for path in model_paths}

menu_text_scale = 0.07
menu_text_scale_small = 0.04
zoom_sensitivity = 0.3
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

logo_paths = {
    'default': str(Path(pooltool.__file__).parent.parent / 'logo' / 'logo.png'),
    'small': str(Path(pooltool.__file__).parent.parent / 'logo' / 'logo_small.png'),
    'smaller': str(Path(pooltool.__file__).parent.parent / 'logo' / 'logo_smaller.png'),
    'pt': str(Path(pooltool.__file__).parent.parent / 'logo' / 'logo_pt.png'),
    'pt_smaller': str(Path(pooltool.__file__).parent.parent / 'logo' / 'logo_pt_smaller.png'),
}

tables_path = Path(__file__).parent.parent.parent / 'config' / 'tables'
table_config_obj = configparser.ConfigParser()
table_config_obj.read(tables_path)
table_config = {}
for table in table_config_obj.sections():
    table_config[table] = {}
    for k, v in table_config_obj[table].items():
        try:
            table_config[table][k] = ast.literal_eval(v)
        except:
            table_config[table][k] = v
