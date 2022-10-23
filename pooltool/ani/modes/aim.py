#! /usr/bin/env python

import numpy as np

import pooltool.ani as ani
import pooltool.ani.utils as autils
from pooltool.ani.action import Action
from pooltool.ani.hud import hud
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.objects.cue import CueAvoid


class AimMode(BaseMode, CueAvoid):
    name = Mode.aim
    keymap = {
        Action.fine_control: False,
        Action.adjust_head: False,
        Action.quit: False,
        Action.stroke: False,
        Action.view: False,
        Action.zoom: False,
        Action.exec_shot: False,
        Action.power: False,
        Action.elevation: False,
        Action.english: False,
        Action.cam_save: False,
        Action.cam_load: False,
        Action.show_help: False,
        Action.pick_ball: False,
        Action.call_shot: False,
        Action.ball_in_hand: False,
        Action.prev_shot: False,
        Action.introspect: False,
    }

    def __init__(self):
        # In this state, the cue sticks to the self.min_theta
        self.magnet_theta = True
        # if cue angle is within this many degrees from self.min_theta, it sticks to
        # self.min_theta
        self.magnet_threshold = 0.2

    def enter(self, load_prev_cam=False):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        if not self.shots.active.cue.has_focus:
            self.shots.active.cue.init_focus(self.shots.active.cue.cueing_ball)
        else:
            self.shots.active.cue.update_focus()

        self.shots.active.cue.show_nodes(ignore=("cue_cseg",))
        self.shots.active.cue.get_node("cue_stick").setX(0)
        self.player_cam.update_focus(
            self.shots.active.cue.cueing_ball.get_node("pos").getPos()
        )
        if load_prev_cam:
            self.player_cam.load_state(Mode.aim)

        self.task_action("escape", Action.quit, True)
        self.task_action("f", Action.fine_control, True)
        self.task_action("f-up", Action.fine_control, False)
        self.task_action("t", Action.adjust_head, True)
        self.task_action("t-up", Action.adjust_head, False)
        self.task_action("mouse1", Action.zoom, True)
        self.task_action("mouse1-up", Action.zoom, False)
        self.task_action("s", Action.stroke, True)
        self.task_action("v", Action.view, True)
        self.task_action("1", Action.cam_save, True)
        self.task_action("2", Action.cam_load, True)
        self.task_action("h", Action.show_help, True)
        self.task_action("q", Action.pick_ball, True)
        self.task_action("c", Action.call_shot, True)
        self.task_action("g", Action.ball_in_hand, True)
        self.task_action("b", Action.elevation, True)
        self.task_action("b-up", Action.elevation, False)
        self.task_action("e", Action.english, True)
        self.task_action("e-up", Action.english, False)
        self.task_action("x", Action.power, True)
        self.task_action("x-up", Action.power, False)
        self.task_action("space", Action.exec_shot, True)
        self.task_action("space-up", Action.exec_shot, False)
        self.task_action("p-up", Action.prev_shot, True)
        self.task_action("i", Action.introspect, True)
        self.task_action("i-up", Action.introspect, False)

        CueAvoid.__init__(self)

        if ani.settings["gameplay"]["cue_collision"]:
            self.add_task(self.collision_task, "collision_task")
        self.add_task(self.aim_task, "aim_task")

    def exit(self):
        self.remove_task("aim_task")
        if ani.settings["gameplay"]["cue_collision"]:
            self.remove_task("collision_task")

        self.player_cam.store_state(Mode.aim, overwrite=True)

    def aim_task(self, task):
        if self.keymap[Action.view]:
            self.change_mode(Mode.view, enter_kwargs=dict(move_active=True))
            return task.done
        elif self.keymap[Action.stroke]:
            self.change_mode(Mode.stroke)
        elif self.keymap[Action.pick_ball]:
            self.change_mode(Mode.pick_ball)
        elif self.keymap[Action.call_shot]:
            self.change_mode(Mode.call_shot)
        elif self.keymap[Action.ball_in_hand]:
            self.change_mode(Mode.ball_in_hand)
        elif self.keymap[Action.zoom]:
            self.zoom_camera_aim()
        elif self.keymap[Action.adjust_head]:
            self.adjust_head_aim()
        elif self.keymap[Action.elevation]:
            self.aim_elevate_cue()
        elif self.keymap[Action.english]:
            self.apply_english()
        elif self.keymap[Action.power]:
            self.aim_apply_power()
        elif self.keymap[Action.exec_shot]:
            self.mode_stroked_from = Mode.aim
            self.shots.active.cue.set_object_state_as_render_state(skip_V0=True)
            self.shots.active.cue.strike()
            self.change_mode(Mode.calculate)
        elif self.keymap[Action.prev_shot]:
            self.keymap[Action.prev_shot] = False
            if len(self.shots) > 1:
                self.change_animation(
                    self.shots.active_index - 1
                )  # ShotMode.change_animation
                self.change_mode(Mode.shot, enter_kwargs=dict(init_animations=False))
                return task.done
        else:
            self.rotate_camera_aim()

        return task.cont

    def zoom_camera_aim(self):
        with self.mouse:
            s = -self.mouse.get_dy() * ani.zoom_sensitivity

        self.player_cam.node.setPos(
            autils.multiply_cw(self.player_cam.node.getPos(), 1 - s)
        )

    def adjust_head_aim(self):
        with self.mouse:
            alpha_y = max(
                min(
                    0,
                    self.player_cam.focus.getR()
                    + ani.rotate_sensitivity_y * self.mouse.get_dy(),
                ),
                -90,
            )

        self.player_cam.focus.setR(alpha_y)  # Move view vertically

    def rotate_camera_aim(self):
        if self.keymap[Action.fine_control]:
            fx, fy = ani.rotate_fine_sensitivity_x, ani.rotate_fine_sensitivity_y
        else:
            fx, fy = ani.rotate_sensitivity_x, ani.rotate_sensitivity_y

        with self.mouse:
            alpha_x = self.player_cam.focus.getH() - fx * self.mouse.get_dx()
            alpha_y = max(
                min(0, self.player_cam.focus.getR() + fy * self.mouse.get_dy()), -90
            )

        self.player_cam.focus.setH(alpha_x)  # Move view laterally
        self.player_cam.focus.setR(alpha_y)  # Move view vertically

        self.fix_cue_stick_to_camera()

        if (
            -self.shots.active.cue.get_node("cue_stick_focus").getR() < self.min_theta
        ) or self.magnet_theta:
            self.shots.active.cue.get_node("cue_stick_focus").setR(-self.min_theta)
            hud.hud_elements["jack"].set(self.min_theta)

        if -self.player_cam.focus.getR() < (
            -self.shots.active.cue.get_node("cue_stick_focus").getR()
            + ani.min_player_cam
        ):
            self.player_cam.focus.setR(
                -(
                    -self.shots.active.cue.get_node("cue_stick_focus").getR()
                    + ani.min_player_cam
                )
            )

    def fix_cue_stick_to_camera(self):
        self.shots.active.cue.get_node("cue_stick_focus").setH(
            self.player_cam.focus.getH()
        )

    def aim_apply_power(self):
        with self.mouse:
            dy = self.mouse.get_dy()

        min_V0, max_V0 = (
            hud.hud_elements["power"].min_strike,
            hud.hud_elements["power"].max_strike,
        )

        V0 = self.shots.active.cue.V0 + dy * ani.power_sensitivity
        if V0 < min_V0:
            V0 = min_V0
        if V0 > max_V0:
            V0 = max_V0

        self.shots.active.cue.set_state(V0=V0)
        hud.hud_elements["power"].set(V0)

    def aim_elevate_cue(self):
        cue = self.shots.active.cue.get_node("cue_stick_focus")

        with self.mouse:
            delta_elevation = self.mouse.get_dy() * ani.elevate_sensitivity

        old_elevation = -cue.getR()
        new_elevation = max(0, min(ani.max_elevate, old_elevation + delta_elevation))

        if self.min_theta >= new_elevation - self.magnet_threshold:
            # user set theta to minimum value, resume cushion tracking
            self.magnet_theta = True
            new_elevation = self.min_theta
        else:
            # theta has been modified by the user, so no longer tracks the cushion
            self.magnet_theta = False

        cue.setR(-new_elevation)

        if -self.player_cam.focus.getR() < (new_elevation + ani.min_player_cam):
            self.player_cam.focus.setR(-(new_elevation + ani.min_player_cam))

        self.shots.active.cue.set_state(theta=new_elevation)
        hud.hud_elements["jack"].set(new_elevation)

    def apply_english(self):
        with self.mouse:
            dx, dy = self.mouse.get_dx(), self.mouse.get_dy()

        cue = self.shots.active.cue.get_node("cue_stick")
        cue_focus = self.shots.active.cue.get_node("cue_stick_focus")
        R = self.shots.active.cue.follow.R

        delta_y, delta_z = dx * ani.english_sensitivity, dy * ani.english_sensitivity

        # y corresponds to side spin, z to top/bottom spin
        new_y = cue.getY() + delta_y
        new_z = cue.getZ() + delta_z

        norm = np.sqrt(new_y**2 + new_z**2)
        if norm > ani.max_english * R:
            new_y *= ani.max_english * R / norm
            new_z *= ani.max_english * R / norm

        cue.setY(new_y)
        cue.setZ(new_z)

        # if application of english increases min_theta beyond current elevation,
        # increase elevation
        if (
            self.magnet_theta
            or self.min_theta >= -cue_focus.getR() - self.magnet_threshold
        ):
            cue_focus.setR(-self.min_theta)

        if -self.player_cam.focus.getR() < (
            -self.shots.active.cue.get_node("cue_stick_focus").getR()
            + ani.min_player_cam
        ):
            self.player_cam.focus.setR(
                -(
                    -self.shots.active.cue.get_node("cue_stick_focus").getR()
                    + ani.min_player_cam
                )
            )

        a, b, theta = (
            -new_y / R,
            new_z / R,
            -self.shots.active.cue.get_node("cue_stick_focus").getR(),
        )
        self.shots.active.cue.set_state(a=a, b=b, theta=theta)
        hud.hud_elements["english"].set(a, b)
        hud.hud_elements["jack"].set(theta)
