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
def register_event(sequence, func, func_args=[]):
    """Register event listener that triggers based on keystroke/mouse/message

    Args:
        sequence:
            Sequence can be (1) a key specifier, (2) a mouse click specifier, or (3) a
            custom string.

            (1): A character in [0-9a-z], or a keyname in {"escape", "backspace",
                 "insert", "home", "page_up", "num_lock", "tab", "delete", "end",
                 "page_down", "caps_lock", "enter", "arrow_left", "arrow_up",
                 "arrow_down", "arrow_right", "shift", "lshift", "rshift", "conrol",
                 "alt", "lcontrol", "window-event", "lalt", "space", "ralt",
                 "rcontrol"}. Each key can be prefixed with modifier keys that can
                 chain, e.g. "shift-control-alt-a", and can be suffixed with "-down",
                 "-up", or "-repeat".

            (2): Any of {"mouse1", "mouse2", "mouse3", "wheel_up", "wheel_down"}. Can be
                 suffixed with "-down" and "-up".

            (3): A custom string. The event will be triggered when a message containing
                 the string is sent. E.g. register_event("test", lambda: print("hi"))
                 would print "hi" when the following call was made:

                    Global.base.messenger.send("test")
    """

    Global.base.accept(sequence, func, func_args)
