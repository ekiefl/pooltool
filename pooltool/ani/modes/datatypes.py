from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, List, Type, TypeVar

import pooltool.ani.action as action

# ------------------------------------------------------------

# FIXME move into utils/strenum


_S = TypeVar("_S", bound="StrEnum")


class StrEnum(str, Enum):
    """
    Enum where members are also (and must be) strings
    """

    def __new__(cls: Type[_S], *values: str) -> _S:
        if len(values) > 3:
            raise TypeError("too many arguments for str(): %r" % (values,))
        if len(values) == 1:
            # it must be a string
            if not isinstance(values[0], str):
                raise TypeError("%r is not a string" % (values[0],))
        if len(values) >= 2:
            # check that encoding argument is a string
            if not isinstance(values[1], str):
                raise TypeError("encoding must be a string, not %r" % (values[1],))
        if len(values) == 3:
            # check that errors argument is a string
            if not isinstance(values[2], str):
                raise TypeError("errors must be a string, not %r" % (values[2]))
        value = str(*values)
        member = str.__new__(cls, value)
        member._value_ = value
        return member

    __str__ = str.__str__

    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: List[Any]
    ) -> str:
        """
        Return the lower-cased version of the member name.
        """
        return name.lower()


# ------------------------------------------------------------


class ModeName(StrEnum):
    aim = auto()
    ball_in_hand = auto()
    calculate = auto()
    call_shot = auto()
    cam_load = auto()
    cam_save = auto()
    game_over = auto()
    menu = auto()
    pick_ball = auto()
    purgatory = auto()
    shot = auto()
    stroke = auto()
    view = auto()
    none = auto()


class Mode(ABC):
    keymap = None
    name = None

    def __init__(self):
        if self.keymap is None:
            raise NotImplementedError("Subclasses of Mode must have 'keymap' attribute")

        if self.name is None:
            raise NotImplementedError("Subclasses of Mode must have 'name' attribute")

        self.add_task(self.shared_task, "shared_task")
        self.add_task(self.cam_save_watch, "cam_save_watch")
        self.add_task(self.cam_load_watch, "cam_load_watch")
        self.add_task(self.help_watch, "help_watch")

    def shared_task(self, task):
        if self.keymap.get(action.quit):
            self.keymap[action.quit] = False
            self.close_scene()
            self.change_mode("menu")
        elif self.keymap.get(action.introspect):
            self.keymap[action.introspect] = False
            import pooltool as pt

            shot = self.shots.active
            import pdb

            pdb.set_trace()

        return task.cont

    def cam_save_watch(self, task):
        if self.keymap.get(action.cam_save) and self.mode != "cam_save":
            self.change_mode("cam_save")

        return task.cont

    def cam_load_watch(self, task):
        if self.keymap.get(action.cam_load) and self.mode != "cam_load":
            self.change_mode("cam_load")

        return task.cont

    def help_watch(self, task):
        if self.keymap.get(action.show_help):
            self.keymap[action.show_help] = False
            if self.help_node.is_hidden():
                self.help_node.show()
            else:
                self.help_node.hide()

        return task.cont

    @abstractmethod
    def enter(self):
        pass

    @abstractmethod
    def exit(self):
        pass
