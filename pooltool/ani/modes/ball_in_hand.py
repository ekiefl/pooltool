#! /usr/bin/env python

import pooltool
import pooltool.ani as ani
import pooltool.ani.utils as autils

from pooltool.utils import panda_path
from pooltool.ani.modes import Mode, action

import numpy as np

from panda3d.core import TransparencyAttrib
from direct.interval.IntervalGlobal import *


class BallInHandMode(Mode):
    keymap = {
        action.quit: False,
        action.ball_in_hand: True,
        'next': False,
    }


    def __init__(self):
        self.trans_ball = None
        self.grab_ball_node = None
        self.grab_ball_shadow_node = None
        self.picking = None


    def enter(self):
        self.grab_selection_highlight_sequence = Parallel()

        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.grabbed_ball = None

        self.task_action('escape', action.quit, True)
        self.task_action('g', action.ball_in_hand, True)
        self.task_action('g-up', action.ball_in_hand, False)
        self.task_action('mouse1-up', 'next', True)

        num_options = len(self.game.active_player.ball_in_hand)
        if num_options == 0:
            # FIXME add message
            self.picking = 'ball'
        elif num_options == 1:
            self.grabbed_ball = self.balls[self.game.active_player.ball_in_hand[0]]
            self.grab_ball_node = self.grabbed_ball.get_node('ball')
            self.grab_ball_shadow_node = self.grabbed_ball.get_node('shadow')
            self.picking = 'placement'
        else:
            self.picking = 'ball'

        self.add_task(self.ball_in_hand_task, 'ball_in_hand_task')


    def exit(self, success=False):
        self.remove_task('ball_in_hand_task')
        BallInHandMode.remove_transparent_ball(self)

        if self.picking == 'ball':
            BallInHandMode.remove_grab_selection_highlight(self)

        if self.picking == 'placement' and not success:
            self.grabbed_ball.set_render_state_as_object_state()

        self.grab_selection_highlight_sequence.pause()


    def ball_in_hand_task(self, task):
        if not self.keymap[action.ball_in_hand]:
            self.change_mode(
                self.last_mode,
                enter_kwargs=dict(load_prev_cam=False),
            )
            return task.done

        self.move_camera_ball_in_hand()

        if self.picking == 'ball':
            closest = BallInHandMode.find_closest_ball(self)
            if closest != self.grabbed_ball:
                BallInHandMode.remove_grab_selection_highlight(self)
                self.grabbed_ball = closest
                self.grab_ball_node = self.grabbed_ball.get_node('ball')
                self.grab_ball_shadow_node = self.grabbed_ball.get_node('shadow')
                BallInHandMode.add_grab_selection_highlight(self)

            if self.keymap['next']:
                self.keymap['next'] = False
                self.picking = 'placement'
                self.player_cam.update_focus(self.grab_ball_node.getPos())
                BallInHandMode.remove_grab_selection_highlight(self)
                BallInHandMode.add_transparent_ball(self)

        elif self.picking == 'placement':
            self.move_grabbed_ball()

            if self.keymap['next']:
                self.keymap['next'] = False
                if self.try_placement():
                    BallInHandMode.exit(self, success=True)
                    BallInHandMode.enter(self)
                    return task.done
                else:
                    # FIXME add error sound and message
                    pass

        return task.cont


    def try_placement(self):
        """Checks if grabbed ball overlaps with others. If no, places and returns True. If yes, returns False"""
        r, pos = self.grabbed_ball.R, np.array(self.grab_ball_node.getPos())

        for ball in self.balls.values():
            if ball == self.grabbed_ball:
                continue
            if np.linalg.norm(ball.rvw[0] - pos) <= (r + ball.R):
                return False

        self.grabbed_ball.set_object_state_as_render_state()
        return True


    def move_grabbed_ball(self):
        x, y = self.player_cam.focus.getX(), self.player_cam.focus.getY()

        self.grab_ball_node.setX(x)
        self.grab_ball_node.setY(y)
        self.grab_ball_shadow_node.setX(x)
        self.grab_ball_shadow_node.setY(y)


    def remove_grab_selection_highlight(self):
        if self.grabbed_ball is not None:
            node = self.grabbed_ball.get_node('ball')
            node.setScale(node.getScale()/ani.ball_highlight['ball_factor'])
            self.grab_ball_shadow_node.setAlphaScale(1)
            self.grab_ball_shadow_node.setScale(1)
            self.grabbed_ball.set_render_state_as_object_state()
            self.remove_task('grab_selection_highlight_animation')


    def add_grab_selection_highlight(self):
        if self.grabbed_ball is not None:
            self.add_task(self.grab_selection_highlight_animation, 'grab_selection_highlight_animation')
            node = self.grabbed_ball.get_node('ball')
            node.setScale(node.getScale()*ani.ball_highlight['ball_factor'])


    def grab_selection_highlight_animation(self, task):
        phase = task.time * ani.ball_highlight['ball_frequency']

        new_height = ani.ball_highlight['ball_offset'] + ani.ball_highlight['ball_amplitude'] * np.sin(phase)
        self.grab_ball_node.setZ(new_height)

        new_alpha = ani.ball_highlight['shadow_alpha_offset'] + ani.ball_highlight['shadow_alpha_amplitude'] * np.sin(-phase)
        new_scale = ani.ball_highlight['shadow_scale_offset'] + ani.ball_highlight['shadow_scale_amplitude'] * np.sin(phase)
        self.grab_ball_shadow_node.setAlphaScale(new_alpha)
        self.grab_ball_shadow_node.setScale(new_scale)

        return task.cont


    def add_transparent_ball(self):
        self.trans_ball = base.loader.loadModel(panda_path(self.grabbed_ball.model_path))
        self.trans_ball.reparentTo(render.find('scene').find('cloth'))
        self.trans_ball.setTransparency(TransparencyAttrib.MAlpha)
        self.trans_ball.setAlphaScale(0.4)
        self.trans_ball.setPos(self.grabbed_ball.get_node('ball').getPos())
        self.trans_ball.setHpr(self.grabbed_ball.get_node('sphere').getHpr())


    def remove_transparent_ball(self):
        if self.trans_ball is not None:
            self.trans_ball.removeNode()
        self.trans_ball = None


    def find_closest_ball(self):
        cam_pos = self.player_cam.focus.getPos()
        d_min = np.inf
        closest = None
        for ball in self.balls.values():
            if ball.id not in self.game.active_player.ball_in_hand:
                continue
            if ball.s == pooltool.pocketed:
                continue
            d = np.linalg.norm(ball.rvw[0] - cam_pos)
            if d < d_min:
                d_min, closest = d, ball

        return closest


    def move_camera_ball_in_hand(self):
        with self.mouse:
            dxp, dyp = self.mouse.get_dx(), self.mouse.get_dy()

        h = self.player_cam.focus.getH() * np.pi/180 + np.pi/2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        self.player_cam.focus.setX(self.player_cam.focus.getX() + dx*ani.move_sensitivity)
        self.player_cam.focus.setY(self.player_cam.focus.getY() + dy*ani.move_sensitivity)


