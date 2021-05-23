#! /usr/bin/env python

from pooltool.ani.modes import *


class AimMode(Mode):
    keymap = {
        action.fine_control: False,
        action.quit: False,
        action.stroke: False,
        action.view: False,
        action.zoom: False,
        action.elevation: False,
        action.english: False,
    }

    def enter(self):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.cue_stick.show_nodes()
        self.cue_stick.get_node('cue_stick').setX(0)
        self.cam.update_focus(self.balls['cue'].get_node('ball').getPos())

        self.task_action('escape', action.quit, True)
        self.task_action('f', action.fine_control, True)
        self.task_action('f-up', action.fine_control, False)
        self.task_action('mouse1', action.zoom, True)
        self.task_action('mouse1-up', action.zoom, False)
        self.task_action('s', action.stroke, True)
        self.task_action('v', action.view, True)
        self.task_action('b', action.elevation, True)
        self.task_action('b-up', action.elevation, False)
        self.task_action('e', action.english, True)
        self.task_action('e-up', action.english, False)

        self.add_task(self.aim_task, 'aim_task')
        self.add_task(self.quit_task, 'quit_task')


    def exit(self):
        self.remove_task('aim_task')
        self.remove_task('quit_task')

        self.cue_stick.hide_nodes()

        self.cam.store_state('aim', overwrite=True)


