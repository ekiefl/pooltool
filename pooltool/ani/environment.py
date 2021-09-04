#! /usr/bin/env python

import pooltool

from pathlib import Path
from panda3d.core import *

class Environment(object):
    def __init__(self, table):

        self.set_table_offset(table)
        self.room = None

        self.slights_on = False
        self.shadow = False

        self.slights = {}
        self.plights = {}

        self.slight_str = 4
        self.slight_color = (0.8, 0.8, 0.6, 1)

        self.plight_str = 4
        self.plight_color = (0.8, 0.8, 0.6, 1)

        self.dlight_str = 3
        self.dlight_color = (0.8, 0.8, 0.7, 1)


    def get_slight(self, light_id, pos, hpr, illuminates, strength=None, color=None, fov=60, shadows=False, near=0.01, far=10, frustum=False):
        if strength is None:
            strength = self.slight_str
        if color is None:
            color = self.slight_color

        color = (strength*color[0], strength*color[1], strength*color[2], 1)

        slight = Spotlight(f'slight_{light_id}')
        slight.setColor(color)
        slight.attenuation = (1, 0, 1)

        lens = PerspectiveLens()
        lens.setFov(fov)
        lens.setNear(near)
        lens.setFar(far)
        lens.setFocalLength(0.01)
        slight.setLens(lens)

        if shadows:
            slight.setShadowCaster(True, 512, 512)
            if frustum:
                slight.showFrustum()

        slnp = render.attachNewNode(slight)
        slnp.setPos((self.offset[0]+pos[0], self.offset[1]+pos[1], self.offset[2]+pos[2]))
        slnp.setHpr(hpr)

        for illuminated in illuminates:
            illuminated.setLight(slnp)

        return slnp


    def get_plight(self, light_id, pos, illuminates, strength=None, color=None):
        if strength is None:
            strength = self.plight_str
        if color is None:
            color = self.plight_color

        color = (strength*color[0], strength*color[1], strength*color[2], 1)

        plight = PointLight(f'plight_{light_id}')
        plight.setColor(color)
        plight.attenuation = (1, 0, 1)

        plnp = render.attachNewNode(plight)
        plnp.setPos((self.offset[0]+pos[0], self.offset[1]+pos[1], self.offset[2]+pos[2]))

        for illuminated in illuminates:
            illuminated.setLight(plnp)

        return plnp


    def get_dlight(self, light_id, hpr, illuminates, strength=None, color=None, shadows=False):
        if strength is None:
            strength = self.dlight_str
        if color is None:
            color = self.dlight_color

        color = (strength*color[0], strength*color[1], strength*color[2], 1)

        dlight = DirectionalLight(f'dlight_{light_id}')
        dlight.setColor(color)

        if shadows:
            dlight.setShadowCaster(True, 512, 512)

        dlnp = render.attachNewNode(dlight)
        dlnp.setHpr(hpr)

        for illuminated in illuminates:
            illuminated.setLight(dlnp)

        return dlnp


    def load_lights(self):
        a_str = 0.1
        alight = AmbientLight('alight')
        alight.setColor((a_str, a_str, a_str, 1))
        alnp = render.attachNewNode(alight)
        render.setLight(alnp)

        if self.slights_on:
            self.slights = {
                 # under bar #1
                'under_bar_1_1': self.get_slight(
                    light_id = 0,
                    pos = (-4.0343, 0.83994, 0.97004),
                    hpr = (-90, -95, 0),
                    strength = 2,
                    far = 1,
                    illuminates = (self.room,),
                    shadows = self.shadow,
                ),
                'under_bar_1_2': self.get_slight(
                    light_id = 1,
                    pos = (-4.0343, -1.78035, 0.97004),
                    hpr = (-90, -95, 0),
                    strength = 2,
                    far = 1,
                    illuminates = (self.room,),
                    shadows = self.shadow,
                ),
                'under_bar_1_3': self.get_slight(
                    light_id = 2,
                    pos = (-4.0343, 3.18681, 0.97004),
                    hpr = (-90, -95, 0),
                    strength = 2,
                    far = 1,
                    illuminates = (self.room,),
                    shadows = self.shadow,
                ),
                # under bar #2
                'under_bar_2_1': self.get_slight(
                    light_id = 3,
                    pos = (1.6281, -4.7401, 0.96149),
                    hpr = (0, -95, 0),
                    strength = 2,
                    far = 1,
                    illuminates = (self.room,),
                    shadows = self.shadow,
                ),
                'under_bar_2_2': self.get_slight(
                    light_id = 4,
                    pos = (3.0487, -4.7401, 0.96149),
                    hpr = (0, -95, 0),
                    strength = 2,
                    far = 1,
                    illuminates = (self.room,),
                    shadows = self.shadow,
                ),
                'cues': self.get_slight(
                    light_id = 5,
                    pos = (0.068, -4.811+0.04, 2.2599-0.04),
                    hpr = (0, -100, 0),
                    fov = (30, 30),
                    far = 2,
                    illuminates = (self.room,),
                    shadows = self.shadow,
                ),
            }
        else:
            self.slights = {}

        self.plights = {
            # cocktail corner
            8: self.get_plight(
                light_id = 2,
                pos = (4.0877-0.08, 3.5745, 2.2042),
                illuminates = (render.find('scene'),),
            ),
            # above bar #1
            5: self.get_plight(
                light_id = 0,
                pos = (-4.1358+0.08, 1.9538, 2.2042),
                illuminates = (render.find('scene'),),
            ),
            6: self.get_plight(
                light_id = 1,
                pos = (-4.1358+0.08, -1.281, 2.2042),
                illuminates = (render.find('scene'),),
            ),
            # above bar # 2
            7: self.get_plight(
                light_id = 3,
                pos = (2.1875, -4.811+0.08, 2.1823),
                illuminates = (render.find('scene'),),
            ),
        }

        self.dlights = {
            # above bar #1
            0: self.get_dlight(
                light_id = 0,
                hpr = (0, -90, 0),
                illuminates = (render.find('scene').find('cloth'),),
                shadows = False,
            ),
        }


    def set_table_offset(self, table):
        self.offset = (table.w/2, table.l/2, -table.height)
        self.table_w = table.w
        self.table_l = table.l
        self.lights_height = table.lights_height + table.height


    def load_room(self, path):
        self.room = loader.loadModel(path)
        self.room.reparentTo(render.find('scene'))
        self.room.setPos(self.offset)
        self.room.setName('room')

        return self.room


