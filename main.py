#! /usr/bin/env python

import pooltool
import pooltool.engine as engine

import argparse

ap = argparse.ArgumentParser()
args = ap.parse_args()

if __name__ == '__main__':
    from pooltool.ani.animate3d import Interface
    ani = Interface()
    ani.start()
