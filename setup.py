#! /usr/bin/env python

from pathlib import Path
from setuptools import setup, find_packages

setup(
    name = 'pooltool-billiards',
    version = '0.1',
    packages = find_packages(),
    scripts = ['run_pooltool'],
    author_email = 'kiefl.evan@gmail.com',
    author = 'Evan Kiefl',
    url = 'https://github.com/ekiefl/pooltool',
    install_requires = [
        'numpy',
        'scipy',
        'pandas',
        'panda3d==1.10.10',
        'panda3d-gltf',
        'panda3d-simplepbr',
        'pyquaternion',
    ],
    include_package_data = True,
    zip_safe = False,
    #options = {
    #    'build_apps': {
    #        #'platforms': ["win_amd64", "manylinux2010_x86_64", "macosx_10_9_x86_64"],
    #        'platforms': ['macosx_10_9_x86_64'],
    #        'include_patterns': [
    #            'models/**/*.png',
    #            'models/**/*.jpg',
    #            'models/**/*.egg',
    #            'models/**/*.glb',
    #            'logo/**/*.png',
    #            'logo/**/*.jpg',
    #            'logo/**/*.egg',
    #            'logo/**/*.glb',
    #        ],
    #        'gui_apps': {
    #            'pooltool': 'run_pooltool',
    #        },
    #        'plugins': [
    #        ],
    #    }
    #}
)

