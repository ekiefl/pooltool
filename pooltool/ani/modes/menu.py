#! /usr/bin/env python, ModeName

import sys

import pooltool.ani.action as action
from pooltool.ani.modes.datatypes import Mode, ModeName


class MenuMode(Mode):
    name = ModeName.menu
    keymap = {
        action.exit: False,
        action.new_game: False,
        action.scroll_up: False,
        action.scroll_down: False,
        "click": False,
    }

    def enter(self):
        self.mouse.show()
        self.mouse.absolute()
        self.show_menu("main_menu")

        self.task_action("escape", action.exit, True)
        self.task_action("escape-up", action.exit, False)
        self.task_action("n", action.new_game, True)
        self.task_action("n-up", action.new_game, False)
        self.task_action("wheel_up", action.scroll_up, True)
        self.task_action("wheel_down", action.scroll_down, True)
        self.task_action("mouse1-up", "click", True)

        self.add_task(self.menu_task, "menu_task")

    def exit(self):
        self.remove_task("menu_task")

    def menu_task(self, task):
        if self.keymap[action.exit]:
            sys.exit()
            return task.done

        if self.keymap[action.new_game]:
            self.go()
            return task.done

        if self.keymap[action.scroll_up]:
            scroll_bar = self.current_menu.area.verticalScroll
            scroll_bar.setValue(scroll_bar.getValue() - scroll_bar["pageSize"])
            self.keymap[action.scroll_up] = False

        if self.keymap[action.scroll_down]:
            scroll_bar = self.current_menu.area.verticalScroll
            scroll_bar.setValue(scroll_bar.getValue() + scroll_bar["pageSize"])
            self.keymap[action.scroll_down] = False

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
