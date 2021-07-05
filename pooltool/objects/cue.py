#! /usr/bin/env python

import pooltool.utils as utils

from pooltool.ani import model_paths
from pooltool.events import StickBallCollision
from pooltool.objects import *

import numpy as np

from panda3d.core import *
from direct.interval.IntervalGlobal import *

class CueRender(Render):
    def __init__(self):
        Render.__init__(self)

        self.follow = None
        self.stroke_sequence = None
        self.stroke_clock = ClockObject()

        self.stroke_pos = []
        self.stroke_time = []


    def init_model(self, R=pooltool.R):
        cue_stick_model = loader.loadModel(model_paths['cylinder'])
        cue_stick_model.setName('cue_stick_model')

        m, M = cue_stick_model.getTightBounds()
        model_R, model_l = (M-m)[0]/2, (M-m)[2]

        # Rescale model to match cue dimensions
        cue_stick_model.setSx(self.tip_radius / model_R)
        cue_stick_model.setSy(self.tip_radius / model_R)
        cue_stick_model.setSz(self.length / model_l)

        cue_stick_tex = loader.loadTexture(model_paths['red_cloth'])
        cue_stick_model.setTexture(cue_stick_tex)
        cue_stick_model.setTexScale(TextureStage.getDefault(), 0.01, 0.01)

        cue_stick = render.find('scene').find('cloth').attachNewNode('cue_stick')
        cue_stick_model.reparentTo(cue_stick)

        self.nodes['cue_stick'] = cue_stick


    def init_focus(self, ball):
        # FIXME this is a potentially memory-leaky reference to an object
        self.follow = ball

        cue_stick = self.get_node('cue_stick')

        cue_stick.find('cue_stick_model').setPos(0, 0, self.length/2 + 1.2*ball.R)
        cue_stick.setP(90)
        cue_stick.setH(90)

        cue_stick_focus = render.find('scene').find('cloth').attachNewNode("cue_stick_focus")
        self.nodes['cue_stick_focus'] = cue_stick_focus

        self.update_focus()
        cue_stick.reparentTo(cue_stick_focus)


    def track_stroke(self):
        """Initialize variables for storing cue position during stroke"""
        self.stroke_pos = []
        self.stroke_time = []
        self.stroke_clock.reset()


    def append_stroke_data(self):
        """Append current cue position and timestamp to the cue tracking data"""
        cue_stick = self.nodes['cue_stick']

        self.stroke_pos.append(self.nodes['cue_stick'].getX())
        self.stroke_time.append(self.stroke_clock.getRealTime())


    def set_stroke_sequence(self):
        """Initiate a stroke sequence based off of self.stroke_pos and self.stroke_time"""

        cue_stick = self.nodes['cue_stick']
        self.stroke_sequence = Sequence()

        # If the stroke is longer than max_time seconds, truncate to max_time
        max_time = 1.0
        backstroke_time, apex_time, strike_time = self.get_stroke_times()
        if strike_time > max_time:
            idx = min(range(len(self.stroke_pos)), key=lambda i: abs(self.stroke_pos[i] - (strike_time - max_time)))
            self.stroke_pos = self.stroke_pos[idx:]
            self.stroke_time = self.stroke_time[idx:]

        xs = np.array(self.stroke_pos)
        dts = np.diff(np.array(self.stroke_time))

        y, z = cue_stick.getY(), cue_stick.getZ()

        for i in range(len(dts)):
            self.stroke_sequence.append(LerpPosInterval(
                nodePath = cue_stick,
                duration = dts[i],
                pos = Vec3(xs[i+1], y, z)
            ))


    def get_stroke_times(self, as_index=False):
        """Get key moments in the trajectory of the stroke

        Parameters
        ==========
        as_index : bool, False
            See Returns

        Returns
        =======
        output : (backstroke, apex, strike)
            Returns a 3-ple of times (or indices of the lists self.stroke_time and self.stroke_pos
            if as_index is True) that describe three critical moments in the cue stick. backstroke is
            start of the backswing, apex is when the cue is at the peak of the backswing, and strike is
            when the cue makes contact.
        """

        apex_pos = 0
        for i, pos in enumerate(self.stroke_pos[::-1]):
            if pos < apex_pos:
                break
            apex_pos = pos
        apex_index = len(self.stroke_pos) - i
        while True:
            if apex_pos == self.stroke_pos[apex_index+1]:
                apex_index += 1
            else:
                break
        apex_time = self.stroke_time[apex_index]

        backstroke_pos = apex_pos
        for j, pos in enumerate(self.stroke_pos[::-1][i:]):
            if pos > backstroke_pos:
                break
            backstroke_pos = pos
        backstroke_index = len(self.stroke_pos) - (i + j)
        while True:
            if backstroke_pos == self.stroke_pos[backstroke_index+1]:
                backstroke_index += 1
            else:
                break
        backstroke_time = self.stroke_time[backstroke_index]

        strike_time = self.stroke_time[-1]
        strike_index = len(self.stroke_time) - 1

        return (backstroke_index, apex_index, strike_index) if as_index else (backstroke_time, apex_time, strike_time)


    def is_shot(self):
        if len(self.stroke_time) < 10:
            # There is only a handful of frames
            return False

        if not any([x > 0 for x in self.stroke_pos]):
            # No backstroke
            return False

        backstroke_time, apex_time, strike_time = self.get_stroke_times()

        if (strike_time - backstroke_time) < 0.3:
            # Stroke is too short
            return False

        return True


    def calc_V0_from_stroke(self):
        """Calculates V0 from the stroke sequence

        Takes the average velocity calculated over the 0.1 seconds preceding the shot. If the time
        between the cue strike and apex of the stroke is less than 0.1 seconds, calculate the average
        velocity since the apex
        """

        backstroke_time, apex_time, strike_time = self.get_stroke_times()

        max_time = 0.1
        if (strike_time - apex_time) < max_time:
            return self.stroke_pos[apex_index]/apex_time

        for i, t in enumerate(self.stroke_time[::-1]):
            if strike_time - t > max_time:
                return self.stroke_pos[::-1][i] / max_time


    def update_focus(self):
        self.nodes['cue_stick_focus'].setPos(self.follow.get_node('ball').getPos())


    def get_render_state(self):
        """Return phi, theta, a, and b as determined by the cue_stick node"""

        cue_stick = self.get_node('cue_stick')
        cue_stick_focus = self.get_node('cue_stick_focus')

        phi = ((cue_stick_focus.getH() + 180) % 360)
        V0 = self.calc_V0_from_stroke()
        cueing_ball = self.follow
        theta = -cue_stick_focus.getR()
        a = -cue_stick.getY()/self.follow.R
        b = cue_stick.getZ()/self.follow.R

        return V0, phi, theta, a, b, cueing_ball


    def set_object_state_as_render_state(self):
        self.V0, self.phi, self.theta, self.a, self.b, self.cueing_ball = self.get_render_state()


    def set_render_state_as_object_state(self):
        # FIXME implement phi, theta, a, and b
        self.update_focus()

        cue_stick = self.get_node('cue_stick')
        cue_stick_focus = self.get_node('cue_stick_focus')

        cue_stick_focus.setH(self.phi + 180) # phi
        cue_stick_focus.setR(-self.theta) # theta
        cue_stick.setY(-self.a * self.follow.R) # a
        cue_stick.setZ(self.b * self.follow.R) # b


    def render(self):
        super().render()
        self.init_model()


class Cue(Object, CueRender):
    object_type = 'cue_stick'

    def __init__(self, M=pooltool.M, length=pooltool.cue_length, tip_radius=pooltool.cue_tip_radius,
                 butt_radius=pooltool.cue_butt_radius, cue_id='cue_stick', brand=None):

        self.id = cue_id
        self.M = M
        self.length = length
        self.tip_radius = tip_radius
        self.butt_radius = butt_radius
        self.brand = brand

        self.V0 = None
        self.phi = None
        self.theta = None
        self.a = None
        self.b = None

        self.cueing_ball = None

        CueRender.__init__(self)


    def reset_state(self):
        self.set_state(V0=0, phi=0, theta=0, a=0, b=0)


    def set_state(self, V0=None, phi=None, theta=None, a=None, b=None, cueing_ball=None):
        """Set the cueing parameters

        Notes
        =====
        - If any parameters are None, they will be left untouched--they will not be set to None
        """

        if V0 is not None: self.V0 = V0
        if phi is not None: self.phi = phi
        if theta is not None: self.theta = theta
        if a is not None: self.a = a
        if b is not None: self.b = b
        if cueing_ball is not None: self.cueing_ball = cueing_ball


    def strike(self, t=None):
        if (self.V0 is None or self.phi is None or self.theta is None or self.a is None or self.b is None):
            raise ValueError("Cue.strike :: Must set V0, phi, theta, a, and b")

        event = StickBallCollision(self, self.cueing_ball, t=t)
        event.resolve()

        return event


    def aim_at(self, pos):
        """Set phi to aim at a 3D position

        Parameters
        ==========
        pos : array-like
            A length-3 iterable specifying the x, y, z coordinates of the position to be aimed at
        """

        direction = utils.angle(utils.unit_vector(np.array(pos) - self.cueing_ball.rvw[0]))
        self.set_state(phi = direction * 180/np.pi)




