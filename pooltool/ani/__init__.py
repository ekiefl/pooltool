#! /usr/bin/env python

from __future__ import annotations

from pathlib import Path

import pooltool as pt
from pooltool.utils import Run, panda_path

run = Run()

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
