from pooltool.ani.globals import Global


def has(name):
    return Global.task_mgr.hasTaskNamed(name)


def add(func, name, *args, **kwargs):
    if not has(name):
        # If the task already exists, don't add it again
        Global.task_mgr.add(func, name, *args, **kwargs)


def add_later(*args, **kwargs):
    Global.task_mgr.doMethodLater(*args, **kwargs)


def remove(name):
    Global.task_mgr.remove(name)
