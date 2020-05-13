#! /usr/bin/env python
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
from direct.interval.IntervalGlobal import Sequence


class Trail(object):
    def __init__(self, ball_node, ghost_array=None, line_array=None):
        self.ghost_array = ghost_array or np.array([3, 6, 9])
        self.line_array = line_array or np.array([3, 6, 9])

        self.n = len(self.ghost_array)
        self.ball_node = ball_node

        self.ghosts = {}
        self.ghosts_node = NodePath('ghosts')
        self.populate_ghosts()


    def get_transparency(self, shift):
        tau = self.ghost_array[-1]/2
        return np.exp(-shift/tau)


    def populate_ghosts(self):
        for shift in self.ghost_array:
            self.ghosts[shift] = self.ghosts_node.attachNewNode(f"trail_{shift}")
            self.ball_node.copyTo(self.ghosts[shift])
            self.ghosts[shift].setTransparency(TransparencyAttrib.MAlpha)
            self.ghosts[shift].setAlphaScale(self.get_transparency(shift))

        self.ghosts_node.reparentTo(self.ball_node)


    def remove_ghosts(self):
        self.ghosts = {}
        self.ghosts_node.removeNode()


class Ball(object):
    def __init__(self, ball, rvw_history, euler_history, quat_history, node, use_euler=False):
        self.node = node
        self._ball = ball

        self.use_euler = use_euler

        self.xs = rvw_history[:,0,0]
        self.ys = rvw_history[:,0,1]
        self.zs = rvw_history[:,0,2]

        self.hs = euler_history[:,0]
        self.ps = euler_history[:,1]
        self.rs = euler_history[:,2]

        self.wxs = rvw_history[:,2,0]
        self.wys = rvw_history[:,2,1]
        self.wzs = rvw_history[:,2,2]

        self.quats = quat_history

        self.trail_on = False
        self.trail = {}

        # FIXME
        self.add_trail()

        self.node.setScale(self.get_scale_factor())
        self.update(0)


    def get_scale_factor(self):
        """Find scale factor to match model size to ball's SI radius"""


        m, M = self.node.getTightBounds()
        current_R = (M - m)[0]/2

        return self._ball.R / current_R


    def update(self, frame):
        # Updates self.node
        if self.use_euler:
            self.node.setHpr(self.hs[frame], self.ps[frame], self.rs[frame])
        else:
            self.node.setQuat(autils.get_quat_from_vector(self.quats[frame]))
        self.node.setPos(self.xs[frame], self.ys[frame], self.zs[frame] + self._ball.R)

        # Update trails
        if self.trail_on:
            get_trail_frame = lambda shift, frame: max([0, frame - shift])

            for shift, trail_node in self.trail.ghosts.items():
                trail_frame = get_trail_frame(shift, frame)

                if self.use_euler:
                    trail_node.setHpr(self.node.getParent(), self.hs[trail_frame], self.ps[trail_frame], self.rs[trail_frame])
                else:
                    trail_node.setQuat(self.node.getParent(), autils.get_quat_from_vector(self.quats[trail_frame]))
                trail_node.setPos(self.node.getParent(), self.xs[trail_frame], self.ys[trail_frame], self.zs[trail_frame] + self._ball.R)


    def add_trail(self):
        self.trail_on = True
        self.trail = Trail(self.node)


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

        # Game states
        self.pause = False
        self.birds_eye = False

    def restart_shot(self):
        self.frame = 0

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

        self.frame = 0

        self.shot = shot
        self.shot.calculate_euler_angles()
        self.shot.calculate_quaternions()
        self.times = shot.get_time_history()
        self.num_frames = shot.n

        self.title = OnscreenText(text='psim',
                                  style=1, fg=(1, 1, 0, 1), shadow=(0, 0, 0, 0.5),
                                  pos=(0.87, -0.95), scale = .07)

        self.table = None
        self.init_table()

        self.balls = {}
        self.init_balls()

        self.scene = None
        self.init_scene()

        self.lights = {}
        self.init_lights()

        self.init_camera()


    def master_task(self, task):
        if not self.pause:
            for ball in self.balls.values():
                ball.update(self.frame)

            if self.frame >= self.num_frames:
                self.frame = 0
            else:
                self.frame += 1

        if self.x_pressed:
            self.toggle_birds_eye()
        else:
            self.toggle_cue_ball_view()

        if self.l_pressed:
            self.toggle_lights()

        return Task.cont


    def toggle_lights(self):
        self.render.setLightOff()


    def toggle_cue_ball_view(self):
        self.camera.setPos(
            self.balls['cue'].xs[self.frame],
            self.balls['cue'].ys[self.frame] - 1.2,
            self.balls['cue'].zs[self.frame] + 1.2
        )

        self.camera.lookAt(self.balls['cue'].node)


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
        self.scene.reparentTo(self.render)
        self.scene.setScale(20)
        self.scene.setPos(0, 6.5, -10)


    def init_camera(self):
        self.disableMouse()
        self.camLens.setNear(0.2)
        self.camera.setPos(-1, -1, 1)
        self.camera.setHpr(-45, -30, 0)


    def init_table(self):
        w, l, h = self.shot.table.w, self.shot.table.l, self.shot.table.height

        self.table = self.render.attachNewNode(autils.make_rectangle(
            x1=0, y1=0, z1=0, x2=w, y2=l, z2=0, name='playing_surface'
        ))

        self.table.setPos(0, 0, h)

        # Currently there are no texture coordinates for make_rectangle, so this just picks a single
        # color
        table_tex = self.loader.loadTexture(model_paths['blue_cloth'])
        table_tex.setWrapU(Texture.WM_repeat)
        table_tex.setWrapV(Texture.WM_repeat)

        self.table.setTexture(table_tex)


    def init_balls(self):
        for ball in self.shot.balls.values():
            self.balls[ball.id] = self.init_ball(ball)


    def init_ball(self, ball):
        rvw_history = self.shot.get_ball_rvw_history(ball.id)
        euler_history = self.shot.get_ball_euler_history(ball.id)
        quat_history = self.shot.get_ball_quat_history(ball.id)

        ball_node = self.loader.loadModel('models/smiley')

        try:
            ball_node.setTexture(self.loader.loadTexture(model_paths[f"{str(ball.id).split('_')[0]}_ball"]), 1)
        except KeyError:
            # No ball texture is found for the given ball.id. Keeping smiley
            pass

        ball_node.reparentTo(self.table)

        return Ball(ball, rvw_history, euler_history, quat_history, ball_node)


    def init_lights(self):
        w, l, h = self.shot.table.w, self.shot.table.l, self.shot.table.lights_height

        self.lights['ambient'] = {}
        self.lights['overhead'] = {}

        overhead_intensity = 0.4

        def add_overhead(x, y, z, name='plight'):
            plight = PointLight(name)
            plight.setColor((overhead_intensity, overhead_intensity, overhead_intensity, 1))
            plight.setShadowCaster(True, 1024, 1024)

            self.lights['overhead'][name] = self.render.attachNewNode(plight)
            self.lights['overhead'][name].setPos(self.table, x, y, z)
            self.render.setLight(self.lights['overhead'][name])

        add_overhead(0.5*w, 1.0*l, h, name='top')
        add_overhead(0.5*w, 0.5*l, h, name='middle')
        add_overhead(0.5*w, 0.0*l, h, name='bottom')

        ambient_intensity = 0.5
        alight = AmbientLight('alight')
        alight.setColor((ambient_intensity, ambient_intensity, ambient_intensity, 1))
        self.lights['ambient']['ambient1'] = self.render.attachNewNode(alight)
        self.render.setLight(self.lights['ambient']['ambient1'])

        self.render.setShaderAuto()


    def start(self):
        self.run()
