#! /usr/bin/env python

from typing import Optional

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.camera import cam
from pooltool.ani.collision import cue_avoid
from pooltool.ani.globals import Global
from pooltool.ani.hud import hud
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse
from pooltool.objects.ball.datatypes import Ball, BallHistory
from pooltool.system.render import PlaybackMode, visual


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

    def enter(
        self, build_animations=False, playback_mode: Optional[PlaybackMode] = None
    ):
        """Enter method for Shot

        Parameters
        ==========
        build_animations : bool, False
            If True, the shot animations are built with visual.build_shot_animation.
        """
        mouse.mode(MouseMode.RELATIVE)

        if build_animations:
            visual.build_shot_animation()
            visual.animate(PlaybackMode.SINGLE)
            visual.advance_to_end_of_stroke()

        if playback_mode is not None:
            visual.animate(playback_mode)

        hud.update_cue(Global.system.cue)

        tasks.register_event("space", visual.toggle_pause)
        tasks.register_event("arrow_up", visual.speed_up)
        tasks.register_event("arrow_down", visual.slow_down)

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
            raise NotImplementedError()
            # If we are here, the plan is probably to return to 'aim' mode so another
            # shot can be taken. This shot needs to be defined by its own system that
            # has yet to be simulated. Depending how 'shot' mode was entered, this
            # system may already exist in Global.multisystem. The following code checks
            # that by seeing whether the latest system has any events. If not, the
            # system is unsimulated and is perfectly fit for 'aim' mode, but if the
            # system has events, a fresh system needs to be appended to
            # Global.multisystem.
            make_new = bool(len(Global.multisystem[-1].events))
            if make_new:
                if Global.multisystem.active_index != len(Global.multisystem) - 1:
                    # Replaying shot that is not most recent. Teardown and then buildup
                    # most recent
                    # FIXME repeated below?
                    Global.multisystem.set_active(-1)
                    visual.attach_system(Global.system)
                    visual.buildup()

                Global.multisystem.append_copy_of_active(
                    state="current",
                    reset_history=True,
                    as_active=False,
                )

                # Set the initial orientations of new shot to final orientations of old
                # shot
                for ball_id in Global.system.balls:
                    old_ball = Global.system.balls[ball_id]
                    new_ball = Global.multisystem[-1].balls[ball_id]
                    new_ball.initial_orientation = old_ball.get_final_orientation()
            else:
                # The latest entry in the collection is an unsimulated shot. Perfect
                pass

            # Switch shots
            Global.multisystem.set_active(-1)
            visual.attach_system(Global.system)
            visual.buildup()

            cue_avoid.init_collisions()

            if make_new:
                raise NotImplementedError()
                # FIXME Is this needed?
                Global.system.cue.reset_state()

            Global.system.cue.set_render_state_as_object_state()

            # Set the HUD
            hud.update_cue(Global.system.cue)

        elif key == "reset":
            if Global.multisystem.active_index != len(Global.multisystem) - 1:
                # Replaying shot that is not most recent. Teardown and then buildup most
                # recent
                Global.multisystem.set_active(-1)
                visual.attach_system(Global.system)
                visual.buildup()
                cue_avoid.init_collisions()
            else:
                visual.reset_animation()

            cam.load_saved_state(Global.mode_mgr.mode_stroked_from)
            for ball_render in visual.balls.values():
                ball = ball_render._ball
                if not ball.history.empty:
                    ball.state.set(
                        rvw=ball.history[0].rvw,
                        s=ball.history[0].s,
                        t=0,
                    )
                    ball_render.get_node("pos").setQuat(ball_render.quats[0])
                ball_render.set_render_state_as_object_state()
                ball.history = BallHistory()
                ball.history_cts = BallHistory()

            ball_id = Global.system.cue.cue_ball_id
            visual.cue.init_focus(visual.balls[ball_id])

        tasks.remove("shot_view_task")
        tasks.remove("shot_animation_task")
        tasks.remove("shared_task")

    def shot_view_task(self, task):
        if self.keymap[Action.close_scene]:
            cam.store_state("last_scene", overwrite=True)
            Global.base.messenger.send("close-scene")
            Global.mode_mgr.end_mode()
            Global.base.messenger.send("stop")

        elif self.keymap[Action.aim] or visual.animation_finished:
            # Either the user has requested to start the next shot, or the animation has
            # finished
            Global.game.advance(Global.multisystem[-1])
            if Global.game.game_over:
                Global.mode_mgr.change_mode(Mode.game_over)
            else:
                Global.mode_mgr.change_mode(Mode.aim, exit_kwargs=dict(key="advance"))

        elif self.keymap[Action.zoom]:
            cam.zoom_via_mouse()

        elif self.keymap[Action.move]:
            cam.move_fixation_via_mouse()

        elif task.time > ani.rotate_downtime:
            # Only rotate the camera if some time has passed since the mode was entered,
            # otherwise the shot followthrough jarringly rotates the camera
            cam.rotate_via_mouse()

        else:
            # We didn't do anything this frame, but touch the mouse so any future mouse
            # movements don't experience a big jump
            mouse.touch()

        return task.cont

    def shot_animation_task(self, task):
        if self.keymap[Action.restart_ani]:
            visual.playback(PlaybackMode.LOOP)
            visual.restart_animation()

        elif self.keymap[Action.rewind]:
            raise NotImplementedError()

        elif self.keymap[Action.fast_forward]:
            raise NotImplementedError()

        elif self.keymap[Action.undo_shot]:
            Global.mode_mgr.change_mode(
                Global.mode_mgr.mode_stroked_from,
                exit_kwargs=dict(key="reset"),
                enter_kwargs=dict(load_prev_cam=True),
            )

        elif self.keymap[Action.parallel]:
            # FIXME Implementing parallel would involve code here and throughout shot.py
            # and view.py
            raise NotImplementedError()

        elif self.keymap[Action.prev_shot]:
            self.keymap[Action.prev_shot] = False
            shot_index = Global.multisystem.active_index - 1
            while True:
                if shot_index < 0:
                    shot_index = len(Global.multisystem) - 1
                if (
                    len(Global.multisystem[shot_index].events)
                    or shot_index != len(Global.multisystem) - 1
                ):
                    break
                shot_index -= 1
            self.change_animation(shot_index)

        elif self.keymap[Action.next_shot]:
            self.keymap[Action.next_shot] = False
            shot_index = Global.multisystem.active_index + 1
            while True:
                if shot_index == len(Global.multisystem):
                    shot_index = 0
                if (
                    len(Global.multisystem[shot_index].events)
                    or shot_index != len(Global.multisystem) - 1
                ):
                    break
                shot_index += 1
            self.change_animation(shot_index)

        return task.cont

    def change_animation(self, shot_index):
        """Switch to a different system in the system collection"""
        # Switch shots
        Global.multisystem.set_active(shot_index)
        visual.attach_system(Global.system)
        visual.buildup()

        # Initialize the animation
        visual.build_shot_animation()

        # Changing to a different shot is considered advanced maneuvering, so we enter
        # loop mode.
        visual.animate(PlaybackMode.LOOP)

        # FIXME No idea what this garbage is. Dissect once you get here.
        raise NotImplementedError()
        # A lot of dumb things to make the cue track the initial position of the ball
        dummy = Ball("dummy")
        dummy.params.R = Global.system.cue.cueing_ball.params.R
        dummy.state.rvw = Global.system.cue.cueing_ball.history[0].rvw
        dummy.render_obj.render(dummy)
        visual.cue.init_focus(dummy)
        Global.system.cue.set_render_state_as_object_state()
        visual.cue.follow = None
        dummy.render_obj.remove_nodes()
        del dummy

        cue_avoid.init_collisions()

        # Set the HUD
        hud.update_cue(Global.system.cue)
