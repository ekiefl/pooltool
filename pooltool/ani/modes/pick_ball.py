#! /usr/bin/env python
"""A mode to for picking which ball to cue"""

import numpy as np

import pooltool.ani as ani
import pooltool.constants as c
from pooltool.ani.action import Action
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import mouse


class PickBallMode(BaseMode):
    name = Mode.pick_ball
    keymap = {
        Action.quit: False,
        Action.pick_ball: True,
        "done": False,
    }

    def enter(self):
        mouse.hide()
        mouse.relative()
        mouse.track()

        self.closest_ball = None

        self.task_action("escape", Action.quit, True)
        self.task_action("q", Action.pick_ball, True)
        self.task_action("q-up", Action.pick_ball, False)
        self.task_action("mouse1-up", "done", True)

        self.add_task(self.pick_ball_task, "pick_ball_task")

    def exit(self):
        PickBallMode.remove_ball_highlight(self)
        self.remove_task("pick_ball_task")

    def pick_ball_task(self, task):
        if not self.keymap[Action.pick_ball]:
            self.change_mode(Mode.aim)
            return task.done

        self.move_camera_pick_ball()

        closest = PickBallMode.find_closest_ball(self)
        if closest != self.closest_ball:
            PickBallMode.remove_ball_highlight(self)
            self.closest_ball = closest
            self.ball_highlight = self.closest_ball.get_node("pos")
            PickBallMode.add_ball_highlight(self)

        if self.keymap["done"]:
            PickBallMode.remove_ball_highlight(self)
            self.shots.active.cue.cueing_ball = self.closest_ball
            if self.shots.active.cue.cueing_ball is not None:
                self.shots.active.cue.init_focus(self.shots.active.cue.cueing_ball)
                self.game.log.add_msg(
                    f"Now cueing the {self.shots.active.cue.cueing_ball.id} ball",
                    sentiment="neutral",
                )
            self.change_mode(Mode.aim)
            return task.done

        return task.cont

    def remove_ball_highlight(self):
        if self.closest_ball is not None and self.has_task(
            "pick_ball_highlight_animation"
        ):
            node = self.closest_ball.get_node("pos")
            node.setScale(node.getScale() / ani.ball_highlight["ball_factor"])
            self.closest_ball.get_node("shadow").setAlphaScale(1)
            self.closest_ball.get_node("shadow").setScale(1)
            self.closest_ball.set_render_state_as_object_state()
            self.remove_task("pick_ball_highlight_animation")

    def add_ball_highlight(self):
        if self.closest_ball is not None:
            self.add_task(
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
        cam_pos = self.player_cam.focus.getPos()
        d_min = np.inf
        closest = None
        for ball in self.shots.active.balls.values():
            if ball.id not in self.game.active_player.can_cue:
                continue
            if ball.s == c.pocketed:
                continue
            d = np.linalg.norm(ball.rvw[0] - cam_pos)
            if d < d_min:
                d_min, closest = d, ball

        return closest

    def move_camera_pick_ball(self):
        with mouse:
            dxp, dyp = mouse.get_dx(), mouse.get_dy()

        h = self.player_cam.focus.getH() * np.pi / 180 + np.pi / 2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        self.player_cam.focus.setX(
            self.player_cam.focus.getX() + dx * ani.move_sensitivity
        )
        self.player_cam.focus.setY(
            self.player_cam.focus.getY() + dy * ani.move_sensitivity
        )
