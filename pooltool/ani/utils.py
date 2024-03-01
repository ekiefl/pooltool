#! /usr/bin/env python

from typing import List

import numpy as np
from direct.gui.DirectGui import DGG
from direct.gui.DirectGuiBase import DirectGuiWidget
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import LVector3, NodePath, PGItem, Quat, Vec3, Vec4

import pooltool.ptmath as ptmath
from pooltool.ani.fonts import load_font


class CustomOnscreenText(OnscreenText):
    def __init__(self, **kwargs):
        assert "font" not in kwargs, "Cannot modify 'font', use 'font_name' instead"

        if "font_name" in kwargs:
            font = load_font(kwargs["font_name"])
            del kwargs["font_name"]
        else:
            font = load_font()
        OnscreenText.__init__(self, font=font, **kwargs)


def get_list_of_Vec3s_from_array(array):
    """array is shape (N, 3)"""
    vec3s = []
    for i in range(array.shape[0]):
        vec3s.append(Vec3(*array[i, :]))

    return vec3s


def as_quaternion(w, t, dQ_0=None) -> List:
    """Convert angular velocities to quaternions

    Notes
    =====
    - This mathematics is taken from the following stackexchange answer:
      https://stackoverflow.com/questions/23503151/how-to-update-quaternion-based-on-3d-gyro-data/41226401
      Though as pointed out by jrichner, the correct quaternions are produced
      only after reversing the order of multiplication.
    """
    dquats = get_infinitesimal_quaternions(w, t, dQ_0)
    dquats = get_quaternion_list_from_array(dquats)

    quats = [dquats[0]]
    for i in range(1, len(dquats)):
        quats.append(quats[i - 1] * dquats[i])

    return quats


def get_infinitesimal_quaternions(w, t, dQ_0=None):
    w_norm = np.linalg.norm(w, axis=1)
    w_unit = ptmath.unit_vector_slow(w, handle_zero=True)

    dt = np.diff(t)
    theta = w_norm[1:] * dt

    # Quaternion looks like m + xi + yj + zk
    dQ_m = np.cos(theta / 2)[:, None]
    dQ_xyz = w_unit[1:] * np.sin(theta / 2)[:, None]
    dQ = np.hstack([dQ_m, dQ_xyz])

    # Since the time elapsed is calculated from a difference of timestamps
    # there is one less datapoint than needed. I remedy this by adding the
    # identity quaternion as the first point
    if dQ_0 is None:
        dQ_0 = np.array([1, 0, 0, 0])
    else:
        dQ_0 = np.array(dQ_0)
    dQ_0 = get_quat_from_vector(dQ_0)

    dQ = np.vstack([dQ_0, dQ])

    return dQ


def get_quaternion_list_from_array(array):
    """array is shape (N, 4)"""
    quats = []
    for i in range(array.shape[0]):
        quats.append(get_quat_from_vector(array[i, :]))

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


def multiply_cw(v, c):
    return LVector3(v[0] * c, v[1] * c, v[2] * c)


def alignTo(obj, other, selfPos, otherPos=None, gap=(0, 0)):
    """
    Usage :
      myGui.alignTo( other, selfPos, otherPos, gap=(x,z) )
        OR
      alignTo( nodepath, other, selfPos, otherPos, gap=(x,z) )

      [+] selfPos is a position in myGui's coordinate space
      [+] otherPos is a position in other's coordinate space
      [x] if otherPos is missing, the same position will be used
      [+] they could be any of :
          LL (lower left)
          UL (upper left)
          LR (lower right)
          UR (upper right)
          C (center)
          CL (center left)
          CR (center right)
          CB (center bottom)
          CT (center top)
          O (origin)
      [+] gap is in the myGui/nodepath's coordinate space
    """
    objNode = obj.node()
    otherNode = other.node()
    if otherPos is None:
        otherPos = selfPos
    if isinstance(objNode, PGItem):
        wB = Vec4(objNode.getFrame())
    else:
        isOrigin = selfPos == 0
        if not NodePath(obj).getBounds().isEmpty() and not isOrigin:
            minb, maxb = obj.getTightBounds()
        else:
            minb = maxb = obj.getPos()
            if isOrigin:
                selfPos = (0,) * 2  # any point is OK
        minb = obj.getRelativePoint(obj.getParent(), minb)
        maxb = obj.getRelativePoint(obj.getParent(), maxb)
        wB = Vec4(minb[0], maxb[0], minb[2], maxb[2])
    if isinstance(otherNode, PGItem):
        oB = Vec4(otherNode.getFrame())
    else:
        isOrigin = otherPos == 0
        if not NodePath(other).getBounds().isEmpty() and not isOrigin:
            minb, maxb = other.getTightBounds()
        else:
            minb = maxb = other.getPos()
            if isOrigin:
                otherPos = (0,) * 2  # any point is OK
        minb = other.getRelativePoint(other.getParent(), minb)
        maxb = other.getRelativePoint(other.getParent(), maxb)
        oB = Vec4(minb[0], maxb[0], minb[2], maxb[2])
    if selfPos[0] < 0:  # center
        selfPos = (0, selfPos[1])
        wB.setX(0.5 * (wB[0] + wB[1]))
    if selfPos[1] < 0:  # center
        selfPos = (selfPos[0], 2)
        wB.setZ(0.5 * (wB[2] + wB[3]))
    if otherPos[0] < 0:  # center
        otherPos = (0, otherPos[1])
        oB.setX(0.5 * (oB[0] + oB[1]))
    if otherPos[1] < 0:  # center
        otherPos = (otherPos[0], 2)
        oB.setZ(0.5 * (oB[2] + oB[3]))
    Xsign = 1 - 2 * (selfPos[0] == otherPos[0])
    if (Xsign == -1 and selfPos[0] == 1) or (Xsign == 1 and selfPos[0] == 0):
        Xsign *= -1
    Zsign = 1 - 2 * (selfPos[1] == otherPos[1])
    if (Zsign == -1 and selfPos[1] == 3) or (Zsign == 1 and selfPos[1] == 2):
        Zsign *= -1
    obj.setX(
        other, oB[otherPos[0]] - (wB[selfPos[0]] + gap[0] * Xsign) * obj.getSx(other)
    )
    obj.setZ(
        other, oB[otherPos[1]] - (wB[selfPos[1]] + gap[1] * Zsign) * obj.getSz(other)
    )


DirectGuiWidget.alignTo = alignTo
LL = DGG.LL = (0, 2)  # LOWER LEFT
UL = DGG.UL = (0, 3)  # UPPER LEFT
LR = DGG.LR = (1, 2)  # LOWER RIGHT
UR = DGG.UR = (1, 3)  # UPPER RIGHT
C = DGG.C = (-1,) * 2  # CENTER
CL = DGG.CL = (0, -1)  # CENTER LEFT
CR = DGG.CR = (1, -1)  # CENTER RIGHT
CB = DGG.CB = (-1, 2)  # CENTER BOTTOM
CT = DGG.CT = (-1, 3)  # CENTER TOP
OO = DGG.O = 0  # ORIGIN
