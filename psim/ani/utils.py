#! /usr/bin/env python
"""File for animating utilities in 3D (panda3d) and 2D (pygame)"""

from panda3d.core import (
    Quat,
    lookAt,
    GeomVertexFormat,
    GeomVertexData,
    Geom,
    GeomTriangles,
    GeomVertexWriter,
    GeomNode,
    LVector3,
)


def get_quat_from_vector(v, normalize=True):
    """Get Quat object from 4-d vector"""
    quat = Quat()
    quat.setR(v[0])
    quat.setI(v[1])
    quat.setJ(v[2])
    quat.setK(v[3])

    if normalize:
        quat.normalize()

    return quat


def normalize(*args):
    myVec = LVector3(*args)
    myVec.normalize()
    return myVec


def make_square(x1, y1, z1, x2, y2, z2, name='square'):
    fmt = GeomVertexFormat.getV3n3cpt2()
    vdata = GeomVertexData('square', fmt, Geom.UHDynamic)

    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')

    # make sure we draw the sqaure in the right plane
    if x1 != x2:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y1, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y2, z2)

        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))

    else:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y2, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y1, z2)

        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))

    tris = GeomTriangles(Geom.UHDynamic)
    tris.addVertices(0, 1, 3)
    tris.addVertices(1, 2, 3)

    square = Geom(vdata)
    square.addPrimitive(tris)
    square_node = GeomNode(name)
    square_node.addGeom(square)

    return square_node

