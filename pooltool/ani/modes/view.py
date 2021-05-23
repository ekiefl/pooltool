#! /usr/bin/env python

from pooltool.ani.modes import *


class ViewMode(Mode):
    keymap ={
        action.aim: False,
        action.fine_control: False,
        action.move: True,
        action.quit: False,
        action.zoom: False,
    }

    def enter(self):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.task_action('escape', action.quit, True)
        self.task_action('mouse1', action.zoom, True)
        self.task_action('mouse1-up', action.zoom, False)
        self.task_action('a', action.aim, True)
        self.task_action('v', action.move, True)
        self.task_action('v-up', action.move, False)

        self.add_task(self.view_task, 'view_task')
        self.add_task(self.quit_task, 'quit_task')


    def exit(self):
        self.remove_task('view_task')
        self.remove_task('quit_task')


