#! /usr/bin/env python

import numpy as np

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.camera import cam
from pooltool.ani.collision import cue_avoid
from pooltool.ani.globals import Global
from pooltool.ani.hud import hud
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.ani.scene import visual
from pooltool.config import settings
from pooltool.ptmath.utils import norm2d, tip_contact_offset
from pooltool.system.datatypes import multisystem


class ViewMode(BaseMode):
    name = Mode.view
    keymap = {
        Action.aim: False,
        Action.call_shot: False,
        Action.fine_control: False,
        Action.move: False,
        Action.stroke: False,
        Action.quit: False,
        Action.zoom: False,
        Action.cam_save: False,
        Action.cam_load: False,
        Action.show_help: False,
        Action.pick_ball: False,
        Action.ball_in_hand: False,
        Action.power: False,
        Action.elevation: False,
        Action.english: False,
        Action.prev_shot: False,
        Action.introspect: False,
        Action.hide_cue: False,
        Action.exec_shot: False,
    }

    def __init__(self):
        super().__init__()

        # In this state, the cue sticks to the cue_avoid.min_theta
        self.magnet_theta = True
        # if cue angle is within this many degrees from cue_avoid.min_theta, it sticks
        # to cue_avoid.min_theta
        self.magnet_threshold = 0.2

    def enter(self, move_active=False, load_prev_cam=False):
        mouse.mode(MouseMode.RELATIVE)

        if multisystem.active is not None:
            visual.cue.hide_nodes(ignore=("cue_cseg",))

        if load_prev_cam:
            cam.load_saved_state(Mode.view)

        if move_active:
            self.keymap[Action.move] = True

        self.register_keymap_event("escape", Action.quit, True)
        self.register_keymap_event("mouse1", Action.zoom, True)
        self.register_keymap_event("mouse1-up", Action.zoom, False)
        self.register_keymap_event("a", Action.aim, True)
        self.register_keymap_event("s", Action.stroke, True)
        self.register_keymap_event("v", Action.move, True)
        self.register_keymap_event("v-up", Action.move, False)
        self.register_keymap_event("1", Action.cam_save, True)
        self.register_keymap_event("2", Action.cam_load, True)
        self.register_keymap_event("h", Action.show_help, True)
        self.register_keymap_event("q", Action.pick_ball, True)
        self.register_keymap_event("g", Action.ball_in_hand, True)
        self.register_keymap_event("c", Action.call_shot, True)
        self.register_keymap_event("i", Action.introspect, True)
        self.register_keymap_event("i-up", Action.introspect, False)
        self.register_keymap_event("b", Action.elevation, True)
        self.register_keymap_event("b-up", Action.hide_cue, True)
        self.register_keymap_event("e", Action.english, True)
        self.register_keymap_event("e-up", Action.hide_cue, True)
        self.register_keymap_event("x", Action.power, True)
        self.register_keymap_event("x-up", Action.hide_cue, True)
        self.register_keymap_event("p-up", Action.prev_shot, True)
        self.register_keymap_event("space", Action.exec_shot, True)
        self.register_keymap_event("space-up", Action.exec_shot, False)

        tasks.add(self.view_task, "view_task")
        tasks.add(self.shared_task, "shared_task")
        if settings.gameplay.cue_collision:
            tasks.add(cue_avoid.collision_task, "collision_task")

    def exit(self):
        tasks.remove("view_task")
        tasks.remove("shared_task")

        if settings.gameplay.cue_collision:
            tasks.remove("collision_task")
        cam.store_state(Mode.view, overwrite=True)

    def view_task(self, task):
        if self.keymap[Action.stroke]:
            Global.mode_mgr.change_mode(Mode.stroke)
        elif self.keymap[Action.pick_ball]:
            Global.mode_mgr.change_mode(Mode.pick_ball)
        elif self.keymap[Action.call_shot]:
            Global.mode_mgr.change_mode(Mode.call_shot)
        elif self.keymap[Action.ball_in_hand]:
            Global.mode_mgr.change_mode(Mode.ball_in_hand)
        elif self.keymap[Action.zoom]:
            cam.zoom_via_mouse()
        elif self.keymap[Action.move]:
            cam.move_fixation_via_mouse()
        elif self.keymap[Action.hide_cue]:
            self.keymap[Action.hide_cue] = False
            self.keymap[Action.english] = False
            self.keymap[Action.elevation] = False
            self.keymap[Action.power] = False
            if multisystem.active is not None:
                visual.cue.hide_nodes(ignore=("cue_cseg",))
        elif self.keymap[Action.elevation]:
            self.view_elevate_cue()
        elif self.keymap[Action.english]:
            self.view_apply_english()
        elif self.keymap[Action.power]:
            self.view_apply_power()
        elif self.keymap[Action.aim]:
            Global.mode_mgr.change_mode(Mode.aim, enter_kwargs=dict(load_prev_cam=True))
        elif self.keymap[Action.exec_shot]:
            self.keymap[Action.exec_shot] = False
            if Global.game.shot_constraints.can_shoot():
                Global.mode_mgr.mode_stroked_from = Mode.aim
                visual.cue.set_object_state_as_render_state(skip_V0=True)
                multisystem.active.strike()
                Global.mode_mgr.change_mode(Mode.calculate)
        elif self.keymap[Action.prev_shot]:
            self.keymap[Action.prev_shot] = False
            if len(multisystem) > 1:
                visual.switch_to_shot(multisystem.active_index - 1)
                self._update_hud()
                Global.mode_mgr.change_mode(
                    Mode.shot, enter_kwargs=dict(build_animations=False)
                )
                return task.done
        else:
            cam.rotate_via_mouse()

        return task.cont

    def view_apply_power(self):
        visual.cue.show_nodes(ignore=("cue_cseg",))

        with mouse:
            dy = mouse.get_dy()

        V0 = multisystem.active.cue.V0 + dy * ani.power_sensitivity
        if V0 < ani.min_stroke_speed:
            V0 = ani.min_stroke_speed
        if V0 > ani.max_stroke_speed:
            V0 = ani.max_stroke_speed

        multisystem.active.cue.set_state(V0=V0)
        self._update_hud()

    def view_elevate_cue(self):
        visual.cue.show_nodes(ignore=("cue_cseg",))

        cue = visual.cue.get_node("cue_stick_focus")

        with mouse:
            delta_elevation = mouse.get_dy() * ani.elevate_sensitivity

        old_elevation = -cue.getR()
        new_elevation = max(0, min(ani.max_elevate, old_elevation + delta_elevation))

        if cue_avoid.min_theta >= new_elevation - self.magnet_threshold:
            # user set theta to minimum value, resume cushion tracking
            self.magnet_theta = True
            new_elevation = cue_avoid.min_theta
        else:
            # theta has been modified by the user, so no longer tracks the cushion
            self.magnet_theta = False

        cue.setR(-new_elevation)

        multisystem.active.cue.set_state(theta=new_elevation)
        self._update_hud()

    def view_apply_english(self):
        visual.cue.show_nodes(ignore=("cue_cseg",))

        with mouse:
            dx, dy = mouse.get_dx(), mouse.get_dy()

        cue = visual.cue.get_node("cue_stick")
        cue_focus = visual.cue.get_node("cue_stick_focus")
        R = visual.cue.follow._ball.params.R

        delta_y, delta_z = dx * ani.english_sensitivity, dy * ani.english_sensitivity

        # y corresponds to side spin, z to top/bottom spin
        new_y = cue.getY() + delta_y
        new_z = cue.getZ() + delta_z

        # y corresponds to side spin, z to top/bottom spin
        cue_axis_offset = (
            np.array([-new_y, new_z]) / R
        )  # components normalized to ball radius
        contact_point_offset = tip_contact_offset(
            cue_axis_offset, multisystem.active.cue.specs.tip_radius, R
        )

        norm = norm2d(contact_point_offset)
        if norm > ani.max_english:
            limit_scaling_factor = ani.max_english / norm
            new_y *= limit_scaling_factor
            new_z *= limit_scaling_factor
            cue_axis_offset *= limit_scaling_factor
            contact_point_offset *= limit_scaling_factor

        cue.setY(new_y)
        cue.setZ(new_z)

        # if application of english increases min_theta beyond current elevation,
        # increase elevation
        if (
            self.magnet_theta
            or cue_avoid.min_theta >= -cue_focus.getR() - self.magnet_threshold
        ):
            cue_focus.setR(-cue_avoid.min_theta)

        multisystem.active.cue.set_state(
            a=contact_point_offset[0],
            b=contact_point_offset[1],
            theta=-visual.cue.get_node("cue_stick_focus").getR(),
        )

        self._update_hud()

    def _update_hud(self) -> None:
        """Update HUD with current system's cue and cue ball"""
        system_cue = multisystem.active.cue
        hud.update_cue(system_cue, multisystem.active.balls[system_cue.cue_ball_id])
