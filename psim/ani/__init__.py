#! /usr/bin/env python
import psim

from pathlib import Path
from panda3d.core import Filename

import os

model_paths = (path for path in (Path(psim.__file__).parent.parent / 'models').glob('*') if path.is_file())
model_paths = {str(path.stem): Filename.fromOsSpecific(str(path.absolute())) for path in model_paths}

TRACE_LENGTH = 80

# num of pixels of largest dimension
MAX_SCREEN = 800

DIAMOND_COLOR = (255,255,255)
EDGE_RGB = (130,87,77)
RAIL_CLOTH_RGB = (47,120,160)
CLOTH_RGB = (60,155,206)
RAIL_RGB = (71,38,27)
BALL_RGB = {
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


