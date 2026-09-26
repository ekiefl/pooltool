import numpy as np
from direct.gui.DirectGui import (
    DGG,
    DirectButton,
    DirectFrame,
    DirectLabel,
)
from direct.gui.DirectGuiBase import DirectGuiWidget
from direct.gui.OnscreenText import OnscreenText
from numba import jit
from numpy.typing import NDArray
from panda3d.core import (
    LVector3,
    NodePath,
    PGItem,
    Quat,
    TextNode,
    Vec3,
    Vec4,
)

import pooltool.constants as const
from pooltool.ani.fonts import load_font
from pooltool.ani.globals import Global


class CustomOnscreenText(OnscreenText):
    def __init__(self, **kwargs):
        assert "font" not in kwargs, "Cannot modify 'font', use 'font_name' instead"

        if "font_name" in kwargs:
            font = load_font(kwargs["font_name"])
            del kwargs["font_name"]
        else:
            font = load_font()
        OnscreenText.__init__(self, font=font, **kwargs)


class TextOverlay:
    def __init__(
        self,
        title="",
        frame_color=(1, 1, 1, 1),
        title_pos=(0, 0, 0.8),
        text_fg=(0, 0, 0, 1),
        text_scale=0.07,
        font_name="LABTSECS",
    ):
        self.titleMenuBackdrop = DirectFrame(
            frameColor=frame_color,
            frameSize=(-1, 1, -1, 1),
            parent=Global.render2d,
        )

        self._text_scale = text_scale
        self._move = 0.12

        self.titleMenu = DirectFrame(frameColor=(1, 1, 1, 0))

        font = load_font(font_name)

        self.title = DirectLabel(
            text=title,
            text_font=font,
            scale=self._text_scale * 1.5,
            pos=title_pos,
            parent=self.titleMenu,
            relief=None,
            text_fg=text_fg,
        )

        self._next_x, self._next_y = -0.5, 0.6
        self._num_elements = 0

        self.hide()

    def add_button(self, text, command=None, **kwargs):
        """Add a button at a location based on self.next_x and self.next_y"""
        button = DirectButton(
            text=text,
            command=command,
            text_align=TextNode.ACenter,
            **kwargs,
        )
        button.reparentTo(self.titleMenu)
        button.setPos((self._next_x, 0, self._next_y))
        self._get_next_pos()

        return button

    def _get_next_pos(self):
        self._next_y -= self._move
        if self._next_y <= -1:
            self._next_y = 0.6
            self._next_x += 0.5
        self._num_elements += 1

    def hide(self):
        self.titleMenuBackdrop.hide()
        self.titleMenu.hide()

    def show(self):
        self.titleMenuBackdrop.show()
        self.titleMenu.show()


def get_list_of_Vec3s_from_array(array):
    """array is shape (N, 3)"""
    vec3s = []
    for i in range(array.shape[0]):
        vec3s.append(Vec3(*array[i, :]))

    return vec3s


@jit(nopython=True, cache=const.use_numba_cache)
def as_quaternion(
    w: NDArray[np.float64], t: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Integrate angular velocities into orientation quaternions

    Args:
        w:
            Angular velocities along a trajectory, shape ``(N, 3)``.
        t:
            The timestamps of the angular velocities, shape ``(N,)``.

    Returns:
        Unit quaternions as ``(r, i, j, k)`` rows, shape ``(N, 4)``. The first is the
        identity, and each following row is the previous orientation rotated by its
        angular velocity over the time elapsed since the previous timestamp.

    Notes:
        - This mathematics is taken from the following stackexchange answer:
          https://stackoverflow.com/questions/23503151/how-to-update-quaternion-based-on-3d-gyro-data/41226401
          Though as pointed out by jrichner, the correct quaternions are produced only
          after reversing the order of multiplication.
    """
    num = len(t)
    quats = np.empty((num, 4))
    quats[0, 0] = 1.0
    quats[0, 1:] = 0.0

    for i in range(1, num):
        wx, wy, wz = w[i, 0], w[i, 1], w[i, 2]
        norm = np.sqrt(wx * wx + wy * wy + wz * wz)
        if norm == 0.0:
            quats[i] = quats[i - 1]
            continue

        half = 0.5 * norm * (t[i] - t[i - 1])
        scale = np.sin(half) / norm
        dr, di, dj, dk = np.cos(half), wx * scale, wy * scale, wz * scale
        r, a, b, c = quats[i - 1]

        quats[i, 0] = dr * r - di * a - dj * b - dk * c
        quats[i, 1] = dr * a + di * r + dj * c - dk * b
        quats[i, 2] = dr * b - di * c + dj * r + dk * a
        quats[i, 3] = dr * c + di * b - dj * a + dk * r
        quats[i] /= np.sqrt((quats[i] ** 2).sum())

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
