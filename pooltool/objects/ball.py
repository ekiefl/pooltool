#! /usr/bin/env python

import pooltool.ani as ani
import pooltool.physics as physics
import pooltool.ani.utils as autils
import pooltool.constants as c

from pooltool.utils import panda_path
from pooltool.error import ConfigError
from pooltool.events import *
from pooltool.objects import Render, Object

import numpy as np

from pathlib import Path
from panda3d.core import *
from direct.interval.IntervalGlobal import *

__all__ = ['Ball', 'ball_from_dict', 'ball_from_pickle']

class BallRender(Render):
    def __init__(self, rel_model_path=None):
        self.rel_model_path = rel_model_path
        self.quats = None
        self.playback_sequence = None
        Render.__init__(self)


    def init_sphere(self):
        position = render.find('scene').find('cloth').attachNewNode(f"ball_{self.id}_position")
        ball = position.attachNewNode(f"ball_{self.id}")

        if self.rel_model_path is None:
            fallback_path = ani.model_dir / 'balls' / 'set_1' / '1.glb'
            expected_path = ani.model_dir / 'balls' / 'set_1' / f'{self.id}.glb'
            path = expected_path if expected_path.exists() else fallback_path

            sphere_node = base.loader.loadModel(panda_path(path))
            sphere_node.reparentTo(position)

            if path == fallback_path:
                tex = sphere_node.find_texture(Path(fallback_path).stem)
            else:
                tex = sphere_node.find_texture(self.id)

            # Here, we define self.rel_model_path based on path. Since rel_model_path is defined relative to
            # the directory, pooltool/models/balls, some work has to be done to define rel_model_path
            # relative to this directory. NOTE assumes no child directory is named balls
            parents = []
            parent = path.parent
            while True:
                if parent.stem == 'balls':
                    self.rel_model_path = Path('/'.join(parents[::-1])) / path.name
                    break
                parents.append(parent.stem)
                parent = parent.parent
        else:
            sphere_node = base.loader.loadModel(panda_path(ani.model_dir / 'balls' / self.rel_model_path))
            sphere_node.reparentTo(position)
            tex = sphere_node.find_texture(Path(self.rel_model_path).stem)

        # https://discourse.panda3d.org/t/visual-artifact-at-poles-of-uv-sphere-gltf-format/27975/8
        tex.set_minfilter(SamplerState.FT_linear)

        sphere_node.setScale(self.get_scale_factor(sphere_node))
        position.setPos(*self.rvw[0,:])

        self.nodes['sphere'] = sphere_node
        self.nodes['ball'] = ball
        self.nodes['pos'] = position
        self.nodes['shadow'] = self.init_shadow()
        if ani.settings['graphics']['angular_vectors']:
            self.nodes['vector'] = self.init_angular_vector()

        self.randomize_orientation()


    def init_collision(self, cue):
        if not cue.rendered:
            raise ConfigError("BallRender.init_collision :: `cue` must be rendered")

        collision_node = self.nodes['ball'].attachNewNode(CollisionNode(f"ball_csphere_{self.id}"))
        collision_node.node().addSolid(CollisionCapsule(0, 0, -self.R, 0, 0, self.R, cue.tip_radius + self.R))
        if ani.settings['graphics']['debug']:
            collision_node.show()

        self.nodes[f"ball_csphere_{self.id}"] = collision_node


    def init_shadow(self):
        N = 20
        start, stop = 0.5, 0.9 # fraction of ball radius
        z_offset = 0.0005
        scales = np.linspace(start, stop, N)

        shadow_path = ani.model_dir / 'balls' / 'set_1' / f'shadow.glb'
        shadow_node = render.find('scene').find('cloth').attachNewNode(f'shadow_{self.id}')
        shadow_node.setPos(self.rvw[0,0], self.rvw[0,1], 0)

        # allow transparency of shadow to change
        shadow_node.setTransparency(TransparencyAttrib.MAlpha)

        for i, scale in enumerate(scales):
            shadow_layer = base.loader.loadModel(panda_path(shadow_path))
            shadow_layer.reparentTo(shadow_node)
            shadow_layer.setScale(self.get_scale_factor(shadow_layer)*scale)
            shadow_layer.setZ(z_offset*(1 - i/N))

        return shadow_node


    def init_angular_vector(self):
        self.vector_drawer = LineSegs()
        self.vector_drawer.setThickness(3)
        node = self.nodes['pos'].attachNewNode(self.vector_drawer.create())

        return node


    def get_angular_vector(self, t, w):
        if 'vector' in self.nodes:
            self.remove_node('vector')

        unit = utils.unit_vector(w, handle_zero=True)
        norm = np.linalg.norm(w)

        max_norm = 50
        min_len = self.R
        max_len = 6*self.R

        factor = min(1, norm/max_norm)
        arrow_len = factor*(max_len - min_len) + min_len

        self.vector_drawer.reset()
        self.vector_drawer.setColor(1, 1-factor, 1-factor)
        self.vector_drawer.moveTo(0, 0, 0)
        self.vector_drawer.drawTo(*(arrow_len*unit))
        try:
            # It is possible that this function is ran after scene is closed, in which case
            # self.nodes['pos'] does not exist.
            self.nodes['vector'] = self.nodes['pos'].attachNewNode(self.vector_drawer.create())
            self.nodes['vector'].set_shader_auto(True)
        except:
            pass


    def get_scale_factor(self, node):
        """Find scale factor to match model size to ball's SI radius"""
        m, M = node.getTightBounds()
        model_R = (M - m)[0]/2

        return self.R / model_R


    def get_render_state(self):
        """Return the position of the rendered ball"""
        x, y, z = self.nodes['pos'].getPos()
        return x, y, z


    def set_object_state_as_render_state(self):
        """Set the object position based on the rendered position"""
        self.rvw[0] = self.get_render_state()


    def set_render_state_as_object_state(self):
        """Set rendered position based on the object's position (self.rvw[0,:])"""
        pos = self.rvw[0]
        self.set_render_state(pos)


    def set_render_state(self, pos):
        """Set the position of the rendered ball

        Parameters
        ==========
        pos : length-3 iterable
        """

        self.nodes['pos'].setPos(*pos)
        self.nodes['shadow'].setPos(pos[0], pos[1], min(0, pos[2]-self.R))


    def set_render_state_from_history(self, i):
        """Set the position of the rendered ball based on history index

        Parameters
        ==========
        i : int
            An index from the history. e.g. 0 refers to initial state, -1 refers to final state
        """

        rvw, _, _ = self.history.get_state(i)
        self.set_render_state(rvw[0])


    def set_playback_sequence(self, playback_speed=1):
        """Creates the sequence motions of the ball for a given playback speed"""
        dts = np.diff(self.history_cts.t)
        motion_states = self.history_cts.s
        playback_dts = dts/playback_speed

        # Get the trajectories
        xyzs = self.history_cts.rvw[:, 0, :]
        ws = self.history_cts.rvw[:, 2, :]

        if (xyzs == xyzs[0,:]).all() and (ws == ws[0,:]).all():
            # Ball has no motion. No need to create Lerp intervals
            self.playback_sequence = Sequence()
            self.quats = autils.as_quaternion(ws, self.history_cts.t)
            return

        xyzs = autils.get_list_of_Vec3s_from_array(xyzs)
        self.quats = autils.as_quaternion(ws, self.history_cts.t)

        # Init the animation sequences
        ball_sequence = Sequence()
        shadow_sequence = Sequence()
        if ani.settings['graphics']['angular_vectors']:
            angular_vector_sequence = Sequence()

        self.set_render_state_from_history(0)

        j = 0
        energetic = False
        for i in range(len(playback_dts)):
            x, y, z = xyzs[i]
            Qm, Qx, Qy, Qz = self.quats[i]

            if not energetic and motion_states[i] in c.energetic:
                # The ball wasn't energetic, but now it is
                energetic = True
                xi, yi, zi = xyzs[j]
                Qmi, Qxi, Qyi, Qzi = self.quats[j]
                dur = playback_dts[j:i].sum()

                ball_sequence.append(LerpPosQuatInterval(
                    nodePath = self.nodes['pos'],
                    duration = dur,
                    startPos = (xi, yi, zi),
                    pos = (xi, yi, zi),
                    startQuat = (Qmi, Qxi, Qyi, Qzi),
                    quat = (Qmi, Qxi, Qyi, Qzi),
                ))
                shadow_sequence.append(LerpPosInterval(
                    nodePath = self.nodes['shadow'],
                    duration = dur,
                    startPos = (xi, yi, min(0, zi-self.R)),
                    pos = (xi, yi, min(0, zi-self.R)),
                ))

            if energetic:
                ball_sequence.append(LerpPosQuatInterval(
                    nodePath = self.nodes['pos'],
                    duration = playback_dts[i],
                    pos = (x, y, z),
                    quat = (Qm, Qx, Qy, Qz),
                ))
                shadow_sequence.append(LerpPosInterval(
                    nodePath = self.nodes['shadow'],
                    duration = playback_dts[i],
                    pos = (x, y, min(0, z-self.R)),
                ))

                if motion_states[i] not in c.energetic:
                    # The ball was energetic, but now it is not
                    energetic = False
                    j = i

            if ani.settings['graphics']['angular_vectors']:
                angular_vector_sequence.append(LerpFunc(
                    self.get_angular_vector,
                    duration = playback_dts[i],
                    extraArgs = [ws[i, :]],
                ))

        self.playback_sequence = Parallel(
            ball_sequence,
            shadow_sequence,
        )
        if ani.settings['graphics']['angular_vectors']:
            self.playback_sequence.append(angular_vector_sequence)


    def set_alpha(self, alpha):
        self.get_node('pos').setTransparency(TransparencyAttrib.MAlpha)
        self.get_node('pos').setAlphaScale(alpha)
        self.get_node('shadow').setAlphaScale(alpha)


    def randomize_orientation(self):
        self.get_node('sphere').setHpr(*np.random.uniform(-180, 180, size=3))


    def reset_angular_integration(self):
        ball, sphere = self.get_node('pos'), self.get_node('sphere')
        sphere.setQuat(sphere.getQuat() * ball.getQuat())

        ball.setHpr(0, 0, 0)


    def teardown(self):
        if self.playback_sequence is not None:
            self.playback_sequence.pause()
        self.remove_nodes()


    def render(self):
        super().render()
        self.init_sphere()


class BallHistory(object):
    def __init__(self):
        self.vectorized = False
        self.reset()


    def get_state(self, i):
        """Get state based on history index

        Returns
        =======
        out : (rvw, s, t)
        """
        return self.rvw[i], self.s[i], self.t[i]


    def reset(self):
        n = 0
        self.vectorized = False
        self.rvw = [np.nan * np.ones((3,3))] * n
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


class Ball(Object, BallRender):
    object_type = 'ball'

    def __init__(self, ball_id, m=None, R=None, u_s=None, u_r=None, u_sp=None, g=None, e_c=None, f_c=None,
                 rel_model_path=None):
        """Initialize a ball

        Parameters
        ==========
        rel_model_path : str
            path should be relative to pooltool/models/balls directory
        """
        self.id = ball_id

        if not (isinstance(self.id, int) or isinstance(self.id, str)):
            raise ConfigError("ball_id must be integer or string")

        # physical properties
        self.m = m or c.m
        self.R = R or c.R
        self.I = 2/5 * self.m * self.R**2
        self.g = g or c.g

        # felt properties
        self.u_s = u_s or c.u_s
        self.u_r = u_r or c.u_r
        self.u_sp = u_sp or c.u_sp

        # restitution properties
        self.e_c = e_c or c.e_c
        self.f_c = f_c or c.f_c

        self.t = 0
        self.s = c.stationary
        self.rvw = np.array([[np.nan, np.nan, np.nan],  # positions (r)
                             [0,      0,      0     ],  # velocities (v)
                             [0,      0,      0     ]]) # angular velocities (w)
        self.update_next_transition_event()

        self.history = BallHistory()
        self.history_cts = BallHistory()

        self.events = Events()

        self.rel_model_path = rel_model_path
        BallRender.__init__(self, rel_model_path=self.rel_model_path)


    def attach_history(self, history):
        """Sets self.history to an existing BallHistory object"""
        self.history = history


    def attach_history_cts(self, history):
        """Sets self.history_cts to an existing BallHistory object"""
        self.history_cts = history


    def update_history(self, event):
        self.history.add(np.copy(self.rvw), self.s, event.time)
        self.events.append(event)


    def init_history(self):
        self.update_history(NonEvent(t=0))


    def update_next_transition_event(self):
        if self.s == c.stationary or self.s == c.pocketed:
            self.next_transition_event = NonEvent(t = np.inf)

        elif self.s == c.spinning:
            dtau_E = physics.get_spin_time_fast(self.rvw, self.R, self.u_sp, self.g)
            self.next_transition_event = SpinningStationaryTransition(self, t=(self.t + dtau_E))

        elif self.s == c.rolling:
            dtau_E_spin = physics.get_spin_time_fast(self.rvw, self.R, self.u_sp, self.g)
            dtau_E_roll = physics.get_roll_time_fast(self.rvw, self.u_r, self.g)

            if dtau_E_spin > dtau_E_roll:
                self.next_transition_event = RollingSpinningTransition(self, t=(self.t + dtau_E_roll))
            else:
                self.next_transition_event = RollingStationaryTransition(self, t=(self.t + dtau_E_roll))

        elif self.s == c.sliding:
            dtau_E = physics.get_slide_time_fast(self.rvw, self.R, self.u_s, self.g)
            self.next_transition_event = SlidingRollingTransition(self, t=(self.t + dtau_E))

        else:
            raise NotImplementedError(f"State '{self.s}' not implemented for object Ball")


    def __repr__(self):
        lines = [
            f'<{self.__class__.__name__} object at {hex(id(self))}>',
            f' ├── id       : {self.id}',
            f' ├── state    : {self.s}',
            f' ├── position : {self.rvw[0]}',
            f' ├── velocity : {self.rvw[1]}',
            f' └── angular  : {self.rvw[2]}',
        ]

        return '\n'.join(lines) + '\n'


    def set(self, rvw, s=None, t=None):
        self.rvw = rvw
        if s is not None:
            self.s = s
        if t is not None:
            self.t = t


    def set_from_history(self, i):
        """Set the ball state according to a history index"""
        self.set(*self.history.get_state(i))


    def set_time(self, t):
        self.t = t


    def as_dict(self):
        """Return a pickle-able dictionary of the ball"""
        return dict(
            id = self.id,
            m = self.m,
            R = self.R,
            I = self.I,
            g = self.g,
            u_s = self.u_s,
            u_r = self.u_r,
            u_sp = self.u_sp,
            s = self.s,
            t = self.t,
            rvw = np.copy(self.rvw),
            rel_model_path = None if self.rel_model_path is None else str(self.rel_model_path),
            history = dict(
                rvw = self.history.rvw,
                s = self.history.s,
                t = self.history.t,
                vectorized = self.history.vectorized,
            ),
            history_cts = dict(
                rvw = self.history_cts.rvw,
                s = self.history_cts.s,
                t = self.history_cts.t,
                vectorized = self.history_cts.vectorized,
            ),
            events = self.events.as_dict(),
        )


    def save(self, path):
        utils.save_pickle(self.as_dict(), path)


def ball_from_dict(d):
    """Return a ball object from a dictionary

    For dictionary form see return value of Ball.as_dict
    """

    ball = Ball(d['id'], rel_model_path=d['rel_model_path'])
    ball.m = d['m']
    ball.R = d['R']
    ball.I = d['I']
    ball.g = d['g']
    ball.u_s = d['u_s']
    ball.u_r = d['u_r']
    ball.u_sp = d['u_sp']
    ball.s = d['s']
    ball.t = d['t']
    ball.rvw = d['rvw']

    ball_history = BallHistory()
    ball_history.rvw = d['history']['rvw']
    ball_history.s = d['history']['s']
    ball_history.t = d['history']['t']
    ball_history.vectorized = d['history']['vectorized']
    ball.attach_history(ball_history)

    ball_history_cts = BallHistory()
    ball_history_cts.rvw = d['history_cts']['rvw']
    ball_history_cts.s = d['history_cts']['s']
    ball_history_cts.t = d['history_cts']['t']
    ball_history_cts.vectorized = d['history_cts']['vectorized']
    ball.attach_history_cts(ball_history_cts)

    events = Events()
    for event_dict in d['events']:
        events.append(event_from_dict(event_dict))
    ball.events = events

    return ball


def ball_from_pickle(path):
    d = utils.load_pickle(path)
    return ball_from_dict(d)


