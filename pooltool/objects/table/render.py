import numpy as np
from panda3d.core import (
    CollisionNode,
    CollisionPlane,
    LineSegs,
    NodePath,
    Plane,
    Point3,
    Vec3,
)

from pooltool.ani.globals import Global
from pooltool.config import settings
from pooltool.objects.datatypes import Render
from pooltool.objects.table.datatypes import Table, TableModelDescr, TableType


class TableRender(Render):
    """A class for all pool table associated panda3d nodes"""

    def __init__(self, table: Table):
        self._table = table
        Render.__init__(self)

    @property
    def _uses_null_model(self) -> bool:
        """Whether the table is drawn as a bare playing surface instead of a real model"""
        return (
            not self._table.model_descr
            or self._table.model_descr == TableModelDescr.null()
            or not settings.graphics.table
        )

    def _load_model(self) -> NodePath:
        """Load the table model, scaled to the table's dimensions when it is the null plane

        Panda3D caches loaded models, so this is cheap to call repeatedly.
        """
        if self._uses_null_model:
            model = Global.loader.loadModel(
                TableModelDescr.null().get_path(
                    settings.graphics.physical_based_rendering
                )
            )
            model.setScale(self._table.w, self._table.l, 1)
            return model

        assert self._table.model_descr is not None
        return Global.loader.loadModel(
            self._table.model_descr.get_path(
                settings.graphics.physical_based_rendering
            )
        )

    def init_table(self):
        model = self._load_model()

        if self._uses_null_model:
            # Rectangular playing surface (not a real table)
            node = Global.render.find("scene").attachNewNode("table")
            model.reparentTo(node)
        else:
            # Real table
            node = model
            node.reparentTo(Global.render.find("scene"))
            node.setName("table")

        self.nodes["table"] = node
        self.collision_nodes = {}

    def init_collisions(self):
        if not settings.gameplay.cue_collision:
            return

        if self._table.table_type not in (
            TableType.BILLIARD,
            TableType.POCKET,
            TableType.SNOOKER,
        ):
            raise NotImplementedError()

        # Make 4 planes, each with its normal facing into the table
        # For diagram of cushion ids, see
        # https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-cushion-collision-times
        table_center = np.array([*self._table.center, 0.0])
        for cushion_id in ["3", "9", "12", "18"]:
            cushion = self._table.cushion_segments.linear[cushion_id]

            x1, y1, z1 = cushion.p1
            n1, n2, n3 = cushion.get_normal_xy(table_center)

            collision_node = self.nodes["table"].attachNewNode(
                CollisionNode(f"cushion_cplane_{cushion_id}")
            )
            collision_node.node().addSolid(
                CollisionPlane(Plane(Vec3(n1, n2, n3), Point3(x1, y1, z1)))
            )

            self.collision_nodes[f"cushion_ccapsule_{cushion_id}"] = collision_node

            if settings.graphics.debug:
                collision_node.show()

        return collision_node

    def init_cushion_line(self, cushion_id):
        cushion = self._table.cushion_segments.linear[cushion_id]

        self.cushion_drawer.moveTo(cushion.p1[0], cushion.p1[1], cushion.p1[2])
        self.cushion_drawer.drawTo(cushion.p2[0], cushion.p2[1], cushion.p2[2])
        node = (
            Global.render.find("scene")
            .find("table")
            .attachNewNode(self.cushion_drawer.create())
        )
        node.set_shader_auto(True)

        self.nodes[f"cushion_{cushion_id}"] = node

    def init_cushion_circle(self, cushion_id):
        cushion = self._table.cushion_segments.circular[cushion_id]

        radius = cushion.radius
        center_x, center_y, center_z = cushion.center
        height = center_z

        circle = self.draw_circle(
            self.cushion_drawer, (center_x, center_y, height), radius, 30
        )
        node = Global.render.find("scene").find("table").attachNewNode(circle)
        node.set_shader_auto(True)
        self.nodes[f"cushion_{cushion_id}"] = node

    def init_cushion_edges(self):
        for cushion_id in self._table.cushion_segments.linear:
            self.init_cushion_line(cushion_id)

        for cushion_id in self._table.cushion_segments.circular:
            self.init_cushion_circle(cushion_id)

    def init_pocket(self, pocket_id):
        pocket = self._table.pockets[pocket_id]
        circle = self.draw_circle(self.pocket_drawer, pocket.center, pocket.radius, 100)
        node = Global.render.find("scene").find("table").attachNewNode(circle)
        node.set_shader_auto(True)
        self.nodes[f"pocket_{pocket_id}"] = node

    def init_pockets(self):
        for pocket_id in self._table.pockets:
            self.init_pocket(pocket_id)

    def render(self):
        super().render()

        # draw table as rectangle
        self.init_table()

        if (
            not self._table.model_descr
            or self._table.model_descr == TableModelDescr.null()
            or not settings.graphics.table
        ):
            # draw cushion_segments as edges
            self.cushion_drawer = LineSegs()
            self.cushion_drawer.setThickness(3)
            self.cushion_drawer.setColor(1, 1, 1)

            self.init_cushion_edges()

            # draw pockets as unfilled circles
            self.pocket_drawer = LineSegs()
            self.pocket_drawer.setThickness(3)
            self.pocket_drawer.setColor(1, 1, 1)
            self.init_pockets()

        self.init_collisions()

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
            "Can't call set_render_state_as_object_state for class 'TableRender'"
        )
