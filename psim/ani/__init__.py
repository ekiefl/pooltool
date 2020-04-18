#! /usr/bin/env python

# num of pixels of largest dimension
MAX_SCREEN = 800

CLOTH_RGB = (60,155,206)
BALL_RGB = {
    'cue': (244,242,238),
    '1': (255,255,80),
    '8': (0,0,0),
}

def d_to_px(scale, d):
    """scale is ratio of d to px"""
    return int(d * scale)


def px_to_d(scale, px):
    """scale is ratio of d to px"""
    return d / scale
