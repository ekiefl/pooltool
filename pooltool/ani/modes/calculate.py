#! /usr/bin/env python

import pooltool.ani as ani
import pooltool.ani.utils as autils
import pooltool.evolution as evolution

from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes import Mode, action

import numpy as np

class CalculateMode(Mode):
    keymap = {
        action.move: False,
        action.quit: False,
        action.zoom: False,
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

        self.cue.set_object_state_as_render_state()

        self.add_task(self.run_simulation, 'run_simulation', taskChain = 'simulation')

        self.task_action('escape', action.quit, True)
        self.task_action('mouse1', action.zoom, True)
        self.task_action('mouse1-up', action.zoom, False)
        self.task_action('a', action.aim, True)
        self.task_action('v', action.move, True)
        self.task_action('v-up', action.move, False)

        self.add_task(self.calculate_view_task, 'calculate_view_task')


    def exit(self):
        self.remove_task('calculate_view_task')
        self.shot_sim_overlay.hide()


    def calculate_view_task(self, task):
        if not 'run_simulation' in self.tasks:
            # simulation calculation is finished
            self.change_mode('shot', enter_kwargs=dict(init_animations=True))
        elif self.keymap[action.zoom]:
            self.zoom_camera_calculate()
        elif self.keymap[action.move]:
            self.move_camera_calculate()
        else:
            if task.time > ani.rotate_downtime:
                # Prevents shot follow through from moving camera
                self.rotate_camera_calculate()
            else:
                # Update mouse positions so there is not a big jump
                self.mouse.touch()

        return task.cont


    def run_simulation(self, task):
        """Run a pool simulation"""
        evolver = evolution.get_shot_evolver(algorithm='event')
        self.shot = evolver(cue=self.cue, table=self.table, balls=self.balls)
        self.shot.simulate(continuize=True, dt=0.005)
        self.game.process_shot(self.shot)

        self.remove_task('run_simulation')

        return task.done


    def zoom_camera_calculate(self):
        with self.mouse:
            s = -self.mouse.get_dy()*ani.zoom_sensitivity

        self.player_cam.node.setPos(autils.multiply_cw(self.player_cam.node.getPos(), 1-s))


    def move_camera_calculate(self):
        with self.mouse:
            dxp, dyp = self.mouse.get_dx(), self.mouse.get_dy()

        h = self.player_cam.focus.getH() * np.pi/180 + np.pi/2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        self.player_cam.focus.setX(self.player_cam.focus.getX() + dx*ani.move_sensitivity)
        self.player_cam.focus.setY(self.player_cam.focus.getY() + dy*ani.move_sensitivity)


    def rotate_camera_calculate(self):
        fx, fy = ani.rotate_sensitivity_x, ani.rotate_sensitivity_y

        with self.mouse:
            alpha_x = self.player_cam.focus.getH() - fx * self.mouse.get_dx()
            alpha_y = max(min(0, self.player_cam.focus.getR() + fy * self.mouse.get_dy()), -90)

        self.player_cam.focus.setH(alpha_x) # Move view laterally
        self.player_cam.focus.setR(alpha_y) # Move view vertically
