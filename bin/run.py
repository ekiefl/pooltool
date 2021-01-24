#! /usr/bin/env python

import psim
import psim.engine as engine

import argparse

ap = argparse.ArgumentParser()
args = ap.parse_args()

if __name__ == '__main__':
    from psim.ani.animate3d import Interface
    ani = Interface()
    ani.start()
