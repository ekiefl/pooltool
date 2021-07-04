#! /usr/bin/env python
import pooltool

from pathlib import Path
from panda3d.core import *

loadPrcFile(str(Path(pooltool.__file__).parent / 'Config.prc'))

model_paths = (path for path in (Path(pooltool.__file__).parent.parent / 'models').glob('*') if path.is_file())
model_paths = {str(path.stem): Filename.fromOsSpecific(str(path.absolute())) for path in model_paths}

menu_text_scale = 0.07
zoom_sensitivity = 0.3
max_english = 5/10
elevate_sensitivity = 3
english_sensitivity = 0.1
rotate_sensitivity_x = 13
rotate_sensitivity_y = 3
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

logo_paths = {
    'default': Path(pooltool.__file__).parent.parent / 'logo' / 'logo.png'
}
