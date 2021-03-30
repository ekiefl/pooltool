#! /usr/bin/env python

import psim.ani

from psim.ani import (
    px_to_d,
    d_to_px,
    CLOTH_RGB,
    BALL_RGB,
    RAIL_RGB,
    MAX_SCREEN,
    TRACE_LENGTH,
)

import pygame
import pygame.gfxdraw

# Import pygame.locals for easier access to key coordinates
from pygame.locals import (
    K_SPACE,
    K_ESCAPE,
    K_DOWN,
    K_UP,
    K_RIGHT,
    K_LEFT,
    KEYDOWN,
    KEYUP,
    QUIT,
)

import numpy as np


class Ball(pygame.sprite.Sprite):
    def __init__(self, ball, flip, scale, trace=True):
        """A ball sprite

        Parameters
        ==========
        ball : psim.objects.Ball
        """
        self.scale = scale
        self.id = ball.id
        self._ball = ball
        self.radius = d_to_px(ball.R, self.scale)

        self.rvw_history = np.array(ball.history['rvw'])
        self.ss = np.array(ball.history['s'])
        self.ys = d_to_px(scale, self.rvw_history[:,0,0] if flip else self.rvw_history[:,0,1])
        self.xs = d_to_px(scale, self.rvw_history[:,0,1] if flip else self.rvw_history[:,0,0])

        super(Ball, self).__init__()

        self.color = BALL_RGB.get(self.id, (255,255,255))

        self.trace = trace
        self.trace_length = TRACE_LENGTH

        # See https://www.reddit.com/r/pygame/comments/6v9os5/how_to_draw_a_sprite_with_a_circular_shape/
        # for anti-aliased version if you don't like this later
        self.surf = pygame.Surface((2*self.radius, 2*self.radius), pygame.SRCALPHA)
        pygame.draw.circle(
            self.surf,
            self.color,
            (self.radius, self.radius),
            self.radius
        )
        self.rect = self.surf.get_rect()

        self.update(frame=0)


    def update(self, frame):
        self.rect.center = (
            self.xs[frame],
            self.ys[frame],
        )


class State(object):
    def __init__(self):
        self.running = True
        self.paused = False
        self.frame_forward = False
        self.frame_backward = False
        self.increase_speed = False
        self.decrease_speed = False


    def update(self):
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE: self.running = False
                elif event.key == K_SPACE: self.paused = not self.paused
                elif event.key == K_DOWN: self.decrease_speed = True
                elif event.key == K_UP: self.increase_speed = True
                elif event.key == K_RIGHT: self.paused = True; self.frame_forward = True
                elif event.key == K_LEFT: self.paused = True; self.frame_backward = True
            elif event.type == KEYUP:
                if event.key == K_DOWN: self.decrease_speed = False
                elif event.key == K_UP: self.increase_speed = False
                elif event.key == K_RIGHT: self.frame_forward = False
                elif event.key == K_LEFT: self.frame_backward = False
            elif event.type == QUIT:
                self.running = False


class AnimateShot(object):
    def __init__(self, shot, flip=False, size=800, cloth_color=None, rail_color=None):
        """Animate a shot in pygame

        Parameters
        ==========
        shot : psim.engine.ShotSimulation

        size : int
            size in pixels of largest dimension of screen
        """

        self.flip = flip
        self.size = size or MAX_SCREEN
        self.cloth_color = cloth_color or CLOTH_RGB
        self.rail_color = rail_color or RAIL_RGB

        self.shot = shot
        self.table = shot.table
        self.balls = shot.balls
        self.times = shot.balls['cue'].history['t']
        self.num_frames = len(self.times)

        # Ratio of pixel to table dimensions
        self.scale = self.size / max([self.table.w, self.table.l])

        self.rail_thickness = d_to_px(0.01, self.scale)
        pygame.init()

        screen_width = d_to_px(self.scale, self.table.l if self.flip else self.table.w)
        screen_height = d_to_px(self.scale, self.table.w if self.flip else self.table.l)
        self.screen = pygame.display.set_mode((screen_width, screen_height))

        self.init_ball_sprites()

        self.clock = pygame.time.Clock()
        self.fps = self.get_fps()
        self.frame = 0

        self.state = State()


    def init_ball_sprites(self):
        self.ball_sprites = pygame.sprite.Group()
        for ball_id, ball in self.balls.items():
            self.ball_sprites.add(Ball(
                ball,
                self.flip,
                self.scale
            ))


    def get_fps(self):
        return 1/(self.times[-1] - self.times[-2])


    def trace_ball_lines(self):
        if self.frame < 2:
            return

        for ball in self.ball_sprites.sprites():
            if not ball.trace:
                continue

            trace_length = self.frame if self.frame < ball.trace_length else ball.trace_length

            for n in range(trace_length - 1):
                #pygame.gfxdraw.line(
                #    self.screen,
                #    ball.xs[self.frame - trace_length + n],
                #    ball.ys[self.frame - trace_length + n],
                #    ball.xs[self.frame - trace_length + n + 1],
                #    ball.ys[self.frame - trace_length + n + 1],
                #    (*psim.STATE_RGB[ball.ss[self.frame - trace_length + n + 1]], 255 * (1 - np.exp(-n/trace_length))),
                #)
                pygame.draw.line(
                    self.screen,
                    (*psim.STATE_RGB[ball.ss[self.frame - trace_length + n + 1]], 255),
                    (ball.xs[self.frame - trace_length + n], ball.ys[self.frame - trace_length + n]),
                    (ball.xs[self.frame - trace_length + n + 1], ball.ys[self.frame - trace_length + n + 1]),
                    2,
                )


    def render_table(self):
        self.screen.fill(self.cloth_color)


    def display(self):
        # Flip vertical axis so origin is bottom left
        if not self.flip:
            display_surface = pygame.display.get_surface()
            display_surface.blit(pygame.transform.flip(display_surface, False, True), dest=(0, 0))

        # Update the display
        pygame.display.flip()


    def draw_balls(self):
        # Draw the balls on the screen
        for ball in self.ball_sprites:
            self.screen.blit(ball.surf, ball.rect)


    def update_balls(self, frame):
        for ball in self.ball_sprites:
            ball.update(frame=frame)


    def start(self):
        while self.state.running:
            self.state.update()
            self.render_table()
            self.trace_ball_lines()
            self.draw_balls()
            self.display()

            if not self.state.paused:
                self.update_balls(self.frame)
                self.frame += 1

            elif self.state.frame_backward:
                self.frame -= 1
                self.update_balls(self.frame)

            elif self.state.frame_forward:
                self.frame += 1
                self.update_balls(self.frame)

            if self.frame >= self.num_frames:
                # Restart animation
                self.frame = 0

            if self.state.decrease_speed:
                self.fps = max([1, self.fps*0.96])
            elif self.state.increase_speed:
                self.fps = min([30, self.fps*1.04])

            self.clock.tick(self.fps)


