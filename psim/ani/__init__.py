#! /usr/bin/env python

TRACE_LENGTH = 10000

# num of pixels of largest dimension
MAX_SCREEN = 800

CLOTH_RGB = (202,222,235)
#CLOTH_RGB = (60,155,206)
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


def d_to_px(scale, d):
    """scale is ratio of d to px"""
    if hasattr(d, '__len__'):
        return (d * scale).astype(int)
    else:
        return int(d * scale)


def px_to_d(scale, px):
    """scale is ratio of d to px"""
    return d / scale
