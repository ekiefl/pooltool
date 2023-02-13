#! /usr/bin/env python

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np
from direct.interval.IntervalGlobal import (
    LerpFunc,
    LerpPosInterval,
    LerpPosQuatInterval,
    Parallel,
    Sequence,
)
from numpy.typing import NDArray
from panda3d.core import (
    CollisionCapsule,
    CollisionNode,
    LineSegs,
    SamplerState,
    TransparencyAttrib,
)

import pooltool.ani as ani
import pooltool.ani.utils as autils
import pooltool.constants as c
import pooltool.events as events
import pooltool.physics as physics
import pooltool.utils as utils
from pooltool.ani.globals import Global
from pooltool.error import ConfigError
from pooltool.events import Event, Events
from pooltool.objects import Render
from pooltool.utils import panda_path


class BallRender(Render):
    def __init__(self, R, rel_model_path=None):
        self.rel_model_path = rel_model_path
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

        if self.rel_model_path is None:
            fallback_path = ani.model_dir / "balls" / "set_1" / "1.glb"
            expected_path = ani.model_dir / "balls" / "set_1" / f"{ball.id}.glb"
            path = expected_path if expected_path.exists() else fallback_path

            sphere_node = Global.loader.loadModel(panda_path(path))
            sphere_node.reparentTo(position)

            if path == fallback_path:
                tex = sphere_node.find_texture(Path(fallback_path).stem)
            else:
                tex = sphere_node.find_texture(ball.id)

            # Here, we define self.rel_model_path based on path. Since rel_model_path is
            # defined relative to the directory, pooltool/models/balls, some work has to
            # be done to define rel_model_path relative to this directory. NOTE assumes
            # no child directory is named balls
            parents = []
            parent = path.parent
            while True:
                if parent.stem == "balls":
                    self.rel_model_path = Path("/".join(parents[::-1])) / path.name
                    break
                parents.append(parent.stem)
                parent = parent.parent
        else:
            sphere_node = Global.loader.loadModel(
                panda_path(ani.model_dir / "balls" / self.rel_model_path)
            )
            sphere_node.reparentTo(position)
            tex = sphere_node.find_texture(Path(self.rel_model_path).stem)

        # https://discourse.panda3d.org/t/visual-artifact-at-poles-of-uv-sphere-gltf-format/27975/8
        tex.set_minfilter(SamplerState.FT_linear)

        sphere_node.setScale(self.get_scale_factor(sphere_node, ball))
        position.setPos(*ball.rvw[0, :])

        self.nodes["sphere"] = sphere_node
        self.nodes["ball"] = ball_node
        self.nodes["pos"] = position
        self.nodes["shadow"] = self.init_shadow(ball)

        if ball.initial_orientation:
            # This ball already has a defined initial orientation, so load it up
            self.set_orientation(ball.initial_orientation)
        else:
            self.randomize_orientation()

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
        shadow_node.setPos(ball.rvw[0, 0], ball.rvw[0, 1], 0)

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

        rvw, _, _ = ball_history.get_state(i)
        quat = self.quats[i] if self.quats is not None else None
        self.set_render_state(rvw[0], quat)

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
        return {
            "pos": [x for x in self.nodes["pos"].getQuat()],
            "sphere": [x for x in self.nodes["sphere"].getQuat()],
        }

    def get_final_orientation(self):
        """Get the ball's quaternions of the final state in the history"""
        return {
            "pos": [x for x in self.quats[-1]],
            "sphere": [x for x in self.nodes["sphere"].getQuat()],
        }

    def set_orientation(self, orientation):
        """Set the orientation of a ball's rendered state from an orientation dict

        Parameters
        ==========
        orientation : dict
            A dictionary of quaternions with keys 'pos' and 'sphere'. Such a dictionary
            can be generated with `self.get_orientation`.
        """
        self.get_node("pos").setQuat(autils.get_quat_from_vector(orientation["pos"]))
        self.get_node("sphere").setQuat(
            autils.get_quat_from_vector(orientation["sphere"])
        )

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


@dataclass
class BallHistory:
    rvw: List[NDArray[np.float64]] = field(default_factory=list)
    s: List[float] = field(default_factory=list)
    t: List[float] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not bool(len(self.rvw))

    def get_state(self, i: int):
        """Get state based on history index

        Returns
        =======
        out : (rvw, s, t)
        """
        return self.rvw[i], self.s[i], self.t[i]

    def add(self, rvw: NDArray[np.float64], s: float, t: float):
        self.rvw.append(rvw)
        self.s.append(s)
        self.t.append(t)

    def vectorize(self):
        """Return all list objects in self.history as array objects"""
        return np.array(self.rvw), np.array(self.s), np.array(self.t)


class Ball:
    def __init__(
        self,
        ball_id,
        m=None,
        R=None,
        u_s=None,
        u_r=None,
        u_sp=None,
        g=None,
        e_c=None,
        f_c=None,
        rel_model_path=None,
        xyz=None,
        initial_orientation=None,
    ):
        """Initialize a ball

        Parameters
        ==========
        rel_model_path : str
            path should be relative to pooltool/models/balls directory
        """
        self.id = ball_id

        if not (isinstance(self.id, int) or isinstance(self.id, str)):
            raise ConfigError("ball_id must be integer or string")

        # physical properties
        self.m = m or c.m
        self.R = R or c.R
        self.I = 2 / 5 * self.m * self.R**2
        self.g = g or c.g

        # felt properties
        self.u_s = u_s or c.u_s
        self.u_r = u_r or c.u_r
        self.u_sp = u_sp or c.u_sp

        # restitution properties
        self.e_c = e_c or c.e_c
        self.f_c = f_c or c.f_c

        self.t = 0
        self.s = c.stationary

        if xyz is None:
            x, y, z = (np.nan, np.nan, np.nan)
        elif len(xyz) == 3:
            x, y, z = xyz
        elif len(xyz) == 2:
            x, y = xyz
            z = self.R

        self.rvw = np.array([[x, y, z], [0, 0, 0], [0, 0, 0]])
        self.update_next_transition_event()

        self.history = BallHistory()
        self.history_cts = BallHistory()

        self.events = Events()

        if initial_orientation is None:
            self.initial_orientation = self.get_random_orientation()

        self.rel_model_path = rel_model_path
        self.render_obj = BallRender(R=self.R, rel_model_path=self.rel_model_path)

    def set_object_state_as_render_state(self):
        """Set the object position based on the rendered position"""
        self.rvw[0] = self.render_obj.get_render_state()

    def set_render_state_as_object_state(self):
        """Set rendered position based on the object's position (self.rvw[0,:])"""
        pos = self.rvw[0]
        self.render_obj.set_render_state(pos)

    def update_history(self, event):
        self.history.add(np.copy(self.rvw), self.s, event.time)
        self.events.append(event)

    def init_history(self):
        self.update_history(events.null_event(time=0))

    def update_next_transition_event(self):
        if self.s == c.stationary or self.s == c.pocketed:
            self.next_transition_event = events.null_event(time=np.inf)

        elif self.s == c.spinning:
            dtau_E = physics.get_spin_time_fast(self.rvw, self.R, self.u_sp, self.g)
            self.next_transition_event = events.spinning_stationary_transition(
                self, self.t + dtau_E
            )

        elif self.s == c.rolling:
            dtau_E_spin = physics.get_spin_time_fast(
                self.rvw, self.R, self.u_sp, self.g
            )
            dtau_E_roll = physics.get_roll_time_fast(self.rvw, self.u_r, self.g)

            if dtau_E_spin > dtau_E_roll:
                self.next_transition_event = events.rolling_spinning_transition(
                    self, self.t + dtau_E_roll
                )
            else:
                self.next_transition_event = events.rolling_stationary_transition(
                    self, self.t + dtau_E_roll
                )

        elif self.s == c.sliding:
            dtau_E = physics.get_slide_time_fast(self.rvw, self.R, self.u_s, self.g)
            self.next_transition_event = events.sliding_rolling_transition(
                self, self.t + dtau_E
            )

        else:
            raise NotImplementedError(
                f"State '{self.s}' not implemented for object Ball"
            )

    def __repr__(self):
        lines = [
            f"<{self.__class__.__name__} object at {hex(id(self))}>",
            f" ├── id       : {self.id}",
            f" ├── state    : {self.s}",
            f" ├── position : {self.rvw[0]}",
            f" ├── velocity : {self.rvw[1]}",
            f" └── angular  : {self.rvw[2]}",
        ]

        return "\n".join(lines) + "\n"

    def set(self, rvw, s=None, t=None):
        self.rvw = rvw
        if s is not None:
            self.s = s
        if t is not None:
            self.t = t

    def set_from_history(self, i):
        """Set the ball state according to a history index"""
        self.set(*self.history.get_state(i))

    def set_time(self, t):
        self.t = t

    def get_random_orientation(self):
        quat1 = [1, 0, 0, 0]
        quat2 = 2 * np.random.rand(4) - 1
        quat2 /= np.linalg.norm(quat2)
        return {"pos": quat1, "sphere": list(quat2)}

    def as_dict(self):
        """Return a pickle-able dictionary of the ball"""
        return dict(
            id=self.id,
            m=self.m,
            R=self.R,
            I=self.I,
            g=self.g,
            u_s=self.u_s,
            u_r=self.u_r,
            u_sp=self.u_sp,
            s=self.s,
            t=self.t,
            rvw=np.copy(self.rvw),
            rel_model_path=None
            if self.rel_model_path is None
            else str(self.rel_model_path),
            history=dict(
                rvw=self.history.rvw,
                s=self.history.s,
                t=self.history.t,
            ),
            history_cts=dict(
                rvw=self.history_cts.rvw,
                s=self.history_cts.s,
                t=self.history_cts.t,
            ),
            events=self.events.as_dict(),
            initial_orientation=self.initial_orientation,
        )

    def save(self, path):
        utils.save_pickle(self.as_dict(), path)

    def render(self):
        self.render_obj.render(self)
        self.initial_orientation = self.render_obj.get_orientation()


def ball_from_dict(d):
    """Return a ball object from a dictionary

    For dictionary form see return value of Ball.as_dict
    """

    try:
        ball = Ball(
            d["id"],
            rel_model_path=d["rel_model_path"],
            initial_orientation=d["initial_orientation"],
        )
    except Exception:
        ball = Ball(
            d["id"],
            rel_model_path=d["rel_model_path"],
        )
    ball.m = d["m"]
    ball.R = d["R"]
    ball.I = d["I"]
    ball.g = d["g"]
    ball.u_s = d["u_s"]
    ball.u_r = d["u_r"]
    ball.u_sp = d["u_sp"]
    ball.s = d["s"]
    ball.t = d["t"]
    ball.rvw = d["rvw"]

    ball_history = BallHistory()
    ball_history.rvw = d["history"]["rvw"]
    ball_history.s = d["history"]["s"]
    ball_history.t = d["history"]["t"]
    ball.history = ball_history

    ball_history_cts = BallHistory()
    ball_history_cts.rvw = d.get("history_cts", {}).get("rvw")
    ball_history_cts.s = d.get("history_cts", {}).get("s")
    ball_history_cts.t = d.get("history_cts", {}).get("t")
    ball.history_cts = ball_history_cts

    events = Events()
    for event_dict in d["events"]:
        events.append(Event.from_dict(event_dict))
    ball.events = events

    ball.initial_orientation = d.get("initial_orientation", None)

    return ball


def ball_from_pickle(path):
    d = utils.load_pickle(path)
    return ball_from_dict(d)
