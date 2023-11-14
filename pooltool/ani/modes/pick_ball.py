#! /usr/bin/env python
"""A mode to for picking which ball to cue"""

import numpy as np

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
import pooltool.constants as c
import pooltool.ptmath as ptmath
from pooltool.ani.action import Action
from pooltool.ani.camera import cam
from pooltool.ani.globals import Global
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.system.datatypes import multisystem
from pooltool.system.render import visual


class PickBallMode(BaseMode):
    name = Mode.pick_ball
    keymap = {
        Action.quit: False,
        Action.pick_ball: True,
        Action.done: False,
    }

    def enter(self):
        mouse.mode(MouseMode.RELATIVE)

        self.closest_ball = None

        self.register_keymap_event("escape", Action.quit, True)
        self.register_keymap_event("q", Action.pick_ball, True)
        self.register_keymap_event("q-up", Action.pick_ball, False)
        self.register_keymap_event("mouse1-up", "done", True)

        tasks.add(self.pick_ball_task, "pick_ball_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self):
        self.remove_ball_highlight()
        tasks.remove("shared_task")
        tasks.remove("pick_ball_task")

    def pick_ball_task(self, task):
        raise NotImplementedError("Woops, this is in a broken state, don't press that")

        if not self.keymap[Action.pick_ball]:
            Global.mode_mgr.change_mode(Mode.aim)
            return task.done

        cam.move_fixation_via_mouse()

        closest = self.find_closest_ball()
        if closest != self.closest_ball:
            self.remove_ball_highlight()
            self.closest_ball = closest
            self.ball_highlight = self.closest_ball.get_node("pos")
            self.add_ball_highlight()

        if self.keymap["done"]:
            self.remove_ball_highlight()
            ball_id = self.closest_ball._ball.id
            if ball_id is not None:
                multisystem.active.cue.cue_ball_id = ball_id
                visual.cue.init_focus(visual.balls[ball_id])
                Global.game.log.add_msg(
                    f"Now cueing the {multisystem.active.cue.cue_ball_id} ball",
                    sentiment="neutral",
                )
            Global.mode_mgr.change_mode(Mode.aim)
            return task.done

        return task.cont

    def remove_ball_highlight(self):
        if self.closest_ball is not None and tasks.has("pick_ball_highlight_animation"):
            node = self.closest_ball.get_node("pos")
            node.setScale(node.getScale() / ani.ball_highlight["ball_factor"])
            self.closest_ball.get_node("shadow").setAlphaScale(1)
            self.closest_ball.get_node("shadow").setScale(1)
            self.closest_ball.set_render_state_as_object_state()
            tasks.remove("pick_ball_highlight_animation")

    def add_ball_highlight(self):
        if self.closest_ball is not None:
            tasks.add(
                self.pick_ball_highlight_animation, "pick_ball_highlight_animation"
            )
            node = self.closest_ball.get_node("pos")
            node.setScale(node.getScale() * ani.ball_highlight["ball_factor"])

    def pick_ball_highlight_animation(self, task):
        phase = task.time * ani.ball_highlight["ball_frequency"]

        new_height = ani.ball_highlight["ball_offset"] + ani.ball_highlight[
            "ball_amplitude"
        ] * np.sin(phase)
        self.ball_highlight.setZ(new_height)

        new_alpha = ani.ball_highlight["shadow_alpha_offset"] + ani.ball_highlight[
            "shadow_alpha_amplitude"
        ] * np.sin(-phase)
        new_scale = ani.ball_highlight["shadow_scale_offset"] + ani.ball_highlight[
            "shadow_scale_amplitude"
        ] * np.sin(phase)
        self.closest_ball.get_node("shadow").setAlphaScale(new_alpha)
        self.closest_ball.get_node("shadow").setScale(new_scale)

        return task.cont

    def find_closest_ball(self):
        cam_fixation = cam.fixation.getPos()
        d_min = np.inf
        closest = None
        for ball_id, ball in visual.balls.items():
            if ball_id not in Global.game.active_player.can_cue:
                continue
            if ball._ball.state.s == c.pocketed:
                continue
            d = ptmath.norm3d(ball._ball.state.rvw[0] - cam_fixation)
            if d < d_min:
                d_min, closest = d, ball

        return closest
