#! /usr/bin/env python

from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    PerspectiveLens,
    PointLight,
    Spotlight,
)

import pooltool.ani as ani
from pooltool.ani.globals import Global
from pooltool.utils import panda_path


class Environment:
    def __init__(self):
        self.room = None
        self.floor = None
        self.room_loaded = False
        self.floor_loaded = False
        self.lights_loaded = False

        self.shadow = True

        self.slights = {}
        self.plights = {}

        shader = ani.settings["graphics"]["shader"]
        lights = ani.settings["graphics"]["lights"]

        self.slight_str = 4
        self.slight_color = (0.8, 0.8, 0.6, 1)

        self.plight_str = 4
        self.plight_color = (0.8, 0.8, 0.6, 1)

        self.dlight_str = 1 if (lights and not shader) else 3
        self.dlight_color = (0.8, 0.8, 0.7, 1)

    def init(self, table):
        if ani.settings["graphics"]["physical_based_rendering"]:
            room_path = panda_path(ani.model_dir / "room/room_pbr.glb")
            floor_path = panda_path(ani.model_dir / "room/floor_pbr.glb")
        else:
            room_path = panda_path(ani.model_dir / "room/room.glb")
            floor_path = panda_path(ani.model_dir / "room/floor.glb")

        self.set_table_offset(table)

        if ani.settings["graphics"]["room"]:
            self.load_room(room_path)
        if ani.settings["graphics"]["floor"]:
            self.load_floor(floor_path)
        if ani.settings["graphics"]["lights"]:
            self.load_lights()

    def get_slight(
        self,
        light_id,
        pos,
        hpr,
        illuminates,
        strength=None,
        color=None,
        fov=60,
        shadows=False,
        near=0.01,
        far=10,
        frustum=False,
    ):
        if strength is None:
            strength = self.slight_str
        if color is None:
            color = self.slight_color

        color = (strength * color[0], strength * color[1], strength * color[2], 1)

        slight = Spotlight(f"slight_{light_id}")
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

        slnp = Global.render.attachNewNode(slight)
        slnp.setPos(
            (self.offset[0] + pos[0], self.offset[1] + pos[1], self.offset[2] + pos[2])
        )
        slnp.setHpr(hpr)

        for illuminated in illuminates:
            if illuminated is not None:
                illuminated.setLight(slnp)

        return slnp

    def get_plight(self, light_id, pos, illuminates, strength=None, color=None):
        if strength is None:
            strength = self.plight_str
        if color is None:
            color = self.plight_color

        color = (strength * color[0], strength * color[1], strength * color[2], 1)

        plight = PointLight(f"plight_{light_id}")
        plight.setColor(color)
        plight.attenuation = (1, 0, 1)

        plnp = Global.render.attachNewNode(plight)
        plnp.setPos(
            (self.offset[0] + pos[0], self.offset[1] + pos[1], self.offset[2] + pos[2])
        )

        for illuminated in illuminates:
            if illuminated is not None:
                illuminated.setLight(plnp)

        return plnp

    def get_dlight(
        self, light_id, hpr, illuminates, strength=None, color=None, shadows=False
    ):
        if strength is None:
            strength = self.dlight_str
        if color is None:
            color = self.dlight_color

        color = (strength * color[0], strength * color[1], strength * color[2], 1)

        dlight = DirectionalLight(f"dlight_{light_id}")
        dlight.setColor(color)

        if shadows:
            dlight.setShadowCaster(True, 512, 512)

        dlnp = Global.render.attachNewNode(dlight)
        dlnp.setHpr(hpr)

        for illuminated in illuminates:
            if illuminated is not None:
                illuminated.setLight(dlnp)

        return dlnp

    def load_lights(self):
        a_str = 0.1
        alight = AmbientLight("alight")
        alight.setColor((a_str, a_str, a_str, 1))
        alnp = Global.render.attachNewNode(alight)
        Global.render.setLight(alnp)

        self.slights = {
            # under bar #1
            "under_bar_1_1": self.get_slight(
                light_id=0,
                pos=(-4.0343, 0.83994, 0.97004),
                hpr=(-90, -95, 0),
                strength=2,
                far=1,
                illuminates=(self.room, self.floor),
                shadows=self.shadow,
            ),
            "under_bar_1_2": self.get_slight(
                light_id=1,
                pos=(-4.0343, -1.78035, 0.97004),
                hpr=(-90, -95, 0),
                strength=2,
                far=1,
                illuminates=(self.room, self.floor),
                shadows=self.shadow,
            ),
            "under_bar_1_3": self.get_slight(
                light_id=2,
                pos=(-4.0343, 3.18681, 0.97004),
                hpr=(-90, -95, 0),
                strength=2,
                far=1,
                illuminates=(self.room, self.floor),
                shadows=self.shadow,
            ),
            # under bar #2
            "under_bar_2_1": self.get_slight(
                light_id=3,
                pos=(1.6281, -4.7401, 0.96149),
                hpr=(0, -95, 0),
                strength=2,
                far=1,
                illuminates=(self.room, self.floor),
                shadows=self.shadow,
            ),
            "under_bar_2_2": self.get_slight(
                light_id=4,
                pos=(3.0487, -4.7401, 0.96149),
                hpr=(0, -95, 0),
                strength=2,
                far=1,
                illuminates=(self.room, self.floor),
                shadows=self.shadow,
            ),
            "cues": self.get_slight(
                light_id=5,
                pos=(0.068, -4.811 + 0.04, 2.2599 - 0.04),
                hpr=(0, -100, 0),
                fov=(30, 30),
                far=2,
                illuminates=(self.room, self.floor),
                shadows=self.shadow,
            ),
        }

        self.plights = {
            # cocktail corner
            8: self.get_plight(
                light_id=2,
                pos=(4.0877 - 0.08, 3.5745, 2.2042),
                illuminates=(Global.render.find("scene"),),
            ),
            # above bar #1
            5: self.get_plight(
                light_id=0,
                pos=(-4.1358 + 0.08, 1.9538, 2.2042),
                illuminates=(Global.render.find("scene"),),
            ),
            6: self.get_plight(
                light_id=1,
                pos=(-4.1358 + 0.08, -1.281, 2.2042),
                illuminates=(Global.render.find("scene"),),
            ),
            # above bar # 2
            7: self.get_plight(
                light_id=3,
                pos=(2.1875, -4.811 + 0.08, 2.1823),
                illuminates=(Global.render.find("scene"),),
            ),
        }

        self.dlights = {
            # above bar #1
            0: self.get_dlight(
                light_id=0,
                hpr=(0, -90, 0),
                illuminates=(Global.render.find("scene").find("table"),),
                shadows=False,
            ),
        }

        self.lights_loaded = True

    def set_table_offset(self, table):
        self.offset = (table.w / 2, table.l / 2, -table.height)
        self.table_w = table.w
        self.table_l = table.l
        self.lights_height = table.lights_height + table.height

    def load_room(self, path):
        self.room = Global.loader.loadModel(panda_path(path))
        self.room.reparentTo(Global.render.find("scene"))
        self.room.setPos(self.offset)
        self.room.setName("room")

        self.room_loaded = True

        return self.room

    def load_floor(self, path):
        self.floor = Global.loader.loadModel(panda_path(path))
        self.floor.reparentTo(Global.render.find("scene"))
        self.floor.setPos(self.offset)
        self.floor.setName("floor")

        self.floor_loaded = True

        return self.floor

    def unload_room(self):
        if not self.room_loaded:
            return

        self.room.removeNode()
        del self.room

        self.room_loaded = False

    def unload_floor(self):
        if not self.floor_loaded:
            return

        self.floor.removeNode()
        del self.floor

        self.floor_loaded = False

    def unload_lights(self):
        Global.render.clearLight()

        if not self.lights_loaded:
            return

        for light in self.slights.values():
            light.removeNode()
        for light in self.plights.values():
            light.removeNode()
        for light in self.dlights.values():
            light.removeNode()

        self.slights = {}
        self.plights = {}
        self.dlights = {}

        self.lights_loaded = False


environment = Environment()
