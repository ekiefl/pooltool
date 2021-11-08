#! /usr/bin/env python

import pooltool.ani as ani
import pooltool.utils as utils
import pooltool.ani.utils as autils

from pooltool.ani.modes import Mode, action

from panda3d.core import *

import numpy as np


class CueAvoid(object):
    def __init__(self):
        """Calculates minimum elevation required by cue stick to avoid colliding with balls and cushions

        This class uses Panda3D collision detection to determine when the cue stick is intersecting
        with a ball or cushion. Rather than use the built in collision solving (e.g.
        https://docs.panda3d.org/1.10/python/reference/panda3d.core.CollisionHandlerPusher), which
        tended to push the cue off of objects in arbitrary ways (such that the cue no longer pointed
        at the cueing ball), I instead rely on geometry to solve the minimum angle that the cue
        stick must be raised in order to avoid all collisions. At each step in AimMode.aim_task, if
        the cue elevation is less than this angle, the elevation is automatically set to this
        minimum.

        Notes
        =====
        - This class has nothing to do with collisions that occurr during the shot evolution, e.g.
          ball-ball collisions, ball-cushion collisions, etc. All of those are handled in events.py
        """

        self.min_theta = 0
        self.troubleshoot = loader.loadModel('smiley.egg')
        self.troubleshoot.setScale(0.005)
        self.troubleshoot.setColor((0,1,1,1))
        self.troubleshoot.reparentTo(self.render.find('scene'))



    def collision_task(self, task):
        max_min_theta = 0

        # Lay cue collision segment flat
        self.cue_collision_node = self.cue.get_node('cue_cseg')
        self.cue_collision_node.setR(-self.cue.get_node('cue_stick_focus').getR())

        for entry in self.collision_handler.entries:
            min_theta = self.process_collision(entry)
            if min_theta > max_min_theta:
                max_min_theta = min_theta

        self.min_theta = max_min_theta
        return task.cont


    def process_collision(self, entry):
        if not entry.has_surface_point():
            # Not a collision we care about
            return 0
        elif entry.into_node.name.startswith('cushion'):
            return 0
            #return self.process_cushion_collision(entry)
        elif entry.into_node.name.startswith('ball'):
            return self.process_ball_collision(entry)
        else:
            raise NotImplementedError(f"CueAvoid :: no collision solver for node {entry.into_node.name}")


    def process_cushion_collision(self, entry):
        cushion = self.get_cushion(entry)
        cushion_height = cushion.p1[2]

        scene = render.find('scene')
        px, py, pz = entry.getSurfacePoint(scene)
        ex, ey, ez = self.cue.get_node('cue_stick_model').getPos(scene)
        bx, by, bz = self.cue.get_node('cue_stick_focus').getPos(scene)
        dx, dy, dz = px, py, cushion_height

        v = np.array([ex-px, ey-py, ez-pz])
        u = utils.unit_vector(v)*self.cue.get_node('cue_stick_model').getX()
        fx, fy, fz = ex + u[0], ey + u[1], ez + u[2]
        min_theta = np.arctan2(dz-fz, np.sqrt((dx-fx)**2 + (dy-fy)**2))

        # correct for cue's cylindrical radius at collision point
        # distance from cue tip to desired collision point
        l = np.sqrt((dx-ex)**2 + (dy-ey)**2 + (dz-ez)**2)
        cue_radius = self.get_cue_radius(l)
        min_theta += np.arctan2(cue_radius, l)

        return max(0, min_theta) * 180/np.pi


    def process_ball_collision(self, entry):
        min_theta = 0
        ball = self.get_ball(entry)

        if ball == self.cueing_ball:
            return 0

        scene = render.find('scene')

        # get radius of transect
        n = np.array(entry.get_surface_normal(render.find('scene')))
        phi = ((self.cue.get_node('cue_stick_focus').getH() + 180) % 360) * np.pi/180
        c = np.array([np.cos(phi), np.sin(phi), 0])
        gamma = np.arccos(np.dot(n, c))
        AB = (ball.R + self.cue.tip_radius)*np.cos(gamma)

        # Center of blocking ball transect
        Ax, Ay, _ = entry.getSurfacePoint(scene)
        Ax -= (AB + self.cue.tip_radius)*np.cos(phi)
        Ay -= (AB + self.cue.tip_radius)*np.sin(phi)
        Az = ball.R

        # Center of aim, leveled to ball height
        Ex, Ey, _ = self.cue.get_node('cue_stick_model').getPos(scene)
        Px, Py, _ = entry.getSurfacePoint(scene)
        v = np.array([Ex-Px, Ey-Py, 0])
        u = utils.unit_vector(v)*self.cue.get_node('cue_stick_model').getX()
        Cx, Cy, Cz = Ex + u[0], Ey + u[1], self.cueing_ball.R + u[2]


        self.troubleshoot.setPos(Cx, Cy, Cz)
        self.cue.get_node('cue_stick_model').setTransparency(TransparencyAttrib.MAlpha)
        self.cueing_ball.get_node('ball').setTransparency(TransparencyAttrib.MAlpha)
        self.cueing_ball.get_node('ball').setAlphaScale(0.2)
        ball.get_node('ball').setTransparency(TransparencyAttrib.MAlpha)
        ball.get_node('ball').setAlphaScale(0.2)
        self.cue.get_node('cue_stick_model').setAlphaScale(0.4)

        AC = np.sqrt((Ax-Cx)**2 + (Ay-Cy)**2 + (Az-Cz)**2)

        BC = np.sqrt(AC**2 - AB**2)

        min_theta_no_english = np.arcsin(AB/AC)



        return max(0, min_theta_no_english) * 180/np.pi
        if beta < 0:
            beta += 10*np.pi/180*(np.exp(bxR/BE)**2 - 1)


    def get_cue_radius(self, l):
        """Returns radius of cue at collision point, given collision point is distance l from cue tip"""

        bounds = self.cue.get_node('cue_stick').get_tight_bounds()
        L = bounds[1][0] - bounds[0][0] # cue length

        r = self.cue.tip_radius
        R = self.cue.butt_radius

        m = (R - r)/L # rise/run
        b = r # intercept

        return m*l + b


    def get_cushion(self, entry):
        expected_suffix = 'cushion_cplane_'
        into_node_path_name = entry.get_into_node_path().name
        assert into_node_path_name.startswith(expected_suffix)
        cushion_id = into_node_path_name[len(expected_suffix):]
        return self.table.cushion_segments['linear'][cushion_id]


    def get_ball(self, entry):
        expected_suffix = 'ball_csphere_'
        into_node_path_name = entry.get_into_node_path().name
        assert into_node_path_name.startswith(expected_suffix)
        ball_id = into_node_path_name[len(expected_suffix):]
        return self.balls[ball_id]


class AimMode(Mode, CueAvoid):
    keymap = {
        action.fine_control: False,
        action.adjust_head: False,
        action.quit: False,
        action.stroke: False,
        action.view: False,
        action.zoom: False,
        action.elevation: False,
        action.english: False,
        action.cam_save: False,
        action.cam_load: False,
        action.pick_ball: False,
        action.call_shot: False,
        action.ball_in_hand: False,
    }

    def __init__(self):
        # In this state, the cue sticks to the self.min_theta
        self.magnet_theta = True
        # if cue angle is within this many degrees from self.min_theta, it sticks to self.min_theta
        self.magnet_threshold = 0.2


    def enter(self, load_prev_cam=False):
        self.mouse.hide()
        self.mouse.relative()
        self.mouse.track()

        if not self.cue.has_focus:
            self.cue.init_focus(self.cueing_ball)
        else:
            self.cue.update_focus()

        self.cue.show_nodes()
        self.cue.get_node('cue_stick').setX(0)
        self.player_cam.update_focus(self.cueing_ball.get_node('ball').getPos())
        if load_prev_cam:
            self.player_cam.load_state('aim')

        self.task_action('escape', action.quit, True)
        self.task_action('f', action.fine_control, True)
        self.task_action('f-up', action.fine_control, False)
        self.task_action('t', action.adjust_head, True)
        self.task_action('t-up', action.adjust_head, False)
        self.task_action('mouse1', action.zoom, True)
        self.task_action('mouse1-up', action.zoom, False)
        self.task_action('s', action.stroke, True)
        self.task_action('v', action.view, True)
        self.task_action('1', action.cam_save, True)
        self.task_action('2', action.cam_load, True)
        self.task_action('q', action.pick_ball, True)
        self.task_action('c', action.call_shot, True)
        self.task_action('g', action.ball_in_hand, True)
        self.task_action('b', action.elevation, True)
        self.task_action('b-up', action.elevation, False)
        self.task_action('e', action.english, True)
        self.task_action('e-up', action.english, False)

        CueAvoid.__init__(self)

        if ani.settings['gameplay']['cue_collision']:
            self.add_task(self.collision_task, 'collision_task')
        self.add_task(self.aim_task, 'aim_task')


    def exit(self):
        self.remove_task('aim_task')
        if ani.settings['gameplay']['cue_collision']:
            self.remove_task('collision_task')

        self.cue.hide_nodes()
        self.player_cam.store_state('aim', overwrite=True)


    def aim_task(self, task):
        if self.keymap[action.view]:
            self.change_mode('view', enter_kwargs=dict(move_active=True))
        elif self.keymap[action.stroke]:
            self.change_mode('stroke')
        elif self.keymap[action.pick_ball]:
            self.change_mode('pick_ball')
        elif self.keymap[action.call_shot]:
            self.change_mode('call_shot')
        elif self.keymap[action.ball_in_hand]:
            self.change_mode('ball_in_hand')
        elif self.keymap[action.zoom]:
            self.zoom_camera_aim()
        elif self.keymap[action.adjust_head]:
            self.adjust_head_aim()
        elif self.keymap[action.elevation]:
            self.elevate_cue()
        elif self.keymap[action.english]:
            self.apply_english()
        else:
            self.rotate_camera_aim()

        return task.cont


    def zoom_camera_aim(self):
        with self.mouse:
            s = -self.mouse.get_dy()*ani.zoom_sensitivity

        self.player_cam.node.setPos(autils.multiply_cw(self.player_cam.node.getPos(), 1-s))


    def adjust_head_aim(self):
        with self.mouse:
            alpha_y = max(min(0, self.player_cam.focus.getR() + ani.rotate_sensitivity_y * self.mouse.get_dy()), -90)

        self.player_cam.focus.setR(alpha_y) # Move view vertically


    def rotate_camera_aim(self):
        if self.keymap[action.fine_control]:
            fx, fy = ani.rotate_fine_sensitivity_x, ani.rotate_fine_sensitivity_y
        else:
            fx, fy = ani.rotate_sensitivity_x, ani.rotate_sensitivity_y

        with self.mouse:
            alpha_x = self.player_cam.focus.getH() - fx * self.mouse.get_dx()
            alpha_y = max(min(0, self.player_cam.focus.getR() + fy * self.mouse.get_dy()), -90)

        self.player_cam.focus.setH(alpha_x) # Move view laterally
        self.player_cam.focus.setR(alpha_y) # Move view vertically

        self.fix_cue_stick_to_camera()

        if (-self.cue.get_node('cue_stick_focus').getR() < self.min_theta) or self.magnet_theta:
            self.cue.get_node('cue_stick_focus').setR(-self.min_theta)
            self.hud_elements['jack'].set(self.min_theta)

        if -self.player_cam.focus.getR() < (-self.cue.get_node('cue_stick_focus').getR() + ani.min_player_cam):
            self.player_cam.focus.setR(-(-self.cue.get_node('cue_stick_focus').getR() + ani.min_player_cam))


    def fix_cue_stick_to_camera(self):
        self.cue.get_node('cue_stick_focus').setH(self.player_cam.focus.getH())


    def elevate_cue(self):
        cue = self.cue.get_node('cue_stick_focus')

        with self.mouse:
            delta_elevation = self.mouse.get_dy()*ani.elevate_sensitivity

        old_elevation = -cue.getR()
        new_elevation = max(0, min(ani.max_elevate, old_elevation + delta_elevation))

        if self.min_theta >= new_elevation - self.magnet_threshold:
            # user set theta to minimum value, resume cushion tracking
            self.magnet_theta = True
            new_elevation = self.min_theta
        else:
            # theta has been modified by the user, so no longer tracks the cushion
            self.magnet_theta = False

        cue.setR(-new_elevation)

        if -self.player_cam.focus.getR() < (new_elevation + ani.min_player_cam):
            self.player_cam.focus.setR(-(new_elevation + ani.min_player_cam))

        # update hud
        self.hud_elements['jack'].set(new_elevation)



    def apply_english(self):
        with self.mouse:
            dx, dy = self.mouse.get_dx(), self.mouse.get_dy()

        cue = self.cue.get_node('cue_stick')
        cue_focus = self.cue.get_node('cue_stick_focus')
        R = self.cue.follow.R

        delta_y, delta_z = dx*ani.english_sensitivity, dy*ani.english_sensitivity

        # y corresponds to side spin, z to top/bottom spin
        new_y = cue.getY() + delta_y
        new_z = cue.getZ() + delta_z

        norm = np.sqrt(new_y**2 + new_z**2)
        if norm > ani.max_english*R:
            new_y *= ani.max_english*R/norm
            new_z *= ani.max_english*R/norm

        cue.setY(new_y)
        cue.setZ(new_z)

        # if application of english increases min_theta beyond current elevation, increase elevation
        if self.magnet_theta or self.min_theta >= -cue_focus.getR() - self.magnet_threshold:
            cue_focus.setR(-self.min_theta)

        if -self.player_cam.focus.getR() < (-self.cue.get_node('cue_stick_focus').getR() + ani.min_player_cam):
            self.player_cam.focus.setR(-(-self.cue.get_node('cue_stick_focus').getR() + ani.min_player_cam))

        # update hud
        a, b = -new_y/R, new_z/R
        self.hud_elements['english'].set(a, b)
        self.hud_elements['jack'].set(-self.cue.get_node('cue_stick_focus').getR())

