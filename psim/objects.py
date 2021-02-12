#! /usr/bin/env python

import psim
import psim.ani.utils as autils
import psim.utils as utils
import psim.physics as physics

from psim.ani import model_paths
from psim.events import *

import numpy as np

from abc import ABC, abstractmethod
from panda3d.core import *
from direct.interval.IntervalGlobal import *



class Object(object):
    object_type = None

    def __init__(self):
        if self.object_type is None:
            raise NotImplementedError("Child classes of Object must have 'object_type' attribute")


class NonObject(Object):
    object_type = 'none'


class DummyBall(NonObject):
    s = psim.stationary


class Render(ABC):
    def __init__(self):
        """A base class for rendering physical pool objects

        This class stores base operations on panda3d nodes that are associated with any pool objects
        such as cues, tables, and balls.

        Notes
        =====
        - All nodes for a given object (e.g. table) are stored in self.nodes.
        - Each method decorated with 'abstractmethod' must be defined by the child class. The
          decorator _ensures_ this happens.
        """

        self.nodes = {}
        self.rendered = False


    def remove_node(self, name):
        self.nodes[name].removeNode()
        del self.nodes[name]


    def remove_nodes(self):
        for node in self.nodes.values():
            node.removeNode()

        self.nodes = {}


    def hide_node(self, name):
        self.nodes[name].hide()


    def hide_nodes(self):
        for node_name in self.nodes:
            self.hide_node(node_name)


    def show_node(self, name):
        self.nodes[name].show()


    def show_nodes(self):
        for node_name in self.nodes:
            self.show_node(node_name)


    def get_node(self, name):
        return self.nodes[name]


    @abstractmethod
    def get_render_state(self):
        pass


    @abstractmethod
    def set_object_state_as_render_state(self):
        pass


    @abstractmethod
    def set_render_state_as_object_state(self):
        pass


    @abstractmethod
    def render(self):
        if self.rendered:
            self.remove_nodes()

        self.rendered = True



# -------------------------------------------------------------------------------------------------
# TABLE {{{
# -------------------------------------------------------------------------------------------------


class TableRender(Render):
    def __init__(self):
        """A class for all pool table associated panda3d nodes"""
        Render.__init__(self)


    def init_cloth(self):
        node = render.find('scene').attachNewNode(
            autils.make_rectangle(
                x1=0,
                y1=0,
                z1=0,
                x2=self.w,
                y2=self.l,
                z2=0,
                name='cloth'
            )
        )

        node.setPos(0, 0, self.height)

        # Currently there are no texture coordinates for make_rectangle, so this just picks a single color
        cloth_tex = loader.loadTexture(model_paths['blue_cloth'])
        cloth_tex.setWrapU(Texture.WM_repeat)
        cloth_tex.setWrapV(Texture.WM_repeat)
        node.setTexture(cloth_tex)

        self.nodes['cloth'] = node


    def render(self):
        super().render()
        self.init_cloth()


    def get_render_state(self):
        raise NotImplementedError("Can't call get_render_state for class 'TableRender'")


    def set_object_state_as_render_state(self):
        raise NotImplementedError("Can't call set_object_state_as_render_state for class 'TableRender'")


    def set_render_state_as_object_state(self):
        raise NotImplementedError("Can't call set_object_state_as_render_state for class 'TableRender'. Call render instead")


class Table(Object, TableRender):
    object_type = 'table'

    def __init__(self, w=None, l=None,
                 edge_width=None, rail_width=None, rail_height=None,
                 table_height=None, lights_height=None):

        self.w = w or psim.table_width
        self.l = l or psim.table_length
        self.edge_width = edge_width or psim.table_edge_width
        self.rail_width = rail_width or psim.rail_width # for visualization
        self.height = table_height or psim.table_height # for visualization
        self.lights_height = lights_height or psim.lights_height # for visualization

        self.L = 0
        self.R = self.w
        self.B = 0
        self.T = self.l

        self.center = (self.w/2, self.l/2)

        self.rails = {
            'L': Rail('L', lx=1, ly=0, l0=-self.L, height=rail_height),
            'R': Rail('R', lx=1, ly=0, l0=-self.R, height=rail_height),
            'B': Rail('B', lx=0, ly=1, l0=-self.B, height=rail_height),
            'T': Rail('T', lx=0, ly=1, l0=-self.T, height=rail_height),
        }

        TableRender.__init__(self)


class Rail(Object):
    object_type = 'cushion'

    def __init__(self, rail_id, lx, ly, l0, height=None):
        """A rail is defined by a line lx*x + ly*y + l0 = 0"""

        self.id = rail_id

        self.lx = lx
        self.ly = ly
        self.l0 = l0

        # Defines the normal vector of the rail surface
        self.normal = np.array([self.lx, self.ly, 0])

        # rail properties
        self.height = height or psim.rail_height


# -------------------------------------------------------------------------------------------------
# }}} BALL {{{
# -------------------------------------------------------------------------------------------------

class BallRender(Render):
    def __init__(self):
        self.xyzs = None
        self.playback_sequence = None
        Render.__init__(self)


    def init_sphere(self):
        node = render.find('scene').find('cloth').attachNewNode(f"ball_{self.id}")

        sphere_node = loader.loadModel('models/smiley')
        expected_texture_name = f"{str(self.id).split('_')[0]}_ball"

        try:
            tex = loader.loadTexture(model_paths[expected_texture_name])
            sphere_node.setTexture(tex, 1)
        except KeyError:
            # No ball texture is found for the given ball.id. Keeping smiley
            pass

        sphere_node.reparentTo(node)
        sphere_node.setScale(self.get_scale_factor(sphere_node))

        node.setPos(*self.rvw[0,:])

        self.nodes['sphere'] = sphere_node
        self.nodes['ball'] = node

        self.randomize_orientation()


    def init_arrow(self):
        """Good for spin diagnostics"""
        arrow = loader.loadModel(model_paths['cylinder'])

        m, M = arrow.getTightBounds()
        model_R, model_l = (M-m)[0]/2, (M-m)[2]

        arrow.setSx(self.R / 7 / model_R)
        arrow.setSy(self.R / 7 / model_R)
        arrow.setSz(self.R*3 / model_l)

        arrow.setColor(0, 0, 1, 1)
        m, M = arrow.getTightBounds()
        model_R, model_l = (M-m)[0]/2, (M-m)[2]

        arrow.reparentTo(self.nodes['ball'])
        arrow.setZ(arrow.getZ() + model_l/2)

        self.nodes['arrow'] = arrow


    def get_scale_factor(self, node):
        """Find scale factor to match model size to ball's SI radius"""
        m, M = node.getTightBounds()
        model_R = (M - m)[0]/2

        return self.R / model_R


    def get_render_state(self):
        x, y, z = self.nodes['ball'].getPos()
        return x, y, z


    def set_object_state_as_render_state(self):
        self.rvw[0,0], self.rvw[0,1], self.rvw[0,2] = self.get_render_state()


    def set_render_state_as_object_state(self):
        self.nodes['ball'].setPos(*self.rvw[0,:])


    def set_playback_sequence(self, playback_speed=1):
        """Creates the sequence motions of the ball for a given playback speed"""
        # Get the trajectories
        xyzs = autils.get_list_of_Vec3s_from_array(self.history.rvw[:, 0, :])
        quats = autils.get_quaternion_list_from_array(utils.as_quaternion(self.history.rvw[:, 3, :]))

        dts = np.diff(self.history.t)
        playback_dts = dts/playback_speed

        # Init the sequences
        ball_sequence = Sequence()

        for i in range(len(playback_dts)):
            # Append to ball sequence
            ball_sequence.append(LerpPosQuatInterval(
                nodePath = self.nodes['ball'],
                duration = playback_dts[i],
                pos = xyzs[i+1],
                quat = quats[i+1]
            ))

        self.playback_sequence = Parallel()
        self.playback_sequence.append(ball_sequence)


    def randomize_orientation(self):
        self.get_node('sphere').setHpr(*np.random.uniform(-180, 180, size=3))


    def reset_angular_integration(self):
        ball, sphere = self.get_node('ball'), self.get_node('sphere')
        sphere.setQuat(sphere.getQuat() * ball.getQuat())

        ball.setHpr(0, 0, 0)
        self.rvw[3] = np.zeros(3)


    def render(self):
        super().render()
        self.init_sphere()
        #self.init_arrow()


class BallHistory(object):
    def __init__(self):
        self.vectorized = False
        self.reset_history()


    def reset_history(self):
        n = 0
        self.rvw = [np.nan * np.ones((4,3))] * n
        self.s = [np.nan] * n
        self.t = [np.nan] * n


    def add(self, rvw, s, t):
        self.rvw.append(rvw)
        self.s.append(s)
        self.t.append(t)


    def vectorize(self):
        """Convert all list objects in self.history to array objects

        Notes
        =====
        - Append operations will cease to work
        """

        self.rvw = np.array(self.rvw)
        self.s = np.array(self.s)
        self.t = np.array(self.t)

        self.vectorized = True


class Ball(Object, BallRender, Events):
    object_type = 'ball'

    def __init__(self, ball_id, m=None, R=None, u_s=None, u_r=None, u_sp=None, g=None):
        self.id = ball_id

        # physical properties
        self.m = m or psim.m
        self.R = R or psim.R
        self.I = 2/5 * self.m * self.R**2
        self.g = g or psim.g

        # felt properties
        self.u_s = u_s or psim.u_s
        self.u_r = u_r or psim.u_r
        self.u_sp = u_sp or psim.u_sp

        self.t = 0
        self.s = psim.stationary
        self.rvw = np.array([[np.nan, np.nan, np.nan],  # positions (r)
                             [0,      0,      0     ],  # velocities (v)
                             [0,      0,      0     ],  # angular velocities (w)
                             [0,      0,      0     ]]) # angular integrations (e)
        self.update_next_transition_event()

        self.history = BallHistory()

        BallRender.__init__(self)
        Events.__init__(self)


    def attach_history(self, history):
        """Sets self.history to an existing BallHistory object"""
        self.history = history


    def update_history(self, event):
        self.history.add(self.rvw, self.s, event.time)
        self.add_event(event)


    def init_history(self):
        self.update_history(NonEvent(t=0))


    def update_next_transition_event(self):
        if self.s == psim.stationary:
            self.next_transition_event = NonEvent(t = np.inf)

        elif self.s == psim.spinning:
            dtau_E = physics.get_spin_time(self.rvw, self.R, self.u_sp, self.g)
            self.next_transition_event = SpinningStationaryTransition(self, t=(self.t + dtau_E))

        elif self.s == psim.rolling:
            dtau_E_spin = physics.get_spin_time(self.rvw, self.R, self.u_sp, self.g)
            dtau_E_roll = physics.get_roll_time(self.rvw, self.u_r, self.g)

            if dtau_E_spin > dtau_E_roll:
                self.next_transition_event = RollingSpinningTransition(self, t=(self.t + dtau_E_roll))
            else:
                self.next_transition_event = RollingStationaryTransition(self, t=(self.t + dtau_E_roll))

        elif self.s == psim.sliding:
            dtau_E = physics.get_slide_time(self.rvw, self.R, self.u_s, self.g)
            self.next_transition_event = SlidingRollingTransition(self, t=(self.t + dtau_E))

        else:
            raise NotImplementedError(f"State '{self.s}' not implemented for object Ball")


    def __repr__(self):
        lines = [
            f'<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>',
            f' ├── id       : {self.id}',
            f' ├── state    : {self.s}',
            f' ├── position : {self.rvw[0]}',
            f' ├── velocity : {self.rvw[1]}',
            f' ├── angular  : {self.rvw[2]}',
            f' └── euler    : {self.rvw[3]}',
        ]

        return '\n'.join(lines) + '\n'


    def set(self, rvw, s, t=None):
        self.s = s
        self.rvw = rvw
        if t is not None:
            self.t = t


    def set_time(self, t):
        self.t = t


# -------------------------------------------------------------------------------------------------
# }}} CUE {{{
# -------------------------------------------------------------------------------------------------


class CueRender(Render):
    def __init__(self):
        Render.__init__(self)

        self.follow = None
        self.stroke_sequence = None
        self.stroke_clock = ClockObject()


    def init_model(self, R=psim.R):
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

    def __init__(self, M=psim.M, length=psim.cue_length, tip_radius=psim.cue_tip_radius,
                 butt_radius=psim.cue_butt_radius, cue_id='cue_stick', brand=None):

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
        # FIXME
        pass

