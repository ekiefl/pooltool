#! /usr/bin/env python

import re
from importlib import import_module
from inspect import isclass
from pathlib import Path
from pkgutil import iter_modules

from pooltool.ani.modes.datatypes import Mode

# https://julienharbulot.com/python-dynamical-import.html
package_dir = str(Path(__file__).resolve().parent)
for (_, module_name, _) in iter_modules([package_dir]):
    if module_name == "datatypes":
        continue

    module = import_module(f"{__name__}.{module_name}")
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)

        if isclass(attribute):
            globals()[attribute_name] = attribute


def _get_mode_name(mode):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", mode.__name__[:-4]).lower()


modes = {_get_mode_name(cls): cls for cls in Mode.__subclasses__()}
