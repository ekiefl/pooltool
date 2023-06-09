#!/usr/bin/env python

from direct.motiontrail.MotionTrail import MotionTrail
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Point3, Vec4

base = ShowBase()
base.set_background_color(0.1, 0.1, 0.1, 1)

base.cam.set_pos(0, -128, 32)
base.cam.look_at(render)

flame_colors = (
    Vec4(1.0, 0.0, 0.0, 1),
    Vec4(1.0, 0.2, 0.0, 1),
    Vec4(1.0, 0.7, 0.0, 1),
    Vec4(0.0, 0.0, 0.2, 1),
)

# A NodePath, rotating in empty space.
pivot = render.attach_new_node("pivot")
pivot.posInterval(3, Point3(-100, -100, 0), startPos=(0, 100, 0)).loop()

# A little chunk of charcoal that rotates along the pivot with an offset.
charcoal = loader.load_model("models/smiley").copy_to(pivot)
charcoal.set_color(flame_colors[0] * 1.5)
charcoal.set_x(32)

# It leaves a trail of flames.
fire_trail = MotionTrail("fire trail", charcoal)
fire_trail.register_motion_trail()
fire_trail.geom_node_path.reparent_to(render)

fire_trail.time_window = 0.5  # Length of trail

# A circle as the trail's shape, by plotting a NodePath in a circle.
center = render.attach_new_node("center")
around = center.attach_new_node("around")
around.set_z(4)
res = 3  # Amount of angles in "circle". Higher is smoother.
for i in range(res + 1):
    center.set_r((360 / res) * i)
    vertex_pos = around.get_pos(render)
    fire_trail.add_vertex(vertex_pos)

    start_color = flame_colors[i % len(flame_colors)] * 1.7
    end_color = Vec4(1, 1, 0, 1)
    fire_trail.set_vertex_color(i, start_color, end_color)

base.run()
