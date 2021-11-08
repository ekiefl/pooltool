#! /usr/bin/env python

import pooltool.ani as ani
import pooltool.ani.utils as autils

from pooltool.ani.modes import Mode, action

import numpy as np

class ShotMode(Mode):
    keymap = {
        action.aim: False,
        action.move: False,
        action.toggle_pause: False,
        action.undo_shot: False,
        action.restart_ani: False,
        action.quit: False,
        action.zoom: False,
        action.rewind: False,
        action.fast_forward: False,
        action.cam_save: False,
        action.cam_load: False,
        action.close_scene: False,
    }

    def enter(self, init_animations=False, single_instance=False):
        """Enter method for Shot

        Parameters
        ==========
        init_animations : bool, False
            If True, the shot animations are built and looped via self.shot.init_shot_animation()
            and self.shot.loop_animation()

        single_instance : bool, False
            If True, exiting with `esc` will close the scene. Otherwise, quit_task will be called,
            and user is brought back to main menu.
        """
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        if init_animations:
            self.shot.init_shot_animation()
            self.shot.loop_animation()

        self.accept('space', self.shot.toggle_pause)
        self.accept('arrow_up', self.shot.speed_up)
        self.accept('arrow_down', self.shot.slow_down)

        if single_instance:
            self.task_action('escape', action.close_scene, True)
        else:
            self.task_action('escape', action.quit, True)
            self.task_action('a', action.aim, True)
            self.task_action('z', action.undo_shot, True)
            self.task_action('z-up', action.undo_shot, False)

        self.task_action('mouse1', action.zoom, True)
        self.task_action('mouse1-up', action.zoom, False)
        self.task_action('v', action.move, True)
        self.task_action('v-up', action.move, False)
        self.task_action('r', action.restart_ani, True)
        self.task_action('r-up', action.restart_ani, False)
        self.task_action('arrow_left', action.rewind, True)
        self.task_action('arrow_left-up', action.rewind, False)
        self.task_action('arrow_right', action.fast_forward, True)
        self.task_action('arrow_right-up', action.fast_forward, False)
        self.task_action('1', action.cam_save, True)
        self.task_action('2', action.cam_load, True)

        self.add_task(self.shot_view_task, 'shot_view_task')
        self.add_task(self.shot_animation_task, 'shot_animation_task')


    def exit(self, key='soft'):
        """Exit shot mode

        Parameters
        ==========
        key : str, 'soft'
            Specifies how shot mode should be exited. Can be any of {'end', 'reset', 'soft'}. 'end'
            and 'reset' end the animation, whereas 'soft' exits shot mode with the animations still
            playing. 'end' sets the system state to the end state of the shot, whereas 'reset' returns
            the system state to the start state of the shot.
        """
        assert key in {'end', 'reset', 'soft'}

        if key != 'soft':
            self.shot.finish_animation()
            self.shot.ball_animations.finish()

        if key == 'end':
            self.shot.cue.reset_state()
            self.shot.cue.set_render_state_as_object_state()

            if self.is_game:
                _, _, theta, a, b, _ = self.shot.cue.get_render_state()
                english = self.hud_elements.get('english').set(a, b)
                jack = self.hud_elements.get('jack').set(theta)

            for ball in self.shot.balls.values():
                ball.reset_angular_integration()
                ball.set_render_state_as_object_state()

            self.shot.cue.update_focus()

        elif key == 'reset':
            self.player_cam.load_state('stroke')
            for ball in self.shot.balls.values():
                if ball.history.is_populated():
                    ball.set(
                        rvw = ball.history.rvw[0],
                        s = ball.history.s[0],
                        t = 0,
                    )
                    ball.get_node('ball').setQuat(ball.quats[0])
                ball.set_render_state_as_object_state()
                ball.history.reset_history()

            self.shot.cue.update_focus()

        self.remove_task('shot_view_task')
        self.remove_task('shot_animation_task')


    def shot_view_task(self, task):
        if self.keymap[action.close_scene]:
            self.close_scene()
            self.end_mode()
            self.stop()
        elif self.keymap[action.aim]:
            self.game.advance(self.shot)
            if self.game.game_over:
                self.change_mode('game_over')
            else:
                self.change_mode('aim', exit_kwargs=dict(key='end'))
        elif self.keymap[action.zoom]:
            self.zoom_camera_shot()
        elif self.keymap[action.move]:
            self.move_camera_shot()
        else:
            if task.time > ani.rotate_downtime:
                # Prevents shot follow through from moving camera
                self.rotate_camera_shot()
            else:
                # Update mouse positions so there is not a big jump
                self.mouse.touch()

        return task.cont


    def shot_animation_task(self, task):
        if self.keymap[action.restart_ani]:
            self.shot.restart_animation()

        if self.keymap[action.rewind]:
            self.shot.offset_time(-ani.fast_forward_dt*self.shot.playback_speed)

        if self.keymap[action.fast_forward]:
            self.shot.offset_time(ani.rewind_dt*self.shot.playback_speed)

        if self.keymap[action.undo_shot]:
            self.change_mode(self.mode_stroked_from, exit_kwargs=dict(key='reset'), enter_kwargs=dict(load_prev_cam=True))

        return task.cont


    def zoom_camera_shot(self):
        with self.mouse:
            s = -self.mouse.get_dy()*ani.zoom_sensitivity

        self.player_cam.node.setPos(autils.multiply_cw(self.player_cam.node.getPos(), 1-s))


    def move_camera_shot(self):
        with self.mouse:
            dxp, dyp = self.mouse.get_dx(), self.mouse.get_dy()

        h = self.player_cam.focus.getH() * np.pi/180 + np.pi/2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        self.player_cam.focus.setX(self.player_cam.focus.getX() + dx*ani.move_sensitivity)
        self.player_cam.focus.setY(self.player_cam.focus.getY() + dy*ani.move_sensitivity)


    def rotate_camera_shot(self):
        fx, fy = ani.rotate_sensitivity_x, ani.rotate_sensitivity_y

        with self.mouse:
            alpha_x = self.player_cam.focus.getH() - fx * self.mouse.get_dx()
            alpha_y = max(min(0, self.player_cam.focus.getR() + fy * self.mouse.get_dy()), -90)

        self.player_cam.focus.setH(alpha_x) # Move view laterally
        self.player_cam.focus.setR(alpha_y) # Move view vertically
