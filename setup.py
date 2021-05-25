#! /usr/bin/env python

from setuptools import setup

setup(
    name="pooltool",
    options = {
        'build_apps': {
            #'platforms': ["win_amd64", "manylinux2010_x86_64", "macosx_10_9_x86_64"],
            'include_patterns': [
                'models/**/*.png',
                'models/**/*.jpg',
                'models/**/*.egg',
            ],
            'gui_apps': {
                'pooltool': 'bin/pooltool',
            },
            'plugins': [
            ],
        }
    }
)
