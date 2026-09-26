import os
from collections.abc import Callable, Iterator

import pytest
from direct.interval.IntervalGlobal import ivalMgr
from panda3d.core import ClockObject

from ani._helpers import DT
from pooltool.ani.animate import DEFAULT_FBF_CONFIG, Interface
from pooltool.ani.collision import cue_avoid
from pooltool.ani.globals import Global
from pooltool.ani.scene import SceneController, visual
from pooltool.evolution import simulate
from pooltool.system.datatypes import System, multisystem


@pytest.fixture
def advance() -> Iterator[Callable[[int], None]]:
    """Advance the interval manager by frames of ``DT`` seconds."""
    clock = ClockObject.get_global_clock()
    mode = clock.get_mode()
    clock.set_mode(ClockObject.M_non_real_time)
    clock.set_dt(DT)

    def _advance(frames: int) -> None:
        for _ in range(frames):
            clock.tick()
            ivalMgr.step()

    yield _advance

    clock.set_mode(mode)


@pytest.fixture(scope="session")
def interface() -> Interface:
    """An offscreen interface, made once because Panda3D allows one ShowBase per process.

    Skips the tests that need it in CI, whose runners have no GPU-backed offscreen
    pipe, and anywhere else the pipe can't be opened. CI skips before Panda3D tries to
    open anything, because a failed attempt hangs the Windows runners at exit.
    """
    if os.environ.get("CI"):
        pytest.skip("No offscreen graphics pipe in CI")

    try:
        interface = Interface(DEFAULT_FBF_CONFIG)
    except Exception as error:
        if str(error) != "Could not open window.":
            raise
        pytest.skip("No offscreen graphics pipe")

    Global.mode_mgr.update_event_baseline()
    return interface


@pytest.fixture(scope="session")
def shots() -> list[System]:
    shots = []
    for V0 in (1.5, 3.0):
        shot = System.example()
        shot.cue.set_state(V0=V0)
        simulate(shot, inplace=True)
        shots.append(shot)
    return shots


@pytest.fixture
def scene(interface: Interface, shots: list[System]) -> Iterator[SceneController]:
    """A scene of two simulated shots, with the mode manager idle and no mode entered."""
    multisystem.reset()
    for shot in shots:
        multisystem.append(shot.copy())
    interface.create_scene()
    cue_avoid.init_collisions()

    yield visual

    Global.mode_mgr.end_mode()
    interface.close_scene()
