#! /usr/bin/env python
import pooltool

from pathlib import Path
from panda3d.core import *

loadPrcFile(str(Path(pooltool.__file__).parent / 'Config.prc'))

model_paths = (path for path in (Path(pooltool.__file__).parent.parent / 'models').glob('*') if path.is_file())
model_paths = {str(path.stem): Filename.fromOsSpecific(str(path.absolute())) for path in model_paths}

menu_text_scale = 0.07

logo_paths = {
    'default': Path(pooltool.__file__).parent.parent / 'logo' / 'logo.png'
}
