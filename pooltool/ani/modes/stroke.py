#! /usr/bin/env python

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.camera import cam
from pooltool.ani.globals import Global
from pooltool.ani.menu import TextOverlay
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.system.datatypes import multisystem
from pooltool.system.render import visual


class StrokeMode(BaseMode):
    name = Mode.stroke
    keymap = {
        Action.fine_control: False,
        Action.stroke: True,
    }

    def __init__(self):
        super().__init__()
        self.call_shot_message = None

    def enter(self):
        mouse.mode(MouseMode.RELATIVE)
        Global.mode_mgr.mode_stroked_from = Global.mode_mgr.last_mode

        visual.cue.track_stroke()
        visual.cue.show_nodes(ignore=("cue_cseg",))

        self.register_keymap_event("f", Action.fine_control, True)
        self.register_keymap_event("f-up", Action.fine_control, False)
        self.register_keymap_event("s", Action.stroke, True)
        self.register_keymap_event("s-up", Action.stroke, False)

        tasks.add(self.stroke_task, "stroke_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self):
        tasks.remove("stroke_task")
        tasks.remove("shared_task")

        # Clean up shot call message if it exists
        if self.call_shot_message is not None:
            self.call_shot_message.hide()
            self.call_shot_message = None

        cam.store_state(Mode.stroke, overwrite=True)

    def stroke_task(self, task):
        if self.keymap[Action.stroke]:
            if not Global.game.shot_constraints.can_shoot():
                # Shot constraints not satisfied - show message
                if self.call_shot_message is None:
                    # Create message that appears when shot calling is required
                    self.call_shot_message = TextOverlay(
                        title='Shot must be called. Hold "c" to call your shot.',
                        frame_color=(0, 0, 0, 0.3),
                        title_pos=(0, 0, 0.6),
                        text_fg=(1, 1, 1, 0.8),
                        text_scale=0.05,
                    )
                    self.call_shot_message.show()
                return task.cont
            elif self.call_shot_message is not None:
                # Hide message if constraints are now satisfied
                self.call_shot_message.hide()
                self.call_shot_message = None

            if self.stroke_cue_stick():
                # The cue stick has contacted the cue ball
                visual.cue.set_object_state_as_render_state()
                multisystem.active.strike()
                Global.mode_mgr.change_mode(Mode.calculate)
                return
        else:
            # Clean up when exiting stroke mode
            if self.call_shot_message is not None:
                self.call_shot_message.hide()
                self.call_shot_message = None

            visual.cue.get_node("cue_stick").setX(0)
            visual.cue.hide_nodes(ignore=("cue_cseg",))
            Global.mode_mgr.change_mode(Global.mode_mgr.last_mode)
            return

        return task.cont

    def stroke_cue_stick(self):
        max_speed_mouse = ani.max_stroke_speed / ani.stroke_sensitivity  # [px/s]
        max_backstroke = (
            multisystem.active.cue.specs.length * ani.backstroke_fraction
        )  # [m]

        with mouse:
            dt = mouse.get_dt()
            dx = mouse.get_dy()

        speed_mouse = dx / dt
        if speed_mouse > max_speed_mouse:
            dx *= max_speed_mouse / speed_mouse

        cue_stick_node = visual.cue.get_node("cue_stick")
        newX = min(max_backstroke, cue_stick_node.getX() - dx * ani.stroke_sensitivity)

        if newX < 0:
            newX = 0
            collision = True if visual.cue.is_shot() else False
        else:
            collision = False

        cue_stick_node.setX(newX)
        visual.cue.append_stroke_data()

        return True if collision else False
