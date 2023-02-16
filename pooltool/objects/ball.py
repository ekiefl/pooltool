#! /usr/bin/env python
from __future__ import annotations

from dataclasses import astuple, dataclass, field, replace
from pathlib import Path
from typing import Any, List, Tuple

import numpy as np
from direct.interval.IntervalGlobal import (
    LerpPosInterval,
    LerpPosQuatInterval,
    Parallel,
    Sequence,
)
from numpy.typing import NDArray
from panda3d.core import (
    CollisionCapsule,
    CollisionNode,
    SamplerState,
    TransparencyAttrib,
)

import pooltool.ani as ani
import pooltool.ani.utils as autils
import pooltool.constants as c
from pooltool.ani.globals import Global
from pooltool.error import ConfigError
from pooltool.objects import Render
from pooltool.utils import panda_path


@dataclass(frozen=True)
class BallOrientation:
    """Stores a ball's rendered orientation"""

    pos: List[float]
    sphere: List[float]

    @staticmethod
    def random() -> BallOrientation:
        return BallOrientation(
            pos=[1, 0, 0, 0],
            sphere=list((tmp := 2 * np.random.rand(4) - 1) / np.linalg.norm(tmp)),
        )


class BallRender(Render):
    def __init__(self, R):
        self.quats = None
        self.R = R
        self.playback_sequence = None
        Render.__init__(self)

    def init_sphere(self, ball):
        """Initialize the ball's nodes"""
        position = (
            Global.render.find("scene")
            .find("table")
            .attachNewNode(f"ball_{ball.id}_position")
        )
        ball_node = position.attachNewNode(f"ball_{ball.id}")

        fallback_path = ani.model_dir / "balls" / "set_1" / "1.glb"
        expected_path = ani.model_dir / "balls" / "set_1" / f"{ball.id}.glb"
        path = expected_path if expected_path.exists() else fallback_path

        sphere_node = Global.loader.loadModel(panda_path(path))
        sphere_node.reparentTo(position)

        if path == fallback_path:
            tex = sphere_node.find_texture(Path(fallback_path).stem)
        else:
            tex = sphere_node.find_texture(ball.id)

        # https://discourse.panda3d.org/t/visual-artifact-at-poles-of-uv-sphere-gltf-format/27975/8
        tex.set_minfilter(SamplerState.FT_linear)

        sphere_node.setScale(self.get_scale_factor(sphere_node, ball))
        position.setPos(*ball.state.rvw[0, :])

        self.nodes["sphere"] = sphere_node
        self.nodes["ball"] = ball_node
        self.nodes["pos"] = position
        self.nodes["shadow"] = self.init_shadow(ball)

        self.set_orientation(ball.initial_orientation)

    def init_collision(self, ball, cue):
        if not cue.render_obj.rendered:
            raise ConfigError("BallRender.init_collision :: `cue` must be rendered")

        collision_node = self.nodes["ball"].attachNewNode(
            CollisionNode(f"ball_csphere_{ball.id}")
        )
        collision_node.node().addSolid(
            CollisionCapsule(0, 0, -self.R, 0, 0, self.R, cue.specs.tip_radius + self.R)
        )
        if ani.settings["graphics"]["debug"]:
            collision_node.show()

        self.nodes[f"ball_csphere_{ball.id}"] = collision_node

    def init_shadow(self, ball):
        N = 20
        start, stop = 0.5, 0.9  # fraction of ball radius
        z_offset = 0.0005
        scales = np.linspace(start, stop, N)

        shadow_path = ani.model_dir / "balls" / "set_1" / "shadow.glb"
        shadow_node = (
            Global.render.find("scene").find("table").attachNewNode(f"shadow_{ball.id}")
        )
        shadow_node.setPos(ball.state.rvw[0, 0], ball.state.rvw[0, 1], 0)

        # allow transparency of shadow to change
        shadow_node.setTransparency(TransparencyAttrib.MAlpha)

        for i, scale in enumerate(scales):
            shadow_layer = Global.loader.loadModel(panda_path(shadow_path))
            shadow_layer.reparentTo(shadow_node)
            shadow_layer.setScale(self.get_scale_factor(shadow_layer, ball) * scale)
            shadow_layer.setZ(z_offset * (1 - i / N))

        return shadow_node

    def get_scale_factor(self, node, ball):
        """Find scale factor to match model size to ball's SI radius"""
        m, M = node.getTightBounds()
        model_R = (M - m)[0] / 2

        return self.R / model_R

    def get_render_state(self):
        """Return the position of the rendered ball"""
        x, y, z = self.nodes["pos"].getPos()
        return x, y, z

    def set_render_state(self, pos, quat=None):
        """Set the position (and quaternion) of the rendered ball

        Parameters
        ==========
        pos : length-3 iterable
        quat : length-4 iterable
        """

        self.nodes["pos"].setPos(*pos)
        self.nodes["shadow"].setPos(pos[0], pos[1], min(0, pos[2] - self.R))

        if quat is not None:
            self.nodes["pos"].setQuat(quat)

    def set_render_state_from_history(self, ball_history, i):
        """Set the position of the rendered ball based on history index

        Parameters
        ==========
        i : int
            An index from the history. e.g. 0 refers to initial state, -1 refers to
            final state
        """

        quat = self.quats[i] if self.quats is not None else None
        self.set_render_state(ball_history[i].rvw[0], quat)

    def set_quats(self, history):
        """Set self.quats based on history

        Quaternions are not calculated in the rvw state vector, so this method provides
        an opportunity to calculate all the quaternions from the ball's history
        """
        rvws, _, ts = history.vectorize()
        ws = rvws[:, 2, :]
        self.quats = autils.as_quaternion(ws, ts)

    def set_playback_sequence(self, ball, playback_speed=1):
        """Creates the motion sequences of the ball for a given playback speed"""
        rvws, motion_states, ts = ball.history_cts.vectorize()

        dts = np.diff(ts)
        playback_dts = dts / playback_speed

        # Get the trajectories
        xyzs = rvws[:, 0, :]
        ws = rvws[:, 2, :]

        if (xyzs == xyzs[0, :]).all() and (ws == ws[0, :]).all():
            # Ball has no motion. No need to create Lerp intervals
            self.playback_sequence = Sequence()
            self.quats = autils.as_quaternion(ws, ts)
            return

        xyzs = autils.get_list_of_Vec3s_from_array(xyzs)
        self.quats = autils.as_quaternion(ws, ts)

        # Init the animation sequences
        ball_sequence = Sequence()
        shadow_sequence = Sequence()

        self.set_render_state_from_history(ball.history_cts, 0)

        j = 0
        energetic = False
        for i in range(len(playback_dts)):
            x, y, z = xyzs[i]
            Qm, Qx, Qy, Qz = self.quats[i]

            if not energetic and motion_states[i] in c.energetic:
                # The ball wasn't energetic, but now it is
                energetic = True
                xi, yi, zi = xyzs[j]
                Qmi, Qxi, Qyi, Qzi = self.quats[j]
                dur = playback_dts[j:i].sum()

                ball_sequence.append(
                    LerpPosQuatInterval(
                        nodePath=self.nodes["pos"],
                        duration=dur,
                        startPos=(xi, yi, zi),
                        pos=(xi, yi, zi),
                        startQuat=(Qmi, Qxi, Qyi, Qzi),
                        quat=(Qmi, Qxi, Qyi, Qzi),
                    )
                )
                shadow_sequence.append(
                    LerpPosInterval(
                        nodePath=self.nodes["shadow"],
                        duration=dur,
                        startPos=(xi, yi, min(0, zi - self.R)),
                        pos=(xi, yi, min(0, zi - self.R)),
                    )
                )

            if energetic:
                ball_sequence.append(
                    LerpPosQuatInterval(
                        nodePath=self.nodes["pos"],
                        duration=playback_dts[i],
                        pos=(x, y, z),
                        quat=(Qm, Qx, Qy, Qz),
                    )
                )
                shadow_sequence.append(
                    LerpPosInterval(
                        nodePath=self.nodes["shadow"],
                        duration=playback_dts[i],
                        pos=(x, y, min(0, z - self.R)),
                    )
                )

                if motion_states[i] not in c.energetic:
                    # The ball was energetic, but now it is not
                    energetic = False
                    j = i

        self.playback_sequence = Parallel(
            ball_sequence,
            shadow_sequence,
        )

    def set_alpha(self, alpha):
        self.get_node("pos").setTransparency(TransparencyAttrib.MAlpha)
        self.get_node("pos").setAlphaScale(alpha)
        self.get_node("shadow").setAlphaScale(alpha)

    def randomize_orientation(self):
        self.get_node("sphere").setHpr(*np.random.uniform(-180, 180, size=3))

    def get_orientation(self):
        """Get the quaternions required to define the ball's rendered orientation"""
        return BallOrientation(
            pos=[x for x in self.nodes["pos"].getQuat()],
            sphere=[x for x in self.nodes["sphere"].getQuat()],
        )

    def get_final_orientation(self):
        """Get the ball's quaternions of the final state in the history"""
        return BallOrientation(
            pos=[x for x in self.quats[-1]],
            sphere=[x for x in self.nodes["sphere"].getQuat()],
        )

    def set_orientation(self, orientation: BallOrientation):
        """Set the orientation of a ball's rendered state from an orientation dict

        Parameters
        ==========
        orientation : dict
            A dictionary of quaternions with keys 'pos' and 'sphere'. Such a dictionary
            can be generated with `self.get_orientation`.
        """
        self.get_node("pos").setQuat(autils.get_quat_from_vector(orientation.pos))
        self.get_node("sphere").setQuat(autils.get_quat_from_vector(orientation.sphere))

    def reset_angular_integration(self):
        """Reset rotations applied to 'pos' while retaining rendered orientation"""
        ball, sphere = self.get_node("pos"), self.get_node("sphere")
        sphere.setQuat(sphere.getQuat() * ball.getQuat())

        ball.setHpr(0, 0, 0)

    def teardown(self):
        if self.playback_sequence is not None:
            self.playback_sequence.pause()
        self.remove_nodes()

    def render(self, ball):
        super().render()
        self.init_sphere(ball)


@dataclass(frozen=True)
class BallParams:
    """Pool ball parameters and physical constants

    Most of the default values are taken from or based off of
    https://billiards.colostate.edu/faq/physics/physical-properties/. All units are SI.
    Some of the parameters aren't truly _ball_ parameters, e.g. the gravitational
    constant, however it is nice to be able to tune such parameters on a ball-by-ball
    basis.

    Attributes:
        m:
            Mass.
        R:
            Radius.
        u_s:
            Coefficient of sliding friction.
        u_r:
            Coefficient of rolling friction.
        u_sp_proportionality:
            The coefficient of spinning friction is proportional ball radius. This is
            the proportionality constant. To obtain the coefficient of spinning
            friction, use the property `u_sp`.
        e_c:
            Cushion coefficient of restitution.
        f_c:
            Cushion coefficient of friction.
        g:
            Gravitational constant.
    """

    m: float = field(default=0.170097)
    R: float = field(default=0.028575)

    u_s: float = field(default=0.2)
    u_r: float = field(default=0.01)
    u_sp_proportionality: float = field(default=10 * 2 / 5 / 9)
    e_c: float = field(default=0.85)
    f_c: float = field(default=0.2)
    g: float = field(default=9.8)

    @property
    def u_sp(self) -> float:
        """Coefficient of spinning friction (radius dependent)"""
        return self.u_sp_proportionality * self.R

    @staticmethod
    def default() -> BallParams:
        return BallParams()


def _null_rvw() -> NDArray[np.float64]:
    return np.array([[np.nan, np.nan, np.nan], [0, 0, 0], [0, 0, 0]], dtype=np.float64)


def _array_safe_eq(a, b) -> bool:
    """Check if a and b are equal, even if they are numpy arrays"""
    if a is b:
        return True
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        return np.array_equal(a, b, equal_nan=True)
    try:
        return a == b
    except TypeError:
        return NotImplemented


def _are_dataclasses_equal(dc1, dc2) -> bool:
    """Check if two dataclasses which hold numpy arrays are equal"""
    if dc1 is dc2:
        return True
    if dc1.__class__ is not dc2.__class__:
        return NotImplemented  # better than False
    t1 = astuple(dc1)
    t2 = astuple(dc2)
    return all(_array_safe_eq(a1, a2) for a1, a2 in zip(t1, t2))


@dataclass(eq=False)
class BallState:
    rvw: NDArray[np.float64]
    s: float
    t: float

    def __eq__(self, other):
        return _are_dataclasses_equal(self, other)

    def set(self, rvw, s=None, t=None):
        self.rvw = rvw
        if s is not None:
            self.s = s
        if t is not None:
            self.t = t

    def copy(self):
        # Twice as fast as copy.deepcopy(self)
        return replace(self, rvw=np.copy(self.rvw))

    @staticmethod
    def default() -> BallState:
        return BallState(
            rvw=_null_rvw(),
            s=c.stationary,
            t=0,
        )


def _float64_array(x: Any) -> NDArray[np.float64]:
    return np.array(x, dtype=np.float64)


@dataclass
class BallHistory:
    states: List[BallState] = field(default_factory=list)

    def __getitem__(self, idx: int) -> BallState:
        return self.states[idx]

    @property
    def empty(self) -> bool:
        return not bool(len(self.states))

    def add(self, state: BallState) -> None:
        """Append a state to self.states"""
        new = state.copy()

        if not self.empty:
            assert new.t >= self.states[-1].t

        self.states.append(new)

    def vectorize(self) -> Tuple[NDArray, NDArray, NDArray]:
        """Return rvw, s, and t as arrays"""
        return tuple(  # type: ignore
            map(_float64_array, zip(*[astuple(x) for x in self.states]))
        )

    @staticmethod
    def factory() -> BallHistory:
        return BallHistory()


@dataclass
class Ball:
    """A pool ball"""

    id: str
    state: BallState = field(default_factory=BallState.default)
    params: BallParams = field(default_factory=BallParams.default)
    initial_orientation: BallOrientation = field(default_factory=BallOrientation.random)

    history: BallHistory = field(default_factory=BallHistory.factory)
    history_cts: BallHistory = field(default_factory=BallHistory.factory)

    render_obj: BallRender = field(init=False)

    def __post_init__(self):
        self.render_obj = BallRender(R=self.params.R)

    def set_object_state_as_render_state(self):
        """Set the object position based on the rendered position"""
        self.state.rvw[0] = self.render_obj.get_render_state()

    def set_render_state_as_object_state(self):
        """Set rendered position based on the object's position (self.state.rvw[0,:])"""
        pos = self.state.rvw[0]
        self.render_obj.set_render_state(pos)

    @staticmethod
    def create() -> Ball:
        """FIXME should allow parameters like xyz"""
        raise NotImplementedError()

    @staticmethod
    def dummy() -> Ball:
        return Ball(id="dummy")
