#! /usr/bin/env python
import psim

import os
import numpy as np

from pathlib import Path
from panda3d.core import *

loadPrcFile(str(Path(psim.__file__).parent / 'Config.prc'))

model_paths = (path for path in (Path(psim.__file__).parent.parent / 'models').glob('*') if path.is_file())
model_paths = {str(path.stem): Filename.fromOsSpecific(str(path.absolute())) for path in model_paths}

fps_target = 60

ghost_trail_array = np.arange(0,20,2)
line_trail_array = np.arange(1, 100, 1)
line_trail_thickness = 2
line_trail_color = LColor(1, 1, 1, 1)
ghost_decay = 4
line_decay = 3


# -----------------------------------------------------------------------------
# Below is for 2D visualization via pygame. All legacy code since porting to panda3d
# -----------------------------------------------------------------------------

PYGAME_TRACE_LENGTH = 50

# num of pixels of largest dimension
PYGAME_MAX_SCREEN = 800

PYGAME_DIAMOND_COLOR = (255,255,255)
PYGAME_EDGE_RGB = (130,87,77)
PYGAME_RAIL_CLOTH_RGB = (47,120,160)
PYGAME_CLOTH_RGB = (60,155,206)
PYGAME_RAIL_RGB = (71,38,27)
PYGAME_BALL_RGB = {
    'cue': (244,242,238),
    '1': (244,200,22),
    '2': (4,93,184),
    '3': (198,1,1),
    '4': (234,132,156),
    '5': (233,98,20),
    '6': (7,117,41),
    '7': (127,51,54),
    '8': (0,0,0),
    '9': (244,200,22),
}

def d_to_px(scale, d, offset=0):
    """scale is ratio of d to px"""
    if hasattr(d, '__len__'):
        return (d * scale + offset).astype(int)
    else:
        return int(d * scale + offset)


def px_to_d(scale, px):
    """scale is ratio of d to px"""
    return d / scale

