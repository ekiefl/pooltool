#! /usr/bin/env python
"""File for animating utilities in 3D (panda3d) and 2D (pygame)"""

from panda3d.core import *


def get_list_of_Vec3s_from_array(array):
    """array is shape (N, 3)"""
    vec3s = []
    for i in range(array.shape[0]):
        vec3s.append(Vec3(*array[i,:]))

    return vec3s


def get_quaternion_list_from_array(array):
    """array is shape (N, 4)"""
    quats = []
    for i in range(array.shape[0]):
        quats.append(get_quat_from_vector(array[i,:]))

    return quats


def get_quat_from_vector(v, normalize=True):
    """Get Quat object from 4-d vector"""
    quat = Quat(Vec4(*v))

    if normalize:
        quat.normalize()

    return quat


def normalize(*args):
    myVec = LVector3(*args)
    myVec.normalize()
    return myVec


def make_rectangle(x1, y1, z1, x2, y2, z2, name='rectangle'):
    fmt = GeomVertexFormat.getV3n3cpt2()
    vdata = GeomVertexData('rectangle', fmt, Geom.UHDynamic)

    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')
    #texcoord = GeomVertexWriter(vdata, 'texcoord')

    # make sure we draw the sqaure in the right plane
    if x1 != x2:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y1, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y2, z2)

        # FIXME calculate the norm
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))

    else:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y2, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y1, z2)

        # FIXME calculate the norm
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))
        normal.addData3(normalize(0,0,1))

    # FIXME calculate with a scale or something
    #scale = 1
    #texcoord.addData2f(0.0, scale)
    #texcoord.addData2f(0.0, 0.0)
    #texcoord.addData2f(scale, 0.0)
    #texcoord.addData2f(scale, scale)

    tris = GeomTriangles(Geom.UHDynamic)
    tris.addVertices(0, 1, 3)
    tris.addVertices(1, 2, 3)

    rectangle = Geom(vdata)
    rectangle.addPrimitive(tris)
    rectangle_node = GeomNode(name)
    rectangle_node.addGeom(rectangle)

    return rectangle_node

