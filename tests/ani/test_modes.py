from collections.abc import Callable

import numpy as np
import pytest
from panda3d.core import PythonTask

import pooltool.ani.tasks as tasks
from pooltool.ani.action import Action
from pooltool.ani.globals import Global
from pooltool.ani.modes.datatypes import Mode
from pooltool.ani.modes.shot import ShotMode
from pooltool.ani.playback import PlaybackState
from pooltool.ani.scene import SceneController
from pooltool.objects.cue.render import StrokeRecording

STROKE_SECONDS = 0.6


def _record_stroke(scene: SceneController) -> None:
    """Record the stroke a player would have traced for the active shot."""
    positions = [0.0, 0.05, 0.1, 0.15, 0.2, 0.15, 0.1, 0.05, 0.0, -0.02]
    times = list(np.linspace(0, STROKE_SECONDS, len(positions)))
    scene.record_stroke(StrokeRecording(positions, times))


def _enter_shot_mode(**enter_kwargs) -> ShotMode:
    Global.mode_mgr.change_mode(Mode.shot, enter_kwargs=enter_kwargs)
    return Global.mode_mgr.modes[Mode.shot]


def test_taken_shot_plays_once_from_the_strike(
    scene: SceneController, advance: Callable[[int], None]
):
    _record_stroke(scene)
    mode = _enter_shot_mode(build_animations=True)
    advance(1)

    assert mode.playback.state is PlaybackState.PLAYING
    assert not mode.playback.loop
    assert mode.playback.t >= 0.0
    assert not scene.cue.visible


def test_viewed_shot_loops_from_the_start_of_the_stroke(
    scene: SceneController, advance: Callable[[int], None]
):
    _record_stroke(scene)
    mode = _enter_shot_mode(build_animations=True, loop=True)

    assert mode.playback.loop
    assert mode.playback.start == pytest.approx(-STROKE_SECONDS, abs=0.01)
    assert mode.playback.t == pytest.approx(mode.playback.start)

    advance(1)
    assert scene.cue.visible


def test_cue_hidden_by_a_mode_is_shown_by_the_replayed_stroke(
    scene: SceneController, advance: Callable[[int], None]
):
    Global.mode_mgr.change_mode(Mode.view)
    assert not scene.cue.visible

    _record_stroke(scene)
    mode = _enter_shot_mode(build_animations=True, loop=True)
    advance(1)
    assert scene.cue.visible

    mode.playback.seek(0.0)
    advance(1)
    assert not scene.cue.visible


def test_entering_without_building_keeps_the_playback(scene: SceneController):
    scene.switch_to_shot(1)
    playback = scene.playback
    assert playback is not None
    state = playback.state

    mode = _enter_shot_mode()

    assert mode.playback is playback
    assert mode.playback.state is state


def test_soft_exit_removes_the_tasks_and_keeps_the_playback(scene: SceneController):
    _enter_shot_mode(build_animations=True)
    assert tasks.has("shot_view_task")
    assert tasks.has("shot_animation_task")

    Global.mode_mgr.end_mode()

    assert not tasks.has("shot_view_task")
    assert not tasks.has("shot_animation_task")
    assert scene.playback is not None


def test_space_toggles_pause_and_arrows_change_speed(scene: SceneController):
    mode = _enter_shot_mode(build_animations=True)
    messenger = Global.base.messenger

    messenger.send("space")
    assert mode.playback.state is PlaybackState.PAUSED

    messenger.send("space")
    assert mode.playback.state is PlaybackState.PLAYING

    messenger.send("arrow_up")
    assert scene.playback_speed == 2.0
    assert mode.playback.loop

    messenger.send("arrow_down")
    assert scene.playback_speed == 1.0


def test_undo_returns_to_aim_with_the_shot_unsimulated_and_the_cue_shown(
    scene: SceneController,
):
    Global.mode_mgr.change_mode(Mode.aim)
    Global.mode_mgr.mode_stroked_from = Mode.aim
    _enter_shot_mode(build_animations=True)

    Global.mode_mgr.change_mode(
        Mode.aim, exit_kwargs={"key": "reset"}, enter_kwargs={"load_prev_cam": True}
    )

    assert scene.playback is None
    assert not scene.multisystem.active.simulated
    assert scene.cue.visible
    assert tasks.has("aim_task")


def test_view_mode_hides_the_cue_and_aim_mode_shows_it(scene: SceneController):
    Global.mode_mgr.change_mode(Mode.aim)
    assert scene.cue.visible
    assert tasks.has("aim_task")

    Global.mode_mgr.change_mode(Mode.view)
    assert not scene.cue.visible
    assert tasks.has("view_task")
    assert not tasks.has("aim_task")

    Global.mode_mgr.end_mode()
    assert not tasks.has("view_task")


def test_scrubbing_while_paused_moves_with_the_playback_speed(scene: SceneController):
    mode = _enter_shot_mode(build_animations=True)
    task = PythonTask(mode.shot_animation_task)
    messenger = Global.base.messenger

    messenger.send("space")
    t = mode.playback.t
    mode.keymap[Action.fast_forward] = True
    mode.shot_animation_task(task)
    full_speed_step = mode.playback.t - t
    assert full_speed_step > 0

    messenger.send("arrow_down")
    assert mode.playback.state is PlaybackState.PAUSED
    t = mode.playback.t
    mode.shot_animation_task(task)
    assert mode.playback.t - t == pytest.approx(full_speed_step / 2)

    mode.keymap[Action.fast_forward] = False
    mode.keymap[Action.rewind] = True
    mode.shot_animation_task(task)
    assert mode.playback.t == pytest.approx(t)


def test_recorded_stroke_replays_after_switching_shots(scene: SceneController):
    _record_stroke(scene)

    scene.switch_to_shot(1)
    assert scene.playback is not None
    assert scene.playback.start == 0.0

    scene.switch_to_shot(0)
    assert scene.playback is not None
    assert scene.playback.start == pytest.approx(-STROKE_SECONDS, abs=0.01)

    scene.playback.seek(scene.playback.start + 0.1)
    assert scene.cue.visible


def test_shot_taken_without_stroking_replays_without_a_stroke(scene: SceneController):
    _record_stroke(scene)
    scene.record_stroke(StrokeRecording())

    mode = _enter_shot_mode(build_animations=True, loop=True)

    assert mode.playback.start == 0.0


def test_replayed_cue_is_posed_at_its_shots_cue_ball(scene: SceneController):
    _record_stroke(scene)
    scene.switch_to_shot(1)
    scene.switch_to_shot(0)

    shot = scene.multisystem.active
    cue_ball = shot.balls[shot.cue.cue_ball_id]
    focus = scene.cue.get_node("cue_stick_focus")

    assert focus.getH() % 360 == pytest.approx((shot.cue.phi + 180) % 360)
    assert -focus.getR() == pytest.approx(shot.cue.theta)
    assert np.array(focus.getPos()) == pytest.approx(cue_ball.history[0].rvw[0])


def test_speed_change_while_playing_resumes_next_frame_at_the_same_time(
    scene: SceneController, advance: Callable[[int], None]
):
    scene.build_shot_animation()
    playback = scene.playback
    assert playback is not None
    playback.play()
    advance(3)
    t = playback.t

    scene.change_speed(2.0)
    rebuilt = scene.playback
    assert rebuilt is not None
    assert rebuilt.state is PlaybackState.PAUSED
    assert rebuilt.t == pytest.approx(t)

    for _ in range(2):
        Global.task_mgr.step()
        if rebuilt.state is PlaybackState.PLAYING:
            break
    assert rebuilt.state is PlaybackState.PLAYING
    assert rebuilt.t == pytest.approx(t)
