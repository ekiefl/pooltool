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
        path = str(Path(pooltool.__file__).parent.parent / 'models' / 'table' / 'table_default.glb')
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
        circle = self.draw_circle(self.pocket_drawer, pocket.center, pocket.radius, 100)
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
        self.cushion_drawer.setThickness(1)
        self.cushion_drawer.setColor(0.3, 0.3, 0.3)
        self.init_cushion_edges()

        # draw pockets as unfilled circles
        self.pocket_drawer = LineSegs()
        self.pocket_drawer.setThickness(1)
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


class PocketTable(Object, TableRender):
    object_type = 'pocket_table'

    def __init__(self, w=None, l=None, cushion_width=None, cushion_height=None, corner_pocket_width=None,
                 corner_pocket_angle=None, corner_pocket_depth=None, corner_pocket_radius=None, corner_jaw_radius=None,
                 side_pocket_width=None, side_pocket_angle=None, side_pocket_depth=None, side_pocket_radius=None,
                 side_jaw_radius=None, table_height=None, lights_height=None):

        self.w = w or pooltool.table_width
        self.l = l or pooltool.table_length
        self.cushion_width = cushion_width or pooltool.cushion_width
        self.cushion_height = cushion_height or pooltool.cushion_height
        self.corner_pocket_width = corner_pocket_width or pooltool.corner_pocket_width
        self.corner_pocket_angle = corner_pocket_angle or pooltool.corner_pocket_angle
        self.corner_pocket_depth = corner_pocket_depth or pooltool.corner_pocket_depth
        self.corner_pocket_radius = corner_pocket_radius or pooltool.corner_pocket_radius
        self.corner_jaw_radius = corner_jaw_radius or pooltool.corner_jaw_radius
        self.side_pocket_width = side_pocket_width or pooltool.side_pocket_width
        self.side_pocket_angle = side_pocket_angle or pooltool.side_pocket_angle
        self.side_pocket_depth = side_pocket_depth or pooltool.side_pocket_depth
        self.side_pocket_radius = side_pocket_radius or pooltool.side_pocket_radius
        self.side_jaw_radius = side_jaw_radius or pooltool.side_jaw_radius
        self.height = table_height or pooltool.table_height # for visualization
        self.lights_height = lights_height or pooltool.lights_height # for visualization

        self.center = (self.w/2, self.l/2)

        self.cushion_segments = self.get_cushion_segments()
        self.pockets = self.get_pockets()

        TableRender.__init__(self)


    def get_cushion_segments(self):
        # https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-cushion-collision-times for diagram
        cw = self.cushion_width
        ca = (self.corner_pocket_angle + 45) * np.pi/180
        sa = self.side_pocket_angle * np.pi/180
        pw = self.corner_pocket_width
        sw = self.side_pocket_width
        h = self.cushion_height
        rc = self.corner_jaw_radius
        rs = self.side_jaw_radius
        dc = self.corner_jaw_radius/np.tan((np.pi/2 + ca)/2)
        ds = self.side_jaw_radius/np.tan((np.pi/2 + sa)/2)

        cushion_segments = {
            'linear' : {
                # long segments
                '3': LinearCushionSegment(
                    '3_edge',
                    p1 = (0, pw*np.cos(np.pi/4)+dc, h),
                    p2 = (0, (self.l-sw)/2-ds, h)
                ),
                '6': LinearCushionSegment(
                    '6_edge',
                    p1 = (0, (self.l+sw)/2+ds, h),
                    p2 = (0, -pw*np.cos(np.pi/4)+self.l-dc, h)
                ),
                '15': LinearCushionSegment(
                    '15_edge',
                    p1 = (self.w, pw*np.cos(np.pi/4)+dc, h),
                    p2 = (self.w, (self.l-sw)/2-ds, h)
                ),
                '12': LinearCushionSegment(
                    '12_edge',
                    p1 = (self.w, (self.l+sw)/2+ds, h),
                    p2 = (self.w, -pw*np.cos(np.pi/4)+self.l-dc, h)
                ),
                '18': LinearCushionSegment(
                    '18_edge',
                    p1 = (pw*np.cos(np.pi/4)+dc, 0, h),
                    p2 = (-pw*np.cos(np.pi/4)+self.w-dc, 0, h)
                ),
                '9': LinearCushionSegment(
                    '9_edge',
                    p1 = (pw*np.cos(np.pi/4)+dc, self.l, h),
                    p2 = (-pw*np.cos(np.pi/4)+self.w-dc, self.l, h)
                ),
                # side jaw segments
                '5': LinearCushionSegment(
                    '5_edge',
                    p1 = (-cw, (self.l+sw)/2-cw*np.sin(sa), h),
                    p2 = (-ds*np.cos(sa), (self.l+sw)/2-ds*np.sin(sa), h),
                ),
                '4': LinearCushionSegment(
                    '4_edge',
                    p1 = (-cw, (self.l-sw)/2+cw*np.sin(sa), h),
                    p2 = (-ds*np.cos(sa), (self.l-sw)/2+ds*np.sin(sa), h),
                ),
                '13': LinearCushionSegment(
                    '13_edge',
                    p1 = (self.w+cw, (self.l+sw)/2-cw*np.sin(sa), h),
                    p2 = (self.w+ds*np.cos(sa), (self.l+sw)/2-ds*np.sin(sa), h),
                ),
                '14': LinearCushionSegment(
                    '14_edge',
                    p1 = (self.w+cw, (self.l-sw)/2+cw*np.sin(sa), h),
                    p2 = (self.w+ds*np.cos(sa), (self.l-sw)/2+ds*np.sin(sa), h),
                ),
                # corner jaw segments
                '1': LinearCushionSegment(
                    '1_edge',
                    p1 = (pw*np.cos(np.pi/4)-cw*np.tan(ca), -cw, h),
                    p2 = (pw*np.cos(np.pi/4)-dc*np.sin(ca), -dc*np.cos(ca), h),
                ),
                '2': LinearCushionSegment(
                    '2_edge',
                    p1 = (-cw, pw*np.cos(np.pi/4)-cw*np.tan(ca), h),
                    p2 = (-dc*np.cos(ca), pw*np.cos(np.pi/4)-dc*np.sin(ca), h),
                ),
                '8': LinearCushionSegment(
                    '8_edge',
                    p1 = (pw*np.cos(np.pi/4)-cw*np.tan(ca), cw+self.l, h),
                    p2 = (pw*np.cos(np.pi/4)-dc*np.sin(ca), self.l+dc*np.cos(ca), h),
                ),
                '7': LinearCushionSegment(
                    '7_edge',
                    p1 = (-cw, -pw*np.cos(np.pi/4)+cw*np.tan(ca)+self.l, h),
                    p2 = (-dc*np.cos(ca), -pw*np.cos(np.pi/4)+self.l+dc*np.sin(ca), h),
                ),
                '11': LinearCushionSegment(
                    '11_edge',
                    p1 = (cw+self.w, -pw*np.cos(np.pi/4)+cw*np.tan(ca)+self.l, h),
                    p2 = (self.w+dc*np.cos(ca), -pw*np.cos(np.pi/4)+self.l+dc*np.sin(ca), h),
                ),
                '10': LinearCushionSegment(
                    '10_edge',
                    p1 = (-pw*np.cos(np.pi/4)+cw*np.tan(ca)+self.w, cw+self.l, h),
                    p2 = (-pw*np.cos(np.pi/4)+self.w+dc*np.sin(ca), self.l+dc*np.cos(ca), h),
                ),
                '16': LinearCushionSegment(
                    '16_edge',
                    p1 = (cw+self.w, +pw*np.cos(np.pi/4)-cw*np.tan(ca), h),
                    p2 = (self.w+dc*np.cos(ca), pw*np.cos(np.pi/4)-dc*np.sin(ca), h),
                ),
                '17': LinearCushionSegment(
                    '17_edge',
                    p1 = (-pw*np.cos(np.pi/4)+cw*np.tan(ca)+self.w, -cw, h),
                    p2 = (-pw*np.cos(np.pi/4)+self.w+dc*np.sin(ca), -dc*np.cos(ca), h),
                ),
            },
            'circular': {
                '1t': CircularCushionSegment('1t', center=(pw*np.cos(np.pi/4)+dc, -rc, h), radius=rc),
                '2t': CircularCushionSegment('2t', center=(-rc, pw*np.cos(np.pi/4)+dc, h), radius=rc),
                '4t': CircularCushionSegment('4t', center=(-rs, self.l/2-sw/2-ds, h), radius=rs),
                '5t': CircularCushionSegment('5t', center=(-rs, self.l/2+sw/2+ds, h), radius=rs),
                '7t': CircularCushionSegment('7t', center=(-rc, self.l - (pw*np.cos(np.pi/4)+dc), h), radius=rc),
                '8t': CircularCushionSegment('8t', center=(pw*np.cos(np.pi/4)+dc, self.l+rc, h), radius=rc),
                '10t': CircularCushionSegment('10t', center=(self.w-pw*np.cos(np.pi/4)-dc, self.l+rc, h), radius=rc),
                '11t': CircularCushionSegment('11t', center=(self.w+rc, self.l - (pw*np.cos(np.pi/4)+dc), h), radius=rc),
                '13t': CircularCushionSegment('13t', center=(self.w+rs, self.l/2+sw/2+ds, h), radius=rs),
                '14t': CircularCushionSegment('14t', center=(self.w+rs, self.l/2-sw/2-ds, h), radius=rs),
                '16t': CircularCushionSegment('16t', center=(self.w+rc, pw*np.cos(np.pi/4)+dc, h), radius=rc),
                '17t': CircularCushionSegment('17t', center=(self.w-pw*np.cos(np.pi/4)-dc, -rc, h), radius=rc),
            },
        }

        return cushion_segments


    def get_pockets(self):
        pw = self.corner_pocket_width
        cr = self.corner_pocket_radius
        sr = self.side_pocket_radius
        cd = self.corner_pocket_depth
        sd = self.side_pocket_depth

        cD = cr + cd - pw/2
        sD = sr + sd

        pockets = {
            'lb': Pocket('lb', center=(-cD/np.sqrt(2), -cD/np.sqrt(2), 0), radius=cr),
            'lc': Pocket('lc', center=(-sD, self.l/2, 0), radius=sr),
            'lt': Pocket('lt', center=(-cD/np.sqrt(2), self.l+cD/np.sqrt(2), 0), radius=cr),
            'rb': Pocket('rb', center=(self.w+cD/np.sqrt(2), -cD/np.sqrt(2), 0), radius=cr),
            'rc': Pocket('rc', center=(self.w+sD, self.l/2, 0), radius=sr),
            'rt': Pocket('rt', center=(self.w+cD/np.sqrt(2), self.l+cD/np.sqrt(2), 0), radius=cr),
        }

        return pockets


class BilliardTable(Object, TableRender):
    object_type = 'billiard_table'

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


