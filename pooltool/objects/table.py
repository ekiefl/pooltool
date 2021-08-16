#! /usr/bin/env python

import pooltool.utils as utils
import pooltool.ani.utils as autils

from pooltool.ani import model_paths
from pooltool.objects import *

import numpy as np

from pathlib import Path
from panda3d.core import *

class TableRender(Render):
    def __init__(self):
        """A class for all pool table associated panda3d nodes"""
        Render.__init__(self)


    def init_cloth(self):
        #path = str(Path(pooltool.__file__).parent.parent / 'models' / 'table' / 'table_default.glb')
        path = str(Path(pooltool.__file__).parent.parent / 'models' / 'table' / 'table_test.glb')
        node = loader.loadModel(path)
        node.reparentTo(render.find('scene'))
        node.setName('cloth')

        self.nodes['cloth'] = node


    def init_cushion_line(self, cushion_id):
        cushion = self.cushion_segments['linear'][cushion_id]

        self.cushion_drawer.moveTo(cushion.p1[0], cushion.p1[1], cushion.p1[2])
        self.cushion_drawer.drawTo(cushion.p2[0], cushion.p2[1], cushion.p2[2])
        node = render.find('scene').find('cloth').attachNewNode(self.cushion_drawer.create())

        self.nodes[f"cushion_{cushion_id}"] = node


    def init_cushion_circle(self, cushion_id):
        cushion = self.cushion_segments['circular'][cushion_id]

        radius = cushion.radius
        center_x, center_y, center_z = cushion.center
        height = center_z

        circle = self.draw_circle(self.cushion_drawer, (center_x, center_y, height), radius, 30)
        node = render.find('scene').find('cloth').attachNewNode(circle)
        self.nodes[f"cushion_{cushion_id}"] = node


    def init_cushion_edges(self):
        for cushion_id in self.cushion_segments['linear']:
            self.init_cushion_line(cushion_id)

        for cushion_id in self.cushion_segments['circular']:
            self.init_cushion_circle(cushion_id)


    def init_pocket(self, pocket_id):
        pocket = self.pockets[pocket_id]
        circle = self.draw_circle(self.pocket_drawer, pocket.center, pocket.radius, 30)
        node = render.find('scene').find('cloth').attachNewNode(circle)
        self.nodes[f"pocket_{pocket_id}"] = node


    def init_pockets(self):
        for pocket_id in self.pockets:
            self.init_pocket(pocket_id)


    def render(self):
        super().render()

        # draw table as rectangle
        self.init_cloth()

        # draw cushion_segments as edges
        self.cushion_drawer = LineSegs()
        self.cushion_drawer.setThickness(5)
        self.cushion_drawer.setColor(0.3, 0.3, 0.3)
        self.init_cushion_edges()

        # draw pockets as unfilled circles
        self.pocket_drawer = LineSegs()
        self.pocket_drawer.setThickness(5)
        self.pocket_drawer.setColor(0, 0, 0)
        self.init_pockets()


    def draw_circle(self, drawer, center, radius, num_points):
        center_x, center_y, height = center

        thetas = np.linspace(0, 2*np.pi, num_points)
        for i in range(1, len(thetas)):
            curr_theta, prev_theta = thetas[i], thetas[i-1]

            x_prev = center_x + radius * np.cos(prev_theta)
            y_prev = center_y + radius * np.sin(prev_theta)
            drawer.moveTo(x_prev, y_prev, height)

            x_curr = center_x + radius * np.cos(curr_theta)
            y_curr = center_y + radius * np.sin(curr_theta)
            drawer.drawTo(x_curr, y_curr, height)

        return drawer.create()


    def get_render_state(self):
        raise NotImplementedError("Can't call get_render_state for class 'TableRender'")


    def set_object_state_as_render_state(self):
        raise NotImplementedError("Can't call set_object_state_as_render_state for class 'TableRender'")


    def set_render_state_as_object_state(self):
        raise NotImplementedError("Can't call set_object_state_as_render_state for class 'TableRender'. Call render instead")


class Table(Object, TableRender):
    object_type = 'table'

    def __init__(self, w=None, l=None,
                 edge_width=None, cushion_width=None, cushion_height=None,
                 table_height=None, lights_height=None):

        self.w = w or pooltool.table_width
        self.l = l or pooltool.table_length
        self.edge_width = edge_width or pooltool.table_edge_width
        self.cushion_height = cushion_height or pooltool.cushion_height
        self.cushion_width = cushion_width or pooltool.cushion_width # for visualization
        self.height = table_height or pooltool.table_height # for visualization
        self.lights_height = lights_height or pooltool.lights_height # for visualization

        self.center = (self.w/2, self.l/2)

        s = 0.05
        c = 0.082
        j = 0.1
        js = 1/np.sqrt(2) * j
        # https://ekiefl.github.io/2020/12/20/pooltool-alg/#-ball-cushion-collision-times for diagram
        self.cushion_segments = {
            'linear' : {
                # long segments
                '3': LinearCushionSegment('3_edge', p1 = (0, c, self.cushion_height), p2 = (0, self.l/2-s, self.cushion_height)),
                '6': LinearCushionSegment('6_edge', p1 = (0, self.l/2+s, self.cushion_height), p2 = (0, self.l-c, self.cushion_height)),
                '9': LinearCushionSegment('9_edge', p1 = (c, self.l, self.cushion_height), p2 = (self.w-c, self.l, self.cushion_height)),
                '12': LinearCushionSegment('12_edge', p1 = (self.w, self.l-c, self.cushion_height), p2 = (self.w, self.l/2+s, self.cushion_height)),
                '15': LinearCushionSegment('15_edge', p1 = (self.w, self.l/2-s, self.cushion_height), p2 = (self.w, c, self.cushion_height)),
                '18': LinearCushionSegment('18_edge', p1 = (self.w-c, 0, self.cushion_height), p2 = (c, 0, self.cushion_height)),
                # jaw segments
                '1': LinearCushionSegment('1_edge', p1 = (c-js, -js, self.cushion_height), p2 = (c, 0, self.cushion_height)),
                '2': LinearCushionSegment('2_edge', p1 = (-js, c-js, self.cushion_height), p2 = (0, c, self.cushion_height)),
                '4': LinearCushionSegment('4_edge', p1 = (-j, self.l/2-s, self.cushion_height), p2 = (0, self.l/2-s, self.cushion_height)),
                '5': LinearCushionSegment('5_edge', p1 = (-j, self.l/2+s, self.cushion_height), p2 = (0, self.l/2+s, self.cushion_height)),
                '7': LinearCushionSegment('7_edge', p1 = (-js, self.l-c+js, self.cushion_height), p2 = (0, self.l-c, self.cushion_height)),
                '8': LinearCushionSegment('8_edge', p1 = (c-js, self.l+js, self.cushion_height), p2 = (c, self.l, self.cushion_height)),
                '10': LinearCushionSegment('10_edge', p1 = (self.w-c+js, self.l+js, self.cushion_height), p2 = (self.w-c, self.l, self.cushion_height)),
                '11': LinearCushionSegment('11_edge', p1 = (self.w+js, self.l-c+js, self.cushion_height), p2 = (self.w, self.l-c, self.cushion_height)),
                '13': LinearCushionSegment('13_edge', p1 = (self.w+j, self.l/2 + s, self.cushion_height), p2 = (self.w, self.l/2 + s, self.cushion_height)),
                '14': LinearCushionSegment('14_edge', p1 = (self.w+j, self.l/2 - s, self.cushion_height), p2 = (self.w, self.l/2 - s, self.cushion_height)),
                '16': LinearCushionSegment('16_edge', p1 = (self.w+js, c-js, self.cushion_height), p2 = (self.w, c, self.cushion_height)),
                '17': LinearCushionSegment('17_edge', p1 = (self.w-c+js, -js, self.cushion_height), p2 = (self.w-c, 0, self.cushion_height)),
            },
            'circular': {
            }
        }
        add_circle = lambda x: CircularCushionSegment(f'{x}t', center=self.cushion_segments['linear'][x].p2, radius=0)
        for x in [1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17]:
            self.cushion_segments['circular'][f'{x}t'] = add_circle(str(x))

        height = 0
        radius = c*0.70
        self.pockets = {
            'lb': Pocket('lb', center=(-radius/np.sqrt(2), -radius/np.sqrt(2), height), radius=radius),
            'lc': Pocket('lc', center=(-radius*np.sqrt(2), self.l/2, height), radius=radius),
            'lt': Pocket('lt', center=(-radius/np.sqrt(2), self.l+radius/np.sqrt(2), height), radius=radius),
            'rb': Pocket('rb', center=(self.w+radius/np.sqrt(2), -radius/np.sqrt(2), height), radius=radius),
            'rc': Pocket('rc', center=(self.w+radius*np.sqrt(2), self.l/2, height), radius=radius),
            'rt': Pocket('rt', center=(self.w+radius/np.sqrt(2), self.l+radius/np.sqrt(2), height), radius=radius),
        }

        TableRender.__init__(self)


class CushionSegment(Object):
    def get_normal(self, *args, **kwargs):
        return self.normal if hasattr(self, 'normal') else None


class LinearCushionSegment(CushionSegment):
    object_type = 'linear_cushion_segment'

    def __init__(self, cushion_id, p1, p2):
        self.id = cushion_id

        self.p1 = np.array(p1)
        self.p2 = np.array(p2)

        p1x, p1y, p1z = self.p1
        p2x, p2y, p2z = self.p2

        if p1z != p2z:
            raise ValueError(f"LinearCushionSegment with id '{self.id}' has points p1 and p2 with different cushion heights (h)")
        self.height = p1z

        if (p2x - p1x) == 0:
            self.lx = 1
            self.ly = 0
            self.l0 = -p1x
        else:
            self.lx = - (p2y - p1y) / (p2x - p1x)
            self.ly = 1
            self.l0 = (p2y - p1y) / (p2x - p1x) * p1x - p1y

        self.normal = utils.unit_vector(np.array([self.lx, self.ly, 0]))


class CircularCushionSegment(CushionSegment):
    object_type = 'circular_cushion_segment'

    def __init__(self, cushion_id, center, radius):
        self.id = cushion_id

        self.center = np.array(center)
        self.radius = radius
        self.height = center[2]

        self.a, self.b = self.center[:2]


    def get_normal(self, rvw):
        normal = utils.unit_vector(rvw[0,:] - self.center)
        normal[2] = 0 # remove z-component
        return normal


class Pocket(object):
    object_type = 'pocket'

    def __init__(self, pocket_id, center, radius, depth=0.08):
        self.id = pocket_id

        self.center = np.array(center)
        self.radius = radius
        self.depth = depth

        self.a, self.b = self.center[:2]

        # hold ball ids of balls the pocket contains
        self.contains = set()


    def add(self, ball_id):
        self.contains.add(ball_id)


    def remove(self, ball_id):
        self.contains.remove(ball_id)


