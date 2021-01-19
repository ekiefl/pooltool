#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.ani.utils as autils
import psim.physics as physics

from psim.ani import model_paths

import numpy as np

from functools import partial
from panda3d.core import *


class Render(object):
    def __init__(self):
        """A base class for rendering physical pool objects

        This class stores base operations on panda3d nodes that are associated with any pool objects
        such as cues, tables, and balls.

        Notes
        =====
        - All nodes are stored in self.nodes.
        - Child classes should have a self.render method that populates self.nodes
        """

        self.nodes = {}
        self.rendered = False


    def remove_node(self, name):
        self.nodes[name].removeNode()
        del self.nodes[name]


    def remove_nodes(self):
        for node in self.nodes.values():
            node.removeNode()

        self.nodes = {}


    def hide_node(self, name):
        self.nodes[name].hide()


    def hide_nodes(self):
        for node_name in self.nodes:
            self.hide_node(node_name)


    def show_node(self, name):
        self.nodes[name].show()


    def show_nodes(self):
        for node_name in self.nodes:
            self.show_node(node_name)


    def get_node(self, name):
        return self.nodes[name]


# -------------------------------------------------------------------------------------------------
# TABLE {{{
# -------------------------------------------------------------------------------------------------


class TableRender(Render):
    def __init__(self):
        """A class for all pool table associated panda3d nodes"""
        Render.__init__(self)


    def init_cloth(self):
        node = render.find('scene').attachNewNode(
            autils.make_rectangle(
                x1=0,
                y1=0,
                z1=0,
                x2=self.w,
                y2=self.l,
                z2=0,
                name='cloth'
            )
        )

        node.setPos(0, 0, self.height)

        # Currently there are no texture coordinates for make_rectangle, so this just picks a single color
        cloth_tex = loader.loadTexture(model_paths['blue_cloth'])
        cloth_tex.setWrapU(Texture.WM_repeat)
        cloth_tex.setWrapV(Texture.WM_repeat)
        node.setTexture(cloth_tex)

        self.nodes['cloth'] = node


    def render(self):
        self.rendered = True
        self.init_cloth()


class Table(TableRender):
    def __init__(self, w=None, l=None, u_s=None, u_r=None, u_sp=None,
                 edge_width=None, rail_width=None, rail_height=None,
                 table_height=None, lights_height=None):

        self.w = w or psim.table_width
        self.l = l or psim.table_length
        self.edge_width = edge_width or psim.table_edge_width
        self.rail_width = rail_width or psim.rail_width # for visualization
        self.height = table_height or psim.table_height # for visualization
        self.lights_height = lights_height or psim.lights_height # for visualization

        self.L = 0
        self.R = self.w
        self.B = 0
        self.T = self.l

        self.center = (self.w/2, self.l/2)

        # felt properties
        self.u_s = u_s or psim.u_s
        self.u_r = u_r or psim.u_r
        self.u_sp = u_sp or psim.u_sp

        self.rails = {
            'L': Rail('L', lx=1, ly=0, l0=-self.L, height=rail_height),
            'R': Rail('R', lx=1, ly=0, l0=-self.R, height=rail_height),
            'B': Rail('B', lx=0, ly=1, l0=-self.B, height=rail_height),
            'T': Rail('T', lx=0, ly=1, l0=-self.T, height=rail_height),
        }

        TableRender.__init__(self)


class Rail(object):
    def __init__(self, rail_id, lx, ly, l0, height=None):
        """A rail is defined by a line lx*x + ly*y + l0 = 0"""

        self.id = rail_id

        self.lx = lx
        self.ly = ly
        self.l0 = l0

        # Defines the normal vector of the rail surface
        self.normal = np.array([self.lx, self.ly, 0])

        # rail properties
        self.height = height or psim.rail_height


# -------------------------------------------------------------------------------------------------
# }}} BALL {{{
# -------------------------------------------------------------------------------------------------

class BallRender(Render):
    def __init__(self):
        Render.__init__(self)


    def init_sphere(self):
        node = loader.loadModel('models/smiley')
        expected_texture_name = f"{str(self.id).split('_')[0]}_ball"

        try:
            tex = loader.loadTexture(model_paths[expected_texture_name])
            node.setTexture(tex, 1)
        except KeyError:
            # No ball texture is found for the given ball.id. Keeping smiley
            pass

        node.reparentTo(render.find('scene').find('cloth'))
        node.setScale(self.get_scale_factor(node))
        node.setPos(*self.rvw[0,:])

        self.nodes['sphere'] = node


    def get_scale_factor(self, node):
        """Find scale factor to match model size to ball's SI radius"""
        m, M = node.getTightBounds()
        model_R = (M - m)[0]/2

        return self.R / model_R


    def render(self):
        self.init_sphere()
        self.rendered = True


class Ball(BallRender):
    def __init__(self, ball_id, m=None, R=None):
        self.id = ball_id

        # physical properties
        self.m = m or psim.m
        self.R = R or psim.R
        self.I = 2/5 * self.m * self.R**2

        self.rvw = np.array([[np.nan, np.nan, np.nan],  # positions (r)
                             [0,      0,      0     ],  # velocities (v)
                             [0,      0,      0     ],  # angular velocities (w)
                             [0,      0,      0     ]]) # angular integrations (e)

        # stationary=0, spinning=1, sliding=2, rolling=3
        self.s = 0

        BallRender.__init__(self)


    def __repr__(self):
        lines = [
            f'<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>',
            f' ├── id       : {self.id}',
            f' ├── state    : {self.s}',
            f' ├── position : {self.rvw[0]}',
            f' ├── velocity : {self.rvw[1]}',
            f' ├── angular  : {self.rvw[2]}',
            f' └── euler    : {self.rvw[3]}',
        ]

        return '\n'.join(lines) + '\n'


    def set(self, rvw, s):
        self.s = s
        self.rvw = rvw


# -------------------------------------------------------------------------------------------------
# }}} CUE {{{
# -------------------------------------------------------------------------------------------------


class CueRender(Render):
    def __init__(self):
        Render.__init__(self)


    def init_model(self, R=psim.R):
        cue_stick_model = loader.loadModel(model_paths['cylinder'])
        cue_stick_model.setName('cue_stick_model')

        m, M = cue_stick_model.getTightBounds()
        model_R, model_l = (M-m)[0]/2, (M-m)[2]

        # Rescale model to match cue dimensions
        cue_stick_model.setSx(self.tip_radius / model_R)
        cue_stick_model.setSy(self.tip_radius / model_R)
        cue_stick_model.setSz(self.length / model_l)

        cue_stick_tex = loader.loadTexture(model_paths['red_cloth'])
        cue_stick_model.setTexture(cue_stick_tex)
        cue_stick_model.setTexScale(TextureStage.getDefault(), 0.01, 0.01)

        cue_stick = render.find('scene').find('cloth').attachNewNode('cue_stick')
        cue_stick_model.reparentTo(cue_stick)

        self.nodes['cue_stick'] = cue_stick


    def init_focus(self, ball):
        cue_stick = self.get_node('cue_stick')

        cue_stick.find('cue_stick_model').setPos(0, 0, self.length/2 + 1.2*ball.R)
        cue_stick.setP(90)
        cue_stick.setH(90)

        cue_stick_focus = render.find('scene').find('cloth').attachNewNode("cue_stick_focus")
        cue_stick_focus.setPos(ball.get_node('sphere').getPos())
        cue_stick.reparentTo(cue_stick_focus)

        self.nodes['cue_stick_focus'] = cue_stick_focus


    def get_node_state(self):
        """Return phi, theta, a, and b as determined by the cue_stick node"""

        cue_stick = self.get_node('cue_stick_focus')
        phi = ((cue_stick.getH() + 180) % 360) * np.pi/180

        # FIXME
        theta = 0
        a = 0
        b = 0

        return phi, theta, a, b


    def set_state_as_node_state(self):
        self.phi, self.theta, self.a, self.b = self.get_node_state()


    def render(self):
        self.init_model()
        self.rendered = True


class Cue(CueRender):
    def __init__(self, M=psim.M, length=psim.cue_length, tip_radius=psim.cue_tip_radius,
                 butt_radius=psim.cue_butt_radius, brand=None):

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

        CueRender.__init__(self)


    def set_state(self, V0=None, phi=None, theta=None, a=None, b=None):
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


    def strike(self, ball):
        if (self.V0 is None or self.phi is None or self.theta is None or self.a is None or self.b is None):
            raise ValueError("Cue.strike :: Must set V0, phi, theta, a, and b")

        v, w = physics.cue_strike(ball.m, self.M, ball.R, self.V0, self.phi, self.theta, self.a, self.b)
        rvw = np.array([ball.rvw[0], v, w, ball.rvw[3]])

        s = (psim.rolling
             if abs(np.sum(physics.get_rel_velocity(rvw, ball.R))) <= psim.tol
             else psim.sliding)

        ball.set(rvw, s)


    def aim_at(self, pos):
        # FIXME
        pass

