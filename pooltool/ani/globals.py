from direct.showbase import ShowBaseGlobal

from pooltool.error import ConfigError


def is_showbase_initialized() -> bool:
    """Return whether ShowBase has been initialized

    Checks by seeing whether `base` is an attribute of the ShowBaseGobal namespace,
    which is dynamically added when ShowBase is initialized:

    https://docs.panda3d.org/1.10/python/reference/direct.showbase.ShowBaseGlobal#module-direct.showbase.ShowBaseGlobal
    """
    return True if hasattr(ShowBaseGlobal, "base") else False


def require_showbase(func):
    """Return wrapper that complains if ShowBase no instance exists"""

    def wrapper(*args, **kwargs):
        if is_showbase_initialized():
            return func(*args, **kwargs)

        raise ConfigError(
            f"ShowBase instance has not been initialized, but a function has been "
            f"called that requires it: '{func.__name__}'."
        )

    return wrapper


class _Global:
    @property
    @require_showbase
    def base(self):
        return ShowBaseGlobal.base


Global = _Global()
