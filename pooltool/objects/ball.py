#! /usr/bin/env python

import pooltool.physics as physics
import pooltool.ani.utils as autils

from pooltool.ani import model_paths
from pooltool.events import *
from pooltool.objects import *

import numpy as np

from direct.interval.IntervalGlobal import *

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
        self.vectorized = False
        self.rvw = [np.nan * np.ones((4,3))] * n
        self.s = [np.nan] * n
        self.t = [np.nan] * n


    def is_populated(self):
        """Returns True if rvw has non-zero length"""
        return True if len(self.rvw) else False


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
        self.m = m or pooltool.m
        self.R = R or pooltool.R
        self.I = 2/5 * self.m * self.R**2
        self.g = g or pooltool.g

        # felt properties
        self.u_s = u_s or pooltool.u_s
        self.u_r = u_r or pooltool.u_r
        self.u_sp = u_sp or pooltool.u_sp

        self.t = 0
        self.s = pooltool.stationary
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
        self.history.add(np.copy(self.rvw), self.s, event.time)
        self.add_event(event)


    def init_history(self):
        self.update_history(NonEvent(t=0))


    def update_next_transition_event(self):
        if self.s == pooltool.stationary or self.s == pooltool.pocketed:
            self.next_transition_event = NonEvent(t = np.inf)

        elif self.s == pooltool.spinning:
            dtau_E = physics.get_spin_time(self.rvw, self.R, self.u_sp, self.g)
            self.next_transition_event = SpinningStationaryTransition(self, t=(self.t + dtau_E))

        elif self.s == pooltool.rolling:
            dtau_E_spin = physics.get_spin_time(self.rvw, self.R, self.u_sp, self.g)
            dtau_E_roll = physics.get_roll_time(self.rvw, self.u_r, self.g)

            if dtau_E_spin > dtau_E_roll:
                self.next_transition_event = RollingSpinningTransition(self, t=(self.t + dtau_E_roll))
            else:
                self.next_transition_event = RollingStationaryTransition(self, t=(self.t + dtau_E_roll))

        elif self.s == pooltool.sliding:
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


