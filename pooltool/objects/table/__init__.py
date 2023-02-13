#! /usr/bin/env python

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Union

import numpy as np
from panda3d.core import CollisionNode, CollisionPlane, LineSegs, Plane, Point3, Vec3

import pooltool.ani as ani
from pooltool.ani.globals import Global
from pooltool.error import ConfigError
from pooltool.objects import Render
from pooltool.objects.table._layout import (
    _create_billiard_table_cushion_segments,
    _create_pocket_table_cushion_segments,
    _create_pocket_table_pockets,
)
from pooltool.objects.table.components import CushionSegment, Pocket
from pooltool.utils import panda_path, strenum


@dataclass
class TableModelDescr:
    name: str

    @property
    def path(self):
        """The path of the model

        The path is searched for in pooltool/models/table/{name}/{name}[_pbr].glb. If
        physical based rendering (PBR) is requested, a model suffixed with _pbr will be
        looked for. ConfigError is raised if model path cannot be determined from name.
        """

        if ani.settings["graphics"]["physical_based_rendering"]:
            path = ani.model_dir / "table" / self.name / (self.name + "_pbr.glb")
        else:
            path = ani.model_dir / "table" / self.name / (self.name + ".glb")

        if not path.exists():
            raise ConfigError(f"Couldn't find table model with name: {self.name}")

        return panda_path(path)

    @staticmethod
    def null() -> TableModelDescr:
        return TableModelDescr(name="null")

    @staticmethod
    def pocket_table_default() -> TableModelDescr:
        return TableModelDescr(name="7_foot")

    @staticmethod
    def billiard_table_default() -> TableModelDescr:
        return TableModelDescr.null()


class TableRender(Render):
    """A class for all pool table associated panda3d nodes"""

    def init_table(self, table):
        if (
            not table.specs.model_descr
            or table.specs.model_descr == TableModelDescr.null()
            or not ani.settings["graphics"]["table"]
        ):
            model = Global.loader.loadModel(TableModelDescr.null().path)
            node = Global.render.find("scene").attachNewNode("table")
            model.reparentTo(node)
            model.setScale(table.w, table.l, 1)
        else:
            node = Global.loader.loadModel(table.specs.model_descr.path)
            node.reparentTo(Global.render.find("scene"))
            node.setName("table")

        self.nodes["table"] = node
        self.collision_nodes = {}

    def init_collisions(self, table):
        if not ani.settings["gameplay"]["cue_collision"]:
            return

        if table.specs.table_type not in (TableType.BILLIARD, TableType.POCKET):
            raise NotImplementedError()

        # Make 4 planes
        # For diagram of cushion ids, see
        # https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-cushion-collision-times
        for cushion_id in ["3", "9", "12", "18"]:
            cushion = table.cushion_segments["linear"][cushion_id]

            x1, y1, z1 = cushion.p1
            x2, y2, z2 = cushion.p2

            n1, n2, n3 = cushion.normal
            if cushion_id in ["9", "12"]:
                # These normals need to be flipped
                n1, n2, n3 = -n1, -n2, -n3

            collision_node = self.nodes["table"].attachNewNode(
                CollisionNode(f"cushion_cplane_{cushion_id}")
            )
            collision_node.node().addSolid(
                CollisionPlane(Plane(Vec3(n1, n2, n3), Point3(x1, y1, z1)))
            )

            self.collision_nodes[f"cushion_ccapsule_{cushion_id}"] = collision_node

            if ani.settings["graphics"]["debug"]:
                collision_node.show()

        return collision_node

    def init_cushion_line(self, table, cushion_id):
        cushion = table.cushion_segments["linear"][cushion_id]

        self.cushion_drawer.moveTo(cushion.p1[0], cushion.p1[1], cushion.p1[2])
        self.cushion_drawer.drawTo(cushion.p2[0], cushion.p2[1], cushion.p2[2])
        node = (
            Global.render.find("scene")
            .find("table")
            .attachNewNode(self.cushion_drawer.create())
        )
        node.set_shader_auto(True)

        self.nodes[f"cushion_{cushion_id}"] = node

    def init_cushion_circle(self, table, cushion_id):
        cushion = table.cushion_segments["circular"][cushion_id]

        radius = cushion.radius
        center_x, center_y, center_z = cushion.center
        height = center_z

        circle = self.draw_circle(
            self.cushion_drawer, (center_x, center_y, height), radius, 30
        )
        node = Global.render.find("scene").find("table").attachNewNode(circle)
        node.set_shader_auto(True)
        self.nodes[f"cushion_{cushion_id}"] = node

    def init_cushion_edges(self, table):
        for cushion_id in table.cushion_segments["linear"]:
            self.init_cushion_line(table, cushion_id)

        for cushion_id in table.cushion_segments["circular"]:
            self.init_cushion_circle(table, cushion_id)

    def init_pocket(self, table, pocket_id):
        pocket = table.pockets[pocket_id]
        circle = self.draw_circle(self.pocket_drawer, pocket.center, pocket.radius, 100)
        node = Global.render.find("scene").find("table").attachNewNode(circle)
        node.set_shader_auto(True)
        self.nodes[f"pocket_{pocket_id}"] = node

    def init_pockets(self, table):
        for pocket_id in table.pockets:
            self.init_pocket(table, pocket_id)

    def render(self, table):
        super().render()

        # draw table as rectangle
        self.init_table(table)

        if (
            not table.specs.model_descr
            or table.specs.model_descr == TableModelDescr.null()
            or not ani.settings["graphics"]["table"]
        ):
            # draw cushion_segments as edges
            self.cushion_drawer = LineSegs()
            self.cushion_drawer.setThickness(3)
            self.cushion_drawer.setColor(1, 1, 1)

            self.init_cushion_edges(table)

            # draw pockets as unfilled circles
            self.pocket_drawer = LineSegs()
            self.pocket_drawer.setThickness(3)
            self.pocket_drawer.setColor(1, 1, 1)
            self.init_pockets(table)

        self.init_collisions(table)

    def draw_circle(self, drawer, center, radius, num_points):
        center_x, center_y, height = center

        thetas = np.linspace(0, 2 * np.pi, num_points)
        for i in range(1, len(thetas)):
            curr_theta, prev_theta = thetas[i], thetas[i - 1]

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
        raise NotImplementedError(
            "Can't call set_object_state_as_render_state for class 'TableRender'"
        )

    def set_render_state_as_object_state(self):
        raise NotImplementedError(
            "Can't call set_object_state_as_render_state for class 'TableRender'"
        )


class TableType(strenum.StrEnum):
    POCKET = strenum.auto()
    BILLIARD = strenum.auto()


@dataclass
class PocketTableSpecs:
    """Parameters that specify a pocket table"""

    # 7-foot table (78x39 in^2 playing surface)
    l: float = field(default=1.9812)
    w: float = field(default=1.9812 / 2)

    cushion_width: float = field(default=2 * 2.54 / 100)
    cushion_height: float = field(default=0.64 * 2 * 0.028575)
    corner_pocket_width: float = field(default=0.118)
    corner_pocket_angle: float = field(default=5.3)  # degrees
    corner_pocket_depth: float = field(default=0.0398)
    corner_pocket_radius: float = field(default=0.124 / 2)
    corner_jaw_radius: float = field(default=0.0419 / 2)
    side_pocket_width: float = field(default=0.137)
    side_pocket_angle: float = field(default=7.14)  # degrees
    side_pocket_depth: float = field(default=0.00437)
    side_pocket_radius: float = field(default=0.129 / 2)
    side_jaw_radius: float = field(default=0.0159 / 2)

    # For visualization
    model_descr: Optional[TableModelDescr] = None
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)

    table_type: TableType = field(init=False, default=TableType.POCKET)

    def __post_init__(self):
        field_defaults = {
            fname: field.default
            for fname, field in self.__dataclass_fields__.items()
            if field.init
        }

        if all(
            getattr(self, fname) == default for fname, default in field_defaults.items()
        ):
            # All parameters match the default table, and so the TableModelDescr is used even
            # if it wasn't explictly requested.
            self.model_descr = TableModelDescr.pocket_table_default()

    def create_cushion_segments(self):
        return _create_pocket_table_cushion_segments(self)

    def create_pockets(self):
        return _create_pocket_table_pockets(self)


@dataclass
class BilliardTableSpecs:
    """Parameters that specify a billiard (pocketless) table"""

    # 10-foot table (imprecise)
    l: float = field(default=3.05)
    w: float = field(default=3.05 / 2)

    # FIXME height should be adjusted for 3-cushion sized balls
    cushion_width: float = field(default=2 * 2.54 / 100)
    cushion_height: float = field(default=0.64 * 2 * 0.028575)

    # For visualization
    model_descr: Optional[TableModelDescr] = None
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)

    table_type: TableType = field(init=False, default=TableType.BILLIARD)

    def __post_init__(self):
        field_defaults = {
            fname: field.default
            for fname, field in self.__dataclass_fields__.items()
            if field.init
        }

        if all(
            getattr(self, fname) == default for fname, default in field_defaults.items()
        ):
            # All parameters match the default table, and so the TableModelDescr is used even
            # if it wasn't explictly requested.
            self.model_descr = TableModelDescr.billiard_table_default()

    def create_cushion_segments(self):
        return _create_billiard_table_cushion_segments(self)

    def create_pockets(self):
        return {}


def _table_render_factory():
    return TableRender()


@dataclass
class Table:
    specs: Union[PocketTableSpecs, BilliardTableSpecs]
    cushion_segments: Dict[str, Dict[str, CushionSegment]]
    pockets: Dict[str, Pocket]
    render_obj: TableRender = field(init=False, default_factory=_table_render_factory)

    @property
    def w(self):
        return self.specs.w

    @property
    def l(self):
        return self.specs.l

    @property
    def center(self):
        return self.w / 2, self.l / 2

    def render(self):
        self.render_obj.render(self)

    @staticmethod
    def from_table_specs(specs: Union[PocketTableSpecs, BilliardTableSpecs]) -> Table:
        return Table(
            specs=specs,
            cushion_segments=specs.create_cushion_segments(),
            pockets=specs.create_pockets(),
        )

    @staticmethod
    def default():
        return Table.from_table_specs(PocketTableSpecs())
