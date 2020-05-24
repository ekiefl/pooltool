#! /usr/bin/env python
import psim.ani as ani
import psim.ani.utils as autils

from psim.ani import model_paths

import sys
import numpy as np

from panda3d.core import *
from direct.task import Task
from direct.actor.Actor import Actor
from direct.gui.OnscreenText import OnscreenText
from direct.showbase import DirectObject
from direct.showbase.ShowBase import ShowBase

from direct.interval.LerpInterval import *
from direct.interval.IntervalGlobal import *


class Trail(object):
    def __init__(self, ball, ghost_array=None, line_array=None, ghost_decay=None, line_decay=None,
                 line_thickness=None):

        self.show_line = True
        self.show_ghosts = True

        self.ghost_array = ghost_array or ani.ghost_trail_array
        self.line_array = line_array or ani.line_trail_array
        self.ghost_decay = ghost_decay or ani.ghost_decay
        self.line_decay = line_decay or ani.line_decay
        self.line_thickness = line_thickness or ani.line_trail_thickness

        self.n = len(self.ghost_array)
        self.ball = ball
        self.ball_node = self.ball.node

        # Make slightly less than 1 so ghosts don't render over the ball
        self.radius_multiplier = 0.99

        self.tau_ghost = self.ghost_array[-1]/self.ghost_decay
        self.tau_trails = self.line_array[-1]/self.line_decay

        self.trail_transparencies = self.get_transparency(self.line_array, self.tau_trails)

        self.ghosts = {}
        self.ghosts_node = NodePath('ghosts')
        self.ghosts_node.reparentTo(render.find('trails'))
        self.populate_ghosts()

        self.line_node = NodePath('line')
        self.ls = LineSegs()
        self.ls.setThickness(self.line_thickness)


    def get_transparency(self, shift, tau):
        return np.exp(-shift/tau)


    def populate_ghosts(self):
        transparencies = self.get_transparency(self.ghost_array, self.tau_ghost)

        for transparency, shift in zip(transparencies, self.ghost_array):
            self.ghosts[shift] = self.ghosts_node.attachNewNode(f"ghost_{shift}")
            self.ball_node.copyTo(self.ghosts[shift])
            self.ghosts[shift].setTransparency(TransparencyAttrib.MAlpha)
            self.ghosts[shift].setAlphaScale(transparency)
            self.ghosts[shift].setScale(self.ball.get_scale_factor()*self.radius_multiplier)


    def remove_ghosts(self):
        self.ghosts = {}
        self.ghosts_node.removeNode()


    def draw_line(self, frame, xyzs):
        self.ls.reset()

        self.line_node.removeNode()
        self.line_node = NodePath('trail')
        self.line_node.setTransparency(TransparencyAttrib.MAlpha)

        for idx, shift in enumerate(self.line_array):
            shifted_frame = frame - shift
            if shifted_frame < 0:
                break

            self.ls.drawTo(xyzs[shifted_frame])

        self.line_node.attachNewNode(self.ls.create())
        self.line_node.reparentTo(render.find('trails'))

        for n in range(self.ls.getNumVertices()):
            # Must be modified after self.ls.create()
            self.ls.setVertexColor(n, LColor(1, 1, 1, self.trail_transparencies[n]))


    def set_pos_by_frame(self, frame):
        get_trail_frame = lambda shift, frame: max([0, frame - shift])

        if self.show_ghosts:
            for shift, ghost_node in self.ghosts.items():
                self.ball._set_pos_by_frame(ghost_node, get_trail_frame(shift, frame))

        if self.show_line:
            self.draw_line(frame, self.ball.xyzs)


class Ball(object):
    def __init__(self, ball, rvw_history, quat_history):
        self._ball = ball

        self.node = self.init_node()
        self.node.setScale(self.get_scale_factor())

        rvw_history[:, 0, 2] += self._ball.R
        self.xyzs = autils.get_list_of_Vec3s_from_array(rvw_history[:, 0, :])
        self.quats = autils.get_quaternion_list_from_array(quat_history)

        self.num_frames = len(self.xyzs)

        self.playback_sequence = Parallel()

        self.trail_on = False
        self.trail = {}

        # FIXME
        self.add_trail()

        self.set_pos_by_frame(0)


    def set_playback_sequence(self, dt, playback_speed, frame_start, frame_stop):
        """Creates the sequence motions of the ball for a given playback speed"""
        ball_sequence = Sequence()

        effective_dt = dt/playback_speed
        fps = 1/effective_dt
        step_by = int(fps // ani.fps_target) if fps > ani.fps_target else 1

        for i in range(frame_start, frame_stop, step_by):
            ball_sequence.append(LerpPosQuatInterval(
                self.node,
                effective_dt*step_by,
                self.xyzs[i],
                self.quats[i],
            ))

        self.playback_sequence = Sequence(
            ball_sequence,
        )


    def init_node(self):
        """Loads ball model and reparents to table"""
        #ball_node = loader.loadModel(model_paths['sphere_yabee'])
        ball_node = loader.loadModel('models/smiley')
        expected_texture_name = f"{str(self._ball.id).split('_')[0]}_ball"

        try:
            tex = loader.loadTexture(model_paths[expected_texture_name])
            ball_node.setTexture(tex, 1)
        except KeyError:
            # No ball texture is found for the given ball.id. Keeping smiley
            pass

        ball_node.reparentTo(render.find('table'))

        return ball_node


    def get_scale_factor(self):
        """Find scale factor to match model size to ball's SI radius"""
        m, M = self.node.getTightBounds()
        current_R = (M - m)[0]/2

        return self._ball.R / current_R


    def _set_pos_by_frame(self, node, frame):
        parent = self.node.getParent()
        node.setQuat(parent, self.quats[frame])
        node.setPos(parent, self.xyzs[frame])


    def set_pos_by_frame(self, frame):
        """Update the position of the ball and trail nodes via a frame number"""
        self._set_pos_by_frame(self.node, frame)

        if self.trail_on:
            self.trail.set_pos_by_frame(frame)


    def add_trail(self):
        """Turn on line trails and/or ghost trails"""
        self.trail_on = True
        self.trail = Trail(self)


class Handler(DirectObject.DirectObject):
    def __init__(self):
        self.accept('escape', sys.exit)
        self.accept('space', self.pause_shot)
        self.accept('r', self.restart_shot)
        self.accept('x', self.press_x)
        self.accept('l', self.press_l)

        self.state = {}

        self.x_pressed = False
        self.l_pressed = False
        self.r_pressed = False

        # Game states
        self.pause = False
        self.birds_eye = False

    def press_r(self):
        self.r_pressed = True

    def pause_shot(self):
        self.pause = not self.pause

    def press_x(self):
        self.x_pressed = not self.x_pressed

    def press_l(self):
        self.l_pressed = not self.l_pressed


class AnimateShot(ShowBase, Handler):
    def __init__(self, shot):
        ShowBase.__init__(self)
        Handler.__init__(self)
        self.taskMgr.add(self.master_task, "Master")

        self.shot = shot

        # Class assumes these shot variables
        self.dt = None
        self.times = None
        self.timestamp = 0
        self.num_frames = None

        # Class assumes these node variables
        self.scene = None
        self.table = None
        self.trails = None
        self.balls = {}
        self.lights = {}

        self.init_shot_info()
        self.init_nodes()

        self.title = OnscreenText(text='psim',
                                  style=1, fg=(1, 1, 0, 1), shadow=(0, 0, 0, 0.5),
                                  pos=(0.87, -0.95), scale = .07)

        self.set_ball_playback_sequences(playback_speed=1)
        self.go()


    def init_shot_info(self):
        self.shot.calculate_quaternions()
        self.times = self.shot.get_time_history()

        # only accept a shot with uniform timestamps
        dts = np.diff(self.times)
        self.dt = dts[0]
        assert (np.round(dts, 6) == self.dt).all()

        self.num_frames = self.shot.n


    def init_nodes(self):
        self.init_table()
        self.init_trails()
        self.init_balls()
        self.init_scene()
        self.init_lights()
        self.init_camera()


    def set_ball_playback_sequences(self, playback_speed=1, frame_start=None, frame_stop=None):
        if frame_start is None: frame_start = 0
        if frame_stop is None: frame_stop = self.num_frames

        for ball in self.balls.values():
            ball.set_playback_sequence(
                playback_speed=playback_speed,
                dt=self.dt,
                frame_start=frame_start,
                frame_stop=frame_stop
            )


    def go(self):
        self.ball_parallel = Parallel()
        for ball in self.balls:
            self.ball_parallel.append(self.balls[ball].playback_sequence)

        self.ball_parallel.loop()


    def master_task(self, task):
        if self.r_pressed:
            self.restart_shot()

        if self.x_pressed:
            self.toggle_birds_eye()
        else:
            self.toggle_player_view()

        if self.l_pressed:
            self.toggle_lights()

        return Task.cont


    def restart_shot(self):
        self.ball_parallel.loop()


    def toggle_lights(self):
        render.setLightOff()


    def toggle_player_view(self):
        w, l, h = self.shot.table.w, self.shot.table.l, self.shot.table.height

        self.camera.setPos(self.table, 3/4*w, -1/2*l, h)
        self.camera.lookAt(self.table, w/2, l/2, 0)


    def toggle_birds_eye(self):
        fov = self.camLens.getFov()
        long_dim_is_y = True if self.shot.table.l >= self.shot.table.w else False
        buffer_factor = 1.1

        if long_dim_is_y and fov[0] >= fov[1]:
            rotate = True
        elif not long_dim_is_y and fov[1] >= fov[0]:
            rotate = True
        else:
            rotate = False

        zs = [
            (self.shot.table.l if long_dim_is_y else self.shot.table.w)/2*buffer_factor / np.tan(max(fov)/2 * np.pi/180),
            (self.shot.table.w if long_dim_is_y else self.shot.table.l)/2*buffer_factor / np.tan(min(fov)/2 * np.pi/180),
        ]
        self.camera.setPos(self.table, self.shot.table.w/2, self.shot.table.l/2, max(zs))
        self.camera.setHpr(0, -90, 0) if not rotate else self.camera.setHpr(90, -90, 0)


    def init_scene(self):
        self.scene = loader.loadModel(model_paths['env.egg'])
        self.scene.reparentTo(render)
        self.scene.setScale(20)
        self.scene.setPos(0, 6.5, -10)


    def init_camera(self):
        self.disableMouse()
        self.camLens.setNear(0.2)

        self.toggle_player_view()


    def init_table(self):
        w, l, h = self.shot.table.w, self.shot.table.l, self.shot.table.height

        self.table = render.attachNewNode(autils.make_rectangle(
            x1=0, y1=0, z1=0, x2=w, y2=l, z2=0, name='table'
        ))

        self.table.setPos(0, 0, h)

        # Currently there are no texture coordinates for make_rectangle, so this just picks a single
        # color
        table_tex = loader.loadTexture(model_paths['blue_cloth'])
        table_tex.setWrapU(Texture.WM_repeat)
        table_tex.setWrapV(Texture.WM_repeat)

        self.table.setTexture(table_tex)


    def init_trails(self):
        self.trails = NodePath('trails')
        self.trails.reparentTo(render)
        self.trails.setPos(0, 0, self.shot.table.height)
        self.trails.hide(0b0001)


    def init_balls(self):
        for ball in self.shot.balls.values():
            self.balls[ball.id] = self.init_ball(ball)


    def init_ball(self, ball):
        rvw_history = self.shot.get_ball_rvw_history(ball.id)
        quat_history = self.shot.get_ball_quat_history(ball.id)

        return Ball(ball, rvw_history, quat_history)


    def init_lights(self):
        w, l, h = self.shot.table.w, self.shot.table.l, self.shot.table.lights_height

        self.lights['ambient'] = {}
        self.lights['overhead'] = {}

        overhead_intensity = 0.6

        def add_overhead(x, y, z, name='plight'):
            plight = PointLight(name)
            plight.setColor((overhead_intensity, overhead_intensity, overhead_intensity, 1))
            plight.setShadowCaster(True, 1024, 1024)
            plight.setAttenuation((1, 0, 1)) # inverse square attenutation
            plight.setCameraMask(0b0001)

            self.lights['overhead'][name] = self.table.attachNewNode(plight)
            self.lights['overhead'][name].setPos(self.table, x, y, z)
            self.table.setLight(self.lights['overhead'][name])

        plight = PointLight('test')
        plight.setColor((1,1,0,0))
        plight.setShadowCaster(False, 1024, 1024)
        self.lights['overhead']['test'] = self.table.attachNewNode(plight)
        self.lights['overhead']['test'].setPos(self.table, 0.5*w, 1.0*l, h)

        add_overhead(0.5*w, 1.0*l, h, name='overhead_top')
        add_overhead(0.5*w, 0.5*l, h, name='overhead_middle')
        add_overhead(0.5*w, 0.0*l, h, name='overhead_bottom')

        ambient_intensity = 0.6
        alight = AmbientLight('alight')
        alight.setColor((ambient_intensity, ambient_intensity, ambient_intensity, 1))
        self.lights['ambient']['ambient1'] = render.attachNewNode(alight)
        self.table.setLight(self.lights['ambient']['ambient1'])

        self.table.setShaderAuto()


    def start(self):
        self.run()
