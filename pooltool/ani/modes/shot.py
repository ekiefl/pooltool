#! /usr/bin/env python

import numpy as np

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
import pooltool.ani.utils as autils
from pooltool.ani.action import Action
from pooltool.ani.camera import player_cam
from pooltool.ani.globals import Global
from pooltool.ani.hud import hud
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.objects.ball import Ball
from pooltool.objects.cue import cue_avoid
from pooltool.system import PlaybackMode


class ShotMode(BaseMode):
    name = Mode.shot
    keymap = {
        Action.aim: False,
        Action.move: False,
        Action.toggle_pause: False,
        Action.undo_shot: False,
        Action.restart_ani: False,
        Action.quit: False,
        Action.zoom: False,
        Action.rewind: False,
        Action.fast_forward: False,
        Action.cam_save: False,
        Action.cam_load: False,
        Action.show_help: False,
        Action.close_scene: False,
        Action.introspect: False,
        Action.next_shot: False,
        Action.prev_shot: False,
        Action.parallel: False,
    }

    # Controls whether user is viewing a shot, or whether they can take control and undo
    # shot, advance to next shot, etc.
    view_only = False

    def enter(self, init_animations=False):
        """Enter method for Shot

        Parameters
        ==========
        init_animations : bool, False
            If True, the shot animations are built and played via
            SystemCollection.init_animation() and SystemCollection.start_animation()
        """
        mouse.mode(MouseMode.RELATIVE)

        if init_animations:
            Global.shots.set_animation()
            Global.shots.start_animation(PlaybackMode.SINGLE)
            Global.shots.skip_stroke()

        player_cam.scale_focus()

        hud.update_cue(Global.shots.active.cue)

        tasks.register_event("space", Global.shots.toggle_pause)
        tasks.register_event("arrow_up", Global.shots.speed_up)
        tasks.register_event("arrow_down", Global.shots.slow_down)

        if self.view_only:
            self.register_keymap_event("escape", Action.close_scene, True)
            self.register_keymap_event("escape-up", Action.close_scene, False)
        else:
            self.register_keymap_event("escape", Action.quit, True)
            self.register_keymap_event("a", Action.aim, True)
            self.register_keymap_event("z", Action.undo_shot, True)
            self.register_keymap_event("z-up", Action.undo_shot, False)

        self.register_keymap_event("mouse1", Action.zoom, True)
        self.register_keymap_event("mouse1-up", Action.zoom, False)
        self.register_keymap_event("v", Action.move, True)
        self.register_keymap_event("v-up", Action.move, False)
        self.register_keymap_event("r", Action.restart_ani, True)
        self.register_keymap_event("r-up", Action.restart_ani, False)
        self.register_keymap_event("arrow_left", Action.rewind, True)
        self.register_keymap_event("arrow_left-up", Action.rewind, False)
        self.register_keymap_event("arrow_right", Action.fast_forward, True)
        self.register_keymap_event("arrow_right-up", Action.fast_forward, False)
        self.register_keymap_event("1", Action.cam_save, True)
        self.register_keymap_event("2", Action.cam_load, True)
        self.register_keymap_event("h", Action.show_help, True)
        self.register_keymap_event("i", Action.introspect, True)
        self.register_keymap_event("i-up", Action.introspect, False)
        self.register_keymap_event("n-up", Action.next_shot, True)
        self.register_keymap_event("p-up", Action.prev_shot, True)
        self.register_keymap_event("enter-up", Action.parallel, True)

        tasks.add(self.shot_view_task, "shot_view_task")
        tasks.add(self.shot_animation_task, "shot_animation_task")
        tasks.add(self.shared_task, "shared_task")

    def exit(self, key="soft"):
        """Exit shot mode

        Parameters
        ==========
        key : str, 'soft'
            Specifies how shot mode should be exited. Can be any of {'advance', 'reset',
            'soft'}. 'advance' and 'reset' end the animation, whereas 'soft' exits shot
            mode with the animations still playing. 'advance' sets the system state to
            the end state of the shot, whereas 'reset' returns the system state to the
            start state of the shot.
        """
        assert key in {"advance", "reset", "soft"}

        if key == "advance":
            if Global.shots.parallel:
                Global.shots.toggle_parallel()

            # If we are here, the plan is probably to return to 'aim' mode so another
            # shot can be taken. This shot needs to be defined by its own system that
            # has yet to be simulated. Depending how 'shot' mode was entered, this
            # system may already exist in Global.shots. The following code checks that
            # by seeing whether the latest system has any events. If not, the system is
            # unsimulated and is perfectly fit for 'aim' mode, but if the system has
            # events, a fresh system needs to be appended to Global.shots.
            make_new = True if len(Global.shots[-1].events) else False
            if make_new:
                if Global.shots.active_index != len(Global.shots) - 1:
                    # Replaying shot that is not most recent. Teardown and then buildup
                    # most recent
                    Global.shots.clear_animation()
                    Global.shots.active.teardown()
                    Global.shots.set_active(-1)
                    Global.shots.active.buildup()

                Global.shots.append_copy_of_active(
                    state="current",
                    reset_history=True,
                    as_active=False,
                )

                # Set the initial orientations of new shot to final orientations of old
                # shot
                for ball_id in Global.shots.active.balls:
                    old_ball = Global.shots.active.balls[ball_id]
                    new_ball = Global.shots[-1].balls[ball_id]
                    new_ball.initial_orientation = old_ball.get_final_orientation()
            else:
                # The latest entry in the collection is an unsimulated shot. Perfect
                pass

            # Switch shots
            Global.shots.clear_animation()
            Global.shots.active.teardown()
            Global.shots.set_active(-1)
            Global.shots.active.buildup()

            cue_avoid.init_collisions()

            if make_new:
                Global.shots.active.cue.reset_state()
            Global.shots.active.cue.set_render_state_as_object_state()

            # Set the HUD
            hud.update_cue(Global.shots.active.cue)

        elif key == "reset":
            if Global.shots.parallel:
                Global.shots.toggle_parallel()

            Global.shots.clear_animation()
            if Global.shots.active_index != len(Global.shots) - 1:
                # Replaying shot that is not most recent. Teardown and then buildup most
                # recent
                Global.shots.active.teardown()
                Global.shots.set_active(-1)
                Global.shots.active.buildup()
                cue_avoid.init_collisions()

            player_cam.load_state(Global.mode_mgr.mode_stroked_from)
            for ball in Global.shots.active.balls.values():
                if ball.history.is_populated():
                    ball.set(
                        rvw=ball.history.rvw[0],
                        s=ball.history.s[0],
                        t=0,
                    )
                    ball.get_node("pos").setQuat(ball.quats[0])
                ball.set_render_state_as_object_state()
                ball.history.reset()

            Global.shots.active.cue.init_focus(Global.shots.active.cue.cueing_ball)

        tasks.remove("shot_view_task")
        tasks.remove("shot_animation_task")
        tasks.remove("shared_task")

    def shot_view_task(self, task):
        if self.keymap[Action.close_scene]:
            player_cam.store_state("last_scene", overwrite=True)
            Global.base.messenger.send("close-scene")
            Global.mode_mgr.end_mode()
            Global.base.messenger.send("stop")

        elif self.keymap[Action.aim] or Global.shots.animation_finished:
            # Either the user has requested to start the next shot, or the animation has
            # finished
            Global.game.advance(Global.shots[-1])
            if Global.game.game_over:
                Global.mode_mgr.change_mode(Mode.game_over)
            else:
                Global.mode_mgr.change_mode(Mode.aim, exit_kwargs=dict(key="advance"))

        elif self.keymap[Action.zoom]:
            self.zoom_camera_shot()

        elif self.keymap[Action.move]:
            self.move_camera_shot()

        elif mouse.initialized:
            self.maybe_rotate_camera(task)

        return task.cont

    def shot_animation_task(self, task):
        if self.keymap[Action.restart_ani]:
            Global.shots.start_animation(PlaybackMode.LOOP)

        elif self.keymap[Action.rewind]:
            Global.shots.rewind()

        elif self.keymap[Action.fast_forward]:
            Global.shots.fast_forward()

        elif self.keymap[Action.undo_shot]:
            Global.mode_mgr.change_mode(
                Global.mode_mgr.mode_stroked_from,
                exit_kwargs=dict(key="reset"),
                enter_kwargs=dict(load_prev_cam=True),
            )

        elif self.keymap[Action.parallel]:
            self.keymap[Action.parallel] = False
            Global.shots.toggle_parallel()
            if not Global.shots.parallel:
                self.change_animation(Global.shots.active_index)

        elif self.keymap[Action.prev_shot]:
            self.keymap[Action.prev_shot] = False
            shot_index = Global.shots.active_index - 1
            while True:
                if shot_index < 0:
                    shot_index = len(Global.shots) - 1
                if (
                    len(Global.shots[shot_index].events)
                    or shot_index != len(Global.shots) - 1
                ):
                    break
                shot_index -= 1
            if not Global.shots.parallel:
                self.change_animation(shot_index)
            else:
                Global.shots.set_active(shot_index)
                Global.shots.highlight_system(shot_index)
                hud.update_cue(Global.shots.active.cue)

        elif self.keymap[Action.next_shot]:
            self.keymap[Action.next_shot] = False
            shot_index = Global.shots.active_index + 1
            while True:
                if shot_index == len(Global.shots):
                    shot_index = 0
                if (
                    len(Global.shots[shot_index].events)
                    or shot_index != len(Global.shots) - 1
                ):
                    break
                shot_index += 1
            if not Global.shots.parallel:
                self.change_animation(shot_index)
            else:
                Global.shots.set_active(shot_index)
                Global.shots.highlight_system(shot_index)
                hud.update_cue(Global.shots.active.cue)

        return task.cont

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

    def zoom_camera_shot(self):
        with mouse:
            s = -mouse.get_dy() * ani.zoom_sensitivity

        player_cam.node.setPos(autils.multiply_cw(player_cam.node.getPos(), 1 - s))
        player_cam.scale_focus()

    def move_camera_shot(self):
        with mouse:
            dxp, dyp = mouse.get_dx(), mouse.get_dy()

        h = player_cam.focus.getH() * np.pi / 180 + np.pi / 2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        player_cam.focus.setX(player_cam.focus.getX() + dx * ani.move_sensitivity)
        player_cam.focus.setY(player_cam.focus.getY() + dy * ani.move_sensitivity)

    def maybe_rotate_camera(self, task):
        if task.time < ani.rotate_downtime:
            # Shot follow through can move camera jarringly, so don't move camera if
            # within the dwell time. But do touch the mouse so there is not a big jump
            mouse.touch()
            return

        fx, fy = ani.rotate_sensitivity_x, ani.rotate_sensitivity_y

        with mouse:
            alpha_x = player_cam.focus.getH() - fx * mouse.get_dx()
            alpha_y = max(min(0, player_cam.focus.getR() + fy * mouse.get_dy()), -90)

        player_cam.focus.setH(alpha_x)  # Move view laterally
        player_cam.focus.setR(alpha_y)  # Move view vertically
