#! /usr/bin/env python

import psim.utils as utils
import psim.engine as engine
import psim.ani.utils as autils
import psim.ani.action as action

import sys
import numpy as np

class Tasks(object):
    def menu_task(self, task):
        if self.keymap[action.exit]:
            sys.exit()

        return task.cont


    def quit_task(self, task):
        if self.keymap[action.quit]:
            self.keymap[action.quit] = False
            self.change_mode('menu')
            self.close_scene()

        return task.cont


    def view_task(self, task):
        if self.keymap[action.aim]:
            self.change_mode('aim')
            return
        elif self.keymap[action.zoom]:
            self.zoom_camera()
        elif self.keymap[action.move]:
            self.move_camera()
        else:
            self.rotate_camera(cue_stick_too=False)

        return task.cont


    def aim_task(self, task):
        if self.keymap[action.view]:
            self.change_mode('view')
            return
        elif self.keymap[action.shoot]:
            self.stroke_cue_stick()
        elif self.keymap[action.zoom]:
            self.zoom_camera()
        else:
            self.rotate_camera(cue_stick_too=True)

        return task.cont


    def stroke_cue_stick(self):
        # Store this in case the cue strikes the ball
        dt = self.mouse.get_dt()
        dx = self.mouse.get_dy()*0.1

        cue_stick_node = self.cue_stick.get_node('cue_stick')

        newX = max(-0.5, cue_stick_node.getX() - dx)
        cue_stick_node.setX(newX)

        # get_dx() is called so that self.last_x is updated. Failing to do this will create a
        # potentially very large return value of get_dx() the next time it is called.
        self.mouse.get_dx()

        if newX < 0:
            self.take_shot(V0=dx/dt)
            self.simulate_shot()

            for ball in self.balls.values():
                ball.set_node_state_as_state()

            self.cue_stick.set_node_state_as_state()
            self.change_mode('view')


    def take_shot(self, V0):
        self.cue_stick.get_node('cue_stick').setX(0)

        self.cue_stick.set_state(V0=V0)
        self.cue_stick.set_state_as_node_state()

        self.cue_stick.strike(self.balls['cue'])


    def simulate_shot(self):
        sim = engine.ShotSimulation(cue=self.cue_stick, table=self.table, balls=self.balls)
        sim.simulate()
        sim.continuize(dt=0.01)


    def zoom_camera(self):
        s = -self.mouse.get_dy()*0.3
        self.cam.node.setPos(autils.multiply_cw(self.cam.node.getPos(), 1-s))

        # get_dx() is called so that self.last_x is updated. Failing to do this will create a
        # potentially very large return value of get_dx() the next time it is called.
        self.mouse.get_dx()


    def move_camera(self):
        dxp, dyp = self.mouse.get_dx(), self.mouse.get_dy()

        # NOTE This conversion _may_ depend on how I initialized self.cam.focus
        h = self.cam.focus.getH() * np.pi/180 + np.pi/2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        f = 0.6
        self.cam.focus.setX(self.cam.focus.getX() + dx*f)
        self.cam.focus.setY(self.cam.focus.getY() + dy*f)


    def fix_cue_stick_to_camera(self):
        self.cue_stick.get_node('cue_stick_focus').setH(self.cam.focus.getH())


    def rotate_camera(self, cue_stick_too=False):
        if self.keymap[action.fine_control]:
            fx, fy = 2, 0
        else:
            fx, fy = 13, 3

        alpha_x = self.cam.focus.getH() - fx * self.mouse.get_dx()
        alpha_y = max(min(0, self.cam.focus.getR() + fy * self.mouse.get_dy()), -70)

        self.cam.focus.setH(alpha_x) # Move view laterally
        self.cam.focus.setR(alpha_y) # Move view vertically

        if cue_stick_too:
            self.fix_cue_stick_to_camera()


    def monitor(self, task):
        #print(f"Mode: {self.mode}")
        #print(f"Tasks: {list(self.tasks.keys())}")
        #print(f"Memory: {utils.get_total_memory_usage()}")
        #print(f"Actions: {[k for k in self.keymap if self.keymap[k]]}")
        #print()

        return task.cont



