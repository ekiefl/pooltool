#! /usr/bin/env python

import psim.utils as utils
import psim.ani.utils as autils
import psim.ani.action as action

import sys

class Tasks(object):
    def menu_task(self, task):
        if self.keymap[action.exit]:
            sys.exit()

        return task.cont


    def quit_task(self, task):
        if self.keymap[action.quit]:
            self.keymap[action.quit] = False
            self.close_scene()
            self.change_mode('menu')

        return task.cont


    def view_task(self, task):
        if self.keymap[action.aim]:
            self.change_mode('aim')
            return
        elif self.keymap[action.zoom]:
            self.zoom_camera()
        else:
            self.rotate_camera(cue_stick_too=True)

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
        s = self.mouse.get_dy()*8
        pos = max(-20, self.cue_stick.getX() - s)
        self.cue_stick.setX(pos)

        # get_dx() is called so that self.last_x is updated. Failing to do this will create a
        # potentially very large return value of get_dx() the next time it is called.
        self.mouse.get_dx()

        if pos < 0:
            # Collision
            self.cue_stick.setX(0)


    def zoom_camera(self):
        s = -self.mouse.get_dy()*0.3
        self.camera.setPos(autils.multiply_cw(self.camera.getPos(), 1-s))

        # get_dx() is called so that self.last_x is updated. Failing to do this will create a
        # potentially very large return value of get_dx() the next time it is called.
        self.mouse.get_dx()


    def fix_cue_stick_to_camera(self):
        self.cue_stick_focus.setH(self.camera_focus.getH())


    def rotate_camera(self, cue_stick_too=False):
        if self.keymap[action.fine_control]:
            fx, fy = 2, 0
        else:
            fx, fy = 10, 3

        alpha_x = self.camera_focus.getH() - fx * self.mouse.get_dx()
        alpha_y = max(min(0, self.camera_focus.getR() + fy * self.mouse.get_dy()), -70)

        self.camera_focus.setH(alpha_x) # Move view laterally
        self.camera_focus.setR(alpha_y) # Move view vertically

        if cue_stick_too:
            self.fix_cue_stick_to_camera()


    def monitor(self, task):
        #print(f"Mode: {self.mode}")
        #print(f"Tasks: {list(self.tasks.keys())}")
        #print(f"Memory: {utils.get_total_memory_usage()}")
        #print(f"Actions: {[k for k in self.keymap if self.keymap[k]]}")
        #print()

        return task.cont



