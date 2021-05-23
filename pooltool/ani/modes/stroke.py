#! /usr/bin/env python

from pooltool.ani.modes import *


class StrokeMode(Mode):
    keymap = {
        action.fine_control: False,
        action.stroke: True,
    }

    def enter(self):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.cue_stick.track_stroke()
        self.cue_stick.show_nodes()

        self.task_action('f', action.fine_control, True)
        self.task_action('f-up', action.fine_control, False)
        self.task_action('s', action.stroke, True)
        self.task_action('s-up', action.stroke, False)

        self.add_task(self.stroke_task, 'stroke_task')


    def exit(self):
        self.remove_task('stroke_task')
        self.cam.store_state('stroke', overwrite=True)
        self.cam.load_state('aim')


