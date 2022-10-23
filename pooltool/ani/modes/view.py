#! /usr/bin/env python

import numpy as np

import pooltool.ani as ani
import pooltool.ani.action as action
import pooltool.ani.utils as autils
from pooltool.ani.modes.datatypes import Mode, ModeName


class ViewMode(Mode):
    name = ModeName.view
    keymap = {
        action.aim: False,
        action.call_shot: False,
        action.fine_control: False,
        action.move: False,
        action.stroke: False,
        action.quit: False,
        action.zoom: False,
        action.cam_save: False,
        action.cam_load: False,
        action.show_help: False,
        action.pick_ball: False,
        action.ball_in_hand: False,
        action.power: False,
        action.elevation: False,
        action.english: False,
        action.prev_shot: False,
        action.introspect: False,
        action.hide_cue: False,
        action.exec_shot: False,
    }

    def enter(self, move_active=False, load_prev_cam=False):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        if self.shots.active is not None:
            self.shots.active.cue.hide_nodes(ignore=("cue_cseg",))

        if load_prev_cam:
            self.player_cam.load_state(ModeName.view)

        self.scale_focus()

        if move_active:
            self.keymap[action.move] = True

        self.task_action("escape", action.quit, True)
        self.task_action("mouse1", action.zoom, True)
        self.task_action("mouse1-up", action.zoom, False)
        self.task_action("a", action.aim, True)
        self.task_action("v", action.move, True)
        self.task_action("s", action.stroke, True)
        self.task_action("v-up", action.move, False)
        self.task_action("1", action.cam_save, True)
        self.task_action("2", action.cam_load, True)
        self.task_action("h", action.show_help, True)
        self.task_action("q", action.pick_ball, True)
        self.task_action("g", action.ball_in_hand, True)
        self.task_action("c", action.call_shot, True)
        self.task_action("i", action.introspect, True)
        self.task_action("i-up", action.introspect, False)
        self.task_action("b", action.elevation, True)
        self.task_action("b-up", action.hide_cue, True)
        self.task_action("e", action.english, True)
        self.task_action("e-up", action.hide_cue, True)
        self.task_action("x", action.power, True)
        self.task_action("x-up", action.hide_cue, True)
        self.task_action("p-up", action.prev_shot, True)
        self.task_action("space", action.exec_shot, True)
        self.task_action("space-up", action.exec_shot, False)

        self.add_task(self.view_task, "view_task")
        if ani.settings["gameplay"]["cue_collision"]:
            self.add_task(self.collision_task, "collision_task")

    def exit(self):
        self.remove_task("view_task")
        if ani.settings["gameplay"]["cue_collision"]:
            self.remove_task("collision_task")
        self.player_cam.store_state(ModeName.view, overwrite=True)

    def view_task(self, task):
        if self.keymap[action.stroke]:
            self.change_mode(ModeName.stroke)
        elif self.keymap[action.pick_ball]:
            self.change_mode(ModeName.pick_ball)
        elif self.keymap[action.call_shot]:
            self.change_mode(ModeName.call_shot)
        elif self.keymap[action.ball_in_hand]:
            self.change_mode(ModeName.ball_in_hand)
        elif self.keymap[action.zoom]:
            self.zoom_camera_view()
        elif self.keymap[action.move]:
            self.move_camera_view()
        elif self.keymap[action.hide_cue]:
            self.keymap[action.hide_cue] = False
            self.keymap[action.english] = False
            self.keymap[action.elevation] = False
            self.keymap[action.power] = False
            if self.shots.active is not None:
                self.shots.active.cue.hide_nodes(ignore=("cue_cseg",))
        elif self.keymap[action.elevation]:
            self.view_elevate_cue()
        elif self.keymap[action.english]:
            self.view_apply_english()
        elif self.keymap[action.power]:
            self.view_apply_power()
        elif self.keymap[action.aim]:
            self.change_mode(ModeName.aim, enter_kwargs=dict(load_prev_cam=True))
        elif self.keymap[action.exec_shot]:
            self.mode_stroked_from = ModeName.view
            self.shots.active.cue.set_object_state_as_render_state(skip_V0=True)
            self.shots.active.cue.strike()
            self.change_mode(ModeName.calculate)
        elif self.keymap[action.prev_shot]:
            self.keymap[action.prev_shot] = False
            if len(self.shots) > 1:
                self.change_animation(
                    self.shots.active_index - 1
                )  # ShotMode.change_animation
                self.change_mode(
                    ModeName.shot, enter_kwargs=dict(init_animations=False)
                )
                return task.done
        else:
            self.rotate_camera_view()

        return task.cont

    def scale_focus(self):
        """Scale the camera's focus object

        The focus marker is a small dot to show where the camera is centered, and where
        it rotates about. This helps a lot in navigating the camera effectively. Here
        the marker is scaled so that it is always a constant size, regardless of how
        zoomed in or out the camera is.
        """
        # `dist` is the distance from the camera to the focus object and is equivalent
        # to: cam_pos, focus_pos = self.player_cam.node.getPos(render),
        # self.player_cam.focus_object.getPos(render) dist = (cam_pos -
        # focus_pos).length()
        dist = self.player_cam.node.getX()
        self.player_cam.focus_object.setScale(0.002 * dist)

    def zoom_camera_view(self):
        with self.mouse:
            s = -self.mouse.get_dy() * ani.zoom_sensitivity

        self.player_cam.node.setPos(
            autils.multiply_cw(self.player_cam.node.getPos(), 1 - s)
        )
        self.scale_focus()

    def move_camera_view(self):
        with self.mouse:
            dxp, dyp = self.mouse.get_dx(), self.mouse.get_dy()

        # NOTE This conversion _may_ depend on how I initialized self.player_cam.focus
        h = self.player_cam.focus.getH() * np.pi / 180 + np.pi / 2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        self.player_cam.focus.setX(
            self.player_cam.focus.getX() + dx * ani.move_sensitivity
        )
        self.player_cam.focus.setY(
            self.player_cam.focus.getY() + dy * ani.move_sensitivity
        )

    def rotate_camera_view(self):
        if self.keymap[action.fine_control]:
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

    def view_apply_power(self):
        self.shots.active.cue.show_nodes(ignore=("cue_cseg",))

        with self.mouse:
            dy = self.mouse.get_dy()

        min_V0, max_V0 = (
            self.hud_elements["power"].min_strike,
            self.hud_elements["power"].max_strike,
        )

        V0 = self.shots.active.cue.V0 + dy * ani.power_sensitivity
        if V0 < min_V0:
            V0 = min_V0
        if V0 > max_V0:
            V0 = max_V0

        self.shots.active.cue.set_state(V0=V0)
        self.hud_elements["power"].set(V0)

    def view_elevate_cue(self):
        self.shots.active.cue.show_nodes(ignore=("cue_cseg",))

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

        self.shots.active.cue.set_state(theta=new_elevation)
        self.hud_elements["jack"].set(new_elevation)

    def view_apply_english(self):
        self.shots.active.cue.show_nodes(ignore=("cue_cseg",))

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

        # if application of english increases min_theta beyond current elevation, increase elevation
        if (
            self.magnet_theta
            or self.min_theta >= -cue_focus.getR() - self.magnet_threshold
        ):
            cue_focus.setR(-self.min_theta)

        a, b, theta = (
            -new_y / R,
            new_z / R,
            -self.shots.active.cue.get_node("cue_stick_focus").getR(),
        )
        self.shots.active.cue.set_state(a=a, b=b, theta=theta)
        self.hud_elements["english"].set(a, b)
        self.hud_elements["jack"].set(theta)
