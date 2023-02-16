#! /usr/bin/env python

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
from direct.interval.IntervalGlobal import LerpPosInterval, Sequence
from panda3d.core import (
    ClockObject,
    CollisionHandlerQueue,
    CollisionNode,
    CollisionSegment,
    CollisionTraverser,
    Vec3,
)

import pooltool.ani as ani
import pooltool.events as events
import pooltool.utils as utils
from pooltool.ani.globals import Global
from pooltool.error import ConfigError, StrokeError
from pooltool.objects import Render


@dataclass
class CueSpecs:
    brand: str = field(default="Predator")
    M: float = field(default=0.567)  # 20oz
    length: float = field(default=1.4732)  # 58in
    tip_radius: float = field(default=0.007)  # 14mm tip
    butt_radius: float = field(default=0.02)

    @staticmethod
    def default() -> CueSpecs:
        return CueSpecs()


class CueRender(Render):
    def __init__(self):
        Render.__init__(self)

        self.follow = None
        self.stroke_sequence = None
        self.stroke_clock = ClockObject()
        self.has_focus = False

        self.stroke_pos = []
        self.stroke_time = []

    def init_model(self):
        path = utils.panda_path(ani.model_dir / "cue" / "cue.glb")
        cue_stick_model = Global.loader.loadModel(path)
        cue_stick_model.setName("cue_stick_model")

        cue_stick = Global.render.find("scene").find("table").attachNewNode("cue_stick")
        cue_stick_model.reparentTo(cue_stick)

        self.nodes["cue_stick"] = cue_stick
        self.nodes["cue_stick_model"] = cue_stick_model

    def init_focus(self, ball):
        self.follow = ball

        self.get_node("cue_stick_model").setPos(ball.params.R, 0, 0)

        cue_stick_focus = (
            Global.render.find("scene").find("table").attachNewNode("cue_stick_focus")
        )
        self.nodes["cue_stick_focus"] = cue_stick_focus

        self.match_ball_position()
        self.get_node("cue_stick").reparentTo(cue_stick_focus)

        self.has_focus = True

    def init_collision_handling(self, collision_handler):
        if not ani.settings["gameplay"]["cue_collision"]:
            return

        if not self.rendered:
            raise ConfigError(
                "Cue.init_collision_handling :: Cue has not been rendered, "
                "so collision handling cannot be initialized."
            )

        bounds = self.get_node("cue_stick").get_tight_bounds()

        x = 0
        X = bounds[1][0] - bounds[0][0]

        cnode = CollisionNode("cue_cseg")
        cnode.set_into_collide_mask(0)
        collision_node = self.get_node("cue_stick_model").attachNewNode(cnode)
        collision_node.node().addSolid(CollisionSegment(x, 0, 0, X, 0, 0))

        self.nodes["cue_cseg"] = collision_node
        Global.base.cTrav.addCollider(collision_node, collision_handler)

        if ani.settings["graphics"]["debug"]:
            collision_node.show()

    def get_length(self):
        bounds = self.get_node("cue_stick").get_tight_bounds()
        return bounds[1][0] - bounds[0][0]

    def track_stroke(self):
        """Initialize variables for storing cue position during stroke"""
        self.stroke_pos = []
        self.stroke_time = []
        self.stroke_clock.reset()

    def append_stroke_data(self):
        """Append current cue position and timestamp to the cue tracking data"""
        self.stroke_pos.append(self.get_node("cue_stick").getX())
        self.stroke_time.append(self.stroke_clock.getRealTime())

    def set_stroke_sequence(self):
        """Init a stroke sequence based off of self.stroke_pos and self.stroke_time"""

        cue_stick = self.get_node("cue_stick")
        self.stroke_sequence = Sequence()

        # If the stroke is longer than max_time seconds, truncate to max_time
        max_time = 1.0
        backstroke_time, apex_time, strike_time = self.get_stroke_times()
        if strike_time > max_time:
            idx = min(
                range(len(self.stroke_pos)),
                key=lambda i: abs(self.stroke_pos[i] - (strike_time - max_time)),
            )
            self.stroke_pos = self.stroke_pos[idx:]
            self.stroke_time = self.stroke_time[idx:]

        xs = np.array(self.stroke_pos)
        dts = np.diff(np.array(self.stroke_time))

        y, z = cue_stick.getY(), cue_stick.getZ()

        for i in range(len(dts)):
            self.stroke_sequence.append(
                LerpPosInterval(
                    nodePath=cue_stick, duration=dts[i], pos=Vec3(xs[i + 1], y, z)
                )
            )

    def get_stroke_times(self, as_index=False):
        """Get key moments in the trajectory of the stroke

        Parameters
        ==========
        as_index : bool, False
            See Returns

        Returns
        =======
        output : (backstroke, apex, strike)
            Returns a 3-ple of times (or indices of the lists self.stroke_time and
            self.stroke_pos if as_index is True) that describe three critical moments in
            the cue stick. backstroke is start of the backswing, apex is when the cue is
            at the peak of the backswing, and strike is when the cue makes contact.
        """
        if not len(self.stroke_pos):
            return 0, 0, 0

        apex_pos = 0
        for i, pos in enumerate(self.stroke_pos[::-1]):
            if pos < apex_pos:
                break
            apex_pos = pos

        apex_index = len(self.stroke_pos) - i
        while True:
            if apex_pos == self.stroke_pos[apex_index + 1]:
                apex_index += 1
            else:
                break
        apex_time = self.stroke_time[apex_index]

        backstroke_pos = apex_pos
        for j, pos in enumerate(self.stroke_pos[::-1][i:]):
            if pos > backstroke_pos:
                break
            backstroke_pos = pos
        backstroke_index = len(self.stroke_pos) - (i + j)
        while True:
            if backstroke_pos == self.stroke_pos[backstroke_index + 1]:
                backstroke_index += 1
            else:
                break
        backstroke_time = self.stroke_time[backstroke_index]

        strike_time = self.stroke_time[-1]
        strike_index = len(self.stroke_time) - 1

        return (
            (backstroke_index, apex_index, strike_index)
            if as_index
            else (backstroke_time, apex_time, strike_time)
        )

    def is_shot(self):
        if len(self.stroke_time) < 10:
            # There is only a handful of frames
            return False

        if not any([x > 0 for x in self.stroke_pos]):
            # No backstroke
            return False

        backstroke_time, apex_time, strike_time = self.get_stroke_times()

        if (strike_time - backstroke_time) < 0.3:
            # Stroke is too short
            return False

        return True

    def calc_V0_from_stroke(self):
        """Calculates V0 from the stroke sequence

        Takes the average velocity calculated over the 0.1 seconds preceding the shot.
        If the time between the cue strike and apex of the stroke is less than 0.1
        seconds, calculate the average velocity since the apex
        """

        try:
            backstroke_time, apex_time, strike_time = self.get_stroke_times()
        except IndexError:
            raise StrokeError("Unresolved edge case")

        max_time = 0.1
        if (strike_time - apex_time) < max_time:
            raise StrokeError("Unresolved edge case")

        for i, t in enumerate(self.stroke_time[::-1]):
            if strike_time - t > max_time:
                return self.stroke_pos[::-1][i] / max_time

    def match_ball_position(self):
        """Update the cue stick's position to match the cueing ball's position"""
        self.get_node("cue_stick_focus").setPos(
            self.follow.render_obj.get_node("pos").getPos()
        )

    def get_render_state(self):
        """Return phi, theta, V0, a, and b as determined by the cue_stick node"""

        cue_stick = self.get_node("cue_stick")
        cue_stick_focus = self.get_node("cue_stick_focus")

        phi = (cue_stick_focus.getH() + 180) % 360

        try:
            V0 = self.calc_V0_from_stroke()
        except StrokeError:
            V0 = 0.1

        cueing_ball = self.follow
        theta = -cue_stick_focus.getR()
        a = -cue_stick.getY() / self.follow.params.R
        b = cue_stick.getZ() / self.follow.params.R

        return V0, phi, theta, a, b, cueing_ball

    def render(self):
        super().render()
        self.init_model()


@dataclass
class Cue:
    id: str = field(default="cue_stick")

    V0: float = field(default=2.0)
    phi: float = field(default=0.0)
    theta: float = field(default=0.0)
    a: float = field(default=0.0)
    b: float = field(default=0.25)
    cueing_ball: Optional[Any] = field(default=None)

    specs: CueSpecs = field(default_factory=CueSpecs.default)

    render_obj: CueRender = field(init=False, default=CueRender())

    def reset_state(self):
        """Reset V0, phi, theta, a and b to their defaults"""
        field_defaults = {
            fname: field.default
            for fname, field in self.__dataclass_fields__.items()
            if fname in ("V0", "phi", "theta", "a", "b")
        }
        self.set_state(**field_defaults)

    def set_state(
        self, V0=None, phi=None, theta=None, a=None, b=None, cueing_ball=None
    ):
        """Set the cueing parameters

        Notes
        =====
        - If any parameters are None, they will be left untouched--they will not be set
          to None
        """

        if V0 is not None:
            self.V0 = V0
        if phi is not None:
            self.phi = phi
        if theta is not None:
            self.theta = theta
        if a is not None:
            self.a = a
        if b is not None:
            self.b = b
        if cueing_ball is not None:
            self.cueing_ball = cueing_ball

    def strike(self, t=None, **state_kwargs):
        """Strike the cue ball

        Parameters
        ==========
        t : float, None
            The time that the collision occurs at

        state_kwargs: **kwargs
            Pass state parameters to be updated before the cue strike. Any parameters
            accepted by Cue.set_state are permissible.
        """
        self.set_state(**state_kwargs)

        assert self.cueing_ball

        event = events.stick_ball_collision(self, self.cueing_ball, t)
        event.resolve()

        return event

    def aim_at_pos(self, pos):
        """Set phi to aim at a 3D position

        Parameters
        ==========
        pos : array-like
            A length-3 iterable specifying the x, y, z coordinates of the position to be
            aimed at
        """

        assert self.cueing_ball

        direction = utils.angle_fast(
            utils.unit_vector_fast(np.array(pos) - self.cueing_ball.state.rvw[0])
        )
        self.set_state(phi=direction * 180 / np.pi)

    def aim_at_ball(self, ball, cut=None):
        """Set phi to aim directly at a ball

        Parameters
        ==========
        ball : pooltool.objects.ball.Ball
            A ball
        cut : float, None
            The cut angle in degrees, within [-89, 89]
        """

        assert self.cueing_ball

        self.aim_at_pos(ball.state.rvw[0])

        if cut is None:
            return

        if cut > 89 or cut < -89:
            raise ConfigError(
                "Cue.aim_at_ball :: cut must be less than 89 and more than -89"
            )

        # Ok a cut angle has been requested. Unfortunately, there exists no analytical
        # function phi(cut), at least as far as I have been able to calculate. Instead,
        # it is a nasty transcendental equation that must be solved. The gaol is to make
        # its value 0. To do this, I sweep from 0 to the max possible angle with 100
        # values and find where the equation flips from positive to negative. The dphi
        # that makes the equation lies somewhere between those two values, so then I do
        # a new parameter sweep between the value that was positive and the value that
        # was negative. Then I rinse and repeat this a total of 5 times.

        left = True if cut < 0 else False
        cut = np.abs(cut) * np.pi / 180
        R = ball.params.R
        d = np.linalg.norm(ball.state.rvw[0] - self.cueing_ball.state.rvw[0])

        lower_bound = 0
        upper_bound = np.pi / 2 - np.arccos((2 * R) / d)

        for _ in range(5):
            dphis = np.linspace(lower_bound, upper_bound, 100)
            transcendental = (
                np.arctan(
                    2 * R * np.sin(cut - dphis) / (d - 2 * R * np.cos(cut - dphis))
                )
                - dphis
            )
            for i in range(len(transcendental)):
                if transcendental[i] < 0:
                    lower_bound = dphis[i - 1] if i > 0 else 0
                    upper_bound = dphis[i]
                    dphi = dphis[i]
                    break
            else:
                raise ConfigError(
                    "Cue.aim_at_ball :: Wow this should never happen. The algorithm "
                    "that finds the cut angle needs to be looked at again, because "
                    "the transcendental equation could not be solved."
                )

        self.phi = (self.phi + 180 / np.pi * (dphi if left else -dphi)) % 360

    def __repr__(self):
        lines = [
            f"<{self.__class__.__name__} object at {hex(id(self))}>",
            f" ├── V0    : {self.V0}",
            f" ├── phi   : {self.phi}",
            f" ├── a     : {self.a}",
            f" ├── b     : {self.b}",
            f" └── theta : {self.theta}",
        ]

        return "\n".join(lines) + "\n"

    def set_object_state_as_render_state(self, skip_V0=False):
        (
            V0,
            self.phi,
            self.theta,
            self.a,
            self.b,
            self.cueing_ball,
        ) = self.render_obj.get_render_state()

        if not skip_V0:
            self.V0 = V0

    def set_render_state_as_object_state(self):
        self.render_obj.match_ball_position()

        cue_stick = self.render_obj.get_node("cue_stick")
        cue_stick_focus = self.render_obj.get_node("cue_stick_focus")

        cue_stick_focus.setH(self.phi + 180)  # phi
        cue_stick_focus.setR(-self.theta)  # theta
        cue_stick.setY(-self.a * self.render_obj.follow.params.R)  # a
        cue_stick.setZ(self.b * self.render_obj.follow.params.R)  # b

    def as_dict(self):
        try:
            # It doesn't make sense to store a dictionary copy of the cueing_ball, since
            # building the ball from Ball.from_dict will lead to an object that is
            # unreferenced elsewhere.  Instead, I store the cueing_ball.id, if it
            # exists. This way, if a system state is loaded from dictionary, the balls
            # and cue can be built, and then set the cueing_ball can be directly set by
            # referencing the newly built Ball
            cueing_ball_id = self.cueing_ball.id
        except AttributeError:
            cueing_ball_id = None

        return dict(
            cue_id=self.id,
            M=self.M,
            length=self.length,
            tip_radius=self.tip_radius,
            butt_radius=self.butt_radius,
            brand=self.brand,
            V0=self.V0,
            phi=self.phi,
            theta=self.theta,
            a=self.a,
            b=self.b,
            cueing_ball_id=cueing_ball_id,
        )

    def save(self, path):
        utils.save_pickle(self.as_dict(), path)


class CueAvoid:
    def __init__(self):
        """Calculates min elevation required to avoid colliding with balls and cushions

        This class uses Panda3D collision detection to determine when the cue stick is
        intersecting with a ball or cushion. Rather than use the built in collision
        solving (e.g.
        https://docs.panda3d.org/1.10/python/reference/panda3d.core.CollisionHandlerPusher),
        which tended to push the cue off of objects in arbitrary ways (such that the cue
        no longer pointed at the cueing ball), I instead rely on geometry to solve the
        minimum angle that the cue stick must be raised in order to avoid all
        collisions. At each step in AimMode.aim_task, if the cue elevation is less than
        this angle, the elevation is automatically set to this minimum.

        Notes
        =====
        - This class has nothing to do with collisions that occur during the shot
          evolution, e.g.  ball-ball collisions, ball-cushion collisions, etc. All of
          those are handled in events.py
        """

        self.min_theta = 0

    def init_collisions(self):
        """Setup collision detection for cue stick

        Notes
        =====
        - NOTE this Panda3D collision handler is specifically for determining whether
          the cue stick is intersecting with cushions or balls. All other collisions
          discussed at
          https://ekiefl.github.io/2020/12/20/pooltool-alg/#2-what-are-events are
          unrelated to this.
        """

        if not ani.settings["gameplay"]["cue_collision"]:
            return

        Global.base.cTrav = CollisionTraverser()
        self.collision_handler = CollisionHandlerQueue()

        Global.system.cue.render_obj.init_collision_handling(self.collision_handler)
        for ball in Global.system.balls.values():
            ball.render_obj.init_collision(ball, Global.system.cue)

        # The stick needs a focus ball
        if not Global.system.cue.render_obj.has_focus:
            Global.system.cue.render_obj.init_focus(Global.system.cue.cueing_ball)

        # Declare frequently used nodes
        self.avoid_nodes = {
            "scene": Global.render.find("scene"),
            "cue_collision_node": Global.system.cue.render_obj.get_node("cue_cseg"),
            "cue_stick_model": Global.system.cue.render_obj.get_node("cue_stick_model"),
            "cue_stick": Global.system.cue.render_obj.get_node("cue_stick"),
            "cue_stick_focus": Global.system.cue.render_obj.get_node("cue_stick_focus"),
        }

    def collision_task(self, task):
        max_min_theta = 0

        # Lay cue collision segment flat
        self.avoid_nodes["cue_collision_node"].setR(
            -self.avoid_nodes["cue_stick_focus"].getR()
        )

        for entry in self.collision_handler.entries:
            min_theta = self.process_collision(entry)
            if min_theta > max_min_theta:
                max_min_theta = min_theta

        self.min_theta = max_min_theta
        return task.cont

    def process_collision(self, entry):
        if not entry.has_surface_point():
            # Not a collision we care about
            return 0
        elif entry.into_node.name.startswith("cushion"):
            return self.process_cushion_collision(entry)
        elif entry.into_node.name.startswith("ball"):
            return self.process_ball_collision(entry)
        else:
            raise NotImplementedError(
                f"CueAvoid :: no collision solver for node {entry.into_node.name}"
            )

    def process_cushion_collision(self, entry):
        cushion = self.get_cushion(entry)
        cushion_height = cushion.p1[2]

        # Point where cue center contacts collision plane
        Px, Py, Pz = entry.getSurfacePoint(self.avoid_nodes["scene"])

        # The tip of the cue stick
        Ex, Ey, Ez = self.avoid_nodes["cue_stick_model"].getPos(
            self.avoid_nodes["scene"]
        )

        # Center ofthe cueing ball
        Bx, By, Bz = self.avoid_nodes["cue_stick_focus"].getPos(
            self.avoid_nodes["scene"]
        )

        # The desired point where cue contacts collision plane, excluding cue width
        Dx, Dy, Dz = Px, Py, cushion_height

        # Center of aim
        v = np.array([Ex - Px, Ey - Py, Ez - Pz])
        u = utils.unit_vector_fast(v) * self.avoid_nodes["cue_stick_model"].getX()
        Fx, Fy, Fz = Ex + u[0], Ey + u[1], Ez + u[2]

        min_theta = np.arctan2(Dz - Fz, np.sqrt((Dx - Fx) ** 2 + (Dy - Fy) ** 2))

        # Correct for cue's cylindrical radius at collision point
        # distance from cue tip (E) to desired collision point (D)
        l = np.sqrt((Dx - Ex) ** 2 + (Dy - Ey) ** 2 + (Dz - Ez) ** 2)
        cue_radius = self.get_cue_radius(l)
        min_theta += np.arctan2(cue_radius, l)

        return max(0, min_theta) * 180 / np.pi

    def process_ball_collision(self, entry):
        min_theta = 0
        ball = self.get_ball(entry)

        if ball == Global.system.cue.cueing_ball:
            return 0

        scene = Global.render.find("scene")

        # Radius of transect
        n = np.array(entry.get_surface_normal(Global.render.find("scene")))
        phi = ((self.avoid_nodes["cue_stick_focus"].getH() + 180) % 360) * np.pi / 180
        c = np.array([np.cos(phi), np.sin(phi), 0])
        gamma = np.arccos(np.dot(n, c))
        AB = (ball.params.R + Global.system.cue.specs.tip_radius) * np.cos(gamma)

        # Center of blocking ball transect
        Ax, Ay, _ = entry.getSurfacePoint(scene)
        Ax -= (AB + Global.system.cue.specs.tip_radius) * np.cos(phi)
        Ay -= (AB + Global.system.cue.specs.tip_radius) * np.sin(phi)
        Az = ball.params.R

        # Center of aim, leveled to ball height
        Cx, Cy, Cz = self.avoid_nodes["cue_stick_focus"].getPos(scene)
        axR = -self.avoid_nodes["cue_stick"].getY()
        Cx += -axR * np.sin(phi)
        Cy += axR * np.cos(phi)

        AC = np.sqrt((Ax - Cx) ** 2 + (Ay - Cy) ** 2 + (Az - Cz) ** 2)
        BC = np.sqrt(AC**2 - AB**2)
        min_theta_no_english = np.arcsin(AB / AC)

        # Cue tip point, no top/bottom english
        m = self.avoid_nodes["cue_stick_model"].getX()
        u = utils.unit_vector_fast(
            np.array([-np.cos(phi), -np.sin(phi), np.sin(min_theta_no_english)])
        )
        Ex, Ey, Ez = Cx + m * u[0], Cy + m * u[1], Cz + m * u[2]

        # Point where cue contacts blocking ball, no top/bottom english
        Bx, By, Bz = Cx + BC * u[0], Cy + BC * u[1], Cz + BC * u[2]

        # Extra angle due to top/bottom english
        BE = np.sqrt((Bx - Ex) ** 2 + (By - Ey) ** 2 + (Bz - Ez) ** 2)
        bxR = self.avoid_nodes["cue_stick"].getZ()
        beta = -np.arctan2(bxR, BE)
        if beta < 0:
            beta += 10 * np.pi / 180 * (np.exp(bxR / BE) ** 2 - 1)

        min_theta = min_theta_no_english + beta
        return max(0, min_theta) * 180 / np.pi

    def get_cue_radius(self, l):
        """Returns cue radius at collision point, given point is distance l from tip"""

        bounds = Global.system.cue.render_obj.get_node("cue_stick").get_tight_bounds()
        L = bounds[1][0] - bounds[0][0]  # cue length

        r = Global.system.cue.specs.tip_radius
        R = Global.system.cue.specs.butt_radius

        m = (R - r) / L  # rise/run
        b = r  # intercept

        return m * l + b

    def get_cushion(self, entry):
        expected_suffix = "cushion_cplane_"
        into_node_path_name = entry.get_into_node_path().name
        assert into_node_path_name.startswith(expected_suffix)
        cushion_id = into_node_path_name[len(expected_suffix) :]
        return Global.system.table.cushion_segments["linear"][cushion_id]

    def get_ball(self, entry):
        expected_suffix = "ball_csphere_"
        into_node_path_name = entry.get_into_node_path().name
        assert into_node_path_name.startswith(expected_suffix)
        ball_id = into_node_path_name[len(expected_suffix) :]
        return Global.system.balls[ball_id]


cue_avoid = CueAvoid()


def cue_from_dict(d):
    cue = Cue(**{k: v for k, v in d.items() if k != "cueing_ball_id"})
    cue.cueing_ball_id = d["cueing_ball_id"]
    return cue


def cue_from_pickle(path):
    d = utils.load_pickle(path)
    return cue_from_dict(d)
