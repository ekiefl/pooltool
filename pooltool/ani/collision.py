import numpy as np
from panda3d.core import CollisionHandlerQueue, CollisionTraverser

import pooltool.ani as ani
import pooltool.ptmath as ptmath
from pooltool.ani.globals import Global
from pooltool.system.datatypes import multisystem
from pooltool.system.render import visual


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

        visual.cue.init_collision_handling(self.collision_handler)
        for ball in visual.balls.values():
            ball.init_collision(multisystem.active.cue)

        # The stick needs a focus ball
        if not visual.cue.has_focus:
            ball_id = multisystem.active.cue.cue_ball_id
            visual.cue.init_focus(visual.balls[ball_id])

        # Declare frequently used nodes
        self.avoid_nodes = {
            "scene": Global.render.find("scene"),
            "cue_collision_node": visual.cue.get_node("cue_cseg"),
            "cue_stick_model": visual.cue.get_node("cue_stick_model"),
            "cue_stick": visual.cue.get_node("cue_stick"),
            "cue_stick_focus": visual.cue.get_node("cue_stick_focus"),
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
        u = ptmath.unit_vector(v) * self.avoid_nodes["cue_stick_model"].getX()
        Fx, Fy, Fz = Ex + u[0], Ey + u[1], Ez + u[2]

        min_theta = np.arctan2(Dz - Fz, np.sqrt((Dx - Fx) ** 2 + (Dy - Fy) ** 2))

        # Correct for cue's cylindrical radius at collision point
        # distance from cue tip (E) to desired collision point (D)
        ll = np.sqrt((Dx - Ex) ** 2 + (Dy - Ey) ** 2 + (Dz - Ez) ** 2)
        cue_radius = self.get_cue_radius(ll)
        min_theta += np.arctan2(cue_radius, ll)

        return max(0, min_theta) * 180 / np.pi

    def process_ball_collision(self, entry):
        min_theta = 0
        ball_id = self.get_ball_id(entry)

        if ball_id == multisystem.active.cue.cue_ball_id:
            return 0

        ball = multisystem.active.balls[ball_id]

        scene = Global.render.find("scene")

        # Radius of transect
        n = np.array(entry.get_surface_normal(Global.render.find("scene")))
        phi = ((self.avoid_nodes["cue_stick_focus"].getH() + 180) % 360) * np.pi / 180
        c = np.array([np.cos(phi), np.sin(phi), 0])
        gamma = np.arccos(np.dot(n, c))
        AB = (ball.params.R + multisystem.active.cue.specs.tip_radius) * np.cos(gamma)

        # Center of blocking ball transect
        Ax, Ay, _ = entry.getSurfacePoint(scene)
        Ax -= (AB + multisystem.active.cue.specs.tip_radius) * np.cos(phi)
        Ay -= (AB + multisystem.active.cue.specs.tip_radius) * np.sin(phi)
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
        u = ptmath.unit_vector(
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

    def get_cue_radius(self, length):
        """Returns cue radius at collision point, given point is distance l from tip"""

        bounds = visual.cue.get_node("cue_stick").get_tight_bounds()
        L = bounds[1][0] - bounds[0][0]  # cue length

        r = multisystem.active.cue.specs.tip_radius
        R = multisystem.active.cue.specs.butt_radius

        m = (R - r) / L  # rise/run
        b = r  # intercept

        return m * length + b

    def get_cushion(self, entry):
        expected_suffix = "cushion_cplane_"
        into_node_path_name = entry.get_into_node_path().name
        assert into_node_path_name.startswith(expected_suffix)
        cushion_id = into_node_path_name[len(expected_suffix) :]
        return multisystem.active.table.cushion_segments.linear[cushion_id]

    def get_ball_id(self, entry) -> str:
        expected_suffix = "ball_csphere_"
        into_node_path_name = entry.get_into_node_path().name
        assert into_node_path_name.startswith(expected_suffix)
        return into_node_path_name[len(expected_suffix) :]


cue_avoid = CueAvoid()
