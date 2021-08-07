#! /usr/bin/env python

import pooltool.ani as ani

from pooltool.ani.modes import Mode, action


class StrokeMode(Mode):
    keymap = {
        action.fine_control: False,
        action.stroke: True,
    }

    def enter(self):
        self.mode_stroked_from = self.last_mode
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.cue.track_stroke()
        self.cue.show_nodes()

        self.task_action('f', action.fine_control, True)
        self.task_action('f-up', action.fine_control, False)
        self.task_action('s', action.stroke, True)
        self.task_action('s-up', action.stroke, False)

        self.add_task(self.stroke_task, 'stroke_task')


    def exit(self):
        self.remove_task('stroke_task')
        self.player_cam.store_state('stroke', overwrite=True)


    def stroke_task(self, task):
        if self.keymap[action.stroke]:
            if self.game.is_call_pocket and self.game.pocket_call is None:
                return task.cont
            if self.game.is_call_ball and self.game.ball_call is None:
                return task.cont

            if self.stroke_cue_stick():
                # The cue stick has contacted the cue ball
                self.change_mode('calculate')
                return
        else:
            self.change_mode('aim')
            return

        return task.cont


    def stroke_cue_stick(self):
        max_speed_mouse = ani.max_stroke_speed/ani.stroke_sensitivity # [px/s]
        max_backstroke = self.cue.length*ani.backstroke_fraction # [m]

        with self.mouse:
            dt = self.mouse.get_dt()
            dx = self.mouse.get_dy()

        speed_mouse = dx/dt
        if speed_mouse > max_speed_mouse:
            dx *= max_speed_mouse/speed_mouse

        cue_stick_node = self.cue.get_node('cue_stick')
        newX = min(max_backstroke, cue_stick_node.getX() - dx*ani.stroke_sensitivity)

        if newX < 0:
            newX = 0
            collision = True if self.cue.is_shot() else False
        else:
            collision = False

        cue_stick_node.setX(newX)
        self.cue.append_stroke_data()

        return True if collision else False


