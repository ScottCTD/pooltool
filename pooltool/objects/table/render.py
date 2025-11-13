import numpy as np
from panda3d.core import (CollisionNode, CollisionPlane, Geom, GeomNode,
                          GeomTriangles, GeomVertexData, GeomVertexFormat,
                          GeomVertexWriter, LineSegs, Plane, Point3, Vec3)

from pooltool.ani.globals import Global
from pooltool.config import settings
from pooltool.objects.datatypes import Render
from pooltool.objects.table.collection import TableName
from pooltool.objects.table.datatypes import Table, TableModelDescr, TableType


class TableRender(Render):
    """A class for all pool table associated panda3d nodes"""

    def __init__(self, table: Table):
        self._table = table
        Render.__init__(self)

    def init_table(self):
        if (
            not self._table.model_descr
            or self._table.model_descr == TableModelDescr.null()
            or not settings.graphics.table
        ):
            # Rectangular playing surface (not a real table)
            model = Global.loader.loadModel(
                TableModelDescr.null().get_path(
                    settings.graphics.physical_based_rendering
                )
            )
            node = Global.render.find("scene").attachNewNode("table")
            model.reparentTo(node)
            model.setScale(self._table.w, self._table.l, 1)
        else:
            # Real table
            node = Global.loader.loadModel(
                self._table.model_descr.get_path(
                    settings.graphics.physical_based_rendering
                )
            )
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

        # Make 4 planes
        # For diagram of cushion ids, see
        # https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-cushion-collision-times
        for cushion_id in ["3", "9", "12", "18"]:
            cushion = self._table.cushion_segments.linear[cushion_id]

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
        circle = self.draw_circle(
            self.pocket_drawer, pocket.center, pocket.radius, 100)
        node = Global.render.find("scene").find("table").attachNewNode(circle)
        node.set_shader_auto(True)
        self.nodes[f"pocket_{pocket_id}"] = node
        self._attach_pocket_marker(pocket_id, pocket)

    def init_pockets(self):
        for pocket_id in self._table.pockets:
            self.init_pocket(pocket_id)

    def render(self):
        super().render()

        # draw table as rectangle
        self.init_table()

        # Always draw overlays so real tables get visual aids too.
        draw_wireframe = (
            not self._table.model_descr
            or self._table.model_descr == TableModelDescr.null()
            or not settings.graphics.table
            or self._table.model_descr.name == TableName.SNOOKER_GENERIC
        )
        thickness = 3 if draw_wireframe else 2

        self.cushion_drawer = LineSegs()
        self.cushion_drawer.setThickness(thickness)
        self.cushion_drawer.setColor(*CUSHION_COLOR)
        self.init_cushion_edges()

        self.pocket_drawer = LineSegs()
        self.pocket_drawer.setThickness(thickness)
        self.pocket_drawer.setColor(*POCKET_OUTLINE_COLOR)
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
        raise NotImplementedError(
            "Can't call get_render_state for class 'TableRender'")

    def set_object_state_as_render_state(self):
        raise NotImplementedError(
            "Can't call set_object_state_as_render_state for class 'TableRender'"
        )

    def set_render_state_as_object_state(self):
        raise NotImplementedError(
            "Can't call set_render_state_as_object_state for class 'TableRender'"
        )

    def _attach_pocket_marker(self, pocket_id: str, pocket):
        """Create a filled marker near the specified pocket."""
        color = POCKET_MARKER_COLORS.get(pocket_id, DEFAULT_MARKER_COLOR)
        table_center = np.array([self._table.w / 2, self._table.l / 2])
        center_xy = np.array([pocket.center[0], pocket.center[1]])
        direction = center_xy - table_center
        norm = np.linalg.norm(direction)
        if norm == 0:
            direction = np.array([0.0, 1.0])
        else:
            direction = direction / norm

        inset = pocket.radius * MARKER_INSET_SCALE
        marker_center = np.array(
            [
                pocket.center[0] - direction[0] * inset,
                pocket.center[1] - direction[1] * inset,
                pocket.center[2] + MARKER_Z_OFFSET,
            ]
        )
        marker_radius = pocket.radius * MARKER_BASE_RADIUS_SCALE
        node = self.nodes["table"].attachNewNode(
            self._create_filled_circle(marker_center, marker_radius, color)
        )
        node.setShaderAuto()
        self.nodes[f"pocket_marker_{pocket_id}"] = node

    def _create_filled_circle(
        self,
        center: np.ndarray,
        radius: float,
        color: tuple[float, float, float, float],
        segments: int = 48,
    ) -> GeomNode:
        """Generate a filled 2D circle mesh."""
        vdata = GeomVertexData(
            "pocket_marker", GeomVertexFormat.getV3c4(), Geom.UHStatic
        )
        vertex = GeomVertexWriter(vdata, "vertex")
        colors = GeomVertexWriter(vdata, "color")

        vertex.addData3(center[0], center[1], center[2])
        colors.addData4f(*color)

        for i in range(segments + 1):
            theta = (2 * np.pi * i) / segments
            x = center[0] + radius * np.cos(theta)
            y = center[1] + radius * np.sin(theta)
            vertex.addData3(x, y, center[2])
            colors.addData4f(*color)

        triangles = GeomTriangles(Geom.UHStatic)
        for i in range(1, segments):
            triangles.addVertices(0, i, i + 1)
        triangles.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(triangles)

        node = GeomNode(f"pocket_marker_geom")
        node.addGeom(geom)
        return node


MARKER_BASE_RADIUS_SCALE = 0.55
MARKER_INSET_SCALE = -2
MARKER_Z_OFFSET = 0.06
POCKET_MARKER_COLORS = {
    "lb": (1.00, 0.00, 0.00, 1.0),  # Red
    "lc": (1.00, 0.40, 0.00, 1.0),  # Orange
    "lt": (0.75, 0.75, 0.75, 1.0),  # Grey
    "rb": (0.00, 1.00, 0.25, 1.0),  # Green
    "rc": (0.00, 0.25, 1.00, 1.0),  # Blue
    "rt": (0.75, 0.00, 1.00, 1.0),  # Purple
}

DEFAULT_MARKER_COLOR = (0.95, 0.6, 0.2, 1.0)
CUSHION_COLOR = (0.15, 0.85, 0.35, 1.0)
POCKET_OUTLINE_COLOR = (0.9, 0.4, 0.2, 1.0)
