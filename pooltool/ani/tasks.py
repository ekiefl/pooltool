#! /usr/bin/env python

import pooltool.evolution as evolution
import pooltool.ani.utils as autils
import pooltool.ani.action as action

import sys
import numpy as np

class Tasks(object):
    frame = 0

    def menu_task(self, task):
        if self.keymap[action.exit]:
            sys.exit()

        if self.keymap[action.new_game]:
            self.go()

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
        elif self.keymap[action.stroke]:
            self.change_mode('stroke')
        elif self.keymap[action.zoom]:
            self.zoom_camera()
        elif self.keymap[action.elevation]:
            self.elevate_cue()
        elif self.keymap[action.english]:
            self.apply_english()
        else:
            self.rotate_camera(cue_stick_too=True)

        return task.cont


    def elevate_cue(self):
        cue = self.cue_stick.get_node('cue_stick_focus')

        with self.mouse:
            delta_elevation = self.mouse.get_dy()*3

        old_elevation = -cue.getR()
        new_elevation = max(0, min(80, old_elevation + delta_elevation))
        cue.setR(-new_elevation)


    def apply_english(self):
        with self.mouse:
            dx, dy = self.mouse.get_dx(), self.mouse.get_dy()

        cue = self.cue_stick.get_node('cue_stick')
        R = self.cue_stick.follow.R

        f = 0.1
        delta_y, delta_z = dx*f, dy*f

        max_english = 5/10

        # y corresponds to side spin, z to top/bottom spin
        new_y = cue.getY() + delta_y
        new_z = cue.getZ() + delta_z

        norm = np.sqrt(new_y**2 + new_z**2)
        if norm > max_english*R:
            new_y *= max_english*R/norm
            new_z *= max_english*R/norm

        cue.setY(new_y)
        cue.setZ(new_z)


    def stroke_task(self, task):
        if self.keymap[action.stroke]:
            if self.stroke_cue_stick():
                self.change_mode('shot')
                return
        else:
            self.change_mode('aim')
            return

        return task.cont


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


    def stroke_cue_stick(self):
        f = 0.4
        max_speed_cue = 7 # [m/s]
        max_speed_mouse = max_speed_cue/f # [px/s]
        max_backstroke = self.cue_stick.length/2 # [m]

        with self.mouse:
            dt = self.mouse.get_dt()
            dx = self.mouse.get_dy()

        speed_mouse = dx/dt
        if speed_mouse > max_speed_mouse:
            dx *= max_speed_mouse/speed_mouse

        cue_stick_node = self.cue_stick.get_node('cue_stick')
        newX = min(max_backstroke, cue_stick_node.getX() - dx*f)

        if newX < 0:
            newX = 0
            collision = True if self.cue_stick.is_shot() else False
        else:
            collision = False

        cue_stick_node.setX(newX)
        self.cue_stick.append_stroke_data()

        return True if collision else False


    def zoom_camera(self):
        with self.mouse:
            s = -self.mouse.get_dy()*0.3

        self.cam.node.setPos(autils.multiply_cw(self.cam.node.getPos(), 1-s))


    def move_camera(self):
        with self.mouse:
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

        with self.mouse:
            alpha_x = self.cam.focus.getH() - fx * self.mouse.get_dx()
            alpha_y = max(min(0, self.cam.focus.getR() + fy * self.mouse.get_dy()), -90)

        self.cam.focus.setH(alpha_x) # Move view laterally
        self.cam.focus.setR(alpha_y) # Move view vertically

        if cue_stick_too:
            self.fix_cue_stick_to_camera()


    def monitor(self, task):
        #print(f"Mode: {self.mode}")
        #print(f"Tasks: {list(self.tasks.keys())}")
        #print(f"Memory: {utils.get_total_memory_usage()}")
        #print(f"Actions: {[k for k in self.keymap if self.keymap[k]]}")
        #print(f"Keymap: {self.keymap}")
        #print(f"Frame: {self.frame}")
        #print()
        self.frame += 1

        return task.cont



