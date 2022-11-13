#! /usr/bin/env python

import sys

import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.menu import menus
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import mouse


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
        mouse.show()
        mouse.absolute()
        menus.show("main_menu")

        self.task_action("escape", Action.exit, True)
        self.task_action("escape-up", Action.exit, False)
        self.task_action("n", Action.new_game, True)
        self.task_action("n-up", Action.new_game, False)
        self.task_action("wheel_up", Action.scroll_up, True)
        self.task_action("wheel_down", Action.scroll_down, True)
        self.task_action("mouse1-up", "click", True)

        tasks.add(self.menu_task, "menu_task")

    def exit(self):
        tasks.remove("menu_task")

    def menu_task(self, task):
        if self.keymap[Action.exit]:
            sys.exit()
            return task.done

        if self.keymap[Action.new_game]:
            self.go()
            return task.done

        if self.keymap[Action.scroll_up]:
            scroll_bar = menus.current.area.verticalScroll
            scroll_bar.setValue(scroll_bar.getValue() - scroll_bar["pageSize"])
            self.keymap[Action.scroll_up] = False

        if self.keymap[Action.scroll_down]:
            scroll_bar = menus.current.area.verticalScroll
            scroll_bar.setValue(scroll_bar.getValue() + scroll_bar["pageSize"])
            self.keymap[Action.scroll_down] = False

        if self.keymap["click"]:
            self.keymap["click"] = False
            for element in menus.current.elements:
                if (
                    element["type"] == "entry"
                    and element["object"]["focus"]
                    and element["name"] != self.current.hovered_entry
                ):
                    element["object"]["focus"] = False

        return task.cont
