from pooltool.ani.globals import Global, require_showbase


@require_showbase
def has(self, name):
    return Global.task_mgr.hasTaskNamed(name)


@require_showbase
def add(self, func, name, *args, **kwargs):
    if not self.has_task(name):
        # If the task already exists, don't add it again
        Global.task_mgr.add(func, name, *args, **kwargs)


@require_showbase
def add_later(self, *args, **kwargs):
    Global.task_mgr.doMethodLater(*args, **kwargs)


@require_showbase
def remove(self, name):
    Global.task_mgr.remove(name)
