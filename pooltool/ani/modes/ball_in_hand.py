#! /usr/bin/env python

import numpy as np
from direct.interval.IntervalGlobal import Parallel
from panda3d.core import TransparencyAttrib

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
import pooltool.constants as c
import pooltool.ptmath as ptmath
from pooltool.ani.action import Action
from pooltool.ani.camera import cam
from pooltool.ani.globals import Global
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.ruleset.datatypes import BallInHandOptions
from pooltool.system.render import visual
from pooltool.utils import panda_path


class BallInHandMode(BaseMode):
    name = Mode.ball_in_hand
    keymap = {
        Action.quit: False,
        Action.ball_in_hand: True,
        Action.next: False,
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

        if Global.game.shot_constraints.movable is None:
            self.picking = "ball"
        elif len(Global.game.shot_constraints.movable) == 0:
            # FIXME: Add message to indicate that no balls are movable
            pass
        elif len(Global.game.shot_constraints.movable) == 1:
            self.grabbed_ball = visual.balls[Global.game.shot_constraints.movable[0]]
            self.grab_ball_node = self.grabbed_ball.get_node("pos")
            self.grab_ball_shadow_node = self.grabbed_ball.get_node("shadow")
            self.picking = "placement"
        else:
            # If there are specific movable balls, set picking to "ball" to allow selection
            self.picking = "ball"

        tasks.add(self.ball_in_hand_task, "ball_in_hand_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self, success=False):
        tasks.remove("ball_in_hand_task")
        tasks.remove("shared_task")

        self.remove_transparent_ball()

        if self.picking == "ball":
            self.remove_grab_selection_highlight()

        if self.picking == "placement" and not success:
            if self.grabbed_ball is not None:
                self.grabbed_ball.set_render_state_as_object_state()

        self.grab_selection_highlight_sequence.pause()

    def ball_in_hand_task(self, task):
        if not self.keymap[Action.ball_in_hand]:
            Global.mode_mgr.change_mode(
                Global.mode_mgr.last_mode,
                enter_kwargs=dict(load_prev_cam=False),
            )
            return task.done

        if Global.game.shot_constraints.ball_in_hand == BallInHandOptions.NONE:
            return task.cont

        cam.move_fixation_via_mouse()

        if self.picking == "ball":
            closest = self.find_closest_ball()
            if closest != self.grabbed_ball:
                self.remove_grab_selection_highlight()
                self.grabbed_ball = closest
                self.grab_ball_node = self.grabbed_ball.get_node("pos")
                self.grab_ball_shadow_node = self.grabbed_ball.get_node("shadow")
                self.add_grab_selection_highlight()

            if self.keymap["next"]:
                self.keymap["next"] = False
                if self.grabbed_ball:
                    self.picking = "placement"
                    cam.move_fixation(self.grab_ball_node.getPos())
                    self.remove_grab_selection_highlight()
                    self.add_transparent_ball()

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
        r, pos = (
            self.grabbed_ball._ball.params.R,
            np.array(self.grab_ball_node.getPos()),
        )

        for ball in visual.balls.values():
            if ball == self.grabbed_ball:
                continue
            if ptmath.norm3d(ball._ball.state.rvw[0] - pos) <= (
                r + ball._ball.params.R
            ):
                return False

        self.grabbed_ball.set_object_state_as_render_state(patch=True)
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
            panda_path(self.grabbed_ball.model_path)
        )
        self.trans_ball.reparentTo(Global.render.find("scene").find("table"))
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
        movable = Global.game.shot_constraints.movable

        for ball_id, ball in visual.balls.items():
            # Skip pocketed balls
            if ball._ball.state.s == c.pocketed:
                continue

            # If there is a list of movable balls, skip balls not in that list
            if movable is not None and ball_id not in movable:
                continue

            # Calculate distance and update closest ball if necessary
            d = ptmath.norm3d(ball._ball.state.rvw[0] - cam_pos)
            if d < d_min:
                d_min, closest = d, ball

        return closest
