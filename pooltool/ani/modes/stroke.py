#! /usr/bin/env python

from pooltool.ani.modes import Mode, action


class StrokeMode(Mode):
    keymap = {
        action.fine_control: False,
        action.stroke: True,
    }

    def enter(self):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        self.cue_stick.track_stroke()
        self.cue_stick.show_nodes()

        self.task_action('f', action.fine_control, True)
        self.task_action('f-up', action.fine_control, False)
        self.task_action('s', action.stroke, True)
        self.task_action('s-up', action.stroke, False)

        self.add_task(self.stroke_task, 'stroke_task')


    def exit(self):
        self.remove_task('stroke_task')
        self.cam.store_state('stroke', overwrite=True)
        self.cam.load_state('aim')


    def stroke_task(self, task):
        if self.keymap[action.stroke]:
            if self.stroke_cue_stick():
                self.change_mode('shot')
                return
        else:
            self.change_mode('aim')
            return

        return task.cont


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


