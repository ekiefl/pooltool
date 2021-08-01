#! /usr/bin/env python

import pooltool
import pooltool.ani as ani
import pooltool.ani.utils as autils

from pooltool.ani.modes import Mode, action

import numpy as np

from direct.interval.IntervalGlobal import *


class CallShotMode(Mode):
    keymap = {
        action.quit: False,
        action.call_shot: True,
        'next': False,
    }


    def __init__(self):
        self.ball_highlight_offset = 0.1
        self.ball_highlight_amplitude = 0.03
        self.ball_highlight_frequency = 4

        self.ball_highlight = None
        self.picking = None


    def enter(self):
        self.ball_highlight_sequence = Parallel()

        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.closest_pocket = None
        self.closest_ball = None

        self.task_action('escape', action.quit, True)
        self.task_action('c', action.call_shot, True)
        self.task_action('c-up', action.call_shot, False)
        self.task_action('mouse1-up', 'next', True)

        self.picking = 'ball'

        self.add_task(self.call_shot_task, 'call_shot_task')



    def exit(self):
        self.remove_task('call_shot_task')
        if self.picking in ('ball', 'pocket'):
            CallShotMode.remove_ball_highlight(self)
        self.ball_highlight_sequence.pause()


    def call_shot_task(self, task):
        if not self.keymap[action.call_shot]:
            self.change_mode(self.last_mode)
            return task.done

        self.move_camera_call_shot()

        if self.picking == 'ball':
            closest = CallShotMode.find_closest_ball(self)
            if closest != self.closest_ball:
                CallShotMode.remove_ball_highlight(self)
                self.closest_ball = closest
                self.ball_highlight = self.closest_ball.get_node('ball')
                CallShotMode.add_ball_highlight(self)

            if self.keymap['next']:
                self.keymap['next'] = False
                self.game.ball_call = self.closest_ball
                self.game.log.add_msg(f"Calling the {self.closest_ball.id} ball", sentiment='neutral')
                self.picking = 'pocket'

        elif self.picking == 'pocket':
            closest = self.find_closest_pocket()
            if closest != self.closest_pocket:
                self.closest_pocket = closest
                self.move_ball_highlight()

            if self.keymap['next']:
                self.keymap['next'] = False
                self.game.pocket_call = self.closest_pocket
                self.game.log.add_msg(f"Calling the {self.closest_pocket.id} pocket", sentiment='neutral')
                self.change_mode(self.last_mode)
                return task.done

        return task.cont


    def move_ball_highlight(self):
        if self.closest_pocket is not None:
            self.ball_highlight_sequence.pause()
            self.ball_highlight_sequence = Parallel(
                LerpFunc(
                    self.ball_highlight.setX,
                    fromData=self.ball_highlight.getX(),
                    toData=self.closest_pocket.center[0],
                    duration=0.07,
                    blendType='easeInOut',
                ),
                LerpFunc(
                    self.ball_highlight.setY,
                    fromData=self.ball_highlight.getY(),
                    toData=self.closest_pocket.center[1],
                    duration=0.07,
                    blendType='easeInOut',
                ),
            )
            self.ball_highlight_sequence.start()


    def find_closest_pocket(self):
        cam_pos = self.player_cam.focus.getPos()
        d_min = np.inf
        closest = None
        for pocket in self.table.pockets.values():
            d = np.linalg.norm(pocket.center - cam_pos)
            if d < d_min:
                d_min, closest = d, pocket

        return closest


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


    def find_closest_ball(self):
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


    def move_camera_call_shot(self):
        with self.mouse:
            dxp, dyp = self.mouse.get_dx(), self.mouse.get_dy()

        h = self.player_cam.focus.getH() * np.pi/180 + np.pi/2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        self.player_cam.focus.setX(self.player_cam.focus.getX() + dx*ani.move_sensitivity)
        self.player_cam.focus.setY(self.player_cam.focus.getY() + dy*ani.move_sensitivity)

