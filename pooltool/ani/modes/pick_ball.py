#! /usr/bin/env python

import pooltool
import pooltool.ani as ani
import pooltool.ani.utils as autils

from pooltool.ani.modes import Mode, action

import numpy as np


class PickBallMode(Mode):
    keymap = {
        action.quit: False,
        action.pick_ball: True,
    }

    def __init__(self):
        self.highlight_factor = 2


    def enter(self):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.closest_ball = None

        self.task_action('escape', action.quit, True)
        self.task_action('q', action.pick_ball, True)
        self.task_action('q-up', action.pick_ball, False)

        self.add_task(self.pick_ball_task, 'pick_ball_task')


    def exit(self):
        self.cueing_ball = self.closest_ball
        self.cue.init_focus(self.closest_ball)
        self.remove_task('pick_ball_task')


    def pick_ball_task(self, task):
        if not self.keymap[action.pick_ball]:
            self.remove_highlight()
            self.change_mode('aim')

        self.move_camera_pick_ball()

        closest = self.find_closest()
        if closest != self.closest_ball:
            self.remove_highlight()
            self.closest_ball = closest
            self.add_highlight()

        return task.cont


    def remove_highlight(self):
        if self.closest_ball is not None:
            node = self.closest_ball.get_node('ball')
            node.setScale(node.getScale()/self.highlight_factor)


    def add_highlight(self):
        if self.closest_ball is not None:
            node = self.closest_ball.get_node('ball')
            node.setScale(node.getScale()*self.highlight_factor)


    def find_closest(self):
        cam_pos = self.player_cam.focus.getPos()
        d_min = np.inf
        closest = None
        for ball in self.balls.values():
            if ball.s == pooltool.pocketed:
                continue
            d = (ball.get_node('ball').getPos() - cam_pos).length()
            if d < d_min:
                d_min, closest = d, ball

        return closest


    def move_camera_pick_ball(self):
        with self.mouse:
            dxp, dyp = self.mouse.get_dx(), self.mouse.get_dy()

        h = self.player_cam.focus.getH() * np.pi/180 + np.pi/2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        self.player_cam.focus.setX(self.player_cam.focus.getX() + dx*ani.move_sensitivity)
        self.player_cam.focus.setY(self.player_cam.focus.getY() + dy*ani.move_sensitivity)


