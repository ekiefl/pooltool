#! /usr/bin/env python

import pooltool.ani as ani
import pooltool.utils as utils

from pooltool.events import StickBallCollision
from pooltool.objects import *

import numpy as np

from pathlib import Path
from panda3d.core import *
from direct.interval.IntervalGlobal import *

class CueRender(Render):
    def __init__(self):
        Render.__init__(self)

        self.follow = None
        self.stroke_sequence = None
        self.stroke_clock = ClockObject()
        self.has_focus = False

        self.stroke_pos = []
        self.stroke_time = []


    def init_model(self, R=pooltool.R):
        path = utils.panda_path(ani.model_dir / 'cue' / 'cue.glb')
        cue_stick_model = loader.loadModel(path)
        cue_stick_model.setName('cue_stick_model')

        cue_stick = render.find('scene').find('cloth').attachNewNode('cue_stick')
        cue_stick_model.reparentTo(cue_stick)

        self.nodes['cue_stick'] = cue_stick
        self.nodes['cue_stick_model'] = cue_stick_model


    def init_focus(self, ball):
        self.follow = ball

        self.get_node('cue_stick_model').setPos(ball.R, 0, 0)

        cue_stick_focus = render.find('scene').find('cloth').attachNewNode("cue_stick_focus")
        self.nodes['cue_stick_focus'] = cue_stick_focus

        self.update_focus()
        self.get_node('cue_stick').reparentTo(cue_stick_focus)

        self.has_focus = True


    def init_collision_handling(self, collision_handler):
        if not ani.settings['gameplay']['cue_collision']:
            return

        if not self.rendered:
            raise ConfigError("Cue.init_collision_handling :: Cue has not been rendered, "
                              "so collision handling cannot be initialized.")

        bounds = self.get_node('cue_stick').get_tight_bounds()

        x = bounds[0][0]
        X = bounds[1][0]

        cnode = CollisionNode(f"cue_cseg")
        cnode.set_into_collide_mask(0)
        collision_node = self.get_node('cue_stick_model').attachNewNode(cnode)
        collision_node.node().addSolid(
            CollisionSegment(x, 0, 0, X, 0, 0)
        )

        if ani.settings['graphics']['debug']:
            collision_node.show()

        self.nodes['cue_cseg'] = collision_node
        base.cTrav.addCollider(collision_node, collision_handler)


    def get_length(self):
        bounds = self.get_node('cue_stick').get_tight_bounds()
        return bounds[1][0] - bounds[0][0]


    def track_stroke(self):
        """Initialize variables for storing cue position during stroke"""
        self.stroke_pos = []
        self.stroke_time = []
        self.stroke_clock.reset()


    def append_stroke_data(self):
        """Append current cue position and timestamp to the cue tracking data"""
        cue_stick = self.get_node('cue_stick')

        self.stroke_pos.append(self.get_node('cue_stick').getX())
        self.stroke_time.append(self.stroke_clock.getRealTime())


    def set_stroke_sequence(self):
        """Initiate a stroke sequence based off of self.stroke_pos and self.stroke_time"""

        cue_stick = self.get_node('cue_stick')
        self.stroke_sequence = Sequence()

        # If the stroke is longer than max_time seconds, truncate to max_time
        max_time = 1.0
        backstroke_time, apex_time, strike_time = self.get_stroke_times()
        if strike_time > max_time:
            idx = min(range(len(self.stroke_pos)), key=lambda i: abs(self.stroke_pos[i] - (strike_time - max_time)))
            self.stroke_pos = self.stroke_pos[idx:]
            self.stroke_time = self.stroke_time[idx:]

        xs = np.array(self.stroke_pos)
        dts = np.diff(np.array(self.stroke_time))

        y, z = cue_stick.getY(), cue_stick.getZ()

        for i in range(len(dts)):
            self.stroke_sequence.append(LerpPosInterval(
                nodePath = cue_stick,
                duration = dts[i],
                pos = Vec3(xs[i+1], y, z)
            ))


    def get_stroke_times(self, as_index=False):
        """Get key moments in the trajectory of the stroke

        Parameters
        ==========
        as_index : bool, False
            See Returns

        Returns
        =======
        output : (backstroke, apex, strike)
            Returns a 3-ple of times (or indices of the lists self.stroke_time and self.stroke_pos
            if as_index is True) that describe three critical moments in the cue stick. backstroke is
            start of the backswing, apex is when the cue is at the peak of the backswing, and strike is
            when the cue makes contact.
        """

        apex_pos = 0
        for i, pos in enumerate(self.stroke_pos[::-1]):
            if pos < apex_pos:
                break
            apex_pos = pos
        apex_index = len(self.stroke_pos) - i
        while True:
            if apex_pos == self.stroke_pos[apex_index+1]:
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
            if backstroke_pos == self.stroke_pos[backstroke_index+1]:
                backstroke_index += 1
            else:
                break
        backstroke_time = self.stroke_time[backstroke_index]

        strike_time = self.stroke_time[-1]
        strike_index = len(self.stroke_time) - 1

        return (backstroke_index, apex_index, strike_index) if as_index else (backstroke_time, apex_time, strike_time)


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

        Takes the average velocity calculated over the 0.1 seconds preceding the shot. If the time
        between the cue strike and apex of the stroke is less than 0.1 seconds, calculate the average
        velocity since the apex
        """

        backstroke_time, apex_time, strike_time = self.get_stroke_times()

        max_time = 0.1
        if (strike_time - apex_time) < max_time:
            return self.stroke_pos[apex_index]/apex_time

        for i, t in enumerate(self.stroke_time[::-1]):
            if strike_time - t > max_time:
                return self.stroke_pos[::-1][i] / max_time


    def update_focus(self):
        self.get_node('cue_stick_focus').setPos(self.follow.get_node('ball').getPos())


    def get_render_state(self):
        """Return phi, theta, V0, a, and b as determined by the cue_stick node"""

        cue_stick = self.get_node('cue_stick')
        cue_stick_focus = self.get_node('cue_stick_focus')

        phi = ((cue_stick_focus.getH() + 180) % 360)
        try:
            # FIXME short strokes give NameError: name 'apex_index' is not defined
            V0 = self.calc_V0_from_stroke()
        except:
            V0 = 1
        cueing_ball = self.follow
        theta = -cue_stick_focus.getR()
        a = -cue_stick.getY()/self.follow.R
        b = cue_stick.getZ()/self.follow.R

        return V0, phi, theta, a, b, cueing_ball


    def set_object_state_as_render_state(self):
        self.V0, self.phi, self.theta, self.a, self.b, self.cueing_ball = self.get_render_state()


    def set_render_state_as_object_state(self):
        self.update_focus()

        cue_stick = self.get_node('cue_stick')
        cue_stick_focus = self.get_node('cue_stick_focus')

        cue_stick_focus.setH(self.phi + 180) # phi
        cue_stick_focus.setR(-self.theta) # theta
        cue_stick.setY(-self.a * self.follow.R) # a
        cue_stick.setZ(self.b * self.follow.R) # b


    def render(self):
        super().render()
        self.init_model()


class Cue(Object, CueRender):
    object_type = 'cue_stick'

    def __init__(self, M=pooltool.M, length=pooltool.cue_length, tip_radius=pooltool.cue_tip_radius,
                 butt_radius=pooltool.cue_butt_radius, cue_id='cue_stick', brand=None):

        self.id = cue_id
        self.M = M
        self.length = length
        self.tip_radius = tip_radius
        self.butt_radius = butt_radius
        self.brand = brand

        self.V0 = None
        self.phi = None
        self.theta = None
        self.a = None
        self.b = None

        self.cueing_ball = None

        CueRender.__init__(self)


    def reset_state(self):
        self.set_state(V0=0, phi=0, theta=0, a=0, b=0)


    def set_state(self, V0=None, phi=None, theta=None, a=None, b=None, cueing_ball=None):
        """Set the cueing parameters

        Notes
        =====
        - If any parameters are None, they will be left untouched--they will not be set to None
        """

        if V0 is not None: self.V0 = V0
        if phi is not None: self.phi = phi
        if theta is not None: self.theta = theta
        if a is not None: self.a = a
        if b is not None: self.b = b
        if cueing_ball is not None: self.cueing_ball = cueing_ball


    def strike(self, t=None):
        if (self.V0 is None or self.phi is None or self.theta is None or self.a is None or self.b is None):
            raise ValueError("Cue.strike :: Must set V0, phi, theta, a, and b")

        event = StickBallCollision(self, self.cueing_ball, t=t)
        event.resolve()

        return event


    def aim_at(self, pos):
        """Set phi to aim at a 3D position

        Parameters
        ==========
        pos : array-like
            A length-3 iterable specifying the x, y, z coordinates of the position to be aimed at
        """

        direction = utils.angle(utils.unit_vector(np.array(pos) - self.cueing_ball.rvw[0]))
        self.set_state(phi = direction * 180/np.pi)


class CueAvoid(object):
    def __init__(self):
        """Calculates minimum elevation required by cue stick to avoid colliding with balls and cushions

        This class uses Panda3D collision detection to determine when the cue stick is intersecting
        with a ball or cushion. Rather than use the built in collision solving (e.g.
        https://docs.panda3d.org/1.10/python/reference/panda3d.core.CollisionHandlerPusher), which
        tended to push the cue off of objects in arbitrary ways (such that the cue no longer pointed
        at the cueing ball), I instead rely on geometry to solve the minimum angle that the cue
        stick must be raised in order to avoid all collisions. At each step in AimMode.aim_task, if
        the cue elevation is less than this angle, the elevation is automatically set to this
        minimum.

        Notes
        =====
        - This class has nothing to do with collisions that occurr during the shot evolution, e.g.
          ball-ball collisions, ball-cushion collisions, etc. All of those are handled in events.py
        """

        self.min_theta = 0

        if not ani.settings['gameplay']['cue_collision']:
            return

        # Declare frequently used nodes
        self.avoid_nodes = {
            'scene': render.find('scene'),
            'cue_collision_node': self.cue.get_node('cue_cseg'),
            'cue_stick_model': self.cue.get_node('cue_stick_model'),
            'cue_stick': self.cue.get_node('cue_stick'),
            'cue_stick_focus': self.cue.get_node('cue_stick_focus'),
        }


    def collision_task(self, task):
        max_min_theta = 0

        # Lay cue collision segment flat
        self.avoid_nodes['cue_collision_node'].setR(-self.avoid_nodes['cue_stick_focus'].getR())

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
        elif entry.into_node.name.startswith('cushion'):
            return self.process_cushion_collision(entry)
        elif entry.into_node.name.startswith('ball'):
            return self.process_ball_collision(entry)
        else:
            raise NotImplementedError(f"CueAvoid :: no collision solver for node {entry.into_node.name}")


    def process_cushion_collision(self, entry):
        cushion = self.get_cushion(entry)
        cushion_height = cushion.p1[2]

        # Point where cue center contacts collision plane
        Px, Py, Pz = entry.getSurfacePoint(self.avoid_nodes['scene'])

        # The tip of the cue stick
        Ex, Ey, Ez = self.avoid_nodes['cue_stick_model'].getPos(self.avoid_nodes['scene'])

        # Center ofthe cueing ball
        Bx, By, Bz = self.avoid_nodes['cue_stick_focus'].getPos(self.avoid_nodes['scene'])

        # The desired point where cue contacts collision plane, excluding cue width
        Dx, Dy, Dz = Px, Py, cushion_height

        # Center of aim
        v = np.array([Ex-Px, Ey-Py, Ez-Pz])
        u = utils.unit_vector(v)*self.avoid_nodes['cue_stick_model'].getX()
        Fx, Fy, Fz = Ex + u[0], Ey + u[1], Ez + u[2]

        min_theta = np.arctan2(Dz-Fz, np.sqrt((Dx-Fx)**2 + (Dy-Fy)**2))

        # Correct for cue's cylindrical radius at collision point
        # distance from cue tip (E) to desired collision point (D)
        l = np.sqrt((Dx-Ex)**2 + (Dy-Ey)**2 + (Dz-Ez)**2)
        cue_radius = self.get_cue_radius(l)
        min_theta += np.arctan2(cue_radius, l)

        return max(0, min_theta) * 180/np.pi


    def process_ball_collision(self, entry):
        min_theta = 0
        ball = self.get_ball(entry)

        if ball == self.cueing_ball:
            return 0

        scene = render.find('scene')

        # Radius of transect
        n = np.array(entry.get_surface_normal(render.find('scene')))
        phi = ((self.avoid_nodes['cue_stick_focus'].getH() + 180) % 360) * np.pi/180
        c = np.array([np.cos(phi), np.sin(phi), 0])
        gamma = np.arccos(np.dot(n, c))
        AB = (ball.R + self.cue.tip_radius)*np.cos(gamma)

        # Center of blocking ball transect
        Ax, Ay, _ = entry.getSurfacePoint(scene)
        Ax -= (AB + self.cue.tip_radius)*np.cos(phi)
        Ay -= (AB + self.cue.tip_radius)*np.sin(phi)
        Az = ball.R

        # Center of aim, leveled to ball height
        Cx, Cy, Cz = self.avoid_nodes['cue_stick_focus'].getPos(scene)
        axR = -self.avoid_nodes['cue_stick'].getY()
        Cx += -axR*np.sin(phi)
        Cy += axR*np.cos(phi)

        AC = np.sqrt((Ax-Cx)**2 + (Ay-Cy)**2 + (Az-Cz)**2)
        BC = np.sqrt(AC**2 - AB**2)
        min_theta_no_english = np.arcsin(AB/AC)

        # Cue tip point, no top/bottom english
        m = self.avoid_nodes['cue_stick_model'].getX()
        u = utils.unit_vector(np.array([-np.cos(phi), -np.sin(phi), np.sin(min_theta_no_english)]))
        Ex, Ey, Ez = Cx + m*u[0], Cy + m*u[1], Cz + m*u[2]

        # Point where cue contacts blocking ball, no top/bottom english
        Bx, By, Bz = Cx + BC*u[0], Cy + BC*u[1], Cz + BC*u[2]

        # Extra angle due to top/bottom english
        BE = np.sqrt((Bx-Ex)**2 + (By-Ey)**2 + (Bz-Ez)**2)
        bxR = self.avoid_nodes['cue_stick'].getZ()
        beta = -np.arctan2(bxR, BE)
        if beta < 0:
            beta += 10*np.pi/180*(np.exp(bxR/BE)**2 - 1)

        min_theta = min_theta_no_english + beta
        return max(0, min_theta) * 180/np.pi


    def get_cue_radius(self, l):
        """Returns radius of cue at collision point, given collision point is distance l from cue tip"""

        bounds = self.cue.get_node('cue_stick').get_tight_bounds()
        L = bounds[1][0] - bounds[0][0] # cue length

        r = self.cue.tip_radius
        R = self.cue.butt_radius

        m = (R - r)/L # rise/run
        b = r # intercept

        return m*l + b


    def get_cushion(self, entry):
        expected_suffix = 'cushion_cplane_'
        into_node_path_name = entry.get_into_node_path().name
        assert into_node_path_name.startswith(expected_suffix)
        cushion_id = into_node_path_name[len(expected_suffix):]
        return self.table.cushion_segments['linear'][cushion_id]


    def get_ball(self, entry):
        expected_suffix = 'ball_csphere_'
        into_node_path_name = entry.get_into_node_path().name
        assert into_node_path_name.startswith(expected_suffix)
        ball_id = into_node_path_name[len(expected_suffix):]
        return self.balls[ball_id]


