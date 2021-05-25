#! /usr/bin/env python

import pooltool.evolution as evolution

from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes import *


class ShotMode(CameraMode):
    keymap = {
        action.aim: False,
        action.fine_control: False,
        action.move: False,
        action.toggle_pause: False,
        action.undo_shot: False,
        action.restart_ani: False,
        action.quit: False,
        action.zoom: False,
        action.rewind: False,
        action.fast_forward: False,
    }

    def enter(self):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.shot_sim_overlay = GenericMenu(
            title = 'Calculating shot...',
            frame_color = (0,0,0,0.4),
            title_pos = (0,0,-0.2),
        )
        self.shot_sim_overlay.show()

        self.cue_stick.set_object_state_as_render_state()

        self.add_task(self.run_simulation, 'run_simulation', taskChain = 'simulation')

        self.task_action('escape', action.quit, True)
        self.task_action('mouse1', action.zoom, True)
        self.task_action('mouse1-up', action.zoom, False)
        self.task_action('a', action.aim, True)
        self.task_action('v', action.move, True)
        self.task_action('v-up', action.move, False)
        self.task_action('r', action.restart_ani, True)
        self.task_action('r-up', action.restart_ani, False)
        self.task_action('z', action.undo_shot, True)
        self.task_action('z-up', action.undo_shot, False)
        self.task_action('f', action.fine_control, True)
        self.task_action('f-up', action.fine_control, False)
        self.task_action('arrow_left', action.rewind, True)
        self.task_action('arrow_left-up', action.rewind, False)
        self.task_action('arrow_right', action.fast_forward, True)
        self.task_action('arrow_right-up', action.fast_forward, False)

        self.add_task(self.quit_task, 'quit_task')


    def exit(self, keep=True):
        """Exit shot mode

        Parameters
        ==========
        keep : bool, True
            If True, the system state will be set to the end state of the shot. Otherwise,
            the system state will be returned to the start state of the shot.
        """

        self.shot.finish_animation()
        self.shot.ball_animations.finish()

        if keep:
            self.shot.cue.reset_state()
            self.shot.cue.set_render_state_as_object_state()

            for ball in self.shot.balls.values():
                ball.reset_angular_integration()
        else:
            self.cam.load_state('stroke')
            for ball in self.shot.balls.values():
                if ball.history.is_populated():
                    ball.set(
                        rvw = ball.history.rvw[0],
                        s = ball.history.s[0],
                        t = 0,
                    )
                ball.set_render_state_as_object_state()
                ball.history.reset_history()

        self.shot.cue.update_focus()

        self.remove_task('shot_view_task')
        self.remove_task('shot_animation_task')
        self.remove_task('quit_task')
        self.shot = None


    def shot_view_task(self, task):
        if self.keymap[action.aim]:
            self.change_mode('aim')
        elif self.keymap[action.zoom]:
            self.zoom_camera()
        elif self.keymap[action.move]:
            self.move_camera()
        else:
            if task.time > 0.1:
                # Prevents shot follow through from moving camera
                self.rotate_camera(cue_stick_too=False)
            else:
                # Update mouse positions so there is not a big jump
                self.mouse.touch()

        return task.cont


    def shot_animation_task(self, task):
        if self.keymap[action.restart_ani]:
            self.shot.restart_animation()

        if self.keymap[action.rewind]:
            rate = 0.02 if not self.keymap[action.fine_control] else 0.002
            self.shot.offset_time(-rate*self.shot.playback_speed)

        if self.keymap[action.fast_forward]:
            rate = 0.02 if not self.keymap[action.fine_control] else 0.002
            self.shot.offset_time(rate*self.shot.playback_speed)

        if self.keymap[action.undo_shot]:
            exit_kwargs = dict(
                keep = False,
            )
            self.change_mode('aim', exit_kwargs=exit_kwargs)
            return

        return task.cont


    def run_simulation(self, task):
        """Run a pool simulation"""
        evolver = evolution.get_shot_evolver(algorithm='event')
        self.shot = evolver(cue=self.cue_stick, table=self.table, balls=self.balls)
        self.shot.simulate()
        self.shot.init_shot_animation()
        self.shot.loop_animation()

        self.accept('space', self.shot.toggle_pause)
        self.accept('arrow_up', self.shot.speed_up)
        self.accept('arrow_down', self.shot.slow_down)

        self.add_task(self.shot_view_task, 'shot_view_task')
        self.add_task(self.shot_animation_task, 'shot_animation_task')

        self.shot_sim_overlay.hide()

        return task.done


