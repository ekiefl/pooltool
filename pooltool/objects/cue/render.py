from typing import List, Tuple

import numpy as np
from direct.interval.IntervalGlobal import LerpPosInterval, Sequence
from panda3d.core import ClockObject, CollisionNode, CollisionSegment, Vec3

import pooltool.ani as ani
import pooltool.utils as utils
from pooltool.ani.globals import Global
from pooltool.error import ConfigError, StrokeError
from pooltool.objects.ball.render import BallRender
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.datatypes import Render


class CueRender(Render):
    def __init__(self, cue: Cue):
        Render.__init__(self)

        self.follow: BallRender

        self._cue = cue
        self.stroke_clock = ClockObject()
        self.has_focus = False

        self.stroke_pos: List[float] = []
        self.stroke_time: List[float] = []

    def set_object_state_as_render_state(self, skip_V0=False):
        (
            V0,
            self._cue.phi,
            self._cue.theta,
            self._cue.a,
            self._cue.b,
            self._cue.cue_ball_id,
        ) = self.get_render_state()

        if not skip_V0:
            self._cue.V0 = V0

    def set_render_state_as_object_state(self):
        self.match_ball_position()

        cue_stick = self.get_node("cue_stick")
        cue_stick_focus = self.get_node("cue_stick_focus")

        cue_stick_focus.setH(self._cue.phi + 180)  # phi
        cue_stick_focus.setR(-self._cue.theta)  # theta
        cue_stick.setY(-self._cue.a * self.follow._ball.params.R)  # a
        cue_stick.setZ(self._cue.b * self.follow._ball.params.R)  # b

    def init_model(self):
        path = utils.panda_path(ani.model_dir / "cue" / "cue.glb")
        cue_stick_model = Global.loader.loadModel(path)
        cue_stick_model.setName("cue_stick_model")

        cue_stick = Global.render.find("scene").find("table").attachNewNode("cue_stick")
        cue_stick_model.reparentTo(cue_stick)

        self.nodes["cue_stick"] = cue_stick
        self.nodes["cue_stick_model"] = cue_stick_model

    def init_focus(self, ball: BallRender):
        self.follow = ball

        self.get_node("cue_stick_model").setPos(self.follow._ball.params.R, 0, 0)

        cue_stick_focus = (
            Global.render.find("scene").find("table").attachNewNode("cue_stick_focus")
        )
        self.nodes["cue_stick_focus"] = cue_stick_focus

        self.match_ball_position()
        self.get_node("cue_stick").reparentTo(cue_stick_focus)

        self.has_focus = True

    def init_collision_handling(self, collision_handler):
        if not ani.settings["gameplay"]["cue_collision"]:
            return

        if not self.rendered:
            raise ConfigError(
                "Cue.init_collision_handling :: Cue has not been rendered, "
                "so collision handling cannot be initialized."
            )

        bounds = self.get_node("cue_stick").get_tight_bounds()

        x = 0
        X = bounds[1][0] - bounds[0][0]

        cnode = CollisionNode("cue_cseg")
        cnode.set_into_collide_mask(0)
        collision_node = self.get_node("cue_stick_model").attachNewNode(cnode)
        collision_node.node().addSolid(CollisionSegment(x, 0, 0, X, 0, 0))

        self.nodes["cue_cseg"] = collision_node
        Global.base.cTrav.addCollider(collision_node, collision_handler)

        if ani.settings["graphics"]["debug"]:
            collision_node.show()

    def get_length(self):
        bounds = self.get_node("cue_stick").get_tight_bounds()
        return bounds[1][0] - bounds[0][0]

    def track_stroke(self):
        """Initialize variables for storing cue position during stroke"""
        self.stroke_pos = []
        self.stroke_time = []
        self.stroke_clock.reset()

    def append_stroke_data(self):
        """Append current cue position and timestamp to the cue tracking data"""
        self.stroke_pos.append(self.get_node("cue_stick").getX())
        self.stroke_time.append(self.stroke_clock.getRealTime())

    def get_stroke_sequence(self) -> Sequence:
        """Init a stroke sequence based off of self.stroke_pos and self.stroke_time"""

        cue_stick = self.get_node("cue_stick")
        stroke_sequence = Sequence()

        # If the stroke is longer than max_time seconds, truncate to max_time
        max_time = 1.0
        _, _, strike_time = self.get_stroke_times()
        if strike_time > max_time:
            idx = min(
                range(len(self.stroke_pos)),
                key=lambda i: abs(self.stroke_pos[i] - (strike_time - max_time)),
            )
            self.stroke_pos = self.stroke_pos[idx:]
            self.stroke_time = self.stroke_time[idx:]

        xs = np.array(self.stroke_pos)
        dts = np.diff(np.array(self.stroke_time))

        y, z = cue_stick.getY(), cue_stick.getZ()

        for i in range(len(dts)):
            stroke_sequence.append(
                LerpPosInterval(
                    nodePath=cue_stick, duration=dts[i], pos=Vec3(xs[i + 1], y, z)
                )
            )

        return stroke_sequence

    def get_stroke_times(self, as_index=False):
        """Get key moments in the trajectory of the stroke

        Args:
            as_index:
                See Returns

        Returns:
            (backstroke, apex, strike):
                Returns a 3-ple of times (or indices of the lists self.stroke_time and
                self.stroke_pos if as_index is True) that describe three critical
                moments in the cue stick. backstroke is start of the backswing, apex is
                when the cue is at the peak of the backswing, and strike is when the cue
                makes contact.
        """
        if not self.stroke_pos:
            return (0, 0, 0)

        # Find the index of the apex (highest point in the backswing)
        apex_index = self.stroke_pos.index(max(self.stroke_pos))
        apex_time = self.stroke_time[apex_index]

        # Find the index of the backstroke start (lowest point before the apex)
        backstroke_index = self.stroke_pos.index(min(self.stroke_pos[: apex_index + 1]))
        backstroke_time = self.stroke_time[backstroke_index]

        # The last position in the list is considered the strike
        strike_index = len(self.stroke_pos) - 1
        strike_time = self.stroke_time[strike_index]

        if as_index:
            return (backstroke_index, apex_index, strike_index)
        else:
            return (backstroke_time, apex_time, strike_time)

    def is_shot(self):
        if len(self.stroke_time) < 10:
            # There is only a handful of frames
            return False

        if not any([x > 0 for x in self.stroke_pos]):
            # No backstroke
            return False

        backstroke_time, _, strike_time = self.get_stroke_times()

        if (strike_time - backstroke_time) < 0.3:
            # Stroke is too short
            return False

        return True

    def calc_V0_from_stroke(self):
        """Calculates V0 from the stroke sequence

        Takes the average velocity calculated over the 0.1 seconds preceding the shot.
        If the time between the cue strike and apex of the stroke is less than 0.1
        seconds, calculate the average velocity since the apex
        """

        try:
            _, apex_time, strike_time = self.get_stroke_times()
        except IndexError:
            raise StrokeError("Unresolved edge case")

        max_time = 0.1
        if (strike_time - apex_time) < max_time:
            raise StrokeError("Unresolved edge case")

        for i, t in enumerate(self.stroke_time[::-1]):
            if strike_time - t > max_time:
                return self.stroke_pos[::-1][i] / max_time

    def match_ball_position(self):
        """Update the cue stick's position to match the cueing ball's position"""
        self.get_node("cue_stick_focus").setPos(self.follow.get_node("pos").getPos())

    def get_render_state(self) -> Tuple[float, float, float, float, float, str]:
        """Return phi, theta, V0, a, and b as determined by the cue_stick node"""

        cue_stick = self.get_node("cue_stick")
        cue_stick_focus = self.get_node("cue_stick_focus")

        phi = (cue_stick_focus.getH() + 180) % 360

        try:
            V0 = self.calc_V0_from_stroke()
        except StrokeError:
            V0 = 0.1

        assert V0 is not None

        theta = -cue_stick_focus.getR()
        a = -cue_stick.getY() / self.follow._ball.params.R
        b = cue_stick.getZ() / self.follow._ball.params.R
        ball_id = self.follow._ball.id

        return V0, phi, theta, a, b, ball_id

    def render(self):
        super().render()
        self.init_model()
