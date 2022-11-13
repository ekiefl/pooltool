#! /usr/bin/env python

import numpy as np
from direct.interval.IntervalGlobal import LerpFunc, Parallel
from panda3d.core import TransparencyAttrib

import pooltool.ani as ani
import pooltool.constants as c
from pooltool.ani.action import Action
from pooltool.ani.camera import player_cam
from pooltool.ani.globals import Global
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import mouse
from pooltool.utils import panda_path


class CallShotMode(BaseMode):
    name = Mode.call_shot
    keymap = {
        Action.quit: False,
        Action.call_shot: True,
        "next": False,
    }

    def __init__(self):
        super().__init__()

        self.head_raise = 14

        self.trans_ball = None
        self.ball_highlight = None
        self.picking = None

    def enter(self):
        self.ball_highlight_sequence = Parallel()

        mouse.hide()
        mouse.relative()
        mouse.track()

        player_cam.focus.setR(player_cam.focus.getR() - self.head_raise)

        self.closest_pocket = None
        self.closest_ball = None

        self.task_action("escape", Action.quit, True)
        self.task_action("c", Action.call_shot, True)
        self.task_action("c-up", Action.call_shot, False)
        self.task_action("mouse1-up", "next", True)

        self.picking = "ball"

        self.add_task(self.call_shot_task, "call_shot_task")

    def exit(self):
        self.remove_task("call_shot_task")
        if self.picking in ("ball", "pocket"):
            CallShotMode.remove_ball_highlight(self)
        CallShotMode.remove_transparent_ball(self)
        self.ball_highlight_sequence.pause()
        player_cam.focus.setR(player_cam.focus.getR() + self.head_raise)

    def call_shot_task(self, task):
        if not self.keymap[Action.call_shot]:
            self.change_mode(self.last_mode)
            return task.done

        self.move_camera_call_shot()

        if self.picking == "ball":
            closest = CallShotMode.find_closest_ball(self)
            if closest != self.closest_ball:
                CallShotMode.remove_ball_highlight(self)
                self.closest_ball = closest
                self.ball_highlight = self.closest_ball.get_node("pos")
                CallShotMode.add_ball_highlight(self)

            if self.keymap["next"]:
                self.keymap["next"] = False
                self.game.ball_call = self.closest_ball
                if self.closest_ball is not None:
                    self.game.log.add_msg(
                        f"Calling the {self.closest_ball.id} ball", sentiment="neutral"
                    )
                self.picking = "pocket"
                self.trans_ball.show()

        elif self.picking == "pocket":
            closest = self.find_closest_pocket()
            if closest != self.closest_pocket:
                self.closest_pocket = closest
                self.move_ball_highlight()

            if self.keymap["next"]:
                self.keymap["next"] = False
                self.game.pocket_call = self.closest_pocket
                if self.closest_pocket is not None:
                    self.game.log.add_msg(
                        f"Calling the {self.closest_pocket.id} pocket",
                        sentiment="neutral",
                    )
                self.change_mode(self.last_mode)
                return task.done

        return task.cont

    def move_ball_highlight(self):
        if self.closest_pocket is not None:
            self.ball_highlight_sequence.pause()
            self.ball_highlight_sequence = Parallel(
                LerpFunc(
                    self.ball_highlight.setX,
                    fromData=self.ball_highlight.getX(),
                    toData=self.closest_pocket.center[0],
                    duration=0.07,
                    blendType="easeInOut",
                ),
                LerpFunc(
                    self.ball_highlight.setY,
                    fromData=self.ball_highlight.getY(),
                    toData=self.closest_pocket.center[1],
                    duration=0.07,
                    blendType="easeInOut",
                ),
                LerpFunc(
                    self.closest_ball.get_node("shadow").setX,
                    fromData=self.closest_ball.get_node("shadow").getX(),
                    toData=self.closest_pocket.center[0],
                    duration=0.07,
                    blendType="easeInOut",
                ),
                LerpFunc(
                    self.closest_ball.get_node("shadow").setY,
                    fromData=self.closest_ball.get_node("shadow").getY(),
                    toData=self.closest_pocket.center[1],
                    duration=0.07,
                    blendType="easeInOut",
                ),
            )
            self.ball_highlight_sequence.start()

    def find_closest_pocket(self):
        cam_pos = player_cam.focus.getPos()
        d_min = np.inf
        closest = None
        for pocket in self.shots.active.table.pockets.values():
            d = np.linalg.norm(pocket.center - cam_pos)
            if d < d_min:
                d_min, closest = d, pocket

        return closest

    def remove_ball_highlight(self):
        if self.closest_ball is not None:
            node = self.closest_ball.get_node("pos")
            node.setScale(node.getScale() / ani.ball_highlight["ball_factor"])
            self.closest_ball.get_node("shadow").setAlphaScale(1)
            self.closest_ball.get_node("shadow").setScale(1)
            self.closest_ball.set_render_state_as_object_state()
            self.remove_task("call_shot_ball_highlight_animation")

    def add_ball_highlight(self):
        if self.closest_ball is not None:
            CallShotMode.add_transparent_ball(self)
            self.trans_ball.hide()
            self.add_task(
                self.call_shot_ball_highlight_animation,
                "call_shot_ball_highlight_animation",
            )
            node = self.closest_ball.get_node("pos")
            node.setScale(node.getScale() * ani.ball_highlight["ball_factor"])

    def call_shot_ball_highlight_animation(self, task):
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

    def add_transparent_ball(self):
        self.trans_ball = Global.loader.loadModel(
            panda_path(ani.model_dir / "balls" / self.closest_ball.rel_model_path)
        )
        self.trans_ball.reparentTo(Global.render.find("scene").find("cloth"))
        self.trans_ball.setTransparency(TransparencyAttrib.MAlpha)
        self.trans_ball.setAlphaScale(0.4)
        self.trans_ball.setPos(self.closest_ball.get_node("pos").getPos())
        self.trans_ball.setHpr(self.closest_ball.get_node("sphere").getHpr())

    def remove_transparent_ball(self):
        if self.trans_ball is not None:
            self.trans_ball.removeNode()
        self.trans_ball = None

    def find_closest_ball(self):
        cam_pos = player_cam.focus.getPos()
        d_min = np.inf
        closest = None
        for ball in self.shots.active.balls.values():
            if ball.id not in self.game.active_player.target_balls:
                continue
            if ball.s == c.pocketed:
                continue
            d = np.linalg.norm(ball.rvw[0] - cam_pos)
            if d < d_min:
                d_min, closest = d, ball

        return closest

    def move_camera_call_shot(self):
        with mouse:
            dxp, dyp = mouse.get_dx(), mouse.get_dy()

        h = player_cam.focus.getH() * np.pi / 180 + np.pi / 2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        player_cam.focus.setX(player_cam.focus.getX() + dx * ani.move_sensitivity)
        player_cam.focus.setY(player_cam.focus.getY() + dy * ani.move_sensitivity)
