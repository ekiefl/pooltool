from pathlib import Path
from typing import Tuple

import numpy as np
from direct.interval.IntervalGlobal import (
    LerpPosInterval,
    LerpPosQuatInterval,
    MetaInterval,
    Parallel,
    Sequence,
)
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
from pooltool.objects.ball.datatypes import Ball, BallHistory, BallOrientation
from pooltool.objects.ball.sets import get_ballset
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.datatypes import Render
from pooltool.utils import panda_path

FALLBACK_ID = "cue"
FALLBACK_BALLSET = get_ballset("pooltool_pocket")
FALLBACK_PATH = FALLBACK_BALLSET.ball_path(FALLBACK_ID)


class BallRender(Render):
    def __init__(self, ball: Ball):
        self._ball = ball
        self.quats: list = []
        Render.__init__(self)

    @property
    def model_path(self) -> Path:
        ballset = self._ball.ballset
        return (
            ballset.ball_path(self._ball.id) if ballset is not None else FALLBACK_PATH
        )

    def init_sphere(self):
        """Initialize the ball's nodes"""
        position = (
            Global.render.find("scene")
            .find("table")
            .attachNewNode(f"ball_{self._ball.id}_position")
        )
        ball_node = position.attachNewNode(f"ball_{self._ball.id}")

        sphere_node = Global.loader.loadModel(panda_path(self.model_path))
        sphere_node.reparentTo(position)

        if self._ball.ballset is None:
            tex = sphere_node.find_texture(FALLBACK_ID)
        else:
            tex = sphere_node.find_texture(self.model_path.stem)

        # https://discourse.panda3d.org/t/visual-artifact-at-poles-of-uv-sphere-gltf-format/27975/8
        tex.set_minfilter(SamplerState.FT_linear)

        sphere_node.setScale(self.get_scale_factor(sphere_node))
        position.setPos(*self._ball.state.rvw[0, :])

        self.nodes["sphere"] = sphere_node
        self.nodes["ball"] = ball_node
        self.nodes["pos"] = position
        self.nodes["shadow"] = self.init_shadow()

        self.set_orientation(self._ball.initial_orientation)

    def set_object_state_as_render_state(self, patch: bool = False):
        """Set the object position based on the rendered position

        NOTE:

        TL;DR The z-component of displacement is manually set to self._ball.params.R
        when `patch` is True

        This method contains an untruthful patch in order to prevent leaky float
        operations likely caused by an unavoidable mixup between single and double float
        precision:

        https://discourse.panda3d.org/t/precision-of-coordinates-in-panda3d/11247

        When the render state is fetched for a ball on the table, the z-component of the
        displacement should be exactly the ball's radius. However, the following
        assertion fails:

        >>> assert (diff := pos[2] - self._ball.params.R) == 0, f"{diff}"

        Propagated over several shots, dramatic z-drift is observed.

        The patch simply sets the object state z-component of displacement to the ball's
        radius. If this method is called with patch=True while the rendered ball is
        airborne, that would be very be problematic.
        """
        x, y, z = self.get_render_state()

        if patch:
            z = self._ball.params.R

        self._ball.state.rvw[0] = (x, y, z)

    def set_render_state_as_object_state(self):
        """Set rendered position based on the object's position (self.state.rvw[0,:])"""
        self.set_render_state(self._ball.state.rvw[0])

    def init_collision(self, cue: Cue):
        R = self._ball.params.R
        collision_node = self.nodes["ball"].attachNewNode(
            CollisionNode(f"ball_csphere_{self._ball.id}")
        )
        collision_node.node().addSolid(
            CollisionCapsule(0, 0, -R, 0, 0, R, cue.specs.tip_radius + R)
        )
        if ani.settings["graphics"]["debug"]:
            collision_node.show()

        self.nodes[f"ball_csphere_{self._ball.id}"] = collision_node

    def init_shadow(self):
        N = 20
        start, stop = 0.5, 0.9  # fraction of ball radius
        z_offset = 0.0005
        scales = np.linspace(start, stop, N)

        if (ballset := self._ball.ballset) is not None:
            shadow_path = ballset.ball_path("shadow")
        else:
            shadow_path = FALLBACK_BALLSET.ball_path("shadow")

        name = f"shadow_{self._ball.id}"
        shadow_node = Global.render.find("scene").find("table").attachNewNode(name)
        x, y, _ = self._ball.state.rvw[0]
        shadow_node.setPos(x, y, 0)

        # allow transparency of shadow to change
        shadow_node.setTransparency(TransparencyAttrib.MAlpha)

        for i, scale in enumerate(scales):
            shadow_layer = Global.loader.loadModel(panda_path(shadow_path))
            shadow_layer.reparentTo(shadow_node)
            shadow_layer.setScale(self.get_scale_factor(shadow_layer) * scale)
            shadow_layer.setZ(z_offset * (1 - i / N))

        return shadow_node

    def get_scale_factor(self, node) -> float:
        """Find scale factor to match model size to ball's SI radius"""
        m, M = node.getTightBounds()
        model_R = (M - m)[0] / 2

        return self._ball.params.R / model_R

    def get_render_state(self) -> Tuple[float, float, float]:
        """Return the position of the rendered ball"""
        x, y, z = self.nodes["pos"].getPos()
        return x, y, z

    def set_render_state(self, pos, quat=None) -> None:
        """Set the position (and quaternion) of the rendered ball

        Parameters
        ==========
        pos : length-3 iterable
        quat : length-4 iterable
        """

        self.nodes["pos"].setPos(*pos)
        self.nodes["shadow"].setPos(
            pos[0], pos[1], min(0, pos[2] - self._ball.params.R)
        )

        if quat is not None:
            self.nodes["pos"].setQuat(quat)

    def set_render_state_from_history(self, ball_history: BallHistory, i: int):
        """Set the position of the rendered ball based on history index

        Parameters
        ==========
        i : int
            An index from the history. e.g. 0 refers to initial state, -1 refers to
            final state
        """

        quat = self.quats[i] if len(self.quats) else None
        self.set_render_state(ball_history[i].rvw[0], quat)

    def set_quats(self, history):
        """Set self.quats based on history

        Quaternions are not calculated in the rvw state vector, so this method provides
        an opportunity to calculate all the quaternions from the ball's history
        """
        rvws, _, ts = history.vectorize()
        ws = rvws[:, 2, :]
        self.quats = autils.as_quaternion(ws, ts)

    def get_playback_sequence(self, playback_speed=1) -> MetaInterval:
        """Creates the motion sequences of the ball for a given playback speed"""
        vectors = self._ball.history_cts.vectorize()
        if vectors is None:
            return Sequence()

        rvws, motion_states, ts = vectors

        dts = np.diff(ts)
        playback_dts = dts / playback_speed

        # Get the trajectories
        xyzs = rvws[:, 0, :]
        ws = rvws[:, 2, :]

        if (xyzs == xyzs[0, :]).all() and (ws == ws[0, :]).all():
            # Ball has no motion. No need to create Lerp intervals
            self.quats = autils.as_quaternion(ws, ts)
            return Sequence()

        xyzs = autils.get_list_of_Vec3s_from_array(xyzs)
        self.quats = autils.as_quaternion(ws, ts)

        # Init the animation sequences
        ball_sequence = Sequence()
        shadow_sequence = Sequence()

        self.set_render_state_from_history(self._ball.history_cts, 0)

        j = 0
        energetic = False
        for i in range(len(playback_dts)):
            x, y, z = xyzs[i]
            Qm, Qx, Qy, Qz = self.quats[i]

            stationary_to_stationary = (
                not energetic
                and motion_states[i] not in c.energetic
                and motion_states[i] != motion_states[j]
            )

            if (
                stationary_to_energetic := not energetic
                and motion_states[i] in c.energetic
            ):
                # The ball wasn't energetic, but now it is
                energetic = True

            if stationary_to_energetic or stationary_to_stationary:
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
                        startPos=(xi, yi, min(0, zi - self._ball.params.R)),
                        pos=(xi, yi, min(0, zi - self._ball.params.R)),
                    )
                )

            if energetic or stationary_to_stationary:
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
                        pos=(x, y, min(0, z - self._ball.params.R)),
                    )
                )

                if motion_states[i] not in c.energetic:
                    energetic = False
                    j = i

        return Parallel(
            ball_sequence,
            shadow_sequence,
        )

    def set_alpha(self, alpha):
        self.get_node("pos").setTransparency(TransparencyAttrib.MAlpha)
        self.get_node("pos").setAlphaScale(alpha)
        self.get_node("shadow").setAlphaScale(alpha)

    def randomize_orientation(self):
        self.get_node("sphere").setHpr(*np.random.uniform(-180, 180, size=3))

    def get_orientation(self) -> BallOrientation:
        """Get the quaternions required to define the ball's rendered orientation"""
        return BallOrientation(
            pos=tuple([float(x) for x in self.nodes["pos"].getQuat()]),
            sphere=tuple([float(x) for x in self.nodes["sphere"].getQuat()]),
        )

    def get_final_orientation(self) -> BallOrientation:
        """Get the ball's quaternions of the final state in the history"""
        return BallOrientation(
            pos=tuple([float(x) for x in self.quats[-1]]),
            sphere=tuple([float(x) for x in self.nodes["sphere"].getQuat()]),
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

    def render(self):
        super().render()
        self.init_sphere()
