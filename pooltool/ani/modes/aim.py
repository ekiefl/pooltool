#! /usr/bin/env python

import numpy as np

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
import pooltool.ani.utils as autils
from pooltool.ani.action import Action
from pooltool.ani.camera import camera
from pooltool.ani.globals import Global
from pooltool.ani.hud import hud
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.objects.ball import Ball
from pooltool.objects.cue import cue_avoid
from pooltool.system import PlaybackMode


class AimMode(BaseMode):
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
        super().__init__()

        # In this state, the cue sticks to the cue_avoid.min_theta
        self.magnet_theta = True
        # if cue angle is within this many degrees from cue_avoid.min_theta, it sticks
        # to cue_avoid.min_theta
        self.magnet_threshold = 0.2

    def enter(self, load_prev_cam=False):
        mouse.mode(MouseMode.RELATIVE)

        if not Global.shots.active.cue.has_focus:
            Global.shots.active.cue.init_focus(Global.shots.active.cue.cueing_ball)
        else:
            Global.shots.active.cue.update_focus()

        Global.shots.active.cue.show_nodes(ignore=("cue_cseg",))
        Global.shots.active.cue.get_node("cue_stick").setX(0)
        camera.update_focus(
            Global.shots.active.cue.cueing_ball.get_node("pos").getPos()
        )
        if load_prev_cam:
            camera.load_state(Mode.aim)

        self.register_keymap_event("escape", Action.quit, True)
        self.register_keymap_event("f", Action.fine_control, True)
        self.register_keymap_event("f-up", Action.fine_control, False)
        self.register_keymap_event("t", Action.adjust_head, True)
        self.register_keymap_event("t-up", Action.adjust_head, False)
        self.register_keymap_event("mouse1", Action.zoom, True)
        self.register_keymap_event("mouse1-up", Action.zoom, False)
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

        camera.store_state(Mode.aim, overwrite=True)

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
            Global.mode_mgr.mode_stroked_from = Mode.aim
            Global.shots.active.cue.set_object_state_as_render_state(skip_V0=True)
            Global.shots.active.cue.strike()
            Global.mode_mgr.change_mode(Mode.calculate)
        elif self.keymap[Action.prev_shot]:
            self.keymap[Action.prev_shot] = False
            if len(Global.shots) > 1:
                self.change_animation(Global.shots.active_index - 1)
                Global.mode_mgr.change_mode(
                    Mode.shot, enter_kwargs=dict(init_animations=False)
                )
                return task.done
        else:
            self.rotate_camera_aim()

        return task.cont

    def zoom_camera_aim(self):
        with mouse:
            s = -mouse.get_dy() * ani.zoom_sensitivity

        camera.node.setPos(autils.multiply_cw(camera.node.getPos(), 1 - s))

    def adjust_head_aim(self):
        with mouse:
            alpha_y = max(
                min(
                    0,
                    camera.focus.getR() + ani.rotate_sensitivity_y * mouse.get_dy(),
                ),
                -90,
            )

        camera.focus.setR(alpha_y)  # Move view vertically

    def rotate_camera_aim(self):
        if self.keymap[Action.fine_control]:
            fx, fy = ani.rotate_fine_sensitivity_x, ani.rotate_fine_sensitivity_y
        else:
            fx, fy = ani.rotate_sensitivity_x, ani.rotate_sensitivity_y

        with mouse:
            alpha_x = camera.focus.getH() - fx * mouse.get_dx()
            alpha_y = max(min(0, camera.focus.getR() + fy * mouse.get_dy()), -90)

        camera.focus.setH(alpha_x)  # Move view laterally
        camera.focus.setR(alpha_y)  # Move view vertically

        self.fix_cue_stick_to_camera()

        if (
            -Global.shots.active.cue.get_node("cue_stick_focus").getR()
            < cue_avoid.min_theta
        ) or self.magnet_theta:
            Global.shots.active.cue.set_state(theta=cue_avoid.min_theta)
            Global.shots.active.cue.set_render_state_as_object_state()
            hud.update_cue(Global.shots.active.cue)

        if -camera.focus.getR() < (
            -Global.shots.active.cue.get_node("cue_stick_focus").getR() + ani.min_camera
        ):
            camera.focus.setR(
                -(
                    -Global.shots.active.cue.get_node("cue_stick_focus").getR()
                    + ani.min_camera
                )
            )

    def fix_cue_stick_to_camera(self):
        phi = (camera.focus.getH() + 180) % 360
        Global.shots.active.cue.set_state(phi=phi)
        Global.shots.active.cue.set_render_state_as_object_state()

    def aim_apply_power(self):
        with mouse:
            dy = mouse.get_dy()

        V0 = Global.shots.active.cue.V0 + dy * ani.power_sensitivity
        if V0 < ani.min_stroke_speed:
            V0 = ani.min_stroke_speed
        if V0 > ani.max_stroke_speed:
            V0 = ani.max_stroke_speed

        Global.shots.active.cue.set_state(V0=V0)
        hud.update_cue(Global.shots.active.cue)

    def aim_elevate_cue(self):
        cue = Global.shots.active.cue.get_node("cue_stick_focus")

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

        if -camera.focus.getR() < (new_elevation + ani.min_camera):
            camera.focus.setR(-(new_elevation + ani.min_camera))

        Global.shots.active.cue.set_state(theta=new_elevation)
        hud.update_cue(Global.shots.active.cue)

    def apply_english(self):
        with mouse:
            dx, dy = mouse.get_dx(), mouse.get_dy()

        cue = Global.shots.active.cue.get_node("cue_stick")
        cue_focus = Global.shots.active.cue.get_node("cue_stick_focus")
        R = Global.shots.active.cue.follow.R

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

        if -camera.focus.getR() < (
            -Global.shots.active.cue.get_node("cue_stick_focus").getR() + ani.min_camera
        ):
            camera.focus.setR(
                -(
                    -Global.shots.active.cue.get_node("cue_stick_focus").getR()
                    + ani.min_camera
                )
            )

        Global.shots.active.cue.set_state(
            a=-new_y / R,
            b=new_z / R,
            theta=-Global.shots.active.cue.get_node("cue_stick_focus").getR(),
        )

        hud.update_cue(Global.shots.active.cue)

    def change_animation(self, shot_index):
        """Switch to a different system in the system collection"""
        # Switch shots
        Global.shots.clear_animation()
        Global.shots.active.teardown()
        Global.shots.set_active(shot_index)
        Global.shots.active.buildup()

        # Initialize the animation
        Global.shots.set_animation()

        # Changing to a different shot is considered advanced maneuvering, so we enter
        # loop mode.
        Global.shots.start_animation(PlaybackMode.LOOP)

        # A lot of dumb things to make the cue track the initial position of the ball
        dummy = Ball("dummy")
        dummy.R = Global.shots.active.cue.cueing_ball.R
        dummy.rvw = Global.shots.active.cue.cueing_ball.history.rvw[0]
        dummy.render()
        Global.shots.active.cue.init_focus(dummy)
        Global.shots.active.cue.set_render_state_as_object_state()
        Global.shots.active.cue.follow = None
        dummy.remove_nodes()
        del dummy

        cue_avoid.init_collisions()

        # Set the HUD
        hud.update_cue(Global.shots.active.cue)
