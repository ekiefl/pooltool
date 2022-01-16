#! /usr/bin/env python

import pooltool as pt
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
        action.show_help: False,
        action.close_scene: False,
        action.introspect: False,
        action.next_shot: False,
        action.prev_shot: False,
    }

    def enter(self, init_animations=False, single_instance=False):
        """Enter method for Shot

        Parameters
        ==========
        init_animations : bool, False
            If True, the shot animations are built and looped via SystemCollection.init_animation()
            and SystemCollection.loop_animation()

        single_instance : bool, False
            If True, exiting with `esc` will close the scene. Otherwise, quit_task will be called,
            and user is brought back to main menu.
        """
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        if init_animations:
            self.shots.set_animation()
            self.shots.loop_animation()
            self.shots.skip_stroke()

        self.hud_elements.get('english').set(self.shots.active.cue.a, self.shots.active.cue.b)
        self.hud_elements.get('jack').set(self.shots.active.cue.theta)
        self.hud_elements.get('power').set(self.shots.active.cue.V0)

        self.accept('space', self.shots.toggle_pause)
        self.accept('arrow_up', self.shots.speed_up)
        self.accept('arrow_down', self.shots.slow_down)

        if single_instance:
            self.task_action('escape', action.close_scene, True)
            self.task_action('escape-up', action.close_scene, False)
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
        self.task_action('h', action.show_help, True)
        self.task_action('i', action.introspect, True)
        self.task_action('i-up', action.introspect, False)
        self.task_action('n-up', action.next_shot, True)
        self.task_action('p-up', action.prev_shot, True)

        self.add_task(self.shot_view_task, 'shot_view_task')
        self.add_task(self.shot_animation_task, 'shot_animation_task')


    def exit(self, key='soft'):
        """Exit shot mode

        Parameters
        ==========
        key : str, 'soft'
            Specifies how shot mode should be exited. Can be any of {'advance', 'reset', 'soft'}. 'advance'
            and 'reset' end the animation, whereas 'soft' exits shot mode with the animations still
            playing. 'advance' sets the system state to the end state of the shot, whereas 'reset' returns
            the system state to the start state of the shot.
        """
        assert key in {'advance', 'reset', 'soft'}

        if key == 'advance':
            # If we are here, the plan is probably to return to 'aim' mode so another shot can be
            # taken. This shot needs to be defined by its own system that has yet to be simulated.
            # Depending how 'shot' mode was entered, this system may already exist in self.shots.
            # The following code checks that by seeing whether the latest system has any events. If
            # not, the system is unsimulated and is perfectly fit for 'aim' mode, but if the system
            # has events, a fresh system needs to be appended to self.shots.
            make_new = True if len(self.shots[-1].events) else False
            if make_new:
                if self.shots.active_index != len(self.shots) - 1:
                    # Replaying shot that is not most recent. Teardown and then buildup most recent
                    self.shots.clear_animation()
                    self.shots.active.teardown()
                    self.shots.set_active(-1)
                    self.shots.active.buildup()

                self.shots.append_copy_of_active(
                    state = 'current',
                    reset_history = True,
                    as_active = False,
                )

                # Set the initial orientations of new shot to final orientations of old shot
                for ball_id in self.shots.active.balls:
                    old_ball = self.shots.active.balls[ball_id]
                    new_ball = self.shots[-1].balls[ball_id]
                    new_ball.initial_orientation = old_ball.get_final_orientation()
            else:
                # The latest entry in the collection is an unsimulated shot. Perfect
                pass

            # Switch shots
            self.shots.clear_animation()
            self.shots.active.teardown()
            self.shots.set_active(-1)
            self.shots.active.buildup()

            self.init_collisions()

            if make_new:
                self.shots.active.cue.reset_state()
            self.shots.active.cue.set_render_state_as_object_state()

            # Set the HUD
            V0, _, theta, a, b, _ = self.shots.active.cue.get_render_state()
            self.hud_elements.get('english').set(a, b)
            self.hud_elements.get('jack').set(theta)
            self.hud_elements.get('power').set(self.shots.active.cue.V0)

        elif key == 'reset':
            self.shots.clear_animation()
            self.player_cam.load_state(self.mode_stroked_from)
            for ball in self.shots.active.balls.values():
                if ball.history.is_populated():
                    ball.set(
                        rvw = ball.history.rvw[0],
                        s = ball.history.s[0],
                        t = 0,
                    )
                    ball.get_node('pos').setQuat(ball.quats[0])
                ball.set_render_state_as_object_state()
                ball.history.reset()

            self.shots.active.cue.update_focus()
            self.shots.active.reset_animation()

        self.remove_task('shot_view_task')
        self.remove_task('shot_animation_task')


    def shot_view_task(self, task):
        if self.keymap[action.close_scene]:
            self.player_cam.store_state('last_scene', overwrite=True)
            self.close_scene()
            self.end_mode()
            self.stop()
        elif self.keymap[action.aim]:
            self.game.advance(self.shots[-1])
            if self.game.game_over:
                self.change_mode('game_over')
            else:
                self.change_mode('aim', exit_kwargs=dict(key='advance'))
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
            self.shots.restart_animation()

        elif self.keymap[action.rewind]:
            self.shots.rewind()

        elif self.keymap[action.fast_forward]:
            self.shots.fast_forward()

        elif self.keymap[action.undo_shot]:
            self.change_mode(self.mode_stroked_from, exit_kwargs=dict(key='reset'), enter_kwargs=dict(load_prev_cam=True))

        elif self.keymap[action.prev_shot]:
            self.keymap[action.prev_shot] = False
            shot_index = self.shots.active_index - 1
            while True:
                if shot_index < 0:
                    shot_index = len(self.shots)-1
                if len(self.shots[shot_index].events):
                    break
                shot_index -= 1
            self.change_animation(shot_index)

        elif self.keymap[action.next_shot]:
            self.keymap[action.next_shot] = False
            shot_index = self.shots.active_index+1# if self.shots.active_index != len(self.shots)-1 else 0
            while True:
                if shot_index == len(self.shots):
                    shot_index = 0
                if len(self.shots[shot_index].events):
                    break
                shot_index += 1
            self.change_animation(shot_index)

        return task.cont


    def change_animation(self, shot_index):
        # Switch shots
        self.shots.clear_animation()
        self.shots.active.teardown()
        self.shots.set_active(shot_index)
        self.shots.active.buildup()

        # A lot of dumb things to make the cue track the initial position of the ball
        dummy = pt.Ball('dummy')
        dummy.R = self.shots.active.cue.cueing_ball.R
        dummy.rvw = self.shots.active.cue.cueing_ball.history.rvw[0]
        dummy.render()
        self.shots.active.cue.init_focus(dummy)
        self.shots.active.cue.set_render_state_as_object_state()
        self.shots.active.cue.follow = None
        dummy.remove_nodes()
        del dummy

        # Initialize the animation
        self.shots.set_animation()
        self.shots.loop_animation()

        # Set the HUD
        self.hud_elements.get('english').set(self.shots.active.cue.a, self.shots.active.cue.b)
        self.hud_elements.get('jack').set(self.shots.active.cue.theta)
        self.hud_elements.get('power').set(self.shots.active.cue.V0)


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
