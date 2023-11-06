from pathlib import Path
from typing import Optional

from pooltool.ani.globals import Global
from pooltool.utils import panda_path

font_paths = {path.stem: path for path in Path(__file__).parent.glob("*.ttf")}

DEFAULT = "HackNerdFontMono-Regular"
assert DEFAULT in font_paths, f"{DEFAULT=} is missing"


def load_font(name: Optional[str] = None):
    if name is None:
        name = DEFAULT

    assert name in font_paths, f"{name=} is not a known font"
    return Global.loader.loadFont(panda_path(font_paths[name]))


def print_font_names() -> None:
    print(font_paths.keys())
