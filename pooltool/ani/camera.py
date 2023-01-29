#! /usr/bin/env python

from panda3d.core import TransparencyAttrib

import pooltool.ani as ani
import pooltool.ani.utils as autils
from pooltool.ani.globals import Global, require_showbase
from pooltool.ani.mouse import mouse


class Camera:
    @require_showbase
    def init(self):
        self.node = Global.base.camera
        self.lens = Global.base.camLens
        self.lens.setNear(0.02)

        self.states = {}
        self.last_state = None
        self.fixated = False

    @property
    def phi(self):
        """The angle about the z-axis where +x-axis is phi=0 and +y-axis is phi=90"""
        return (self.fixation.getH() + 180) % 360

    @property
    def theta(self):
        """The zenith angle, where theta=-90 is south pole and theta=90 is north pole"""
        return -self.fixation.getR()

    def zoom(self, s: float):
        """Zoom the camera

        Args:
            s:
                Defines the amount of zoom. Start with with small values between [-1,
                1]. FIXME should be replaced with a more intuitive measure of zoomage.
        """
        self.node.setPos(autils.multiply_cw(self.node.getPos(), 1 - s))
        self._scale_fixation_object()

    def zoom_via_mouse(self):
        """Zoom the camera based on mouse movement for the current frame"""
        with mouse:
            self.zoom(-mouse.get_dy() * ani.zoom_sensitivity)

    def rotate(self, phi=None, theta=None):
        """Rotate about the fixation point

        See properties phi and theta for definitions.
        """
        if phi is not None:
            self.fixation.setH(phi + 180)

        if theta is not None:
            self.fixation.setR(-theta)

    def rotate_via_mouse(self, fine_control: bool = False, theta_only: bool = False):
        if fine_control:
            fx, fy = ani.rotate_fine_sensitivity_x, ani.rotate_fine_sensitivity_y
        else:
            fx, fy = ani.rotate_sensitivity_x, ani.rotate_sensitivity_y

        with mouse:
            dphi = -fx * mouse.get_dx()
            dtheta = -fy * mouse.get_dy()

        theta = self.theta + dtheta
        phi = self.phi + dphi

        if theta > 90:
            theta = 90
        if theta < 0:
            theta = 0

        if theta_only:
            self.rotate(theta=theta)
        else:
            self.rotate(phi=phi, theta=theta)

    def fixate(self, pos, node):
        """Fixate on a position

        This creates a fixation for the camera. The camera always looks at the fixation.
        A small spherical object shows what the camera is fixated on.

        Args:
            pos:
                The (x, y, z) coordinates of the point of fixation.
            node:
                The render node that the coordinates are calculated from. Also becomes
                the parent of the focus and the fixation object.
        """
        self.fixation = node.attachNewNode("camera_focus")
        self.fixation.setH(-90)

        # create the fixation object. It's just the panda3d built in smiley sphere. The
        # smile faces away from the camera.
        self.fixation_object = Global.loader.loadModel("smiley.egg")
        self.fixation_object.setScale(0.005)
        self.fixation_object.setTransparency(TransparencyAttrib.MAlpha)
        self.fixation_object.setAlphaScale(0.4)
        self.fixation_object.setH(-90)
        self.fixation_object.setColor(1, 0, 0, 1)

        # Move 'head' up so you're not staring at the butt of the cue
        self.fixation.setR(-10)

        self.fixation_object.reparentTo(self.fixation)
        self.fixation.setPos(*pos)
        self.node.reparentTo(self.fixation)
        self.node.setPos(2, 0, 0)
        self.node.lookAt(self.fixation)
        self.fixated = True

    def update_fixation(self, pos):
        self.fixation.setPos(pos)

    def get_state(self):
        return {
            "CamHpr": self.node.getHpr(),
            "CamPos": self.node.getPos(),
            "FocusHpr": self.fixation.getHpr() if self.fixated else None,
            "FocusPos": self.fixation.getPos() if self.fixated else None,
        }

    def store_state(self, name, overwrite=False):
        if name in self.states and not overwrite:
            raise Exception(f"Camera :: '{name}' is already a camera state")

        self.states[name] = self.get_state()
        self.last_state = name

    def load_state(self, name, ok_if_not_exists=False):
        if name not in self.states:
            if ok_if_not_exists:
                return
            else:
                raise Exception(f"Camera :: '{name}' is not a camera state")

        self.node.setPos(self.states[name]["CamPos"])
        self.node.setHpr(self.states[name]["CamHpr"])

        if self.fixated:
            self.fixation.setPos(self.states[name]["FocusPos"])
            self.fixation.setHpr(self.states[name]["FocusHpr"])

    def _scale_fixation_object(self):
        """Scale the camera's focus object

        The focus marker is a small dot to show where the camera is centered, and where
        it rotates about. This helps a lot in navigating the camera effectively. Here
        the marker is scaled so that it is always a constant size, regardless of how
        zoomed in or out the camera is.
        """
        # `dist` is the distance from the camera to the focus object and is equivalent
        # to: cam_pos, focus_pos = camera.node.getPos(render),
        # camera.focus_object.getPos(render) dist = (cam_pos - focus_pos).length()
        dist = self.node.getX()
        self.fixation_object.setScale(0.002 * dist)


camera = Camera()
