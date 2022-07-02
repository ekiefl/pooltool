#! /usr/bin/env python

from pooltool.ani.modes import Mode, action

import sys


class MenuMode(Mode):
    keymap = {
        action.exit: False,
        action.new_game: False,
    }

    def enter(self):
        self.mouse.show()
        self.mouse.absolute()
        self.show_menu('main')

        self.task_action('escape', action.exit, True)
        self.task_action('escape-up', action.exit, False)
        self.task_action('n', action.new_game, True)
        self.task_action('n-up', action.new_game, False)

        self.add_task(self.menu_task, 'menu_task')


    def exit(self):
        self.hide_menus()
        self.remove_task('menu_task')


    def menu_task(self, task):
        if self.keymap[action.exit]:
            sys.exit()

        if self.keymap[action.new_game]:
            self.go()

        return task.cont


