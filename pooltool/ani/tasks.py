from pooltool.ani.globals import Global, require_showbase


@require_showbase
def has(name):
    return Global.task_mgr.hasTaskNamed(name)


@require_showbase
def add(func, name, *args, **kwargs):
    if not has(name):
        # If the task already exists, don't add it again
        Global.task_mgr.add(func, name, *args, **kwargs)


@require_showbase
def add_later(*args, **kwargs):
    Global.task_mgr.doMethodLater(*args, **kwargs)


@require_showbase
def remove(name):
    Global.task_mgr.remove(name)


@require_showbase
def register_event(keystroke, func, func_args=[]):
    """Register event listener that triggers based on keystroke/mouse"""

    Global.base.accept(keystroke, func, func_args)
