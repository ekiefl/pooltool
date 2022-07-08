#! /usr/bin/env python

from pooltool.ani.modes import Mode, action

import sys


class MenuMode(Mode):
    keymap = {
        action.exit: False,
        action.new_game: False,
        action.scroll_up: False,
        action.scroll_down: False,
    }

    def enter(self):
        self.mouse.show()
        self.mouse.absolute()
        self.show_menu('main_menu')

        self.task_action('escape', action.exit, True)
        self.task_action('escape-up', action.exit, False)
        self.task_action('n', action.new_game, True)
        self.task_action('n-up', action.new_game, False)
        self.task_action('wheel_up', action.scroll_up, True)
        self.task_action('wheel_down', action.scroll_down, True)

        self.add_task(self.menu_task, 'menu_task')


    def exit(self):
        self.remove_task('menu_task')


    def menu_task(self, task):
        if self.keymap[action.exit]:
            sys.exit()
            return task.done

        if self.keymap[action.new_game]:
            self.go()
            return task.done

        if self.keymap[action.scroll_up]:
            scroll_bar = self.current_menu.area.verticalScroll
            scroll_bar.setValue(scroll_bar.getValue() - scroll_bar['pageSize'])
            self.keymap[action.scroll_up] = False

        if self.keymap[action.scroll_down]:
            scroll_bar = self.current_menu.area.verticalScroll
            scroll_bar.setValue(scroll_bar.getValue() + scroll_bar['pageSize'])
            self.keymap[action.scroll_down] = False

        return task.cont

