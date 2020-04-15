#! /usr/bin/env python

# num of pixels of largest dimension
MAX_SCREEN = 800

def d_to_px(scale, d):
    """scale is ratio of d to px"""
    return int(d * scale)


def px_to_d(scale, px):
    """scale is ratio of d to px"""
    return d / scale
