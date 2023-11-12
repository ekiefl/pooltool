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
from pooltool.ani.modes.shot import ShotMode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.system.datatypes import multisystem
from pooltool.system.render import visual


class AimMode(BaseMode):
    name = Mode.aim
    keymap = {
        Action.rotate_cue_left: False,
        Action.rotate_cue_right: False,
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
        super().__init__()

        # In this state, the cue sticks to the cue_avoid.min_theta
        self.magnet_theta = True
        # if cue angle is within this many degrees from cue_avoid.min_theta, it sticks
        # to cue_avoid.min_theta
        self.magnet_threshold = 0.2

    def enter(self, load_prev_cam=False):
        mouse.mode(MouseMode.RELATIVE)

        if not visual.cue.has_focus:
            ball_id = multisystem.active.cue.cue_ball_id
            visual.cue.init_focus(visual.balls[ball_id])
        else:
            visual.cue.match_ball_position()

        visual.cue.show_nodes(ignore=("cue_cseg",))
        visual.cue.get_node("cue_stick").setX(0)

        # Fixate the camera onto the cueing ball
        cueing_ball_id = multisystem.active.cue.cue_ball_id
        cam.move_fixation(visual.balls[cueing_ball_id].get_node("pos").getPos())

        if load_prev_cam:
            cam.load_saved_state(Mode.aim)

        self.register_keymap_event("escape", Action.quit, True)
        self.register_keymap_event("f", Action.fine_control, True)
        self.register_keymap_event("f-up", Action.fine_control, False)
        self.register_keymap_event("t", Action.adjust_head, True)
        self.register_keymap_event("t-up", Action.adjust_head, False)
        self.register_keymap_event("mouse1", Action.zoom, True)
        self.register_keymap_event("mouse1-up", Action.zoom, False)
        self.register_keymap_event("j", Action.rotate_cue_left, True)
        self.register_keymap_event("j-up", Action.rotate_cue_left, False)
        self.register_keymap_event("k", Action.rotate_cue_right, True)
        self.register_keymap_event("k-up", Action.rotate_cue_right, False)
        self.register_keymap_event("s", Action.stroke, True)
        self.register_keymap_event("v", Action.view, True)
        self.register_keymap_event("1", Action.cam_save, True)
        self.register_keymap_event("2", Action.cam_load, True)
        self.register_keymap_event("h", Action.show_help, True)
        self.register_keymap_event("q", Action.pick_ball, True)
        self.register_keymap_event("c", Action.call_shot, True)
        self.register_keymap_event("g", Action.ball_in_hand, True)
        self.register_keymap_event("b", Action.elevation, True)
        self.register_keymap_event("b-up", Action.elevation, False)
        self.register_keymap_event("e", Action.english, True)
        self.register_keymap_event("e-up", Action.english, False)
        self.register_keymap_event("x", Action.power, True)
        self.register_keymap_event("x-up", Action.power, False)
        self.register_keymap_event("space", Action.exec_shot, True)
        self.register_keymap_event("space-up", Action.exec_shot, False)
        self.register_keymap_event("p-up", Action.prev_shot, True)
        self.register_keymap_event("i", Action.introspect, True)
        self.register_keymap_event("i-up", Action.introspect, False)

        if ani.settings["gameplay"]["cue_collision"]:
            tasks.add(cue_avoid.collision_task, "collision_task")

        tasks.add(self.aim_task, "aim_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self):
        tasks.remove("aim_task")
        tasks.remove("shared_task")

        if ani.settings["gameplay"]["cue_collision"]:
            tasks.remove("collision_task")

        cam.store_state(Mode.aim, overwrite=True)

    def aim_task(self, task):
        if self.keymap[Action.view]:
            Global.mode_mgr.change_mode(Mode.view, enter_kwargs=dict(move_active=True))
            return task.done
        elif self.keymap[Action.stroke]:
            Global.mode_mgr.change_mode(Mode.stroke)
        elif self.keymap[Action.pick_ball]:
            Global.mode_mgr.change_mode(Mode.pick_ball)
        elif self.keymap[Action.call_shot]:
            Global.mode_mgr.change_mode(Mode.call_shot)
        elif self.keymap[Action.ball_in_hand]:
            Global.mode_mgr.change_mode(Mode.ball_in_hand)
        elif self.keymap[Action.zoom]:
            cam.zoom_via_mouse()
        elif self.keymap[Action.adjust_head]:
            cam.rotate_via_mouse(theta_only=True)
            self.cue_avoidance()
        elif self.keymap[Action.elevation]:
            self.aim_elevate_cue()
        elif self.keymap[Action.english]:
            self.apply_english()
        elif self.keymap[Action.power]:
            self.aim_apply_power()
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
                ShotMode.change_animation(multisystem.active_index - 1)
                Global.mode_mgr.change_mode(Mode.shot)
                return task.done
        else:
            self.rotate()

        return task.cont

    def rotate(self):
        keyboard_rotation = 0.1 if self.keymap[Action.fine_control] else 2
        if self.keymap[Action.rotate_cue_left]:
            cam.rotate(phi=cam.phi + keyboard_rotation)
        elif self.keymap[Action.rotate_cue_right]:
            cam.rotate(phi=cam.phi - keyboard_rotation)
        else:
            cam.rotate_via_mouse(fine_control=self.keymap[Action.fine_control])
        self.fix_cue_stick_to_camera()
        self.cue_avoidance()

    def cue_avoidance(self):
        _, _, theta, *_ = visual.cue.get_render_state()

        if (theta < cue_avoid.min_theta) or self.magnet_theta:
            theta = cue_avoid.min_theta
            multisystem.active.cue.set_state(theta=theta)
            visual.cue.set_render_state_as_object_state()
            hud.update_cue(multisystem.active.cue)

        if cam.theta < theta + ani.min_camera:
            cam.rotate(theta=theta + ani.min_camera)

    def fix_cue_stick_to_camera(self):
        phi = (cam.fixation.getH() + 180) % 360
        multisystem.active.cue.set_state(phi=phi)
        visual.cue.set_render_state_as_object_state()

    def aim_apply_power(self):
        with mouse:
            dy = mouse.get_dy()

        V0 = multisystem.active.cue.V0 + dy * ani.power_sensitivity
        if V0 < ani.min_stroke_speed:
            V0 = ani.min_stroke_speed
        if V0 > ani.max_stroke_speed:
            V0 = ani.max_stroke_speed

        multisystem.active.cue.set_state(V0=V0)
        hud.update_cue(multisystem.active.cue)

    def aim_elevate_cue(self):
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

        if cam.theta < (new_elevation + ani.min_camera):
            cam.rotate(theta=new_elevation + ani.min_camera)

        multisystem.active.cue.set_state(theta=new_elevation)
        hud.update_cue(multisystem.active.cue)

    def apply_english(self):
        with mouse:
            dx, dy = mouse.get_dx(), mouse.get_dy()

        cue = visual.cue.get_node("cue_stick")
        cue_focus = visual.cue.get_node("cue_stick_focus")

        R = visual.cue.follow._ball.params.R

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
            or cue_avoid.min_theta >= -cue_focus.getR() - self.magnet_threshold
        ):
            cue_focus.setR(-cue_avoid.min_theta)

        if cam.theta < (new_theta := -cue_focus.getR() + ani.min_camera):
            cam.rotate(theta=new_theta)

        multisystem.active.cue.set_state(
            a=-new_y / R,
            b=new_z / R,
            theta=-cue_focus.getR(),
        )

        hud.update_cue(multisystem.active.cue)
