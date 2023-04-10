#! /usr/bin/env python

from setuptools import find_packages, setup

setup(
    name="pooltool-billiards",
    version="0.2.1.dev0",
    packages=find_packages(),
    scripts=["run_pooltool", "run_pooltool.bat"],
    author_email="kiefl.evan@gmail.com",
    author="Evan Kiefl",
    url="https://github.com/ekiefl/pooltool",
    install_requires=[
        "numpy",
        "pandas",
        "numba",
        "scipy",
        "panda3d==1.10.13",
        "panda3d-gltf",
        "panda3d-simplepbr",
        "Pillow",
        "cattrs",
        "attrs",
        "pprofile",
        "msgpack",
        "msgpack-numpy",
        "h5py",
        "pyyaml",
    ],
    include_package_data=True,
    zip_safe=False,
    # options = {
    #    'build_apps': {
    #        #'platforms': ["win_amd64", "manylinux2010_x86_64", "macosx_10_9_x86_64"],
    #        'platforms': ['macosx_10_9_x86_64'],
    #        'include_patterns': [
    #            'pooltool/**/*.png',
    #            'pooltool/**/*.jpg',
    #            'pooltool/**/*.egg',
    #            'pooltool/**/*.glb',
    #            'pooltool/**/*.png',
    #            'pooltool/**/*.jpg',
    #            'pooltool/**/*.egg',
    #            'pooltool/**/*.glb',
    #        ],
    #        'gui_apps': {
    #            'pooltool': 'run_pooltool',
    #        },
    #        'plugins': [
    #        ],
    #    }
    # }
)
