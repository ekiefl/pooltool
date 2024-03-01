#! /usr/bin/env python

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import numpy as np
from attrs import define
from panda3d.core import LVecBase3f, TransparencyAttrib

import pooltool.ani as ani
import pooltool.ani.utils as autils
from pooltool.ani.globals import Global, require_showbase
from pooltool.ani.mouse import mouse
from pooltool.objects.table.datatypes import Table
from pooltool.ptmath import wiggle
from pooltool.serialize import conversion


class Camera:
    @require_showbase
    def init(self) -> None:
        self.node = Global.base.camera
        self.lens = Global.base.camLens
        self.lens.setNear(0.02)

        self.states: Dict[str, CameraState] = {}
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

    @property
    def state(self) -> CameraState:
        return CameraState.from_camera(self)

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
        """Rotate about camera fixation based on mouse movement for the current frame"""
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

    def move_fixation(self, pos):
        """Move the point that the camera is fixated upon

        Args:
            pos:
                The (x, y, z) coordinates of the point of fixationw w w
        """
        self.fixation.setPos(pos)

    def move_fixation_via_mouse(self):
        """Move camera fixation based on mouse movement for the current frame"""
        with mouse:
            dxp, dyp = mouse.get_dx(), mouse.get_dy()

        h = self.fixation.getH() * np.pi / 180 + np.pi / 2
        dx = dxp * np.cos(h) - dyp * np.sin(h)
        dy = dxp * np.sin(h) + dyp * np.cos(h)

        self.fixation.setX(self.fixation.getX() + dx * ani.move_sensitivity)
        self.fixation.setY(self.fixation.getY() + dy * ani.move_sensitivity)

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
        self.fixation = node.attachNewNode("camera_fixation")
        self.fixation.setH(-90)

        # create the fixation object. It's just the panda3d built in smiley sphere. The
        # smile faces away from the camera.
        self.fixation_object = Global.loader.loadModel("smiley.egg")
        self.fixation_object.setScale(0.0025)
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

    def store_state(self, name, overwrite=False):
        """Store the current camera state in self.states"""
        if name in self.states and not overwrite:
            raise Exception(f"Camera :: '{name}' is already a camera state")

        self.states[name] = self.state
        self.last_state = name

    def load_saved_state(self, name, ok_if_not_exists=False):
        """Load a named camera state found in self.states"""
        if name not in self.states:
            if ok_if_not_exists:
                return
            else:
                raise Exception(f"Camera :: '{name}' is not a camera state")

        self.load_state(self.states[name])

    def load_state(self, camera_state: CameraState):
        """Load a camera state"""
        self.node.setPos(camera_state.cam_pos)
        self.node.setHpr(camera_state.cam_hpr)

        if self.fixated:
            self.fixation.setPos(camera_state.fixation_pos)
            self.fixation.setHpr(camera_state.fixation_hpr)

    def _scale_fixation_object(self):
        """Scale the camera's focus object

        The focus marker is a small dot to show where the camera is centered, and where
        it rotates about. This helps a lot in navigating the camera effectively. Here
        the marker is scaled so that it is always a constant size, regardless of how
        zoomed in or out the camera is.
        """
        # `dist` is the distance from the camera to the focus object and is equivalent
        # to: cam_pos, focus_pos = camera.node.getPos(render),
        # camera.fixation_object.getPos(render) dist = (cam_pos - focus_pos).length()
        dist = self.node.getX()
        self.fixation_object.setScale(0.0012 * min(dist, 1.5))


Vec3D = Tuple[float, float, float]


def _vec_to_tuple(vec: LVecBase3f) -> Vec3D:
    return vec.x, vec.y, vec.z


@define(frozen=True)
class CameraState:
    cam_hpr: Vec3D
    cam_pos: Vec3D
    fixation_hpr: Optional[Vec3D]
    fixation_pos: Optional[Vec3D]

    def to_json(self, path: Union[str, Path]):
        conversion.unstructure_to(self, path, fmt="json")

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> CameraState:
        return conversion.structure_from(path, cls, fmt="json")

    @classmethod
    def from_camera(cls, camera: Camera) -> CameraState:
        return cls(
            cam_hpr=_vec_to_tuple(camera.node.getHpr()),
            cam_pos=_vec_to_tuple(camera.node.getPos()),
            fixation_hpr=(
                _vec_to_tuple(camera.fixation.getHpr()) if camera.fixated else None
            ),
            fixation_pos=(
                _vec_to_tuple(camera.fixation.getPos()) if camera.fixated else None
            ),
        )

    @classmethod
    def random(cls, table: Table) -> CameraState:
        """Generate a random camera state, within reason

        Args:
            table:
                This is needed so the fixation point is somewhere on the playing surface
        """

        def rand(m, M):
            return (M - m) * np.random.rand() + m

        # The camera fixates on a point (fix_x, fix_y) that is within 1/4 the table's
        # width from the table's center
        fix_rad = table.w / 4
        r = rand(0, fix_rad)
        ang = rand(0, 2 * np.pi)
        fix_x = r * np.cos(ang) + table.w / 2
        fix_y = r * np.sin(ang) + table.l / 2

        # Rotate the camera about the fixation point such that it faces the center, with
        # some added variation
        deg = wiggle(
            np.rad2deg(np.arctan2(table.l / 2 - fix_y, table.w / 2 - fix_x)) + 180, 20
        )

        return cls(
            cam_hpr=(90, 0, rand(-10, 10)),
            cam_pos=(rand(1.5, 3.0), 0, 0),
            fixation_hpr=(deg, 0, rand(-45, -10)),
            fixation_pos=(fix_x, fix_y, 0),
        )
