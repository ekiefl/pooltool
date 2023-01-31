#! /usr/bin/env python

import numpy as np
from direct.interval.IntervalGlobal import Parallel
from panda3d.core import TransparencyAttrib

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
import pooltool.constants as c
from pooltool.ani.action import Action
from pooltool.ani.camera import cam
from pooltool.ani.globals import Global
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.utils import panda_path


class BallInHandMode(BaseMode):
    name = Mode.ball_in_hand
    keymap = {
        Action.quit: False,
        Action.ball_in_hand: True,
        "next": False,
    }

    def __init__(self):
        super().__init__()

        self.trans_ball = None
        self.grab_ball_node = None
        self.grab_ball_shadow_node = None
        self.picking = None

    def enter(self):
        self.grab_selection_highlight_sequence = Parallel()

        mouse.mode(MouseMode.RELATIVE)

        self.grabbed_ball = None

        self.register_keymap_event("escape", Action.quit, True)
        self.register_keymap_event("g", Action.ball_in_hand, True)
        self.register_keymap_event("g-up", Action.ball_in_hand, False)
        self.register_keymap_event("mouse1-up", "next", True)

        num_options = len(Global.game.active_player.ball_in_hand)
        if num_options == 0:
            # FIXME add message
            self.picking = "ball"
        elif num_options == 1:
            self.grabbed_ball = Global.shots.active.balls[
                Global.game.active_player.ball_in_hand[0]
            ]
            self.grab_ball_node = self.grabbed_ball.get_node("pos")
            self.grab_ball_shadow_node = self.grabbed_ball.get_node("shadow")
            self.picking = "placement"
        else:
            self.picking = "ball"

        tasks.add(self.ball_in_hand_task, "ball_in_hand_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self, success=False):
        tasks.remove("ball_in_hand_task")
        tasks.remove("shared_task")

        BallInHandMode.remove_transparent_ball(self)

        if self.picking == "ball":
            BallInHandMode.remove_grab_selection_highlight(self)

        if self.picking == "placement" and not success:
            self.grabbed_ball.set_render_state_as_object_state()

        self.grab_selection_highlight_sequence.pause()

    def ball_in_hand_task(self, task):
        if not self.keymap[Action.ball_in_hand]:
            Global.mode_mgr.change_mode(
                Global.mode_mgr.last_mode,
                enter_kwargs=dict(load_prev_cam=False),
            )
            return task.done

        cam.move_fixation_via_mouse()

        if self.picking == "ball":
            closest = BallInHandMode.find_closest_ball(self)
            if closest != self.grabbed_ball:
                BallInHandMode.remove_grab_selection_highlight(self)
                self.grabbed_ball = closest
                self.grab_ball_node = self.grabbed_ball.get_node("pos")
                self.grab_ball_shadow_node = self.grabbed_ball.get_node("shadow")
                BallInHandMode.add_grab_selection_highlight(self)

            if self.keymap["next"]:
                self.keymap["next"] = False
                if self.grabbed_ball:
                    self.picking = "placement"
                    cam.move_fixation(self.grab_ball_node.getPos())
                    BallInHandMode.remove_grab_selection_highlight(self)
                    BallInHandMode.add_transparent_ball(self)

        elif self.picking == "placement":
            self.move_grabbed_ball()

            if self.keymap["next"]:
                self.keymap["next"] = False
                if self.try_placement():
                    Global.mode_mgr.change_mode(Global.mode_mgr.last_mode)
                    return task.done
                else:
                    # FIXME add error sound and message
                    pass

        return task.cont

    def try_placement(self):
        """Checks if grabbed ball overlaps with others

        If no, places and returns True. If yes, returns False
        """
        r, pos = self.grabbed_ball.R, np.array(self.grab_ball_node.getPos())

        for ball in Global.shots.active.balls.values():
            if ball == self.grabbed_ball:
                continue
            if np.linalg.norm(ball.rvw[0] - pos) <= (r + ball.R):
                return False

        self.grabbed_ball.set_object_state_as_render_state()
        return True

    def move_grabbed_ball(self):
        x, y = cam.fixation.getX(), cam.fixation.getY()

        self.grab_ball_node.setX(x)
        self.grab_ball_node.setY(y)
        self.grab_ball_shadow_node.setX(x)
        self.grab_ball_shadow_node.setY(y)

    def remove_grab_selection_highlight(self):
        if self.grabbed_ball is not None:
            node = self.grabbed_ball.get_node("pos")
            node.setScale(node.getScale() / ani.ball_highlight["ball_factor"])
            self.grab_ball_shadow_node.setAlphaScale(1)
            self.grab_ball_shadow_node.setScale(1)
            self.grabbed_ball.set_render_state_as_object_state()
            tasks.remove("grab_selection_highlight_animation")

    def add_grab_selection_highlight(self):
        if self.grabbed_ball is not None:
            tasks.add(
                self.grab_selection_highlight_animation,
                "grab_selection_highlight_animation",
            )
            node = self.grabbed_ball.get_node("pos")
            node.setScale(node.getScale() * ani.ball_highlight["ball_factor"])

    def grab_selection_highlight_animation(self, task):
        phase = task.time * ani.ball_highlight["ball_frequency"]

        new_height = ani.ball_highlight["ball_offset"] + ani.ball_highlight[
            "ball_amplitude"
        ] * np.sin(phase)
        self.grab_ball_node.setZ(new_height)

        new_alpha = ani.ball_highlight["shadow_alpha_offset"] + ani.ball_highlight[
            "shadow_alpha_amplitude"
        ] * np.sin(-phase)
        new_scale = ani.ball_highlight["shadow_scale_offset"] + ani.ball_highlight[
            "shadow_scale_amplitude"
        ] * np.sin(phase)
        self.grab_ball_shadow_node.setAlphaScale(new_alpha)
        self.grab_ball_shadow_node.setScale(new_scale)

        return task.cont

    def add_transparent_ball(self):
        self.trans_ball = Global.loader.loadModel(
            panda_path(ani.model_dir / "balls" / self.grabbed_ball.rel_model_path)
        )
        self.trans_ball.reparentTo(Global.render.find("scene").find("cloth"))
        self.trans_ball.setTransparency(TransparencyAttrib.MAlpha)
        self.trans_ball.setAlphaScale(0.4)
        self.trans_ball.setPos(self.grabbed_ball.get_node("pos").getPos())
        self.trans_ball.setHpr(self.grabbed_ball.get_node("sphere").getHpr())

    def remove_transparent_ball(self):
        if self.trans_ball is not None:
            self.trans_ball.removeNode()
        self.trans_ball = None

    def find_closest_ball(self):
        cam_pos = cam.fixation.getPos()
        d_min = np.inf
        closest = None
        for ball in Global.shots.active.balls.values():
            if ball.id not in Global.game.active_player.ball_in_hand:
                continue
            if ball.s == c.pocketed:
                continue
            d = np.linalg.norm(ball.rvw[0] - cam_pos)
            if d < d_min:
                d_min, closest = d, ball

        return closest
