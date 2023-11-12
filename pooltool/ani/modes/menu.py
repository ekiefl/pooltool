#! /usr/bin/env python

import sys

import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.globals import Global
from pooltool.ani.menu import menus
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse


class MenuMode(BaseMode):
    name = Mode.menu
    keymap = {
        Action.exit: False,
        Action.new_game: False,
        Action.scroll_up: False,
        Action.scroll_down: False,
        Action.click: False,
    }

    def enter(self):
        mouse.mode(MouseMode.ABSOLUTE)

        try:
            menus.show(menus.current.name)
        except AttributeError:
            menus.show("main_menu")

        self.register_keymap_event("escape", Action.exit, True)
        self.register_keymap_event("escape-up", Action.exit, False)
        self.register_keymap_event("n", Action.new_game, True)
        self.register_keymap_event("n-up", Action.new_game, False)
        self.register_keymap_event("wheel_up", Action.scroll_up, True)
        self.register_keymap_event("wheel_down", Action.scroll_down, True)
        self.register_keymap_event("mouse1-up", "click", True)

        tasks.add(self.menu_task, "menu_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self):
        tasks.remove("shared_task")
        tasks.remove("menu_task")

    def menu_task(self, task):
        if self.keymap[Action.exit]:
            sys.exit()

        if self.keymap[Action.new_game]:
            Global.base.messenger.send("enter-game")
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
                    and element["name"] != menus.current.hovered_entry
                ):
                    element["object"]["focus"] = False

        return task.cont
