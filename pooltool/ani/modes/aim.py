#! /usr/bin/env python

from pooltool.ani.modes import *

import numpy as np


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

    def enter(self, load_prev_cam=False):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.cue_stick.show_nodes()
        self.cue_stick.get_node('cue_stick').setX(0)
        self.cam.update_focus(self.balls['cue'].get_node('ball').getPos())
        if load_prev_cam:
            self.cam.load_state('aim')

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


    def aim_task(self, task):
        if self.keymap[action.view]:
            self.change_mode('view')
        elif self.keymap[action.stroke]:
            self.change_mode('stroke')
        elif self.keymap[action.zoom]:
            self.zoom_camera()
        elif self.keymap[action.elevation]:
            self.elevate_cue()
        elif self.keymap[action.english]:
            self.apply_english()
        else:
            self.rotate_camera(cue_stick_too=True)

        return task.cont


    def elevate_cue(self):
        cue = self.cue_stick.get_node('cue_stick_focus')

        with self.mouse:
            delta_elevation = self.mouse.get_dy()*3

        old_elevation = -cue.getR()
        new_elevation = max(0, min(80, old_elevation + delta_elevation))
        cue.setR(-new_elevation)


    def apply_english(self):
        with self.mouse:
            dx, dy = self.mouse.get_dx(), self.mouse.get_dy()

        cue = self.cue_stick.get_node('cue_stick')
        R = self.cue_stick.follow.R

        f = 0.1
        delta_y, delta_z = dx*f, dy*f

        max_english = 5/10

        # y corresponds to side spin, z to top/bottom spin
        new_y = cue.getY() + delta_y
        new_z = cue.getZ() + delta_z

        norm = np.sqrt(new_y**2 + new_z**2)
        if norm > max_english*R:
            new_y *= max_english*R/norm
            new_z *= max_english*R/norm

        cue.setY(new_y)
        cue.setZ(new_z)


