from direct.interval.IntervalGlobal import Func, Parallel, Sequence, Wait
from panda3d.direct import HideInterval, ShowInterval

import pooltool.ani as ani
from pooltool.error import ConfigError
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum, auto


class PlaybackMode(StrEnum):
    LOOP = auto()
    SINGLE = auto()


class SystemRender:
    def __init__(self, system: System):
        self.reset_animation()

    def reset_animation(self):
        self.shot_animation = None
        self.ball_animations = None
        self.stroke_animation = None
        self.user_stroke = False
        self.playback_speed = 1

    def init_shot_animation(
        self, shot, animate_stroke=True, trailing_buffer=0, leading_buffer=0
    ):
        if not shot.continuized:
            # playback speed / fps * 2.0 is basically the sweetspot for creating smooth
            # interpolations that capture motion. Any more is wasted computation and any
            # less and the interpolation starts to look bad.
            if self.playback_speed > 0.99:
                shot.continuize(
                    dt=self.playback_speed / ani.settings["graphics"]["fps"] * 2.5
                )
            else:
                shot.continuize(
                    dt=self.playback_speed / ani.settings["graphics"]["fps"] * 1.5
                )

        if self.ball_animations is None:
            # This takes ~90% of this method's execution time
            self.ball_animations = Parallel()
            for ball in shot.balls.values():
                if not ball.render_obj.rendered:
                    ball.render_obj.render(ball)
                ball.render_obj.set_playback_sequence(
                    ball, playback_speed=self.playback_speed
                )
                self.ball_animations.append(ball.render_obj.playback_sequence)

        if self.user_stroke and animate_stroke:
            # There exists a stroke trajectory, and animating the stroke has been
            # requested
            shot.cue.render_obj.set_stroke_sequence()
            self.stroke_animation = Sequence(
                ShowInterval(shot.cue.render_obj.get_node("cue_stick")),
                shot.cue.render_obj.stroke_sequence,
                HideInterval(shot.cue.render_obj.get_node("cue_stick")),
            )
            self.shot_animation = Sequence(
                Func(self.restart_ball_animations),
                self.stroke_animation,
                self.ball_animations,
                Wait(trailing_buffer),
            )
        else:
            shot.cue.render_obj.hide_nodes()
            self.stroke_animation = None
            self.shot_animation = Sequence(
                Func(self.restart_ball_animations),
                self.ball_animations,
                Wait(trailing_buffer),
            )

    def start_animation(self, playback_mode: PlaybackMode):
        if self.shot_animation is None:
            raise Exception("First call SystemRender.init_shot_animation()")

        if playback_mode == PlaybackMode.SINGLE:
            self.shot_animation.start()
        elif playback_mode == PlaybackMode.LOOP:
            self.shot_animation.loop()

    def restart_animation(self):
        self.shot_animation.set_t(0)

    def restart_ball_animations(self):
        self.ball_animations.set_t(0)

    def clear_animation(self, shot):
        if self.shot_animation is not None:
            self.shot_animation.clearToInitial()
            self.shot_animation = None
            self.ball_animations = None
            self.stroke_animation = None

        for ball in shot.balls.values():
            if ball.render_obj.playback_sequence is not None:
                ball.render_obj.playback_sequence.pause()
                ball.render_obj.playback_sequence = None

    def toggle_pause(self):
        if self.shot_animation.isPlaying():
            self.pause_animation()
        else:
            self.resume_animation()

    def offset_time(self, dt):
        old_t = self.shot_animation.get_t()
        new_t = max(0, min(old_t + dt, self.shot_animation.duration))
        self.shot_animation.set_t(new_t)

    def pause_animation(self):
        self.shot_animation.pause()

    def resume_animation(self):
        self.shot_animation.resume()

    def teardown(self, shot):
        self.clear_animation(shot)
        for ball in shot.balls.values():
            ball.render_obj.remove_nodes()
        shot.cue.render_obj.remove_nodes()

    def buildup(self, shot):
        self.clear_animation(shot)
        for ball in shot.balls.values():
            ball.render_obj.render(ball)
            ball.render_obj.reset_angular_integration()
        shot.cue.render_obj.render()
        shot.cue.render_obj.init_focus(shot.cue.cueing_ball)


class MultiSystemRender:
    def __init__(self):
        self.shot_animation = None
        self.playback_speed = 1.0
        self.parallel = False
        self.paused = False

    @property
    def animation_finished(self):
        """Returns whether or not the animation is finished

        Returns true if the animation has stopped and it's not because the game has been
        paused. The animation is never finished if it's playing in a loop.
        """

        if not self.shot_animation.isPlaying() and not self.paused:
            return True
        else:
            return False

    def set_animation(self, multisystem):
        if self.parallel:
            self.shot_animation = Parallel()

            # `max_dur` is the shot duration of the longest shot in the collection. All
            # shots beside this one will have a buffer appended where the balls stay in
            # their final state until the last shot finishes.
            max_dur = max([shot.events[-1].time for shot in multisystem])

            # FIXME `leading_buffer` should be utilized here to sync up all shots that
            # have cue trajectories such that the ball animations all start at the
            # moment of the stick-ball collision
            pass

            for shot in multisystem:
                shot_dur = shot.events[-1].time
                shot.render_obj.init_shot_animation(
                    shot,
                    trailing_buffer=max_dur - shot_dur,
                    leading_buffer=0,
                )
                self.shot_animation.append(shot.render_obj.shot_animation)
        else:
            if not multisystem.active:
                raise ConfigError(
                    "MultiSystemRender.set_animation :: multisystem.active not set"
                )
            multisystem.active.render_obj.init_shot_animation(multisystem.active)
            self.shot_animation = multisystem.active.render_obj.shot_animation

    def start_animation(self, playback_mode: PlaybackMode):
        if playback_mode == PlaybackMode.SINGLE:
            self.shot_animation.start()
        elif playback_mode == PlaybackMode.LOOP:
            self.shot_animation.loop()

    def skip_stroke(self, multisystem):
        stroke = multisystem.active.render_obj.stroke_animation
        if stroke is not None:
            self.shot_animation.set_t(stroke.get_duration())

    def restart_animation(self):
        self.shot_animation.set_t(0)

    def clear_animation(self, multisystem):
        if self.parallel:
            for shot in multisystem:
                shot.render_obj.clear_animation(shot)
        else:
            multisystem.active.render_obj.clear_animation(multisystem.active)

        if self.shot_animation is not None:
            self.shot_animation.clearToInitial()
            self.shot_animation.pause()
            self.shot_animation = None

    def toggle_parallel(self, multisystem):
        self.clear_animation(multisystem)

        if self.parallel:
            for shot in multisystem:
                shot.render_obj.teardown(shot)
            multisystem.active.render_obj.buildup(multisystem.active)
            self.parallel = False
            self.set_animation(multisystem)
        else:
            multisystem.active.render_obj.teardown(multisystem.active)
            for shot in multisystem:
                shot.render_obj.buildup(shot)
            self.parallel = True
            self.set_animation(multisystem)

        if not self.paused:
            self.start_animation(PlaybackMode.LOOP)

    def toggle_pause(self):
        if self.shot_animation.isPlaying():
            self.pause_animation()
        else:
            self.resume_animation()

    def pause_animation(self):
        self.paused = True
        self.shot_animation.pause()

    def resume_animation(self):
        self.paused = False
        self.shot_animation.resume()

    def slow_down(self, multisystem):
        self.change_speed(0.5, multisystem)

    def speed_up(self, multisystem):
        self.change_speed(2.0, multisystem)

    def change_speed(self, factor, multisystem):
        # FIXME This messes up the syncing of shots when self.parallel is True. One
        # clear issue is that trailing_buffer times do not respect self.playback_speed.
        self.playback_speed *= factor
        for shot in multisystem:
            shot.render_obj.playback_speed *= factor

            # Reset the continuous ball history
            for ball in shot.balls.values():
                ball.history_cts = BallHistory()

        curr_time = self.shot_animation.get_t()
        self.clear_animation(multisystem)
        self.set_animation(multisystem)
        self.shot_animation.setPlayRate(factor * self.shot_animation.getPlayRate())

        if not self.paused:
            self.start_animation(PlaybackMode.LOOP)

        self.shot_animation.set_t(curr_time / factor)

    def rewind(self):
        self.offset_time(-ani.rewind_dt)

    def fast_forward(self):
        self.offset_time(ani.fast_forward_dt)

    def offset_time(self, dt):
        old_t = self.shot_animation.get_t()
        new_t = max(0, min(old_t + dt, self.shot_animation.duration))
        self.shot_animation.set_t(new_t)

    def highlight_system(self, i, multisystem):
        for system in multisystem:
            for ball in system.balls.values():
                ball.render_obj.set_alpha(1 / len(multisystem))

        for ball in multisystem[i].balls.values():
            ball.render_obj.set_alpha(1.0)
