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
        self.ball_highlight_factor = 2
        self.ball_highlight_offset = 0.1
        self.ball_highlight_amplitude = 0.03
        self.ball_highlight_frequency = 4


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
        self.remove_ball_highlight()
        self.cueing_ball = self.closest_ball
        self.cue.init_focus(self.closest_ball)
        self.remove_task('pick_ball_task')


    def pick_ball_task(self, task):
        if not self.keymap[action.pick_ball]:
            self.change_mode('aim')
            return task.done

        self.move_camera_pick_ball()

        closest = self.find_closest()
        if closest != self.closest_ball:
            self.remove_ball_highlight()
            self.closest_ball = closest
            self.ball_highlight = self.closest_ball.get_node('ball')
            self.add_ball_highlight()

        return task.cont


    def remove_ball_highlight(self):
        if self.closest_ball is not None:
            node = self.closest_ball.get_node('ball')
            node.setScale(node.getScale()/self.ball_highlight_factor)
            self.closest_ball.set_render_state_as_object_state()
            self.remove_task('ball_highlight_animation')


    def add_ball_highlight(self):
        if self.closest_ball is not None:
            self.add_task(self.ball_highlight_animation, 'ball_highlight_animation')
            node = self.closest_ball.get_node('ball')
            node.setScale(node.getScale()*self.ball_highlight_factor)


    def ball_highlight_animation(self, task):
        phase = task.time * self.ball_highlight_frequency
        new_height = self.ball_highlight_offset + self.ball_highlight_amplitude * np.sin(phase)
        self.ball_highlight.setZ(new_height)

        return task.cont


    def find_closest(self):
        cam_pos = self.player_cam.focus.getPos()
        d_min = np.inf
        closest = None
        for ball in self.balls.values():
            if ball.s == pooltool.pocketed:
                continue
            d = np.linalg.norm(ball.rvw[0] - cam_pos)
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


