#! /usr/bin/env python

import pooltool.ani.utils as autils

from pooltool.ani import model_paths
from pooltool.objects import *

import numpy as np

from panda3d.core import *

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
        super().render()
        self.init_cloth()


    def get_render_state(self):
        raise NotImplementedError("Can't call get_render_state for class 'TableRender'")


    def set_object_state_as_render_state(self):
        raise NotImplementedError("Can't call set_object_state_as_render_state for class 'TableRender'")


    def set_render_state_as_object_state(self):
        raise NotImplementedError("Can't call set_object_state_as_render_state for class 'TableRender'. Call render instead")


class Table(Object, TableRender):
    object_type = 'table'

    def __init__(self, w=None, l=None,
                 edge_width=None, rail_width=None, rail_height=None,
                 table_height=None, lights_height=None):

        self.w = w or pooltool.table_width
        self.l = l or pooltool.table_length
        self.edge_width = edge_width or pooltool.table_edge_width
        self.rail_width = rail_width or pooltool.rail_width # for visualization
        self.height = table_height or pooltool.table_height # for visualization
        self.lights_height = lights_height or pooltool.lights_height # for visualization

        self.L = 0
        self.R = self.w
        self.B = 0
        self.T = self.l

        self.center = (self.w/2, self.l/2)

        self.rails = {
            'L': Rail('L', lx=1, ly=0, l0=-self.L, height=rail_height),
            'R': Rail('R', lx=1, ly=0, l0=-self.R, height=rail_height),
            'B': Rail('B', lx=0, ly=1, l0=-self.B, height=rail_height),
            'T': Rail('T', lx=0, ly=1, l0=-self.T, height=rail_height),
        }

        TableRender.__init__(self)


class Rail(Object):
    object_type = 'cushion'

    def __init__(self, rail_id, lx, ly, l0, height=None):
        """A rail is defined by a line lx*x + ly*y + l0 = 0"""

        self.id = rail_id

        self.lx = lx
        self.ly = ly
        self.l0 = l0

        # Defines the normal vector of the rail surface
        self.normal = np.array([self.lx, self.ly, 0])

        # rail properties
        self.height = height or pooltool.rail_height


