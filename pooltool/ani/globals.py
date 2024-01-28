import functools
import sys
from typing import Any

from direct.showbase import ShowBaseGlobal

from pooltool.error import ConfigError
from pooltool.utils import classproperty


def is_showbase_initialized() -> bool:
    """Return whether ShowBase has been initialized

    Checks by seeing whether `base` is an attribute of the ShowBaseGlobal namespace,
    which is dynamically added when ShowBase is initialized:

    https://docs.panda3d.org/1.10/python/reference/direct.showbase.ShowBaseGlobal#module-direct.showbase.ShowBaseGlobal
    """
    return hasattr(ShowBaseGlobal, "base")


def require_showbase(func):
    """Return wrapper that complains if ShowBase no instance exists"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if "sphinx" in sys.modules:
            # Sphinx's autodoc generation needs introspective access
            return func(*args, **kwargs)

        if is_showbase_initialized():
            return func(*args, **kwargs)

        raise ConfigError(
            f"ShowBase instance has not been initialized, but a function has been "
            f"called that requires it: '{func.__name__}'."
        )

    return wrapper


class Global:
    """A namespace for shared variables

    When an instance of ShowBase is created, Panda3d populates the global namespace with
    many variables, so they can be accessed from anywhere. But to those unfamiliar with
    this design idiom, tracking the origin of these variables is extremely confusing.
    Fortunately, Panda3d provides a module, `ShowBaseGlobal`, that you can use to access
    these variables the _right_ way:

    https://docs.panda3d.org/1.10/python/reference/direct.showbase.ShowBaseGlobal#module-direct.showbase.ShowBaseGlobal

    With that in mind, this class is designed for two things:

        (1) It gives access to the `ShowBaseGlobal` variables.
        (2) It provide a namespace for other variables designed to be shared across many
            modules.
    """

    clock = ShowBaseGlobal.globalClock
    aspect2d = ShowBaseGlobal.aspect2d
    render2d = ShowBaseGlobal.render2d

    game: Any = None
    mode_mgr: Any = None

    @classproperty
    @require_showbase
    def base(self):
        return ShowBaseGlobal.base

    @classproperty
    @require_showbase
    def render(self):
        return ShowBaseGlobal.base.render

    @classproperty
    @require_showbase
    def task_mgr(self):
        return ShowBaseGlobal.base.taskMgr

    @classproperty
    @require_showbase
    def loader(self):
        return ShowBaseGlobal.base.loader

    @classmethod
    def register_game(cls, game):
        cls.game = game

    @classmethod
    def register_mode_mgr(cls, mode_mgr):
        cls.mode_mgr = mode_mgr
