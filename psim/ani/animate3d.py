#! /usr/bin/env python
import psim.ani.utils as autils

from psim.ani import model_paths

import numpy as np

from direct.task import Task
from panda3d.core import Point3
from direct.actor.Actor import Actor
from direct.showbase.ShowBase import ShowBase
from direct.interval.IntervalGlobal import Sequence


class Ball(object):
    def __init__(self, ball, rvw_history, node):
        self.node = node
        self._ball = ball

        self.xs = rvw_history[:,0,0]
        self.ys = rvw_history[:,0,1]
        self.zs = rvw_history[:,0,2]

        self.node.setScale(self.get_scale_factor())
        self.update(0)


    def get_scale_factor(self):
        """Find scale factor to match model size to ball's SI radius"""

        m, M = self.node.getTightBounds()
        current_R = (M - m)[0]/2

        return self._ball.R / current_R


    def update(self, frame):
        self.node.setPos(self.xs[frame], self.ys[frame], self.zs[frame] + self._ball.R)


class AnimateShot(ShowBase):
    def __init__(self, shot):
        ShowBase.__init__(self)

        self.frame = 0

        self.shot = shot
        self.times = shot.get_time_array()
        self.num_frames = shot.n

        self.balls = {}
        self.init_balls()

        self.scene = None
        self.init_scene()

        self.table = None
        self.init_table()

        self.init_camera()

        self.taskMgr.add(self.master_task, "Master")
        #self.taskMgr.add(self.translate_ball_task, "TranslateBallTask")


    def master_task(self, task):
        print(task.time)
        for ball in self.balls.values():
            ball.update(self.frame)

        if self.frame >= self.num_frames:
            self.frame = 0
        else:
            self.frame += 1

        return Task.cont


    def init_table(self):
        self.table = self.render.attachNewNode(autils.make_square(
            self.render, 0, 0, 0, self.shot.table.w, self.shot.table.l, 0, 'square'
        ))
        self.table.setTexture(self.loader.loadTexture(model_paths['blue_cloth']))


    def init_scene(self):
        self.scene = self.loader.loadModel("models/environment")
        self.scene.reparentTo(self.render)
        self.scene.setScale(0.030, 0.030, 0.030)
        self.scene.setPos(0, 6.5, -0.7)


    def init_camera(self):
        self.disableMouse()
        self.camera.setPos(-3, -3, 3)
        self.camera.setHpr(-45, -30, 0)


    def init_balls(self):
        for ball in self.shot.balls.values():
            self.balls[ball.id] = self.init_ball(ball)


    def init_ball(self, ball):
        rvw_history = self.shot.get_ball_rvw_history(ball.id)
        ball_node = self.loader.loadModel("models/smiley")
        ball_node.reparentTo(self.render)

        return Ball(ball, rvw_history, ball_node)


    def translate_ball_task(self, task):
        self.ball.setPos(self.ball.getX() + 0.02, 0, 0)
        return Task.cont


    def spin_ball_task(self, task):
        angleDegrees = task.time * 200.0
        angleRadians = angleDegrees * (np.pi / 180.0)
        self.ball.setHpr(angleDegrees, angleDegrees, 0)
        return Task.cont


    def start(self):
        self.run()
