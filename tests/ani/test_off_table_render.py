from collections.abc import Callable, Iterator

import pytest

import pooltool.constants as const
from ani._helpers import DT
from pooltool.ani.animate import Interface
from pooltool.ani.collision import cue_avoid
from pooltool.ani.globals import Global
from pooltool.ani.off_table import FADE_START, TAIL_DURATION
from pooltool.ani.scene import PARALLEL_INACTIVE_ALPHA, SceneController, visual
from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based.simulate import simulate
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.physics.resolve.resolver import default_resolver_3d
from pooltool.system.datatypes import System, multisystem


def _flyaway_shot() -> System:
    """The cue ball is the only ball moving and it flies off the left side."""
    table = Table.default()
    ball = Ball.create("cue")
    ball.state.rvw[0] = [0.1, table.l / 4, ball.params.R + 0.2]
    ball.state.rvw[1] = [-2.0, 0.3, 1.0]
    ball.state.s = const.airborne

    shot = System(cue=Cue(cue_ball_id="cue"), table=table, balls=(ball,))
    engine = SimulationEngine(is_3d=True, resolver=default_resolver_3d())
    simulate(shot, engine=engine, inplace=True)
    return shot


@pytest.fixture
def flyaway_scene(interface: Interface) -> Iterator[SceneController]:
    multisystem.reset()
    multisystem.append(_flyaway_shot())
    interface.create_scene()
    cue_avoid.init_collisions()

    yield visual

    Global.mode_mgr.end_mode()
    interface.close_scene()


def _alpha(scene: SceneController) -> float:
    return scene.balls["cue"].get_node("pos").getColorScale()[3]


def test_playback_runs_to_the_end_of_the_tail(flyaway_scene: SceneController):
    flyaway_scene.build_shot_animation(animate_stroke=False)
    playback = flyaway_scene.playback
    assert playback is not None

    crossing = flyaway_scene.balls["cue"].left_table_at
    assert crossing is not None
    assert flyaway_scene.multisystem.active.events[-1].time == crossing
    assert playback.duration == pytest.approx(crossing + TAIL_DURATION, abs=0.02)


def test_ball_fades_after_leaving_and_reappears_on_rewind(
    flyaway_scene: SceneController,
):
    flyaway_scene.build_shot_animation(animate_stroke=False)
    playback = flyaway_scene.playback
    assert playback is not None
    crossing = flyaway_scene.balls["cue"].left_table_at
    assert crossing is not None

    playback.seek(crossing + FADE_START / 2)
    assert _alpha(flyaway_scene) == 1.0

    playback.seek(crossing + (FADE_START + TAIL_DURATION) / 2)
    assert 0.0 < _alpha(flyaway_scene) < 1.0

    playback.seek(playback.duration)
    assert _alpha(flyaway_scene) == 0.0

    playback.seek(0.0)
    assert _alpha(flyaway_scene) == 1.0


def test_looping_playback_comes_back_at_full_opacity(
    flyaway_scene: SceneController, advance: Callable[[int], None]
):
    flyaway_scene.build_shot_animation(animate_stroke=False)
    playback = flyaway_scene.playback
    assert playback is not None
    playback.loop = True
    playback.play()

    lowest_alpha = 1.0
    last_t = playback.t
    for _ in range(int(2 * playback.duration / DT)):
        advance(1)
        if playback.t < last_t:
            break
        last_t = playback.t
        lowest_alpha = min(lowest_alpha, _alpha(flyaway_scene))
    else:
        pytest.fail("Playback never wrapped")

    assert lowest_alpha < 0.5
    assert playback.t < FADE_START
    assert _alpha(flyaway_scene) == 1.0


def test_fade_scales_a_dimmed_ball(flyaway_scene: SceneController):
    flyaway_scene.balls["cue"].set_alpha(PARALLEL_INACTIVE_ALPHA)
    flyaway_scene.build_shot_animation(animate_stroke=False)
    playback = flyaway_scene.playback
    assert playback is not None
    crossing = flyaway_scene.balls["cue"].left_table_at
    assert crossing is not None

    playback.seek(crossing + FADE_START / 2)
    assert _alpha(flyaway_scene) == pytest.approx(PARALLEL_INACTIVE_ALPHA, abs=1e-3)

    playback.seek(crossing + (FADE_START + TAIL_DURATION) / 2)
    assert _alpha(flyaway_scene) == pytest.approx(PARALLEL_INACTIVE_ALPHA / 2, abs=0.05)


def test_ball_that_starts_off_the_table_is_hidden(flyaway_scene: SceneController):
    finished = flyaway_scene.multisystem.active
    next_shot = finished.copy()
    next_shot.reset_history()
    assert next_shot.balls["cue"].state.s == const.off_table

    multisystem.append(next_shot)
    flyaway_scene.switch_rendered_system(multisystem.max_index)

    assert flyaway_scene.balls["cue"].get_node("pos").is_hidden()
    assert flyaway_scene.balls["cue"].get_node("shadow").is_hidden()
