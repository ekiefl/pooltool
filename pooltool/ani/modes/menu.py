#! /usr/bin/env python

import sys

from pooltool.ani.action import Action
from pooltool.ani.modes.datatypes import BaseMode, Mode


class MenuMode(BaseMode):
    name = Mode.menu
    keymap = {
        Action.exit: False,
        Action.new_game: False,
        Action.scroll_up: False,
        Action.scroll_down: False,
        "click": False,
    }

    def enter(self):
        self.mouse.show()
        self.mouse.absolute()
        self.show_menu("main_menu")

        self.task_action("escape", Action.exit, True)
        self.task_action("escape-up", Action.exit, False)
        self.task_action("n", Action.new_game, True)
        self.task_action("n-up", Action.new_game, False)
        self.task_action("wheel_up", Action.scroll_up, True)
        self.task_action("wheel_down", Action.scroll_down, True)
        self.task_action("mouse1-up", "click", True)

        self.add_task(self.menu_task, "menu_task")

    def exit(self):
        self.remove_task("menu_task")

    def menu_task(self, task):
        if self.keymap[Action.exit]:
            sys.exit()
            return task.done

        if self.keymap[Action.new_game]:
            self.go()
            return task.done

        if self.keymap[Action.scroll_up]:
            scroll_bar = self.current_menu.area.verticalScroll
            scroll_bar.setValue(scroll_bar.getValue() - scroll_bar["pageSize"])
            self.keymap[Action.scroll_up] = False

        if self.keymap[Action.scroll_down]:
            scroll_bar = self.current_menu.area.verticalScroll
            scroll_bar.setValue(scroll_bar.getValue() + scroll_bar["pageSize"])
            self.keymap[Action.scroll_down] = False

        if self.keymap["click"]:
            self.keymap["click"] = False
            for element in self.current_menu.elements:
                if (
                    element["type"] == "entry"
                    and element["object"]["focus"]
                    and element["name"] != self.current_menu.hovered_entry
                ):
                    element["object"]["focus"] = False

        return task.cont
