#! /usr/bin/env python

import numpy as np
from direct.interval.IntervalGlobal import LerpFunc, Parallel
from panda3d.core import TransparencyAttrib

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
import pooltool.constants as c
from pooltool.ani.action import Action
from pooltool.ani.camera import camera
from pooltool.ani.globals import Global
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
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

        mouse.mode(MouseMode.RELATIVE)

        camera.rotate(theta=camera.theta + self.head_raise)

        self.closest_pocket = None
        self.closest_ball = None

        self.register_keymap_event("escape", Action.quit, True)
        self.register_keymap_event("c", Action.call_shot, True)
        self.register_keymap_event("c-up", Action.call_shot, False)
        self.register_keymap_event("mouse1-up", "next", True)

        self.picking = "ball"

        tasks.add(self.call_shot_task, "call_shot_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self):
        tasks.remove("call_shot_task")
        tasks.remove("shared_task")

        if self.picking in ("ball", "pocket"):
            CallShotMode.remove_ball_highlight(self)
        CallShotMode.remove_transparent_ball(self)
        self.ball_highlight_sequence.pause()
        camera.rotate(theta=camera.theta - self.head_raise)

    def call_shot_task(self, task):
        if not self.keymap[Action.call_shot]:
            Global.mode_mgr.change_mode(Global.mode_mgr.last_mode)
            return task.done

        camera.move_fixation_via_mouse()

        if self.picking == "ball":
            closest = CallShotMode.find_closest_ball(self)
            if closest != self.closest_ball:
                CallShotMode.remove_ball_highlight(self)
                self.closest_ball = closest
                self.ball_highlight = self.closest_ball.get_node("pos")
                CallShotMode.add_ball_highlight(self)

            if self.keymap["next"]:
                self.keymap["next"] = False
                Global.game.ball_call = self.closest_ball
                if self.closest_ball is not None:
                    Global.game.log.add_msg(
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
                Global.game.pocket_call = self.closest_pocket
                if self.closest_pocket is not None:
                    Global.game.log.add_msg(
                        f"Calling the {self.closest_pocket.id} pocket",
                        sentiment="neutral",
                    )
                Global.mode_mgr.change_mode(Global.mode_mgr.last_mode)
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
        fixation_pos = camera.fixation.getPos()
        d_min = np.inf
        closest = None
        for pocket in Global.shots.active.table.pockets.values():
            d = np.linalg.norm(pocket.center - fixation_pos)
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
            tasks.remove("call_shot_ball_highlight_animation")

    def add_ball_highlight(self):
        if self.closest_ball is not None:
            CallShotMode.add_transparent_ball(self)
            self.trans_ball.hide()
            tasks.add(
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
        fixation_pos = camera.fixation.getPos()
        d_min = np.inf
        closest = None
        for ball in Global.shots.active.balls.values():
            if ball.id not in Global.game.active_player.target_balls:
                continue
            if ball.s == c.pocketed:
                continue
            d = np.linalg.norm(ball.rvw[0] - fixation_pos)
            if d < d_min:
                d_min, closest = d, ball

        return closest
