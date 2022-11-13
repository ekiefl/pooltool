#! /usr/bin/env python

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.camera import player_cam
from pooltool.ani.globals import Global
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import mouse


class StrokeMode(BaseMode):
    name = Mode.stroke
    keymap = {
        Action.fine_control: False,
        Action.stroke: True,
    }

    def enter(self):
        self.mode_stroked_from = self.last_mode
        mouse.hide()
        mouse.relative()
        mouse.track()

        Global.shots.active.cue.track_stroke()
        Global.shots.active.cue.show_nodes(ignore=("cue_cseg",))

        self.register_keymap_event("f", Action.fine_control, True)
        self.register_keymap_event("f-up", Action.fine_control, False)
        self.register_keymap_event("s", Action.stroke, True)
        self.register_keymap_event("s-up", Action.stroke, False)

        tasks.add(self.stroke_task, "stroke_task")

    def exit(self):
        tasks.remove("stroke_task")
        player_cam.store_state(Mode.stroke, overwrite=True)

    def stroke_task(self, task):
        if self.keymap[Action.stroke]:
            if Global.game.is_call_pocket and Global.game.pocket_call is None:
                return task.cont
            if Global.game.is_call_ball and Global.game.ball_call is None:
                return task.cont

            if self.stroke_cue_stick():
                # The cue stick has contacted the cue ball
                Global.shots.active.cue.set_object_state_as_render_state()
                Global.shots.active.cue.strike()
                Global.shots.active.user_stroke = True
                self.change_mode(Mode.calculate)
                return
        else:
            Global.shots.active.cue.get_node("cue_stick").setX(0)
            Global.shots.active.cue.hide_nodes(ignore=("cue_cseg",))
            self.change_mode(self.last_mode)
            return

        return task.cont

    def stroke_cue_stick(self):
        max_speed_mouse = ani.max_stroke_speed / ani.stroke_sensitivity  # [px/s]
        max_backstroke = Global.shots.active.cue.length * ani.backstroke_fraction  # [m]

        with mouse:
            dt = mouse.get_dt()
            dx = mouse.get_dy()

        speed_mouse = dx / dt
        if speed_mouse > max_speed_mouse:
            dx *= max_speed_mouse / speed_mouse

        cue_stick_node = Global.shots.active.cue.get_node("cue_stick")
        newX = min(max_backstroke, cue_stick_node.getX() - dx * ani.stroke_sensitivity)

        if newX < 0:
            newX = 0
            collision = True if Global.shots.active.cue.is_shot() else False
        else:
            collision = False

        cue_stick_node.setX(newX)
        Global.shots.active.cue.append_stroke_data()

        return True if collision else False
